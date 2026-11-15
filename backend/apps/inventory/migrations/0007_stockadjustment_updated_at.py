from django.db import migrations, models
from django.utils import timezone


def preserve_history_dates(apps, schema_editor):
    adjustment = apps.get_model("inventory", "StockAdjustment")
    adjustment.objects.using(schema_editor.connection.alias).update(updated_at=models.F("created_at"))


class Migration(migrations.Migration):
    dependencies = [("inventory", "0006_alter_dailybalance_card_sale_and_more")]
    operations = [
        migrations.AddField(
            model_name="stockadjustment", name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now), preserve_default=False,
        ),
        migrations.RunPython(preserve_history_dates, migrations.RunPython.noop),
        migrations.AlterModelOptions(name="stockadjustment", options={"ordering": ["-updated_at", "-id"]}),
    ]
