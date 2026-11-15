from rest_framework.routers import DefaultRouter

from .views import ProductCategoryViewSet, ProductViewSet, OnlineProductViewSet

router = DefaultRouter()
router.register("categories", ProductCategoryViewSet, basename="product-category")
router.register("online", OnlineProductViewSet, basename="online-product")
router.register("", ProductViewSet, basename="product")

urlpatterns = router.urls
