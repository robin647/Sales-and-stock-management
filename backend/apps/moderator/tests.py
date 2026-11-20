from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZipFile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from openpyxl import load_workbook
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import FactoryStock, StockAdjustment
from apps.products.models import Product, ProductCategory
from apps.shop.models import Order, ShopSettings

from .models import Asset, FacebookOrder


API = "/api/moderator/"


class WorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = uuid4().hex
        cls.admin = User.objects.create_user("staff-admin", password=cls.password, role=User.Role.ADMIN)
        cls.moderator = User.objects.create_user("staff-moderator", password=cls.password, role=User.Role.MODERATOR)
        cls.customer = User.objects.create_user("buyer", password=cls.password, role=User.Role.CUSTOMER)
        cls.category = ProductCategory.objects.create(name="Clothing", sales_channel="online")
        cls.live = Product.objects.create(
            name="Wedding Sherwani", code="BLACK-M", category=cls.category, sales_channel="online",
            color="Black", size="M", selling_price=100, discount_price=80,
        )
        cls.hidden = Product.objects.create(
            name=cls.live.name, code="BLACK-L", category=cls.category, sales_channel="online",
            color="Black", size="L", selling_price=100, is_active=False,
        )
        cls.white = Product.objects.create(
            name=cls.live.name, code="WHITE-L", category=cls.category, sales_channel="online",
            color="White", size="L", selling_price=100,
        )
        cls.main = Product.objects.create(name="Factory only", category=cls.category, selling_price=100)
        FactoryStock.objects.create(product=cls.live, quantity=5)

    def setUp(self):
        cache.clear()
        temp = self.enterContext(TemporaryDirectory())
        self.private = Path(temp) / "private"
        self.enterContext(self.settings(MEDIA_ROOT=Path(temp) / "public", MODERATOR_MEDIA_ROOT=self.private))
        self.client = APIClient()

    def login(self, user, password=None):
        browser = APIClient()
        login_url = "/api/auth/login/" if user.role == User.Role.ADMIN else API + "login/"
        reply = browser.post(login_url, {"username": user.username, "password": password or self.password})
        self.assertEqual(reply.status_code, 200, reply.data)
        browser.credentials(HTTP_AUTHORIZATION=f"Bearer {reply.data['access']}")
        return browser, reply.data

    @staticmethod
    def image(name="same.png"):
        file = BytesIO()
        Image.new("RGB", (8, 8), "green").save(file, "PNG")
        return SimpleUploadedFile(name, file.getvalue(), "image/png")

    def upload(self, product, kind="edited", file=None):
        response = self.client.post(API + "assets/", {
            "product": product.pk, "kind": kind, "file": file or self.image(),
        }, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_workspace_permissions_and_variant_filters(self):
        self.assertEqual(self.client.post(API + "login/", {
            "username": self.admin.username, "password": self.password,
        }).status_code, 401)
        for user, status in [(None, 401), (self.customer, 403)]:
            self.client.force_authenticate(user)
            for route in ["dashboard/", "products/", "categories/", "accounts/", "downloads/bulk/?preview=1"]:
                self.assertEqual(self.client.get(API + route).status_code, status, route)
            self.assertEqual(self.client.get(API + "assets/123/download/").status_code, status)
        moderator, _ = self.login(self.moderator)
        for route in ["products/", "categories/", "assets/", "accounts/"]:
            self.assertEqual(moderator.post(API + route, {}, format="json").status_code, 403, route)
        self.assertEqual(moderator.post("/api/auth/login/", {
            "username": self.moderator.username, "password": self.password,
        }).status_code, 401)
        self.assertEqual(moderator.get(API + "accounts/").status_code, 403)
        self.assertEqual(moderator.get(API + f"products/{self.hidden.pk}/").status_code, 404)
        self.assertEqual(moderator.get(API + f"products/{self.main.pk}/").status_code, 404)
        self.assertEqual(moderator.get(API + "products/", {"color": "black", "size": "L"}).data["count"], 0)
        listing = moderator.get(API + "products/", {
            "category": self.category.pk, "search": "black-m", "discount": "20.00", "stock": "low", "size": "M",
            "color": "Black", "ordering": "effective_price", "active": "false",
        })
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual([p["id"] for p in listing.data["results"]], [self.live.pk])
        detail = moderator.get(API + f"products/{self.live.pk}/")
        self.assertEqual([p["id"] for p in detail.data["variants"]], [self.white.pk])
        admin, _ = self.login(self.admin)
        inactive = admin.get(API + "products/", {"active": "false"})
        self.assertEqual([p["id"] for p in inactive.data["results"]], [self.hidden.pk])
        self.assertEqual(admin.get(API + "dashboard/").data["moderators"], 1)
        self.assertNotIn("moderators", moderator.get(API + "dashboard/").data)

    def test_facebook_orders_are_admin_only_and_totals_cover_every_page(self):
        url = API + "facebook-orders/"
        admin, _ = self.login(self.admin)
        moderator, _ = self.login(self.moderator)
        order = {
            "tracking_id": "120000001", "invoice": "8", "customer_name": "Sample Customer",
            "phone": "01000000000", "address": "Sample Road", "area": "Dhaka",
            "quantity": 2, "cod_amount": "2994.50", "delivery_zone": "inside",
        }
        self.assertEqual(moderator.get(url).status_code, 403)
        self.assertEqual(moderator.get(url + "export/").status_code, 403)
        self.assertEqual(moderator.post(url, order).status_code, 403)
        self.assertEqual(admin.post(url, {**order, "quantity": 0}).status_code, 400)
        first = admin.post(url, order)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["status"], "pending")
        self.assertEqual(first.data["delivery_charge"], 70)
        self.assertEqual(admin.post(url, order).status_code, 400)
        second = admin.post(url, {**order, "tracking_id": "120000002", "quantity": 3,
                                  "cod_amount": "450.25", "delivery_zone": "outside", "delivery_charge": 1})
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(second.data["delivery_charge"], 150)
        self.assertEqual(moderator.patch(f"{url}{first.data['id']}/", {"quantity": 6}).status_code, 403)
        first_url = f"{url}{first.data['id']}/"
        self.assertEqual(admin.patch(first_url, {"status": "delivered"}).status_code, 400)
        self.assertEqual(admin.patch(first_url, {
            "quantity": 1, "status": "delivered", "courier_charge": "80.00",
        }).status_code, 200)
        self.assertEqual(admin.patch(f"{url}{second.data['id']}/", {
            "status": "cancelled", "courier_charge": "110.00",
        }).status_code, 200)
        FacebookOrder.objects.filter(pk=second.data["id"]).update(created_at=timezone.now() - timedelta(days=10))
        listing = admin.get(url, {"page_size": 1})
        self.assertEqual(len(listing.data["results"]), 1)
        self.assertEqual(listing.data["summary"], {
            "orders": 2, "units": 1, "cod": "2994.50", "courier_charge": "190.00",
            "steadfast_fee": "29.15", "net_sales": "2775.35", "pending": 0, "cancelled": 1,
        })
        self.assertEqual(admin.get(url, {"period": "week"}).data["summary"]["orders"], 1)
        self.assertEqual(admin.get(url, {"period": "month"}).data["summary"]["orders"], 2)
        today = timezone.localdate().isoformat()
        params = {"period": "custom", "start_date": today, "end_date": today}
        response = admin.get(url + "export/", params)
        self.assertEqual(response.status_code, 200)
        sheet = load_workbook(BytesIO(response.content), read_only=True).active
        rows = list(sheet.values)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1], order["tracking_id"])
        self.assertEqual(rows[1][-4:], (70, 80, 29.15, 2885.35))
        self.assertEqual(admin.get(url + "export/", {**params, "end_date": "2000-01-01"}).status_code, 400)

    def test_steadfast_quote_validates_route_and_uses_official_delivery_amount(self):
        cache.clear()
        self.addCleanup(cache.clear)
        admin, _ = self.login(self.admin)
        url = API + "facebook-orders/steadfast-quote/"
        params = {"origin": 1, "destination": 15, "weight": "1.5", "delivery": "home"}
        with patch("apps.moderator.steadfast.urlopen") as fetch:
            fetch.return_value.__enter__.return_value.read.return_value = b'{"available":true,"charge":155}'
            self.assertEqual(admin.get(url, {**params, "weight": 0}).status_code, 400)
            response = admin.get(url, params)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["courier_charge"], "155.00")
            self.assertEqual(fetch.call_args.args[0].full_url,
                             "https://steadfast.com.bd/pricing/quote?from=1&to=15&weight=1.50&category=1&service=1&delivery=0")

    def test_admin_account_management_revokes_password_and_inactive_sessions(self):
        admin, _ = self.login(self.admin)
        password = uuid4().hex
        joined = admin.post(API + "accounts/", {
            "username": "new-staff", "password": password, "role": "admin", "is_superuser": True,
        })
        self.assertEqual(joined.status_code, 201, joined.data)
        account = User.objects.get(pk=joined.data["id"])
        self.assertEqual(account.role, User.Role.MODERATOR)
        self.assertFalse(account.is_superuser)
        self.assertNotIn("password", joined.data)
        self.assertEqual(admin.patch(API + f"accounts/{self.admin.pk}/", {"is_active": False}).status_code, 404)
        moderator, old = self.login(account, password)
        new_password = uuid4().hex
        updated = admin.patch(API + f"accounts/{account.pk}/", {
            "first_name": "Staff", "email": "staff@example.test", "password": new_password,
        })
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(moderator.get(API + "dashboard/").status_code, 401)
        self.assertEqual(moderator.post("/api/auth/refresh/", {"refresh": old["refresh"]}).status_code, 401)
        moderator, current = self.login(account, new_password)
        self.assertEqual(moderator.post(API + "logout/", {"refresh": current["refresh"]}).status_code, 204)
        self.assertEqual(moderator.get(API + "dashboard/").status_code, 401)
        self.assertEqual(moderator.post("/api/auth/refresh/", {"refresh": current["refresh"]}).status_code, 401)
        moderator, current = self.login(account, new_password)
        self.assertEqual(admin.patch(API + f"accounts/{account.pk}/", {"is_active": False}).status_code, 200)
        self.assertEqual(moderator.get(API + "dashboard/").status_code, 401)
        self.assertEqual(moderator.post("/api/auth/refresh/", {"refresh": current["refresh"]}).status_code, 401)

    def test_catalog_prices_and_stock_use_existing_checkout_records(self):
        admin, _ = self.login(self.admin)
        product = admin.post(API + "products/", {
            "name": self.live.name, "code": "GOLD-M", "category": self.category.pk,
            "color": "Gold", "size": "M", "selling_price": "100.00", "discount": 75,
            "manual_offer_price": "33.00", "stock": 3, "online_enabled": True,
        }, format="json")
        self.assertEqual(product.status_code, 201, product.data)
        pk = product.data["id"]
        self.assertEqual(product.data["effective_price"], "33.00")
        self.assertEqual(FactoryStock.objects.get(product_id=pk).quantity, 3)
        detail = API + f"products/{pk}/"
        duplicate = admin.patch(detail, {"color": "Black"}, format="json")
        self.assertEqual(duplicate.status_code, 400, duplicate.data)
        regular = admin.patch(detail, {"discount": 0, "manual_offer_price": "10.00"}, format="json")
        self.assertEqual(regular.data["effective_price"], "100.00")
        free = admin.patch(detail, {"discount": 100, "stock": 4}, format="json")
        self.assertEqual(free.status_code, 200, free.data)
        self.assertEqual(free.data["effective_price"], "0.00")
        self.assertTrue(StockAdjustment.objects.filter(product_id=pk, previous_quantity=3, new_quantity=4).exists())
        self.assertEqual(APIClient().get(f"/api/products/online/{pk}/").data["effective_price"], "0.00")

        ShopSettings.objects.create(pk=1, shipping_fee=0, accepting_orders=True)
        shopper = APIClient()
        shopper.force_authenticate(self.customer)
        items = [{"product": pk, "quantity": 1}]
        quote = shopper.post("/api/shop/orders/quote/", {"items": items}, format="json")
        self.assertEqual(quote.status_code, 200, quote.data)
        self.assertEqual(str(quote.data["subtotal"]), "0.00")
        order = shopper.post("/api/shop/orders/", {
            "request_key": str(uuid4()), "recipient_name": "Test Buyer", "phone": "01700000000",
            "address": "Test Address", "city": "Dhaka", "expected_total": "0.00",
            "expected_shipping_fee": "0.00", "items": items,
        }, format="json")
        self.assertEqual(order.status_code, 201, order.data)
        self.assertEqual(FactoryStock.objects.get(product_id=pk).quantity, 3)
        self.assertEqual(Order.objects.get().items.get().product_id, pk)
        self.assertEqual(admin.delete(detail).status_code, 405)
        self.assertEqual(admin.delete(API + f"categories/{self.category.pk}/").status_code, 400)

    def test_media_replacement_privacy_and_archives(self):
        self.client.force_authenticate(self.admin)
        first = self.upload(self.live)
        second = self.upload(self.live)
        raw = self.upload(self.live, "raw")
        hidden = self.upload(self.hidden)
        mp4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42"
        self.upload(self.live, "video", SimpleUploadedFile("clip.mp4", mp4, "video/mp4"))
        for row in (first, second):
            self.assertEqual(self.client.post(API + f"assets/{row['id']}/primary/").status_code, 200)
        self.assertEqual(Asset.objects.get(primary=True).pk, second["id"])
        self.assertEqual(self.client.post(API + f"assets/{raw['id']}/primary/").status_code, 400)

        asset = Asset.objects.get(pk=first["id"])
        old = self.private / asset.file.name
        self.assertTrue(old.exists())
        self.assertEqual(APIClient().get("/media/" + asset.file.name).status_code, 404)
        download = API + f"assets/{asset.pk}/download/"
        self.assertEqual(APIClient().get(download).status_code, 401)
        with self.captureOnCommitCallbacks(execute=True):
            replaced = self.client.post(API + f"assets/{asset.pk}/replace/", {"file": self.image("new.png")}, format="multipart")
        self.assertEqual(replaced.status_code, 200, replaced.data)
        self.assertFalse(old.exists())

        self.client.force_authenticate(self.moderator)
        self.assertEqual(self.client.get(API + f"assets/{hidden['id']}/download/").status_code, 404)
        self.assertEqual(self.client.get(API + f"products/{self.hidden.pk}/archive/").status_code, 404)
        self.assertEqual(self.client.delete(API + f"assets/{first['id']}/").status_code, 403)
        preview = self.client.get(download + "?inline=1")
        self.assertEqual(preview["Cache-Control"], "private, no-store")
        self.assertEqual(preview["Content-Type"], "image/png")
        self.assertTrue(preview["Content-Disposition"].startswith("inline"))
        self.assertTrue(b"".join(preview.streaming_content))
        thumbnail = self.client.get(API + f"assets/{second['id']}/download/?thumbnail=1")
        self.assertEqual(thumbnail["Content-Type"], "image/webp")
        self.assertTrue(b"".join(thumbnail.streaming_content))

        path = API + "downloads/bulk/"
        params = {"category": self.category.pk, "offer": "yes", "discount": "20"}
        count = self.client.get(path, {**params, "preview": 1})
        self.assertEqual(count.data, {"images": 2, "products": 1})
        self.assertEqual(self.client.get(path, {"preview": 1}).data["images"], 2)
        names = self.archive_names(self.client.get(path, params))
        self.assertEqual(len(set(names)), 2)
        self.assertTrue(all(name.startswith(f"20.00% off/clothing-{self.category.pk}/") for name in names))
        for kind, count in [("edited", 2), ("raw", 1)]:
            names = self.archive_names(self.client.get(API + f"products/{self.live.pk}/archive/?kind={kind}"))
            self.assertEqual(len(names), count)
            self.assertTrue(all(f"/{kind}-" in name and name.endswith(".png") for name in names))

        self.client.force_authenticate(self.admin)
        new_path = self.private / Asset.objects.get(pk=asset.pk).file.name
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.delete(API + f"assets/{asset.pk}/").status_code, 204)
        self.assertFalse(new_path.exists())

    def test_reject_invalid_uploads_and_apply_route_specific_request_limit(self):
        self.client.force_authenticate(self.admin)
        for kind, name, payload in [
            ("edited", "bad.png", b"<svg onload='alert(1)'/>"),
            ("raw", "too-large.png", b"0" * (20 * 1024 * 1024 + 1)),
            ("video", "fake.mp4", b"not a video"),
        ]:
            response = self.client.post(API + "assets/", {
                "product": self.live.pk, "kind": kind, "file": SimpleUploadedFile(name, payload),
            }, format="multipart")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Asset.objects.exists())
        with self.settings(REQUEST_MAX_BYTES=64):
            upload = self.upload(self.live)
            self.assertTrue(upload["id"])
            result = self.client.post(API + "categories/", {"name": "x" * 100}, format="json")
            self.assertEqual(result.status_code, 413)

    def archive_names(self, response):
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        data = BytesIO(b"".join(response.streaming_content))
        with ZipFile(data) as zip_file:
            self.assertIsNone(zip_file.testzip())
            return zip_file.namelist()
