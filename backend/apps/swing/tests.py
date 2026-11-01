from decimal import Decimal
from io import BytesIO

from django.urls import reverse
from openpyxl import load_workbook
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import SwingLot, SwingOperator, SwingPayment, SwingReject


class SwingManagementApiTests(APITestCase):
    def setUp(self):
        admin = User.objects.create_user(
            username="swing-admin", password="test-password", role=User.Role.ADMIN
        )
        self.client.force_authenticate(user=admin)

    def create_operator(self, name="Operator One", nid_number=""):
        response = self.client.post(
            reverse("swing-operator-list"),
            {"name": name, "nid_number": nid_number},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def create_lot(self, operator_id, **overrides):
        payload = {
            "operator": operator_id,
            "lot_number": "LOT-001",
            "quantity": 500,
            "fabric_specification": "Navy cotton",
            "rate": "10.00",
            "cutting_master_name": "Master A",
            "lot_date": "2026-10-01",
        }
        payload.update(overrides)
        response = self.client.post(reverse("swing-lot-list"), payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_operator_search_update_and_safe_delete_preserve_history(self):
        operator = self.create_operator("Nusrat Operator", "NID-007")
        self.assertEqual(
            self.client.get(reverse("swing-operator-list"), {"search": "Nusr"}).data[0]["id"],
            operator["id"],
        )
        lot = self.create_lot(operator["id"])
        payment = self.client.post(
            reverse("swing-payment-list"),
            {"operator": operator["id"], "payment_date": "2026-10-02", "amount": "500.00"},
            format="json",
        )
        self.assertEqual(payment.status_code, 201, payment.data)

        updated = self.client.patch(
            reverse("swing-operator-detail", args=[operator["id"]]),
            {"name": "Nusrat Updated"}, format="json",
        )
        self.assertEqual(updated.status_code, 200)
        removed = self.client.delete(reverse("swing-operator-detail", args=[operator["id"]]))
        self.assertEqual(removed.status_code, 204)
        self.assertFalse(SwingOperator.objects.get(pk=operator["id"]).is_active)
        self.assertTrue(SwingLot.objects.filter(pk=lot["id"]).exists())
        self.assertTrue(SwingPayment.objects.filter(pk=payment.data["id"]).exists())

    def test_lot_reject_payment_statement_and_balance_recalculation(self):
        operator = self.create_operator()
        first_lot = self.create_lot(operator["id"])
        payment = self.client.post(
            reverse("swing-payment-list"),
            {"operator": operator["id"], "payment_date": "2026-10-02", "amount": "1000.00", "remarks": "Cash"},
            format="json",
        )
        self.assertEqual(payment.status_code, 201, payment.data)
        rejection = self.client.post(
            reverse("swing-reject-list"),
            {"lot": first_lot["id"], "quantity": 20, "reject_date": "2026-10-03", "remarks": "Damaged"},
            format="json",
        )
        self.assertEqual(rejection.status_code, 201, rejection.data)
        self.assertEqual(rejection.data["reject_amount"], "200.00")
        second_lot = self.create_lot(
            operator["id"], lot_number="LOT-002", quantity=100, rate="12.00", lot_date="2026-10-04"
        )

        statement = self.client.get(reverse("swing-operator-statement", args=[operator["id"]]))
        self.assertEqual(statement.status_code, 200, statement.data)
        self.assertEqual([row["event_type"] for row in statement.data["statement"]], ["lot", "payment", "reject", "lot"])
        self.assertEqual([row["bf_taka"] for row in statement.data["statement"]], [Decimal("0.00"), Decimal("5000.00"), Decimal("4000.00"), Decimal("3800.00")])
        self.assertEqual([row["due_taka"] for row in statement.data["statement"]], [Decimal("5000.00"), Decimal("4000.00"), Decimal("3800.00"), Decimal("5000.00")])
        self.assertEqual(statement.data["summary"], {
            "total_lots": 2,
            "total_products_assigned": 600,
            "total_rejected_quantity": 20,
            "total_accepted_quantity": 580,
            "total_sewing_amount": Decimal("6200.00"),
            "net_sewing_amount": Decimal("6000.00"),
            "total_payments_received": Decimal("1000.00"),
            "current_outstanding_balance": Decimal("5000.00"),
        })

        over_reject = self.client.post(
            reverse("swing-reject-list"),
            {"lot": first_lot["id"], "quantity": 481, "reject_date": "2026-10-05"},
            format="json",
        )
        self.assertEqual(over_reject.status_code, 400)

        changed = self.client.patch(
            reverse("swing-reject-detail", args=[rejection.data["id"]]),
            {"quantity": 30}, format="json",
        )
        self.assertEqual(changed.status_code, 200, changed.data)
        statement = self.client.get(reverse("swing-operator-statement", args=[operator["id"]]))
        self.assertEqual(statement.data["summary"]["current_outstanding_balance"], Decimal("4900.00"))

        deleted = self.client.delete(reverse("swing-lot-detail", args=[second_lot["id"]]))
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(SwingLot.objects.get(pk=second_lot["id"]).is_active)
        statement = self.client.get(reverse("swing-operator-statement", args=[operator["id"]]))
        self.assertEqual(statement.data["summary"]["total_lots"], 1)
        self.assertEqual(statement.data["summary"]["current_outstanding_balance"], Decimal("3700.00"))

    def test_rejects_are_lot_scoped_and_payment_edits_recalculate_balance(self):
        first_operator = self.create_operator("First")
        other_operator = self.create_operator("Other")
        first_lot = self.create_lot(first_operator["id"])
        other_lot = self.create_lot(other_operator["id"], lot_number="OTHER-LOT")
        rejects = self.client.get(reverse("swing-reject-list"), {"operator": first_operator["id"]})
        self.assertEqual(rejects.status_code, 200)
        self.assertEqual(rejects.data, [])

        payment = self.client.post(
            reverse("swing-payment-list"),
            {"operator": first_operator["id"], "payment_date": "2026-10-02", "amount": "100.00"},
            format="json",
        )
        self.assertEqual(payment.status_code, 201, payment.data)
        updated = self.client.patch(
            reverse("swing-payment-detail", args=[payment.data["id"]]),
            {"amount": "250.00"}, format="json",
        )
        self.assertEqual(updated.status_code, 200)
        statement = self.client.get(reverse("swing-operator-statement", args=[first_operator["id"]]))
        self.assertEqual(statement.data["summary"]["current_outstanding_balance"], Decimal("4750.00"))
        self.assertNotEqual(first_lot["operator"], other_lot["operator"])

        deleted_payment = self.client.delete(reverse("swing-payment-detail", args=[payment.data["id"]]))
        self.assertEqual(deleted_payment.status_code, 204)
        self.assertFalse(SwingPayment.objects.get(pk=payment.data["id"]).is_active)

    def test_editing_historical_lot_recalculates_amounts_and_preserves_valid_dates(self):
        operator = self.create_operator()
        lot = self.create_lot(operator["id"])
        rejection = self.client.post(
            reverse("swing-reject-list"),
            {"lot": lot["id"], "quantity": 20, "reject_date": "2026-10-03"},
            format="json",
        )
        self.assertEqual(rejection.status_code, 201, rejection.data)

        updated = self.client.patch(
            reverse("swing-lot-detail", args=[lot["id"]]),
            {"quantity": 600, "rate": "12.00", "lot_date": "2026-10-02"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        statement = self.client.get(reverse("swing-operator-statement", args=[operator["id"]]))
        self.assertEqual(statement.data["summary"]["total_sewing_amount"], Decimal("7200.00"))
        self.assertEqual(statement.data["summary"]["net_sewing_amount"], Decimal("6960.00"))
        self.assertEqual(statement.data["summary"]["current_outstanding_balance"], Decimal("6960.00"))

        invalid_date = self.client.patch(
            reverse("swing-lot-detail", args=[lot["id"]]),
            {"lot_date": "2026-10-04"},
            format="json",
        )
        self.assertEqual(invalid_date.status_code, 400)

        deleted_reject = self.client.delete(reverse("swing-reject-detail", args=[rejection.data["id"]]))
        self.assertEqual(deleted_reject.status_code, 204)
        statement = self.client.get(reverse("swing-operator-statement", args=[operator["id"]]))
        self.assertEqual(statement.data["summary"]["total_sewing_amount"], Decimal("7200.00"))
        self.assertEqual(statement.data["summary"]["net_sewing_amount"], Decimal("7200.00"))
        self.assertEqual(statement.data["summary"]["current_outstanding_balance"], Decimal("7200.00"))

    def test_showroom_users_cannot_access_swing_apis(self):
        showroom_user = User.objects.create_user(
            username="swing-showroom", password="test-password", role=User.Role.SHOWROOM_USER
        )
        self.client.force_authenticate(user=showroom_user)
        for path in (
            reverse("swing-summary"),
            reverse("swing-operators-export"),
            reverse("swing-operator-statement-export", args=[1]),
            reverse("swing-operator-list"),
            reverse("swing-lot-list"),
            reverse("swing-payment-list"),
            reverse("swing-reject-list"),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_dashboard_aggregates_active_operators_and_lot_rows_keep_rejections_grouped(self):
        operator = self.create_operator("Active operator")
        other = self.create_operator("Inactive operator")
        lot = self.create_lot(operator["id"], quantity=100, rate="12.50")
        self.create_lot(other["id"], quantity=900, rate="30.00", lot_number="INACTIVE-LOT")
        self.client.post(
            reverse("swing-reject-list"),
            {"lot": lot["id"], "quantity": 8, "reject_date": "2026-10-04"},
            format="json",
        )
        self.client.post(
            reverse("swing-payment-list"),
            {"operator": operator["id"], "payment_date": "2026-10-05", "amount": "200.00"},
            format="json",
        )
        SwingOperator.objects.filter(pk=other["id"]).update(is_active=False)

        dashboard = self.client.get(reverse("swing-summary"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["summary"], {
            "total_products_sewn": 100,
            "total_sewing_cost": Decimal("1250.00"),
            "total_payments_made": Decimal("200.00"),
            "total_outstanding_due": Decimal("950.00"),
        })
        self.assertEqual([row["id"] for row in dashboard.data["operators"]], [operator["id"]])

        statement = self.client.get(reverse("swing-operator-statement", args=[operator["id"]]))
        self.assertEqual(statement.data["lot_rows"], [{
            "lot_id": lot["id"],
            "event_date": statement.data["lot_rows"][0]["event_date"],
            "bf_taka": Decimal("0.00"),
            "colour": "Navy cotton",
            "lot_no": "LOT-001",
            "lot_qty": 100,
            "lot_rate": Decimal("12.50"),
            "total_tk": Decimal("1250.00"),
            "reject_qty": 8,
            "reject_tk": Decimal("100.00"),
            "receive_tk": Decimal("200.00"),
            "due_taka": Decimal("950.00"),
        }])

    def test_all_operator_and_operator_statement_xlsx_exports(self):
        operator = self.create_operator("Export Operator")
        lot = self.create_lot(operator["id"], lot_number="XLSX-LOT", quantity=50, rate="8.25")
        self.client.post(
            reverse("swing-reject-list"),
            {"lot": lot["id"], "quantity": 2, "reject_date": "2026-10-02"},
            format="json",
        )
        self.client.post(
            reverse("swing-payment-list"),
            {"operator": operator["id"], "payment_date": "2026-10-03", "amount": "100.00", "remarks": "Cash"},
            format="json",
        )

        all_export = self.client.get(reverse("swing-operators-export"))
        self.assertEqual(all_export.status_code, 200)
        self.assertEqual(all_export["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertIn("swing-all-operators.xlsx", all_export["Content-Disposition"])
        all_sheet = load_workbook(BytesIO(all_export.content), read_only=True).active
        self.assertEqual(next(all_sheet.iter_rows(values_only=True)), (
            "Operator Name", "Total Products", "Rejected Products", "Total Work Amount", "Total Paid", "Total Due",
        ))
        self.assertEqual(list(all_sheet.iter_rows(min_row=2, max_row=2, values_only=True))[0], (
            "Export Operator", 50, 2, Decimal("412.50"), Decimal("100.00"), Decimal("296.00"),
        ))

        statement_export = self.client.get(reverse("swing-operator-statement-export", args=[operator["id"]]))
        self.assertEqual(statement_export.status_code, 200)
        self.assertEqual(statement_export["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertIn(f"swing-operator-{operator['id']}-statement.xlsx", statement_export["Content-Disposition"])
        statement_sheet = load_workbook(BytesIO(statement_export.content), read_only=True).active
        self.assertEqual(statement_sheet["A1"].value, "Export Operator")
        self.assertEqual(tuple(cell.value for cell in statement_sheet[4]), (
            "Date", "B/F Taka", "Colour", "Lot No", "Lot QTY", "Lote Rate", "Total Tk",
            "Reject QTY", "Reject Tk", "Receive Tk", "Due Taka",
        ))
        lot_row = [cell.value for cell in statement_sheet[5]]
        self.assertEqual(lot_row[0].date().isoformat(), "2026-10-01")
        self.assertEqual(lot_row[1], 0)
        self.assertEqual(lot_row[2:5], ["Navy cotton", "XLSX-LOT", 50])
        self.assertEqual([Decimal(str(value)).quantize(Decimal("0.01")) for value in (lot_row[5], lot_row[6], lot_row[8], lot_row[9], lot_row[10])], [
            Decimal("8.25"), Decimal("412.50"), Decimal("16.50"), Decimal("100.00"), Decimal("296.00"),
        ])
        self.assertEqual(lot_row[7], 2)
