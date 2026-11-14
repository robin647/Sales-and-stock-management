from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.db.models import IntegerField, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, Http404, HttpResponseNotModified

from .models import Product, ProductCategory
from .serializers import ProductCategorySerializer, ProductSerializer

class ProductCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.all()
    permission_classes = [permissions.AllowAny]

    def check_permissions(self, request):
        super().check_permissions(request)
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

    def get_queryset(self):
        qs = Product.objects.select_related("category").annotate(factory_quantity=Coalesce("factory_stock__quantity", Value(0), output_field=IntegerField()))
        if not self.request.user.is_authenticated or self.request.user.role != "admin":
            qs = qs.filter(is_active=True)
        if self.request.query_params.get("storefront") == "true":
            qs = qs.filter(online_enabled=True)
        return qs.order_by("name", "pk")

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
        if request.method in permissions.SAFE_METHODS:
            return
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication is required to manage products.")
        if request.method not in permissions.SAFE_METHODS and request.user.role != "admin":
            raise PermissionDenied("Only Admin can manage products.")
