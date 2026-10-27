import csv
from datetime import date

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Employee, SalaryEntry
from .serializers import EmployeeSerializer, SalaryEntrySerializer


class AdminOnly:
    permission_classes = [permissions.IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can access employee management.")


class EmployeeViewSet(AdminOnly, viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    pagination_class = None


class SalaryEntryViewSet(AdminOnly, viewsets.ModelViewSet):
    queryset = SalaryEntry.objects.select_related("employee").all()
    serializer_class = SalaryEntrySerializer
    http_method_names = ["get", "patch", "head", "options"]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        month = self.request.query_params.get("month")
        if month:
            parsed = parse_date(f"{month}-01")
            if not parsed:
                raise ValidationError({"month": "Use YYYY-MM format."})
            queryset = queryset.filter(month=parsed)
        return queryset


class CreateSalarySheetView(AdminOnly, APIView):
    def post(self, request):
        month_value = request.data.get("month")
        month = parse_date(f"{month_value}-01") if month_value else None
        if not month:
            raise ValidationError({"month": "Select a valid month in YYYY-MM format."})
        total_days = SalaryEntry.days_in_month(month.year, month.month)
        employees = Employee.objects.all()
        for employee in employees:
            SalaryEntry.objects.get_or_create(
                employee=employee,
                month=month,
                defaults={"total_days": total_days, "base_salary": employee.salary},
            )
        entries = SalaryEntry.objects.filter(month=month).select_related("employee")
        return Response(SalaryEntrySerializer(entries, many=True).data)


class ExportSalarySheetView(AdminOnly, APIView):
    def get(self, request):
        month_value = request.query_params.get("month", "")
        month = parse_date(f"{month_value}-01") if month_value else None
        if not month:
            raise ValidationError({"month": "Select a valid month in YYYY-MM format."})
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = f'attachment; filename="salary-sheet-{month:%Y-%m}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Employee ID", "Name", "Designation", "Month", "Net Salary", "Perday Rate", "Absent", "Leave / Chuti", "Leave Ammount", "Absent Amount", "OT Hours", "OT Rete", "Hazira Bownous", "Loan", "Deduct", "Total Salary"])
        for entry in SalaryEntry.objects.filter(month=month).select_related("employee"):
            writer.writerow([entry.employee.employee_id, entry.employee.name, entry.employee.designation, month.strftime("%Y-%m"), entry.base_salary, entry.per_day_rate, entry.absent_days, entry.leave_days, entry.leave_amount, entry.absence_deduction, entry.overtime_hours, entry.overtime_rate, entry.attendance_bonus, entry.loan, entry.other_deduction, entry.net_salary])
        return response
