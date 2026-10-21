from django.db import transaction
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
    elif transfer_type == "return":
        # Customer returns go back into this showroom's stock.
        store.quantity += quantity
        daily.return_qty += quantity
    else:
        raise ValidationError({"transfer_type": "Choose receive, sale, or return."})
    factory.save(update_fields=["quantity", "updated_at"])
    store.save(update_fields=["quantity", "updated_at"])
    daily.save()
    return StockTransfer.objects.create(
        product=product, showroom=showroom, quantity=quantity,
        transfer_type=transfer_type, date=date, notes=notes, created_by=created_by,
    )


@transaction.atomic
def update_transfer_quantity(*, transfer, quantity):
    from .models import DailyStock
    from rest_framework.exceptions import ValidationError

    difference = quantity - transfer.quantity
    if difference == 0:
        return transfer
    factory = _lock_stock(transfer.product, "factory")
    store = _lock_stock(transfer.product, "showroom", transfer.showroom)
    daily = DailyStock.objects.select_for_update().get(
        showroom=transfer.showroom, product=transfer.product, date=transfer.date
    )
    if transfer.transfer_type == "receive":
        if difference > 0 and factory.quantity < difference:
            raise ValidationError({"quantity": f"Factory has only {factory.quantity} units available."})
        factory.quantity -= difference
        store.quantity += difference
        daily.received_qty += difference
    elif transfer.transfer_type == "sale":
        if difference > 0 and store.quantity < difference:
            raise ValidationError({"quantity": f"Showroom has only {store.quantity} units available."})
        store.quantity -= difference
        daily.sold_qty += difference
    elif transfer.transfer_type == "return":
        if difference < 0 and store.quantity < -difference:
            raise ValidationError({"quantity": f"Showroom has only {store.quantity} units available to reverse this return."})
        store.quantity += difference
        daily.return_qty += difference
    factory.save(update_fields=["quantity", "updated_at"])
    store.save(update_fields=["quantity", "updated_at"])
    daily.save()
    transfer.quantity = quantity
    transfer.save(update_fields=["quantity"])
    return transfer
