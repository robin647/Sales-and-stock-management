from django.db.models import Case, DecimalField, F, IntegerField, Q, Value, When
from django.db.models.functions import Cast, Coalesce, Round
from rest_framework import serializers

from apps.accounts.models import User
from apps.products.models import Product


class CatalogFilters(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=150)
    category = serializers.IntegerField(required=False, min_value=1)
    discount = serializers.DecimalField(required=False, max_digits=5, decimal_places=2, min_value=0, max_value=100)
    offer = serializers.ChoiceField(required=False, choices=["yes", "no"])
    color = serializers.CharField(required=False, max_length=60)
    size = serializers.CharField(required=False, max_length=30)
    stock = serializers.ChoiceField(required=False, choices=["available", "low", "out"])
    active = serializers.ChoiceField(required=False, choices=["true", "false"])
    ordering = serializers.ChoiceField(required=False, choices=[
        "name", "-name", "created_at", "-created_at", "selling_price", "-selling_price",
        "effective_price", "-effective_price",
    ])


def visible_products(user):
    products = Product.objects.filter(sales_channel="online")
    return products if user.role == User.Role.ADMIN else products.filter(is_active=True)


def catalog(user):
    percent = DecimalField(max_digits=5, decimal_places=2)
    return visible_products(user).select_related("category").annotate(
        factory_quantity=Coalesce("factory_stock__quantity", Value(0), output_field=IntegerField()),
        effective_price=Coalesce("discount_price", "selling_price"),
        effective_discount=Case(
            When(selling_price__gt=0, discount_price__isnull=False, then=Cast(Round(Cast(
                100.0 * (F("selling_price") - F("discount_price")) / F("selling_price"),
                DecimalField(max_digits=15, decimal_places=6),
            ), 2), percent)),
            default=Value(0), output_field=percent,
        ),
    )


def filtered_catalog(request):
    params = request.query_params
    filters = CatalogFilters(data={key: params[key] for key in CatalogFilters().fields if params.get(key)})
    filters.is_valid(raise_exception=True)
    values = filters.validated_data
    products = catalog(request.user)
    if "search" in values:
        search = values["search"]
        products = products.filter(Q(name__icontains=search) | Q(code__icontains=search))
    for field, lookup in (
        ("category", "category_id"), ("discount", "effective_discount"), ("color", "color__iexact"), ("size", "size__iexact"),
    ):
        if field in values:
            products = products.filter(**{lookup: values[field]})
    if "offer" in values:
        products = products.filter(discount_price__isnull=values["offer"] == "no")
    if "active" in values and request.user.role == User.Role.ADMIN:
        products = products.filter(is_active=values["active"] == "true")
    stock = values.get("stock")
    if stock == "available":
        products = products.filter(factory_quantity__gt=0)
    elif stock == "low":
        products = products.filter(factory_quantity__range=(1, 5))
    elif stock == "out":
        products = products.filter(factory_quantity=0)
    return products.order_by(values.get("ordering", "-created_at"), "pk")
