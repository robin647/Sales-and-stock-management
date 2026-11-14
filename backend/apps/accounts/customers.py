"""Admin-only customer directory; order snapshots survive account deletion."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, DecimalField, F, Max, Q, Sum, Value
from django.db.models.functions import Coalesce, Concat
from django.shortcuts import get_object_or_404
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from core.permissions import IsAdmin
from .models import User


class CustomerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    order_count = serializers.IntegerField(read_only=True)
    delivered_count = serializers.IntegerField(read_only=True)
    active_order_count = serializers.IntegerField(read_only=True)
    delivered_spend = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    last_order_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "name", "username", "first_name", "last_name", "email", "phone_number",
            "is_active", "date_joined", "last_login", "order_count", "delivered_count",
            "active_order_count", "delivered_spend", "last_order_at"]
        read_only_fields = fields

    def get_name(self, obj):
        return obj.get_full_name().strip() or obj.username


class CustomerViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdmin]
    serializer_class = CustomerSerializer

    def base_queryset(self):
        return User.objects.filter(role=User.Role.CUSTOMER, is_staff=False, is_superuser=False)

    def get_queryset(self):
        qs = self.base_queryset().annotate(
            order_count=Count("online_orders"),
            delivered_count=Count("online_orders", filter=Q(online_orders__status="delivered")),
            active_order_count=Count("online_orders", filter=Q(online_orders__status__in=["pending", "confirmed", "shipped"])),
            delivered_spend=Coalesce(Sum(F("online_orders__subtotal") - F("online_orders__coupon_discount"),
                filter=Q(online_orders__status="delivered"), output_field=DecimalField(max_digits=14, decimal_places=2)),
                Value(Decimal("0")), output_field=DecimalField(max_digits=14, decimal_places=2)),
            last_order_at=Max("online_orders__created_at"),
        )
        if self.action == "list":
            search = self.request.query_params.get("search", "").strip()
            if search:
                qs = qs.annotate(search_name=Concat("first_name", Value(" "), "last_name")).filter(Q(search_name__icontains=search)
                    | Q(email__icontains=search) | Q(phone_number__icontains=search) | Q(username__icontains=search))
            status = self.request.query_params.get("status")
            if status in ("active", "inactive"):
                qs = qs.filter(is_active=status == "active")
            if self.request.query_params.get("has_orders") == "true":
                qs = qs.filter(order_count__gt=0)
        return qs.order_by("-date_joined", "-pk")

    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.base_queryset()
        return Response({"total": qs.count(), "active": qs.filter(is_active=True).count(),
            "inactive": qs.filter(is_active=False).count(), "with_orders": qs.filter(online_orders__isnull=False).distinct().count()})

    @action(detail=True, methods=["get"])
    def orders(self, request, pk=None):
        from apps.shop.models import Order
        from apps.shop.serializers import OrderSerializer
        customer = self.get_object()
        queryset = Order.objects.filter(customer=customer).prefetch_related("items").order_by("-created_at", "-pk")
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(OrderSerializer(page, many=True, context={"request": request}).data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        customer = self.get_object()
        customer = get_object_or_404(self.base_queryset().select_for_update(), pk=customer.pk)
        preserved_orders = customer.online_orders.count()
        for token in OutstandingToken.objects.filter(user=customer):
            BlacklistedToken.objects.get_or_create(token=token)
        customer.delete()
        return Response({"detail": "Customer account deleted. Existing order records have been preserved.",
            "preserved_orders": preserved_orders})
