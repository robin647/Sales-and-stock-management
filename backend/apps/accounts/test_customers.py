import uuid
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from apps.products.models import Product, ProductCategory
from apps.inventory.models import FactoryStock
from apps.shop.models import Order, OrderItem
from .models import User


class CustomerDirectoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user("directory-admin", role="admin")
        self.customer = User.objects.create_user("01700123456", first_name="Mahir", last_name="Customer",
            email="customer@gmail.com", phone_number="01700123456", role="customer", password="MahirPass#2026")
        self.other = User.objects.create_user("01700999999", role="customer", is_active=False)
        self.staff = User.objects.create_user("directory-staff", role="showroom_user")
        category = ProductCategory.objects.create(name="Directory test")
        self.product = Product.objects.create(name="Classic Sherwani", category=category, selling_price=1000)
        self.stock = FactoryStock.objects.create(product=self.product, quantity=9)
        self.delivered = self.make_order("delivered", 1000, 100)
        self.pending = self.make_order("pending", 200, 0)
        self.client.force_authenticate(self.admin)

    def make_order(self, status, subtotal, discount):
        order = Order.objects.create(customer=self.customer, request_key=uuid.uuid4(), recipient_name="Delivery Recipient",
            phone="01700123456", address="House 2, Road 3", city="Dhaka", subtotal=subtotal,
            coupon_discount=discount, shipping_fee=120, total=subtotal - discount + 120,
            delivery_payment_reference=uuid.uuid4().hex, status=status)
        OrderItem.objects.create(order=order, product=self.product, product_name=self.product.name,
            quantity=1, unit_price=subtotal, line_total=subtotal)
        return order

    def test_directory_lists_only_customers_and_correct_financial_totals(self):
        response = self.client.get("/api/accounts/customers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        customer = next(c for c in response.data["results"] if c["id"] == self.customer.pk)
        self.assertEqual(customer["name"], "Mahir Customer")
        self.assertEqual(customer["email"], "customer@gmail.com")
        self.assertEqual(customer["phone_number"], "01700123456")
        self.assertEqual(customer["order_count"], 2)
        self.assertEqual(customer["active_order_count"], 1)
        self.assertEqual(customer["delivered_count"], 1)
        self.assertEqual(Decimal(customer["delivered_spend"]), Decimal("900"))
        self.assertNotIn("password", customer)
        self.assertNotIn("user_permissions", customer)

    def test_search_and_filters(self):
        for search in ("Mahir Customer", "CUSTOMER@GMAIL.COM", "01700123456"):
            response = self.client.get("/api/accounts/customers/", {"search": search})
            self.assertEqual(response.data["count"], 1)
            self.assertEqual(response.data["results"][0]["id"], self.customer.pk)
        self.assertEqual(self.client.get("/api/accounts/customers/", {"status": "inactive"}).data["count"], 1)
        self.assertEqual(self.client.get("/api/accounts/customers/", {"has_orders": "true"}).data["count"], 1)

    def test_summary(self):
        self.assertEqual(self.client.get("/api/accounts/customers/summary/").data,
            {"total": 2, "active": 1, "inactive": 1, "with_orders": 1})

    def test_customer_order_history_is_paginated_and_contains_delivery_and_items(self):
        response = self.client.get(f"/api/accounts/customers/{self.customer.pk}/orders/", {"page_size": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertIsNotNone(response.data["next"])
        order = response.data["results"][0]
        self.assertEqual(order["address"], "House 2, Road 3")
        self.assertEqual(order["items"][0]["product_name"], "Classic Sherwani")
        self.assertIn("delivery_payment_reference", order)

    def test_customer_and_showroom_cannot_read_or_delete_customer_accounts(self):
        for user in (self.customer, self.staff):
            self.client.force_authenticate(user)
            for path in ("/api/accounts/customers/", "/api/accounts/customers/summary/",
                f"/api/accounts/customers/{self.customer.pk}/", f"/api/accounts/customers/{self.customer.pk}/orders/"):
                self.assertEqual(self.client.get(path).status_code, 403)
            self.assertEqual(self.client.delete(f"/api/accounts/customers/{self.customer.pk}/").status_code, 403)

    def test_anonymous_cannot_read_customer_directory(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/accounts/customers/").status_code, 401)

    def test_admin_and_showroom_accounts_cannot_be_deleted_from_customer_endpoint(self):
        for user in (self.admin, self.staff):
            self.assertEqual(self.client.delete(f"/api/accounts/customers/{user.pk}/").status_code, 404)
            self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_delete_account_preserves_orders_items_and_inventory(self):
        customer_id = self.customer.pk
        response = self.client.delete(f"/api/accounts/customers/{customer_id}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["preserved_orders"], 2)
        self.assertFalse(User.objects.filter(pk=customer_id).exists())
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(OrderItem.objects.count(), 2)
        self.pending.refresh_from_db()
        self.assertIsNone(self.pending.customer_id)
        self.assertEqual(self.pending.status, "pending")
        self.assertEqual(self.pending.recipient_name, "Delivery Recipient")
        self.assertEqual(self.pending.address, "House 2, Road 3")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 9)

    def test_delete_revokes_refresh_token_and_existing_access_token(self):
        token = RefreshToken.for_user(self.customer)
        access = str(token.access_token)
        token_id = OutstandingToken.objects.get(user=self.customer).pk
        self.assertEqual(self.client.delete(f"/api/accounts/customers/{self.customer.pk}/").status_code, 200)
        self.assertTrue(BlacklistedToken.objects.filter(token_id=token_id).exists())
        self.client.force_authenticate(None)
        response = self.client.post("/api/auth/refresh/", {"refresh": str(token)}, format="json")
        self.assertEqual(response.status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access)
        self.assertEqual(self.client.get("/api/accounts/me/").status_code, 401)

    def test_delete_customer_without_orders(self):
        response = self.client.delete(f"/api/accounts/customers/{self.other.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["preserved_orders"], 0)

    def test_deleted_account_orders_do_not_appear_for_new_account_with_same_phone(self):
        self.client.delete(f"/api/accounts/customers/{self.customer.pk}/")
        replacement = User.objects.create_user("01700123456", role="customer")
        self.client.force_authenticate(replacement)
        self.assertEqual(self.client.get("/api/shop/orders/").data["count"], 0)
