import json
from datetime import date
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, Client
from core.models import Owner
from core.access import provision_access
from .models import FiscalYear, ChargeKey, Expense, ExpensePayment, Entry
from .services import balance


class PaymentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("manager", is_staff=True)
        self.client.force_login(self.user)
        self.year = FiscalYear.objects.create(name="2026", starts_on=date(2026,1,1), ends_on=date(2026,12,31))
        self.key = ChargeKey.objects.create(name="Entretien")
        result = self.post("expenses", {"year":self.year.pk,"key":self.key.pk,"supplier":"Entreprise test",
            "reference":"TEST-001","label":"Entretien","date":"2026-02-01","amount":"100.00"})
        self.assertEqual(result.status_code,201,result.content)
        self.expense = Expense.objects.get(pk=result.json()["id"])

    def post(self, path, data, client=None):
        return (client or self.client).post("/api/finance/"+path+"/",json.dumps(data),content_type="application/json")

    def pay(self, value=None, day="2026-02-02", client=None):
        return self.post(f"expenses/{self.expense.pk}/pay",{"date":day,"amount":value},client)

    def test_partial_then_remaining_payment_balances(self):
        self.assertEqual(self.pay("25.50").status_code,200)
        self.expense.refresh_from_db()
        self.assertIsNone(self.expense.payment_entry_id)
        data=self.client.get("/api/finance/expenses/").json()["items"][0]
        self.assertFalse(data["paid"])
        self.assertEqual(Decimal(data["remaining"]),Decimal("74.50"))
        self.assertEqual(self.pay().status_code,200)
        data=self.client.get("/api/finance/expenses/").json()["items"][0]
        self.assertTrue(data["paid"])
        self.assertEqual(Decimal(data["remaining"]),0)
        self.assertEqual(len(data["payments"]),2)
        self.assertEqual(self.pay("1").status_code,400)
        rows=balance(self.year)
        self.assertEqual(Decimal(next(r for r in rows if r["code"]=="512")["balance"]),-100)
        self.assertEqual(sum(Decimal(r["debit"]) for r in rows),sum(Decimal(r["credit"]) for r in rows))

    def test_invalid_and_excessive_payments_leave_no_entry(self):
        for value in ["100.01","-1","0","NaN","1.001"]:
            self.assertEqual(self.pay(value).status_code,400)
        self.assertEqual(self.pay("10",day="2026-01-31").status_code,400)
        self.assertEqual(Entry.objects.count(),1)
        self.assertEqual(ExpensePayment.objects.count(),0)
        self.year.closed=True;self.year.save()
        self.assertEqual(self.pay("10").status_code,400)
        self.assertEqual(ExpensePayment.objects.count(),0)

    def test_partial_payment_cannot_be_reversed_as_manual_entry(self):
        self.assertEqual(self.pay("10").status_code,200)
        payment=ExpensePayment.objects.get()
        response=self.post(f"operations/reverse-entry/{payment.entry_id}",{"date":"2026-02-03"})
        self.assertEqual(response.status_code,400)
        self.assertEqual(Entry.objects.count(),2)

    def test_member_cannot_read_or_record_supplier_payments(self):
        owner=Owner.objects.create(first_name="Alice",last_name="Test",email="alice@example.test")
        provision_access(owner);owner.must_change_password=False;owner.save()
        member=Client();member.force_login(owner.user)
        self.assertEqual(member.get("/api/finance/expenses/").status_code,403)
        self.assertEqual(self.pay("10",client=member).status_code,403)
        self.assertEqual(ExpensePayment.objects.count(),0)

    def test_legacy_payment_migration_preserves_ledger_and_is_idempotent(self):
        self.assertEqual(self.pay().status_code,200)
        ExpensePayment.objects.all().delete()
        entries=list(Entry.objects.values_list("pk",flat=True))
        copy=import_module("finance.migrations.0004_expensepayment").copy_legacy_payments
        copy(apps,SimpleNamespace(connection=connection))
        copy(apps,SimpleNamespace(connection=connection))
        self.assertEqual(ExpensePayment.objects.count(),1)
        self.assertEqual(ExpensePayment.objects.get().amount,Decimal("100"))
        self.assertEqual(list(Entry.objects.values_list("pk",flat=True)),entries)
