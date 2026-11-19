from copy import copy
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import CustomTokenObtainPairSerializer
from apps.inventory.services import adjust_stock
from apps.products.serializers import ProductSerializer

from .models import Asset


class ModeratorLoginSerializer(CustomTokenObtainPairSerializer):
    allowed_roles = (User.Role.ADMIN, User.Role.MODERATOR)


class ModeratorAccountSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8, max_length=1024, trim_whitespace=False)
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "password", "is_active"]

    def validate(self, attrs):
        password = attrs.get("password")
        if not self.instance and password is None:
            raise serializers.ValidationError({"password": "Enter a password."})
        if password:
            candidate = copy(self.instance) if self.instance else User(role=User.Role.MODERATOR)
            for field in ("username", "first_name", "last_name", "email"):
                if field in attrs:
                    setattr(candidate, field, attrs[field])
            try:
                validate_password(password, candidate)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(role=User.Role.MODERATOR, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


class CatalogProductSerializer(ProductSerializer):
    online_enabled = serializers.BooleanField(required=False)
    discount = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100, required=False, write_only=True,
    )
    manual_offer_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, allow_null=True, write_only=True,
    )
    stock = serializers.IntegerField(min_value=0, max_value=2147483647, required=False, write_only=True)
    primary_asset = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta(ProductSerializer.Meta):
        fields = [
            "id", "name", "code", "category", "category_name", "size", "color", "description",
            "is_active", "online_enabled", "selling_price", "discount_price", "discount",
            "manual_offer_price", "stock", "factory_quantity", "primary_asset", "created_at",
        ]
        read_only_fields = [*ProductSerializer.Meta.read_only_fields, "discount_price"]

    def variant_color(self, attrs):
        return attrs.get("color", super().variant_color(attrs))

    def allows_zero_offer(self):
        return self.context.get("allow_workspace_free_offer", False) or super().allows_zero_offer()

    def validate(self, attrs):
        percentage = attrs.pop("discount", None)
        manual = attrs.pop("manual_offer_price", None)
        if percentage is None and manual is not None:
            raise serializers.ValidationError({"discount": "Enter a discount when setting an offer price."})
        if percentage is not None:
            regular = attrs.get("selling_price", getattr(self.instance, "selling_price", None))
            if regular is None:
                raise serializers.ValidationError({"selling_price": "Enter the regular price."})
            if not percentage or not regular:
                attrs["discount_price"] = None
            elif manual is not None:
                attrs["discount_price"] = manual
            else:
                attrs["discount_price"] = (
                    regular * (100 - percentage) / 100
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            self.context["allow_workspace_free_offer"] = percentage == 100
        return super().validate(attrs)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result.pop("image", None)
        result["primary_asset"] = getattr(instance, "primary_asset", None)
        return result

    def create(self, validated_data):
        validated_data["initial_stock"] = validated_data.pop("stock", 0)
        validated_data.setdefault("online_enabled", False)
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        stock = validated_data.pop("stock", None)
        product = super().update(instance, validated_data)
        if stock is not None:
            adjust_stock(
                product=product, location="factory", new_quantity=stock,
                reason="Moderator workspace stock count", created_by=self.context["request"].user,
            )
            product.factory_quantity = stock
        return product


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ["id", "product", "kind", "original_name", "content_type", "size_bytes", "primary", "updated_at"]
