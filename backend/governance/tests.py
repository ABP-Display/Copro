import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase,TestCase,Client
from core.models import Owner
from core.access import provision_access
from .calculations import vote_result,split_result,installment_result
from .models import Meeting,Resolution


def ballot(**changes):
    return {"rule":"25","mode":"first","total_votes":"1000","total_owners":10,"participating_owners":6,
        "for_owners":3,"for_votes":"400","against_votes":"300","abstain_votes":"100",**changes}


class CalculationTests(SimpleTestCase):
    def test_simple_majority_excludes_abstention_and_tie_fails(self):
        result=vote_result(ballot(rule="24",for_votes="301",against_votes="300",abstain_votes="200"))
        self.assertTrue(result["adopted"])
        self.assertEqual(Decimal(result["expressed_votes"]),601)
        self.assertFalse(vote_result(ballot(rule="24",for_votes="300"))["adopted"])

    def test_no_expressed_votes_is_distinct_from_rejection(self):
        result=vote_result(ballot(rule="24",for_votes="0",against_votes="0",abstain_votes="100",for_owners=0,participating_owners=3))
        self.assertEqual(result["status"],"no_expressed_votes")
        self.assertFalse(result["adopted"])

    def test_absolute_majority_is_strict_and_bridge_has_exact_third(self):
        self.assertFalse(vote_result(ballot(for_votes="500"))["adopted"])
        self.assertTrue(vote_result(ballot(for_votes="500.01"))["adopted"])
        self.assertIsNone(vote_result(ballot(for_votes="333.33"))["bridge"])
        self.assertEqual(vote_result(ballot(for_votes="333.34"))["bridge"],"25-1")

    def test_double_majority_requires_headcount_and_two_thirds(self):
        data=ballot(rule="26",total_votes="900",participating_owners=7,for_owners=6,for_votes="600",against_votes="100",abstain_votes="0")
        self.assertTrue(vote_result(data)["adopted"])
        self.assertFalse(vote_result(data|{"for_owners":5})["adopted"])
        self.assertFalse(vote_result(data|{"for_votes":"599.99"})["adopted"])

    def test_26_bridge_uses_participants_not_all_owners(self):
        result=vote_result(ballot(rule="26"))
        self.assertFalse(result["adopted"])
        self.assertEqual(result["bridge"],"26-1")
        self.assertIsNone(vote_result(ballot(rule="26",for_owners=2))["bridge"])

    def test_second_vote_is_separate_and_bridges_cannot_chain(self):
        first=ballot()
        second=ballot(rule="24",mode="25-1",initial=first)
        self.assertTrue(vote_result(second)["adopted"])
        self.assertIsNone(vote_result(second)["bridge"])
        first26=ballot(rule="26")
        second26=ballot(rule="25",mode="26-1",initial=first26)
        self.assertFalse(vote_result(second26)["adopted"])
        self.assertIsNone(vote_result(second26)["bridge"])
        with self.assertRaises(ValueError):vote_result(ballot(rule="24",mode="25-1",initial=second26))
        with self.assertRaises(ValueError):vote_result(second|{"total_votes":"1001"})
        with self.assertRaises(ValueError):vote_result(second|{"initial":ballot(for_votes="100")})

    def test_unanimity_requires_all_owners_and_voices(self):
        full=ballot(rule="unanimity",for_votes="1000",against_votes="0",abstain_votes="0",for_owners=10,participating_owners=10)
        self.assertTrue(vote_result(full)["adopted"])
        self.assertFalse(vote_result(full|{"for_votes":"999","against_votes":"1","for_owners":9})["adopted"])

    def test_inconsistent_or_special_electorates_are_rejected(self):
        cases=[{"total_owners":2},{"total_owners":True},{"for_votes":"NaN"},{"for_votes":"-1"},{"for_votes":"600.001"},
            {"for_votes":"900"},{"for_owners":7},{"participating_owners":10},{"for_votes":"0"},{"for_votes":True}]
        for changes in cases:
            with self.subTest(changes=changes),self.assertRaises(ValueError):vote_result(ballot(**changes))

    def test_weighted_split_conserves_cents_and_zero_weights(self):
        data={"amount":"100.00","rows":[{"label":str(i),"weight":"1"} for i in range(3)]}
        result=split_result(data)
        self.assertEqual([Decimal(r["amount"]) for r in result["rows"]],[Decimal("33.34"),Decimal("33.33"),Decimal("33.33")])
        self.assertEqual(Decimal(result["total"]),100)
        result=split_result({"amount":"0.01","rows":[{"weight":"1"},{"weight":"0"}]})
        self.assertEqual([Decimal(r["amount"]) for r in result["rows"]],[Decimal("0.01"),0])
        for data in [{"amount":"1","rows":[{"weight":"0"}]},{"amount":"1","rows":[{"weight":"-1"}]},{"amount":"NaN","rows":[{"weight":"1"}]}]:
            with self.assertRaises(ValueError):split_result(data)

    def test_installments_conserve_total_and_reject_invalid_counts(self):
        result=installment_result({"amount":"100","count":3})
        self.assertEqual([Decimal(r["amount"]) for r in result["rows"]],[Decimal("33.34"),Decimal("33.33"),Decimal("33.33")])
        for count in [0,61,1.5,True]:
            with self.assertRaises(ValueError):installment_result({"amount":"100","count":count})


