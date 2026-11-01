from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from .models import Employee, SalaryEntry


class EmployeeSerializer(serializers.ModelSerializer):
    nid_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Employee
        fields = ["id", "name", "employee_id", "nid_number", "designation", "salary", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_nid_number(self, value):
        return value.strip() or None if value is not None else None


class SalaryEntrySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee_name_snapshot", read_only=True)
    employee_id = serializers.CharField(source="employee_id_snapshot", read_only=True)
    designation = serializers.CharField(source="designation_snapshot", read_only=True)
    absence_deduction = serializers.DecimalField(source="absence_amount", max_digits=12, decimal_places=2, read_only=True)
    per_day_rate = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    overtime_pay = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_salary = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_deductions = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = SalaryEntry
        fields = [
            "id", "employee", "employee_name", "employee_id", "designation", "month", "total_days",
            "absent_days", "leave_days", "leave_amount", "absence_amount", "absence_deduction",
            "overtime_hours", "overtime_rate", "overtime_pay", "attendance_bonus", "advance_balance",
            "advance_deduction", "outstanding_loan", "loan", "other_deduction", "base_salary",
            "per_day_rate", "net_salary", "total_salary", "total_deductions",
        ]
        read_only_fields = ["id", "employee", "month", "total_days", "base_salary"]

    def validate(self, attrs):
        total = attrs.get("total_days", getattr(self.instance, "total_days", 0))
        absent = attrs.get("absent_days", getattr(self.instance, "absent_days", 0))
        leave = attrs.get("leave_days", getattr(self.instance, "leave_days", 0))
        if absent + leave > total:
            raise serializers.ValidationError({"absent_days": "Absent days and leave days together cannot exceed days in the month."})
        if self.instance and "absent_days" in attrs and "absence_amount" not in attrs:
            attrs["absence_amount"] = (
                self.instance.base_salary / self.instance.total_days * absent
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return attrs
