from rest_framework.routers import DefaultRouter

from .views import SwingLotViewSet, SwingOperatorViewSet, SwingPaymentViewSet, SwingRejectViewSet

router = DefaultRouter()
router.register("operators", SwingOperatorViewSet, basename="swing-operator")
router.register("lots", SwingLotViewSet, basename="swing-lot")
router.register("payments", SwingPaymentViewSet, basename="swing-payment")
router.register("rejects", SwingRejectViewSet, basename="swing-reject")

urlpatterns = router.urls
