from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import FactoryStock, ShowroomStock, StockAdjustment

def _lock_stock(product, location, showroom=None):
    if location == "factory":
        row, _ = FactoryStock.objects.get_or_create(product=product, defaults={"quantity": 0})
        return FactoryStock.objects.select_for_update().get(pk=row.pk)
    if location == "showroom" and showroom is not None:
        row, _ = ShowroomStock.objects.get_or_create(
            product=product, showroom=showroom, defaults={"quantity": 0}
        )
        return ShowroomStock.objects.select_for_update().get(pk=row.pk)
    raise ValidationError({"showroom": "A valid showroom is required for showroom stock."})

@transaction.atomic
def adjust_stock(*, product, location, showroom=None, new_quantity, reason, created_by):
    from apps.showrooms.models import Showroom

    if showroom and not isinstance(showroom, Showroom):
        showroom = Showroom.objects.get(pk=showroom)
    if location == "factory" and showroom:
        raise ValidationError({"showroom": "Factory stock cannot be assigned to a showroom."})
    stock = _lock_stock(product, location, showroom)
    previous = stock.quantity
    stock.quantity = new_quantity
    stock.save(update_fields=["quantity", "updated_at"])
    return StockAdjustment.objects.create(
        product=product, location=location, showroom=showroom,
        previous_quantity=previous, new_quantity=new_quantity,
        difference=new_quantity - previous, reason=reason.strip(), created_by=created_by,
    )

@transaction.atomic
def transfer_stock(*, product, showroom, quantity, transfer_type, date, created_by, notes=""):
    from .models import DailyStock, StockTransfer

    factory = _lock_stock(product, "factory")
    store = _lock_stock(product, "showroom", showroom)
    daily, _ = DailyStock.objects.select_for_update().get_or_create(
        showroom=showroom, product=product, date=date,
        defaults={"created_by": created_by},
    )
    if date == timezone.localdate():
        recorded_quantity = daily.compute_closing()
        if store.quantity > recorded_quantity:
            daily.opening_qty += store.quantity - recorded_quantity

    if transfer_type == "receive":
        if factory.quantity < quantity:
            raise ValidationError({"quantity": f"Factory has only {factory.quantity} units available."})
        factory.quantity -= quantity
        store.quantity += quantity
        daily.received_qty += quantity
    elif transfer_type == "sale":
        if store.quantity < quantity:
            raise ValidationError({"quantity": f"Showroom has only {store.quantity} units available."})
        store.quantity -= quantity
        daily.sold_qty += quantity
    elif transfer_type == "factory_return":
        if store.quantity < quantity:
            raise ValidationError({"quantity": f"Showroom has only {store.quantity} units available."})
        store.quantity -= quantity
        factory.quantity += quantity
        daily.returned_to_factory_qty += quantity
    elif transfer_type == "return":

        store.quantity += quantity
        daily.return_qty += quantity
    else:
        raise ValidationError({"transfer_type": "Choose a valid stock transfer type."})
    factory.save(update_fields=["quantity", "updated_at"])
    store.save(update_fields=["quantity", "updated_at"])
    try:
        daily.save()
    except DjangoValidationError as exc:
        detail = getattr(exc, "message_dict", None) or exc.messages
        raise ValidationError(detail) from exc
    return StockTransfer.objects.create(
        product=product, showroom=showroom, quantity=quantity,
        transfer_type=transfer_type, date=date, notes=notes, created_by=created_by,
    )

@transaction.atomic
def update_transfer(*, transfer, quantity, transfer_type):
    from .models import DailyStock

    transfer = transfer.__class__.objects.select_for_update().get(pk=transfer.pk)
    factory = _lock_stock(transfer.product, "factory")
    store = _lock_stock(transfer.product, "showroom", transfer.showroom)
    daily = DailyStock.objects.select_for_update().get(
        showroom=transfer.showroom, product=transfer.product, date=transfer.date
    )
    _apply_transfer_change(
        transfer, factory, store, daily, quantity=quantity, transfer_type=transfer_type
    )
    return transfer

@transaction.atomic
def delete_transfer(*, transfer):
    from .models import DailyStock

    transfer = transfer.__class__.objects.select_for_update().get(pk=transfer.pk)
    factory = _lock_stock(transfer.product, "factory")
    store = _lock_stock(transfer.product, "showroom", transfer.showroom)
    daily = DailyStock.objects.select_for_update().get(
        showroom=transfer.showroom, product=transfer.product, date=transfer.date
    )
    _apply_transfer_change(
        transfer, factory, store, daily, quantity=0, transfer_type=None
    )
    transfer.delete()

def _apply_transfer_change(transfer, factory, store, daily, *, quantity, transfer_type):
    from rest_framework.exceptions import ValidationError

    daily_fields = {
        "receive": "received_qty",
        "sale": "sold_qty",
        "factory_return": "returned_to_factory_qty",
        "return": "return_qty",
    }
    old_type = transfer.transfer_type
    new_type = transfer_type
    old_quantity = transfer.quantity
    new_quantity = quantity
    if old_type not in daily_fields or (new_type is not None and new_type not in daily_fields):
        raise ValidationError({"transfer_type": "Choose a valid stock transfer type."})

    def deltas(kind, amount):
        if kind == "receive":
            return -amount, amount
        if kind == "sale":
            return 0, -amount
        if kind == "factory_return":
            return amount, -amount
        return 0, amount

    old_factory, old_store = deltas(old_type, old_quantity)
    new_factory, new_store = deltas(new_type, new_quantity) if new_type else (0, 0)
    factory.quantity += new_factory - old_factory
    store.quantity += new_store - old_store
    if factory.quantity < 0:
        raise ValidationError({"quantity": f"Factory stock would become negative ({factory.quantity})."})
    if store.quantity < 0:
        raise ValidationError({"quantity": f"Showroom stock would become negative ({store.quantity})."})

    setattr(daily, daily_fields[old_type], getattr(daily, daily_fields[old_type]) - old_quantity)
    if new_type:
        setattr(daily, daily_fields[new_type], getattr(daily, daily_fields[new_type]) + new_quantity)
    try:
        daily.save()
    except DjangoValidationError as exc:
        detail = getattr(exc, "message_dict", None) or exc.messages
        raise ValidationError(detail) from exc
    factory.save(update_fields=["quantity", "updated_at"])
    store.save(update_fields=["quantity", "updated_at"])
    if new_type:
        transfer.quantity = new_quantity
        transfer.transfer_type = new_type
        transfer.save(update_fields=["quantity", "transfer_type"])
