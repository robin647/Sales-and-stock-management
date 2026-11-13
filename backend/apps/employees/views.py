from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from rest_framework import permissions, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from core.permissions import IsStaffUser

from .models import Employee, SalaryEntry, SalarySheet
from .serializers import EmployeeSerializer, SalaryEntrySerializer

MONEY = Decimal("0.01")


def parse_month(value):
    if not isinstance(value, str) or len(value) != 7:
        return None
    parsed = parse_date(f"{value}-01")
    return parsed if parsed and parsed.day == 1 else None


def create_salary_entries(sheet):
    total_days = monthrange(sheet.month.year, sheet.month.month)[1]
    employees = Employee.objects.filter(is_active=True)
    existing_ids = set(sheet.entries.values_list("employee_id", flat=True))
    entries = []
    for employee in employees:
        if employee.pk in existing_ids:
            continue
        entries.append(SalaryEntry(
            employee=employee,
            sheet_id=sheet.pk,
            month=sheet.month,
            employee_name_snapshot=employee.name,
            employee_id_snapshot=employee.employee_id,
            designation_snapshot=employee.designation,
            total_days=total_days,
            base_salary=employee.salary,
            absence_amount=Decimal("0.00"),
        ))
    for entry in entries:
        entry.save(force_insert=True)
    return len(entries)


class AdminOnly:
    permission_classes = [IsStaffUser]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can access employee management.")


class EmployeeViewSet(AdminOnly, viewsets.ModelViewSet):
    queryset = Employee.objects.filter(is_active=True)
    serializer_class = EmployeeSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(employee_id__icontains=search)
                | Q(nid_number__icontains=search)
            )
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class SalaryEntryViewSet(AdminOnly, viewsets.ModelViewSet):
    queryset = SalaryEntry.objects.select_related("employee", "sheet").all()
    serializer_class = SalaryEntrySerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        month = self.request.query_params.get("month")
        if month:
            parsed = parse_month(month)
            if not parsed:
                raise ValidationError({"month": "Use YYYY-MM format."})
            queryset = queryset.filter(sheet__month=parsed)
        return queryset


class SalarySheetHistoryView(AdminOnly, APIView):
    def get(self, request):
        sheets = SalarySheet.objects.annotate(entry_count=Count("entries")).order_by("-month")
        return Response([
            {
                "id": sheet.id,
                "month": sheet.month.strftime("%Y-%m"),
                "entry_count": sheet.entry_count,
                "created_at": sheet.created_at,
                "updated_at": sheet.updated_at,
            }
            for sheet in sheets
        ])


class CreateSalarySheetView(AdminOnly, APIView):
    def post(self, request):
        month_value = request.data.get("month")
        month = parse_month(month_value)
        if not month:
            raise ValidationError({"month": "Select a valid month in YYYY-MM format."})

        if not SalarySheet.objects.filter(month=month).exists() and not Employee.objects.filter(is_active=True).exists():
            raise ValidationError({"employees": "No active employees exist. Add an active employee before creating a salary sheet."})

        with transaction.atomic():
            sheet, sheet_created = SalarySheet.objects.get_or_create(month=month)
            entries_created = create_salary_entries(sheet)
            if not sheet.entries.exists():
                raise ValidationError({"employees": "No active employees are available to populate this salary sheet."})

        entries = sheet.entries.select_related("employee").all()
        status_code = 201 if sheet_created or entries_created else 200
        return Response(SalaryEntrySerializer(entries, many=True).data, status=status_code)


class OpenSalarySheetView(AdminOnly, APIView):
    def get(self, request):
        month_value = request.query_params.get("month", "")
        month = parse_month(month_value)
        if not month:
            raise ValidationError({"month": "Select a valid month in YYYY-MM format."})

        try:
            sheet = SalarySheet.objects.get(month=month)
        except SalarySheet.DoesNotExist as exc:
            raise NotFound("No salary sheet exists for this month. Create one to begin.") from exc

        entries = sheet.entries.select_related("employee").all()
        return Response(SalaryEntrySerializer(entries, many=True).data)


