from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from .models import CostSpecification, OtherCost, Producer, ProducerCost, ProducerPayment


class CostSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostSpecification
        fields = ["id", "name", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProducerSerializer(serializers.ModelSerializer):
    total_products = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    due_amount = serializers.SerializerMethodField()

    class Meta:
        model = Producer
        fields = [
            "id", "name", "mobile_number", "address", "is_active",
            "total_products", "total_cost", "total_paid", "due_amount",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "total_products", "total_cost", "total_paid", "due_amount"]

    def get_total_products(self, obj):
        return obj.total_products.quantize(Decimal("0.01"))

    def get_total_cost(self, obj):
        return obj.total_cost.quantize(Decimal("0.01"))

    def get_total_paid(self, obj):
        return obj.total_payments.quantize(Decimal("0.01"))

    def get_due_amount(self, obj):
        return obj.outstanding_balance.quantize(Decimal("0.01"))

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Producer name is required.")
        if Producer.objects.filter(name__iexact=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("A producer with this name already exists.")
        return value


class ProducerCostSerializer(serializers.ModelSerializer):
    producer = serializers.PrimaryKeyRelatedField(queryset=Producer.objects.filter(is_active=True))
    producer_name = serializers.SerializerMethodField()
    base_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    gst_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = ProducerCost
        fields = [
            "id", "producer", "producer_name", "bale_number", "product_specification",
            "quantity", "rate", "gst_percentage", "base_cost", "gst_amount",
            "total_cost", "transaction_date", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "producer_name", "base_cost", "gst_amount", "total_cost", "created_at", "updated_at"]

    def get_producer_name(self, obj):
        return obj.producer.name

    def validate(self, attrs):
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", Decimal("0.00")))
        rate = attrs.get("rate", getattr(self.instance, "rate", Decimal("0.00")))
        gst_percentage = attrs.get("gst_percentage", getattr(self.instance, "gst_percentage", Decimal("0.00")))
        if quantity is not None and quantity <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be greater than zero."})
        if rate is not None and rate < 0:
            raise serializers.ValidationError({"rate": "Rate cannot be negative."})
        if gst_percentage is not None and gst_percentage < 0:
            raise serializers.ValidationError({"gst_percentage": "GST percentage cannot be negative."})
        return attrs


class ProducerPaymentSerializer(serializers.ModelSerializer):
    producer = serializers.PrimaryKeyRelatedField(queryset=Producer.objects.filter(is_active=True))
    producer_name = serializers.SerializerMethodField()

    class Meta:
        model = ProducerPayment
        fields = ["id", "producer", "producer_name", "payment_date", "amount", "payment_method", "remarks", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "producer_name", "created_at", "updated_at"]

    def get_producer_name(self, obj):
        return obj.producer.name

    def validate(self, attrs):
        amount = attrs.get("amount", getattr(self.instance, "amount", Decimal("0.00")))
        if amount is not None and amount <= 0:
            raise serializers.ValidationError({"amount": "Payment amount must be greater than zero."})
        return attrs


class OtherCostSerializer(serializers.ModelSerializer):
    specification = serializers.PrimaryKeyRelatedField(queryset=CostSpecification.objects.filter(is_active=True), required=False, allow_null=True)
    specification_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    specification_label = serializers.SerializerMethodField()

    class Meta:
        model = OtherCost
        fields = ["id", "specification", "specification_name", "specification_label", "amount", "cost_date", "notes", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "specification_label", "created_at", "updated_at"]

    def get_specification_label(self, obj):
        return obj.specification.name

    @transaction.atomic
    def create(self, validated_data):
        specification_name = validated_data.pop("specification_name", "")
        spec = validated_data.get("specification")
        if not spec and specification_name:
            spec, _ = CostSpecification.objects.get_or_create(name__iexact=specification_name.strip(), defaults={"name": specification_name.strip()})
            validated_data["specification"] = spec
        if not spec:
            raise serializers.ValidationError({"specification": "Cost specification is required."})
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        specification_name = validated_data.pop("specification_name", "")
        spec = validated_data.get("specification")
        if not spec and specification_name:
            spec, _ = CostSpecification.objects.get_or_create(name__iexact=specification_name.strip(), defaults={"name": specification_name.strip()})
            validated_data["specification"] = spec
        if not spec and instance.specification_id:
            validated_data["specification"] = instance.specification
        if validated_data.get("specification") is None:
            raise serializers.ValidationError({"specification": "Cost specification is required."})
        return super().update(instance, validated_data)

    def validate(self, attrs):
        amount = attrs.get("amount", getattr(self.instance, "amount", Decimal("0.00")))
        if amount is not None and amount <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than zero."})
        return attrs
