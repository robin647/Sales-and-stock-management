from django.urls import reverse
from rest_framework.test import APIClient

from django.test import TestCase
from .models import Product, ProductCategory


class PublicCatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = ProductCategory.objects.create(name="Panjabi")
        self.active_product = Product.objects.create(
            name="Festive Panjabi",
            category=self.category,
            selling_price="5000.00",
            discount_price="4200.00",
        )
        Product.objects.create(
            name="Archived Panjabi",
            category=self.category,
            selling_price="3500.00",
            is_active=False,
        )

    def test_anonymous_shoppers_only_see_active_products_and_offer_price(self):
        response = self.client.get(reverse("product-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.active_product.id)
        self.assertEqual(str(response.data["results"][0]["discount_price"]), "4200.00")

    def test_anonymous_shopper_cannot_create_products(self):
        response = self.client.post(reverse("product-list"), {}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_storefront_request_returns_paginated_products_with_images(self):
        self.active_product.image = "products/2026/11/panjabi.jpg"
        self.active_product.save(update_fields=["image"])

        response = self.client.get(
            reverse("product-list"),
            {"is_active": "true", "page_size": 100, "page": 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        product = response.data["results"][0]
        self.assertEqual(product["id"], self.active_product.id)
        self.assertEqual(product["category_name"], "Panjabi")
        self.assertTrue(product["image"].endswith("/media/products/2026/11/panjabi.jpg"))
        self.assertEqual(str(product["discount_price"]), "4200.00")

    def test_discount_price_must_be_less_than_regular_price(self):
        from apps.accounts.models import User

        admin = User.objects.create_user("catalog-admin", password="MahirPass#2026", role="admin")
        self.client.force_authenticate(admin)
        response = self.client.post(
            reverse("product-list"),
            {
                "name": "Invalid Offer",
                "category": self.category.id,
                "selling_price": "4000.00",
                "discount_price": "4000.00",
                "initial_stock": 0,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class CatalogManagementTests(TestCase):
    def setUp(self):
        from apps.accounts.models import User
        self.client = APIClient()
        self.admin = User.objects.create_user("product-manager", role="admin")
        self.client.force_authenticate(self.admin)
        self.category = ProductCategory.objects.create(name="Formal")

    def test_create_product_with_percentage_discount_and_initial_stock(self):
        from apps.inventory.models import FactoryStock
        response = self.client.post(reverse("product-list"), {"name": "Classic", "category": self.category.pk,
            "selling_price": "5000", "discount_percentage": "15", "initial_stock": 12}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(str(response.data["discount_price"]), "4250.00")
        self.assertEqual(FactoryStock.objects.get(product_id=response.data["id"]).quantity, 12)

    def test_edit_product_does_not_reset_inventory_and_can_remove_discount(self):
        from apps.inventory.models import FactoryStock
        product = Product.objects.create(name="Classic", category=self.category, selling_price=5000, discount_price=4000)
        FactoryStock.objects.create(product=product, quantity=9)
        response = self.client.patch(reverse("product-detail", args=[product.pk]), {"discount_price": None, "initial_stock": 0}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["discount_price"])
        self.assertEqual(FactoryStock.objects.get(product=product).quantity, 9)

    def test_photo_upload_persists_in_database_and_is_publicly_served(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import ProductPhoto
        buffer = BytesIO()
        Image.new("RGB", (30, 30), "green").save(buffer, "PNG")
        response = self.client.post(reverse("product-list"), {"name": "Photo product", "category": self.category.pk,
            "selling_price": "3000", "image": SimpleUploadedFile("photo.png", buffer.getvalue(), content_type="image/png")}, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(ProductPhoto.objects.count(), 1)
        self.assertIn("/photo/?v=", response.data["image"])
        self.client.force_authenticate(None)
        photo = self.client.get(reverse("product-photo", args=[response.data["id"]]))
        self.assertEqual(photo.status_code, 200)
        self.assertEqual(photo["Content-Type"], "image/webp")
        self.assertLess(len(photo.content), 250000)

    def test_storefront_visibility_does_not_hide_products_from_showroom_catalog(self):
        Product.objects.create(name="Offline only", category=self.category, selling_price=3000, online_enabled=False)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("product-list"), {"storefront": "true"}).data["count"], 0)
        self.assertEqual(self.client.get(reverse("product-list")).data["count"], 1)
