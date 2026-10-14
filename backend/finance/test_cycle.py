import json
from unittest.mock import patch
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, Client
from core.models import Owner, Lot
from operations.models import Supplier
from .models import *
from .cycle import regularization_data, funds
from .services import balance


class AccountingCycleTests(TestCase):
    def test_sale_preserves_paid_fund_and_transfers_only_unpaid_portion(self):
        from .cycle import match_lines
        result=self.post('calls',{'year':self.year.pk,'key':self.key.pk,'label':'Fonds','date':'2026-01-01','due_date':'2026-12-01','amount':'200','kind':'fund'})
        self.post(f'calls/{result["id"]}/publish',{},200)
        call=FundCall.objects.get(pk=result['id'])
        receipt=self.post('receipts',{'year':self.year.pk,'owner':self.owners[0].pk,'date':'2026-06-01','amount':'40'})
        with transaction.atomic():
            match_lines(call.entry.lines.get(owner=self.owners[0],debit__gt=0),Receipt.objects.get(pk=receipt['id']).entry.lines.get(owner=self.owners[0]),Decimal('40'),self.user)
        self.mutation({'lot':self.lots[0].pk,'new_owner':self.owners[1].pk,'effective_date':'2026-09-01','reference':'Vente et fonds versé'})
        transfer=AllocationTransfer.objects.get()
        self.assertEqual(transfer.entry.lines.get(debit__gt=0).debit,Decimal('60'))
        receipt=self.post('receipts',{'year':self.year.pk,'owner':self.owners[1].pk,'date':'2026-10-01','amount':'60'})
        with transaction.atomic():
            match_lines(transfer.entry.lines.get(debit__gt=0),Receipt.objects.get(pk=receipt['id']).entry.lines.get(owner=self.owners[1]),Decimal('60'),self.user)
        row=next(r for r in funds(date(2026,12,31)) if r['lot']==self.lots[0].pk)
        self.assertEqual(Decimal(row['paid']),Decimal('100'))
        self.assertEqual(Decimal(row['available']),Decimal('100'))

    def setUp(self):
        clock = patch(
            "finance.services.timezone.localdate", return_value=date(2027, 2, 28)
        )
        clock.start()
        self.addCleanup(clock.stop)
        self.user = get_user_model().objects.create_user("manager", is_staff=True)
        self.client.force_login(self.user)
        self.year = FiscalYear.objects.create(
            name="2026", starts_on=date(2026, 1, 1), ends_on=date(2026, 12, 31)
        )
        self.next = FiscalYear.objects.create(
            name="2027", starts_on=date(2027, 1, 1), ends_on=date(2027, 12, 31)
        )
        self.key = ChargeKey.objects.create(name="Générales")
        self.owners = [
            Owner.objects.create(first_name=f"Personne{i}", last_name="Test")
            for i in range(2)
        ]
        self.lots = [
            Lot.objects.create(number=str(i), owner=o, shares=1)
            for i, o in enumerate(self.owners)
        ]
        self.bank = BankAccount.objects.create(
            name="Banque",
            account=Account.objects.create(code="512", name="Banque"),
            is_default=True,
        )
        self.supplier = Supplier.objects.create(name="Entreprise", created_by=self.user)

    def post(self, path, data, status=201):
        response = self.client.post(
            "/api/finance/" + path + "/",
            json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def get(self, path, **query):
        response = self.client.get("/api/finance/cycle/" + path + "/", query)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def call(self, value="200", kind="current", project=None):
        result = self.post(
            "calls",
            {
                "year": self.year.pk,
                "key": self.key.pk,
                "label": "Appel",
                "date": "2026-01-01",
                "due_date": "2026-01-10",
                "amount": value,
                "kind": kind,
                "project": project.pk if project else "",
                "decision": "AG financement" if project else "",
            },
        )
        self.post(f'calls/{result["id"]}/publish', {}, 200)
        return FundCall.objects.get(pk=result["id"])

    def expense(self, value="150", project=None):
        result = self.post(
            "expenses",
            {
                "year": self.year.pk,
                "key": self.key.pk,
                "supplier_record": self.supplier.pk,
                "reference": "F001",
                "label": "Facture",
                "date": "2026-02-01",
                "amount": value,
                "project": project.pk if project else "",
            },
        )
        return Expense.objects.get(pk=result["id"])

    def reg(self):
        preview = self.get("regularization", year=self.year.pk)["preview"]
        return self.post(
            "cycle/regularization",
            {
                "year": self.year.pk,
                "source_hash": preview["source_hash"],
                "decision": "AG approbation",
                "approved_on": "2027-01-15",
            },
        )

    def close(self, year=None, next_year=None):
        year = year or self.year
        next_year = next_year or self.next
        preview = self.get("close", year=year.pk)
        self.assertEqual(preview["errors"], [])
        return self.post(
            "cycle/close",
            {
                "year": year.pk,
                "next_year": next_year.pk,
                "source_hash": preview["source_hash"],
            },
        )

    def test_complete_current_cycle_carry_and_supplier_payment_next_year(self):
        call = self.call()
        expense = self.expense()
        for owner in self.owners:
            self.post(
                "receipts",
                {
                    "year": self.year.pk,
                    "owner": owner.pk,
                    "date": "2026-03-01",
                    "amount": "60",
                    "bank": self.bank.pk,
                },
            )
        self.assertEqual(len(ChargeAllocation.objects.all()), 2)
        self.assertEqual(
            Decimal(regularization_data(self.year)["total"]), Decimal("-50")
        )
        self.reg()
        statement = self.post(
            "cycle/statements",
            {
                "bank": self.bank.pk,
                "starts_on": "2026-01-01",
                "ends_on": "2026-12-31",
                "opening_balance": "0",
                "closing_balance": "120",
                "csv": "date;libelle;montant;reference\n2026-03-01;Versement A;60;A\n2026-03-01;Versement B;60;B\n",
            },
        )
        statement_rows = list(
            StatementLine.objects.filter(statement_id=statement["id"])
        )
        bank_lines = list(Line.objects.filter(account=self.bank.account))
        for row, line in zip(statement_rows, bank_lines):
            self.post(f"cycle/bank-match/{row.pk}", {"line_ids": [str(line.pk)]}, 200)
        self.post(f'cycle/validate-statement/{statement["id"]}', {}, 200)
        self.close()
        self.year.refresh_from_db()
        self.assertTrue(self.year.closed)
        self.assertEqual(YearClosure.objects.count(), 1)
        self.assertEqual(Entry.objects.filter(year=self.next, kind="carry").count(), 1)
        self.assertEqual(
            Decimal(
                next(r for r in balance(self.next) if r["code"] == "401")["balance"]
            ),
            Decimal("-150"),
        )
        self.post(
            f"expenses/{expense.pk}/pay",
            {
                "year": self.next.pk,
                "date": "2027-02-01",
                "amount": "50",
                "bank": self.bank.pk,
            },
            200,
        )
        self.assertEqual(Settlement.objects.filter(active=True).count(), 1)
        response = self.client.get("/api/finance/banks/", {"date": "2027-02-01"}).json()
        self.assertEqual(Decimal(response["items"][0]["balance"]), Decimal("70"))
        # A rerun cannot add a second carry or reopen the immutable snapshot.
        self.post(
            "cycle/close",
            {"year": self.year.pk, "next_year": self.next.pk, "source_hash": "x"},
            400,
        )
        self.assertEqual(Entry.objects.filter(kind="carry").count(), 1)

    def test_snapshot_survives_share_and_owner_changes_and_stale_preview_rejected(self):
        self.call()
        self.expense()
        self.lots[0].shares = 9
        self.lots[0].owner = self.owners[1]
        self.lots[0].save()
        rows = regularization_data(self.year)["rows"]
        self.assertEqual(
            [Decimal(r["actual"]) for r in rows], [Decimal("75"), Decimal("75")]
        )
        self.assertEqual(rows[0]["owner"], self.owners[1].pk)
        self.assertEqual(
            ChargeAllocation.objects.get(lot=self.lots[0]).owner_id, self.owners[0].pk
        )
        self.post(
            "cycle/regularization",
            {
                "year": self.year.pk,
                "source_hash": "stale",
                "decision": "AG",
                "approved_on": "2027-01-01",
            },
            400,
        )
        self.assertFalse(AnnualSettlement.objects.exists())

    def test_initial_balance_is_balanced_identified_and_once(self):
        invalid = {
            "year": self.year.pk,
            "lines": [
                {"code": "512", "debit": "100"},
                {"code": "450", "credit": "100"},
            ],
        }
        self.post("cycle/opening", invalid, 400)
        invalid["lines"][1]["owner"] = self.owners[0].pk
        self.post("cycle/opening", invalid)
        self.post("cycle/opening", invalid, 400)
        self.assertEqual(Entry.objects.filter(kind="opening").count(), 1)
        self.assertFalse(self.get("allocation", year=self.year.pk)["rows"])

    def test_reconciliation_rejects_wrong_amount_duplicate_and_closed_changes(self):
        self.post(
            "receipts",
            {
                "year": self.year.pk,
                "owner": self.owners[0].pk,
                "date": "2026-01-05",
                "amount": "100",
            },
        )
        data = {
            "bank": self.bank.pk,
            "starts_on": "2026-01-01",
            "ends_on": "2026-12-31",
            "opening_balance": "0",
            "closing_balance": "100",
            "csv": "date;libelle;montant;reference\n05/01/2026;Virement;100,00;V1\n",
        }
        statement = self.post("cycle/statements", data)
        again = self.post("cycle/statements", data, 200)
        self.assertEqual(statement["id"], again["id"])
        row = StatementLine.objects.get()
        line = Line.objects.get(account=self.bank.account)
        self.post(f'cycle/validate-statement/{statement["id"]}', {}, 400)
        self.post(f"cycle/bank-match/{row.pk}", {"line_ids": [line.pk, line.pk]}, 400)
        self.post(f"cycle/bank-match/{row.pk}", {"line_ids": [line.pk]}, 200)
        self.post(f"cycle/bank-match/{row.pk}", {"line_ids": [line.pk]}, 400)
        self.post(f'cycle/validate-statement/{statement["id"]}', {}, 200)
        self.post(f"cycle/bank-unmatch/{row.pk}", {}, 400)
        self.year.closed = True
        self.year.save()
        self.post(f'cycle/unlock-statement/{statement["id"]}', {}, 400)

    def test_lettering_partial_cross_year_and_asof_age(self):
        call = self.call()
        debit = call.entry.lines.get(owner=self.owners[0])
        receipt = self.post(
            "receipts",
            {
                "year": self.next.pk,
                "owner": self.owners[0].pk,
                "date": "2027-01-05",
                "amount": "40",
            },
        )
        credit = Receipt.objects.get(pk=receipt["id"]).entry.lines.get(
            owner=self.owners[0]
        )
        self.post(
            "cycle/lettering",
            {"debit_line": debit.pk, "credit_line": credit.pk, "amount": "40"},
        )
        self.post(
            "cycle/lettering",
            {"debit_line": debit.pk, "credit_line": credit.pk, "amount": "1"},
            400,
        )
        old = self.get("outstanding", date="2026-12-31")["rows"]
        self.assertEqual(
            Decimal(next(r for r in old if r["id"] == debit.pk)["remaining"]),
            Decimal("100"),
        )
        current = self.get("outstanding", date="2027-01-06")["rows"]
        self.assertEqual(
            Decimal(next(r for r in current if r["id"] == debit.pk)["remaining"]),
            Decimal("60"),
        )

    def test_reg_cancel_preserves_original_and_freezes_new_charges(self):
        self.call()
        self.expense()
        item = self.reg()
        self.post(
            "expenses",
            {
                "year": self.year.pk,
                "key": self.key.pk,
                "supplier": "Autre",
                "reference": "F2",
                "label": "Autre",
                "date": "2026-03-01",
                "amount": "10",
            },
            400,
        )
        self.post(f'cycle/undo-regularization/{item["id"]}', {"year": self.year.pk})
        self.assertEqual(Entry.objects.filter(kind="regularization").count(), 2)
        self.assertFalse(AnnualSettlement.objects.filter(active=True).exists())
        self.reg()

    def test_unfinished_works_carry_120_then_completion_balances(self):
        p = FinanceProject.objects.create(
            name="Toiture", key=self.key, budget=100, decision="AG"
        )
        self.call("100", "works", p)
        self.expense("60", p)
        self.close()
        carried = next(r for r in balance(self.next) if r["code"] == "120")
        self.assertEqual(Decimal(carried["balance"]), Decimal("60"))
        self.post(
            f"cycle/project-complete/{p.pk}",
            {
                "year": self.next.pk,
                "date": "2027-01-20",
                "decision": "AG approbation travaux",
            },
        )
        p.refresh_from_db()
        self.assertIsNotNone(p.completed_on)
        totals = {r["code"]: Decimal(r["balance"]) for r in balance(self.next)}
        self.assertEqual(totals["120"], 0)
        self.assertEqual(totals["102"], 0)
        self.assertEqual(totals["671"] + totals["702"], 0)
        self.assertEqual(totals["450"], Decimal("60"))

    def test_fund_requires_paid_and_stays_attached_to_lot(self):
        self.bank.kind = "works"
        self.bank.save(update_fields=["kind"])
        call = self.call("100", "fund")
        p = FinanceProject.objects.create(
            name="Toiture", key=self.key, budget=100, decision="AG"
        )
        self.post(
            f"cycle/fund-use/{p.pk}",
            {
                "year": self.year.pk,
                "date": "2026-02-01",
                "amount": "40",
                "decision": "AG",
            },
            400,
        )
        for owner in self.owners:
            receipt = self.post(
                "receipts",
                {
                    "year": self.year.pk,
                    "date": "2026-02-01",
                    "amount": "50",
                    "owner": owner.pk,
                },
            )
            credit = Receipt.objects.get(pk=receipt["id"]).entry.lines.get(owner=owner)
            debit = call.entry.lines.get(owner=owner)
            self.post(
                "cycle/lettering",
                {"debit_line": debit.pk, "credit_line": credit.pk, "amount": "50"},
            )
        self.post(
            f"cycle/fund-use/{p.pk}",
            {
                "year": self.year.pk,
                "date": "2026-03-01",
                "amount": "40",
                "decision": "AG",
            },
        )
        self.assertEqual(
            [Decimal(r["available"]) for r in funds()], [Decimal("30"), Decimal("30")]
        )
        self.lots[0].owner = self.owners[1]
        self.lots[0].save()
        self.assertEqual(Decimal(funds()[0]["paid"]), Decimal("50"))

    def test_private_endpoints_and_fec(self):
        member = get_user_model().objects.create_user("member")
        owner = self.owners[0]
        owner.user = member
        owner.email = "member@example.test"
        owner.save()
        client = Client()
        client.force_login(member)
        for resource in [
            "context",
            "funds",
            "lettering",
            "outstanding",
            "statements",
            "bank-lines",
            "allocation",
            "close",
            "annexes",
            "fec",
        ]:
            self.assertEqual(
                client.get(
                    "/api/finance/cycle/" + resource + "/", {"year": self.year.pk}
                ).status_code,
                403,
            )
        self.call()
        response = self.client.get("/api/finance/cycle/fec/", {"year": self.year.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.content.decode().splitlines()[0].split("\t")), 18)

    def test_empty_year_can_close_but_wrong_successor_or_stale_hash_cannot(self):
        preview = self.get("close", year=self.year.pk)
        self.post(
            "cycle/close",
            {"year": self.year.pk, "next_year": self.next.pk, "source_hash": "stale"},
            400,
        )
        self.next.starts_on = date(2027, 1, 2)
        self.next.save()
        self.post(
            "cycle/close",
            {
                "year": self.year.pk,
                "next_year": self.next.pk,
                "source_hash": preview["source_hash"],
            },
            400,
        )
        self.next.starts_on = date(2027, 1, 1)
        self.next.save()
        self.close()

    def mutation(self, body):
        preview = self.post("cycle/preview-mutation", body, 200)
        self.assertEqual(OwnershipChange.objects.count(), 0)
        return self.post(
            "cycle/mutation", {**body, "source_hash": preview["source_hash"]}
        )

    def test_all_authenticated_read_pages_and_bad_csv_are_controlled(self):
        for resource in [
            "context",
            "funds",
            "lettering",
            "outstanding",
            "statements",
            "bank-lines",
            "allocation",
            "close",
            "annexes",
            "corrections",
            "mutations",
        ]:
            self.get(resource, year=self.year.pk)
        self.post(
            "cycle/statements",
            {
                "bank": self.bank.pk,
                "starts_on": "2026-01-01",
                "ends_on": "2026-12-31",
                "opening_balance": "0",
                "closing_balance": "0",
                "csv": "date;libelle;montant;reference\n2026-01-01;Erreur;abc;X\n",
            },
            400,
        )

    def test_schedule_exact_cents_retry_and_out_of_year_roll_back(self):
        import uuid

        body = {
            "year": self.year.pk,
            "key": self.key.pk,
            "request_id": str(uuid.uuid4()),
            "first_date": "2026-01-01",
            "amount": "100.01",
            "count": 4,
            "interval": 3,
            "label": "Provisions",
            "kind": "current",
        }
        result = self.post("cycle/call-schedule", body)
        self.assertEqual(
            sum(FundCall.objects.values_list("amount", flat=True)), Decimal("100.01")
        )
        self.assertEqual(FundCall.objects.filter(entry__isnull=True).count(), 4)
        self.assertEqual(self.post("cycle/call-schedule", body)["id"], result["id"])
        self.post("cycle/call-schedule", {**body, "amount": "100.02"}, 400)
        self.post(
            "cycle/call-schedule",
            {**body, "request_id": str(uuid.uuid4()), "first_date": "2026-10-01"},
            400,
        )
        self.assertEqual(FundCall.objects.count(), 4)

    def test_unpresented_cheque_can_close_and_match_in_following_year(self):
        self.post(
            "cycle/opening",
            {
                "year": self.year.pk,
                "lines": [
                    {"code": "512", "debit": "100"},
                    {"code": "450", "owner": self.owners[0].pk, "credit": "100"},
                ],
            },
        )
        expense = self.expense("30")
        self.post(
            f"expenses/{expense.pk}/pay",
            {"date": "2026-12-30", "amount": "30", "bank": self.bank.pk},
            200,
        )
        bank_line = ExpensePayment.objects.get().entry.lines.get(
            account=self.bank.account
        )
        statement = self.post(
            "cycle/statements",
            {
                "bank": self.bank.pk,
                "starts_on": "2026-01-01",
                "ends_on": "2026-12-31",
                "opening_balance": "100",
                "closing_balance": "100",
                "csv": "date;libelle;montant;reference\n",
            },
        )
        self.post(f'cycle/validate-statement/{statement["id"]}', {}, 400)
        self.post(
            f'cycle/validate-statement/{statement["id"]}',
            {
                "transit_reasons": {
                    str(bank_line.pk): "Chèque non présenté au 31 décembre"
                }
            },
            200,
        )
        self.reg()
        self.close()
        following = self.post(
            "cycle/statements",
            {
                "bank": self.bank.pk,
                "starts_on": "2027-01-01",
                "ends_on": "2027-01-31",
                "opening_balance": "100",
                "closing_balance": "70",
                "csv": "date;libelle;montant;reference\n2027-01-05;Chèque débité;-30;C1\n",
            },
        )
        row = StatementLine.objects.get(statement_id=following["id"])
        self.post(f"cycle/bank-match/{row.pk}", {"line_ids": [bank_line.pk]}, 200)
        self.post(f'cycle/validate-statement/{following["id"]}', {}, 200)

    def test_payment_correction_restores_invoice_without_deleting_it(self):
        expense = self.expense("100")
        self.post(
            f"expenses/{expense.pk}/pay", {"date": "2026-03-01", "amount": "100"}, 200
        )
        payment = ExpensePayment.objects.get()
        self.post(
            f"cycle/cancel-entry/{payment.entry_id}",
            {"year": self.year.pk, "date": "2026-03-01"},
            400,
        )
        self.post(f"cycle/unletter/{Settlement.objects.get().pk}", {}, 200)
        self.post(
            f"cycle/cancel-entry/{payment.entry_id}",
            {"year": self.year.pk, "date": "2026-03-01"},
        )
        expense.refresh_from_db()
        self.assertIsNone(expense.payment_entry_id)
        self.assertEqual(ExpensePayment.objects.count(), 1)
        self.post(
            f"expenses/{expense.pk}/pay", {"date": "2026-03-02", "amount": "100"}, 200
        )
        self.assertEqual(ExpensePayment.objects.count(), 2)

    def test_opening_supplier_debt_can_be_paid_and_lettered(self):
        self.post(
            "cycle/opening",
            {
                "year": self.year.pk,
                "lines": [
                    {"code": "512", "debit": "100"},
                    {"code": "401", "supplier": self.supplier.pk, "credit": "100"},
                ],
            },
        )
        source = Line.objects.get(account__code="401")
        self.post(
            f"cycle/pay-balance/{source.pk}",
            {
                "year": self.year.pk,
                "date": "2026-03-01",
                "amount": "40",
                "bank": self.bank.pk,
            },
        )
        self.assertEqual(Settlement.objects.get().amount, Decimal("40"))
        self.assertEqual(
            Decimal(self.get("lettering")["rows"][0]["remaining"]), Decimal("60")
        )

    def test_sale_reassigns_future_due_call_and_annual_adjustment(self):
        result = self.post(
            "calls",
            {
                "year": self.year.pk,
                "key": self.key.pk,
                "label": "Provision",
                "date": "2026-01-01",
                "due_date": "2026-12-01",
                "amount": "200",
            },
        )
        self.post(f'calls/{result["id"]}/publish', {}, 200)
        self.expense("150")
        body = {
            "lot": self.lots[0].pk,
            "new_owner": self.owners[1].pk,
            "effective_date": "2026-09-01",
            "reference": "Notification notariale",
        }
        mutation = self.mutation(body)
        self.lots[0].refresh_from_db()
        self.assertEqual(self.lots[0].owner_id, self.owners[1].pk)
        self.assertEqual(AllocationTransfer.objects.count(), 1)
        self.assertEqual(
            Settlement.objects.filter(credit_line__entry__kind="ownership").count(), 1
        )
        preview = self.get(
            "regularization", year=self.year.pk, approved_on="2027-01-15"
        )["preview"]
        self.assertTrue(all(r["owner"] == self.owners[1].pk for r in preview["rows"]))
        self.post(f'cycle/cancel-mutation/{mutation["id"]}', {}, 200)
        self.lots[0].refresh_from_db()
        self.assertEqual(self.lots[0].owner_id, self.owners[0].pk)
        self.assertEqual(Entry.objects.filter(kind="ownership").count(), 2)

    def test_sale_after_publication_uses_owner_at_approval_without_prorata(self):
        self.call()
        self.expense()
        self.mutation(
            {
                "lot": self.lots[0].pk,
                "new_owner": self.owners[1].pk,
                "effective_date": "2026-09-01",
                "reference": "Acte",
            }
        )
        early = self.get("regularization", year=self.year.pk, approved_on="2026-08-01")[
            "preview"
        ]["rows"]
        self.assertEqual(early[0]["owner"], self.owners[0].pk)
        later = self.get("regularization", year=self.year.pk, approved_on="2027-01-15")[
            "preview"
        ]["rows"]
        self.assertEqual(later[0]["owner"], self.owners[1].pk)
        self.assertEqual(Decimal(later[0]["adjustment"]), Decimal("-25"))
        response = self.client.patch(
            f"/api/lots/{self.lots[0].pk}/",
            json.dumps({"owner": self.owners[0].pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_retried_receipt_and_partial_payment_do_not_duplicate_money(self):
        import uuid

        body = {
            "year": self.year.pk,
            "owner": self.owners[0].pk,
            "date": "2026-03-01",
            "amount": "20",
            "request_id": str(uuid.uuid4()),
        }
        first = self.post("receipts", body)
        again = self.post("receipts", body)
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(Receipt.objects.count(), 1)
        self.post("receipts", {**body, "amount": "30"}, 400)
        expense = self.expense("100")
        payment = {
            "date": "2026-03-01",
            "amount": "20",
            "request_id": str(uuid.uuid4()),
        }
        first = self.post(f"expenses/{expense.pk}/pay", payment, 200)
        self.post(f"expenses/{expense.pk}/pay", payment, 200)
        self.assertEqual(ExpensePayment.objects.count(), 1)

    def test_correct_initial_balance_preserves_reversal_and_allows_new_opening(self):
        result = self.post(
            "cycle/opening",
            {
                "year": self.year.pk,
                "lines": [
                    {"code": "512", "debit": "100"},
                    {"code": "401", "supplier": self.supplier.pk, "credit": "100"},
                ],
            },
        )
        self.post(f'cycle/undo-opening/{result["id"]}', {"year": self.year.pk}, 201)
        self.post(
            "cycle/opening",
            {
                "year": self.year.pk,
                "lines": [
                    {"code": "512", "debit": "120"},
                    {"code": "401", "supplier": self.supplier.pk, "credit": "120"},
                ],
            },
        )
        self.assertEqual(Entry.objects.filter(kind="opening").count(), 3)
        self.assertEqual(
            Decimal(
                next(r for r in balance(self.year) if r["code"] == "512")["balance"]
            ),
            Decimal("120"),
        )

    def test_late_sale_and_cancel_correct_closed_regularization_in_open_year(self):
        self.call()
        self.expense()
        self.reg()
        self.close()
        mutation = self.mutation(
            {
                "lot": self.lots[0].pk,
                "new_owner": self.owners[1].pk,
                "effective_date": "2026-09-01",
                "reference": "Notification tardive",
            }
        )
        correction = RegularizationTransfer.objects.get().entry
        self.assertEqual(correction.year_id, self.next.pk)
        self.assertEqual(YearClosure.objects.count(), 1)
        self.post(f'cycle/cancel-mutation/{mutation["id"]}', {}, 200)
        self.assertTrue(
            Entry.objects.filter(reversal_of=correction, year=self.next).exists()
        )
        self.lots[0].refresh_from_db()
        self.assertEqual(self.lots[0].owner_id, self.owners[0].pk)

    def test_former_owner_keeps_personal_balance_but_not_shared_new_data(self):
        member = get_user_model().objects.create_user("seller")
        owner = self.owners[0]
        owner.user = member
        owner.email = "seller@example.test"
        owner.save()
        self.mutation(
            {
                "lot": self.lots[0].pk,
                "new_owner": self.owners[1].pk,
                "effective_date": "2026-09-01",
                "reference": "Vente",
            }
        )
        self.client.force_login(member)
        self.assertEqual(
            self.client.get("/api/operations/my-account/").status_code, 200
        )
        self.assertEqual(self.client.get("/api/overview/").status_code, 403)
