from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP

from django.core.validators import MinValueValidator
from django.db import models


class Employee(models.Model):
    name = models.CharField(max_length=180)
    employee_id = models.CharField(max_length=80, unique=True)
    nid_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    designation = models.CharField(max_length=120)
    salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "employee_id"]

    def __str__(self):
        return f"{self.name} ({self.employee_id})"


class SalarySheet(models.Model):
    month = models.DateField(unique=True, help_text="First day of the salary month")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-month"]

    def __str__(self):
        return self.month.strftime("%B %Y")


class SalaryEntry(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="salary_entries")
    sheet = models.ForeignKey(SalarySheet, on_delete=models.CASCADE, related_name="entries")
    month = models.DateField(help_text="First day of the salary month")
    employee_name_snapshot = models.CharField(max_length=180)
    employee_id_snapshot = models.CharField(max_length=80)
    designation_snapshot = models.CharField(max_length=120)
    total_days = models.PositiveSmallIntegerField()
    absent_days = models.PositiveSmallIntegerField(default=0)
    leave_days = models.PositiveSmallIntegerField(default=0)
    leave_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    absence_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    overtime_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    attendance_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    advance_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    advance_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    outstanding_loan = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    loan = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    other_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["employee__name"]
        constraints = [models.UniqueConstraint(fields=["employee", "month"], name="unique_employee_salary_month")]

    @property
    def absence_deduction(self):
        return self.absence_amount

    @property
    def per_day_rate(self):
        return (self.base_salary / Decimal(self.total_days)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def overtime_pay(self):
        return (self.overtime_hours * self.overtime_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_deductions(self):
        return self.absence_amount + max(self.leave_amount, Decimal("0")) + self.advance_deduction + self.loan + self.other_deduction

    @property
    def net_salary(self):
        return (
            self.base_salary
            - self.absence_amount
            - self.leave_amount
            + self.overtime_pay
            + self.attendance_bonus
            - self.advance_deduction
            - self.loan
            - self.other_deduction
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_salary(self):
        return self.net_salary

    @staticmethod
    def days_in_month(year, month):
        return monthrange(year, month)[1]
