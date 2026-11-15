from decimal import Decimal
from django.core.exceptions import FieldDoesNotExist
from django.db import models, transaction
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import viewsets, serializers, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import SearchFilter
from rest_framework.throttling import UserRateThrottle
from apps.products.models import Product, ProductCategory
from apps.inventory.models import FactoryStock
from apps.shop.models import Order, OrderItem
from . import models as records
from .permissions import CommercePermission, commerce_allowed, ROLE_MODULES
from .registry import MODULES, READ_ONLY
from .serializers import serializer_for, TeamSerializer
from .services import save_record


class RecordViewSet(viewsets.ModelViewSet):
    permission_classes = [CommercePermission]
    filter_backends = [SearchFilter]

    def get_queryset(self):
        qs = self.queryset.all()
        if "status" in {f.name for f in qs.model._meta.fields} and self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        save_record(serializer, self.request.user)

    @transaction.atomic
    def perform_update(self, serializer):
        save_record(serializer, self.request.user)

    @transaction.atomic
    def perform_destroy(self, instance):
        instance = type(instance).objects.select_for_update().get(pk=instance.pk)
        if isinstance(instance, (records.Purchase, records.ReturnRequest, records.Payment, records.LedgerEntry, records.TeamMember)):
            raise ValidationError("Keep financial, stock and team history. Use status, a correction entry or deactivate access instead.")
        instance.delete()


def record_view(module):
    model, _, _ = MODULES[module]
    return type(model.__name__ + "ViewSet", (RecordViewSet,), {
        "queryset": model.objects.all(), "serializer_class": TeamSerializer if module == "team" else serializer_for(model),
        "commerce_module": module,
        "search_fields": [f.name for f in model._meta.fields if isinstance(f, (models.CharField, models.TextField))],
    })


class WorkspaceView(APIView):
    permission_classes = [CommercePermission]
    commerce_module = "dashboard"

    def get(self, request):
        schemas = {}
        for module, (model, title, description) in MODULES.items():
            if not commerce_allowed(request.user, module):
                continue
            serializer = TeamSerializer() if module == "team" else serializer_for(model)()
            fields = []
            for name, field in serializer.fields.items():
                if field.read_only or name in READ_ONLY:
                    continue
                kind = "text"
                if isinstance(field, serializers.BooleanField): kind = "checkbox"
                elif isinstance(field, serializers.PrimaryKeyRelatedField): kind = "relation"
                elif isinstance(field, serializers.ChoiceField): kind = "select"
                elif isinstance(field, serializers.DateTimeField): kind = "datetime-local"
                elif isinstance(field, serializers.DateField): kind = "date"
                elif isinstance(field, serializers.DecimalField): kind = "decimal"
                elif isinstance(field, serializers.IntegerField): kind = "number"
                elif isinstance(field, serializers.EmailField): kind = "email"
                elif isinstance(field, serializers.URLField): kind = "url"
                elif name == "password": kind = "password"
                elif name in ("body", "message", "notes", "comment", "reply", "description", "reason", "address", "districts"): kind = "textarea"
                item = {"name": name, "label": (field.label or name.replace("_", " ")).capitalize(), "type": kind,
                        "required": field.required, "nullable": field.allow_null, "allow_blank": getattr(field, "allow_blank", False), "help": str(field.help_text or "")}
                if kind == "select": item["options"] = [{"value": k, "label": str(v)} for k, v in field.choices.items()]
                if getattr(field, "max_length", None): item["maxLength"] = field.max_length
                if getattr(field, "min_value", None) is not None: item["min"] = str(field.min_value)
                if getattr(field, "max_value", None) is not None: item["max"] = str(field.max_value)
                default = getattr(field, "default", serializers.empty)
                if default is not serializers.empty and not callable(default): item["default"] = default
                if "default" not in item:
                    try:
                        model_field = model._meta.get_field(name)
                        if model_field.has_default() and not callable(model_field.default):
                            item["default"] = model_field.default
                    except FieldDoesNotExist:
                        pass
                fields.append(item)
            schemas[module] = {"title": title, "description": description, "fields": fields,
                               "can_write": commerce_allowed(request.user, module, True),
                               "can_delete": module not in ("payments", "returns", "purchases", "finance", "team")}
        membership = getattr(request.user, "commerce_membership", None)
        access = [name for name in set().union(*ROLE_MODULES.values(), {"team", "audit"}) if commerce_allowed(request.user, name)]
        return Response({"modules": schemas, "access": access, "write_access": [name for name in access if commerce_allowed(request.user, name, True)], "role": membership.access_role if membership else "admin"})


