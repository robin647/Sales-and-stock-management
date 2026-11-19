import re
import shutil
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

from django.db import transaction
from django.http import FileResponse, Http404
from django.utils.text import slugify
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers


IMAGE_TYPES = {
    "JPEG": (".jpg", "image/jpeg"), "PNG": (".png", "image/png"), "WEBP": (".webp", "image/webp"),
    "GIF": (".gif", "image/gif"), "BMP": (".bmp", "image/bmp"),
}
VIDEO_TYPES = {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime"}


def validate_upload(upload, kind):
    video = kind == "video"
    limit = 200 if video else 20
    if not 0 < upload.size <= limit * 1024 * 1024:
        raise serializers.ValidationError({"file": f"Upload a file up to {limit} MB."})
    if video:
        extension = Path(upload.name).suffix.lower()
        head = upload.read(4096)
        upload.seek(0)
        iso_media = len(head) >= 16 and head[4:8] == b"ftyp" and 16 <= int.from_bytes(head[:4], "big") <= upload.size
        quicktime = iso_media and head[8:12] == b"qt  "
        webm = head.startswith(b"\x1a\x45\xdf\xa3") and b"\x42\x82\x84webm" in head
        if not ((extension == ".mp4" and iso_media and not quicktime) or
                (extension == ".mov" and quicktime) or (extension == ".webm" and webm)):
            raise serializers.ValidationError({"file": "Choose a valid MP4, WEBM or MOV video."})
        return extension, VIDEO_TYPES[extension]
    try:
        with Image.open(upload, formats=list(IMAGE_TYPES)) as image:
            if image.width * image.height > 50_000_000:
                raise ValueError("Image dimensions are too large.")
            image.verify()
            kind = image.format
        upload.seek(0)
        with Image.open(upload, formats=[kind]) as image:
            image.load()
        return IMAGE_TYPES[kind]
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise serializers.ValidationError({"file": "Choose a valid JPEG, PNG, WebP, GIF or BMP image."}) from exc
    finally:
        upload.seek(0)


def save_upload(asset, upload):
    extension, content_type = validate_upload(upload, asset.kind)
    storage, previous = asset.file.storage, asset.file.name
    stem = Path(upload.name.replace("\\", "/")).stem
    asset.original_name = (re.sub(r"[\x00-\x1f\x7f]", "", stem)[:240] or "asset") + extension
    asset.content_type = content_type
    asset.size_bytes = upload.size
    with transaction.atomic():
        asset.file.save("asset" + extension, upload, save=False)
        current = asset.file.name
        try:
            asset.save()
        except Exception:
            storage.delete(current)
            raise
        if previous:
            transaction.on_commit(lambda: storage.delete(previous), robust=True)
    return asset


def private_download(source, filename, content_type, *, attachment):
    response = FileResponse(source, filename=filename, content_type=content_type, as_attachment=attachment)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response


def download_asset(asset, *, inline, thumbnail=False):
    if thumbnail and (asset.kind != "edited" or not asset.primary):
        raise Http404
    try:
        source = asset.file.open("rb")
    except FileNotFoundError as exc:
        raise Http404("This asset file is unavailable.") from exc
    if thumbnail:
        output = BytesIO()
        try:
            with source, Image.open(source) as image:
                image.draft("RGB", (160, 160))
                image.thumbnail((160, 160))
                ImageOps.exif_transpose(image).save(output, "WEBP", quality=78)
        except (OSError, ValueError) as exc:
            output.close()
            raise Http404("Thumbnail unavailable.") from exc
        output.seek(0)
        return private_download(output, f"asset-{asset.pk}.webp", "image/webp", attachment=False)
    return private_download(source, asset.original_name, asset.content_type, attachment=not inline)


def archive(assets, filename, *, bulk=False):
    temp = tempfile.TemporaryFile()
    try:
        with ZipFile(temp, "w", ZIP_STORED) as output:
            count = 0
            for asset in assets.iterator(chunk_size=100):
                product = asset.product
                folder = f"{slugify(product.name)[:70] or 'product'}-{product.pk}"
                if bulk:
                    category = product.category
                    offer = "regular-price"
                    if product.discount_price is not None and product.selling_price:
                        discount = 100 * (product.selling_price - product.discount_price) / product.selling_price
                        offer = f"{discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}% off"
                    folder = f"{offer}/{slugify(category.name)[:70] or 'category'}-{category.pk}/{folder}"
                extension = Path(asset.original_name).suffix
                name = f"{folder}/{asset.kind}-{asset.pk}{extension}"
                with asset.file.open("rb") as source, output.open(name, "w", force_zip64=True) as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
                count += 1
            if not count:
                raise serializers.ValidationError("No matching images are available.")
        temp.seek(0)
        return private_download(temp, filename, "application/zip", attachment=True)
    except FileNotFoundError as exc:
        temp.close()
        raise Http404("An asset file is unavailable. Refresh the list and try again.") from exc
    except Exception:
        temp.close()
        raise
