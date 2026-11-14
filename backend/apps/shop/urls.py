from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CouponViewSet, OrderViewSet, ShopSettingsView

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="online-order")
router.register("coupons", CouponViewSet, basename="shop-coupon")
urlpatterns = [path("settings/", ShopSettingsView.as_view(), name="shop-settings"), path("", include(router.urls))]