class OptionsView(APIView):
    permission_classes = [CommercePermission]

    def get(self, request):
        module = request.query_params.get("module", "products")
        if not commerce_allowed(request.user, module):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        result = {}
        fields = {f.name for f in MODULES[module][0]._meta.fields} if module in MODULES else set()
        if "product" in fields or module == "products":
            result["product"] = [{"value": p.pk, "label": f"{p.name} · {p.code} · {p.size}"} for p in Product.objects.filter(sales_channel="online").order_by("name")]
        if "supplier" in fields:
            result["supplier"] = [{"value": p.pk, "label": p.name} for p in records.Supplier.objects.filter(is_active=True)]
        if "order" in fields:
            result["order"] = [{"value": str(p.pk), "label": f"#{str(p.pk)[:8].upper()} · {p.recipient_name} · {p.status}"} for p in Order.objects.all()[:500]]
        if "item" in fields:
            result["item"] = [{"value": p.pk, "label": f"#{str(p.order_id)[:8].upper()} · {p.product_name} · {p.quantity} pcs"} for p in OrderItem.objects.filter(product__sales_channel="online", order__status="delivered").order_by("-pk")[:500]]
        if module == "products":
            result["online_brand"] = [{"value": p.pk, "label": p.name} for p in records.Brand.objects.filter(is_active=True)]
            result["online_vendor"] = [{"value": p.pk, "label": p.name} for p in records.Vendor.objects.filter(status="active")]
        return Response(result)


class DashboardView(APIView):
    permission_classes = [CommercePermission]
    commerce_module = "dashboard"

    def get(self, request):
        orders = Order.objects.all()
        delivered = orders.filter(status="delivered")
        sold = delivered.aggregate(value=Sum(F("subtotal") - F("coupon_discount")))["value"] or Decimal(0)
        threshold = records.StorePreferences.objects.filter(pk=1).values_list("low_stock_threshold", flat=True).first()
        threshold = 5 if threshold is None else threshold
        low = FactoryStock.objects.filter(product__sales_channel="online", product__is_active=True, quantity__lte=threshold)
        stats = {"orders": orders.count(), "revenue": sold, "products": Product.objects.filter(sales_channel="online").count(),
                 "pending": orders.filter(status="pending").count(), "to_ship": orders.filter(status="confirmed").count(),
                 "low_stock": low.count(), "open_support": records.SupportTicket.objects.filter(status__in=["open", "progress"]).count(),
                 "returns": records.ReturnRequest.objects.filter(status__in=["requested", "approved"]).count()}
        finance = {"income": 0, "expense": 0}
        for row in records.LedgerEntry.objects.values("kind").annotate(total=Sum("amount")):
            finance[row["kind"]] = row["total"]
        trend = list(delivered.annotate(day=TruncDate("created_at")).values("day").annotate(sales=Sum(F("subtotal") - F("coupon_discount")), count=Count("id")).order_by("-day")[:30])
        stats["ledger"] = finance
        stats["trend"] = list(reversed(trend))
        stats["by_status"] = list(orders.values("status").annotate(count=Count("id")))
        stats["recent_orders"] = [{"id": str(p.pk), "customer": p.recipient_name, "total": p.total, "status": p.status, "date": p.created_at} for p in orders[:6]]
        stats["stock_alerts"] = [{"id": p.product_id, "name": p.product.name, "quantity": p.quantity} for p in low.select_related("product").order_by("quantity")[:8]]
        if not commerce_allowed(request.user, "finance"):
            stats.pop("ledger", None)
        return Response(stats)


