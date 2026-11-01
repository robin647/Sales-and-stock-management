from decimal import Decimal

from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SwingLot, SwingOperator, SwingPayment, SwingReject
from .serializers import (
    SwingLotSerializer,
    SwingOperatorSerializer,
    SwingPaymentSerializer,
    SwingRejectSerializer,
)
from .services import validate_lot_capacity, validate_reject_capacity


ZERO = Decimal("0.00")


class SwingDashboardSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can access Swing Management.")

    def get(self, request):
        operators = SwingOperator.objects.filter(is_active=True).prefetch_related(
            "lots", "payments", "lots__rejections"
        )
        rows = []
        for operator in operators:
            lots = [lot for lot in operator.lots.all() if lot.is_active]
            payments = [payment for payment in operator.payments.all() if payment.is_active]
            rejects = [reject for lot in lots for reject in lot.rejections.all() if reject.is_active]
            total_products = sum(lot.quantity for lot in lots)
            rejected_products = sum(reject.quantity for reject in rejects)
            total_work = sum((Decimal(lot.quantity) * lot.rate for lot in lots), ZERO)
            reject_total = sum((Decimal(reject.quantity) * reject.lot.rate for reject in rejects), ZERO)
            total_paid = sum((payment.amount for payment in payments), ZERO)
            total_work = total_work.quantize(Decimal("0.01"))
            total_due = (total_work - reject_total - total_paid).quantize(Decimal("0.01"))
            rows.append({
                "id": operator.pk,
                "name": operator.name,
                "total_products": total_products,
                "rejected_products": rejected_products,
                "total_work_amount": total_work,
                "total_paid": total_paid.quantize(Decimal("0.01")),
                "total_due": total_due,
            })

        return Response({
            "summary": {
                "total_products_sewn": sum(row["total_products"] for row in rows),
                "total_sewing_cost": sum((row["total_work_amount"] for row in rows), ZERO).quantize(Decimal("0.01")),
                "total_payments_made": sum((row["total_paid"] for row in rows), ZERO).quantize(Decimal("0.01")),
                "total_outstanding_due": sum((row["total_due"] for row in rows), ZERO).quantize(Decimal("0.01")),
            },
            "operators": rows,
        })


class AdminOnlyViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can access Swing Management.")


