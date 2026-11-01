from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import (
	SwingDashboardSummaryView,
	SwingLotViewSet,
	SwingOperatorViewSet,
	SwingPaymentViewSet,
	SwingRejectViewSet,
)

router = DefaultRouter()
router.register("operators", SwingOperatorViewSet, basename="swing-operator")
router.register("lots", SwingLotViewSet, basename="swing-lot")
router.register("payments", SwingPaymentViewSet, basename="swing-payment")
router.register("rejects", SwingRejectViewSet, basename="swing-reject")

urlpatterns = [path("summary/", SwingDashboardSummaryView.as_view(), name="swing-summary")] + router.urls
