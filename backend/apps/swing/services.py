from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from .models import SwingReject


def rejected_quantity(lot, exclude_id=None):
    queryset = SwingReject.objects.filter(lot=lot, is_active=True)
    if exclude_id is not None:
        queryset = queryset.exclude(pk=exclude_id)
    return queryset.aggregate(total=Sum("quantity"))["total"] or 0


def validate_reject_capacity(lot, quantity, exclude_id=None):
    already_rejected = rejected_quantity(lot, exclude_id)
    if quantity + already_rejected > lot.quantity:
        available = max(lot.quantity - already_rejected, 0)
        raise ValidationError({"quantity": f"Reject quantity exceeds the lot's remaining available quantity ({available})."})


def validate_lot_capacity(lot, quantity):
    total_rejected = rejected_quantity(lot)
    if quantity < total_rejected:
        raise ValidationError({"quantity": f"Lot quantity cannot be less than its existing rejected quantity ({total_rejected})."})
