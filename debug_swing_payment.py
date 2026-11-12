import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
import django
django.setup()

from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.swing.models import SwingOperator, SwingLot, SwingPayment

User.objects.all().delete(); SwingPayment.objects.all().delete(); SwingLot.objects.all().delete(); SwingOperator.objects.all().delete()
admin = User.objects.create_user(username='swing-admin', password='test-password', role=User.Role.ADMIN)
client = APIClient(); client.force_authenticate(user=admin)

op = client.post(reverse('swing-operator-list'), {'name': 'First', 'nid_number': ''}, format='json')
print('op', op.status_code, op.data)
opid = op.data['id']
lot = client.post(reverse('swing-lot-list'), {'operator': opid, 'lot_number': 'LOT-001', 'quantity': 500, 'fabric_specification': 'Navy cotton', 'rate': '10.00', 'cutting_master_name': 'Master A', 'lot_date': '2026-10-01'}, format='json')
print('lot', lot.status_code, lot.data)
payment = client.post(reverse('swing-payment-list'), {'operator': opid, 'payment_date': '2026-10-02', 'amount': '100.00'}, format='json')
print('payment create', payment.status_code, payment.data)
pid = payment.data['id']
updated = client.patch(reverse('swing-payment-detail', args=[pid]), {'amount': '250.00'}, format='json')
print('payment update', updated.status_code, updated.data)
print('payment record', SwingPayment.objects.get(pk=pid).amount)