class PreferencesView(APIView):
    permission_classes = [CommercePermission]
    commerce_module = "settings"

    def get(self, request):
        return Response(serializer_for(records.StorePreferences)(records.StorePreferences.objects.get_or_create(pk=1)[0]).data)

    def patch(self, request):
        obj = records.StorePreferences.objects.get_or_create(pk=1)[0]
        serializer = serializer_for(records.StorePreferences)(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [CommercePermission]
    commerce_module = "audit"
    queryset = records.AuditEvent.objects.all()
    serializer_class = serializer_for(records.AuditEvent)
    filter_backends = [SearchFilter]
    search_fields = ["actor_name", "module", "action", "summary"]


class PublicView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        now = timezone.now()
        preferences = records.StorePreferences.objects.filter(pk=1).first()
        path = request.query_params.get("path", "/")
        seo = records.SeoEntry.objects.filter(path=path).first()
        return Response({
            "store": serializer_for(records.StorePreferences)(preferences).data if preferences else {},
            "content": list(records.ContentPage.objects.filter(status="published").order_by("position", "pk").values("id", "title", "slug", "kind", "body", "image_url", "link")[:100]),
            "campaigns": list(records.Campaign.objects.filter(status="active", starts_at__lte=now, ends_at__gte=now, channel="website").values("id", "headline", "message")[:10]),
            "locales": list(records.Locale.objects.filter(is_active=True).values("language_code", "language_name", "currency_code", "currency_symbol", "exchange_rate", "is_default")),
            "seo": serializer_for(records.SeoEntry)(seo).data if seo else None,
            "brands": list(records.Brand.objects.filter(is_active=True).values("id", "name")),
            "reviews": list(records.Review.objects.filter(status="published").values("id", "product", "customer_name", "rating", "comment", "reply")[:100]),
        })


class ContactThrottle(UserRateThrottle):
    scope = "commerce_contact"
    rate = "10/hour"


class CustomerHelpView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ContactThrottle]

    def get(self, request):
        tickets = records.SupportTicket.objects.filter(customer=request.user)
        return Response({"tickets": list(tickets.values("id", "subject", "status", "reply", "updated_at")),
                         "returns": list(records.ReturnRequest.objects.filter(item__order__customer=request.user).values("id", "item", "quantity", "status", "refund_amount", "refund_reference"))})

    @transaction.atomic
    def post(self, request):
        if request.user.role != "customer":
            raise ValidationError("Use a customer account to submit a request.")
        kind = request.data.get("kind", "support")
        if kind == "review":
            product = serializers.IntegerField(min_value=1).run_validation(request.data.get("product"))
            if not OrderItem.objects.filter(order__customer=request.user, order__status="delivered", product_id=product, product__sales_channel="online").exists():
                raise ValidationError("Only customers with a delivered purchase can submit a review.")
            serializer = serializer_for(records.Review)(data={key: request.data[key] for key in ("product", "rating", "comment") if key in request.data} | {"customer_name": request.user.get_full_name() or request.user.username, "status": "pending"})
        elif kind == "return":
            item_id = serializers.IntegerField(min_value=1).run_validation(request.data.get("item"))
            if not OrderItem.objects.filter(pk=item_id, order__customer=request.user).exists():
                raise ValidationError("Choose an item from your own order.")
            serializer = serializer_for(records.ReturnRequest)(data={key: request.data[key] for key in ("item", "quantity", "reason") if key in request.data})
        elif kind == "support":
            order_id = request.data.get("order")
            if order_id:
                order_id = serializers.UUIDField().run_validation(order_id)
            if order_id and not Order.objects.filter(pk=order_id, customer=request.user).exists():
                raise ValidationError("Choose your own order.")
            serializer = serializer_for(records.SupportTicket)(data={key: request.data[key] for key in ("subject", "email", "message", "order") if key in request.data} | {"customer_name": request.user.get_full_name() or request.user.username})
        else:
            raise ValidationError("Unknown request type.")
        serializer.is_valid(raise_exception=True)
        obj = save_record(serializer, request.user)
        if kind == "support":
            obj.customer = request.user
            obj.save(update_fields=["customer"])
        return Response({"id": obj.pk, "message": "Your request has been received."}, status=201)
