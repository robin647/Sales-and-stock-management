from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.db.models import Count, IntegerField, Q, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, Http404, HttpResponseNotModified

from .models import Product, ProductCategory
from .serializers import ProductCategorySerializer, ProductSerializer
from apps.ecommerce.permissions import commerce_allowed

class ProductCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.all()
    product_channel = "main"

    def get_queryset(self):
        channel = self.product_channel
        if not self.request.user.is_authenticated or self.request.user.role not in ("admin", "showroom_user"):
            channel = "online"
        return super().get_queryset().filter(sales_channel=channel)

    def perform_create(self, serializer):
        serializer.save(sales_channel=self.product_channel)

    permission_classes = [permissions.AllowAny]

    def check_permissions(self, request):
        super().check_permissions(request)
        if self.product_channel == "online" and commerce_allowed(request.user, "products", request.method not in permissions.SAFE_METHODS):
            return
        if request.method in permissions.SAFE_METHODS:
            return
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication is required to manage product categories.")
        if request.method not in permissions.SAFE_METHODS and request.user.role != "admin":
            raise PermissionDenied("Only Admin can manage product categories.")

class ProductViewSet(viewsets.ModelViewSet):
    """
    Admin: full CRUD over all products (active + inactive).
    Showroom user: read-only, active products only (they need this list to
    log daily stock/sales but must not be able to edit product data).
    """

    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["category", "is_active"]
    product_channel = "main"

    def perform_create(self, serializer):
        serializer.save(sales_channel=self.product_channel)

    def get_queryset(self):
        qs = Product.objects.select_related("category").annotate(factory_quantity=Coalesce("factory_stock__quantity", Value(0), output_field=IntegerField()))
        channel = self.product_channel
        if (not self.request.user.is_authenticated or self.request.user.role not in ("admin", "showroom_user")
                or self.request.query_params.get("storefront") == "true"):
            channel = "online"
        # Photo URLs remain valid for existing main-inventory product images.
        if self.action != "photo":
            qs = qs.filter(sales_channel=channel)
        if not commerce_allowed(self.request.user, "products"):
            qs = qs.filter(is_active=True)
        if self.request.query_params.get("storefront") == "true":
            qs = qs.filter(online_enabled=True).filter(Q(online_vendor__isnull=True) | Q(online_vendor__status="active")).annotate(popularity_orders=Count(
                "online_order_items__order",
                filter=Q(online_order_items__order__status__in=["confirmed", "shipped", "delivered"]),
                distinct=True,
            ))
            return qs.order_by("-popularity_orders", "-created_at", "-pk")
        if channel == "online" and not commerce_allowed(self.request.user, "products"):
            qs = qs.filter(online_enabled=True).filter(Q(online_vendor__isnull=True) | Q(online_vendor__status="active"))
        return qs.order_by("name", "pk")

    @action(detail=True, methods=["post"], url_path="copy-to-online")
    def copy_to_online(self, request, pk=None):
        from django.db import transaction
        from rest_framework.response import Response
        from .models import ProductPhoto
        from apps.inventory.models import FactoryStock
        source = self.get_object()
        with transaction.atomic():
            online_category, _ = ProductCategory.objects.get_or_create(name=source.category.name, sales_channel="online")
            data = {field: getattr(source, field) for field in (
                "name", "category", "size", "selling_price", "discount_price", "description",
                "image", "image_url", "photo_version",
            )}
            product, created = Product.objects.get_or_create(
                name=source.name, category=online_category, size=source.size, sales_channel="online",
                defaults={key: value for key, value in data.items() if key not in ("name", "category", "size")},
            )
            if created:
                product.online_enabled = False
                product.save(update_fields=["online_enabled"])
                FactoryStock.objects.create(product=product, quantity=0)
                photo = ProductPhoto.objects.filter(product=source).first()
                if photo:
                    ProductPhoto.objects.create(product=product, content=photo.content)
        return Response(self.get_serializer(product).data, status=201 if created else 200)

    @action(detail=True, methods=["get"], url_name="photo")
    def photo(self, request, pk=None):
        product = self.get_object()
        etag = f'"{product.photo_version}"'
        if request.headers.get("If-None-Match") == etag and product.photo_version:
            response = HttpResponseNotModified()
            response["ETag"] = etag
            response["Cache-Control"] = "public, max-age=86400" if product.is_active else "private, no-cache"
            return response
        from .models import ProductPhoto
        photo = ProductPhoto.objects.filter(product=product).first()
        if not photo:
            raise Http404
        response = HttpResponse(bytes(photo.content), content_type="image/webp")
        response["Cache-Control"] = "public, max-age=86400" if product.is_active else "private, no-cache"
        response["ETag"] = etag
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def check_permissions(self, request):
        super().check_permissions(request)
        if self.product_channel == "online" and commerce_allowed(request.user, "products", request.method not in permissions.SAFE_METHODS):
            return
        if request.method in permissions.SAFE_METHODS:
            return
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication is required to manage products.")
        if request.method not in permissions.SAFE_METHODS and request.user.role != "admin":
            raise PermissionDenied("Only Admin can manage products.")


class OnlineCategoryViewSet(ProductCategoryViewSet):
    product_channel = "online"


class OnlineProductViewSet(ProductViewSet):
    product_channel = "online"
