import json
from datetime import date,timedelta
from django.test import TestCase,Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Owner
from finance.models import FiscalYear,Entry,Line,Account,AuditEvent
from .models import Case,Quote,Reminder


class OperationsTests(TestCase):
    def setUp(self):
        self.manager=get_user_model().objects.create_user('manager',is_staff=True)
        self.client.force_login(self.manager)
        self.owner=Owner.objects.create(first_name='Alice',last_name='Test',email='alice@example.test')
        self.other=Owner.objects.create(first_name='Bruno',last_name='Privé')
        self.year=FiscalYear.objects.create(name='Année',starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        self.account=Account.objects.create(code='450000',name='Copropriétaires')
        self.line(self.owner,'100',1)
        self.line(self.other,'200',2)

    def line(self,owner,amount,number):
        entry=Entry.objects.create(year=self.year,number=number,date=timezone.localdate(),journal='OD',label=f'Mouvement {number}',created_by=self.manager)
        return Line.objects.create(entry=entry,owner=owner,account=self.account,debit=amount)

    def post(self,path,data,method='post',client=None):
        return getattr(client or self.client,method)('/api/operations/'+path+'/',json.dumps(data),content_type='application/json')

    def test_cases_documents_dates_and_budget_validation(self):
        response=self.post('cases',{'kind':'works','title':'Toiture','budget':'1200','status':'open','documents':[]})
        self.assertEqual(response.status_code,201,response.content)
        pk=response.json()['id']
        self.assertEqual(self.post(f'cases/{pk}',{'status':'archived'},'patch').status_code,200)
        self.assertEqual(self.post(f'cases/{pk}',{'status':'open'},'patch').status_code,200)
        self.assertEqual(self.post(f'cases/{pk}',{'budget':'-1'},'patch').status_code,400)
        self.assertEqual(self.post(f'cases/{pk}',{'source_url':'http://example.test'},'patch').status_code,400)

    def test_quotes_compared_and_selection_reversible(self):
        case=Case.objects.create(kind='works',title='Travaux',budget='1500',created_by=self.manager)
        self.assertEqual(self.post(f'cases/{case.id}/quotes',{'supplier':'A','amount':'1000'}).status_code,201)
        self.assertEqual(self.post(f'cases/{case.id}/quotes',{'supplier':'B','amount':'900'}).status_code,201)
        a,b=Quote.objects.order_by('id')
        self.assertEqual(self.post(f'quotes/{a.id}/select',{}).status_code,200)
        self.assertEqual(self.post(f'quotes/{b.id}/select',{}).status_code,400)
        self.assertEqual(self.post(f'quotes/{a.id}/select',{'selected':False}).status_code,200)
        self.assertEqual(self.post(f'quotes/{b.id}/select',{}).status_code,200)
        self.assertEqual(Entry.objects.count(),2)

    def test_metrics_deadline_window_and_no_false_overdue_debt(self):
        for title,days,status in [('Proche',2,'open'),('Retard',-1,'open'),('Lointain',60,'open'),('Terminé',-2,'done')]:
            Case.objects.create(kind='obligation',title=title,due_date=timezone.localdate()+timedelta(days=days),status=status,created_by=self.manager)
        data=self.client.get('/api/operations/metrics/').json()
        titles=[a['title'] for a in data['alerts']]
        self.assertIn('Proche',titles);self.assertIn('Retard',titles)
        self.assertNotIn('Lointain',titles);self.assertNotIn('Terminé',titles)
        self.assertEqual(data['debtor_count'],2)

    def test_reminder_evidence_edit_validation_and_declared_send(self):
        response=self.post('reminders',{'owner':self.owner.id})
        self.assertEqual(response.status_code,201,response.content)
        pk=response.json()['id'];self.assertEqual(response.json()['balance'],'100.00')
        self.assertEqual(self.post('reminders',{'owner':self.owner.id}).status_code,400)
        self.assertEqual(self.post(f'reminders/{pk}',{'status':'sent'},'patch').status_code,400)
        self.assertEqual(self.post(f'reminders/{pk}',{'text':'Texte relu'},'patch').status_code,200)
        self.assertEqual(self.post(f'reminders/{pk}',{'status':'approved'},'patch').status_code,200)
        self.assertEqual(self.post(f'reminders/{pk}',{'text':'Autre'},'patch').status_code,400)
        self.assertEqual(self.post(f'reminders/{pk}',{'status':'sent'},'patch').status_code,200)
        self.assertTrue(AuditEvent.objects.filter(action='reminder.prepare').exists())

    def test_stale_reminder_cannot_be_approved(self):
        pk=self.post('reminders',{'owner':self.owner.id}).json()['id']
        self.line(self.owner,'10',3)
        self.assertEqual(self.post(f'reminders/{pk}',{'status':'approved'},'patch').status_code,400)
        self.assertEqual(self.post(f'reminders/{pk}',{'status':'cancelled'},'patch').status_code,200)
        self.assertEqual(self.post('reminders',{'owner':self.owner.id}).status_code,201)

    def test_personal_account_cannot_choose_another_owner(self):
        user=get_user_model().objects.create_user('member')
        self.owner.user=user;self.owner.save()
        member=Client();member.force_login(user)
        response=member.get('/api/operations/my-account/',{'owner':self.other.id})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['balance'],'100.00')
        self.assertNotContains(response,'Mouvement 2')
        self.assertEqual(member.get('/api/operations/metrics/').status_code,403)
        self.assertEqual(member.get('/api/operations/cases/').status_code,403)
        self.assertEqual(member.get('/api/operations/reminders/').status_code,403)
        self.owner.must_change_password=True;self.owner.save()
        self.assertEqual(member.get('/api/operations/my-account/').status_code,403)

    def test_anonymous_endpoints_and_csrf_protected(self):
        for endpoint in ['cases','reminders','metrics','options','my-account']:
            self.assertEqual(Client().get('/api/operations/'+endpoint+'/').status_code,401)
        client=Client(enforce_csrf_checks=True);client.force_login(self.manager)
        self.assertEqual(self.post('cases',{'title':'Non autorisé'},client=client).status_code,403)
