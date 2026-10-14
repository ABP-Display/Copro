import json
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, Client
from core.models import Owner, Lot
from core.access import provision_access
from .models import FiscalYear, ChargeKey, FundCall, Entry, Line, Allocation, Expense, Account
from .services import distribute, post_entry, open_year, balance


class FinanceTests(TestCase):
    def setUp(self):
        self.manager=get_user_model().objects.create_user("manager",password="Test-Manager-173!",is_staff=True)
        self.client.force_login(self.manager)
        self.year=FiscalYear.objects.create(name="2026",starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        self.key=ChargeKey.objects.create(name="Charges générales")
        self.owners=[Owner.objects.create(first_name=str(i),last_name="Test",email=f"o{i}@example.test") for i in range(3)]
        self.lots=[Lot.objects.create(number=str(i),owner=o,shares=1) for i,o in enumerate(self.owners)]

    def post(self,path,data,client=None,method="post"):
        return getattr(client or self.client,method)("/api/finance/"+path+"/",json.dumps(data),content_type="application/json")

    def draft(self):
        return FundCall.objects.create(year=self.year,key=self.key,label="Trimestre",date=date(2026,1,1),due_date=date(2026,1,15),amount=100)

    def test_allocation_exact_and_stable(self):
        result=distribute("100.00",[(lot,1) for lot in self.lots])
        self.assertEqual([value for _,_,value in result],[Decimal("33.34"),Decimal("33.33"),Decimal("33.33")])
        self.assertEqual(sum(value for _,_,value in result),Decimal("100"))
        for invalid in ["NaN","Infinity","1.001","-1"]:
            with self.assertRaises(ValueError): distribute(invalid,[(self.lots[0],1)])

    def test_unassigned_lots_block_validation(self):
        self.lots[0].owner=None;self.lots[0].save()
        result=self.post(f"calls/{self.draft().pk}/publish",{})
        self.assertEqual(result.status_code,400)
        self.assertEqual(Entry.objects.count(),0)

    def test_call_posting_immutable_snapshot_and_no_duplicate(self):
        call=self.draft()
        self.assertEqual(self.post(f"calls/{call.pk}/publish",{}).status_code,200)
        self.assertEqual(sum(a.amount for a in Allocation.objects.all()),Decimal("100"))
        self.assertEqual(Entry.objects.count(),1)
        self.assertEqual(self.post(f"calls/{call.pk}/publish",{}).status_code,400)
        self.lots[0].shares=50;self.lots[0].save()
        self.assertEqual(Allocation.objects.get(lot=self.lots[0]).amount,Decimal("33.34"))
        rows=balance(self.year)
        self.assertEqual(sum(Decimal(r["debit"]) for r in rows),sum(Decimal(r["credit"]) for r in rows))

    def test_unbalanced_entry_rolls_back_number_and_data(self):
        result=self.post("entries",{"year":self.year.pk,"date":"2026-01-01","label":"Test","lines":[{"code":"512","debit":"12"},{"code":"450","credit":"10"}]})
        self.assertEqual(result.status_code,400)
        self.assertEqual(Entry.objects.count(),0)
        self.year.refresh_from_db();self.assertEqual(self.year.next_entry,1)

    def test_expense_payment_and_receipt_balance(self):
        response=self.post("expenses",{"year":self.year.pk,"key":self.key.pk,"supplier":"Fournisseur","reference":"F-01","label":"Nettoyage","date":"2026-02-01","amount":"60.00"})
        self.assertEqual(response.status_code,201,response.content)
        expense=response.json()["id"]
        self.assertEqual(self.post(f"expenses/{expense}/pay",{"date":"2026-02-02"}).status_code,200)
        self.assertEqual(self.post(f"expenses/{expense}/pay",{"date":"2026-02-02"}).status_code,400)
        self.assertEqual(self.post("receipts",{"year":self.year.pk,"owner":self.owners[0].pk,"date":"2026-02-03","amount":"100.00"}).status_code,201)
        bank=next(r for r in balance(self.year) if r["code"]=="512")
        self.assertEqual(Decimal(bank["balance"]),Decimal("40.00"))

    def test_closing_freezes_transactions(self):
        self.assertEqual(self.post(f"years/{self.year.pk}/close",{}).status_code,400)
        self.year.closed=True;self.year.save(update_fields=['closed'])
        response=self.post("receipts",{"year":self.year.pk,"owner":self.owners[0].pk,"date":"2026-02-03","amount":"100.00"})
        self.assertEqual(response.status_code,400)
        self.assertEqual(Entry.objects.count(),0)

    def test_draft_blocks_closing_and_date_validation(self):
        self.draft()
        self.assertEqual(self.post(f"years/{self.year.pk}/close",{}).status_code,400)
        response=self.post("calls",{"year":self.year.pk,"key":self.key.pk,"label":"Test","date":"2027-01-01","due_date":"2027-01-02","amount":"10.00"})
        self.assertEqual(response.status_code,400)

    def test_private_ledger_and_expenses_not_shared(self):
        owner=self.owners[0];provision_access(owner);owner.must_change_password=False;owner.save()
        member=Client();member.force_login(owner.user)
        for resource in ["entries","expenses","accounts","balance"]:
            self.assertEqual(member.get(f"/api/finance/{resource}/").status_code,403)
        self.assertEqual(self.post("reports",{"year":self.year.pk},member).status_code,403)
        self.assertEqual(member.get("/api/finance/calls/").json()["items"],[])
        self.assertEqual(self.post("reports",{"year":self.year.pk,"title":"Synthèse"}).status_code,201)
        reports=member.get("/api/finance/reports/").json()["items"]
        self.assertEqual(len(reports),1)
        self.assertNotIn("owner",str(reports))
        self.assertNotIn("supplier",str(reports))

    def test_custom_shares_and_duplicate_lots(self):
        key=ChargeKey.objects.create(name="Ascenseur",general=False)
        response=self.post(f"keys/{key.pk}/shares",{"shares":[{"lot":self.lots[0].pk,"value":"10"},{"lot":self.lots[0].pk,"value":"20"}]},method="put")
        self.assertEqual(response.status_code,400)
        self.assertEqual(key.shares.count(),0)
        response=self.post(f"keys/{key.pk}/shares",{"shares":[{"lot":self.lots[0].pk,"value":"10"}]},method="put")
        self.assertEqual(response.status_code,200)

    def test_year_overlap_and_csv_injection(self):
        self.assertEqual(self.post("years",{"name":"Chevauchement","starts_on":"2026-06-01","ends_on":"2027-05-31"}).status_code,400)
        Account.objects.create(code="601",name="=DANGEROUS()")
        response=self.post("entries",{"year":self.year.pk,"date":"2026-01-01","label":"Test","lines":[{"code":"601","debit":"1"},{"code":"512","credit":"1"}]})
        self.assertEqual(response.status_code,201)
        result=self.client.get(f"/api/finance/balance/?year={self.year.pk}&format=csv")
        self.assertEqual(result.status_code,200)
        self.assertIn("'=DANGEROUS()",result.content.decode())
