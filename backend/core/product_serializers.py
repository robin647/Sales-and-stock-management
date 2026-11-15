from rest_framework import serializers


class InventoryProductSerializer(serializers.ModelSerializer):
    """Prevent online inventory from being used in showroom/wholesale entries."""
    def get_fields(self):
        fields = super().get_fields()
        product = fields.get("product")
        if isinstance(product, serializers.PrimaryKeyRelatedField) and product.queryset is not None:
            channel = getattr(self.context.get("view"), "product_channel", "main")
            product.queryset = product.queryset.filter(sales_channel=channel)
        return fields
