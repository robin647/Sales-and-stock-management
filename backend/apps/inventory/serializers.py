from rest_framework import serializers

from apps.showrooms.models import Showroom
from .models import DailyBalance, DailyStock, FactoryStock, ShowroomStock, StockTransfer

class DailyStockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)

    class Meta:
        model = DailyStock
        fields = [
            "id", "showroom", "showroom_name", "product", "product_name", "date",
            "opening_qty", "received_qty", "sold_qty", "return_qty", "returned_to_factory_qty", "closing_qty",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "opening_qty", "closing_qty", "created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        showroom = attrs.get("showroom") or getattr(self.instance, "showroom", None)
        product = attrs.get("product") or getattr(self.instance, "product", None)
        date = attrs.get("date") or getattr(self.instance, "date", None)

        opening = getattr(self.instance, "opening_qty", None)
        if opening is None and showroom and product and date:
            previous = DailyStock.objects.filter(showroom=showroom, product=product, date__lt=date).order_by("-date").first()
            opening = previous.closing_qty if previous else 0
        if opening is not None:
            closing = opening + attrs.get("received_qty", getattr(self.instance, "received_qty", 0)) - attrs.get("sold_qty", getattr(self.instance, "sold_qty", 0)) - attrs.get("returned_to_factory_qty", getattr(self.instance, "returned_to_factory_qty", 0)) + attrs.get("return_qty", getattr(self.instance, "return_qty", 0))
            if closing < 0:
                raise serializers.ValidationError({"non_field_errors": [f"Insufficient stock: this change would leave {closing} units. Reduce sold/return-to-factory quantity or record a stock receipt first."]})

        if DailyStock.objects.filter(showroom=showroom, product=product, date=date).exclude(
            pk=getattr(self.instance, "pk", None)
        ).exists():
            raise serializers.ValidationError(
                "A stock entry for this product on this date already exists for this showroom."
            )
        return attrs

    def create(self, validated_data):
        showroom = validated_data["showroom"]
        product = validated_data["product"]
        date = validated_data["date"]

        previous_entry = (
            DailyStock.objects.filter(showroom=showroom, product=product, date__lt=date)
            .order_by("-date")
            .first()
        )
        validated_data["opening_qty"] = previous_entry.closing_qty if previous_entry else 0
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

class DailyBalanceSerializer(serializers.ModelSerializer):

    showroom = serializers.PrimaryKeyRelatedField(
        queryset=Showroom.objects.all(), required=False
    )
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)

    class Meta:
        model = DailyBalance
        fields = [
            "id", "showroom", "showroom_name", "date",
            "opening_balance", "cash_sale", "card_sale", "total_sale",
            "expense", "salary", "deposit", "closing_balance",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "opening_balance", "total_sale", "closing_balance",
            "created_by", "created_at", "updated_at",
        ]

    validators = []

    def validate(self, attrs):
        showroom = attrs.get("showroom") or getattr(self.instance, "showroom", None)
        request = self.context.get("request")
        if showroom is None and request and request.user.role != "admin":
            showroom = request.user.showroom
        date = attrs.get("date") or getattr(self.instance, "date", None)

        # The opening for an edited entry comes from the preceding date, not
        # from the value stored on this row (which may be stale after edits).
        opening = None
        if showroom and date:
            previous = DailyBalance.objects.filter(
                showroom=showroom, date__lt=date
            ).exclude(pk=getattr(self.instance, "pk", None)).order_by("-date").first()
            opening = previous.closing_balance if previous else 0
        if opening is not None:
            cash = attrs.get("cash_sale", getattr(self.instance, "cash_sale", 0))
            expense = attrs.get("expense", getattr(self.instance, "expense", 0))
            salary = attrs.get("salary", getattr(self.instance, "salary", 0))
            deposit = attrs.get("deposit", getattr(self.instance, "deposit", 0))
            if opening + cash - expense - salary - deposit < 0:
                raise serializers.ValidationError({"non_field_errors": ["Closing balance cannot be negative. Check expense, salary, and deposit against opening balance and cash sale."]})

        if DailyBalance.objects.filter(showroom=showroom, date=date).exclude(
            pk=getattr(self.instance, "pk", None)
        ).exists():
            raise serializers.ValidationError(
                "A balance entry for this date already exists for this showroom."
            )
        return attrs

    def create(self, validated_data):
        showroom = validated_data.get("showroom") or self.context["request"].user.showroom
        validated_data["showroom"] = showroom
        date = validated_data["date"]

        previous_entry = (
            DailyBalance.objects.filter(showroom=showroom, date__lt=date).order_by("-date").first()
        )
        validated_data["opening_balance"] = previous_entry.closing_balance if previous_entry else 0
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Date/showroom changes also need an opening from the new position.
        showroom = validated_data.get("showroom", instance.showroom)
        date = validated_data.get("date", instance.date)
        previous = DailyBalance.objects.filter(
            showroom=showroom, date__lt=date
        ).exclude(pk=instance.pk).order_by("-date").first()
        validated_data["opening_balance"] = previous.closing_balance if previous else 0
        return super().update(instance, validated_data)

class FactoryStockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = FactoryStock
        fields = ["id", "product", "product_name", "quantity", "updated_at"]

class ShowroomStockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)

    class Meta:
        model = ShowroomStock
        fields = ["id", "product", "product_name", "showroom", "showroom_name", "quantity", "updated_at"]

class StockTransferSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    from_location = serializers.SerializerMethodField()
    to_location = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    showroom = serializers.PrimaryKeyRelatedField(queryset=Showroom.objects.all(), required=False, allow_null=True)

    class Meta:
        model = StockTransfer
        fields = ["id", "product", "product_name", "showroom", "quantity", "transfer_type", "date", "notes", "from_location", "to_location", "status", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_from_location(self, obj):
        return {
            "receive": "Factory",
            "sale": obj.showroom.name,
            "factory_return": obj.showroom.name,
            "return": "Customer",
        }[obj.transfer_type]

    def get_to_location(self, obj):
        return {
            "receive": obj.showroom.name,
            "sale": "Customer",
            "factory_return": "Factory",
            "return": obj.showroom.name,
        }[obj.transfer_type]

    def get_status(self, obj):
        return "Completed"

    def create(self, validated_data):
        from .services import transfer_stock

        return transfer_stock(created_by=self.context["request"].user, **validated_data)

    def update(self, instance, validated_data):
        unknown_fields = set(validated_data) - {"quantity", "transfer_type"}
        if unknown_fields:
            raise serializers.ValidationError("Only quantity and transfer type can be edited.")
        from .services import update_transfer
        return update_transfer(
            transfer=instance,
            quantity=validated_data.get("quantity", instance.quantity),
            transfer_type=validated_data.get("transfer_type", instance.transfer_type),
        )
