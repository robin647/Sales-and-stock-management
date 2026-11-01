from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class SwingOperator(models.Model):
    name = models.CharField(max_length=180)
    nid_number = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [models.Index(fields=["name", "is_active"])]

    def __str__(self):
        return self.name


class SwingLot(models.Model):
    operator = models.ForeignKey(SwingOperator, on_delete=models.PROTECT, related_name="lots")
    lot_number = models.CharField(max_length=80, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    fabric_specification = models.CharField(max_length=180, blank=True)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    cutting_master_name = models.CharField(max_length=180, blank=True)
    lot_date = models.DateField(default=timezone.localdate)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["lot_date", "id"]
        indexes = [models.Index(fields=["operator", "lot_date"])]
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gte=0), name="swing_lot_quantity_nonnegative"),
            models.CheckConstraint(check=models.Q(rate__gte=0), name="swing_lot_rate_nonnegative"),
        ]

    def __str__(self):
        return self.lot_number or f"Lot {self.pk}"


class SwingPayment(models.Model):
    operator = models.ForeignKey(SwingOperator, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField(default=timezone.localdate)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    remarks = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["payment_date", "id"]
        indexes = [models.Index(fields=["operator", "payment_date"])]
        constraints = [models.CheckConstraint(check=models.Q(amount__gt=0), name="swing_payment_amount_positive")]

    def __str__(self):
        return f"Payment {self.pk} · {self.operator.name}"


class SwingReject(models.Model):
    lot = models.ForeignKey(SwingLot, on_delete=models.PROTECT, related_name="rejections")
    reject_date = models.DateField(default=timezone.localdate)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    remarks = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["reject_date", "id"]
        indexes = [models.Index(fields=["lot", "reject_date"])]
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gt=0), name="swing_reject_quantity_positive"),
        ]

    @property
    def reject_amount(self):
        return self.quantity * self.lot.rate

    def __str__(self):
        return f"Reject {self.pk} · {self.lot}"
