import json
import uuid
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, Client
from core.models import Owner
from documents.models import Document
from operations.models import Supplier
from .models import Account, BankAccount, BankTransfer, FiscalYear, ChargeKey, Expense, ExpensePayment, Receipt, Entry, Line, AuditEvent, Budget, Organization, CostCenter
from .services import open_year, post_entry


class BankingSupplierTests(TestCase):
    def setUp(self):
        self.manager=get_user_model().objects.create_user('manager',is_staff=True)
        self.client.force_login(self.manager)
        self.year=FiscalYear.objects.create(name='2026',starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        self.key=ChargeKey.objects.create(name='Charges générales')
        self.supplier=Supplier.objects.create(name='Entreprise A',created_by=self.manager)
        self.owner=Owner.objects.create(first_name='Alice',last_name='Test',email='alice@example.test')
        self.member_user=get_user_model().objects.create_user('member')
        self.owner.user=self.member_user;self.owner.save()
        self.member=Client();self.member.force_login(self.member_user)

    def send(self,path,body,method='post',client=None):
        return getattr(client or self.client,method)('/api/finance/'+path+'/',json.dumps(body),content_type='application/json')

    def bank(self,code='5121',**extra):
        response=self.send('banks',{'name':f'Banque {code}','account_code':code,**extra})
        self.assertEqual(response.status_code,201,response.content)
        return BankAccount.objects.get(pk=response.json()['id'])

    def invoice(self,**extra):
        response=self.send('expenses',{'year':self.year.pk,'key':self.key.pk,'supplier_record':self.supplier.pk,'reference':'F001','label':'Entretien','date':'2026-01-05','amount':'100',**extra})
        return response

    def transfer(self,source_bank,destination_bank,**extra):
        return self.send('bank-transfers',{'request_id':str(uuid.uuid4()),'year':self.year.pk,'date':'2026-02-01','source':source_bank.pk,'destination':destination_bank.pk,'amount':'20','reference':'V001',**extra})

    def entry(self,rows,year=None,day='2026-01-01'):
        with transaction.atomic():
            year=open_year((year or self.year).pk,date.fromisoformat(day))
            return post_entry(year,date.fromisoformat(day),'OD','Test',rows,self.manager)

    def test_bank_creation_associates_existing_movements_without_reposting(self):
        self.entry([{'code':'512','debit':'100'},{'code':'701','credit':'100'}])
        before=Entry.objects.count()
        bank=self.bank('512',iban='FR76 3000 6000 0112 3456 7890 189')
        self.assertTrue(bank.is_default)
        self.assertEqual(bank.iban,'FR7630006000011234567890189')
        data=self.client.get('/api/finance/banks/',{'date':'2026-01-31'}).json()
        self.assertEqual(data['items'][0]['balance'],'100.00')
        self.assertEqual(data['unassigned'],[])
        self.assertEqual(Entry.objects.count(),before)

    def test_unassigned_bank_accounts_and_date_filter_remain_visible(self):
        self.entry([{'code':'512','debit':'100'},{'code':'701','credit':'100'}])
        self.entry([{'code':'512','debit':'50'},{'code':'701','credit':'50'}],day='2026-02-01')
        row=self.client.get('/api/finance/banks/',{'date':'2026-01-31'}).json()['unassigned'][0]
        self.assertEqual(row['code'],'512');self.assertEqual(row['balance'],'100.00')
        self.assertEqual(self.client.get('/api/finance/banks/',{'date':'bad'}).status_code,400)
        self.assertEqual(self.client.get('/api/finance/banks/99999/').status_code,404)

    def test_bank_validation_defaults_edit_and_unique_account(self):
        for invalid in [{'account_code':'401'},{'account_code':'512x'},{'iban':'not-an-iban'},{'kind':'other'},{'active':'false'},{'unknown':True}]:
            response=self.send('banks',{'name':'Banque','account_code':'5121',**invalid})
            self.assertEqual(response.status_code,400,(invalid,response.content))
        self.assertFalse(BankAccount.objects.exists())
        bank=self.bank()
        self.assertEqual(self.send('banks',{'name':'Doublon','account_code':'5121'}).status_code,400)
        self.assertEqual(self.send(f'banks/{bank.pk}',{'name':'Nom corrigé'},'patch').status_code,200)
        self.assertEqual(self.send(f'banks/{bank.pk}',{'account_code':'5122'},'patch').status_code,400)
        self.assertEqual(self.send(f'banks/{bank.pk}',{'active':False},'patch').status_code,400)
        second=self.bank('5122',kind='works')
        self.assertEqual(self.send(f'banks/{second.pk}/default',{}).status_code,200)
        self.assertEqual(BankAccount.objects.filter(is_default=True).count(),1)
        self.assertEqual(self.send(f'banks/{bank.pk}',{'active':False},'patch').status_code,200)
        self.assertEqual(self.send(f'banks/{bank.pk}/default',{}).status_code,400)
        self.assertEqual(self.send(f'manage/accounts/{second.account_id}',{'code':'5123'},'patch').status_code,400)

    def test_first_active_bank_after_inactive_setup_becomes_default(self):
        inactive=self.bank('5121',active=False)
        self.assertFalse(inactive.is_default)
        self.assertEqual(self.client.get('/api/finance/banks/').json()['unassigned'],[])
        active=self.bank('5122')
        self.assertTrue(active.is_default)
        body={'year':self.year.pk,'owner':self.owner.pk,'date':'2026-01-10','amount':'25'}
        self.assertEqual(self.send('receipts',body).status_code,201)
        self.assertEqual(Receipt.objects.get().bank,active)

    def test_bank_transfer_balances_and_preserves_global_treasury(self):
        source=self.bank('512');destination=self.bank('5122',kind='savings')
        self.entry([{'code':'512','debit':'100'},{'code':'701','credit':'100'}])
        response=self.transfer(source,destination)
        self.assertEqual(response.status_code,201,response.content)
        transfer=BankTransfer.objects.get()
        self.assertEqual(transfer.entry.lines.get(account=source.account).credit,Decimal('20'))
        self.assertEqual(transfer.entry.lines.get(account=destination.account).debit,Decimal('20'))
        data=self.client.get('/api/finance/banks/',{'date':'2026-02-01'}).json()
        balances={b['account_code']:b['balance'] for b in data['items']}
        self.assertEqual(balances,{'512':'80.00','5122':'20.00'})
        summary=self.client.get('/api/finance/treasury/').json()['items'][0]
        self.assertEqual(summary['treasury_movement'],'100.00')
        self.assertTrue(AuditEvent.objects.filter(action='bank.transfer').exists())
        self.assertEqual(self.send(f'operations/reverse-entry/{transfer.entry_id}',{'date':'2026-02-02'}).status_code,400)

    def test_transfer_retries_are_idempotent_and_changed_payload_rejected(self):
        source=self.bank();destination=self.bank('5122');operation=str(uuid.uuid4())
        first=self.transfer(source,destination,request_id=operation)
        self.assertEqual(first.status_code,201,first.content)
        retry=self.transfer(source,destination,request_id=operation)
        self.assertEqual(retry.status_code,200,retry.content)
        self.assertEqual(first.json()['id'],retry.json()['id'])
        self.assertEqual(BankTransfer.objects.count(),1)
        self.assertEqual(Entry.objects.count(),1)
        self.assertEqual(self.transfer(source,destination,request_id=operation,amount='21').status_code,400)

    def test_transfers_reject_invalid_banks_dates_amounts_and_lock_exercise(self):
        source=self.bank();destination=self.bank('5122')
        for invalid in [{'destination':source.pk},{'amount':'-1'},{'amount':'NaN'},{'amount':'1.001'},
                        {'date':'2027-01-01'},{'source':True},{'destination':99999},{'request_id':'invalid'}]:
            self.assertEqual(self.transfer(source,destination,**invalid).status_code,400,invalid)
        self.assertEqual(BankTransfer.objects.count(),0)
        self.assertEqual(Entry.objects.count(),0)
        self.year.refresh_from_db();self.assertEqual(self.year.next_entry,1)
        self.year.closed=True;self.year.save()
        self.assertEqual(self.transfer(source,destination).status_code,400)

    def test_transfer_analytic_requirement_and_inactive_accounts(self):
        source=self.bank();destination=self.bank('5122')
        Organization.objects.update_or_create(pk=1,defaults={'analytic_required':True})
        self.assertEqual(self.transfer(source,destination).status_code,400)
        center=CostCenter.objects.create(name='Global')
        self.assertEqual(self.transfer(source,destination,cost_center=center.pk).status_code,201)
        destination.account.active=False;destination.account.save()
        self.assertEqual(self.transfer(source,destination,cost_center=center.pk).status_code,400)
        self.assertEqual(Entry.objects.count(),1)

    def test_expense_records_supplier_document_and_balanced_supplier_line(self):
        document=Document.objects.create(title='Facture')
        response=self.invoice(document=document.pk)
        self.assertEqual(response.status_code,201,response.content)
        expense=Expense.objects.get()
        self.assertEqual(expense.supplier,'Entreprise A')
        self.assertEqual(expense.supplier_record,self.supplier)
        self.assertEqual(expense.document,document)
        line=expense.entry.lines.get(account__code='401')
        self.assertEqual(line.supplier,self.supplier)
        self.assertEqual(line.credit,Decimal('100'))
        row=self.client.get('/api/finance/expenses/').json()['items'][0]
        self.assertEqual(row['supplier_record'],self.supplier.pk)
        self.assertEqual(row['document'],document.pk)

    def test_invoice_duplicate_after_supplier_rename_does_not_post(self):
        self.assertEqual(self.invoice().status_code,201)
        self.supplier.name='Entreprise renommée';self.supplier.save()
        self.assertIn(self.invoice().status_code,[400,409])
        self.assertEqual(Expense.objects.count(),1);self.assertEqual(Entry.objects.count(),1)
        self.assertEqual(Expense.objects.get().supplier,'Entreprise A')
        self.year.refresh_from_db();self.assertEqual(self.year.next_entry,2)

    def test_archived_supplier_and_document_cannot_be_used_for_new_invoice(self):
        self.supplier.archived=True;self.supplier.save()
        self.assertEqual(self.invoice().status_code,400)
        self.supplier.archived=False;self.supplier.save()
        doc=Document.objects.create(title='Ancienne',archived=True)
        self.assertEqual(self.invoice(document=doc.pk).status_code,400)
        self.assertEqual(Entry.objects.count(),0)
        self.assertEqual(self.invoice(supplier_record='',supplier='Saisie libre').status_code,201)

    def test_supplier_payment_uses_selected_bank_and_keeps_auxiliary_reference(self):
        default=self.bank();chosen=self.bank('5122')
        self.assertEqual(self.invoice().status_code,201)
        expense=Expense.objects.get()
        response=self.send(f'expenses/{expense.pk}/pay',{'date':'2026-01-10','amount':'30','bank':chosen.pk})
        self.assertEqual(response.status_code,200,response.content)
        payment=ExpensePayment.objects.get()
        self.assertEqual(payment.bank,chosen)
        self.assertEqual(payment.entry.lines.get(account__code='401').supplier,self.supplier)
        self.assertEqual(payment.entry.lines.get(account=chosen.account).credit,Decimal('30'))
        self.assertFalse(payment.entry.lines.filter(account=default.account).exists())
        row=self.client.get('/api/finance/expenses/').json()['items'][0]
        self.assertEqual(row['remaining'],'70.00');self.assertEqual(row['payments'][0]['bank_name'],chosen.name)

    def test_receipts_use_default_and_explicit_bank_and_reject_inactive(self):
        default=self.bank();chosen=self.bank('5122')
        body={'year':self.year.pk,'owner':self.owner.pk,'date':'2026-01-10','amount':'25'}
        self.assertEqual(self.send('receipts',body).status_code,201)
        self.assertEqual(Receipt.objects.get().bank,default)
        self.assertEqual(self.send('receipts',body|{'bank':chosen.pk}).status_code,201)
        chosen.active=False;chosen.save()
        self.assertEqual(self.send('receipts',body|{'bank':chosen.pk}).status_code,400)
        self.assertEqual(Receipt.objects.count(),2)

    def test_supplier_report_opening_debt_payment_and_unidentified_legacy(self):
        self.assertEqual(self.invoice().status_code,201)
        expense=Expense.objects.get()
        self.assertEqual(self.send(f'expenses/{expense.pk}/pay',{'date':'2026-02-05','amount':'30'}).status_code,200)
        self.assertEqual(self.invoice(supplier_record='',supplier='Saisie libre',reference='F002',date='2026-02-01',amount='50').status_code,201)
        result=self.client.get('/api/finance/reporting/supplier-auxiliary/',{'year':self.year.pk,'start':'2026-02-01'}).json()
        supplier=next(r for r in result['rows'] if r['supplier']==self.supplier.name)
        self.assertEqual(supplier['opening'],'100.00');self.assertEqual(supplier['debit'],'30.00');self.assertEqual(supplier['balance'],'70.00')
        self.assertEqual(result['totals']['balance'],'120.00')
        selected=self.client.get('/api/finance/reporting/supplier-auxiliary/',{'year':self.year.pk,'supplier':self.supplier.pk}).json()
        self.assertEqual(len(selected['rows']),1)
        self.assertEqual(selected['totals']['balance'],'70.00')

    def test_manual_supplier_line_and_reversal_keep_supplier_identity(self):
        response=self.send('entries',{'year':self.year.pk,'date':'2026-01-01','label':'Dette','lines':[{'code':'601','debit':'10'},{'code':'401','credit':'10','supplier':self.supplier.pk}]})
        self.assertEqual(response.status_code,201,response.content)
        pk=response.json()['id']
        reversed=self.send(f'operations/reverse-entry/{pk}',{'date':'2026-01-02'})
        self.assertEqual(reversed.status_code,201,reversed.content)
        self.assertEqual(Entry.objects.get(pk=reversed.json()['id']).lines.get(account__code='401').supplier,self.supplier)
        invalid=self.send('entries',{'year':self.year.pk,'date':'2026-01-01','label':'Invalide','lines':[{'code':'512','debit':'10','supplier':self.supplier.pk},{'code':'401','credit':'10'}]})
        self.assertEqual(invalid.status_code,400)

    def test_bank_and_supplier_reports_are_private_and_csrf_protected(self):
        bank=self.bank(iban='FR7630006000011234567890189')
        for path in ['banks','bank-transfers','banks/'+str(bank.pk)]:
            self.assertEqual(self.member.get('/api/finance/'+path+'/').status_code,403)
            self.assertEqual(Client().get('/api/finance/'+path+'/').status_code,401)
        self.assertEqual(self.member.get('/api/finance/reporting/supplier-auxiliary/',{'year':self.year.pk}).status_code,403)
        protected=Client(enforce_csrf_checks=True);protected.force_login(self.manager)
        self.assertEqual(self.send('banks',{'name':'No','account_code':'5122'},client=protected).status_code,403)

    def test_budget_notes_persist_with_previous_year_comparison_and_blank_unknowns(self):
        self.entry([{'code':'601','debit':'40'},{'code':'512','credit':'40'}])
        account=Account.objects.get(code='601')
        response=self.send('manage/budgets',{'year':self.year.pk,'account':account.pk,'amount':'50','variance_note':'Entretien prévu mais reporté'})
        self.assertEqual(response.status_code,201,response.content)
        budget=response.json()['id']
        self.assertEqual(self.send(f'manage/budgets/{budget}',{'variance_note':'Dépense reportée à février'},'patch').status_code,200)
        previous=FiscalYear.objects.create(name='2025',starts_on=date(2025,1,1),ends_on=date(2025,12,31))
        self.entry([{'code':'601','debit':'30'},{'code':'512','credit':'30'}],year=previous,day='2025-06-01')
        Budget.objects.create(year=previous,account=account,amount='35')
        result=self.client.get('/api/finance/reporting/budget/',{'year':self.year.pk}).json()
        row=next(r for r in result['rows'] if r['code']=='601')
        self.assertEqual(result['previous_year'],'2025')
        self.assertEqual(row['previous_actual'],'30.00');self.assertEqual(row['previous_budget'],'35.00')
        self.assertEqual(row['variance'],'-10.00');self.assertEqual(row['variance_note'],'Dépense reportée à février')
        no_previous=self.client.get('/api/finance/reporting/budget/',{'year':previous.pk}).json()
        self.assertIsNone(no_previous['previous_year']);self.assertIsNone(no_previous['rows'][0]['previous_actual'])

    def test_budget_comparison_keeps_annual_prior_period_and_respects_analytic(self):
        center=CostCenter.objects.create(name='Ascenseur')
        previous=FiscalYear.objects.create(name='2025',starts_on=date(2025,1,1),ends_on=date(2025,12,31))
        with transaction.atomic():
            year=open_year(previous.pk,date(2025,1,1))
            post_entry(year,date(2025,1,1),'OD','Ancienne charge',[{'code':'601','debit':'30'},{'code':'512','credit':'30'}],self.manager,cost_center=center)
        result=self.client.get('/api/finance/reporting/budget/',{'year':self.year.pk,'start':'2026-02-01','center':center.pk}).json()
        self.assertEqual(result['rows'][0]['previous_actual'],'30.00');self.assertEqual(result['rows'][0]['actual'],'0')
        other=CostCenter.objects.create(name='Autre')
        self.assertEqual(self.client.get('/api/finance/reporting/budget/',{'year':self.year.pk,'center':other.pk}).json()['rows'],[])

    def test_budget_notes_validate_and_csv_neutralizes_formulas(self):
        account=Account.objects.create(code='601',name='Entretien')
        body={'year':self.year.pk,'account':account.pk,'amount':'50','variance_note':'=DANGEREUX()'}
        response=self.send('manage/budgets',body)
        self.assertEqual(response.status_code,201,response.content)
        pk=response.json()['id']
        self.assertEqual(self.send(f'manage/budgets/{pk}',{'variance_note':'x'*2001},'patch').status_code,400)
        csv=self.client.get('/api/finance/reporting/budget/',{'year':self.year.pk,'format':'csv'}).content.decode()
        self.assertIn("'=DANGEREUX()",csv)
        self.assertNotIn('None',csv)
        self.year.closed=True;self.year.save()
        self.assertEqual(self.send(f'manage/budgets/{pk}',{'variance_note':'Fermé'},'patch').status_code,400)
