from django.urls import path
from rest_framework.routers import DefaultRouter
from .customers import CustomerViewSet

from .views import ChangePasswordView, CustomerSignupView, MeView, ShowroomUserDetailView, ShowroomUserListCreateView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("signup/", CustomerSignupView.as_view(), name="customer-signup"),
    path("password/change/", ChangePasswordView.as_view(), name="showroom-password-change"),
    path("showroom-users/", ShowroomUserListCreateView.as_view(), name="showroom-user-list"),
    path("showroom-users/<int:pk>/", ShowroomUserDetailView.as_view(), name="showroom-user-detail"),
]

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
urlpatterns += router.urls
