from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.products.models import Product
from apps.showrooms.models import Showroom

class FactoryStock(models.Model):
    product = models.OneToOneField(Product, on_delete=models.PROTECT, related_name="factory_stock")
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

class ShowroomStock(models.Model):
    showroom = models.ForeignKey(Showroom, on_delete=models.PROTECT, related_name="product_stocks")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="showroom_stocks")
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["showroom_id", "product_id"]
        constraints = [models.UniqueConstraint(fields=["showroom", "product"], name="unique_showroom_product_stock")]

class StockAdjustment(models.Model):
    LOCATION_CHOICES = [("factory", "Factory"), ("showroom", "Showroom")]
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_adjustments")
    location = models.CharField(max_length=12, choices=LOCATION_CHOICES)
    showroom = models.ForeignKey(Showroom, null=True, blank=True, on_delete=models.PROTECT, related_name="stock_adjustments")
    previous_quantity = models.PositiveIntegerField()
    new_quantity = models.PositiveIntegerField()
    difference = models.IntegerField()
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stock_adjustments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

class StockTransfer(models.Model):
    TRANSFER_TYPES = [
        ("receive", "Receive from Factory"),
        ("sale", "Sale to Customer"),
        ("factory_return", "Return to Factory"),
        ("return", "Return from Customer"),
    ]
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_transfers")
    showroom = models.ForeignKey(Showroom, on_delete=models.PROTECT, related_name="stock_transfers")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    transfer_type = models.CharField(max_length=16, choices=TRANSFER_TYPES)
    date = models.DateField()
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stock_transfers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

class DailyStock(models.Model):
    """
    One row per (showroom, product, date).
    closing_qty = opening_qty + received_qty - sold_qty - returned_to_factory_qty + return_qty
    Enforced by full_clean() before every save — see clean().
    """

    showroom = models.ForeignKey(Showroom, on_delete=models.PROTECT, related_name="daily_stocks")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="daily_stocks")
    date = models.DateField()

    opening_qty = models.PositiveIntegerField(default=0)
    received_qty = models.PositiveIntegerField(default=0)
    sold_qty = models.PositiveIntegerField(default=0)
    return_qty = models.PositiveIntegerField(default=0)
    returned_to_factory_qty = models.PositiveIntegerField(default=0)
    closing_qty = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "product__name"]
        constraints = [
            models.UniqueConstraint(fields=["showroom", "product", "date"], name="unique_daily_stock_entry")
        ]

    def __str__(self):
        return f"{self.showroom} / {self.product} / {self.date}"

    def compute_closing(self):
        return self.opening_qty + self.received_qty - self.sold_qty - self.returned_to_factory_qty + self.return_qty

    def clean(self):
        from django.core.exceptions import ValidationError

        closing = self.compute_closing()
        if closing < 0:
            raise ValidationError(
                "Closing stock cannot be negative. Stock movements exceed available quantity "
                f"(opening {self.opening_qty} + received {self.received_qty} + return {self.return_qty} - factory return {self.returned_to_factory_qty})."
            )

    def save(self, *args, **kwargs):
        self.closing_qty = self.compute_closing()
        self.full_clean()
        super().save(*args, **kwargs)

class DailyBalance(models.Model):
    """
    One row per (showroom, date).
    total_sale = cash_sale + card_sale
    closing_balance = opening_balance + cash_sale - expense - salary - deposit
    (card_sale counts toward total_sale but NOT toward cash closing_balance)
    """

    showroom = models.ForeignKey(Showroom, on_delete=models.PROTECT, related_name="daily_balances")
    date = models.DateField()

    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cash_sale = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    card_sale = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_sale = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expense = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["showroom", "date"], name="unique_daily_balance_entry")
        ]

    def __str__(self):
        return f"{self.showroom} / {self.date}"

    def compute_totals(self):
        total_sale = self.cash_sale + self.card_sale
        closing_balance = self.opening_balance + self.cash_sale - self.expense - self.salary - self.deposit
        return total_sale, closing_balance

    def clean(self):
        from django.core.exceptions import ValidationError

        _, closing_balance = self.compute_totals()
        if closing_balance < 0:
            raise ValidationError(
                "Closing balance would be negative. Check expense, salary, and deposit amounts "
                "against opening balance and cash sale."
            )

    def save(self, *args, **kwargs):
        self.total_sale, self.closing_balance = self.compute_totals()
        self.full_clean()
        super().save(*args, **kwargs)
