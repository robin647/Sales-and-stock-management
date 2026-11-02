from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Producer(models.Model):
    name = models.CharField(max_length=200, unique=True)
    mobile_number = models.CharField(max_length=30, blank=True, default="")
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def total_products(self):
        total = self.costs.filter(is_active=True).aggregate(total_quantity=models.Sum("quantity"))["total_quantity"] or Decimal("0.00")
        return Decimal(total)

    @property
    def total_cost(self):
        total = self.costs.filter(is_active=True).aggregate(total_cost=models.Sum("total_cost"))["total_cost"] or Decimal("0.00")
        return Decimal(total)

    @property
    def total_payments(self):
        total = self.payments.filter(is_active=True).aggregate(total_amount=models.Sum("amount"))["total_amount"] or Decimal("0.00")
        return Decimal(total)

    @property
    def outstanding_balance(self):
        return self.total_cost - self.total_payments


class CostSpecification(models.Model):
    name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProducerCost(models.Model):
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT, related_name="costs")
    bale_number = models.CharField(max_length=100, blank=True, default="")
    product_specification = models.CharField(max_length=255, blank=True, default="")
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    rate = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_percentage = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    base_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    transaction_date = models.DateField(default=timezone.localdate)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_date", "-id"]

    def clean(self):
        if self.quantity < 0:
            raise ValidationError({"quantity": "Quantity cannot be negative."})
        if self.rate < 0:
            raise ValidationError({"rate": "Rate cannot be negative."})
        if self.gst_percentage < 0:
            raise ValidationError({"gst_percentage": "GST percentage cannot be negative."})

    def save(self, *args, **kwargs):
        self.base_cost = (self.quantity * self.rate).quantize(Decimal("0.01"))
        gst_rate = self.gst_percentage or Decimal("0.00")
        self.gst_amount = ((self.base_cost * gst_rate) / Decimal("100")).quantize(Decimal("0.01")) if gst_rate else Decimal("0.00")
        self.total_cost = (self.base_cost + self.gst_amount).quantize(Decimal("0.01"))
        self.full_clean(exclude=["producer"]) if hasattr(self, "full_clean") else None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producer.name} - {self.bale_number or 'N/A'}"


class ProducerPayment(models.Model):
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField(default=timezone.localdate)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=100, blank=True, default="")
    remarks = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-payment_date", "-id"]

    def clean(self):
        if self.amount < 0:
            raise ValidationError({"amount": "Payment amount cannot be negative."})

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["producer"]) if hasattr(self, "full_clean") else None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producer.name} - {self.amount}"


class OtherCost(models.Model):
    specification = models.ForeignKey(CostSpecification, on_delete=models.PROTECT, related_name="costs")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cost_date = models.DateField(default=timezone.localdate)
    notes = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-cost_date", "-id"]

    def clean(self):
        if self.amount < 0:
            raise ValidationError({"amount": "Other cost amount cannot be negative."})

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["specification"]) if hasattr(self, "full_clean") else None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.specification.name} - {self.amount}"
