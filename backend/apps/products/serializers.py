from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from uuid import uuid4

from django.db import transaction
from django.urls import reverse
from PIL import Image, ImageOps
from rest_framework import serializers

from apps.inventory.models import FactoryStock
from .models import Product, ProductCategory, ProductPhoto

class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name"]

class ProductSerializer(serializers.ModelSerializer):
    size = serializers.CharField(required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, max_length=10000)
    is_active = serializers.BooleanField(required=False, default=True)
    online_enabled = serializers.BooleanField(required=False, default=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    initial_stock = serializers.IntegerField(write_only=True, min_value=0, required=False, default=0)
    image = serializers.ImageField(write_only=True, required=False)
    remove_image = serializers.BooleanField(write_only=True, required=False, default=False)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0"), max_value=Decimal("99.99"), write_only=True, required=False)
    factory_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "code", "category", "category_name", "size",
            "selling_price", "discount_price", "discount_percentage", "image", "image_url", "remove_image",
            "description", "is_featured", "online_enabled", "factory_quantity", "is_active", "initial_stock", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_selling_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Selling price cannot be negative.")
        return value

    def validate(self, attrs):
        regular_price = attrs.get("selling_price", getattr(self.instance, "selling_price", None))
        if "discount_percentage" in attrs:
            if "discount_price" in attrs and attrs["discount_price"] is not None:
                raise serializers.ValidationError({"discount_price": "Use either a discount percentage or an offer price."})
            percentage = attrs.pop("discount_percentage")
            attrs["discount_price"] = ((regular_price * (100 - percentage) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if percentage else None)
        discount_price = attrs.get("discount_price", getattr(self.instance, "discount_price", None))
        if discount_price is not None and discount_price <= 0:
            raise serializers.ValidationError({"discount_price": "Offer price must be greater than zero."})
        if discount_price is not None and regular_price is not None and discount_price >= regular_price:
            raise serializers.ValidationError({"discount_price": "Discount price must be lower than the regular price."})
        return attrs

    def validate_image(self, upload):
        if upload.size > 3 * 1024 * 1024:
            raise serializers.ValidationError("Choose an image under 3 MB.")
        with Image.open(upload) as image:
            if image.width * image.height > 20_000_000:
                raise serializers.ValidationError("Image dimensions are too large.")
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((1000, 1000))
            output = BytesIO()
            image.save(output, "WEBP", quality=78)
            if output.tell() > 250_000:
                output = BytesIO()
                image.thumbnail((720, 720))
                image.save(output, "WEBP", quality=60)
            if output.tell() > 250_000:
                raise serializers.ValidationError("Please choose a smaller image.")
            return output.getvalue()

    def _save_photo(self, product, content, remove):
        if remove:
            ProductPhoto.objects.filter(product=product).delete()
            product.image = ""
            product.image_url = ""
            product.photo_version = ""
        if content is not None:
            ProductPhoto.objects.update_or_create(product=product, defaults={"content": content})
            product.image = ""
            product.image_url = ""
            product.photo_version = str(uuid4())
        if remove or content is not None:
            product.save(update_fields=["image", "image_url", "photo_version"])

    def to_representation(self, instance):
        result = super().to_representation(instance)
        request = self.context.get("request")
        image = instance.image_url
        if not image and instance.photo_version:
            image = reverse("product-photo", args=[instance.pk]) + f"?v={instance.photo_version}"
            if request:
                image = request.build_absolute_uri(image)
        if not image and instance.image:
            image = instance.image.url
            if request:
                image = request.build_absolute_uri(image)
        result["image"] = image or None
        price = instance.discount_price if instance.discount_price is not None else instance.selling_price
        result["effective_price"] = str(price)
        result["discount_percent"] = round(float((instance.selling_price - price) / instance.selling_price * 100), 2) if instance.selling_price else 0
        return result

    @transaction.atomic
    def create(self, validated_data):
        initial_stock = validated_data.pop("initial_stock", 0)
        content = validated_data.pop("image", None)
        remove = validated_data.pop("remove_image", False)
        product = Product.objects.create(**validated_data)
        FactoryStock.objects.create(product=product, quantity=initial_stock)
        self._save_photo(product, content, remove)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("initial_stock", None)
        content = validated_data.pop("image", None)
        remove = validated_data.pop("remove_image", False)
        instance = super().update(instance, validated_data)
        self._save_photo(instance, content, remove)
        return instance
