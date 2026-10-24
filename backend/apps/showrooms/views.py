from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db.models.deletion import ProtectedError
from django.db import transaction

from apps.accounts.models import User
from apps.inventory.models import DailyBalance, DailyStock, ShowroomStock, StockAdjustment, StockTransfer
from apps.wholesale.models import (
    EasyWholesaleReturn,
    EasyWholesaleSale,
    EasyWholesaleStockMovement,
    WholesaleInvoice,
    WholesalePayment,
    WholesaleReturn,
    WholesaleSaleItem,
)

from core.permissions import IsAdmin

from .models import Showroom
from .serializers import ShowroomSerializer

class ShowroomViewSet(viewsets.ModelViewSet):
    """
    Admin: full CRUD over all showrooms.
    Showroom user: read-only access to their own showroom only (no listing others).
    """

    serializer_class = ShowroomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Showroom.objects.prefetch_related("users").all()
        return Showroom.objects.prefetch_related("users").filter(id=user.showroom_id)

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in permissions.SAFE_METHODS and request.user.role != "admin":
            raise PermissionDenied("Only Admin can manage showrooms.")

    @transaction.atomic
    def perform_destroy(self, instance):
        showroom_id = instance.pk

        # Remove showroom-linked wholesale records in dependency order because
        # these models intentionally protect their invoice and transaction links.
        invoice_ids = list(WholesaleInvoice.objects.filter(showroom_id=showroom_id).values_list("id", flat=True))
        invoice_item_ids = list(WholesaleSaleItem.objects.filter(invoice_id__in=invoice_ids).values_list("id", flat=True))
        easy_sale_ids = list(EasyWholesaleSale.objects.filter(showroom_id=showroom_id).values_list("id", flat=True))
        easy_return_ids = list(
            EasyWholesaleReturn.objects.filter(showroom_id=showroom_id)
            .values_list("id", flat=True)
        )
        easy_return_ids = list(set(easy_return_ids) | set(
            EasyWholesaleReturn.objects.filter(easy_sale_id__in=easy_sale_ids).values_list("id", flat=True)
        ))

        EasyWholesaleStockMovement.objects.filter(
            showroom_id=showroom_id
        ).delete()
        EasyWholesaleStockMovement.objects.filter(
            easy_sale_id__in=easy_sale_ids
        ).delete()
        EasyWholesaleStockMovement.objects.filter(
            easy_return_id__in=easy_return_ids
        ).delete()
        EasyWholesaleReturn.objects.filter(id__in=easy_return_ids).delete()
        EasyWholesaleSale.objects.filter(id__in=easy_sale_ids).delete()

        WholesaleReturn.objects.filter(invoice_item_id__in=invoice_item_ids).delete()
        WholesalePayment.objects.filter(invoice_id__in=invoice_ids).delete()
        WholesaleSaleItem.objects.filter(id__in=invoice_item_ids).delete()
        WholesaleInvoice.objects.filter(id__in=invoice_ids).delete()

        StockTransfer.objects.filter(showroom_id=showroom_id).delete()
        DailyStock.objects.filter(showroom_id=showroom_id).delete()
        DailyBalance.objects.filter(showroom_id=showroom_id).delete()
        StockAdjustment.objects.filter(showroom_id=showroom_id).delete()
        ShowroomStock.objects.filter(showroom_id=showroom_id).delete()

        # Remove the showroom login accounts after their owned records are gone.
        User.objects.filter(showroom_id=showroom_id, role=User.Role.SHOWROOM_USER).delete()
        try:
            instance.delete()
        except ProtectedError as exc:
            raise ValidationError("Could not delete this showroom because another record still references it.") from exc
