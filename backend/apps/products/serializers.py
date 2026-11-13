from django.db import transaction
from rest_framework import serializers

from apps.inventory.models import FactoryStock
from .models import Product, ProductCategory

class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name"]

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    initial_stock = serializers.IntegerField(write_only=True, min_value=0, required=False, default=0)

    class Meta:
        model = Product
        fields = [
            "id", "name", "code", "category", "category_name", "size",
            "selling_price", "discount_price", "image", "is_active", "initial_stock", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_selling_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Selling price cannot be negative.")
        return value

    def validate(self, attrs):
        regular_price = attrs.get("selling_price", getattr(self.instance, "selling_price", None))
        discount_price = attrs.get("discount_price", getattr(self.instance, "discount_price", None))
        if discount_price is not None and regular_price is not None and discount_price >= regular_price:
            raise serializers.ValidationError({"discount_price": "Discount price must be lower than the regular price."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        initial_stock = validated_data.pop("initial_stock", 0)
        product = Product.objects.create(**validated_data)
        FactoryStock.objects.create(product=product, quantity=initial_stock)
        return product
