from decimal import Decimal, ROUND_HALF_UP

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


def ensure_employee_active_column(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    database = schema_editor.connection.alias
    columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(), Employee._meta.db_table
        )
    }
    if "is_active" not in columns:
        schema_editor.add_field(Employee, Employee._meta.get_field("is_active"))
        Employee.objects.using(database).all().update(is_active=True)


def link_existing_salary_entries(apps, schema_editor):
    SalarySheet = apps.get_model("employees", "SalarySheet")
    SalaryEntry = apps.get_model("employees", "SalaryEntry")
    database = schema_editor.connection.alias
    sheets = {}

    for entry in SalaryEntry.objects.using(database).select_related("employee").iterator():
        sheet = sheets.get(entry.month)
        if sheet is None:
            sheet, _ = SalarySheet.objects.using(database).get_or_create(month=entry.month)
            sheets[entry.month] = sheet

        per_day_rate = (entry.base_salary / Decimal(entry.total_days)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        entry.sheet_id = sheet.pk
        entry.employee_name_snapshot = entry.employee.name
        entry.employee_id_snapshot = entry.employee.employee_id
        entry.designation_snapshot = entry.employee.designation
        entry.absence_amount = (per_day_rate * entry.absent_days).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        # Prior versions treated leave days as paid leave; a negative adjustment
        # preserves that historical total under the new deduction convention.
        entry.leave_amount = -(per_day_rate * entry.leave_days).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        entry.save(
            using=database,
            update_fields=[
                "sheet",
                "employee_name_snapshot",
                "employee_id_snapshot",
                "designation_snapshot",
                "absence_amount",
                "leave_amount",
            ],
        )


class Migration(migrations.Migration):
    dependencies = [("employees", "0002_salaryentry_leave_loan_deductions")]

    operations = [
        migrations.RunPython(ensure_employee_active_column, migrations.RunPython.noop),
        migrations.CreateModel(
            name="SalarySheet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.DateField(help_text="First day of the salary month", unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-month"]},
        ),
        migrations.AddField(
            model_name="employee",
            name="nid_number",
            field=models.CharField(blank=True, max_length=30, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="employee_name_snapshot",
            field=models.CharField(default="", max_length=180),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="employee_id_snapshot",
            field=models.CharField(default="", max_length=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="designation_snapshot",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="leave_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="absence_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="advance_balance",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="advance_deduction",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="outstanding_loan",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="sheet",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="entries",
                to="employees.salarysheet",
            ),
        ),
        migrations.RunPython(link_existing_salary_entries, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="salaryentry",
            name="sheet",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="entries",
                to="employees.salarysheet",
            ),
        ),
    ]
