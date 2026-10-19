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
            "selling_price", "is_active", "initial_stock", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_selling_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Selling price cannot be negative.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        initial_stock = validated_data.pop("initial_stock", 0)
        product = Product.objects.create(**validated_data)
        FactoryStock.objects.create(product=product, quantity=initial_stock)
        return product
