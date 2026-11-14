from django.core.validators import MinValueValidator
from django.db import models

class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Product categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=64, blank=True, default="")
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name="products")
    size = models.CharField(max_length=30, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to="products/%Y/%m/", blank=True)
    image_url = models.URLField(max_length=1000, blank=True)
    photo_version = models.CharField(max_length=36, blank=True, editable=False)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    online_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "category", "size"], name="unique_product_variant")
        ]

    def __str__(self):
        return f"{self.name} ({self.size})" if self.size else self.name


class ProductPhoto(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="stored_photo")
    content = models.BinaryField()
