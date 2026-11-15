from django.db import migrations


def languages(apps, schema_editor):
    Locale = apps.get_model("ecommerce", "Locale")
    alias = schema_editor.connection.alias
    Locale.objects.using(alias).get_or_create(language_code="en", currency_code="BDT", defaults={"language_name": "English", "currency_symbol": "৳", "exchange_rate": 1, "is_default": True})
    Locale.objects.using(alias).get_or_create(language_code="bn", currency_code="BDT", defaults={"language_name": "বাংলা", "currency_symbol": "৳", "exchange_rate": 1})


class Migration(migrations.Migration):
    dependencies = [("ecommerce", "0001_initial")]
    operations = [migrations.RunPython(languages, migrations.RunPython.noop)]
