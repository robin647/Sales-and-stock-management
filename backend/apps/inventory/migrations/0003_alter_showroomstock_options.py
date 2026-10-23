

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_factorystock_showroomstock_stockadjustment_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='showroomstock',
            options={'ordering': ['showroom_id', 'product_id']},
        ),
    ]
