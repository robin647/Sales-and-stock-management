from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("employees", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="salaryentry",
            name="leave_days",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="loan",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name="salaryentry",
            name="other_deduction",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
    ]
