from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count, OuterRef, Subquery, Sum
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from openpyxl import Workbook
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
from core.excel import protect_workbook

from .assets import archive, download_asset, save_upload
from .catalog import catalog, filtered_catalog, visible_products
from .models import Asset, FacebookOrder
from .serializers import (
    AssetSerializer, CatalogProductSerializer, FacebookOrderSerializer, ModeratorAccountSerializer,
    ModeratorLoginSerializer, SteadfastQuoteSerializer,
)
from .steadfast import quote_delivery


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


class FacebookOrderViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):
    lookup_value_regex = r"[0-9]+"
    permission_classes = [WorkspaceAdminPermission]
    serializer_class = FacebookOrderSerializer
    queryset = FacebookOrder.objects.all()

    @action(detail=False, methods=["get"], url_path="steadfast-quote")
    def steadfast_quote(self, request):
        params = SteadfastQuoteSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        return Response({"courier_charge": quote_delivery(**params.validated_data)})

    def get_queryset(self):
        orders = super().get_queryset()
        if self.action not in ("list", "export"):
            return orders
        period = serializers.ChoiceField(choices=("all", "week", "month", "custom")).run_validation(
            self.request.query_params.get("period", "all"),
        )
        if period in ("week", "month"):
            today = timezone.localdate()
            days = 7 if period == "week" else 30
            return orders.filter(created_at__date__range=(today - timedelta(days=days - 1), today))
        if period == "custom":
            date = serializers.DateField()
            start = date.run_validation(self.request.query_params.get("start_date"))
            end = date.run_validation(self.request.query_params.get("end_date"))
            if start > end:
                raise serializers.ValidationError({"end_date": "End date must be on or after the start date."})
            return orders.filter(created_at__date__range=(start, end))
        return orders

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        counts = dict(orders=0, units=0, pending=0, cancelled=0)
        zero = Decimal("0.00")
        cod = courier_charge = steadfast_fee = zero
        orders = self.get_queryset().order_by().only("status", "quantity", "cod_amount", "courier_charge")
        for order in orders.iterator():
            counts["orders"] += 1
            if order.status == FacebookOrder.Status.DELIVERED:
                counts["units"] += order.quantity
            else:
                counts[order.status] += 1
            cod += order.collected_cod
            courier_charge += order.settled_courier_charge or zero
            steadfast_fee += order.steadfast_fee or zero
        response.data["summary"] = {
            **counts, "cod": str(cod), "courier_charge": str(courier_charge),
            "steadfast_fee": str(steadfast_fee), "net_sales": str(cod - courier_charge - steadfast_fee),
        }
        return response

    @action(detail=False, methods=["get"])
    def export(self, request):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Facebook orders"
        sheet.freeze_panes = "A2"
        sheet.append((
            "Recorded (Dhaka)", "Tracking ID", "Invoice", "Customer", "Phone", "Address", "Area",
            "Delivery zone", "Weight (kg)", "Delivery type", "Status", "Ordered units", "COD requested", "COD collected",
            "Customer delivery rate", "Steadfast delivery charge", "Steadfast COD fee", "Net sales",
        ))
        for column in sheet[1]:
            sheet.column_dimensions[column.column_letter].width = len(column.value) + 4
        for order in self.get_queryset().iterator():
            sheet.append((
                timezone.localtime(order.created_at).replace(tzinfo=None), order.tracking_id,
                order.invoice, order.customer_name, order.phone, order.address, order.area,
                order.get_delivery_zone_display(), order.weight_kg, order.get_courier_delivery_display(),
                order.get_status_display(), order.quantity,
                order.cod_amount, order.collected_cod, order.delivery_charge, order.courier_charge,
                order.steadfast_fee, order.net_sales if order.status != FacebookOrder.Status.PENDING else None,
            ))
        sheet.auto_filter.ref = sheet.dimensions
        protect_workbook(workbook)
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="facebook-orders.xlsx"'
        workbook.save(response)
        return response

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except IntegrityError:
            raise serializers.ValidationError({"tracking_id": "An order with this tracking ID already exists."})

    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().update(request, *args, **kwargs)
        except IntegrityError:
            raise serializers.ValidationError({"tracking_id": "An order with this tracking ID already exists."})


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
