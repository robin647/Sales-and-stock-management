from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="moderator-product")
router.register("categories", views.CategoryViewSet, basename="moderator-category")
router.register("accounts", views.AccountViewSet, basename="moderator-account")
router.register("assets", views.AssetViewSet, basename="moderator-asset")

urlpatterns = [
    path("login/", views.ModeratorLoginView.as_view(), name="moderator-login"),
    path("logout/", views.logout, name="moderator-logout"),
    path("dashboard/", views.dashboard, name="moderator-dashboard"),
    path("downloads/bulk/", views.bulk, name="moderator-bulk"),
    *router.urls,
]