class ExportSalarySheetView(AdminOnly, APIView):
    def get(self, request):
        month_value = request.query_params.get("month", "")
        month = parse_month(month_value)
        if not month:
            raise ValidationError({"month": "Select a valid month in YYYY-MM format."})
        sheet = SalarySheet.objects.filter(month=month).first()
        if not sheet:
            raise ValidationError({"month": "No salary sheet exists for this month."})

        entries = list(sheet.entries.select_related("employee").order_by("employee_name_snapshot", "employee_id_snapshot"))
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = month.strftime("%b %Y")[:31]
        worksheet.merge_cells("A1:S1")
        worksheet["A1"] = f"Monthly Salary Sheet - {month.strftime('%B %Y')}"
        worksheet["A1"].font = Font(bold=True, size=16, color="FFFFFF")
        worksheet["A1"].fill = PatternFill("solid", fgColor="047857")
        worksheet["A1"].alignment = Alignment(horizontal="center")

        headers = [
            "Employee ID", "Employee Name", "Designation", "Basic Salary", "Per Day Rate",
            "Absent Days", "Leave Days", "Leave Adjustment", "Absent Amount", "OT Hours",
            "OT Rate", "OT Amount", "Hazira Bonus", "Advance Balance", "Advance Deduction",
            "Outstanding Loan", "Loan Deduction", "Additional Deduction", "Total Salary",
        ]
        worksheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
        worksheet.cell(2, 1, f"Month: {month.strftime('%B %Y')}")
        worksheet.cell(2, 1).font = Font(italic=True, color="475569")
        header_row = 4
        for column, heading in enumerate(headers, 1):
            cell = worksheet.cell(header_row, column, heading)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="334155")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        currency_columns = {4, 5, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19}
        thin_gray = Side(style="thin", color="CBD5E1")
        for row_number, entry in enumerate(entries, header_row + 1):
            row = [
                entry.employee_id_snapshot,
                entry.employee_name_snapshot,
                entry.designation_snapshot,
                entry.base_salary,
                entry.per_day_rate,
                entry.absent_days,
                entry.leave_days,
                entry.leave_amount,
                entry.absence_amount,
                entry.overtime_hours,
                entry.overtime_rate,
                entry.overtime_pay,
                entry.attendance_bonus,
                entry.advance_balance,
                entry.advance_deduction,
                entry.outstanding_loan,
                entry.loan,
                entry.other_deduction,
                entry.total_salary,
            ]
            for column, value in enumerate(row, 1):
                cell = worksheet.cell(row_number, column, float(value) if isinstance(value, Decimal) else value)
                cell.border = Border(bottom=thin_gray)
                cell.alignment = Alignment(vertical="center", horizontal="right" if column in currency_columns else "left")
                if column in currency_columns:
                    cell.number_format = '"৳" #,##0.00;[Red]("৳" #,##0.00)'

        total_row = header_row + len(entries) + 1
        sum_columns = {
            4: "base_salary",
            8: "leave_amount",
            9: "absence_amount",
            12: "overtime_pay",
            13: "attendance_bonus",
            15: "advance_deduction",
            17: "loan",
            18: "other_deduction",
            19: "total_salary",
        }
        worksheet.cell(total_row, 1, "TOTAL")
        for column, field in sum_columns.items():
            amount = sum((getattr(entry, field) for entry in entries), Decimal("0.00"))
            if field == "leave_amount":
                amount = sum((max(entry.leave_amount, Decimal("0.00")) for entry in entries), Decimal("0.00"))
            if field == "total_salary":
                amount = sum((entry.total_salary for entry in entries), Decimal("0.00"))
            cell = worksheet.cell(total_row, column, float(amount))
            cell.number_format = '"৳" #,##0.00;[Red]("৳" #,##0.00)'
        for cell in worksheet[total_row]:
            cell.font = Font(bold=True, color="064E3B")
            cell.fill = PatternFill("solid", fgColor="D1FAE5")
            cell.border = Border(top=Side(style="medium", color="047857"))

        summary_row = total_row + 2
        deductions_total = sum((entry.total_deductions for entry in entries), Decimal("0.00"))
        overtime_total = sum((entry.overtime_pay for entry in entries), Decimal("0.00"))
        bonuses_total = sum((entry.attendance_bonus + max(-entry.leave_amount, Decimal("0.00")) for entry in entries), Decimal("0.00"))
        payable_total = sum((entry.total_salary for entry in entries), Decimal("0.00"))
        for label_column, value_column, label, amount in [
            (1, 2, "Basic Salary", sum((entry.base_salary for entry in entries), Decimal("0.00"))),
            (4, 5, "Deductions", deductions_total),
            (7, 8, "Overtime", overtime_total),
            (10, 11, "Bonuses", bonuses_total),
            (13, 14, "Payable", payable_total),
        ]:
            worksheet.cell(summary_row, label_column, label)
            value_cell = worksheet.cell(summary_row, value_column, float(amount))
            value_cell.number_format = '"৳" #,##0.00;[Red]("৳" #,##0.00)'
        for cell in worksheet[summary_row]:
            cell.font = Font(bold=True, color="064E3B")
            cell.fill = PatternFill("solid", fgColor="D1FAE5")

        widths = [16, 24, 20, 17, 17, 13, 13, 18, 18, 13, 14, 15, 16, 18, 19, 18, 17, 20, 18]
        for column, width in enumerate(widths, 1):
            worksheet.column_dimensions[get_column_letter(column)].width = width
        worksheet.freeze_panes = "A5"
        worksheet.auto_filter.ref = f"A{header_row}:S{max(total_row - 1, header_row)}"
        worksheet.row_dimensions[header_row].height = 32

        output = BytesIO()
        workbook.save(output)
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="salary-sheet-{month:%Y-%m}.xlsx"'
        return response



