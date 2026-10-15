import json
import tempfile
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from core.models import Owner, Lot
from documents.models import Document, Version
from finance.models import FiscalYear, ChargeKey, Expense, ExpensePayment, Entry, Account, BankAccount
from operations.models import Case, Quote
from .models import CouncilSettings, Mandate, ExpenseDraft, ReviewRequest, Review, AccountControl, CouncilEvent


class CouncilTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.media.name)
        self.override.enable(); self.addCleanup(self.override.disable)
        User = get_user_model()
        self.admin = User.objects.create_user("admin", is_staff=True, is_superuser=True)
        self.client.force_login(self.admin)
        self.today = timezone.localdate()
        self.year = FiscalYear.objects.create(name=str(self.today.year), starts_on=self.today.replace(month=1, day=1), ends_on=self.today.replace(month=12, day=31))
        self.key = ChargeKey.objects.create(name="Charges générales")
        self.owner = self.person("Alice")
        self.second = self.person("Benoit")
        self.third = self.person("Claire")
        self.doc = Document.objects.create(title="Pièce de contrôle privée")
        self.proof = self.version(self.doc)
        self.doc.current = self.proof; self.doc.save()
        self.config = CouncilSettings.objects.create(pk=1)

    def person(self, name):
        user = get_user_model().objects.create_user(name.lower(), email=name.lower()+"@example.test")
        owner = Owner.objects.create(first_name=name, last_name="Exemple", email=user.email, user=user)
        Lot.objects.create(number=name, owner=owner, shares=100)
        return owner

    def version(self, doc):
        return Version.objects.create(document=doc, filename="controle.pdf", size=18, content_type="application/pdf", checksum="a"*64, created_by=self.admin, file=SimpleUploadedFile("controle.pdf", b"%PDF-1.4\nTest PDF\n"))

    def client_for(self, owner):
        c = Client(); c.force_login(owner.user if isinstance(owner, Owner) else owner); return c

    def send(self, path, data, client=None, method="post"):
        return getattr(client or self.client, method)("/api/"+path+"/", json.dumps(data), content_type="application/json")

    def grant(self, role="council", owner=None, **extra):
        data = {"role": role, "owner": (owner or self.owner).pk, "starts_on": str(self.today-timedelta(days=1)), "ends_on": str(self.today+timedelta(days=365)),
                "authority": "council" if role in ["president", "coop_syndic", "vice"] else "organisation" if role == "treasurer" else "ag",
                "proof": self.proof.pk, "reference": "Désignation documentée", "eligibility_confirmed": True, **extra}
        response = self.send("council/mandates", data)
        self.assertEqual(response.status_code, 201, response.content)
        return Mandate.objects.get(pk=response.json()["id"])

    def expense(self, value="100.00"):
        response = self.send("finance/expenses", {"year": self.year.pk, "key": self.key.pk, "supplier": "Entreprise", "reference": "F-"+str(Expense.objects.count()),
            "label": "Nettoyage", "date": str(self.today), "amount": value, "document": self.doc.pk})
        self.assertEqual(response.status_code, 201, response.content)
        return Expense.objects.get(pk=response.json()["id"])

    def request(self, expense):
        r = self.send("council/requests", {"kind": "expense", "target": expense.pk})
        self.assertEqual(r.status_code, 201, r.content)
        return ReviewRequest.objects.get(pk=r.json()["id"])

    def opinion(self, request, owner=None, decision="approved", reason="Pièce examinée et montant vérifié"):
        return self.send(f"council/requests/{request.pk}/review", {"decision": decision, "reason": reason}, self.client_for(owner or self.owner))

    def pay(self, expense, value=None, client=None):
        return self.send(f"finance/expenses/{expense.pk}/pay", {"date": str(self.today), "amount": value}, client)

    def policy(self, count=1, threshold="0.00"):
        self.config.approval_enabled = True; self.config.required_approvals = count; self.config.threshold = Decimal(threshold); self.config.save()

    def test_ordinary_member_has_no_council_or_private_file_access(self):
        member = self.client_for(self.owner)
        for path in ["context", "requests", "records", "controls", f"files/{self.proof.pk}"]:
            self.assertEqual(member.get("/api/council/"+path+"/").status_code, 403)
        self.assertEqual(member.get("/api/documents/").status_code, 404)
        self.assertEqual(member.get("/api/documents/items/").json()["items"], [])
        self.assertEqual(member.get(f"/api/documents/versions/{self.proof.pk}/download/").status_code, 404)

    def test_council_reads_accounts_and_files_without_manager_mutations(self):
        self.grant(); e = self.expense(); c = self.client_for(self.owner)
        for kind in ["expenses", "balance", "ledger", "budget", "banks", "contracts", "documents", "history", "works", "statements"]:
            r = c.get(f"/api/council/records/?kind={kind}&year={self.year.pk}")
            self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(c.get(f"/api/council/files/{self.proof.pk}/").status_code, 200)
        self.assertEqual(c.get("/api/finance/expenses/").status_code, 403)
        self.assertEqual(self.pay(e, client=c).status_code, 403)
        self.assertEqual(self.send("council/settings", {}, c, "patch").status_code, 403)
        self.assertEqual(self.send("council/mandates", {}, c).status_code, 403)
        self.assertEqual(self.send("council/controls", {}, c).status_code, 403)
        self.assertEqual(ExpensePayment.objects.count(), 0)
        session = c.get("/api/session/").json()["user"]
        self.assertFalse(session["is_manager"])
        self.assertIn("expense.review", session["capabilities"])
        self.assertNotIn("access.admin", session["capabilities"])

    def test_expiry_future_revocation_and_lot_loss_remove_access(self):
        mandate = self.grant(); c = self.client_for(self.owner)
        self.assertEqual(c.get("/api/council/context/").status_code, 200)
        mandate.starts_on = self.today+timedelta(days=1); mandate.save()
        self.assertEqual(c.get("/api/council/context/").status_code, 403)
        mandate.starts_on = self.today-timedelta(days=5); mandate.ends_on = self.today-timedelta(days=1); mandate.save()
        self.assertEqual(c.get("/api/council/context/").status_code, 403)
        mandate.ends_on = self.today+timedelta(days=1); mandate.save()
        Lot.objects.filter(owner=self.owner).update(owner=None)
        self.assertEqual(c.get("/api/council/context/").status_code, 403)
        Lot.objects.filter(number="Alice").update(owner=self.owner)
        self.assertEqual(self.send(f"council/mandates/{mandate.pk}/revoke", {"reason": "Fin de mission"}).status_code, 200)
        self.assertEqual(c.get("/api/council/context/").status_code, 403)
        self.assertEqual(Mandate.objects.count(), 1)

    def test_grants_require_admin_eligibility_proof_dates_and_no_duplicates(self):
        raw = {"role": "council", "owner": self.owner.pk, "starts_on": str(self.today), "ends_on": str(self.today+timedelta(days=365)), "authority": "ag", "reference": "AG", "proof": self.proof.pk}
        self.assertEqual(self.send("council/mandates", raw).status_code, 400)
        raw["eligibility_confirmed"] = True
        raw["proof"] = None
        self.assertEqual(self.send("council/mandates", raw).status_code, 400)
        raw["proof"] = self.proof.pk; raw["ends_on"] = str(self.today-timedelta(days=1))
        self.assertEqual(self.send("council/mandates", raw).status_code, 400)
        self.grant()
        raw["ends_on"] = str(self.today+timedelta(days=365))
        self.assertEqual(self.send("council/mandates", raw).status_code, 400)
        self.assertEqual(Mandate.objects.count(), 1)

    def test_controller_cannot_combine_management_and_council(self):
        self.grant()
        raw = {"role": "controller", "owner": self.owner.pk, "starts_on": str(self.today), "ends_on": str(self.today+timedelta(days=300)), "authority": "ag", "reference": "AG", "proof": self.proof.pk, "eligibility_confirmed": True}
        self.assertEqual(self.send("council/mandates", raw).status_code, 400)
        controller = self.grant("controller", self.second)
        self.assertFalse(controller.user.is_staff)
        response = self.send(f"finance/manage/users/{self.second.user_id}", {"is_staff": True}, method="patch")
        self.assertEqual(response.status_code, 400, response.content)

    def test_cooperative_syndic_depends_on_council_seat_and_expiry(self):
        self.config.mode = "cooperative"; self.config.save()
        seat = self.grant()
        mandate = self.grant("coop_syndic", seat=seat.pk)
        c = self.client_for(self.owner)
        self.assertTrue(c.get("/api/session/").json()["user"]["is_manager"])
        self.assertEqual(c.get("/api/owners/").status_code, 200)
        self.assertFalse(self.owner.user.is_staff)
        self.assertEqual(self.send(f"council/mandates/{seat.pk}/revoke", {"reason": "Fin de désignation"}).status_code, 200)
        self.assertFalse(c.get("/api/session/").json()["user"]["is_manager"])
        self.assertEqual(c.get("/api/owners/").status_code, 403)

    def test_treasurer_prepares_without_posting_and_cannot_review_own_draft(self):
        self.grant("treasurer"); self.grant("council")
        c = self.client_for(self.owner)
        r = self.send("council/drafts", {"year": self.year.pk, "key": self.key.pk, "supplier": "Entreprise", "reference": "DRAFT", "label": "Entretien", "date": str(self.today), "amount": "75.00", "document": self.doc.pk}, c)
        self.assertEqual(r.status_code, 201, r.content); draft = ExpenseDraft.objects.get(pk=r.json()["id"])
        self.assertEqual(Entry.objects.count(), 0)
        r = self.send(f"council/drafts/{draft.pk}/submit", {}, c)
        self.assertEqual(r.status_code, 201, r.content)
        review = ReviewRequest.objects.get(pk=r.json()["id"])
        self.assertEqual(self.opinion(review).status_code, 400)
        self.assertEqual(self.send(f"council/drafts/{draft.pk}/post", {}, c).status_code, 403)
        self.assertEqual(Entry.objects.count(), 0)

    def test_mandated_syndic_uses_manager_api_and_cannot_grant_access(self):
        self.grant("syndic")
        c = self.client_for(self.owner)
        self.assertTrue(c.get("/api/session/").json()["user"]["is_manager"])
        self.assertEqual(c.get("/api/finance/manage/organization/").status_code, 200)
        self.assertEqual(self.send("council/mandates", {}, c).status_code, 403)
        self.assertEqual(self.send("finance/manage/users/1", {"is_staff": True}, c, "patch").status_code, 403)

    def test_policy_blocks_partial_payment_based_on_whole_invoice(self):
        self.policy(threshold="100.00"); expense = self.expense()
        self.assertEqual(self.pay(expense, "1.00").status_code, 400)
        self.assertEqual(ExpensePayment.objects.count(), 0)
        lower = self.expense("99.99")
        self.assertEqual(self.pay(lower).status_code, 200)

    def test_two_distinct_reviews_are_required_and_kept_with_reasons(self):
        self.policy(count=2); self.grant(); self.grant(owner=self.second)
        expense = self.expense(); request = self.request(expense)
        self.assertEqual(self.opinion(request, reason="").status_code, 400)
        self.assertEqual(self.opinion(request).status_code, 200)
        self.assertEqual(self.opinion(request).status_code, 400)
        self.assertEqual(self.pay(expense).status_code, 400)
        self.assertEqual(self.opinion(request, self.second).status_code, 200)
        self.assertEqual(self.pay(expense, "20.00").status_code, 200)
        self.assertEqual(self.pay(expense).status_code, 200)
        self.assertEqual(Review.objects.count(), 2)
        self.assertEqual(self.send(f"council/requests/{request.pk}/withdraw", {"reason": "Trop tard"}).status_code, 400)
        self.assertTrue(CouncilEvent.objects.filter(action="review.approved").exists())

    def test_refusal_and_existing_request_remain_blocking_when_policy_disabled(self):
        self.grant(); expense = self.expense(); request = self.request(expense)
        self.assertEqual(self.opinion(request, decision="rejected").status_code, 200)
        self.config.approval_enabled = False; self.config.save()
        self.assertEqual(self.pay(expense).status_code, 400)
        self.assertEqual(self.send(f"council/requests/{request.pk}/withdraw", {"reason": "Correction du dossier"}).status_code, 200)
        fresh = self.request(expense)
        self.assertEqual(self.opinion(fresh).status_code, 200)
        self.assertEqual(self.pay(expense).status_code, 200)
        self.assertEqual(ReviewRequest.objects.count(), 2)

    def test_quorum_cannot_be_lowered_on_open_request(self):
        self.policy(count=2); self.grant(); expense = self.expense(); r = self.request(expense)
        self.assertEqual(self.opinion(r).status_code, 200)
        self.config.required_approvals = 1; self.config.approval_enabled = False; self.config.save()
        self.assertEqual(self.pay(expense).status_code, 400)

    def test_new_document_version_invalidates_approval(self):
        self.grant(); e = self.expense(); r = self.request(e)
        self.assertEqual(self.opinion(r).status_code, 200)
        self.doc.current = self.version(self.doc); self.doc.save()
        self.assertEqual(self.pay(e).status_code, 400)
        self.assertEqual(self.client.get("/api/council/requests/").json()["items"][0]["state"], "stale")

    def test_full_draft_control_posting_and_payment(self):
        self.policy(); self.grant("treasurer"); self.grant(owner=self.second)
        c = self.client_for(self.owner)
        r = self.send("council/drafts", {"year": self.year.pk, "key": self.key.pk, "supplier": "Entreprise", "reference": "DRAFT", "label": "Entretien", "date": str(self.today), "amount": "75.00", "document": self.doc.pk}, c)
        d = ExpenseDraft.objects.get(pk=r.json()["id"])
        r = self.send(f"council/drafts/{d.pk}/submit", {}, c)
        review = ReviewRequest.objects.get(pk=r.json()["id"])
        self.assertEqual(self.send(f"council/drafts/{d.pk}/post", {}).status_code, 400)
        self.assertEqual(self.opinion(review, self.second).status_code, 200)
        result = self.send(f"council/drafts/{d.pk}/post", {})
        self.assertEqual(result.status_code, 201, result.content)
        e = Expense.objects.get(pk=result.json()["expense"])
        self.assertEqual(self.send(f"council/drafts/{d.pk}/post", {}).status_code, 400)
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(self.pay(e).status_code, 200)

    def test_quote_selection_requires_the_same_reviewed_quote(self):
        self.policy(); self.grant()
        case = Case.objects.create(kind="works", title="Toiture", created_by=self.admin)
        quote = Quote.objects.create(case=case, supplier="Couvreur", amount="100.00", document=self.doc)
        self.assertEqual(self.send(f"operations/quotes/{quote.pk}/select", {}).status_code, 400)
        r = self.send("council/requests", {"kind": "quote", "target": quote.pk})
        self.assertEqual(r.status_code, 201, r.content)
        item = ReviewRequest.objects.get(pk=r.json()["id"])
        self.assertEqual(self.opinion(item).status_code, 200)
        self.assertEqual(self.send(f"operations/quotes/{quote.pk}/select", {}).status_code, 200)

    def test_controller_report_frozen_and_changes_detected(self):
        self.grant("controller")
        c = self.client_for(self.owner)
        data = {"year": self.year.pk, "title": "Contrôle annuel", "observations": "Les pièces ont été examinées.", "checks": {k: True for k in ["books", "invoices", "banks", "allocation", "budget"]}, "evidence": [self.proof.pk]}
        r = self.send("council/controls", data, c)
        self.assertEqual(r.status_code, 201, r.content); pk = r.json()["id"]
        r = self.send(f"council/controls/{pk}/finalize", {"conclusion": "reserves"}, c)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(r.json()["changed_since_control"])
        self.assertEqual(self.send(f"council/controls/{pk}", {"observations": "Réécriture interdite"}, c, "patch").status_code, 400)
        self.expense()
        self.assertTrue(c.get("/api/council/controls/").json()["items"][0]["changed_since_control"])
        self.assertEqual(self.send(f"council/controls/{pk}", {"observations": "Modification par le syndic"}, method="patch").status_code, 403)

    def test_controller_cannot_finalize_accounts_they_previously_entered(self):
        e = self.expense(); Entry.objects.filter(pk=e.entry_id).update(created_by=self.owner.user)
        self.grant("controller"); c = self.client_for(self.owner)
        r = self.send("council/controls", {"year": self.year.pk, "title": "Rapport", "observations": "Compte examiné", "checks": {k: True for k in ["books", "invoices", "banks", "allocation", "budget"]}, "evidence": [self.proof.pk]}, c)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.send(f'council/controls/{r.json()["id"]}/finalize', {"conclusion": "favorable"}, c).status_code, 400)

    def test_external_account_requires_password_change_and_stops_at_end_of_mandate(self):
        response = self.send("council/mandates", {"role": "controller", "external_name": "Contrôleur extérieur", "external_email": "controle@example.test", "starts_on": str(self.today), "ends_on": str(self.today+timedelta(days=300)), "authority": "ag", "reference": "Désignation AG", "proof": self.proof.pk, "eligibility_confirmed": True})
        self.assertEqual(response.status_code, 201, response.content)
        m = Mandate.objects.get(pk=response.json()["id"])
        credentials = response.json()["credentials"]
        c = Client(); r = self.send("login", {"username": credentials["email"], "password": credentials["temporary_password"]}, c)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["user"]["must_change_password"])
        self.assertEqual(c.get("/api/council/context/").status_code, 403)
        # Password-change mechanics are already covered by core tests; enable the fixture account here.
        m.user.council_identity.must_change_password = False; m.user.council_identity.save()
        self.assertEqual(c.get("/api/council/context/").status_code, 200)
        m.ends_on = self.today-timedelta(days=1); m.starts_on = self.today-timedelta(days=10); m.save()
        self.assertEqual(c.get("/api/council/context/").status_code, 403)

    def test_settings_require_source_and_preserve_change_details(self):
        r = self.send("council/settings", {"approval_enabled": True, "reference": "Règle", "reason": "Mise en place"}, method="patch")
        self.assertEqual(r.status_code, 400)
        r = self.send("council/settings", {"approval_enabled": True, "threshold": "50", "required_approvals": 2, "reference": "Règle", "proof": self.proof.pk, "reason": "Mise en place"}, method="patch")
        self.assertEqual(r.status_code, 200, r.content)
        change = CouncilEvent.objects.get(action="settings.updated")
        self.assertFalse(change.details["before"]["approval_enabled"])
        self.assertTrue(change.details["after"]["approval_enabled"])

    def test_partially_paid_invoice_can_be_controlled_after_policy_enabled(self):
        e = self.expense()
        self.assertEqual(self.pay(e, "25.00").status_code, 200)
        self.policy(); self.grant()
        self.assertEqual(self.pay(e).status_code, 400)
        targets = self.client.get("/api/council/targets/?kind=expense").json()["items"]
        self.assertEqual([r["id"] for r in targets], [e.pk])
        r = self.request(e)
        self.assertEqual(self.opinion(r).status_code, 200)
        self.assertEqual(self.pay(e).status_code, 200)

    def test_target_search_excludes_existing_requests_and_is_manager_only(self):
        e = self.expense(); self.grant()
        self.assertEqual(self.client_for(self.owner).get("/api/council/targets/").status_code, 403)
        self.assertEqual(self.client.get("/api/council/targets/?q=Nettoyage").json()["count"], 1)
        self.assertEqual(self.client.get("/api/council/targets/?q=Inconnu").json()["count"], 0)
        self.request(e)
        self.assertEqual(self.client.get("/api/council/targets/").json()["count"], 0)

    def test_treasurer_upload_is_private_and_other_members_cannot_upload(self):
        self.grant("treasurer")
        c = self.client_for(self.owner)
        r = c.post("/api/council/upload/", {"title": "Facture préparée", "file": SimpleUploadedFile("facture.pdf", b"%PDF-1.4\nFacture de test\n")})
        self.assertEqual(r.status_code, 201, r.content)
        document = Document.objects.get(pk=r.json()["id"])
        self.assertFalse(document.published)
        self.assertEqual(self.client_for(self.second).get(f"/api/documents/items/{document.pk}/download/").status_code, 404)
        self.grant(owner=self.second)
        r = self.client_for(self.second).post("/api/council/upload/", {"title": "Interdit", "file": SimpleUploadedFile("x.pdf", b"%PDF-1.4")})
        self.assertEqual(r.status_code, 403)

    def test_draft_can_only_be_edited_before_submission_and_by_its_preparer(self):
        self.grant("treasurer"); self.grant("treasurer", owner=self.second)
        c = self.client_for(self.owner)
        data = {"year": self.year.pk, "key": self.key.pk, "supplier": "Entreprise", "reference": "DRAFT", "label": "Entretien", "date": str(self.today), "amount": "75.00", "document": self.doc.pk}
        r = self.send("council/drafts", data, c); pk = r.json()["id"]
        data["amount"] = "65.00"
        self.assertEqual(self.send(f"council/drafts/{pk}", data, self.client_for(self.second), "patch").status_code, 400)
        self.assertEqual(self.send(f"council/drafts/{pk}", data, c, "patch").status_code, 200)
        self.assertEqual(self.send(f"council/drafts/{pk}/submit", {}, c).status_code, 201)
        self.assertEqual(self.send(f"council/drafts/{pk}", data, c, "patch").status_code, 400)

    def test_mandate_can_be_imported_from_signed_ag_without_retyping_proof(self):
        from governance.models import Meeting, Resolution, AssemblyWorkflow, AssemblyVote, AssemblyDecision, AssemblyMandate
        meeting = Meeting.objects.create(title="AG source", scheduled_at=timezone.now()-timedelta(days=1), location="Salle", created_by=self.admin)
        workflow = AssemblyWorkflow.objects.create(meeting=meeting, phase="signed", minutes={"signed_proof": {"id": self.proof.pk}})
        resolution = Resolution.objects.create(meeting=meeting, position=1, title="Désignation du conseil", majority="article24")
        vote = AssemblyVote.objects.create(workflow=workflow, resolution=resolution, data={}, recorded_by=self.admin)
        decision = AssemblyDecision.objects.create(vote=vote, kind="council", data={"reference": "AG source / résolution 1"}, created_by=self.admin)
        source = AssemblyMandate.objects.create(decision=decision, owner=self.owner, kind="council", starts_on=self.today, ends_on=self.today+timedelta(days=365))
        mandate = self.grant(starts_on=str(source.starts_on), ends_on=str(source.ends_on), assembly_mandate=source.pk, proof=None)
        self.assertEqual(mandate.proof_id, self.proof.pk)
        self.assertEqual(mandate.assembly_mandate_id, source.pk)
        self.assertEqual(self.client.get("/api/council/context/").status_code, 200)

    def test_increasing_quorum_reopens_approval_in_ui_and_blocks_payment(self):
        self.grant(); e = self.expense(); r = self.request(e)
        self.assertEqual(self.opinion(r).status_code, 200)
        self.policy(count=2)
        data = self.client.get("/api/council/requests/").json()["items"][0]
        self.assertEqual(data["state"], "pending")
        self.assertEqual(data["required_approvals"], 2)
        self.assertEqual(self.pay(e).status_code, 400)
