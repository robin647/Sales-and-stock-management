from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CreateSalarySheetView,
    EmployeeViewSet,
    ExportSalarySheetView,
    OpenSalarySheetView,
    SalaryEntryViewSet,
    SalarySheetHistoryView,
)

router = DefaultRouter()
router.register("salary-entries", SalaryEntryViewSet, basename="salary-entry")
router.register("", EmployeeViewSet, basename="employee")

urlpatterns = [
    path("salary-sheets/", SalarySheetHistoryView.as_view(), name="salary-sheet-list"),
    path("salary-sheets/open/", OpenSalarySheetView.as_view(), name="salary-sheet-open"),
    path("salary-sheets/create/", CreateSalarySheetView.as_view(), name="salary-sheet-create"),
    path("salary-sheets/export/", ExportSalarySheetView.as_view(), name="salary-sheet-export"),
] + router.urls
