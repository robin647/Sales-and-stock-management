from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.products.models import Product
from apps.inventory.models import FactoryStock
from .models import Coupon, Order, OrderItem, ShopSettings


def get_settings():
    return ShopSettings.objects.get_or_create(pk=1)[0]


def quote_order(items, code=""):
    settings = get_settings()
    products = {p.pk: p for p in Product.objects.select_related("factory_stock").filter(pk__in=[i["product"] for i in items], is_active=True, online_enabled=True)}
    subtotal = Decimal("0")
    for item in items:
        product = products.get(item["product"])
        if not product:
            raise ValidationError("A product is no longer available.")
        stock = getattr(product, "factory_stock", None)
        if not stock or stock.quantity < item["quantity"]:
            raise ValidationError(f"Not enough stock for {product.name}. Update your bag before paying the delivery charge.")
        subtotal += (product.discount_price if product.discount_price is not None else product.selling_price) * item["quantity"]
    discount, _ = calculate_discount(code, subtotal)
    return {"subtotal": subtotal, "coupon_discount": discount, "shipping_fee": settings.shipping_fee,
        "total": subtotal - discount + settings.shipping_fee, "cod_amount": subtotal - discount}


def calculate_discount(code, subtotal, *, lock=False):
    if not code:
        return Decimal("0.00"), None
    qs = Coupon.objects.select_for_update() if lock else Coupon.objects
    coupon = qs.filter(code=code.strip().upper(), is_active=True).first()
    if not coupon or (coupon.expires_on and coupon.expires_on < timezone.localdate()) or (coupon.usage_limit and coupon.used_count >= coupon.usage_limit):
        raise ValidationError({"coupon": "This coupon is invalid, expired or fully used."})
    if subtotal < coupon.minimum_order:
        raise ValidationError({"coupon": f"Minimum order for this coupon is ৳{coupon.minimum_order}."})
    value = subtotal * coupon.value / 100 if coupon.kind == "percent" else coupon.value
    return min(value, subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), coupon


@transaction.atomic
def place_order(customer, data):
    # Serialize this customer's retries, including concurrent identical submissions.
    type(customer).objects.select_for_update().get(pk=customer.pk)
    existing = Order.objects.filter(request_key=data["request_key"]).first()
    if existing:
        if existing.customer_id != customer.pk:
            raise ValidationError("Order request key is already in use.")
        return existing
    settings = get_settings()
    expected_total = data.pop("expected_total")
    expected_shipping_fee = data.pop("expected_shipping_fee")
    if expected_shipping_fee != settings.shipping_fee:
        raise ValidationError("Delivery charge changed. Refresh checkout before paying.")
    if not settings.accepting_orders:
        raise ValidationError("Online orders are temporarily paused.")
    if settings.shipping_fee > 0 and not settings.payment_number:
        raise ValidationError("Delivery payment details have not been configured. Please contact the shop.")
    if settings.shipping_fee > 0 and not data.get("delivery_payment_reference", "").strip():
        raise ValidationError({"delivery_payment_reference": "Pay the delivery charge first and enter the transaction ID."})
    reference = data.get("delivery_payment_reference", "")
    if reference and Order.objects.filter(delivery_payment_reference__iexact=reference).exists():
        raise ValidationError({"delivery_payment_reference": "This transaction ID has already been submitted. Check My orders or contact the shop."})
    requested = {item["product"]: item["quantity"] for item in data.pop("items")}
    products = {p.pk: p for p in Product.objects.filter(pk__in=requested, is_active=True, online_enabled=True)}
    stocks = {s.product_id: s for s in FactoryStock.objects.select_for_update().filter(product_id__in=requested).order_by("product_id")}
    lines = []
    subtotal = Decimal("0")
    for pk, quantity in requested.items():
        product, stock = products.get(pk), stocks.get(pk)
        if not product:
            raise ValidationError({"items": "One of the products is no longer available. Refresh your bag."})
        if not stock or stock.quantity < quantity:
            raise ValidationError({"items": f"Not enough stock for {product.name}. Available: {stock.quantity if stock else 0}."})
        price = product.discount_price if product.discount_price is not None else product.selling_price
        subtotal += price * quantity
        lines.append((product, quantity, price))
    discount, coupon = calculate_discount(data.pop("coupon", ""), subtotal, lock=True)
    if expected_total != subtotal - discount + settings.shipping_fee:
        raise ValidationError("Prices or coupon availability changed. Refresh checkout and review the total.")
    order = Order.objects.create(customer=customer, subtotal=subtotal, coupon_discount=discount,
        coupon_code=coupon.code if coupon else "", shipping_fee=settings.shipping_fee,
        total=subtotal - discount + settings.shipping_fee,
        delivery_payment_status="submitted" if settings.shipping_fee else "not_required", **data)
    for product, quantity, price in lines:
        stock = stocks[product.pk]
        stock.quantity -= quantity
        stock.save(update_fields=["quantity", "updated_at"])
        OrderItem.objects.create(order=order, product=product, product_name=product.name,
            code=product.code, size=product.size, quantity=quantity, unit_price=price, line_total=price * quantity)
    if coupon:
        coupon.used_count += 1
        coupon.save(update_fields=["used_count"])
    return order


@transaction.atomic
def update_order(order_id, data, *, customer=None):
    order = Order.objects.select_for_update().get(pk=order_id)
    next_status = data.get("status", order.status)
    if customer and (order.customer_id != customer.pk or order.status != "pending" or next_status != "cancelled"):
        raise ValidationError("Only your own pending order can be cancelled.")
    transitions = {"pending": {"confirmed", "cancelled"}, "confirmed": {"shipped", "cancelled"}, "shipped": {"delivered"}, "delivered": set(), "cancelled": set()}
    if next_status != order.status and next_status not in transitions[order.status]:
        raise ValidationError({"status": "This order status transition is not allowed."})
    payment_status = data.get("delivery_payment_status", order.delivery_payment_status)
    if next_status in ("confirmed", "shipped", "delivered") and order.shipping_fee > 0 and payment_status != "verified":
        raise ValidationError({"delivery_payment_status": "Verify the advance delivery charge before confirming the order."})
    if next_status == "cancelled" and order.status != "cancelled":
        items = list(order.items.all())
        stocks = {s.product_id: s for s in FactoryStock.objects.select_for_update().filter(product_id__in=[i.product_id for i in items]).order_by("product_id")}
        for item in items:
            stock = stocks[item.product_id]
            stock.quantity += item.quantity
            stock.save(update_fields=["quantity", "updated_at"])
    for field, value in data.items():
        setattr(order, field, value)
    order.save()
    return order
