from decimal import Decimal
from io import BytesIO

from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdmin

from .models import CostSpecification, OtherCost, Producer, ProducerCost, ProducerPayment
from .serializers import (
    CostSpecificationSerializer,
    OtherCostSerializer,
    ProducerCostSerializer,
    ProducerPaymentSerializer,
    ProducerSerializer,
)


class ProducerViewSet(viewsets.ModelViewSet):
    queryset = Producer.objects.filter(is_active=True).all()
    serializer_class = ProducerSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(mobile_number__icontains=search))
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=False, url_path="dashboard-summary")
    def dashboard_summary(self, request):
        producer_total = ProducerCost.objects.filter(is_active=True).aggregate(total=Sum("total_cost"))["total"] or Decimal("0.00")
        other_total = OtherCost.objects.filter(is_active=True).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        return Response({
            "total_producer_cost": producer_total,
            "total_other_cost": other_total,
            "grand_total_cost": producer_total + other_total,
            "producer_count": Producer.objects.filter(is_active=True).count(),
        })

    @action(detail=True, url_path="ledger")
    def ledger(self, request, pk=None):
        producer = self.get_object()
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        cost_qs = producer.costs.filter(is_active=True)
        payment_qs = producer.payments.filter(is_active=True)
        if start_date:
            parsed_start = parse_date(start_date)
            if parsed_start:
                cost_qs = cost_qs.filter(transaction_date__gte=parsed_start)
                payment_qs = payment_qs.filter(payment_date__gte=parsed_start)
        if end_date:
            parsed_end = parse_date(end_date)
            if parsed_end:
                cost_qs = cost_qs.filter(transaction_date__lte=parsed_end)
                payment_qs = payment_qs.filter(payment_date__lte=parsed_end)

        total_cost = cost_qs.aggregate(total=Sum("total_cost"))["total"] or Decimal("0.00")
        total_payments = payment_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        opening_cost_before = producer.costs.filter(is_active=True)
        opening_payment_before = producer.payments.filter(is_active=True)
        if start_date:
            parsed_start = parse_date(start_date)
            if parsed_start:
                opening_cost_before = opening_cost_before.filter(transaction_date__lt=parsed_start)
                opening_payment_before = opening_payment_before.filter(payment_date__lt=parsed_start)
        opening_balance = (opening_cost_before.aggregate(total=Sum("total_cost"))["total"] or Decimal("0.00")) - (opening_payment_before.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"))

        entries = []
        for item in cost_qs.order_by("transaction_date", "id"):
            entries.append({
                "id": item.id,
                "action": "Producer Cost",
                "date": item.transaction_date,
                "transaction_type": "Producer Cost",
                "bale_no": item.bale_number,
                "product_specification": item.product_specification,
                "quantity": item.quantity,
                "rate": item.rate,
                "gst": item.gst_percentage,
                "debit": item.total_cost,
                "credit": Decimal("0.00"),
                "kind": "cost",
            })
        for item in payment_qs.order_by("payment_date", "id"):
            entries.append({
                "id": item.id,
                "action": "Payment",
                "date": item.payment_date,
                "transaction_type": "Payment",
                "bale_no": "",
                "product_specification": item.remarks or item.payment_method,
                "quantity": Decimal("0.00"),
                "rate": Decimal("0.00"),
                "gst": Decimal("0.00"),
                "debit": Decimal("0.00"),
                "credit": item.amount,
                "kind": "payment",
            })

        entries.sort(key=lambda entry: (entry["date"], entry["id"], entry["action"]))
        running_balance = opening_balance
        for entry in entries:
            if entry["kind"] == "cost":
                running_balance += entry["debit"]
            else:
                running_balance -= entry["credit"]
            entry["balance"] = running_balance

        closing_balance = opening_balance + total_cost - total_payments
        return Response({
            "producer": ProducerSerializer(producer).data,
            "summary": {
                "opening_balance": opening_balance,
                "total_product_quantity": cost_qs.aggregate(total=Sum("quantity"))["total"] or Decimal("0.00"),
                "total_producer_cost": total_cost,
                "total_payments": total_payments,
                "closing_balance": closing_balance,
            },
            "entries": entries,
        })


class ProducerCostViewSet(viewsets.ModelViewSet):
    queryset = ProducerCost.objects.filter(is_active=True).select_related("producer")
    serializer_class = ProducerCostSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(Q(producer__name__icontains=search) | Q(bale_number__icontains=search))
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            queryset = queryset.filter(transaction_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(transaction_date__lte=end_date)
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class ProducerPaymentViewSet(viewsets.ModelViewSet):
    queryset = ProducerPayment.objects.filter(is_active=True).select_related("producer")
    serializer_class = ProducerPaymentSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(Q(producer__name__icontains=search) | Q(remarks__icontains=search))
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            queryset = queryset.filter(payment_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(payment_date__lte=end_date)
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class OtherCostViewSet(viewsets.ModelViewSet):
    queryset = OtherCost.objects.filter(is_active=True).select_related("specification")
    serializer_class = OtherCostSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(Q(specification__name__icontains=search) | Q(notes__icontains=search))
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            queryset = queryset.filter(cost_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(cost_date__lte=end_date)
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class CostSpecificationViewSet(viewsets.ModelViewSet):
    queryset = CostSpecification.objects.filter(is_active=True)
    serializer_class = CostSpecificationSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class ProducerDashboardSummaryView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        producer_total = ProducerCost.objects.filter(is_active=True).aggregate(total=Sum("total_cost"))["total"] or Decimal("0.00")
        other_total = OtherCost.objects.filter(is_active=True).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        return Response({
            "total_producer_cost": producer_total,
            "total_other_cost": other_total,
            "grand_total_cost": producer_total + other_total,
            "producer_count": Producer.objects.filter(is_active=True).count(),
        })


class ProducerExcelExportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        producers = Producer.objects.filter(is_active=True).prefetch_related("costs", "payments")
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Producer Report"
        worksheet.merge_cells("A1:G1")
        worksheet["A1"] = "Producer Financial Summary"
        worksheet["A1"].font = Font(bold=True, size=14)
        worksheet["A1"].alignment = Alignment(horizontal="center")
        worksheet["A2"] = f"Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        headers = [
            "Producer Name",
            "Mobile Number",
            "Address",
            "Total Products",
            "Total Producer Cost",
            "Total Payment",
            "Outstanding Due",
        ]
        for column_index, header in enumerate(headers, start=1):
            cell = worksheet.cell(row=4, column=column_index, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
            cell.alignment = Alignment(horizontal="center")
            cell.border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))

        row_index = 5
        grand_total_products = Decimal("0.00")
        grand_total_cost = Decimal("0.00")
        grand_total_payment = Decimal("0.00")
        grand_total_due = Decimal("0.00")
        for producer in producers:
            total_products = producer.total_products.quantize(Decimal("0.01"))
            total_cost = producer.total_cost.quantize(Decimal("0.01"))
            total_payment = producer.total_payments.quantize(Decimal("0.01"))
            due = producer.outstanding_balance.quantize(Decimal("0.01"))
            grand_total_products += total_products
            grand_total_cost += total_cost
            grand_total_payment += total_payment
            grand_total_due += due
            row = [
                producer.name,
                producer.mobile_number,
                producer.address,
                total_products,
                total_cost,
                total_payment,
                due,
            ]
            for column_index, value in enumerate(row, start=1):
                cell = worksheet.cell(row=row_index, column=column_index, value=value)
                cell.border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
                if column_index in {4, 5, 6, 7}:
                    cell.number_format = '#,##0.00'
                if column_index == 2:
                    cell.alignment = Alignment(horizontal="left")
            row_index += 1

        summary_row = row_index + 1
        worksheet.cell(summary_row, 1, "Grand Total")
        worksheet.cell(summary_row, 4, grand_total_products)
        worksheet.cell(summary_row, 5, grand_total_cost)
        worksheet.cell(summary_row, 6, grand_total_payment)
        worksheet.cell(summary_row, 7, grand_total_due)
        for col in range(1, 8):
            cell = worksheet.cell(summary_row, col)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="2E7D32")
            cell.border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
            if col in {4, 5, 6, 7}:
                cell.number_format = '#,##0.00'

        for col in range(1, 8):
            worksheet.column_dimensions[chr(64 + col)].width = 18
        worksheet.column_dimensions["A"].width = 24
        worksheet.column_dimensions["C"].width = 30
        worksheet.column_dimensions["D"].width = 16

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        response = HttpResponse(output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="producer-financial-summary.xlsx"'
        return response
