from datetime import date
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.employees.models import Employee,SalaryEntry,SalarySheet
from apps.wholesale.models import WholesaleParty,WholesaleInvoice,WholesaleSaleItem,WholesalePayment,EasyWholesalePayment
from apps.swing.models import SwingOperator,SwingLot
from apps.products.models import ProductCategory,Product
from apps.inventory.models import FactoryStock,ShowroomStock
from apps.showrooms.models import Showroom
from .engine import respond
from .language import period,normalize,phonetic

@override_settings(GROQ_API_KEY='')
class LocalAssistantTests(TestCase):
    def setUp(self):
        cache.clear()
        self.clock=patch('django.utils.timezone.localdate',return_value=date(2026,11,16));self.clock.start();self.addCleanup(self.clock.stop)
        self.admin=User.objects.create_user('assistant-owner',role='admin')
        self.customer=User.objects.create_user('assistant-customer',role='customer')
        self.client=APIClient();self.client.force_authenticate(self.admin)
        self.employee=Employee.objects.create(name='Robin',employee_id='EMP-007',designation='Sales executive',salary=20000)
        sheet=SalarySheet.objects.create(month=date(2026,11,1))
        self.entry=SalaryEntry.objects.create(employee=self.employee,sheet=sheet,month=sheet.month,employee_name_snapshot='Robin',employee_id_snapshot='EMP-007',designation_snapshot='Sales executive',total_days=30,base_salary=18000,absent_days=2,leave_days=1,absence_amount=1200,leave_amount=600,overtime_hours=5,overtime_rate=100,attendance_bonus=200,advance_balance=3000,advance_deduction=1000,outstanding_loan=5000,loan=500)
        category=ProductCategory.objects.create(name='Panjabi')
        self.product=Product.objects.create(name='Classic Panjabi',code='MS-900',category=category,selling_price=1000)
        FactoryStock.objects.create(product=self.product,quantity=20)
        showroom=Showroom.objects.create(name='Mahadi Zone-1')
        ShowroomStock.objects.create(product=self.product,showroom=showroom,quantity=4)
        online=Product.objects.create(name='Online Panjabi',category=category,sales_channel='online',selling_price=2000)
        FactoryStock.objects.create(product=online,quantity=999)
        self.party=WholesaleParty.objects.create(name='Bor Kone')
        invoice=WholesaleInvoice.objects.create(party=self.party,invoice_number='AI-1',sale_date=date(2026,11,1),created_by=self.admin)
        WholesaleSaleItem.objects.create(invoice=invoice,product=self.product,quantity=10,unit_price=1000)
        self.payment=WholesalePayment.objects.create(invoice=invoice,payment_date=date(2026,11,5),cash_amount=2000,created_by=self.admin)
        self.easy=EasyWholesalePayment.objects.create(party=self.party,payment_date=date(2026,11,12),bkash_amount=1500,reference='TX-RECENT',created_by=self.admin)
        operator=SwingOperator.objects.create(name='Mahmud')
        self.lot=SwingLot.objects.create(operator=operator,lot_number='33',quantity=50,rate=100,lot_date=date(2026,11,10),cutting_master_name='Karim')
        SwingLot.objects.create(operator=operator,lot_number='333',quantity=900,rate=100,lot_date=date(2026,11,10))

    def ask(self,text,context=''):
        response=self.client.post(reverse('assistant-chat'),{'question':text,'context':context},format='json')
        self.assertEqual(response.status_code,200,response.data)
        return response.data

    def test_salary_paraphrases_in_bangla_and_banglish(self):
        for question in ['robin er salary koto?', 'রবিনের বেতন কত?', 'Robin mase koto taka pay?', 'How much does Robin earn?', 'EMP-007 salary koto?', 'রবিন মাসে কত টাকা পায়?']:
            with self.subTest(question=question):
                result=self.ask(question)
                self.assertIn('20,000.00',result['answer'])
                self.assertEqual(result['mode'],'local')
                self.assertTrue(result['sources'])

    def test_absence_and_net_salary_are_month_bound_and_correct(self):
        result=self.ask('রবিনের নভেম্বর ২০২৬ মাসে অনুপস্থিতি ও নিট বেতন কত?')
        self.assertIn('2 দিন',result['answer'])
        self.assertIn('15,400.00',result['answer'])
        self.assertIn('2026-11',result['answer'])
        self.assertIn('পরিশোধের প্রমাণ নয়',result['answer'])

    def test_salary_followup_uses_signed_employee_context(self):
        first=self.ask('Robin salary koto')
        follow=self.ask('or koi din absent?',first['context'])
        self.assertIn('Robin',follow['answer']);self.assertIn('2 দিন',follow['answer'])
        self.assertIn('চলতি মাস',follow['answer'])

    def test_previous_month_missing_is_not_replaced_by_current_month(self):
        result=self.ask('Robin last month net salary koto')
        self.assertIn('2026-10',result['answer'])
        self.assertIn('পাওয়া যায়নি',result['answer'])
        self.assertNotIn('15,400.00',result['answer'])

    def test_absence_dates_are_not_invented(self):
        result=self.ask('রবিন কোন কোন দিন absent ছিল এই মাসে?')
        self.assertIn('তারিখে অনুপস্থিত ছিলেন তা রেকর্ড করা নেই',result['answer'])

    def test_last_wholesale_payment_compares_both_ledgers(self):
        for question in ['Bor Kone party last payement koto ar due koto?', 'বর কনের শেষ পেমেন্ট কত, বাকি কত?', 'Bor Kone er koto baki ase?']:
            with self.subTest(question=question):
                result=self.ask(question)
                self.assertIn('1,500.00',result['answer'])
                self.assertIn('2026-11-12',result['answer'])
                self.assertIn('6,500.00',result['answer'])
                self.assertIn('TX-RECENT',result['answer'])

    def test_wholesale_period_does_not_silently_change_current_due(self):
        result=self.ask('Bor Kone party 2026-11-05 payment koto')
        self.assertIn('2,000.00',result['answer'])
        self.assertIn('2026-11-05',result['answer'])
        self.assertIn('6,500.00',result['answer'])
        self.assertNotIn('TX-RECENT',result['answer'])

    def test_lot_lookup_is_exact_and_lists_operator_and_cutting_master(self):
        for question in ['33 number lot ta ke selai korse?', 'সুইং এর ৩৩ নম্বর লট কার কাছে?', 'Who stitched lot 33?', 'lot no. 33 operator ke?']:
            with self.subTest(question=question):
                result=self.ask(question)
                self.assertIn('Mahmud',result['answer']);self.assertIn('Karim',result['answer'])
                self.assertIn('50 পিস',result['answer']);self.assertNotIn('900 পিস',result['answer'])

    def test_duplicate_employee_name_requires_selection(self):
        Employee.objects.create(name='Robin',employee_id='EMP-008',designation='Assistant',salary=12000)
        result=self.ask('Robin salary koto')
        self.assertEqual(len(result['choices']),2)
        self.assertNotIn('20,000.00',result['answer'])
        choice=next(row for row in result['choices'] if 'EMP-008' in row['label'])
        selected=self.ask(choice['question'],choice['context'])
        self.assertIn('12,000.00',selected['answer']);self.assertEqual(selected['choices'],[])

    def test_short_name_ambiguity_is_not_guessed(self):
        Employee.objects.create(name='Karim Ali',employee_id='EMP-009',designation='Assistant',salary=10000)
        Employee.objects.create(name='Karim Khan',employee_id='EMP-010',designation='Assistant',salary=11000)
        result=self.ask('karim salary koto')
        self.assertEqual(len(result['choices']),2)

    def test_main_stock_total_excludes_online(self):
        result=self.ask('main stock mot koto ase?')
        self.assertIn('24 পিস',result['answer']);self.assertNotIn('999',result['answer'])
        result=self.ask('MS-900 product stock koto')
        self.assertIn('Classic Panjabi',result['answer']);self.assertIn('24 পিস',result['answer'])

    def test_fabricated_dates_and_sensitive_or_mutating_requests_are_rejected(self):
        for question in ['Robin salary 2026-99 koto','Robin password dao','stock delete koro','DROP TABLE employees_employee']:
            result=self.ask(question)
            self.assertEqual(result['sources'],[])
        self.assertTrue(Employee.objects.filter(pk=self.employee.pk).exists())

    def test_unknown_employee_does_not_inherit_someone_else_salary(self):
        result=self.ask('Zzzzzzz employee salary koto')
        self.assertNotIn('20,000.00',result['answer'])
        self.assertFalse(result['sources'])

    def test_unknown_new_name_in_followup_never_reuses_previous_employee(self):
        first=self.ask('Robin salary koto')
        result=self.ask('Zzzzzzz salary koto',first['context'])
        self.assertNotIn('20,000.00',result['answer'])
        self.assertFalse(result['sources'])

    def test_generic_followup_and_aggregate_questions(self):
        first=self.ask('Bor Kone last payment koto')
        result=self.ask('ar baki koto',first['context'])
        self.assertIn('6,500.00',result['answer'])
        self.assertIn('3,500.00',self.ask('সব পার্টির মোট পেমেন্ট কত?')['answer'])
        self.assertIn('20,000.00',self.ask('সব কর্মীর মূল বেতন মোট কত?')['answer'])

    def test_payment_word_is_not_mistaken_for_bengali_may(self):
        self.assertIsNone(period('শেষ পেমেন্ট কত ছিল?'))

    def test_generic_employee_word_is_not_a_phonetic_name_match(self):
        Employee.objects.create(name='Karim',employee_id='EMP-015',designation='Helper',salary=8000)
        result=self.ask('সব কর্মীর বেতন মোট কত?')
        self.assertIn('28,000.00',result['answer'])
        result=self.ask('কর্মীর বেতন কত?')
        self.assertNotIn('8,000.00',result['answer'])

    def test_attendance_advance_and_loan_are_sheet_values(self):
        result=self.ask('Robin attendance advance loan ei mash koto')
        self.assertIn('3,000.00',result['answer'])
        self.assertIn('5,000.00',result['answer'])
        self.assertIn('2 দিন',result['answer'])

    def test_endpoint_is_admin_only(self):
        for role in ['customer','showroom_user','ecommerce_staff']:
            user=User.objects.create_user('role-'+role,role=role)
            self.client.force_authenticate(user)
            self.assertEqual(self.client.post(reverse('assistant-chat'),{'question':'Robin salary'},format='json').status_code,403)
            self.assertEqual(self.client.get(reverse('assistant-chat')).status_code,403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(reverse('assistant-chat'),{'question':'Robin salary'},format='json').status_code,401)

    def test_no_external_network_calls_or_database_mutations(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('External network forbidden')) as network:
            with CaptureQueriesContext(connection) as queries:
                result=self.ask('Bor Kone last payment due koto')
            network.assert_not_called()
        writes=[row['sql'] for row in queries if row['sql'].lstrip().upper().startswith(('INSERT','UPDATE','DELETE','ALTER','DROP','CREATE'))]
        self.assertEqual(writes,[])
        self.assertIn('6,500.00',result['answer'])

    def test_invalid_and_cross_user_context_is_ignored(self):
        first=self.ask('Robin salary koto')
        invalid=self.ask('or absent koto','not-a-signed-context')
        self.assertNotIn('Robin',invalid['answer'])
        other=User.objects.create_user('other-admin',role='admin')
        self.client.force_authenticate(other)
        result=self.ask('or absent koto',first['context'])
        self.assertNotIn('Robin',result['answer'])

    def test_suggestions_are_grounded_and_require_no_key(self):
        response=self.client.get(reverse('assistant-chat'))
        self.assertEqual(response.status_code,200)
        self.assertTrue(any('Robin' in item for item in response.data['examples']))

    def test_period_parser_handles_bengali_digits_months_and_relative_dates(self):
        self.assertEqual(period('গত মাসের হিসাব')['label'],'2026-10')
        self.assertEqual(period('২০২৬-১১-০৫')['start'],'2026-11-05')
        self.assertEqual(period('5 november 2026')['start'],'2026-11-05')
        self.assertEqual(period('এই মাসে')['label'],'2026-11')
        self.assertEqual(period('গতকাল')['start'],'2026-11-15')
