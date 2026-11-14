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
