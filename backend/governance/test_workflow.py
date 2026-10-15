import json
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase
from core.models import Owner, Lot
from documents.models import Document, Version
from finance.models import ChargeKey, FundCall, FiscalYear
from .models import Meeting, Resolution, AssemblyWorkflow, AssemblyVote
from .deadlines import latest_notification, notice_expires
from .templates import TEMPLATES


class DeadlineTests(SimpleTestCase):
    def test_notice_excludes_notification_day_and_extends_weekend(self):
        self.assertEqual(notice_expires(date(2026, 10, 10)), date(2026, 11, 2))
        self.assertLess(
            notice_expires(latest_notification(date(2026, 11, 1))), date(2026, 11, 1)
        )


class AssemblyWorkflowTests(TestCase):
    def setUp(self):
        self.today = date(2026, 10, 14)
        clock = patch(
            "governance.workflow.timezone.localdate", side_effect=lambda: self.today
        )
        clock.start()
        self.addCleanup(clock.stop)
        now = patch(
            "governance.workflow.timezone.now",
            side_effect=lambda: datetime.combine(
                self.today, datetime.min.time(), dt_timezone.utc
            ),
        )
        now.start()
        self.addCleanup(now.stop)
        self.user = get_user_model().objects.create_user("manager", is_staff=True)
        self.client.force_login(self.user)
        self.owners = [
            Owner.objects.create(
                first_name=f"Test{i}", last_name="Owner", email=f"owner{i}@example.test"
            )
            for i in range(3)
        ]
        self.lots = [
            Lot.objects.create(number=str(i), owner=owner, shares=shares)
            for i, (owner, shares) in enumerate(zip(self.owners, [60, 20, 20]))
        ]
        self.meeting = Meeting.objects.create(
            title="Assemblée annuelle",
            scheduled_at=datetime(2026, 11, 21, 14, tzinfo=dt_timezone.utc),
            location="Salle commune",
            created_by=self.user,
            roster=[
                {
                    "owner_id": o.pk,
                    "name": str(o),
                    "shares": str(l.shares),
                    "attendance": "absent",
                }
                for o, l in zip(self.owners, self.lots)
            ],
        )
        self.resolution = Resolution.objects.create(
            meeting=self.meeting,
            position=1,
            title="Décision test",
            text="Le syndicat adopte la décision test.",
            majority="24",
        )
        doc = Document.objects.create(title="Justificatif")
        self.proof = Version.objects.create(
            document=doc,
            file="tests/proof.pdf",
            filename="preuve.pdf",
            size=100,
            content_type="application/pdf",
            checksum="a" * 64,
            created_by=self.user,
        )
        self.year = FiscalYear.objects.create(
            name="2027", starts_on=date(2027, 1, 1), ends_on=date(2027, 12, 31)
        )
        self.key = ChargeKey.objects.create(name="Générales")

    def act(self, action, data=None, status=200):
        # The simulated assembly advances the clock past the session lifetime.
        self.client.force_login(self.user)
        response = self.client.post(
            f"/api/ag/meetings/{self.meeting.pk}/workflow/{action}/",
            json.dumps(data or {}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def freeze(self):
        config = {
            "organizer": "Syndic bénévole",
            "return_address": "Adresse du syndic",
            "consultation": "Salle commune, sur rendez-vous, avant l’AG",
            "legal_checked": True,
            "contacts": {
                f"owner:{o.pk}": {"address": f"Adresse {i}"}
                for i, o in enumerate(self.owners)
            },
        }
        self.act("configure", {"config": config})
        return self.act("freeze")

    def invite(self):
        for owner in self.owners:
            self.act(
                "delivery",
                {
                    "kind": "invitation",
                    "elector": f"owner:{owner.pk}",
                    "method": "lrar",
                    "sent_on": str(self.today),
                    "effective_on": str(self.today),
                    "proof": self.proof.pk,
                    "reference": "LRAR test",
                    "proof_checked": True,
                },
            )

    def attend(self, statuses=None):
        rows = [
            {
                "elector": f"owner:{o.pk}",
                "attendance": (statuses or {}).get(i, "present"),
            }
            for i, o in enumerate(self.owners)
        ]
        return self.act("participants", {"participants": rows})

    def start(self):
        self.today = date(2026, 11, 21)
        return self.act(
            "start",
            {
                "president": f"owner:{self.owners[0].pk}",
                "secretary": str(self.owners[1]),
                "president_eligible": True,
                "attendance_checked": True,
                "bureau_elected": True,
            },
        )

    def vote(self, **extra):
        return self.act(
            "vote",
            {
                "resolution": self.resolution.pk,
                "choices": {
                    f"owner:{o.pk}": "for" if i < 2 else "against"
                    for i, o in enumerate(self.owners)
                },
                **extra,
            },
        )

    def sign(self):
        self.act("minutes", {"reviewed": True, "remarks": "Réserves de séance"})
        return self.act(
            "sign",
            {
                "signed_on": str(self.today),
                "signed_proof": self.proof.pk,
                "attendance_proof": self.proof.pk,
                "signatures_checked": True,
            },
        )

    def test_complete_assembly_invitation_votes_signatures_notifications_and_drafts(
        self,
    ):
        data = self.freeze()
        self.assertEqual(
            Decimal(data["packet"]["electors"][0]["shares"]), Decimal("40")
        )
        self.invite()
        self.attend()
        self.start()
        data = self.vote()
        self.assertTrue(data["votes"][0]["result"]["adopted"])
        self.act("vote", {"resolution": self.resolution.pk, "choices": {}}, 400)
        data = self.sign()
        self.assertEqual(data["phase"], "signed")
        self.assertEqual(
            data["minutes"]["required_notifications"], [f"owner:{self.owners[2].pk}"]
        )
        self.act("close", {"reviewed": True}, 400)
        self.act(
            "delivery",
            {
                "kind": "minutes",
                "elector": f"owner:{self.owners[2].pk}",
                "method": "lre",
                "sent_on": str(self.today),
                "effective_on": str(self.today),
                "proof": self.proof.pk,
                "reference": "Notification du PV",
                "proof_checked": True,
            },
        )
        self.act("publish", {"published": True})
        data = self.act(
            "execute",
            {
                "vote": data["votes"][0]["id"],
                "kind": "current",
                "year": self.year.pk,
                "key": self.key.pk,
                "label": "Budget voté",
                "amount": "100.01",
                "date": "2027-01-01",
                "count": 4,
                "months": 3,
                "reviewed": True,
            },
        )
        self.assertEqual(FundCall.objects.count(), 4)
        self.assertEqual(
            sum(FundCall.objects.values_list("amount", flat=True)), Decimal("100.01")
        )
        self.assertFalse(FundCall.objects.filter(entry__isnull=False).exists())
        self.act("close", {"reviewed": True})
        self.meeting.refresh_from_db()
        self.assertTrue(self.meeting.archived)
        self.assertEqual(
            self.client.get("/api/ag/summaries/").json()["items"][0]["resolutions"][0][
                "adopted"
            ],
            True,
        )

    def test_frozen_agenda_and_roster_cannot_be_changed_by_legacy_endpoints(self):
        self.freeze()
        response = self.client.patch(
            f"/api/ag/meetings/{self.meeting.pk}/",
            json.dumps({"location": "Autre salle"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(
            f"/api/ag/resolutions/{self.resolution.pk}/",
            json.dumps({"majority": "25"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.act("configure", {"config": {}}, 400)

    def test_late_invitation_and_missing_proofs_are_blocked(self):
        self.freeze()
        self.today = date(2026, 11, 10)
        self.act(
            "delivery",
            {
                "kind": "invitation",
                "elector": f"owner:{self.owners[0].pk}",
                "method": "lrar",
                "sent_on": str(self.today),
                "effective_on": str(self.today),
                "proof": self.proof.pk,
                "reference": "Trop tard",
                "proof_checked": True,
            },
            400,
        )
        self.attend()
        self.today = date(2026, 11, 21)
        self.act(
            "start",
            {
                "president": f"owner:{self.owners[0].pk}",
                "secretary": "S",
                "president_eligible": True,
                "attendance_checked": True,
                "bureau_elected": True,
            },
            400,
        )

    def test_proxy_correspondence_amendment_and_each_vote_keeps_its_presence(self):
        self.freeze()
        self.invite()
        rows = [
            {"elector": f"owner:{self.owners[0].pk}", "attendance": "present"},
            {
                "elector": f"owner:{self.owners[1].pk}",
                "attendance": "represented",
                "representative_id": f"owner:{self.owners[0].pk}",
                "representative": "Test",
                "proof": self.proof.pk,
                "eligible": True,
            },
            {
                "elector": f"owner:{self.owners[2].pk}",
                "attendance": "correspondence",
                "proof": self.proof.pk,
                "received_on": str(self.today),
                "choices": {str(self.resolution.pk): "for"},
            },
        ]
        self.act("participants", {"participants": rows})
        self.start()
        data = self.act(
            "vote",
            {
                "resolution": self.resolution.pk,
                "choices": {f"owner:{o.pk}": "for" for o in self.owners[:2]},
                "amendment": "Le syndicat adopte le texte modifié.",
            },
        )
        self.assertEqual(
            data["votes"][0]["correspondents_deemed_absent"],
            [f"owner:{self.owners[2].pk}"],
        )
        from .workflow import minutes_data
        wf=AssemblyWorkflow.objects.get(meeting=self.meeting)
        minutes=minutes_data(wf)
        self.assertEqual(len(minutes['resolutions'][0]['groups']['deemed_default']),1)
        self.assertFalse(minutes['resolutions'][0]['groups']['absent'])
        self.assertIn('sans ses annexes',minutes['appeal_notice'])
        rows[1]["proof"] = {"id": self.proof.pk}
        rows[2] = {"elector": f"owner:{self.owners[2].pk}", "attendance": "present"}
        self.act("participants", {"participants": rows})
        first = AssemblyVote.objects.get()
        self.assertEqual(first.data["input"]["roster"][2]["attendance"], "absent")

    def test_second_vote_distinct_correction_retained_and_signed_pv_is_locked(self):
        self.resolution.majority = "25"
        self.resolution.save()
        self.freeze()
        self.invite()
        self.attend()
        self.start()
        choices = {
            f"owner:{o.pk}": "for" if i == 0 else "against"
            for i, o in enumerate(self.owners)
        }
        data = self.act("vote", {"resolution": self.resolution.pk, "choices": choices})
        self.assertEqual(data["votes"][0]["result"]["bridge"], "25-1")
        self.vote(tour=2)
        self.assertEqual(AssemblyVote.objects.count(), 2)
        self.act(
            "void-vote", {"vote": data["votes"][0]["id"], "reason": "Correction"}, 400
        )
        self.sign()
        self.act(
            "void-vote",
            {"vote": data["votes"][0]["id"], "reason": "Modification tardive"},
            400,
        )
        self.act("revise-minutes", {"reason": "Tardif"}, 400)

    def test_two_owner_regime_keeps_raw_shares_and_absolute_two_thirds(self):
        self.lots[2].delete()
        self.owners[2].delete()
        self.owners = self.owners[:2]
        self.lots[0].shares = 70
        self.lots[0].save()
        self.lots[1].shares = 30
        self.lots[1].save()
        self.meeting.roster = [
            {
                "owner_id": o.pk,
                "name": str(o),
                "shares": str(l.shares),
                "attendance": "absent",
            }
            for o, l in zip(self.owners, self.lots)
        ]
        self.meeting.save()
        self.resolution.majority = "25"
        self.resolution.save()
        data = self.freeze()
        self.assertTrue(data["packet"]["two_owners"])
        self.assertEqual(data["packet"]["electors"][0]["shares"], "70")
        self.invite()
        self.attend()
        self.start()
        data = self.act(
            "vote",
            {
                "resolution": self.resolution.pk,
                "choices": {
                    f"owner:{o.pk}": "for" if i == 0 else "against"
                    for i, o in enumerate(self.owners)
                },
            },
        )
        self.assertTrue(data["votes"][0]["result"]["adopted"])
        self.assertIsNone(data["votes"][0]["result"]["bridge"])

    def test_member_cannot_read_management_and_unpublished_summaries_are_private(self):
        user = get_user_model().objects.create_user("member")
        self.owners[0].user = user
        self.owners[0].save()
        self.client.force_login(user)
        self.assertEqual(
            self.client.get(
                f"/api/ag/meetings/{self.meeting.pk}/workflow/"
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/ag/summaries/").json()["items"], [])

    def test_budget_posts_and_mandate_are_linked_to_signed_adopted_vote(self):
        from .models import AssemblyMandate
        from finance.models import Budget

        self.resolution.majority = "25"
        self.resolution.save()
        self.freeze()
        self.invite()
        self.attend()
        self.start()
        data = self.vote()
        self.sign()
        vote = data["votes"][0]["id"]
        body = {
            "vote": vote,
            "kind": "syndic",
            "owner": self.owners[0].pk,
            "starts_on": "2026-11-21",
            "ends_on": "2030-01-01",
            "reviewed": True,
        }
        self.act("execute", body, 400)
        self.act("execute", {**body, "ends_on": "2029-11-21"})
        self.assertEqual(AssemblyMandate.objects.get().decision.vote_id, vote)
        self.act("execute", {**body, "ends_on": "2029-11-21"}, 400)

    def test_budget_duplicate_posts_roll_back_then_valid_budget_records_source(self):
        from finance.models import Budget

        self.freeze()
        self.invite()
        self.attend()
        self.start()
        data = self.vote()
        self.sign()
        row = {"code": "601", "key": self.key.pk, "amount": "90"}
        body = {
            "vote": data["votes"][0]["id"],
            "kind": "budget",
            "year": self.year.pk,
            "lines": [row, row],
            "reviewed": True,
        }
        self.act("execute", body, 400)
        self.assertFalse(Budget.objects.exists())
        self.act("execute", {**body, "lines": [row]})
        self.assertEqual(Budget.objects.get().amount, Decimal("90"))

    def test_accounts_approval_uses_assembly_date_and_signed_decision(self):
        from finance.cycle import regularization_data
        from finance.models import AnnualSettlement

        prior = FiscalYear.objects.create(
            name="2025", starts_on=date(2025, 1, 1), ends_on=date(2025, 12, 31)
        )
        self.freeze()
        self.invite()
        self.attend()
        self.start()
        data = self.vote()
        self.sign()
        preview = regularization_data(prior, self.today)
        self.act(
            "execute",
            {
                "vote": data["votes"][0]["id"],
                "kind": "accounts",
                "year": prior.pk,
                "source_hash": preview["source_hash"],
                "reviewed": True,
            },
        )
        settlement = AnnualSettlement.objects.get()
        self.assertEqual(settlement.approved_on, self.today)
        self.assertIn("résolution 1", settlement.decision)

    def test_appeal_and_metrics_keep_recorded_proof_and_updates(self):
        from .models import AssemblyAppeal

        self.freeze()
        self.invite()
        self.attend()
        self.start()
        self.vote()
        self.sign()
        data = self.act(
            "appeal",
            {
                "elector": f"owner:{self.owners[2].pk}",
                "resolution": self.resolution.pk,
                "filed_on": str(self.today),
                "reference": "Recours test",
                "proof": self.proof.pk,
                "notes": "À suivre",
            },
        )
        appeal = data["appeals"][0]
        metrics = self.client.get("/api/operations/metrics/")
        self.assertEqual(metrics.status_code, 200)
        self.assertTrue(
            any(
                a["title"] == "Contestations à suivre" for a in metrics.json()["alerts"]
            )
        )
        self.act(
            "appeal-update",
            {"appeal": appeal["id"], "status": "resolved", "notes": "Issue documentée"},
        )
        self.assertEqual(AssemblyAppeal.objects.get().status, "resolved")

    def test_template_documents_and_structured_configuration_are_required(self):
        self.resolution.title = "Approbation des comptes"
        self.resolution.save()
        data = self.act("configure", {"config": {"contacts": []}}, 400)
        config = {
            "organizer": "Syndic",
            "return_address": "Adresse",
            "consultation": "Créneau de consultation",
            "legal_checked": True,
            "contacts": {f"owner:{o.pk}": {"address": "Adresse"} for o in self.owners},
        }
        self.act("configure", {"config": config})
        self.act("freeze", {}, 400)
        config["resolutions"] = {
            str(self.resolution.pk): {
                "template": "accounts",
                "pieces": [{"label":label,"version":self.proof.pk} for label in next(t for t in TEMPLATES if t['id']=='accounts')['pieces']],
            }
        }
        self.act("configure", {"config": config})
        self.act("freeze",{},400)
        from finance.cycle import annexes
        year=FiscalYear.objects.create(name='2025',starts_on=date(2025,1,1),ends_on=date(2025,12,31))
        annual=annexes(year)['regulatory']
        config.update(fiscal_year=year.pk,accounts_reviewed=True,accounts_source_hash=annual['source_hash'])
        self.act('configure',{'config':{**config,'accounts_source_hash':'stale'}})
        self.act('freeze',{},400)
        self.act('configure',{'config':config})
        data=self.act('freeze')
        self.assertEqual(data['packet']['account_year']['dossier']['source_hash'],annual['source_hash'])
