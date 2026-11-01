from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import Employee, SalaryEntry, SalarySheet


class EmployeeManagementApiTests(APITestCase):
    def setUp(self):
        admin = User.objects.create_user(
            username="employee-admin",
            password="test-password",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=admin)
        self.employees_url = reverse("employee-list")

    def create_employee(self, employee_id="EMP-001", **overrides):
        payload = {
            "name": "Test Employee",
            "employee_id": employee_id,
            "nid_number": "NID-001" if employee_id == "EMP-001" else "",
            "designation": "Tailor",
            "salary": "30000.00",
        }
        payload.update(overrides)
        response = self.client.post(self.employees_url, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def create_sheet(self, month="2026-11"):
        rest_framework_settings = {
            **settings.REST_FRAMEWORK,
            "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
        }
        with override_settings(REST_FRAMEWORK=rest_framework_settings):
            response = self.client.post(
                reverse("salary-sheet-create"), {"month": month}, format="json"
            )
        self.assertEqual(response.status_code, 200, response.data)
        return response

    def test_employee_crud_search_and_soft_delete_preserves_salary_history(self):
        employee = self.create_employee()
        self.create_employee(
            "EMP-002", name="Another Worker", nid_number="NID-002"
        )

        response = self.client.get(self.employees_url, {"search": "NID-002"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["employee_id"] for row in response.data], ["EMP-002"], response.data)

        self.create_sheet()
        response = self.client.patch(
            reverse("employee-detail", kwargs={"pk": employee["id"]}),
            {"designation": "Senior Tailor"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["designation"], "Senior Tailor")

        response = self.client.delete(
            reverse("employee-detail", kwargs={"pk": employee["id"]})
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Employee.objects.get(pk=employee["id"]).is_active)
        self.assertEqual(self.client.get(self.employees_url).data[0]["employee_id"], "EMP-002")
        entry = SalaryEntry.objects.get(employee_id=employee["id"])
        self.assertEqual(entry.employee_name_snapshot, "Test Employee")
        self.assertEqual(entry.designation_snapshot, "Tailor")

    def test_duplicate_employee_id_and_nid_are_rejected(self):
        self.create_employee()
        duplicate_id = self.client.post(
            self.employees_url,
            {"name": "Duplicate", "employee_id": "EMP-001", "designation": "OP", "salary": "1000"},
            format="json",
        )
        self.assertEqual(duplicate_id.status_code, 400)

        duplicate_nid = self.client.post(
            self.employees_url,
            {"name": "Duplicate NID", "employee_id": "EMP-003", "nid_number": "NID-001", "designation": "OP", "salary": "1000"},
            format="json",
        )
        self.assertEqual(duplicate_nid.status_code, 400)

    def test_employee_and_payroll_apis_remain_admin_only(self):
        showroom_user = User.objects.create_user(
            username="employee-showroom-user",
            password="test-password",
            role=User.Role.SHOWROOM_USER,
        )
        self.client.force_authenticate(user=showroom_user)

        protected_gets = [
            self.employees_url,
            reverse("salary-entry-list"),
            reverse("salary-sheet-list"),
            reverse("salary-sheet-export"),
        ]
        for path in protected_gets:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

        self.assertEqual(
            self.client.post(
                reverse("salary-sheet-create"), {"month": "2026-11"}, format="json"
            ).status_code,
            403,
        )

    def test_month_sheet_is_unique_and_snapshots_employee_profile(self):
        employee = self.create_employee()
        first = self.create_sheet()
        second = self.create_sheet()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data[0]["id"], second.data[0]["id"])
        self.assertEqual(SalarySheet.objects.filter(month="2026-11-01").count(), 1)

        self.client.patch(
            reverse("employee-detail", kwargs={"pk": employee["id"]}),
            {"name": "Changed Name", "designation": "Manager", "salary": "45000"},
            format="json",
        )
        response = self.client.get(reverse("salary-entry-list"), {"month": "2026-11"})
        self.assertEqual(response.data[0]["employee_name"], "Test Employee")
        self.assertEqual(response.data[0]["designation"], "Tailor")
        self.assertEqual(response.data[0]["base_salary"], "30000.00")

        history = self.client.get(reverse("salary-sheet-list"))
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data[0]["month"], "2026-11")
        self.assertEqual(history.data[0]["entry_count"], 1)

    def test_payroll_calculation_and_manual_adjustments(self):
        self.create_employee()
        response = self.create_sheet()
        entry_id = response.data[0]["id"]
        update_url = reverse("salary-entry-detail", kwargs={"pk": entry_id})
        response = self.client.patch(
            update_url,
            {
                "absent_days": 2,
                "leave_days": 1,
                "leave_amount": "500.00",
                "overtime_hours": "2.00",
                "overtime_rate": "100.00",
                "attendance_bonus": "50.00",
                "advance_balance": "1000.00",
                "advance_deduction": "300.00",
                "outstanding_loan": "5000.00",
                "loan": "100.00",
                "other_deduction": "25.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["per_day_rate"], "1000.00")
        self.assertEqual(response.data["absence_amount"], "2000.00")
        self.assertEqual(response.data["net_salary"], "27325.00")

        response = self.client.patch(
            update_url,
            {"absent_days": 3, "absence_amount": "2500.00", "leave_amount": "-500.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["absence_amount"], "2500.00")
        self.assertEqual(response.data["net_salary"], "27825.00")

        invalid_days = self.client.patch(
            update_url, {"absent_days": 30, "leave_days": 1}, format="json"
        )
        self.assertEqual(invalid_days.status_code, 400)

    def test_deleting_salary_row_preserves_sheet_and_other_months(self):
        employee = self.create_employee()
        november = self.create_sheet("2026-11").data[0]
        december = self.create_sheet("2026-12").data[0]

        response = self.client.delete(
            reverse("salary-entry-detail", kwargs={"pk": november["id"]})
        )
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Employee.objects.filter(pk=employee["id"], is_active=True).exists())
        self.assertTrue(SalaryEntry.objects.filter(pk=december["id"]).exists())
        self.assertTrue(SalarySheet.objects.filter(month="2026-11-01").exists())
        history = self.client.get(reverse("salary-sheet-list"))
        self.assertEqual({row["month"] for row in history.data}, {"2026-11", "2026-12"})

    def test_export_is_formatted_xlsx_with_totals(self):
        self.create_employee()
        response = self.create_sheet("2026-11")
        self.client.patch(
            reverse("salary-entry-detail", kwargs={"pk": response.data[0]["id"]}),
            {"overtime_hours": "2", "overtime_rate": "100", "attendance_bonus": "50", "loan": "100"},
            format="json",
        )
        response = self.client.get(
            reverse("salary-sheet-export"), {"month": "2026-11"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        workbook = load_workbook(BytesIO(response.content), data_only=True)
        sheet = workbook.active
        self.assertEqual(sheet["A1"].value, "Monthly Salary Sheet - November 2026")
        self.assertEqual(sheet["A4"].value, "Employee ID")
        self.assertEqual(sheet["S4"].value, "Total Salary")
        self.assertEqual(sheet["S5"].value, 30150)
        self.assertEqual(sheet["A6"].value, "TOTAL")
        self.assertEqual(sheet["S6"].value, 30150)
        self.assertEqual(sheet["A8"].value, "Basic Salary")
        self.assertEqual(sheet["B8"].value, 30000)
        self.assertEqual(sheet["D8"].value, "Deductions")
        self.assertEqual(sheet["E8"].value, 100)
        self.assertEqual(sheet["G8"].value, "Overtime")
        self.assertEqual(sheet["H8"].value, 200)
        self.assertEqual(sheet["J8"].value, "Bonuses")
        self.assertEqual(sheet["K8"].value, 50)
        self.assertEqual(sheet["M8"].value, "Payable")
        self.assertEqual(sheet["N8"].value, 30150)
        self.assertEqual(sheet.freeze_panes, "A5")
