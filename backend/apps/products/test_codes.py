from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from .models import Product, ProductCategory


class ProductCodeTests(TestCase):
    def setUp(self):
        self.category = ProductCategory.objects.create(name="Coded products")

    def product(self, name="Sherwani", **fields):
        return Product.objects.create(name=name, category=self.category, selling_price=5000, **fields)

    def test_new_product_gets_persisted_code_automatically(self):
        product = self.product()
        self.assertEqual(product.code, f"MS-{product.pk:06d}")
        product.refresh_from_db()
        self.assertEqual(product.code, f"MS-{product.pk:06d}")
        other = self.product("Panjabi")
        self.assertNotEqual(product.code, other.code)

    def test_price_edit_keeps_product_code_stable(self):
        product = self.product()
        original = product.code
        product.selling_price = 4500
        product.save(update_fields=["selling_price"])
        product.refresh_from_db()
        self.assertEqual(product.code, original)

    def test_existing_custom_code_is_preserved(self):
        product = self.product(code="SHERWANI-RED-XL")
        self.assertEqual(product.code, "SHERWANI-RED-XL")

    def test_legacy_non_ascii_code_does_not_block_existing_product_edits(self):
        product = self.product(code="পুরোনো-কোড")
        client = APIClient()
        client.force_authenticate(User.objects.create_user("legacy-code-admin", role="admin"))
        response = client.patch(f"/api/products/{product.pk}/", {"code": product.code, "selling_price": "4500"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["code"], product.code)

    def test_auto_code_avoids_existing_custom_code_collision(self):
        existing = self.product("Existing", code="CUSTOM")
        existing.code = f"MS-{existing.pk + 1:06d}"
        existing.save(update_fields=["code"])
        product = self.product("New")
        self.assertNotEqual(product.code, existing.code)
        self.assertEqual(product.code, f"MS-{product.pk:06d}-1")

    def test_migration_fills_only_blank_codes_and_can_be_repeated(self):
        first = self.product("Blank")
        second = self.product("Whitespace")
        custom = self.product("Existing", code="LEGACY-123")
        Product.objects.filter(pk=first.pk).update(code="")
        Product.objects.filter(pk=second.pk).update(code="  ")
        populate = import_module("apps.products.migrations.0006_populate_product_codes").populate_codes
        populate(apps, SimpleNamespace(connection=connection))
        populate(apps, SimpleNamespace(connection=connection))
        first.refresh_from_db(); second.refresh_from_db(); custom.refresh_from_db()
        self.assertEqual(first.code, f"MS-{first.pk:06d}")
        self.assertEqual(second.code, f"MS-{second.pk:06d}")
        self.assertEqual(custom.code, "LEGACY-123")

    def test_admin_api_generates_code_and_rejects_duplicate_custom_code(self):
        client = APIClient()
        client.force_authenticate(User.objects.create_user("code-admin", role="admin"))
        response = client.post("/api/products/", {"name": "API product", "category": self.category.pk,
            "selling_price": "5000", "code": ""}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["code"], f"MS-{response.data['id']:06d}")
        duplicate = client.post("/api/products/", {"name": "Duplicate code", "category": self.category.pk,
            "selling_price": "5000", "code": response.data["code"]}, format="json")
        self.assertEqual(duplicate.status_code, 400)
