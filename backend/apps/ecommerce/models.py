from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Record(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-updated_at", "-pk"]


class Brand(Record):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Vendor(Record):
    name = models.CharField(max_length=150, unique=True)
    contact = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    status = models.CharField(max_length=12, choices=[("pending", "Pending approval"), ("active", "Active"), ("suspended", "Suspended")], default="pending")
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Supplier(Record):
    name = models.CharField(max_length=150, unique=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Purchase(Record):
    reference = models.CharField(max_length=80, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=12, choices=[("draft", "Draft"), ("received", "Received"), ("cancelled", "Cancelled")], default="draft")
    notes = models.TextField(blank=True)


class Payment(Record):
    order = models.ForeignKey("shop.Order", on_delete=models.PROTECT)
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    purpose = models.CharField(max_length=12, choices=[("delivery", "Delivery fee"), ("cod", "Product / COD"), ("refund", "Refund")])
    method = models.CharField(max_length=50, default="Cash")
    status = models.CharField(max_length=12, choices=[("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")], default="pending")
    notes = models.TextField(blank=True)


class ReturnRequest(Record):
    item = models.ForeignKey("shop.OrderItem", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=[("requested", "Requested"), ("approved", "Approved"), ("received", "Received"), ("rejected", "Rejected")], default="requested")
    restock = models.BooleanField(default=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    refund_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)


class ShippingZone(Record):
    name = models.CharField(max_length=120, unique=True)
    districts = models.TextField(help_text="Comma-separated city or district names")
    fee = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    delivery_days = models.CharField(max_length=60, default="2–5 business days")
    courier = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)


class Review(Record):
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    customer_name = models.CharField(max_length=120)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=3000)
    status = models.CharField(max_length=12, choices=[("pending", "Pending"), ("published", "Published"), ("rejected", "Rejected")], default="pending")
    reply = models.TextField(blank=True)


class SupportTicket(Record):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=180)
    customer_name = models.CharField(max_length=120)
    email = models.EmailField()
    order = models.ForeignKey("shop.Order", on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField(max_length=5000)
    priority = models.CharField(max_length=10, choices=[("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")], default="normal")
    status = models.CharField(max_length=12, choices=[("open", "Open"), ("progress", "In progress"), ("resolved", "Resolved"), ("closed", "Closed")], default="open")
    reply = models.TextField(blank=True, max_length=5000)


class ContentPage(Record):
    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    kind = models.CharField(max_length=12, choices=[("page", "Page"), ("banner", "Banner"), ("faq", "FAQ")], default="page")
    body = models.TextField(max_length=20000)
    image_url = models.URLField(blank=True)
    link = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=[("draft", "Draft"), ("published", "Published")], default="draft")
    position = models.PositiveIntegerField(default=0)


class Campaign(Record):
    name = models.CharField(max_length=150)
    channel = models.CharField(max_length=12, choices=[("website", "Website"), ("email", "Email"), ("social", "Social"), ("sms", "SMS")], default="website")
    headline = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=12, choices=[("draft", "Draft"), ("active", "Active"), ("paused", "Paused"), ("completed", "Completed")], default="draft")
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])


class LedgerEntry(Record):
    reference = models.CharField(max_length=80, unique=True)
    date = models.DateField()
    kind = models.CharField(max_length=10, choices=[("income", "Income"), ("expense", "Expense")])
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    notes = models.TextField(blank=True)


class SeoEntry(Record):
    path = models.CharField(max_length=300, unique=True)
    title = models.CharField(max_length=70)
    description = models.CharField(max_length=170)
    canonical_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    noindex = models.BooleanField(default=False)


class Locale(Record):
    language_code = models.CharField(max_length=12)
    language_name = models.CharField(max_length=80)
    currency_code = models.CharField(max_length=3)
    currency_symbol = models.CharField(max_length=10)
    exchange_rate = models.DecimalField(max_digits=16, decimal_places=6, default=1, validators=[MinValueValidator(0.000001)])
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at", "-pk"]
        constraints = [models.UniqueConstraint(fields=["language_code", "currency_code"], name="unique_store_locale")]


class TeamMember(Record):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="commerce_membership")
    name = models.CharField(max_length=120)
    access_role = models.CharField(max_length=15, choices=[("manager", "Manager"), ("catalog", "Catalog manager"), ("fulfillment", "Order fulfillment"), ("support", "Customer support"), ("finance", "Finance"), ("viewer", "Read only")])
    is_active = models.BooleanField(default=True)


class StorePreferences(Record):
    store_name = models.CharField(max_length=120, default="Mahir Sherwani")
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    announcement = models.CharField(max_length=250, blank=True)
    return_policy = models.TextField(blank=True)
    privacy_policy = models.TextField(blank=True)


class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    actor_name = models.CharField(max_length=150)
    action = models.CharField(max_length=20)
    module = models.CharField(max_length=60)
    object_id = models.CharField(max_length=100, blank=True)
    summary = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
