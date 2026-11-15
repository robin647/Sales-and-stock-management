from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.products.models import Product, ProductCategory
from apps.inventory.models import FactoryStock, ShowroomStock, StockAdjustment
from apps.showrooms.models import Showroom
from apps.shop.models import Order, OrderItem, ShopSettings
from apps.shop.services import quote_order, place_order
from .models import Supplier, Purchase, ReturnRequest, Payment, TeamMember, AuditEvent, SupportTicket, ContentPage, Review, Locale


class EcommerceWorkflowTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.admin = User.objects.create_user("commerce-owner", role="admin")
        self.customer = User.objects.create_user("buyer", role="customer", email="buyer@example.com")
        self.other = User.objects.create_user("other-buyer", role="customer", email="other@example.com")
        self.category = ProductCategory.objects.create(name="Online collection", sales_channel="online")
        self.product = Product.objects.create(name="Online Sherwani", category=self.category, sales_channel="online", selling_price=1000)
        self.stock = FactoryStock.objects.create(product=self.product, quantity=8)
        category = ProductCategory.objects.create(name="Main collection")
        self.main = Product.objects.create(name="Main Sherwani", category=category, selling_price=600)
        self.main_stock = FactoryStock.objects.create(product=self.main, quantity=30)
        self.showroom = Showroom.objects.create(name="Showroom")
        self.showroom_stock = ShowroomStock.objects.create(showroom=self.showroom, product=self.main, quantity=12)
        self.order = Order.objects.create(customer=self.customer, request_key=uuid4(), recipient_name="Buyer",
            phone="01712345678", address="Dhaka", city="Dhaka", subtotal=2000, shipping_fee=120, total=2120, status="delivered")
        self.item = OrderItem.objects.create(order=self.order, product=self.product, product_name=self.product.name,
            quantity=2, unit_price=1000, line_total=2000)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def post(self, module, data):
        return self.client.post(f"/api/ecommerce/{module}/", data, format="json")

    def patch(self, module, pk, data):
        return self.client.patch(f"/api/ecommerce/{module}/{pk}/", data, format="json")

    def supplier(self):
        return Supplier.objects.create(name="Online supplier")

    def assert_main_unchanged(self):
        self.main_stock.refresh_from_db(); self.showroom_stock.refresh_from_db(); self.main.refresh_from_db()
        self.assertEqual(self.main_stock.quantity, 30)
        self.assertEqual(self.showroom_stock.quantity, 12)
        self.assertEqual(self.main.selling_price, Decimal("600"))

    def test_workspace_metadata_defaults_and_dashboard(self):
        response = self.client.get("/api/ecommerce/workspace/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("team", response.data["modules"])
        fields = response.data["modules"]["purchases"]["fields"]
        self.assertEqual(next(field for field in fields if field["name"] == "status")["default"], "draft")
        self.assertEqual(self.client.get("/api/ecommerce/dashboard/").status_code, 200)

    def test_purchase_receipt_is_once_only_and_main_data_survives(self):
        response = self.post("purchases", {"reference": "PO-1", "supplier": self.supplier().pk,
            "product": self.product.pk, "quantity": 5, "unit_cost": "500"})
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.assertEqual(self.patch("purchases", pk, {"status": "received"}).status_code, 200)
        self.assertEqual(self.patch("purchases", pk, {"status": "received"}).status_code, 400)
        self.stock.refresh_from_db(); self.assertEqual(self.stock.quantity, 13)
        self.assertEqual(StockAdjustment.objects.filter(product=self.product).count(), 1)
        self.assertEqual(self.client.delete(f"/api/ecommerce/purchases/{pk}/").status_code, 400)
        self.assert_main_unchanged()

    def test_purchase_cannot_use_main_product_or_skip_draft(self):
        supplier = self.supplier()
        data = {"reference": "PO-2", "supplier": supplier.pk, "product": self.main.pk, "quantity": 2, "unit_cost": "100"}
        self.assertEqual(self.post("purchases", data).status_code, 400)
        data.update(product=self.product.pk, status="received")
        self.assertEqual(self.post("purchases", data).status_code, 400)
        self.assertFalse(Purchase.objects.exists())
        self.assert_main_unchanged()

    def test_customer_return_request_approval_receive_and_restock(self):
        self.client.force_authenticate(self.customer)
        response = self.post("help", {"kind": "return", "item": self.item.pk, "quantity": 1, "reason": "Wrong fit", "status": "received"})
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.assertEqual(ReturnRequest.objects.get(pk=pk).status, "requested")
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.patch("returns", pk, {"status": "received"}).status_code, 400)
        self.assertEqual(self.patch("returns", pk, {"status": "approved"}).status_code, 200)
        self.assertEqual(self.patch("returns", pk, {"status": "received"}).status_code, 200)
        self.assertEqual(self.patch("returns", pk, {"status": "received"}).status_code, 400)
        self.stock.refresh_from_db(); self.assertEqual(self.stock.quantity, 9)
        self.assert_main_unchanged()

    def test_return_quantity_and_refund_bounds_and_ownership(self):
        self.assertEqual(self.post("returns", {"item": self.item.pk, "quantity": 3, "reason": "Fit"}).status_code, 400)
        self.assertEqual(self.post("returns", {"item": self.item.pk, "quantity": 1, "reason": "Fit", "refund_amount": "1001"}).status_code, 400)
        response = self.post("returns", {"item": self.item.pk, "quantity": 2, "reason": "Fit"})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.post("returns", {"item": self.item.pk, "quantity": 1, "reason": "Duplicate"}).status_code, 400)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.post("help", {"kind": "return", "item": self.item.pk, "quantity": 1, "reason": "Not mine"}).status_code, 400)

    def test_verified_payment_bounds_and_records_locked(self):
        data = {"order": str(self.order.pk), "reference": "COD-1", "amount": "2000", "purpose": "cod", "status": "verified"}
        response = self.post("payments", data)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.patch("payments", response.data["id"], {"amount": "100"}).status_code, 400)
        data.update(reference="COD-2", amount="1")
        self.assertEqual(self.post("payments", data).status_code, 400)
        data.update(reference="REFUND-1", amount="2001", purpose="refund")
        self.assertEqual(self.post("payments", data).status_code, 400)
        self.assertEqual(Payment.objects.count(), 1)

    def test_delivery_payment_verification_and_cod_before_delivery_rejected(self):
        self.order.status = "pending"; self.order.save()
        response = self.post("payments", {"order": str(self.order.pk), "reference": "SHIP-1", "amount": "120", "purpose": "delivery", "status": "verified"})
        self.assertEqual(response.status_code, 201, response.data)
        self.order.refresh_from_db(); self.assertEqual(self.order.delivery_payment_status, "verified")
        response = self.post("payments", {"order": str(self.order.pk), "reference": "EARLY-COD", "amount": "2000", "purpose": "cod", "status": "verified"})
        self.assertEqual(response.status_code, 400)

    def test_shipping_zone_changes_quote_and_checkout_consistently(self):
        response = self.post("shipping", {"name": "Inside Dhaka", "districts": "Dhaka, ঢাকা", "fee": "60"})
        self.assertEqual(response.status_code, 201, response.data)
        ShopSettings.objects.create(pk=1, shipping_fee=120, payment_number="01712345678")
        items = [{"product": self.product.pk, "quantity": 1}]
        self.assertEqual(quote_order(items, city=" dhaka ")["shipping_fee"], Decimal("60"))
        self.assertEqual(quote_order(items, city="Sylhet")["shipping_fee"], Decimal("120"))
        order = place_order(self.customer, {"request_key": uuid4(), "recipient_name": "Buyer", "phone": "01712345678",
            "address": "House 1", "city": "Dhaka", "delivery_payment_reference": "TX-SHIP", "items": items,
            "expected_total": Decimal("1060"), "expected_shipping_fee": Decimal("60")})
        self.assertEqual(order.shipping_fee, Decimal("60"))
        self.assert_main_unchanged()

    def test_public_content_only_published_and_active_campaigns(self):
        self.post("content", {"title": "Public policy", "slug": "policy", "body": "Policy text", "status": "published"})
        self.post("content", {"title": "Private draft", "slug": "draft", "body": "Private text"})
        self.post("campaigns", {"name": "Festive", "headline": "Season edit", "starts_at": (timezone.now() - timedelta(days=1)).isoformat(), "ends_at": (timezone.now() + timedelta(days=1)).isoformat(), "status": "active"})
        self.client.force_authenticate(None)
        response = self.client.get("/api/ecommerce/public/")
        self.assertEqual([row["slug"] for row in response.data["content"]], ["policy"])
        self.assertEqual(response.data["campaigns"][0]["headline"], "Season edit")
        self.assertEqual(self.client.get("/api/ecommerce/payments/").status_code, 401)

    def test_verified_purchase_review_moderation(self):
        self.client.force_authenticate(self.other)
        data = {"kind": "review", "product": self.product.pk, "rating": 5, "comment": "Great"}
        self.assertEqual(self.post("help", data).status_code, 400)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.post("help", data).status_code, 201)
        self.assertEqual(self.client.get("/api/ecommerce/public/").data["reviews"], [])
        self.client.force_authenticate(self.admin)
        review = Review.objects.get()
        self.assertEqual(self.patch("reviews", review.pk, {"status": "published"}).status_code, 200)
        self.assertEqual(len(self.client.get("/api/ecommerce/public/").data["reviews"]), 1)

    def test_support_request_cannot_impersonate_another_customer(self):
        self.client.force_authenticate(self.customer)
        response = self.post("help", {"kind": "support", "subject": "Delivery", "email": self.other.email, "message": "Help please", "status": "resolved", "reply": "Spoof"})
        self.assertEqual(response.status_code, 201, response.data)
        ticket = SupportTicket.objects.get()
        self.assertEqual(ticket.customer, self.customer)
        self.assertEqual(ticket.status, "open")
        self.assertEqual(ticket.reply, "")
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/ecommerce/help/").data["tickets"], [])

    def test_team_logins_are_scoped_and_do_not_grant_main_access(self):
        response = self.post("team", {"name": "Catalog operator", "username": "catalog-operator", "password": "UniqueCatalogPass#784", "access_role": "catalog"})
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username="catalog-operator")
        self.assertTrue(user.check_password("UniqueCatalogPass#784"))
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/ecommerce/brands/").status_code, 200)
        self.assertEqual(self.client.get("/api/ecommerce/payments/").status_code, 403)
        self.assertEqual(self.client.get("/api/ecommerce/team/").status_code, 403)
        self.assertEqual(self.client.get("/api/inventory/factory-stocks/").status_code, 403)
        response = self.client.post("/api/products/online/", {"name": "New online", "category": self.category.pk, "selling_price": 2000}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.client.patch(f"/api/products/{self.main.pk}/", {"selling_price": 1}, format="json").status_code, 403)
        TeamMember.objects.filter(user=user).update(is_active=False)
        self.client.force_authenticate(User.objects.get(pk=user.pk))
        self.assertEqual(self.client.get("/api/ecommerce/brands/").status_code, 403)

    def test_viewer_cannot_mutate_and_audit_cannot_be_modified(self):
        user = User.objects.create_user("read-only", role="ecommerce_staff")
        TeamMember.objects.create(user=user, name="Viewer", access_role="viewer")
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/ecommerce/dashboard/").status_code, 200)
        self.assertEqual(self.client.post("/api/products/online/", {}, format="json").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.post("brands", {"name": "Mahir"})
        event = AuditEvent.objects.filter(module="ecommerce").first()
        self.assertIsNotNone(event)
        self.assertEqual(self.patch("audit", event.pk, {"summary": "Changed"}).status_code, 405)
        self.assertNotIn("password", event.summary)

    def test_online_category_rename_does_not_change_main_category(self):
        main_category = self.main.category
        response = self.client.post("/api/products/online-categories/", {"name": main_category.name}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        response = self.client.patch(f"/api/products/online-categories/{response.data['id']}/", {"name": "Online renamed"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        main_category.refresh_from_db(); self.assertEqual(main_category.name, "Main collection")
        self.assert_main_unchanged()

    def test_locale_default_is_unique_and_bad_campaign_dates_rejected(self):
        response = self.post("locales", {"language_code": "fr", "language_name": "Français", "currency_code": "eur", "currency_symbol": "€", "exchange_rate": "0.008", "is_default": True})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Locale.objects.filter(is_default=True).count(), 1)
        self.assertEqual(Locale.objects.get(pk=response.data["id"]).currency_code, "EUR")
        now = timezone.now().isoformat()
        self.assertEqual(self.post("campaigns", {"name": "Invalid", "headline": "Test", "starts_at": now, "ends_at": now}).status_code, 400)

    def test_finance_and_support_roles_cannot_fulfil_orders(self):
        self.order.status = "confirmed"; self.order.delivery_payment_status = "verified"; self.order.save()
        for role in ("finance", "support"):
            user = User.objects.create_user("scoped-" + role, role="ecommerce_staff")
            TeamMember.objects.create(user=user, name=role, access_role=role)
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get("/api/shop/orders/").status_code, 200)
            self.assertEqual(self.client.patch(f"/api/shop/orders/{self.order.pk}/", {"status": "shipped"}, format="json").status_code, 403)
        self.order.refresh_from_db(); self.assertEqual(self.order.status, "confirmed")

    def test_suspended_vendor_products_are_not_sold(self):
        from .models import Vendor
        from rest_framework.exceptions import ValidationError
        vendor = Vendor.objects.create(name="Partner", status="active")
        self.product.online_vendor = vendor; self.product.save()
        vendor.status = "suspended"; vendor.save()
        self.client.force_authenticate(None)
        rows = self.client.get("/api/products/online/", {"storefront": "true"}).data["results"]
        self.assertNotIn(self.product.pk, [row["id"] for row in rows])
        with self.assertRaises(ValidationError):
            quote_order([{"product": self.product.pk, "quantity": 1}])

    def test_bdt_display_rate_cannot_diverge_from_settlement(self):
        response = self.post("locales", {"language_code": "test", "language_name": "Test", "currency_code": "BDT", "currency_symbol": "৳", "exchange_rate": "2"})
        self.assertEqual(response.status_code, 400, response.data)

    def test_category_data_migration_preserves_main_catalog_and_stock(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        self.product.category = self.main.category; self.product.save(update_fields=["category"])
        original_category = self.main.category_id
        migration = import_module("apps.products.migrations.0009_separate_online_categories")
        from types import SimpleNamespace
        migration.separate_categories(apps, SimpleNamespace(connection=connection))
        self.product.refresh_from_db(); self.main.refresh_from_db()
        self.assertEqual(self.main.category_id, original_category)
        self.assertNotEqual(self.product.category_id, original_category)
        self.assertEqual(self.product.category.sales_channel, "online")
        self.assert_main_unchanged()

    def test_customer_help_rejects_malformed_identifiers(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.post("help", {"kind": "return", "item": "invalid", "quantity": 1, "reason": "Test"}).status_code, 400)
        self.assertEqual(self.post("help", {"kind": "review", "product": "invalid", "rating": 5, "comment": "Test"}).status_code, 400)
        self.assertEqual(self.post("help", {"kind": "support", "order": "invalid", "subject": "Help", "message": "Test", "email": self.customer.email}).status_code, 400)
