from rest_framework.routers import DefaultRouter

from .views import DailyBalanceViewSet, DailyStockViewSet

router = DefaultRouter()
router.register("stocks", DailyStockViewSet, basename="daily-stock")
router.register("balances", DailyBalanceViewSet, basename="daily-balance")

urlpatterns = router.urls
