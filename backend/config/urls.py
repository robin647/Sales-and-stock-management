from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import CustomTokenObtainPairView, ShowroomLoginView
from config.views import api_status

urlpatterns = [
    path("", api_status, name="root-status"),
    path("api/health/", lambda request: JsonResponse({"status": "ok"}), name="health"),
    path("admin/", admin.site.urls),
    path("api/auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/login/showroom/", ShowroomLoginView.as_view(), name="showroom_login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/showrooms/", include("apps.showrooms.urls")),
    path("api/products/", include("apps.products.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/wholesale/", include("apps.wholesale.urls")),
    path("api/employees/", include("apps.employees.urls")),
]
