from rest_framework import serializers
from decimal import Decimal
from .models import Coupon, Order, OrderItem, ShopSettings


class ShopSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopSettings
        exclude = ["id"]

    def validate_whatsapp_number(self, value):
        if not value.isdigit() or not 8 <= len(value) <= 20:
            raise serializers.ValidationError("Enter digits including country code, without + or spaces.")
        return value


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"
        read_only_fields = ["used_count"]

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", "fixed"))
        value = attrs.get("value", getattr(self.instance, "value", 0))
        if kind == "percent" and value > 100:
            raise serializers.ValidationError({"value": "Percentage cannot exceed 100."})
        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        exclude = ["order"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    cod_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        exclude = ["request_key"]

    def get_cod_amount(self, obj):
        return str(obj.subtotal - obj.coupon_discount)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context["request"].user.role != "admin":
            data.pop("admin_notes", None)
        return data


class CheckoutItemSerializer(serializers.Serializer):
    product = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=1000)


class CheckoutSerializer(serializers.Serializer):
    request_key = serializers.UUIDField()
    recipient_name = serializers.CharField(max_length=120)
    phone = serializers.RegexField(r"^\+?[0-9\s-]{8,25}$", max_length=25)
    address = serializers.CharField(max_length=1000)
    city = serializers.CharField(max_length=100)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    delivery_payment_reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    coupon = serializers.CharField(max_length=30, required=False, allow_blank=True)
    expected_total = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    expected_shipping_fee = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))
    items = CheckoutItemSerializer(many=True, allow_empty=False, max_length=100)

    def validate_items(self, items):
        if len({i["product"] for i in items}) != len(items):
            raise serializers.ValidationError("Combine repeated products into one line.")
        return items

    def validate_delivery_payment_reference(self, value):
        return value.strip().upper()


class QuoteSerializer(serializers.Serializer):
    items = CheckoutItemSerializer(many=True, allow_empty=False, max_length=100)
    coupon = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate_items(self, items):
        if len({i["product"] for i in items}) != len(items):
            raise serializers.ValidationError("Combine repeated products into one line.")
        return items


class OrderUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices, required=False)
    delivery_payment_status = serializers.ChoiceField(choices=["submitted", "verified", "rejected", "not_required"], required=False)
    tracking_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    courier = serializers.CharField(max_length=100, required=False, allow_blank=True)
    admin_notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)
