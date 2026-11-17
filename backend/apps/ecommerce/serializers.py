from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from django.db import transaction
from apps.accounts.models import User
from .models import TeamMember


class RecordSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    def get_label(self, obj):
        return str(getattr(obj, "name", None) or getattr(obj, "title", None) or getattr(obj, "reference", None)
                   or getattr(obj, "subject", None) or f"#{obj.pk}")

    def get_fields(self):
        fields = super().get_fields()
        for key, field in fields.items():
            if isinstance(field, serializers.PrimaryKeyRelatedField) and field.queryset is not None:
                if key == "product":
                    field.queryset = field.queryset.filter(sales_channel="online")
                elif key == "item":
                    field.queryset = field.queryset.filter(product__sales_channel="online", order__status="delivered")
        return fields

    def validate(self, attrs):
        obj = self.instance
        model = self.Meta.model.__name__
        value = lambda field, default=None: attrs.get(field, getattr(obj, field, default))
        if model == "Campaign" and value("ends_at") <= value("starts_at"):
            raise serializers.ValidationError({"ends_at": "End must be after start."})
        if model == "SeoEntry" and (not value("path").startswith("/") or "?" in value("path")):
            raise serializers.ValidationError({"path": "Use a page path starting with /, without query parameters."})
        if model == "Locale":
            attrs["currency_code"] = value("currency_code").upper()
            if len(attrs["currency_code"]) != 3 or not attrs["currency_code"].isascii() or not attrs["currency_code"].isalpha():
                raise serializers.ValidationError({"currency_code": "Use a three-letter currency code, such as BDT or USD."})
            if attrs["currency_code"] == "BDT" and value("exchange_rate", 1) != 1:
                raise serializers.ValidationError({"exchange_rate": "BDT is the settlement currency; its rate must be 1."})
            if value("is_default", False) and not value("is_active", True):
                raise serializers.ValidationError({"is_active": "The default locale must be active."})
        if model == "ContentPage":
            link = value("link", "")
            if link and not (link.startswith("/") and not link.startswith("//") or link.startswith("https://")):
                raise serializers.ValidationError({"link": "Use a local path or an HTTPS link."})
        return attrs


def serializer_for(model):
    meta = type("Meta", (), {"model": model, "fields": "__all__", "read_only_fields": ["id", "created_at", "updated_at", "customer"]})
    return type(model.__name__ + "Serializer", (RecordSerializer,), {"Meta": meta})


class TeamSerializer(RecordSerializer):
    username = serializers.CharField(max_length=150, write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    login_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TeamMember
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate(self, attrs):
        if not self.instance and (not attrs.get("username") or not attrs.get("password")):
            raise serializers.ValidationError("Username and password are required for a new team member.")
        username = attrs.get("username")
        if username and User.objects.filter(username=username).exclude(pk=self.instance.user_id if self.instance else None).exists():
            raise serializers.ValidationError({"username": "Username is already in use."})
        if self.instance and username and username != self.instance.user.username:
            raise serializers.ValidationError({"username": "Login names cannot be changed."})
        if attrs.get("password"):
            try:
                validate_password(attrs["password"], self.instance.user if self.instance else User(username=username))
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": exc.messages})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(username=validated_data.pop("username"), password=validated_data.pop("password"), role="ecommerce_staff")
        return TeamMember.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        validated_data.pop("username", None)
        if password:
            instance.user.set_password(password)
            instance.user.save(update_fields=["password"])
        return super().update(instance, validated_data)
