import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import Owner, Lot
from .access import provision_access


class AccessTests(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user("admin", password="Manager-test-pass!", is_staff=True)
        self.client.force_login(self.manager)

    def post(self, url, data, client=None):
        return (client or self.client).post(url, json.dumps(data), content_type="application/json")

    def create_owner(self):
        response = self.post("/api/owners/", {"first_name": "Alice", "last_name": "Test", "email": "Alice@Example.test"})
        self.assertEqual(response.status_code, 201)
        return Owner.objects.get(pk=response.json()["id"]), response.json()["credentials"]

    def test_credentials_generated_once_and_hashed(self):
        owner, credentials = self.create_owner()
        self.assertEqual(owner.email, "alice@example.test")
        self.assertTrue(owner.user.check_password(credentials["temporary_password"]))
        self.assertNotEqual(owner.user.password, credentials["temporary_password"])
        self.assertTrue(owner.must_change_password)
        response = self.client.get("/api/owners/")
        self.assertNotIn("temporary_password", response.content.decode())
        self.assertNotIn(credentials["temporary_password"], response.content.decode())

    def test_first_login_requires_password_change(self):
        owner, credentials = self.create_owner()
        member = Client()
        response = self.post("/api/login/", {"username": "ALICE@example.test", "password": credentials["temporary_password"]}, member)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["user"]["must_change_password"])
        self.assertEqual(member.get("/api/lots/").status_code, 403)
        result = self.post("/api/password/", {"old_password": credentials["temporary_password"], "new_password": "My-new-password!249"}, member)
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()["user"]["must_change_password"])
        self.assertEqual(member.get("/api/lots/").status_code, 200)

    def test_member_read_only_and_private_data_hidden(self):
        owner, _ = self.create_owner()
        owner.must_change_password = False; owner.save()
        Lot.objects.create(number="A1", owner=owner, shares=100)
        member = Client(); member.force_login(owner.user)
        self.assertEqual(member.get("/api/overview/").status_code, 200)
        lot = member.get("/api/lots/").json()["items"][0]
        self.assertIsNone(lot["owner"]); self.assertEqual(lot["owner_name"], "")
        self.assertEqual(member.get("/api/owners/").status_code, 403)
        self.assertEqual(self.post("/api/lots/", {"number": "A2"}, member).status_code, 403)
        self.assertEqual(self.post(f"/api/owners/{owner.pk}/access/", {"reset": True}, member).status_code, 403)
        self.assertEqual(member.delete(f"/api/owners/{owner.pk}/").status_code, 403)

    def test_email_uniqueness_case_insensitive(self):
        self.create_owner()
        response = self.post("/api/owners/", {"first_name": "Bob", "last_name": "Test", "email": "ALICE@EXAMPLE.TEST"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Owner.objects.count(), 1)

    def test_reset_requires_explicit_flag_and_invalidates_session(self):
        owner, original = self.create_owner()
        member = Client(); member.force_login(owner.user)
        self.assertEqual(self.post(f"/api/owners/{owner.pk}/access/", {}).status_code, 400)
        result = self.post(f"/api/owners/{owner.pk}/access/", {"reset": True})
        self.assertEqual(result.status_code, 200)
        new = result.json()["credentials"]["temporary_password"]
        self.assertNotEqual(new, original["temporary_password"])
        owner.user.refresh_from_db(); self.assertTrue(owner.user.check_password(new))
        self.assertEqual(member.get("/api/lots/").status_code, 401)

    def test_email_change_syncs_login_without_exposing_password(self):
        owner, original = self.create_owner()
        response = self.client.patch(f"/api/owners/{owner.pk}/", json.dumps({"email": "new@example.test"}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("credentials", response.json())
        member = Client()
        self.assertEqual(self.post("/api/login/", {"username": "alice@example.test", "password": original["temporary_password"]}, member).status_code, 401)
        self.assertEqual(self.post("/api/login/", {"username": "new@example.test", "password": original["temporary_password"]}, member).status_code, 200)

    def test_delete_deactivates_account(self):
        owner, _ = self.create_owner(); account = owner.user
        self.assertEqual(self.client.delete(f"/api/owners/{owner.pk}/").status_code, 200)
        account.refresh_from_db(); self.assertFalse(account.is_active)

    def test_password_policy_and_current_password_checked(self):
        owner, credentials = self.create_owner(); member = Client(); member.force_login(owner.user)
        for old, new in [("wrong", "A-long-secure-password!"), (credentials["temporary_password"], "short")]:
            self.assertEqual(self.post("/api/password/", {"old_password": old, "new_password": new}, member).status_code, 400)

    def test_contact_edit_and_password_reset_do_not_reactivate_suspended_user(self):
        owner,_=self.create_owner()
        owner.user.is_active=False;owner.user.save()
        response=self.client.patch(f"/api/owners/{owner.pk}/",json.dumps({"phone":"0102030405"}),content_type="application/json")
        self.assertEqual(response.status_code,200)
        owner.user.refresh_from_db();self.assertFalse(owner.user.is_active)
        self.assertEqual(self.post(f"/api/owners/{owner.pk}/access/",{"reset":True}).status_code,400)
        owner.user.refresh_from_db();self.assertFalse(owner.user.is_active)

    def test_promoted_owner_still_must_change_temporary_password(self):
        owner,credentials=self.create_owner()
        owner.user.is_staff=True;owner.user.save()
        manager=Client();manager.force_login(owner.user)
        self.assertEqual(manager.get("/api/owners/").status_code,403)
        self.assertEqual(manager.get("/api/lots/").status_code,403)
        self.assertEqual(self.post("/api/password/",{"old_password":credentials["temporary_password"],"new_password":"My-new-password!249"},manager).status_code,200)
        self.assertEqual(manager.get("/api/owners/").status_code,200)

    def test_owner_editor_cannot_disable_or_delete_linked_manager(self):
        owner,_=self.create_owner()
        owner.user.is_staff=True;owner.user.save()
        self.assertEqual(self.client.patch(f"/api/owners/{owner.pk}/",json.dumps({"email":""}),content_type="application/json").status_code,400)
        self.assertEqual(self.client.delete(f"/api/owners/{owner.pk}/").status_code,409)
        owner.user.refresh_from_db();self.assertTrue(owner.user.is_active)
