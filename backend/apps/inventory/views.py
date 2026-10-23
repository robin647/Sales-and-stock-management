from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import DailyBalance, DailyStock, FactoryStock, ShowroomStock, StockTransfer
from .serializers import (DailyBalanceSerializer, DailyStockSerializer, FactoryStockSerializer,
                          ShowroomStockSerializer, StockTransferSerializer)

class ShowroomScopedMixin:
    """
    Shared scoping rule used by both DailyStock and DailyBalance viewsets:
    - Admin sees everything, optionally filtered by ?showroom=<id>.
    - Showroom user only ever sees / writes their OWN showroom's data,
      no matter what showroom_id the client sends in the request body.
      This is the server-side enforcement required by the spec: a
      showroom user cannot access another showroom's data even if the
      frontend is tampered with.
    """

    def get_queryset(self):
        qs = self.queryset_base()
        user = self.request.user
        if user.role == "admin":
            showroom_id = self.request.query_params.get("showroom")
            if showroom_id:
                qs = qs.filter(showroom_id=showroom_id)
        else:
            qs = qs.filter(showroom_id=user.showroom_id)

        product_id = self.request.query_params.get("product")
        date = self.request.query_params.get("date")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if product_id:
            qs = qs.filter(product_id=product_id)
        if date:
            qs = qs.filter(date=date)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "admin":
            if not serializer.validated_data.get("showroom"):
                raise PermissionDenied("Admin must specify a showroom when creating an entry.")
            serializer.save()
        else:
            if not user.showroom_id:
                raise PermissionDenied("Your account is not assigned to a showroom.")

            serializer.save(showroom=user.showroom)

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == "admin":
            serializer.save()
        else:
            if not user.showroom_id:
                raise PermissionDenied("Your account is not assigned to a showroom.")
            serializer.save(showroom=user.showroom)

class DailyStockViewSet(ShowroomScopedMixin, viewsets.ModelViewSet):
    serializer_class = DailyStockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def queryset_base(self):
        return DailyStock.objects.select_related("showroom", "product").all()

class DailyBalanceViewSet(ShowroomScopedMixin, viewsets.ModelViewSet):
    serializer_class = DailyBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def queryset_base(self):
        return DailyBalance.objects.select_related("showroom").all()

    def perform_update(self, serializer):
        from django.db import transaction

        with transaction.atomic():
            entry = serializer.save()
            later_entries = DailyBalance.objects.select_for_update().filter(
                showroom_id=entry.showroom_id, date__gt=entry.date
            ).order_by("date", "id")
            previous = entry
            for later in later_entries:
                later.opening_balance = previous.closing_balance
                later.save(update_fields=["opening_balance", "total_sale", "closing_balance", "updated_at"])
                previous = later

class FactoryStockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FactoryStockSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = FactoryStock.objects.select_related("product").all()

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can view factory inventory.")

class ShowroomStockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ShowroomStockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ShowroomStock.objects.select_related("product", "showroom")
        if self.request.user.role == "admin":
            showroom_id = self.request.query_params.get("showroom")
            if showroom_id:
                queryset = queryset.filter(showroom_id=showroom_id)
            return queryset
        return queryset.filter(showroom_id=self.request.user.showroom_id)

class StockTransferViewSet(viewsets.ModelViewSet):
    serializer_class = StockTransferSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = StockTransfer.objects.select_related("product", "showroom", "created_by")
        user = self.request.user
        if user.role != "admin":
            queryset = queryset.filter(showroom_id=user.showroom_id)
        if self.request.query_params.get("date"):
            queryset = queryset.filter(date=self.request.query_params["date"])
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "admin":
            showroom = serializer.validated_data.get("showroom")
            if not showroom:
                raise PermissionDenied("Admin must select a showroom.")
        else:
            if not user.showroom_id:
                raise PermissionDenied("Your account is not assigned to a showroom.")
            serializer.save(showroom=user.showroom)
            return
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        from .services import delete_transfer

        delete_transfer(transfer=self.get_object())
        return Response(status=204)
