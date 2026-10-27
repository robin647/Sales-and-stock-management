from rest_framework import serializers

from .models import Employee, SalaryEntry


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ["id", "name", "employee_id", "designation", "salary", "created_at"]
        read_only_fields = ["id", "created_at"]


class SalaryEntrySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)
    employee_id = serializers.CharField(source="employee.employee_id", read_only=True)
    designation = serializers.CharField(source="employee.designation", read_only=True)
    absence_deduction = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    per_day_rate = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    leave_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    overtime_pay = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = SalaryEntry
        fields = ["id", "employee", "employee_name", "employee_id", "designation", "month", "total_days", "absent_days", "leave_days", "overtime_hours", "overtime_rate", "attendance_bonus", "loan", "other_deduction", "base_salary", "per_day_rate", "leave_amount", "absence_deduction", "overtime_pay", "net_salary"]
        read_only_fields = ["id", "month", "total_days", "base_salary"]

    def validate(self, attrs):
        total = attrs.get("total_days", getattr(self.instance, "total_days", 0))
        absent = attrs.get("absent_days", getattr(self.instance, "absent_days", 0))
        leave = attrs.get("leave_days", getattr(self.instance, "leave_days", 0))
        if absent + leave > total:
            raise serializers.ValidationError({"absent_days": "Absent days and leave days together cannot exceed days in the month."})
        return attrs