class SwingOperatorViewSet(AdminOnlyViewSet):
    queryset = SwingOperator.objects.all()
    serializer_class = SwingOperatorSerializer
    search_fields = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        active = self.request.query_params.get("is_active")
        if active in ("true", "1"):
            queryset = queryset.filter(is_active=True)
        elif active in ("false", "0"):
            queryset = queryset.filter(is_active=False)
        return queryset

    def perform_destroy(self, instance):
        with transaction.atomic():
            operator = SwingOperator.objects.select_for_update().get(pk=instance.pk)
            operator.is_active = False
            operator.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["get"])
    def statement(self, request, pk=None):
        operator = self.get_object()
        lots = list(operator.lots.filter(is_active=True).order_by("lot_date", "id"))
        lot_ids = [lot.pk for lot in lots]
        rejects = list(
            SwingReject.objects.filter(lot_id__in=lot_ids, lot__is_active=True, is_active=True)
            .select_related("lot")
            .order_by("reject_date", "id")
        )
        payments = list(operator.payments.filter(is_active=True).order_by("payment_date", "id"))

        events = []
        for lot in lots:
            gross = (Decimal(lot.quantity) * lot.rate).quantize(Decimal("0.01"))
            events.append({
                "event_type": "lot", "event_id": lot.pk, "event_date": lot.lot_date,
                "priority": 0, "lot": lot, "reject": None, "payment": None,
                "amount": gross,
            })
        for reject in rejects:
            amount = (Decimal(reject.quantity) * reject.lot.rate).quantize(Decimal("0.01"))
            events.append({
                "event_type": "reject", "event_id": reject.pk, "event_date": reject.reject_date,
                "priority": 1, "lot": reject.lot, "reject": reject, "payment": None,
                "amount": amount,
            })
        for payment in payments:
            events.append({
                "event_type": "payment", "event_id": payment.pk, "event_date": payment.payment_date,
                "priority": 2, "lot": None, "reject": None, "payment": payment,
                "amount": payment.amount,
            })
        events.sort(key=lambda event: (event["event_date"], event["priority"], event["event_id"]))

        balance = ZERO
        statement = []
        for event in events:
            brought_forward = balance
            lot = event["lot"]
            reject = event["reject"]
            payment = event["payment"]
            if event["event_type"] == "lot":
                balance += event["amount"]
            elif event["event_type"] == "reject":
                balance -= event["amount"]
            else:
                balance -= event["amount"]
            statement.append({
                "event_type": event["event_type"],
                "event_id": event["event_id"],
                "event_date": event["event_date"],
                "bf_taka": brought_forward,
                "colour": lot.fabric_specification if lot else "",
                "lot_id": lot.pk if lot else None,
                "lot_no": lot.lot_number if lot else "",
                "lot_qty": lot.quantity if lot else None,
                "lot_rate": lot.rate if lot else ZERO,
                "total_tk": event["amount"] if event["event_type"] == "lot" else ZERO,
                "reject_qty": reject.quantity if reject else 0,
                "reject_tk": event["amount"] if reject else ZERO,
                "receive_tk": payment.amount if payment else ZERO,
                "due_taka": balance,
                "remarks": (reject.remarks if reject else payment.remarks if payment else ""),
                "payment_id": payment.pk if payment else None,
                "reject_id": reject.pk if reject else None,
            })

        total_quantity = sum(lot.quantity for lot in lots)
        total_rejected = sum(reject.quantity for reject in rejects)
        total_gross = sum((Decimal(lot.quantity) * lot.rate for lot in lots), ZERO)
        total_reject_amount = sum((Decimal(reject.quantity) * reject.lot.rate for reject in rejects), ZERO)
        total_payments = sum((payment.amount for payment in payments), ZERO)
        lot_rows = []
        lot_balance = ZERO
        previous_lot_date = None
        for lot in lots:
            lot_rejects = [reject for reject in rejects if reject.lot_id == lot.pk]
            reject_qty = sum(reject.quantity for reject in lot_rejects)
            reject_amount = sum((Decimal(reject.quantity) * lot.rate for reject in lot_rejects), ZERO).quantize(Decimal("0.01"))
            lot_total = (Decimal(lot.quantity) * lot.rate).quantize(Decimal("0.01"))
            lot_payments = [
                payment for payment in payments
                if (previous_lot_date is None or payment.payment_date > previous_lot_date)
                and payment.payment_date <= lot.lot_date
            ]
            if lot == lots[-1]:
                lot_payments.extend(payment for payment in payments if payment.payment_date > lot.lot_date)
            receive_amount = sum((payment.amount for payment in lot_payments), ZERO).quantize(Decimal("0.01"))
            lot_brought_forward = lot_balance
            lot_due = (lot_brought_forward + lot_total - reject_amount - receive_amount).quantize(Decimal("0.01"))
            lot_rows.append({
                "lot_id": lot.pk,
                "event_date": lot.lot_date,
                "bf_taka": lot_brought_forward,
                "colour": lot.fabric_specification,
                "lot_no": lot.lot_number,
                "lot_qty": lot.quantity,
                "lot_rate": lot.rate,
                "total_tk": lot_total,
                "reject_qty": reject_qty,
                "reject_tk": reject_amount,
                "receive_tk": receive_amount,
                "due_taka": lot_due,
            })
            lot_balance = lot_due
            previous_lot_date = lot.lot_date
        return Response({
            "operator": SwingOperatorSerializer(operator).data,
            "summary": {
                "total_lots": len(lots),
                "total_products_assigned": total_quantity,
                "total_rejected_quantity": total_rejected,
                "total_accepted_quantity": total_quantity - total_rejected,
                "total_sewing_amount": total_gross.quantize(Decimal("0.01")),
                "net_sewing_amount": (total_gross - total_reject_amount).quantize(Decimal("0.01")),
                "total_payments_received": total_payments.quantize(Decimal("0.01")),
                "current_outstanding_balance": balance.quantize(Decimal("0.01")),
            },
            "statement": statement,
            "lot_rows": lot_rows,
            "lots": SwingLotSerializer(lots, many=True).data,
        })


