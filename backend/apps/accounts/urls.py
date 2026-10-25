from django.urls import path

from .views import ChangePasswordView, MeView, ShowroomUserDetailView, ShowroomUserListCreateView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("password/change/", ChangePasswordView.as_view(), name="showroom-password-change"),
    path("showroom-users/", ShowroomUserListCreateView.as_view(), name="showroom-user-list"),
    path("showroom-users/<int:pk>/", ShowroomUserDetailView.as_view(), name="showroom-user-detail"),
]
