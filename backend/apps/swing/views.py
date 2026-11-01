from decimal import Decimal

from django.db import transaction
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
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
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _dashboard_data():
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
        total_work = sum((Decimal(lot.quantity) * lot.rate for lot in lots), ZERO).quantize(Decimal("0.01"))
        reject_total = sum((Decimal(reject.quantity) * reject.lot.rate for reject in rejects), ZERO)
        total_paid = sum((payment.amount for payment in payments), ZERO).quantize(Decimal("0.01"))
        total_due = (total_work - reject_total - total_paid).quantize(Decimal("0.01"))
        rows.append({
            "id": operator.pk,
            "name": operator.name,
            "total_products": total_products,
            "rejected_products": rejected_products,
            "total_work_amount": total_work,
            "total_paid": total_paid,
            "total_due": total_due,
        })

    return {
        "summary": {
            "total_products_sewn": sum(row["total_products"] for row in rows),
            "total_sewing_cost": sum((row["total_work_amount"] for row in rows), ZERO).quantize(Decimal("0.01")),
            "total_payments_made": sum((row["total_paid"] for row in rows), ZERO).quantize(Decimal("0.01")),
            "total_outstanding_due": sum((row["total_due"] for row in rows), ZERO).quantize(Decimal("0.01")),
        },
        "operators": rows,
    }


def _build_lot_rows(lots, rejects, payments):
    rows = []
    lot_balance = ZERO
    previous_lot_date = None
    for lot_index, lot in enumerate(lots):
        lot_rejects = [reject for reject in rejects if reject.lot_id == lot.pk]
        reject_qty = sum(reject.quantity for reject in lot_rejects)
        reject_amount = sum((Decimal(reject.quantity) * lot.rate for reject in lot_rejects), ZERO).quantize(Decimal("0.01"))
        lot_total = (Decimal(lot.quantity) * lot.rate).quantize(Decimal("0.01"))
        lot_payments = [
            payment for payment in payments
            if (previous_lot_date is None or payment.payment_date > previous_lot_date)
            and payment.payment_date <= lot.lot_date
        ]
        if lot_index == len(lots) - 1:
            lot_payments.extend(payment for payment in payments if payment.payment_date > lot.lot_date)
        receive_amount = sum((payment.amount for payment in lot_payments), ZERO).quantize(Decimal("0.01"))
        brought_forward = lot_balance
        lot_balance = (brought_forward + lot_total - reject_amount - receive_amount).quantize(Decimal("0.01"))
        rows.append({
            "lot_id": lot.pk,
            "event_date": lot.lot_date,
            "bf_taka": brought_forward,
            "colour": lot.fabric_specification,
            "lot_no": lot.lot_number,
            "lot_qty": lot.quantity,
            "lot_rate": lot.rate,
            "total_tk": lot_total,
            "reject_qty": reject_qty,
            "reject_tk": reject_amount,
            "receive_tk": receive_amount,
            "due_taka": lot_balance,
        })
        previous_lot_date = lot.lot_date
    return rows


def _style_sheet(sheet, header_row=1):
    sheet.freeze_panes = f"A{header_row + 1}"
    for cell in sheet[header_row]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="176B52")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    sheet.auto_filter.ref = f"A{header_row}:{get_column_letter(sheet.max_column)}{sheet.max_row}"
    for column_index in range(1, sheet.max_column + 1):
        column_letter = get_column_letter(column_index)
        width = max((len(str(sheet.cell(row, column_index).value or "")) for row in range(1, sheet.max_row + 1)), default=0)
        sheet.column_dimensions[column_letter].width = min(max(width + 2, 12), 30)


class SwingOperatorsExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can export Swing Management data.")

    def get(self, request):
        data = _dashboard_data()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "All Operators"
        sheet.append(["Operator Name", "Total Products", "Rejected Products", "Total Work Amount", "Total Paid", "Total Due"])
        for row in data["operators"]:
            sheet.append([
                row["name"], row["total_products"], row["rejected_products"],
                row["total_work_amount"], row["total_paid"], row["total_due"],
            ])
        totals = data["summary"]
        sheet.append([
            "TOTAL", totals["total_products_sewn"],
            sum(row["rejected_products"] for row in data["operators"]),
            totals["total_sewing_cost"], totals["total_payments_made"], totals["total_outstanding_due"],
        ])
        _style_sheet(sheet)
        for cell in sheet[sheet.max_row]:
            cell.font = Font(bold=True, color="064E3B")
        for row in sheet.iter_rows(min_row=2, min_col=4, max_col=6):
            for cell in row:
                cell.number_format = '"৳" #,##0.00;[Red]("৳" #,##0.00)'
        response = HttpResponse(content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = 'attachment; filename="swing-all-operators.xlsx"'
        workbook.save(response)
        return response


class SwingOperatorStatementExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can export Swing Management data.")

    def get(self, request, operator_id):
        operator = SwingOperator.objects.filter(pk=operator_id).first()
        if not operator:
            from rest_framework.exceptions import NotFound

            raise NotFound("Swing operator not found.")

        lots = list(operator.lots.filter(is_active=True).order_by("lot_date", "id"))
        lot_ids = [lot.pk for lot in lots]
        rejects = list(SwingReject.objects.filter(
            lot_id__in=lot_ids, lot__is_active=True, is_active=True,
        ).select_related("lot").order_by("reject_date", "id"))
        payments = list(operator.payments.filter(is_active=True).order_by("payment_date", "id"))
        lot_rows = _build_lot_rows(lots, rejects, payments)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Lot Statement"
        sheet.merge_cells("A1:K1")
        sheet["A1"] = operator.name
        sheet["A1"].font = Font(bold=True, size=16, color="FFFFFF")
        sheet["A1"].fill = PatternFill("solid", fgColor="176B52")
        sheet["A1"].alignment = Alignment(horizontal="center")
        sheet.merge_cells("A2:K2")
        sheet["A2"] = "Swing Operator Lot Statement"
        sheet["A2"].font = Font(italic=True, color="475569")
        headers = ["Date", "B/F Taka", "Colour", "Lot No", "Lot QTY", "Lote Rate", "Total Tk", "Reject QTY", "Reject Tk", "Receive Tk", "Due Taka"]
        sheet.append([])
        sheet.append(headers)
        for row in lot_rows:
            sheet.append([
                row["event_date"], row["bf_taka"], row["colour"], row["lot_no"], row["lot_qty"],
                row["lot_rate"], row["total_tk"], row["reject_qty"], row["reject_tk"],
                row["receive_tk"], row["due_taka"],
            ])
        _style_sheet(sheet, header_row=4)
        for row in sheet.iter_rows(min_row=5, min_col=2, max_col=2):
            for cell in row:
                cell.number_format = '"৳" #,##0.00;[Red]("৳" #,##0.00)'
        for row in sheet.iter_rows(min_row=5, min_col=6, max_col=7):
            for cell in row:
                cell.number_format = '"৳" #,##0.00;[Red]("৳" #,##0.00)'
        for row in sheet.iter_rows(min_row=5, min_col=9, max_col=11):
            for cell in row:
                cell.number_format = '"৳" #,##0.00;[Red]("৳" #,##0.00)'
        response = HttpResponse(content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="swing-operator-{operator.pk}-statement.xlsx"'
        workbook.save(response)
        return response


class SwingDashboardSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can access Swing Management.")

    def get(self, request):
        return Response(_dashboard_data())


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
        lot_rows = _build_lot_rows(lots, rejects, payments)
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
