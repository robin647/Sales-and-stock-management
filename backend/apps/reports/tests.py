from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from .views import DashboardView


class AdminBusinessSummaryTests(SimpleTestCase):
    def test_all_time_summary_combines_business_totals_without_mixing_dues(self):
        lot_queryset = MagicMock()
        lot_queryset.aggregate.side_effect = [
            {"total": 50},
            {"total": 10},
        ]
        reject_queryset = MagicMock()
        reject_queryset.aggregate.return_value = {"total": 5}
        swing_payment_queryset = MagicMock()
        swing_payment_queryset.aggregate.return_value = {"total": 15}

        with (
            patch("apps.reports.views.DailyBalance.objects.aggregate", return_value={
                "sales": 100, "cash": 60, "card": 40, "expenses": 5, "salary": 4,
            }),
            patch("apps.reports.views.DailyStock.objects.aggregate", return_value={"total": 2}),
            patch("apps.reports.views.SalaryEntry.objects.aggregate", return_value={
                "base": 100, "absence": 10, "leave": 5, "overtime": 8,
                "bonus": 2, "advance": 3, "loan": 4, "other_deduction": 1,
            }),
            patch("apps.reports.views.SwingLot.objects.filter", return_value=lot_queryset),
            patch("apps.reports.views.SwingReject.objects.filter", return_value=reject_queryset),
            patch("apps.reports.views.SwingPayment.objects.filter", return_value=swing_payment_queryset),
            patch("apps.reports.views.ProducerCost.objects.filter") as producer_cost_filter,
            patch("apps.reports.views.ProducerPayment.objects.filter") as producer_payment_filter,
            patch("apps.reports.views.OtherCost.objects.filter") as other_cost_filter,
            patch("apps.reports.views.WholesalePayment.objects.aggregate", return_value={"total": 3}),
            patch("apps.reports.views.EasyWholesalePayment.objects.aggregate", return_value={"total": 2}),
        ):
            producer_cost_filter.return_value.aggregate.return_value = {"total": 30}
            producer_payment_filter.return_value.aggregate.return_value = {"total": 10}
            other_cost_filter.return_value.aggregate.return_value = {"total": 4}

            summary = DashboardView._all_time_summary({
                "total_sales": 20,
                "total_due": 6,
                "total_products": 3,
            })

        self.assertEqual(summary["costs"]["employee_salary"], 87)
        self.assertEqual(summary["total_cost"], 180)
        self.assertEqual(summary["total_sales"], 120)
        self.assertEqual(summary["sales"]["total_cash_received"], 65)
        self.assertEqual(summary["total_products_produced"], 10)
        self.assertEqual(summary["products_sold"]["total"], 5)
        self.assertEqual(summary["dues"], {
            "wholesale_receivable": 6,
            "swing_operator_payable": 30,
            "producer_payable": 20,
        })