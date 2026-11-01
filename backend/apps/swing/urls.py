from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import (
	SwingDashboardSummaryView,
	SwingLotViewSet,
	SwingOperatorStatementExportView,
	SwingOperatorViewSet,
	SwingOperatorsExportView,
	SwingPaymentViewSet,
	SwingRejectViewSet,
)

router = DefaultRouter()
router.register("operators", SwingOperatorViewSet, basename="swing-operator")
router.register("lots", SwingLotViewSet, basename="swing-lot")
router.register("payments", SwingPaymentViewSet, basename="swing-payment")
router.register("rejects", SwingRejectViewSet, basename="swing-reject")

urlpatterns = [
	path("summary/", SwingDashboardSummaryView.as_view(), name="swing-summary"),
	path("operators/export/", SwingOperatorsExportView.as_view(), name="swing-operators-export"),
	path(
		"operators/<int:operator_id>/statement/export/",
		SwingOperatorStatementExportView.as_view(),
		name="swing-operator-statement-export",
	),
] + router.urls