class AssemblyTests(TestCase):
    def setUp(self):
        self.manager=get_user_model().objects.create_user("manager",is_staff=True)
        self.client.force_login(self.manager)

    def post(self,path,data,client=None,method="post"):
        return getattr(client or self.client,method)("/api/ag/"+path+"/",json.dumps(data),content_type="application/json")

    def meeting(self):
        result=self.post("meetings",{"title":"AG annuelle","scheduled_at":"2026-11-15T18:30:00+01:00","location":"Salle commune","notes":"Préparer les devis"})
        self.assertEqual(result.status_code,201,result.content)
        return result.json()["id"]

    def resolution(self,meeting):
        result=self.post(f"meetings/{meeting}/resolutions",{"position":1,"title":"Projet","majority":"25","text":"Texte proposé"})
        self.assertEqual(result.status_code,201,result.content)
        return result.json()["id"]

    def test_meetings_and_resolutions_persist_with_archive_restore(self):
        meeting=self.meeting();resolution=self.resolution(meeting)
        data=self.client.get("/api/ag/meetings/").json()["items"][0]
        self.assertEqual(data["resolutions"][0]["id"],resolution)
        self.assertEqual(self.post(f"meetings/{meeting}",{"archived":True},method="patch").status_code,200)
        self.assertEqual(self.client.get("/api/ag/meetings/").json()["items"],[])
        self.assertEqual(len(self.client.get("/api/ag/meetings/",{"archived":"1"}).json()["items"]),1)
        self.assertEqual(self.post(f"resolutions/{resolution}",{"title":"Modifié"},method="patch").status_code,400)
        self.assertEqual(self.post(f"meetings/{meeting}",{"archived":False},method="patch").status_code,200)
        self.assertEqual(Resolution.objects.count(),1)

    def test_simulations_are_recalculated_and_second_vote_keeps_first(self):
        resolution=self.resolution(self.meeting())
        response=self.post(f"resolutions/{resolution}/simulate",ballot(rule="24"))
        self.assertEqual(response.status_code,200,response.content)
        self.assertFalse(response.json()["result"]["adopted"])
        self.assertEqual(response.json()["result"]["rule"],"25")
        response=self.post(f"resolutions/{resolution}/simulate",ballot(rule="24",mode="25-1"))
        self.assertEqual(response.status_code,200,response.content)
        self.assertTrue(response.json()["result"]["adopted"])
        self.assertIsNotNone(response.json()["first_vote"])
        self.assertEqual(self.post(f"resolutions/{resolution}/simulate",ballot(rule="24",mode="25-1")).status_code,400)

    def test_editing_resolution_discards_outdated_simulation_and_duplicate_position_fails(self):
        meeting=self.meeting();resolution=self.resolution(meeting)
        self.post(f"resolutions/{resolution}/simulate",ballot())
        self.assertEqual(self.post(f"resolutions/{resolution}",{"text":"Nouveau texte"},method="patch").status_code,200)
        self.assertIsNone(Resolution.objects.get(pk=resolution).analysis)
        self.assertEqual(self.post(f"meetings/{meeting}/resolutions",{"position":1,"title":"Doublon","majority":"24"}).status_code,409)

    def test_tools_do_not_create_accounting_entries(self):
        from finance.models import Entry
        self.assertEqual(self.post("tools/vote",ballot()).status_code,200)
        self.assertEqual(self.post("tools/installments",{"amount":"100","count":3}).status_code,200)
        self.assertEqual(Entry.objects.count(),0)
        self.assertEqual(Meeting.objects.count(),0)

    def test_members_and_anonymous_cannot_access_private_preparation(self):
        owner=Owner.objects.create(first_name="Alice",last_name="Test",email="alice@example.test")
        provision_access(owner);owner.must_change_password=False;owner.save()
        member=Client();member.force_login(owner.user)
        meeting=self.meeting();resolution=self.resolution(meeting)
        self.assertEqual(member.get("/api/ag/meetings/").status_code,403)
        self.assertEqual(Client().get("/api/ag/meetings/").status_code,401)
        self.assertEqual(self.post("tools/vote",ballot(),member).status_code,403)
        self.assertEqual(self.post(f"resolutions/{resolution}/simulate",ballot(),member).status_code,403)


