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
            "opening_qty", "received_qty", "sold_qty", "return_qty", "closing_qty",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "opening_qty", "closing_qty", "created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        showroom = attrs.get("showroom") or getattr(self.instance, "showroom", None)
        product = attrs.get("product") or getattr(self.instance, "product", None)
        date = attrs.get("date") or getattr(self.instance, "date", None)

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

    def validate(self, attrs):
        showroom = attrs.get("showroom") or getattr(self.instance, "showroom", None)
        date = attrs.get("date") or getattr(self.instance, "date", None)

        if DailyBalance.objects.filter(showroom=showroom, date=date).exclude(
            pk=getattr(self.instance, "pk", None)
        ).exists():
            raise serializers.ValidationError(
                "A balance entry for this date already exists for this showroom."
            )
        return attrs

    def create(self, validated_data):
        showroom = validated_data["showroom"]
        date = validated_data["date"]

        previous_entry = (
            DailyBalance.objects.filter(showroom=showroom, date__lt=date).order_by("-date").first()
        )
        validated_data["opening_balance"] = previous_entry.closing_balance if previous_entry else 0
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


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
        return {"receive": "Factory", "sale": obj.showroom.name, "return": "Customer"}[obj.transfer_type]

    def get_to_location(self, obj):
        return {"receive": obj.showroom.name, "sale": "Customer", "return": obj.showroom.name}[obj.transfer_type]

    def get_status(self, obj):
        return "Completed"

    def create(self, validated_data):
        from .services import transfer_stock

        return transfer_stock(created_by=self.context["request"].user, **validated_data)
