import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Employee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("employee_id", models.CharField(max_length=80, unique=True)),
                ("designation", models.CharField(max_length=120)),
                ("salary", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name", "employee_id"]},
        ),
        migrations.CreateModel(
            name="SalaryEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.DateField(help_text="First day of the salary month")),
                ("total_days", models.PositiveSmallIntegerField()),
                ("absent_days", models.PositiveSmallIntegerField(default=0)),
                ("overtime_hours", models.DecimalField(decimal_places=2, default=0, max_digits=8, validators=[django.core.validators.MinValueValidator(0)])),
                ("overtime_rate", models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("attendance_bonus", models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("base_salary", models.DecimalField(decimal_places=2, max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="salary_entries", to="employees.employee")),
            ],
            options={"ordering": ["employee__name"]},
        ),
        migrations.AddConstraint(
            model_name="salaryentry",
            constraint=models.UniqueConstraint(fields=("employee", "month"), name="unique_employee_salary_month"),
        ),
    ]
