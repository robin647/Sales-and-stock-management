from django.db import transaction
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from core.permissions import IsStaffUser

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
        if product_id and qs.model is DailyStock:
            qs = qs.filter(product_id=product_id)
        if date:
            qs = qs.filter(date=date)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs


class DailyStockViewSet(ShowroomScopedMixin, viewsets.ModelViewSet):
    serializer_class = DailyStockSerializer
    permission_classes = [IsStaffUser]

    def queryset_base(self):
        return DailyStock.objects.select_related("showroom", "product").all()

    def perform_create(self, serializer):
        from .services import recalculate_daily_stock

        showroom = serializer.validated_data["showroom"]
        product = serializer.validated_data["product"]
        date = serializer.validated_data["date"]
        with transaction.atomic():
            serializer.save(showroom=showroom)
            recalculate_daily_stock(showroom.id, product.id, date)

    def perform_update(self, serializer):
        from .services import recalculate_daily_stock

        with transaction.atomic():
            old = serializer.instance
            old_showroom_id, old_product_id, old_date = old.showroom_id, old.product_id, old.date
            entry = serializer.save()
            recalculate_daily_stock(old_showroom_id, old_product_id, old_date)
            if (entry.showroom_id, entry.product_id, entry.date) != (old_showroom_id, old_product_id, old_date):
                recalculate_daily_stock(entry.showroom_id, entry.product_id, entry.date)

class DailyBalanceViewSet(ShowroomScopedMixin, viewsets.ModelViewSet):
    serializer_class = DailyBalanceSerializer
    permission_classes = [IsStaffUser]

    def queryset_base(self):
        return DailyBalance.objects.select_related("showroom").all()

    @staticmethod
    def _recalculate_from(showroom_id, start_date):
        """Rebuild opening/closing balances from a changed date onward."""
        entries = DailyBalance.objects.select_for_update().filter(
            showroom_id=showroom_id, date__gte=start_date
        ).order_by("date", "id")
        previous = DailyBalance.objects.select_for_update().filter(
            showroom_id=showroom_id, date__lt=start_date
        ).order_by("-date", "-id").first()
        opening = previous.closing_balance if previous else 0
        for entry in entries:
            entry.opening_balance = opening
            entry.total_sale, entry.closing_balance = entry.compute_totals()
            if entry.closing_balance < 0:
                raise ValidationError({
                    "non_field_errors": [
                        f"Updating this balance would make {entry.date} closing balance negative. "
                        "Review that day's expenses, salary, and deposit."
                    ]
                })
            if entry.closing_balance > 100000:
                raise ValidationError({
                    "non_field_errors": [
                        f"Updating this balance would make {entry.date} closing balance exceed 100,000."
                    ]
                })
            entry.save(update_fields=["opening_balance", "total_sale", "closing_balance", "updated_at"])
            opening = entry.closing_balance

    def perform_create(self, serializer):
        showroom = serializer.validated_data["showroom"]
        date = serializer.validated_data["date"]
        with transaction.atomic():
            serializer.save(showroom=showroom)
            self._recalculate_from(showroom.id, date)

    def perform_update(self, serializer):
        with transaction.atomic():
            old_showroom_id = serializer.instance.showroom_id
            old_date = serializer.instance.date
            entry = serializer.save()
            self._recalculate_from(old_showroom_id, old_date)
            if (entry.showroom_id, entry.date) != (old_showroom_id, old_date):
                self._recalculate_from(entry.showroom_id, entry.date)

    @transaction.atomic
    def perform_destroy(self, instance):
        showroom_id, date = instance.showroom_id, instance.date
        instance.delete()
        self._recalculate_from(showroom_id, date)


class FactoryStockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FactoryStockSerializer
    permission_classes = [IsStaffUser]
    queryset = FactoryStock.objects.select_related("product").filter(product__sales_channel="main").order_by("product_id")

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can view factory inventory.")

class ShowroomStockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ShowroomStockSerializer
    permission_classes = [IsStaffUser]

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
    permission_classes = [IsStaffUser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = StockTransfer.objects.select_related("product", "showroom", "created_by")
        user = self.request.user
        if user.role != "admin":
            queryset = queryset.filter(showroom_id=user.showroom_id)
        elif self.request.query_params.get("showroom"):
            queryset = queryset.filter(showroom_id=self.request.query_params["showroom"])
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
