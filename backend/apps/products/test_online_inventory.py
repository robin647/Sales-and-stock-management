from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import FactoryStock
from apps.shop.models import ShopSettings
from apps.shop.services import place_order, update_order
from .models import Product, ProductCategory


class OnlineInventoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user("inventory-admin", role="admin")
        self.customer = User.objects.create_user("online-customer", role="customer")
        self.category = ProductCategory.objects.create(name="Sherwani")
        self.main = Product.objects.create(name="Classic", category=self.category, selling_price=1000)
        self.main_stock = FactoryStock.objects.create(product=self.main, quantity=50)
        self.client.force_authenticate(self.admin)

    def online(self):
        response = self.client.post("/api/products/online/", {
            "name": "Classic", "category": self.category.pk, "selling_price": 1500,
            "discount_percentage": 20, "initial_stock": 7,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return Product.objects.get(pk=response.data["id"])

    def test_online_catalog_and_prices_are_independent(self):
        online = self.online()
        self.assertEqual(online.discount_price, Decimal("1200"))
        self.main.refresh_from_db()
        self.assertEqual(self.main.selling_price, Decimal("1000"))
        self.assertIsNone(self.main.discount_price)
        self.assertEqual(self.client.get("/api/products/").data["count"], 1)
        self.assertEqual(self.client.get("/api/inventory/factory-stocks/").data["count"], 1)
        self.client.force_authenticate(None)
        rows = self.client.get("/api/products/online/", {"storefront": "true"}).data["results"]
        self.assertEqual([p["id"] for p in rows], [online.pk])
        self.assertEqual(rows[0]["online_quantity"], 7)
        self.assertEqual(self.client.get(f"/api/products/{self.main.pk}/").status_code, 404)

    def test_add_from_main_copies_photo_with_new_online_price_and_stock(self):
        from .models import ProductPhoto
        ProductPhoto.objects.create(product=self.main, content=b"saved-main-photo")
        response = self.client.post("/api/products/online/", {
            "source_product": self.main.pk, "name": self.main.name, "category": self.category.pk,
            "selling_price": "2000", "discount_percentage": "15", "initial_stock": 4,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        online = Product.objects.get(pk=response.data["id"])
        self.assertEqual(online.discount_price, Decimal("1700"))
        self.assertEqual(bytes(online.stored_photo.content), b"saved-main-photo")
        self.assertEqual(response.data["online_quantity"], 4)
        self.assertNotEqual(online.code, self.main.code)
        self.main.refresh_from_db()
        self.main_stock.refresh_from_db()
        self.assertEqual(self.main.selling_price, Decimal("1000"))
        self.assertEqual(self.main_stock.quantity, 50)

    def test_main_source_cannot_be_used_in_main_creation_or_changed_on_edit(self):
        data = {"source_product": self.main.pk, "name": "Another", "category": self.category.pk, "selling_price": 2000}
        response = self.client.post("/api/products/", data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        online = self.online()
        response = self.client.patch(f"/api/products/online/{online.pk}/", {"source_product": self.main.pk}, format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_copy_creates_zero_stock_draft_without_changing_main(self):
        url = f"/api/products/{self.main.pk}/copy-to-online/"
        copied = self.client.post(url)
        self.assertEqual(copied.status_code, 201, copied.data)
        self.assertEqual(copied.data["online_quantity"], 0)
        self.assertFalse(copied.data["online_enabled"])
        self.assertNotEqual(copied.data["code"], self.main.code)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(Product.objects.filter(sales_channel="online").count(), 1)
        self.main_stock.refresh_from_db()
        self.assertEqual(self.main_stock.quantity, 50)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/products/online/").data["count"], 0)

    def test_online_adjustments_are_isolated_and_cannot_target_main(self):
        online = self.online()
        data = {"product": online.pk, "location": "factory", "new_quantity": 9, "reason": "Online replenishment"}
        self.assertEqual(self.client.post("/api/wholesale/stock-adjustments/", data, format="json").status_code, 400)
        response = self.client.post("/api/wholesale/online-stock-adjustments/", data, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.assertEqual(self.client.get("/api/wholesale/stock-adjustments/").data["count"], 0)
        self.assertEqual(self.client.patch(f"/api/wholesale/stock-adjustments/{pk}/", {"new_quantity": 3}, format="json").status_code, 404)
        self.assertEqual(self.client.patch(f"/api/wholesale/online-stock-adjustments/{pk}/", {"new_quantity": 8}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/wholesale/online-stock-adjustments/{pk}/").status_code, 204)
        self.assertEqual(FactoryStock.objects.get(product=online).quantity, 7)
        self.main_stock.refresh_from_db()
        self.assertEqual(self.main_stock.quantity, 50)
        data["product"] = self.main.pk
        self.assertEqual(self.client.post("/api/wholesale/online-stock-adjustments/", data, format="json").status_code, 400)

    def test_order_reserves_and_cancels_only_online_stock(self):
        online = self.online()
        ShopSettings.objects.create(pk=1, shipping_fee=0)
        order = place_order(self.customer, {
            "request_key": uuid4(), "recipient_name": "Buyer", "phone": "01712345678",
            "address": "House 1", "city": "Dhaka", "expected_total": Decimal("2400"),
            "expected_shipping_fee": Decimal("0"), "items": [{"product": online.pk, "quantity": 2}],
        })
        self.assertEqual(FactoryStock.objects.get(product=online).quantity, 5)
        self.main_stock.refresh_from_db()
        self.assertEqual(self.main_stock.quantity, 50)
        update_order(order.pk, {"status": "cancelled"}, customer=self.customer)
        self.assertEqual(FactoryStock.objects.get(product=online).quantity, 7)
        self.main_stock.refresh_from_db()
        self.assertEqual(self.main_stock.quantity, 50)

    def test_showroom_cannot_sell_online_inventory_or_manage_online_products(self):
        online = self.online()
        data = {"product": online.pk, "quantity": 1, "transfer_type": "sale", "date": "2026-11-15"}
        response = self.client.post("/api/inventory/transfers/", data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        user = User.objects.create_user("showroom-staff", role="showroom_user")
        self.client.force_authenticate(user)
        self.assertEqual(self.client.patch(f"/api/products/online/{online.pk}/", {"selling_price": 1}, format="json").status_code, 403)

    def test_checkout_rejects_main_stock_even_if_id_is_submitted_directly(self):
        from apps.shop.services import quote_order
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            quote_order([{"product": self.main.pk, "quantity": 1}])

    def test_wholesale_invoice_rejects_online_product(self):
        online = self.online()
        party = self.client.post("/api/wholesale/parties/", {"name": "Wholesale buyer"}, format="json")
        response = self.client.post("/api/wholesale/invoices/", {
            "party": party.data["id"], "invoice_number": "CH-001", "sale_date": "2026-11-15",
            "stock_location": "factory", "items": [{"product": online.pk, "quantity": 1, "unit_price": "100"}],
        }, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(FactoryStock.objects.get(product=online).quantity, 7)

    def test_customer_catalog_cannot_read_main_prices(self):
        online = self.online()
        self.client.force_authenticate(self.customer)
        rows = self.client.get("/api/products/").data["results"]
        self.assertEqual([row["id"] for row in rows], [online.pk])
        self.assertEqual(self.client.get(f"/api/products/{self.main.pk}/").status_code, 404)
