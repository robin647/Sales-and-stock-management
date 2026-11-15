from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError
from apps.inventory.models import FactoryStock
from apps.inventory.services import adjust_stock
from apps.shop.models import OrderItem, Order
from .models import Purchase, ReturnRequest, Payment, Locale


def check_transition(previous, next_status, transitions):
    if previous != next_status and next_status not in transitions.get(previous, set()):
        raise ValidationError({"status": f"Cannot change {previous} to {next_status}."})


@transaction.atomic
def save_record(serializer, user):
    model = serializer.Meta.model
    old = None
    if serializer.instance:
        old = model.objects.select_for_update().get(pk=serializer.instance.pk)
        serializer.instance = old
    data = serializer.validated_data
    if model == Purchase:
        if old and old.status in ("received", "cancelled"):
            raise ValidationError("A completed purchase is locked. Record a stock correction instead.")
        target = data.get("status", old.status if old else "draft")
        if not old and target != "draft":
            raise ValidationError("Create a draft purchase first, then receive it.")
        if old:
            check_transition(old.status, target, {"draft": {"received", "cancelled"}})
        supplier = data.get("supplier", old.supplier if old else None)
        if not supplier.is_active:
            raise ValidationError({"supplier": "Supplier is inactive."})
    elif model == ReturnRequest:
        if old and old.status in ("received", "rejected"):
            raise ValidationError("A completed return is locked.")
        if old and any(field in data and data[field] != getattr(old, field) for field in ("item", "quantity")):
            raise ValidationError("The order item and quantity cannot be changed after a return is requested.")
        target = data.get("status", old.status if old else "requested")
        if not old and target != "requested":
            raise ValidationError("Create the return request before approving it.")
        if old:
            check_transition(old.status, target, {"requested": {"approved", "rejected"}, "approved": {"received", "rejected"}})
        item = data.get("item", old.item if old else None)
        item = OrderItem.objects.select_for_update().select_related("order").get(pk=item.pk)
        if item.product.sales_channel != "online" or item.order.status != "delivered":
            raise ValidationError({"item": "Only delivered online items can be returned."})
        quantity = data.get("quantity", old.quantity if old else 0)
        used = ReturnRequest.objects.filter(item=item).exclude(status="rejected")
        if old:
            used = used.exclude(pk=old.pk)
        if (used.aggregate(total=Sum("quantity"))["total"] or 0) + quantity > item.quantity:
            raise ValidationError({"quantity": "Return quantity exceeds the remaining delivered quantity."})
        paid_ratio = (item.order.subtotal - item.order.coupon_discount) / item.order.subtotal if item.order.subtotal else Decimal(0)
        if data.get("refund_amount", old.refund_amount if old else 0) > (item.unit_price * quantity * paid_ratio).quantize(Decimal("0.01")):
            raise ValidationError({"refund_amount": "Refund cannot exceed the item's paid value."})
    elif model == Payment:
        if old and old.status == "verified":
            raise ValidationError("Verified payment records are locked. Record a separate refund or correction.")
        order = data.get("order", old.order if old else None)
        order = Order.objects.select_for_update().get(pk=order.pk)
        purpose = data.get("purpose", old.purpose if old else None)
        target = data.get("status", old.status if old else "pending")
        amount = data.get("amount", old.amount if old else Decimal(0))
        if target == "verified":
            verified = Payment.objects.filter(order=order, purpose=purpose, status="verified")
            if old:
                verified = verified.exclude(pk=old.pk)
            total = (verified.aggregate(value=Sum("amount"))["value"] or Decimal(0)) + amount
            limit = order.shipping_fee if purpose == "delivery" else order.subtotal - order.coupon_discount
            if purpose == "refund":
                limit = Payment.objects.filter(order=order, status="verified").exclude(purpose="refund").aggregate(value=Sum("amount"))["value"] or Decimal(0)
            if total > limit:
                raise ValidationError({"amount": "Verified amounts exceed the payable or recorded refundable balance."})
            if purpose == "cod" and order.status != "delivered":
                raise ValidationError({"order": "Record verified COD collection only after delivery."})
    obj = serializer.save()
    if model == Purchase and obj.status == "received":
        product = obj.product
        stock = FactoryStock.objects.select_for_update().get(product=product)
        adjust_stock(product=product, location="factory", new_quantity=stock.quantity + obj.quantity,
                     reason=f"Online purchase received: {obj.reference}", created_by=user)
    if model == ReturnRequest and obj.status == "received" and obj.restock:
        product = obj.item.product
        stock = FactoryStock.objects.select_for_update().get(product=product)
        adjust_stock(product=product, location="factory", new_quantity=stock.quantity + obj.quantity,
                     reason=f"Online return received: #{obj.pk}", created_by=user)
    if model == Payment and obj.status == "verified" and obj.purpose == "delivery":
        total = Payment.objects.filter(order=obj.order, purpose="delivery", status="verified").aggregate(value=Sum("amount"))["value"] or 0
        if total == obj.order.shipping_fee:
            Order.objects.filter(pk=obj.order_id).update(delivery_payment_status="verified")
    if model == Locale and obj.is_default:
        Locale.objects.exclude(pk=obj.pk).update(is_default=False)
    return obj


def delivery_fee(city, default):
    from .models import ShippingZone
    city = city.strip().casefold()
    if city:
        for zone in ShippingZone.objects.filter(is_active=True).order_by("pk"):
            if city in {name.strip().casefold() for name in zone.districts.split(",")}:
                return zone.fee
    return default
