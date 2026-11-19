from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
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
