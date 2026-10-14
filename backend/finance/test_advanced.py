import json
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase,Client
from core.models import Owner
from core.access import provision_access
from .models import Account,FiscalYear,CostCenter,Organization,Entry,Budget,Journal,AuditEvent


class AdvancedTests(TestCase):
    def setUp(self):
        self.admin=get_user_model().objects.create_superuser("admin",password="Admin-test-19!173")
        self.client.force_login(self.admin)
        self.year=FiscalYear.objects.create(name="2026",starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        for code,name in [("512","Banque"),("601","Charges"),("701","Provisions"),("450","Copropriétaires")]:Account.objects.create(code=code,name=name)

    def send(self,path,data,method="post",client=None):
        return getattr(client or self.client,method)("/api/finance/"+path+"/",json.dumps(data),content_type="application/json")

    def entry(self,day="2026-01-01",debit="512",credit="701",value="100",**extra):
        return self.send("entries",{"year":self.year.pk,"date":day,"label":"Test","journal":"OD","lines":[{"code":debit,"debit":value},{"code":credit,"credit":value}],**extra})

    def report(self,kind,**params):
        return self.client.get(f"/api/finance/reporting/{kind}/",{"year":self.year.pk,**params})

    def test_configuration_persists_and_code_length_enforced(self):
        result=self.send("manage/organization",{"name":"Résidence du test","code_length":4,"analytic_required":False,"default_today":False})
        self.assertEqual(result.status_code,200,result.content)
        self.assertEqual(Organization.objects.get(pk=1).name,"Résidence du test")
        self.assertEqual(self.send("manage/accounts",{"code":"602","name":"Court","active":True}).status_code,400)
        self.assertEqual(self.send("accounts",{"code":"602","name":"Court"}).status_code,400)
        self.assertEqual(self.send("manage/accounts",{"code":"6021","name":"Long","active":True}).status_code,201)

    def test_custom_journal_used_and_default_unique(self):
        response=self.send("manage/journals",{"code":"AV","name":"Avances","active":True})
        self.assertEqual(response.status_code,201)
        self.assertEqual(self.send(f"operations/default-journal/{response.json()['id']}",{}).status_code,200)
        self.assertEqual(Journal.objects.filter(is_default=True).count(),1)
        journals=self.client.get("/api/finance/manage/journals/").json()["items"]
        self.assertTrue(next(j for j in journals if j["code"]=="AV")["is_default"])
        self.assertEqual(self.entry(journal="AV").status_code,201)

    def test_analytic_required_and_report_filter(self):
        Organization.objects.create(pk=1,analytic_required=True)
        self.assertEqual(self.entry().status_code,400)
        center=CostCenter.objects.create(name="Ascenseur")
        self.assertEqual(self.entry(cost_center=center.pk).status_code,201)
        response=self.report("income",center=center.pk)
        self.assertEqual(response.json()["totals"]["products"],"100.00")
        other=CostCenter.objects.create(name="Toiture")
        self.assertEqual(self.report("income",center=other.pk).json()["rows"],[])

    def test_template_validation_and_application(self):
        invalid=self.send("manage/templates",{"name":"Déséquilibré","journal":"OD","lines":[{"code":"512","debit":"5"},{"code":"701","credit":"4"}]})
        self.assertEqual(invalid.status_code,400)
        response=self.send("manage/templates",{"name":"Provision","journal":"OD","lines":[{"code":"450","debit":"50"},{"code":"701","credit":"50"}]})
        self.assertEqual(response.status_code,201,response.content)
        result=self.send(f"operations/apply-template/{response.json()['id']}",{"year":self.year.pk,"date":"2026-04-01"})
        self.assertEqual(result.status_code,201)
        self.assertEqual(Entry.objects.count(),1)

    def test_manual_reversal_preserves_original_and_rejects_duplicate(self):
        original=self.entry().json()["id"]
        response=self.send(f"operations/reverse-entry/{original}",{"date":"2026-01-02"})
        self.assertEqual(response.status_code,201,response.content)
        self.assertEqual(Entry.objects.count(),2)
        self.assertEqual(Entry.objects.get(pk=response.json()["id"]).reversal_of_id,original)
        self.assertEqual(self.send(f"operations/reverse-entry/{original}",{"date":"2026-01-03"}).status_code,400)
        self.assertEqual(Decimal(self.report("income").json()["totals"]["result"]),0)

    def test_ledger_opening_and_cumulative_balance(self):
        self.entry(value="100")
        self.entry(day="2026-02-01",value="20")
        result=self.report("ledger",start="2026-02-01",prefix="512").json()
        self.assertEqual(len(result["rows"]),1)
        self.assertEqual(Decimal(result["rows"][0]["opening"]),100)
        self.assertEqual(Decimal(result["rows"][0]["balance"]),120)

    def test_income_sheet_budget_totals(self):
        self.entry(value="100")
        self.entry(day="2026-02-01",debit="601",credit="512",value="40")
        Budget.objects.create(year=self.year,account=Account.objects.get(code="601"),amount=50)
        income=self.report("income").json()
        self.assertEqual(Decimal(income["totals"]["result"]),60)
        charge=next(r for r in income["rows"] if r["code"]=="601")
        self.assertEqual(Decimal(charge["variance"]),-10)
        sheet=self.report("sheet").json()
        self.assertEqual(Decimal(sheet["totals"]["assets"]),60)
        self.assertEqual(Decimal(sheet["totals"]["difference"]),0)
        as_of=self.report("sheet",start="2026-02-01",end="2026-02-28").json()
        self.assertEqual(as_of["start"],"2026-01-01")
        self.assertEqual(Decimal(as_of["totals"]["assets"]),60)

    def test_report_invalid_dates_and_export_safety(self):
        self.assertEqual(self.report("ledger",start="2025-12-31").status_code,400)
        self.assertEqual(self.report("sheet",prefix="abc").status_code,400)
        self.entry(label="=DANGEROUS()")
        response=self.report("ledger",format="csv")
        self.assertEqual(response.status_code,200)
        self.assertIn("'=DANGEROUS()",response.content.decode())

    def test_used_account_code_cannot_be_renamed(self):
        self.entry()
        account=Account.objects.get(code="512")
        self.assertEqual(self.send(f"manage/accounts/{account.pk}",{"code":"513"},method="patch").status_code,400)
        self.assertEqual(self.send(f"manage/accounts/{account.pk}",{"name":"Banque principale"},method="patch").status_code,200)

    def test_member_denied_management_and_private_reports(self):
        owner=Owner.objects.create(first_name="Alice",last_name="Test",email="alice@example.test")
        provision_access(owner);owner.must_change_password=False;owner.save()
        client=Client();client.force_login(owner.user)
        for path in ["manage/organization","manage/accounts","manage/users","manage/audit","reporting/ledger"]:
            self.assertEqual(client.get(f"/api/finance/{path}/",{"year":self.year.pk}).status_code,403)

    def test_superuser_protection_and_staff_cannot_promote_users(self):
        self.assertEqual(self.send(f"manage/users/{self.admin.pk}",{"is_active":False},method="patch").status_code,400)
        staff=get_user_model().objects.create_user("staff",password="Staff-pass-19!",is_staff=True)
        client=Client();client.force_login(staff)
        self.assertEqual(self.send(f"manage/users/{staff.pk}",{"is_staff":True},method="patch",client=client).status_code,403)

    def test_chart_initialization_idempotent_and_audited(self):
        result=self.send("operations/initialize-chart/1",{})
        self.assertEqual(result.status_code,200,result.content)
        self.assertGreater(Account.objects.count(),40)
        self.assertEqual(Account.objects.get(code="512").name,"Banque")
        self.assertEqual(self.send("operations/initialize-chart/1",{}).json()["created"],0)
        self.assertTrue(AuditEvent.objects.filter(action="chart.initialize").exists())

    def test_auxiliary_balances_include_opening_and_stay_private(self):
        owner=Owner.objects.create(first_name="Alice",last_name="Test",email="alice@example.test")
        response=self.send("entries",{"year":self.year.pk,"date":"2026-01-01","label":"Provision","lines":[{"code":"450","owner":owner.pk,"debit":"100"},{"code":"701","credit":"100"}]})
        self.assertEqual(response.status_code,201)
        self.assertEqual(self.send("receipts",{"year":self.year.pk,"date":"2026-02-01","owner":owner.pk,"amount":"40"}).status_code,201)
        result=self.report("auxiliary",start="2026-02-01").json()
        self.assertEqual(len(result["rows"]),1)
        self.assertEqual(Decimal(result["rows"][0]["opening"]),100)
        self.assertEqual(Decimal(result["rows"][0]["credit"]),40)
        self.assertEqual(Decimal(result["rows"][0]["balance"]),60)
        provision_access(owner);owner.must_change_password=False;owner.save()
        member=Client();member.force_login(owner.user)
        self.assertEqual(member.get("/api/finance/reporting/auxiliary/",{"year":self.year.pk}).status_code,403)

    def test_entries_query_count_does_not_grow_per_entry(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.entry()
        with CaptureQueriesContext(connection) as first:
            self.assertEqual(self.client.get("/api/finance/entries/").status_code,200)
        for i in range(5):self.entry()
        with CaptureQueriesContext(connection) as many:
            response=self.client.get("/api/finance/entries/")
        self.assertEqual(len(response.json()["items"]),6)
        self.assertEqual(len(first),len(many))