class SwingLotViewSet(AdminOnlyViewSet):
    queryset = SwingLot.objects.select_related("operator").all()
    serializer_class = SwingLotSerializer
    filterset_fields = ["operator"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("include_inactive") not in ("true", "1"):
            queryset = queryset.filter(is_active=True)
        operator_id = self.request.query_params.get("operator")
        if operator_id:
            queryset = queryset.filter(operator_id=operator_id)
        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            operator = serializer.validated_data["operator"]
            SwingOperator.objects.select_for_update().get(pk=operator.pk)
            serializer.save()

    def perform_update(self, serializer):
        with transaction.atomic():
            lot = SwingLot.objects.select_for_update().get(pk=serializer.instance.pk)
            validate_lot_capacity(lot, serializer.validated_data.get("quantity", lot.quantity))
            serializer.save()

    def perform_destroy(self, instance):
        with transaction.atomic():
            lot = SwingLot.objects.select_for_update().get(pk=instance.pk)
            lot.is_active = False
            lot.save(update_fields=["is_active", "updated_at"])


class SwingPaymentViewSet(AdminOnlyViewSet):
    queryset = SwingPayment.objects.select_related("operator").all()
    serializer_class = SwingPaymentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("include_inactive") not in ("true", "1"):
            queryset = queryset.filter(is_active=True)
        operator_id = self.request.query_params.get("operator")
        if operator_id:
            queryset = queryset.filter(operator_id=operator_id)
        return queryset

    def perform_create(self, serializer):
        operator = serializer.validated_data["operator"]
        with transaction.atomic():
            locked_operator = SwingOperator.objects.select_for_update().get(pk=operator.pk)
            if not locked_operator.is_active:
                raise PermissionDenied("Payments can only be recorded for an active swing operator.")
            serializer.save()

    def perform_update(self, serializer):
        with transaction.atomic():
            SwingPayment.objects.select_for_update().get(pk=serializer.instance.pk)
            serializer.save()

    def perform_destroy(self, instance):
        with transaction.atomic():
            payment = SwingPayment.objects.select_for_update().get(pk=instance.pk)
            payment.is_active = False
            payment.save(update_fields=["is_active", "updated_at"])


class SwingRejectViewSet(AdminOnlyViewSet):
    queryset = SwingReject.objects.select_related("lot", "lot__operator").all()
    serializer_class = SwingRejectSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("include_inactive") not in ("true", "1"):
            queryset = queryset.filter(is_active=True)
        operator_id = self.request.query_params.get("operator")
        lot_id = self.request.query_params.get("lot")
        if operator_id:
            queryset = queryset.filter(lot__operator_id=operator_id)
        if lot_id:
            queryset = queryset.filter(lot_id=lot_id)
        return queryset

    def perform_create(self, serializer):
        lot = serializer.validated_data["lot"]
        with transaction.atomic():
            locked_lot = SwingLot.objects.select_for_update().get(pk=lot.pk, is_active=True)
            validate_reject_capacity(locked_lot, serializer.validated_data["quantity"])
            serializer.save()

    def perform_update(self, serializer):
        reject = serializer.instance
        lot = serializer.validated_data.get("lot", reject.lot)
        with transaction.atomic():
            locked_lot = SwingLot.objects.select_for_update().get(pk=lot.pk, is_active=True)
            validate_reject_capacity(
                locked_lot,
                serializer.validated_data.get("quantity", reject.quantity),
                exclude_id=reject.pk,
            )
            serializer.save()

    def perform_destroy(self, instance):
        with transaction.atomic():
            reject = SwingReject.objects.select_for_update().get(pk=instance.pk)
            reject.is_active = False
            reject.save(update_fields=["is_active", "updated_at"])
