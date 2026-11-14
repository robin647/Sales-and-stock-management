import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class ShopSettings(models.Model):
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=120, validators=[MinValueValidator(0)])
    payment_number = models.CharField(max_length=30, blank=True)
    payment_method = models.CharField(max_length=60, default="bKash / Nagad")
    payment_instructions = models.TextField(blank=True)
    whatsapp_number = models.CharField(max_length=20, default="8801781879276")
    accepting_orders = models.BooleanField(default=True)


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    kind = models.CharField(max_length=10, choices=[("fixed", "Fixed amount"), ("percent", "Percentage")])
    value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    minimum_order = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    expires_on = models.DateField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(default=0, help_text="0 means unlimited")
    used_count = models.PositiveIntegerField(default=0, editable=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting verification"
        CONFIRMED = "confirmed", "Confirmed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="online_orders")
    request_key = models.UUIDField(unique=True)
    recipient_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=25)
    address = models.TextField(max_length=1000)
    city = models.CharField(max_length=100)
    notes = models.TextField(blank=True, max_length=1000)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    coupon_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=30, blank=True)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_payment_reference = models.CharField(max_length=100, blank=True)
    delivery_payment_status = models.CharField(max_length=15, default="submitted", choices=[("submitted", "Submitted"), ("verified", "Verified"), ("rejected", "Rejected"), ("not_required", "Not required")])
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    tracking_number = models.CharField(max_length=100, blank=True)
    courier = models.CharField(max_length=100, blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"]), models.Index(fields=["customer", "created_at"])]
        constraints = [models.UniqueConstraint(fields=["delivery_payment_reference"], condition=~models.Q(delivery_payment_reference=""), name="unique_delivery_payment_reference")]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="online_order_items")
    product_name = models.CharField(max_length=150)
    code = models.CharField(max_length=64, blank=True)
    size = models.CharField(max_length=30, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