class RosterTests(TestCase):
    def setUp(self):
        self.manager=get_user_model().objects.create_user("roster-manager",is_staff=True)
        self.client.force_login(self.manager)
        self.rows=[{"owner_id":None,"name":name,"shares":"100","attendance":attendance,"vote":vote}
                   for name,attendance,vote in [("Alice","present","for"),("Bruno","represented","against"),("Claire","correspondence","for"),("Denis","absent","pending")]]

    def test_votes_and_presence_are_recomputed_from_roster(self):
        result=vote_result({"rule":"24","roster":self.rows,"total_votes":"1","for_votes":"0"})
        self.assertTrue(result["adopted"])
        self.assertEqual(result["total_votes"],"400")
        self.assertEqual(result["participating_owners"],3)
        self.assertEqual(result["for_owners"],2)
        self.assertEqual(result["against_votes"],"100")

    def test_duplicate_owners_pending_votes_and_zero_rights_rejected(self):
        for rows in [self.rows+[self.rows[0]], [{**r,"owner_id":1} for r in self.rows],
                     [{**r,"vote":"pending"} for r in self.rows],
                     [{**r,"shares":"0"} for r in self.rows]]:
            with self.subTest(rows=rows),self.assertRaises(ValueError):
                vote_result({"roster":rows})

    def test_second_vote_preserves_electorate_not_just_total(self):
        initial={"rule":"25","roster":self.rows}
        second={"rule":"24","mode":"25-1","roster":self.rows,"initial":initial}
        self.assertTrue(vote_result(second)["adopted"])
        changed=[{**r,"name":"Autre"} if i==0 else r for i,r in enumerate(self.rows)]
        with self.assertRaises(ValueError):vote_result({**second,"roster":changed})

    def test_directory_groups_lots_and_does_not_expose_contacts(self):
        from core.models import Lot
        owner=Owner.objects.create(first_name="Alice",last_name="Test",email="private@example.test")
        Lot.objects.create(number="A",owner=owner,shares="100.25")
        Lot.objects.create(number="B",owner=owner,shares="40.50")
        Lot.objects.create(number="C",shares="5")
        response=self.client.get("/api/ag/electorate/")
        self.assertEqual(response.status_code,200)
        self.assertEqual(Decimal(response.json()["items"][0]["shares"]),Decimal("140.75"))
        self.assertEqual(response.json()["unassigned_lots"],1)
        self.assertNotContains(response,"private@example.test")
        self.assertEqual(Client().get("/api/ag/electorate/").status_code,401)

    def test_presence_snapshot_persists_and_archived_meeting_is_protected(self):
        meeting=Meeting.objects.create(title="AG",scheduled_at="2026-12-01T12:00Z",created_by=self.manager)
        path=f"/api/ag/meetings/{meeting.id}/"
        response=self.client.patch(path,json.dumps({"roster":self.rows}),content_type="application/json")
        self.assertEqual(response.status_code,200,response.content)
        meeting.refresh_from_db();self.assertEqual(len(meeting.roster),4)
        meeting.archived=True;meeting.save()
        response=self.client.patch(path,json.dumps({"roster":self.rows}),content_type="application/json")
        self.assertEqual(response.status_code,400)
