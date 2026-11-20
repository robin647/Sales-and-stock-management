from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver


class PrivateMediaStorage(FileSystemStorage):
    @property
    def base_location(self):
        private = Path(settings.MODERATOR_MEDIA_ROOT).resolve()
        public = Path(settings.MEDIA_ROOT).resolve()
        if private.is_relative_to(public) or public.is_relative_to(private):
            raise ImproperlyConfigured("MODERATOR_MEDIA_ROOT and MEDIA_ROOT must be separate directories.")
        return str(private)

    def url(self, name):
        raise NotImplementedError("Use the authenticated moderator asset endpoint.")

    @property
    def location(self):
        return self.base_location


def private_storage():
    return PrivateMediaStorage(file_permissions_mode=0o600, directory_permissions_mode=0o700)


def asset_path(asset, filename):
    return f"{asset.product_id}/{asset.kind}/{uuid4().hex}{Path(filename).suffix}"


class Asset(models.Model):
    class Kind(models.TextChoices):
        EDITED = "edited", "Edited image"
        RAW = "raw", "Raw image"
        VIDEO = "video", "Video"

    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="moderator_assets")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    file = models.FileField(storage=private_storage, upload_to=asset_path)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=40)
    size_bytes = models.PositiveIntegerField()
    primary = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-primary", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["product"], condition=models.Q(primary=True), name="one_moderator_thumbnail"),
            models.CheckConstraint(condition=models.Q(primary=False) | models.Q(kind="edited"), name="moderator_thumbnail_edited"),
        ]


@receiver(post_delete, sender=Asset)
def remove_asset_file(sender, instance, using, **kwargs):
    storage, name = instance.file.storage, instance.file.name
    transaction.on_commit(lambda: storage.delete(name), using=using, robust=True)


class FacebookOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class DeliveryZone(models.TextChoices):
        INSIDE = "inside", "Inside Dhaka"
        OUTSIDE = "outside", "Outside Dhaka"

    DELIVERY_FEES = {DeliveryZone.INSIDE: 70, DeliveryZone.OUTSIDE: 150}

    tracking_id = models.CharField(max_length=64, unique=True)
    invoice = models.CharField(max_length=64, blank=True)
    customer_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32)
    address = models.CharField(max_length=500)
    area = models.CharField(max_length=150, blank=True)
    delivery_zone = models.CharField(max_length=7, choices=DeliveryZone.choices, blank=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    cod_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=9, choices=Status.choices, default=Status.PENDING)
    courier_charge = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def delivery_charge(self):
        return self.DELIVERY_FEES.get(self.delivery_zone)

    @property
    def collected_cod(self):
        return self.cod_amount if self.status == self.Status.DELIVERED else Decimal("0.00")

    @property
    def settled_courier_charge(self):
        if self.status == self.Status.PENDING:
            return Decimal("0.00")
        return self.courier_charge

    @property
    def steadfast_fee(self):
        charge = self.settled_courier_charge
        if charge is None:
            return None
        return (max(self.collected_cod - charge, 0) * Decimal("0.01")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )

    @property
    def net_sales(self):
        fee = self.steadfast_fee
        if fee is None:
            return None
        return self.collected_cod - self.settled_courier_charge - fee

    class Meta:
        ordering = ["-created_at", "-pk"]
