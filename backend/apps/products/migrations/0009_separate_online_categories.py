from django.db import migrations


def separate_categories(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    Category = apps.get_model("products", "ProductCategory")
    alias = schema_editor.connection.alias
    for product in Product.objects.using(alias).filter(sales_channel="online").select_related("category").iterator():
        if product.category.sales_channel != "online":
            category, _ = Category.objects.using(alias).get_or_create(name=product.category.name, sales_channel="online")
            Product.objects.using(alias).filter(pk=product.pk).update(category=category)


class Migration(migrations.Migration):
    dependencies = [("products", "0008_product_online_brand_product_online_vendor_and_more")]
    operations = [migrations.RunPython(separate_categories, migrations.RunPython.noop)]
