from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CostSpecificationViewSet,
    OtherCostViewSet,
    ProducerCostViewSet,
    ProducerExcelExportView,
    ProducerPaymentViewSet,
    ProducerViewSet,
)

router = DefaultRouter()
router.register("producers", ProducerViewSet, basename="producer")
router.register("producer-costs", ProducerCostViewSet, basename="producer-cost")
router.register("producer-payments", ProducerPaymentViewSet, basename="producer-payment")
router.register("other-costs", OtherCostViewSet, basename="other-cost")
router.register("cost-specifications", CostSpecificationViewSet, basename="cost-specification")

urlpatterns = [
    *router.urls,
    path("producers/export/", ProducerExcelExportView.as_view(), name="producer-export"),
]
