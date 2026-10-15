import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, Client
from documents.models import Document, Version
from core.models import Owner, Lot
from .models import *
from .services import post_entry, publish_call
from .cycle import match_lines, record_mutation, annexes, apply_regularization, regularization_data
from .funding import rules, advance_balances


class FundingAndAnnexTests(TestCase):
    def setUp(self):
        clock = patch('finance.services.timezone.localdate',return_value=date(2027,2,28))
        clock.start();self.addCleanup(clock.stop)
        self.user=get_user_model().objects.create_user('manager',is_staff=True)
        self.client.force_login(self.user)
        self.year=FiscalYear.objects.create(name='2026',starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        self.next=FiscalYear.objects.create(name='2027',starts_on=date(2027,1,1),ends_on=date(2027,12,31))
        self.owner=Owner.objects.create(first_name='Camille',last_name='Dupont')
        self.other=Owner.objects.create(first_name='Camille',last_name='Dupont')
        self.lot=Lot.objects.create(number='A',owner=self.owner,shares=100)
        self.key=ChargeKey.objects.create(name='Générales')
        document=Document.objects.create(title='Décision et justificatif')
        self.proof=Version.objects.create(document=document,file='documents/test.pdf',filename='decision.pdf',size=10,content_type='application/pdf',checksum='a'*64,created_by=self.user)
        self.bank=BankAccount.objects.create(name='Courant',account=Account.objects.create(code='512',name='Banque'),is_default=True)

    def post(self,path,data,status=201):
        response=self.client.post('/api/finance/'+path+'/',json.dumps(data),content_type='application/json')
        self.assertEqual(response.status_code,status,response.content)
        return response.json()

    def policy(self,**kw):
        defaults=dict(housing='housing',received_on=date(2000,1,1),annual_budget=Decimal('6000'),
            budget_reference='AG budget',ppt_adopted=False,fund_contribution=Decimal('300'),
            fund_reference='AG fonds',fund_proof=self.proof,reserve_authorized=True,advance_reference='Règlement et AG',advance_proof=self.proof,updated_by=self.user)
        defaults.update(kw)
        return FundingPolicy.objects.create(year=self.year,**defaults)

    def call(self,value='100',kind='advance',subtype='reserve',due='2026-01-15'):
        call=FundCall.objects.create(year=self.year,key=self.key,label='Appel test',date=date(2026,1,1),due_date=date.fromisoformat(due),amount=Decimal(value),kind=kind,advance_type=subtype,decision='AG autorisation')
        with transaction.atomic(): publish_call(call,self.user)
        self.year.refresh_from_db()
        return call

    def payment(self,call,value='100',owner=None,on='2026-02-01',debit=None):
        owner=owner or self.owner
        with transaction.atomic():
            entry=post_entry(self.year,date.fromisoformat(on),'BQ','Versement',[{'code':'512','debit':value},{'code':'450','credit':value,'owner':owner}],self.user)
            match=match_lines(debit or call.entry.lines.get(account__code='450',owner=owner),entry.lines.get(account__code='450'),Decimal(value),self.user)
        self.year.refresh_from_db()
        return match

    def refund(self,value='100',**kw):
        data=dict(year=self.year.pk,date='2026-10-01',lot=self.lot.pk,owner=self.owner.pk,code='1031',amount=value,reference='Restitution votée',proof=self.proof.pk,method='account')
        data.update(kw)
        return self.post('funding/refund',data,kw.pop('status',201) if 'status' in kw else 201)

    def test_fund_minima_ppt_round_up_and_ten_year_anniversary(self):
        policy=self.policy(ppt_adopted=True,ppt_amount=Decimal('20000.01'),fund_contribution=Decimal('500.01'))
        self.assertEqual(rules(policy)['minimum'],'500.01')
        policy.received_on=date(2016,10,1)
        self.assertFalse(rules(policy,date(2026,9,30))['mandatory'])
        self.assertTrue(rules(policy,date(2026,10,1))['mandatory'])
        self.assertEqual(rules(policy,date(2026,10,1))['minimum'],'500.01')

    def test_fund_suspension_needs_both_thresholds_and_evidence(self):
        policy=self.policy(annual_budget=Decimal('1000'),ppt_adopted=True,ppt_amount=Decimal('4000'),suspended=True)
        with transaction.atomic():post_entry(self.year,date(2026,1,1),'AN','Ouverture',[{'code':'512','debit':'1500'},{'code':'105','lot':self.lot,'credit':'1500'}],self.user,kind='opening')
        self.assertFalse(rules(policy)['suspension_possible'])
        policy.ppt_amount=Decimal('2000')
        self.assertTrue(rules(policy)['suspension_possible'])
        self.assertTrue(any('suspension' in s for s in rules(policy)['errors']))

    def test_configured_fund_call_cannot_exceed_vote_or_minimum(self):
        self.policy(fund_contribution=Decimal('250'))
        with self.assertRaises(ValueError):self.call('100',kind='fund')
        FundingPolicy.objects.update(fund_contribution=300)
        self.call('200',kind='fund')
        with self.assertRaises(ValueError):self.call('101',kind='fund')

    def test_reserve_ceiling_includes_existing_balance(self):
        self.policy()
        self.call('900')
        with self.assertRaises(ValueError):self.call('100.01')
        self.call('100')

    def test_three_advance_accounts_and_required_ppt(self):
        self.policy()
        with self.assertRaises(ValueError):self.call('10',subtype='ppt')
        FundingPolicy.objects.update(ppt_adopted=True,ppt_amount=1000)
        for subtype,code in [('reserve','1031'),('ppt','1032'),('temporary','1033')]:
            call=self.call('10',subtype=subtype)
            self.assertTrue(call.entry.lines.filter(account__code=code,owner=self.owner,lot=self.lot).exists())

    def test_refund_only_paid_amount_and_cannot_refund_105(self):
        call=self.call()
        self.payment(call,'40')
        self.assertEqual(advance_balances()[0]['refundable'],'40.00')
        self.refund('40')
        self.assertEqual(advance_balances()[0]['refundable'],'0.00')
        self.post('funding/refund',dict(year=self.year.pk,date='2026-10-01',lot=self.lot.pk,owner=self.owner.pk,code='1031',amount='1',reference='Test',proof=self.proof.pk,method='account'),400)
        self.post('funding/refund',dict(year=self.year.pk,date='2026-10-01',lot=self.lot.pk,owner=self.owner.pk,code='105',amount='1',reference='Test',proof=self.proof.pk,method='account'),400)

    def test_paid_advance_remains_with_seller_and_unpaid_part_transfers(self):
        call=self.call(due='2026-12-01')
        self.payment(call,'40')
        with transaction.atomic():record_mutation({'lot':self.lot.pk,'new_owner':self.other.pk,'effective_date':'2026-09-01','reference':'Vente'},self.user)
        self.year.refresh_from_db()
        rows={r['owner']:r for r in advance_balances()}
        self.assertEqual(rows[self.owner.pk]['refundable'],'40.00')
        self.assertEqual(rows[self.other.pk]['constituted'],'60.00')
        self.assertEqual(rows[self.other.pk]['refundable'],'0.00')
        transfer=AllocationTransfer.objects.get()
        self.payment(call,'60',owner=self.other,debit=transfer.entry.lines.get(account__code='450',debit__gt=0),on='2026-09-20')
        self.refund('40')
        self.refund('60',owner=self.other.pk)
        self.assertTrue(all(r['refundable']=='0.00' for r in advance_balances()))

    def test_cannot_unletter_cash_after_advance_refund_and_can_correct_refund(self):
        call=self.call();match=self.payment(call)
        r=self.refund()
        self.post(f'cycle/unletter/{match.pk}',{},400)
        match.refresh_from_db();self.assertTrue(match.active)
        self.post('funding/cancel-refund',{'year':self.year.pk,'id':r['id'],'date':'2026-10-02'},200)
        self.post(f'cycle/unletter/{match.pk}',{},200)
        self.assertEqual(advance_balances()[0]['refundable'],'0.00')

    def test_bank_refund_and_dedicated_fund_bank_rejected(self):
        call=self.call();self.payment(call)
        works=BankAccount.objects.create(name='Travaux',kind='works',account=Account.objects.create(code='5122',name='Fonds'))
        common=dict(year=self.year.pk,date='2026-10-01',lot=self.lot.pk,owner=self.owner.pk,code='1031',amount='100',reference='Virement',proof=self.proof.pk,method='bank')
        self.post('funding/refund',{**common,'bank':works.pk},400)
        r=self.post('funding/refund',{**common,'bank':self.bank.pk})
        self.assertEqual(AdvanceRefund.objects.get(pk=r['id']).entry.lines.get(account__code='512').credit,Decimal('100'))

    def test_unconfigured_policy_visible_and_private(self):
        r=self.client.get(f'/api/finance/funding/context/?year={self.year.pk}')
        self.assertFalse(r.json()['configured'])
        outsider=Client();outsider.force_login(get_user_model().objects.create_user('reader'))
        self.assertEqual(outsider.get(f'/api/finance/funding/context/?year={self.year.pk}').status_code,403)

    def test_same_name_owners_never_compensated_in_annex1(self):
        with transaction.atomic():post_entry(self.year,date(2026,1,1),'AN','Tiers homonymes',[{'code':'450','owner':self.owner,'debit':'50'},{'code':'450','owner':self.other,'credit':'50'}],self.user,kind='opening')
        pack=annexes(self.year)['regulatory']
        rows=[r for r in pack['annexes'][0]['rows'] if r['code']=='450']
        self.assertEqual(len(rows),2)
        self.assertEqual(sum(Decimal(r['debit']) for r in rows),50)
        self.assertTrue(all(c['ok'] for c in pack['checks']))

    def test_provisions_are_not_changed_by_posted_regularization(self):
        self.call('100',kind='current')
        before=annexes(self.year)['regulatory']
        with transaction.atomic():apply_regularization(self.year,{'approved_on':'2027-02-01','decision':'AG','source_hash':regularization_data(self.year,date(2027,2,1))['source_hash']},self.user)
        after=annexes(self.year)['regulatory']
        for p in [before,after]:
            provision=next(r for r in p['annexes'][2]['rows'] if r['code']=='701')
            self.assertEqual(provision['actual_current'],'100.00')
            self.assertTrue(all(c['ok'] for c in p['checks']),p['checks'])
        self.assertEqual(before['after_allocation'],'proposed')
        self.assertEqual(after['after_allocation'],'posted')

    def test_pending_work_annex5_and_annex1_concordance(self):
        project=FinanceProject.objects.create(name='Toiture',key=self.key,budget=1000,decision='AG 2026',decided_on=date(2026,1,1))
        with transaction.atomic():
            post_entry(self.year,date(2026,1,1),'AP','Appel travaux',[{'code':'450','owner':self.owner,'debit':'500'},{'code':'102','project':project,'key':self.key,'credit':'500'}],self.user)
            post_entry(self.year,date(2026,2,1),'AC','Travaux',[{'code':'671','project':project,'key':self.key,'debit':'300'},{'code':'401','credit':'300'}],self.user)
        pack=annexes(self.year)['regulatory']
        self.assertEqual(pack['annexes'][4]['rows'][0]['waiting'],'200.00')
        row=next(r for r in pack['annexes'][0]['rows'] if r['code']=='12')
        self.assertEqual(row['credit'],'200.00')
        self.assertTrue(all(c['ok'] for c in pack['checks']),pack['checks'])

    def test_future_work_and_unknown_dates_are_not_invented(self):
        FinanceProject.objects.create(name='Futur',key=self.key,budget=1,decision='Préparation',decided_on=date(2027,2,1))
        self.assertFalse(annexes(self.year)['regulatory']['annexes'][4]['rows'])

    def test_previous_and_future_budget_columns(self):
        account=Account.objects.create(code='601',name='Eau')
        Budget.objects.create(year=self.year,account=account,key=self.key,amount=100)
        Budget.objects.create(year=self.next,account=account,key=self.key,amount=120)
        row=annexes(self.year)['regulatory']['annexes'][2]['rows'][0]
        self.assertEqual(row['budget_current'],'100.00')
        self.assertEqual(row['budget_next'],'120.00')
        self.assertIsNone(row['actual_previous'])
        self.assertIsNone(row['budget_following'])

    def test_refund_request_is_idempotent(self):
        from uuid import uuid4
        call=self.call();self.payment(call)
        data=dict(year=self.year.pk,date='2026-10-01',lot=self.lot.pk,owner=self.owner.pk,code='1031',amount='50',reference='Restitution',proof=self.proof.pk,method='account',request_id=str(uuid4()))
        a=self.post('funding/refund',data)
        b=self.post('funding/refund',data)
        self.assertEqual(a,b)
        self.assertEqual(AdvanceRefund.objects.count(),1)

    def test_cent_installments_never_over_allocate_paid_advances(self):
        self.lot.shares=1;self.lot.save()
        lot2=Lot.objects.create(number='B',owner=self.owner,shares=1)
        call=self.call('0.03')
        for i in range(3):self.payment(call,'0.01',on=f'2026-02-0{i+1}')
        rows={r['lot']:r for r in advance_balances()}
        self.assertEqual(rows[self.lot.pk]['paid'],'0.02')
        self.assertEqual(rows[lot2.pk]['paid'],'0.01')

    def test_fund_at_historical_date_keeps_later_cancelled_opening(self):
        from .cycle import funds
        with transaction.atomic():
            original=post_entry(self.year,date(2026,1,1),'AN','Fonds repris',[{'code':'512','debit':'100'},{'code':'105','lot':self.lot,'credit':'100'}],self.user,kind='opening')
            post_entry(self.year,date(2026,10,1),'AN','Correction',[{'code':'512','credit':'100'},{'code':'105','lot':self.lot,'debit':'100'}],self.user,kind='opening',reversal_of=original)
        self.assertEqual(Decimal(funds(date(2026,9,1))[0]['available']),100)
        self.assertEqual(Decimal(funds(date(2026,10,1))[0]['available']),0)

    def test_backdated_reserve_cannot_break_later_peak(self):
        self.policy()
        call=FundCall.objects.create(year=self.year,key=self.key,label='Réserve septembre',date=date(2026,9,1),due_date=date(2026,9,1),amount=Decimal('1000'),kind='advance')
        with transaction.atomic():publish_call(call,self.user)
        with self.assertRaises(ValueError):self.call('0.01')

    def test_archived_proof_and_closed_policy_cannot_be_used(self):
        self.call();self.payment(FundCall.objects.get())
        self.proof.document.archived=True;self.proof.document.save()
        self.post('funding/refund',dict(year=self.year.pk,date='2026-10-01',lot=self.lot.pk,owner=self.owner.pk,code='1031',amount='10',reference='Restitution',proof=self.proof.pk,method='account'),400)
        self.year.closed=True;self.year.save()
        self.post('funding/policy',dict(year=self.year.pk),400)

    def ppt_use(self,call,value='60',**kw):
        project=FinanceProject.objects.create(name='PPT toiture',key=self.key,budget=100,decision='AG travaux',decided_on=date(2026,1,1))
        data=dict(year=self.year.pk,date='2026-09-01',lot=self.lot.pk,owner=self.owner.pk,code='1032',amount=value,reference='AG affectation',proof=self.proof.pk,project=project.pk)
        data.update(kw)
        return project,self.post('funding/use',data)

    def test_ppt_use_consumes_refundable_balance_and_correction_restores_it(self):
        call=self.call(subtype='ppt');self.payment(call)
        project,result=self.ppt_use(call)
        row=advance_balances()[0]
        self.assertEqual((row['used'],row['refundable']),('60.00','40.00'))
        self.refund('40',code='1032')
        self.post('funding/cancel-use',dict(year=self.year.pk,date='2026-10-02',id=result['id']),200)
        self.assertEqual(advance_balances()[0]['refundable'],'60.00')

    def test_cannot_unletter_paid_ppt_already_used(self):
        call=self.call(subtype='ppt');match=self.payment(call)
        self.ppt_use(call,'100')
        self.post(f'cycle/unletter/{match.pk}',{},400)

    def test_ppt_funds_work_completion_without_charging_twice(self):
        from .cycle import finish_project
        call=self.call(subtype='ppt');self.payment(call)
        project,_=self.ppt_use(call,'100')
        with transaction.atomic():
            self.year.refresh_from_db()
            post_entry(self.year,date(2026,9,2),'AC','Travaux réalisés',[{'code':'671','key':self.key,'project':project,'debit':'100'},{'code':'401','credit':'100'}],self.user)
            finish_project(project,self.year,{'date':'2026-10-01','decision':'AG approbation'},self.user)
        self.assertFalse(Line.objects.filter(entry__kind='project-complete',account__code='450').exists())
        pack=annexes(self.year)['regulatory']
        self.assertTrue(all(c['ok'] for c in pack['checks']),pack['checks'])
        item=AdvanceUse.objects.get()
        self.post('funding/cancel-use',dict(year=self.year.pk,date='2026-10-02',id=item.pk),400)

    def test_ppt_of_seller_is_not_assigned_to_buyers_work(self):
        call=self.call(subtype='ppt');self.payment(call)
        with transaction.atomic():record_mutation({'lot':self.lot.pk,'new_owner':self.other.pk,'effective_date':'2026-08-01','reference':'Vente'},self.user)
        project=FinanceProject.objects.create(name='Toiture',key=self.key,budget=100,decision='AG travaux',decided_on=date(2026,1,1))
        self.post('funding/use',dict(year=self.year.pk,date='2026-09-01',lot=self.lot.pk,owner=self.owner.pk,code='1032',amount='100',reference='AG affectation',proof=self.proof.pk,project=project.pk),400)
        self.refund('100',code='1032')
