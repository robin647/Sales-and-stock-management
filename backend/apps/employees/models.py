from calendar import monthrange
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Employee(models.Model):
    name = models.CharField(max_length=180)
    employee_id = models.CharField(max_length=80, unique=True)
    designation = models.CharField(max_length=120)
    salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "employee_id"]

    def __str__(self):
        return f"{self.name} ({self.employee_id})"


class SalaryEntry(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="salary_entries")
    month = models.DateField(help_text="First day of the salary month")
    total_days = models.PositiveSmallIntegerField()
    absent_days = models.PositiveSmallIntegerField(default=0)
    leave_days = models.PositiveSmallIntegerField(default=0)
    overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    overtime_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    attendance_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
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
        return (self.base_salary / Decimal(self.total_days) * self.absent_days).quantize(Decimal("0.01"))

    @property
    def per_day_rate(self):
        return (self.base_salary / Decimal(self.total_days)).quantize(Decimal("0.01"))

    @property
    def leave_amount(self):
        return (self.per_day_rate * self.leave_days).quantize(Decimal("0.01"))

    @property
    def overtime_pay(self):
        return self.overtime_hours * self.overtime_rate

    @property
    def net_salary(self):
        return self.base_salary - self.absence_deduction + self.leave_amount + self.overtime_pay + self.attendance_bonus - self.loan - self.other_deduction

    @staticmethod
    def days_in_month(year, month):
        return monthrange(year, month)[1]
