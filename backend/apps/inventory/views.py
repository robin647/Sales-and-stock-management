from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied

from .models import DailyBalance, DailyStock
from .serializers import DailyBalanceSerializer, DailyStockSerializer


class ShowroomScopedMixin:
    """
    Shared scoping rule used by both DailyStock and DailyBalance viewsets:
    - Admin sees everything, optionally filtered by ?showroom=<id>.
    - Showroom user only ever sees / writes their OWN showroom's data,
      no matter what showroom_id the client sends in the request body.
      This is the server-side enforcement required by the spec: a
      showroom user cannot access another showroom's data even if the
      frontend is tampered with.
    """

    def get_queryset(self):
        qs = self.queryset_base()
        user = self.request.user
        if user.role == "admin":
            showroom_id = self.request.query_params.get("showroom")
            if showroom_id:
                qs = qs.filter(showroom_id=showroom_id)
        else:
            qs = qs.filter(showroom_id=user.showroom_id)

        product_id = self.request.query_params.get("product")
        date = self.request.query_params.get("date")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if product_id:
            qs = qs.filter(product_id=product_id)
        if date:
            qs = qs.filter(date=date)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "admin":
            if not serializer.validated_data.get("showroom"):
                raise PermissionDenied("Admin must specify a showroom when creating an entry.")
            serializer.save()
        else:
            # Showroom user's own showroom is forced here — any showroom_id
            # sent from the client for this field is silently overridden.
            serializer.save(showroom=user.showroom)


class DailyStockViewSet(ShowroomScopedMixin, viewsets.ModelViewSet):
    serializer_class = DailyStockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def queryset_base(self):
        return DailyStock.objects.select_related("showroom", "product").all()


class DailyBalanceViewSet(ShowroomScopedMixin, viewsets.ModelViewSet):
    serializer_class = DailyBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def queryset_base(self):
        return DailyBalance.objects.select_related("showroom").all()
