from django.db import migrations
from django.db.models.functions import Trim


def populate_codes(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    products = Product.objects.using(schema_editor.connection.alias)
    missing = products.annotate(trimmed_code=Trim("code")).filter(trimmed_code="")
    for pk in missing.values_list("pk", flat=True).iterator(chunk_size=500):
        base = f"MS-{pk:06d}"
        candidate, suffix = base, 1
        while products.exclude(pk=pk).filter(code__iexact=candidate).exists():
            candidate = f"{base}-{suffix}"
            suffix += 1
        products.filter(pk=pk).update(code=candidate)


class Migration(migrations.Migration):
    dependencies = [("products", "0005_product_description_product_image_url_and_more")]
    operations = [migrations.RunPython(populate_codes, migrations.RunPython.noop)]
