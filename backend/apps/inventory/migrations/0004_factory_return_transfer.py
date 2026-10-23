from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_alter_showroomstock_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailystock",
            name="returned_to_factory_qty",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="stocktransfer",
            name="transfer_type",
            field=models.CharField(
                choices=[
                    ("receive", "Receive from Factory"),
                    ("sale", "Sale to Customer"),
                    ("factory_return", "Return to Factory"),
                    ("return", "Return from Customer"),
                ],
                max_length=16,
            ),
        ),
    ]
