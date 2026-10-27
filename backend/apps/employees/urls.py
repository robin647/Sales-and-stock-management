from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CreateSalarySheetView, EmployeeViewSet, ExportSalarySheetView, SalaryEntryViewSet

router = DefaultRouter()
router.register("", EmployeeViewSet, basename="employee")
router.register("salary-entries", SalaryEntryViewSet, basename="salary-entry")

urlpatterns = [
    path("salary-sheets/create/", CreateSalarySheetView.as_view(), name="salary-sheet-create"),
    path("salary-sheets/export/", ExportSalarySheetView.as_view(), name="salary-sheet-export"),
] + router.urls
