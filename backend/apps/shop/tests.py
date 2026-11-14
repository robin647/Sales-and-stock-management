import uuid
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.products.models import Product, ProductCategory
from apps.inventory.models import FactoryStock
from .models import Coupon, Order, ShopSettings
from unittest import skipUnless
from concurrent.futures import ThreadPoolExecutor
from django.db import connection, close_old_connections
from django.test import TransactionTestCase


class CheckoutTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.customer = User.objects.create_user("shopper", role="customer")
        self.admin = User.objects.create_user("shop-admin", role="admin")
        self.other = User.objects.create_user("other-shopper", role="customer")
        category = ProductCategory.objects.create(name="Sherwani")
        self.product = Product.objects.create(name="Wedding Sherwani", category=category,
            selling_price="5000", discount_price="4500")
        self.stock = FactoryStock.objects.create(product=self.product, quantity=10)
        self.settings = ShopSettings.objects.create(pk=1, shipping_fee="120", payment_number="01700000000")
        self.client.force_authenticate(self.customer)

    def payload(self, **changes):
        payload = {"request_key": str(uuid.uuid4()), "recipient_name": "A Customer", "phone": "01712345678",
            "address": "House 1, Road 2", "city": "Dhaka", "delivery_payment_reference": "TX-12345",
            "expected_total": "9120.00", "expected_shipping_fee": "120.00",
            "items": [{"product": self.product.pk, "quantity": 2}]}
        payload.update(changes)
        return payload

    def place(self, payload=None):
        response = self.client.post("/api/shop/orders/", payload or self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def test_checkout_snapshots_prices_and_reserves_factory_stock(self):
        response = self.place()
        self.assertEqual(Decimal(response.data["cod_amount"]), Decimal("9000"))
        self.assertEqual(Decimal(response.data["total"]), Decimal("9120"))
        self.assertEqual(response.data["delivery_payment_status"], "submitted")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)
        self.product.selling_price = 6000
        self.product.save()
        self.assertEqual(Order.objects.first().items.first().unit_price, Decimal("4500"))

    def test_repeated_request_is_idempotent(self):
        data = self.payload()
        first, second = self.place(data), self.place(data)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Order.objects.count(), 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)

    def test_missing_advance_payment_reference_rejects_without_stock_change(self):
        response = self.client.post("/api/shop/orders/", self.payload(delivery_payment_reference=""), format="json")
        self.assertEqual(response.status_code, 400)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)
        self.assertFalse(Order.objects.exists())

    def test_insufficient_stock_rejects_without_partial_order(self):
        response = self.client.post("/api/shop/orders/", self.payload(items=[{"product": self.product.pk, "quantity": 11}]), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_quote_checks_stock_before_customer_pays_delivery_charge(self):
        response = self.client.post("/api/shop/orders/quote/", {"items": [{"product": self.product.pk, "quantity": 11}]}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_duplicate_product_lines_rejected(self):
        response = self.client.post("/api/shop/orders/", self.payload(items=[{"product": self.product.pk, "quantity": 1}] * 2), format="json")
        self.assertEqual(response.status_code, 400)

    def test_delivery_transaction_cannot_be_used_for_another_order(self):
        self.place()
        response = self.client.post("/api/shop/orders/", self.payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)

    def test_price_tampering_rejected(self):
        response = self.client.post("/api/shop/orders/", self.payload(expected_total="1.00"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_changed_delivery_fee_rejected(self):
        response = self.client.post("/api/shop/orders/", self.payload(expected_shipping_fee="1.00"), format="json")
        self.assertEqual(response.status_code, 400)

    def test_confirmation_requires_verified_advance_payment(self):
        order = self.place().data
        self.client.force_authenticate(self.admin)
        url = f"/api/shop/orders/{order['id']}/"
        response = self.client.patch(url, {"status": "confirmed"}, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(url, {"status": "confirmed", "delivery_payment_status": "verified"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "confirmed")

    def test_customer_cannot_verify_own_payment(self):
        order = self.place().data
        response = self.client.patch(f"/api/shop/orders/{order['id']}/", {"delivery_payment_status": "verified"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_cancellation_restores_stock_once(self):
        order = self.place().data
        url = f"/api/shop/orders/{order['id']}/cancel/"
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 400)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)

    def test_other_customer_cannot_view_or_cancel_order(self):
        order = self.place().data
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/shop/orders/{order['id']}/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/shop/orders/{order['id']}/cancel/").status_code, 404)
        self.assertEqual(self.client.get("/api/shop/orders/").data["count"], 0)

    def test_admin_notes_are_private(self):
        order = self.place().data
        Order.objects.filter(pk=order["id"]).update(admin_notes="Private operations note")
        response = self.client.get(f"/api/shop/orders/{order['id']}/")
        self.assertNotIn("admin_notes", response.data)

    def test_coupon_quote_and_checkout_use_same_amount(self):
        Coupon.objects.create(code="FESTIVE", kind="percent", value="10", usage_limit=1)
        payload = self.payload(coupon="festive", expected_total="8220.00")
        quote = self.client.post("/api/shop/orders/quote/", {"items": payload["items"], "coupon": "FESTIVE"}, format="json")
        self.assertEqual(Decimal(str(quote.data["total"])), Decimal("8220"))
        order = self.place(payload)
        self.assertEqual(Decimal(order.data["coupon_discount"]), Decimal("900"))
        self.assertEqual(Coupon.objects.get().used_count, 1)
        response = self.client.post("/api/shop/orders/", self.payload(coupon="FESTIVE", expected_total="8220", delivery_payment_reference="TX-SECOND"), format="json")
        self.assertEqual(response.status_code, 400)

    def test_shipped_order_cannot_be_cancelled_and_delivered_is_terminal(self):
        order = self.place().data
        self.client.force_authenticate(self.admin)
        url = f"/api/shop/orders/{order['id']}/"
        for status in ("confirmed", "shipped"):
            response = self.client.patch(url, {"status": status, "delivery_payment_status": "verified"}, format="json")
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post(url + "cancel/").status_code, 400)
        self.assertEqual(self.client.patch(url, {"status": "delivered"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(url, {"status": "pending"}, format="json").status_code, 400)

    def test_customer_cannot_change_settings_or_manage_coupons(self):
        self.assertEqual(self.client.patch("/api/shop/settings/", {"shipping_fee": 0}).status_code, 403)
        self.assertEqual(self.client.get("/api/shop/coupons/").status_code, 403)

    def test_showroom_user_cannot_access_online_orders(self):
        showroom_user = User.objects.create_user("showroom-only", role="showroom_user")
        self.client.force_authenticate(showroom_user)
        self.assertEqual(self.client.get("/api/shop/orders/").status_code, 403)

    def test_delivery_summary_only_counts_delivered_product_revenue(self):
        order = self.place().data
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/shop/orders/summary/").data["delivered_sales"], 0)
        Order.objects.filter(pk=order["id"]).update(status="delivered")
        self.assertEqual(self.client.get("/api/shop/orders/summary/").data["delivered_sales"], Decimal("9000"))


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locking")
class ConcurrentCheckoutTests(TransactionTestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.customers = [User.objects.create_user(f"concurrent-{n}", role="customer") for n in range(2)]
        category = ProductCategory.objects.create(name="Limited collection")
        self.product = Product.objects.create(name="Last piece", category=category, selling_price=100)
        self.stock = FactoryStock.objects.create(product=self.product, quantity=1)
        ShopSettings.objects.create(pk=1, shipping_fee=0)

    def submit(self, customer, key):
        close_old_connections()
        try:
            client = APIClient()
            client.force_authenticate(customer)
            return client.post("/api/shop/orders/", {"request_key": str(key), "recipient_name": "Customer",
                "phone": "01712345678", "address": "Dhaka", "city": "Dhaka", "expected_total": "100",
                "expected_shipping_fee": "0", "items": [{"product": self.product.pk, "quantity": 1}]}, format="json").status_code
        finally:
            close_old_connections()

    def test_two_customers_cannot_buy_the_same_last_piece(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(self.submit, customer, uuid.uuid4()) for customer in self.customers]
            self.assertEqual(sorted(f.result() for f in futures), [201, 400])
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 0)
        self.assertEqual(Order.objects.count(), 1)

    def test_concurrent_retries_create_only_one_order(self):
        key = uuid.uuid4()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(self.submit, self.customers[0], key) for _ in range(2)]
            self.assertEqual([f.result() for f in futures], [201, 201])
        self.assertEqual(Order.objects.count(), 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 0)
