from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from .models import CostSpecification, OtherCost, Producer, ProducerCost, ProducerPayment


class ProducerFinancialModelTests(TestCase):
    def test_cost_and_payment_totals_are_computed(self):
        producer = Producer.objects.create(name="Alpha Producer", mobile_number="01700000000")
        ProducerCost.objects.create(
            producer=producer,
            bale_number="B-101",
            product_specification="Cotton Suit",
            quantity=Decimal("5"),
            rate=Decimal("100"),
            gst_percentage=Decimal("10"),
            transaction_date=timezone.now().date(),
        )
        ProducerPayment.objects.create(
            producer=producer,
            payment_date=timezone.now().date(),
            amount=Decimal("150"),
            payment_method="Cash",
            remarks="advance",
        )

        producer.refresh_from_db()
        self.assertEqual(producer.total_cost, Decimal("550.00"))
        self.assertEqual(producer.total_payments, Decimal("150.00"))
        self.assertEqual(producer.outstanding_balance, Decimal("400.00"))

    def test_other_costs_are_saved_and_totaled(self):
        transport = CostSpecification.objects.create(name="Transport")
        packaging = CostSpecification.objects.create(name="Packaging")

        OtherCost.objects.create(specification=transport, amount=Decimal("250"), cost_date=timezone.now().date())
        OtherCost.objects.create(specification=packaging, amount=Decimal("125"), cost_date=timezone.now().date())

        self.assertEqual(OtherCost.objects.count(), 2)
        self.assertEqual(sum((item.amount for item in OtherCost.objects.all()), Decimal("0.00")), Decimal("375.00"))
