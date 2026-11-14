from django.db.models import Q, Sum, Count
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from core.permissions import IsAdmin
from .models import Coupon, Order
from .serializers import CheckoutSerializer, CouponSerializer, OrderSerializer, OrderUpdateSerializer, ShopSettingsSerializer, QuoteSerializer
from .services import get_settings, place_order, update_order, quote_order


class CheckoutRateThrottle(UserRateThrottle):
    scope = "checkout"
    rate = "20/hour"


class ShopSettingsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(ShopSettingsSerializer(get_settings()).data)

    def patch(self, request):
        if not request.user.is_authenticated or request.user.role != "admin":
            raise PermissionDenied("Only admin can change shop settings.")
        serializer = ShopSettingsSerializer(get_settings(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CouponViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer


class OrderViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer

    def get_throttles(self):
        if self.action == "create":
            return [CheckoutRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        qs = Order.objects.prefetch_related("items").all()
        if self.request.user.role == "admin":
            if self.request.query_params.get("status"):
                qs = qs.filter(status=self.request.query_params["status"])
            if self.request.query_params.get("search"):
                term = self.request.query_params["search"]
                qs = qs.filter(Q(recipient_name__icontains=term) | Q(phone__icontains=term) | Q(delivery_payment_reference__icontains=term))
            return qs
        if self.request.user.role == "customer":
            return qs.filter(customer=self.request.user)
        raise PermissionDenied("Online orders are available to customers and admin only.")

    def list(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    def create(self, request):
        if request.user.role != "customer":
            raise PermissionDenied("Sign in with a customer account to place an order.")
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = place_order(request.user, serializer.validated_data)
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        if request.user.role != "admin":
            raise PermissionDenied("Only admin can update orders.")
        order = self.get_object()
        serializer = OrderUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(self.get_serializer(update_order(order.pk, serializer.validated_data)).data)

    @action(detail=False, methods=["post"])
    def quote(self, request):
        serializer = QuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(quote_order(serializer.validated_data["items"], serializer.validated_data.get("coupon", "")))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        updated = update_order(order.pk, {"status": "cancelled"}, customer=request.user if request.user.role != "admin" else None)
        return Response(self.get_serializer(updated).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAdmin])
    def summary(self, request):
        rows = Order.objects.values("status").annotate(count=Count("pk"))
        return Response({"by_status": {row["status"]: row["count"] for row in rows},
            "delivered_sales": Order.objects.filter(status="delivered").aggregate(total=Sum("subtotal") - Sum("coupon_discount"))["total"] or 0})
