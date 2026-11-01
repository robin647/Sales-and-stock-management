from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import Employee


class EmployeeManagementApiTests(APITestCase):
    def setUp(self):
        admin = User.objects.create_user(
            username="employee-admin",
            password="test-password",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=admin)

    def test_employee_crud_keeps_salary_history_on_delete(self):
        list_url = reverse("employee-list")
        response = self.client.post(
            list_url,
            {
                "name": "Test Employee",
                "employee_id": "EMP-001",
                "designation": "Tailor",
                "salary": "30000.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        employee_id = response.data["id"]

        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        response = self.client.patch(
            reverse("employee-detail", kwargs={"pk": employee_id}),
            {"designation": "Senior Tailor"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["designation"], "Senior Tailor")

        response = self.client.delete(
            reverse("employee-detail", kwargs={"pk": employee_id})
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Employee.objects.get(pk=employee_id).is_active)
        self.assertEqual(self.client.get(list_url).data, [])

    def test_salary_sheet_routes_and_payroll_update(self):
        employee = Employee.objects.create(
            name="Test Employee",
            employee_id="EMP-002",
            designation="Tailor",
            salary=Decimal("30000.00"),
        )
        create_url = reverse("salary-sheet-create")
        response = self.client.post(create_url, {"month": "2026-11"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["total_days"], 30)

        entry_id = response.data[0]["id"]
        list_url = reverse("salary-entry-list")
        response = self.client.get(list_url, {"month": "2026-11"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["employee_id"], employee.employee_id)

        response = self.client.patch(
            reverse("salary-entry-detail", kwargs={"pk": entry_id}),
            {
                "absent_days": 2,
                "leave_days": 1,
                "overtime_hours": "2.00",
                "overtime_rate": "100.00",
                "attendance_bonus": "50.00",
                "loan": "100.00",
                "other_deduction": "25.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["net_salary"], "29125.00")

        response = self.client.get(
            reverse("salary-sheet-export"), {"month": "2026-11"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"EMP-002", response.content)

    def test_salary_entry_path_does_not_match_employee_detail(self):
        response = self.client.get(reverse("salary-entry-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
