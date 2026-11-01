from rest_framework import serializers

from .models import SwingLot, SwingOperator, SwingPayment, SwingReject
from .services import rejected_quantity, validate_lot_capacity, validate_reject_capacity


class SwingOperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwingOperator
        fields = ["id", "name", "nid_number", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Operator name is required.")
        return value

    def validate_nid_number(self, value):
        return value.strip()


class SwingLotSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source="operator.name", read_only=True)
    rejected_quantity = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()

    class Meta:
        model = SwingLot
        fields = [
            "id", "operator", "operator_name", "lot_number", "quantity", "fabric_specification",
            "rate", "cutting_master_name", "lot_date", "rejected_quantity", "available_quantity",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "operator_name", "rejected_quantity", "available_quantity", "is_active", "created_at", "updated_at"]

    def get_rejected_quantity(self, lot):
        return rejected_quantity(lot)

    def get_available_quantity(self, lot):
        return max(lot.quantity - rejected_quantity(lot), 0)

    def validate_operator(self, operator):
        if not operator.is_active:
            raise serializers.ValidationError("Select an active swing operator.")
        if self.instance and operator.pk != self.instance.operator_id:
            raise serializers.ValidationError("A saved lot cannot be reassigned to another operator.")
        return operator

    def validate(self, attrs):
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 0))
        if self.instance:
            validate_lot_capacity(self.instance, quantity)
            lot_date = attrs.get("lot_date", self.instance.lot_date)
            first_reject_date = self.instance.rejections.filter(is_active=True).order_by("reject_date").values_list("reject_date", flat=True).first()
            if first_reject_date and lot_date > first_reject_date:
                raise serializers.ValidationError({"lot_date": "Lot date cannot be later than an existing rejection date."})
        return attrs


class SwingPaymentSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source="operator.name", read_only=True)

    class Meta:
        model = SwingPayment
        fields = ["id", "operator", "operator_name", "payment_date", "amount", "remarks", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "operator_name", "is_active", "created_at", "updated_at"]

    def validate_operator(self, operator):
        if not operator.is_active:
            raise serializers.ValidationError("Select an active swing operator.")
        if self.instance and operator.pk != self.instance.operator_id:
            raise serializers.ValidationError("A saved payment cannot be reassigned to another operator.")
        return operator


class SwingRejectSerializer(serializers.ModelSerializer):
    lot_number = serializers.CharField(source="lot.lot_number", read_only=True)
    operator = serializers.IntegerField(source="lot.operator_id", read_only=True)
    operator_name = serializers.CharField(source="lot.operator.name", read_only=True)
    lot_rate = serializers.DecimalField(source="lot.rate", max_digits=12, decimal_places=2, read_only=True)
    reject_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = SwingReject
        fields = [
            "id", "lot", "lot_number", "operator", "operator_name", "lot_rate", "quantity",
            "reject_date", "reject_amount", "remarks", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "lot_number", "operator", "operator_name", "lot_rate", "reject_amount", "is_active", "created_at", "updated_at"]

    def validate_lot(self, lot):
        if not lot.is_active:
            raise serializers.ValidationError("Rejections can only be recorded against an active lot.")
        if self.instance and lot.pk != self.instance.lot_id:
            raise serializers.ValidationError("A saved rejection cannot be moved to another lot.")
        return lot

    def validate(self, attrs):
        lot = attrs.get("lot", getattr(self.instance, "lot", None))
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 0))
        if lot:
            reject_date = attrs.get("reject_date", getattr(self.instance, "reject_date", None))
            if reject_date and reject_date < lot.lot_date:
                raise serializers.ValidationError({"reject_date": "Reject date cannot be earlier than the lot date."})
            validate_reject_capacity(lot, quantity, self.instance.pk if self.instance else None)
        return attrs
