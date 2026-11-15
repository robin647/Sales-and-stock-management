from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import record_view, WorkspaceView, DashboardView, OptionsView, PreferencesView, AuditViewSet, PublicView, CustomerHelpView
from .registry import MODULES

router = DefaultRouter()
for module in MODULES:
    router.register(module, record_view(module), basename="commerce-" + module)
router.register("audit", AuditViewSet, basename="commerce-audit")
urlpatterns = [
    path("workspace/", WorkspaceView.as_view()), path("dashboard/", DashboardView.as_view()),
    path("options/", OptionsView.as_view()), path("preferences/", PreferencesView.as_view()),
    path("public/", PublicView.as_view()), path("help/", CustomerHelpView.as_view()),
    path("", include(router.urls)),
]
