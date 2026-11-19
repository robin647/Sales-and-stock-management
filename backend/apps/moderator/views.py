from django.db import IntegrityError, transaction
from django.db.models import Count, OuterRef, Subquery, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import datetime_from_epoch

from apps.accounts.models import User
from apps.accounts.views import CustomTokenObtainPairView
from apps.products.models import ProductCategory
from apps.products.serializers import ProductCategorySerializer

from .assets import archive, download_asset, save_upload
from .catalog import catalog, filtered_catalog, visible_products
from .models import Asset
from .serializers import AssetSerializer, CatalogProductSerializer, ModeratorAccountSerializer, ModeratorLoginSerializer


class WorkspaceSessionPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated or user.role not in (User.Role.ADMIN, User.Role.MODERATOR):
            return False
        if request.auth and BlacklistedToken.objects.filter(token__jti=request.auth[api_settings.JTI_CLAIM]).exists():
            raise AuthenticationFailed("This workspace session has ended. Sign in again.")
        return True


class WorkspacePermission(WorkspaceSessionPermission):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.role == User.Role.ADMIN or request.method in SAFE_METHODS
        )


class WorkspaceAdminPermission(WorkspaceSessionPermission):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == User.Role.ADMIN


class ModeratorLoginView(CustomTokenObtainPairView):
    serializer_class = ModeratorLoginSerializer


@api_view(["POST"])
@permission_classes([WorkspaceSessionPermission])
@transaction.atomic
def logout(request):
    access = request.auth
    if access:
        outstanding, _ = OutstandingToken.objects.get_or_create(
            jti=access[api_settings.JTI_CLAIM],
            defaults={
                "token": str(access),
                "user": request.user,
                "created_at": datetime_from_epoch(access["iat"]),
                "expires_at": datetime_from_epoch(access["exp"]),
            },
        )
        BlacklistedToken.objects.get_or_create(token=outstanding)
    refresh = request.data.get("refresh")
    if not isinstance(refresh, str) or not refresh:
        return Response(status=204)
    try:
        token = RefreshToken(refresh)
        if str(token.get("user_id")) == str(request.user.pk):
            token.blacklist()
    except TokenError:
        pass
    return Response(status=204)


class AccountViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin, viewsets.GenericViewSet):
    lookup_value_regex = r"[0-9]+"
    permission_classes = [WorkspaceAdminPermission]
    serializer_class = ModeratorAccountSerializer
    queryset = User.objects.filter(role=User.Role.MODERATOR, is_staff=False, is_superuser=False).order_by("username")

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        self.queryset = self.queryset.select_for_update()
        return super().update(request, *args, **kwargs)


class CategoryViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r"[0-9]+"
    permission_classes = [WorkspacePermission]
    serializer_class = ProductCategorySerializer
    product_channel = "online"
    pagination_class = None
    queryset = ProductCategory.objects.filter(sales_channel="online").order_by("name", "pk")

    def perform_create(self, serializer):
        serializer.save(sales_channel=self.product_channel)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as exc:
            raise serializers.ValidationError("Move linked products before deleting this category.") from exc


def with_thumbnail(products):
    thumbnail = Asset.objects.filter(product_id=OuterRef("pk"), primary=True, kind=Asset.Kind.EDITED)
    return products.annotate(primary_asset=Subquery(thumbnail.values("pk")[:1]))


class ProductViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin, viewsets.GenericViewSet):
    lookup_value_regex = r"[0-9]+"
    permission_classes = [WorkspacePermission]
    serializer_class = CatalogProductSerializer
    product_channel = "online"

    def get_queryset(self):
        products = filtered_catalog(self.request) if self.action == "list" else catalog(self.request.user)
        return with_thumbnail(products)

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        data = self.get_serializer(product).data
        siblings = self.get_queryset().filter(category=product.category, name=product.name).exclude(pk=product.pk)
        data["variants"] = list(siblings.order_by("color", "size", "pk").values(
            "id", "code", "color", "size", "factory_quantity", "is_active",
        ))
        data["assets"] = AssetSerializer(product.moderator_assets.all(), many=True).data
        return Response(data)

    def perform_create(self, serializer):
        self.save_catalog(serializer, sales_channel=self.product_channel)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        get_object_or_404(visible_products(request.user).select_for_update(), pk=kwargs["pk"])
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        self.save_catalog(serializer)

    @staticmethod
    def save_catalog(serializer, **kwargs):
        try:
            with transaction.atomic():
                serializer.save(**kwargs)
        except IntegrityError as exc:
            raise serializers.ValidationError("This catalog entry conflicts with an existing record.") from exc

    @action(detail=True, methods=["get"])
    def archive(self, request, pk=None):
        product = self.get_object()
        kind = request.query_params.get("kind", "edited")
        if kind not in (Asset.Kind.EDITED, Asset.Kind.RAW):
            raise serializers.ValidationError({"kind": "Choose edited or raw images."})
        assets = product.moderator_assets.filter(kind=kind).select_related("product").order_by("pk")
        return archive(assets, f"product-{product.pk}-{kind}.zip")


class UploadSerializer(serializers.Serializer):
    product = serializers.IntegerField(min_value=1)
    kind = serializers.ChoiceField(choices=Asset.Kind.choices)
    file = serializers.FileField()


class ReplaceSerializer(serializers.Serializer):
    file = serializers.FileField()


class AssetViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    lookup_value_regex = r"[0-9]+"
    permission_classes = [WorkspacePermission]
    serializer_class = AssetSerializer
    parser_classes = [MultiPartParser]

    def get_queryset(self):
        return Asset.objects.filter(product__in=visible_products(self.request.user))

    def create(self, request, *args, **kwargs):
        form = UploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        product = get_object_or_404(visible_products(request.user), pk=form.validated_data["product"])
        asset = Asset(product=product, kind=form.validated_data["kind"])
        save_upload(asset, form.validated_data["file"])
        return Response(self.get_serializer(asset).data, status=201)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        return download_asset(
            self.get_object(),
            inline=request.query_params.get("inline") == "1",
            thumbnail=request.query_params.get("thumbnail") == "1",
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def replace(self, request, pk=None):
        form = ReplaceSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        asset = get_object_or_404(self.get_queryset().select_for_update(), pk=pk)
        save_upload(asset, form.validated_data["file"])
        return Response(self.get_serializer(asset).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def primary(self, request, pk=None):
        current = self.get_object()
        get_object_or_404(visible_products(request.user).select_for_update(), pk=current.product_id)
        asset = get_object_or_404(self.get_queryset().select_for_update(), pk=pk)
        if asset.kind != Asset.Kind.EDITED:
            raise serializers.ValidationError("Only edited images can be the primary thumbnail.")
        Asset.objects.filter(product_id=asset.product_id, primary=True).exclude(pk=asset.pk).update(primary=False)
        asset.primary = True
        asset.save(update_fields=["primary", "updated_at"])
        return Response(self.get_serializer(asset).data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        asset = get_object_or_404(self.get_queryset().select_for_update(), pk=kwargs["pk"])
        asset.delete()
        return Response(status=204)


@api_view(["GET"])
@permission_classes([WorkspacePermission])
def bulk(request):
    assets = Asset.objects.filter(
        product__in=filtered_catalog(request).order_by().values("pk"), kind=Asset.Kind.EDITED,
    ).select_related("product__category").order_by("product_id", "pk")
    if request.query_params.get("preview") == "1":
        return Response(assets.aggregate(images=Count("pk"), products=Count("product_id", distinct=True)))
    return archive(assets, "edited-catalog.zip", bulk=True)


@api_view(["GET"])
@permission_classes([WorkspacePermission])
def dashboard(request):
    products = catalog(request.user)
    data = {
        "products": products.count(),
        "on_offer": products.filter(discount_price__isnull=False).count(),
        "stock": products.aggregate(total=Sum("factory_quantity", default=0))["total"],
        "out_of_stock": products.filter(factory_quantity=0).count(),
        "recent": CatalogProductSerializer(with_thumbnail(products).order_by("-created_at", "-pk")[:5], many=True).data,
    }
    if request.user.role == User.Role.ADMIN:
        data["inactive"] = products.filter(is_active=False).count()
        data["moderators"] = AccountViewSet.queryset.count()
    return Response(data)
