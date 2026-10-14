import json
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from .models import Owner, Lot


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user("manager", password="test-password-long", is_staff=True)
        cls.reader = get_user_model().objects.create_user("reader", password="test-password-long")

    def setUp(self):
        self.client.force_login(self.admin)

    def send(self, path, data, method="post"):
        return getattr(self.client, method)(path, json.dumps(data), content_type="application/json")

    def test_anonymous_cannot_read_or_write(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/owners/").status_code, 401)
        self.assertEqual(self.send("/api/lots/", {"number": "1"}).status_code, 401)

    def test_non_manager_cannot_access_data(self):
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get("/api/lots/").status_code, 403)

    def test_owner_validation_and_partial_update(self):
        self.assertEqual(self.send("/api/owners/", {"first_name": "Alice"}).status_code, 400)
        response = self.send("/api/owners/", {"first_name": "Alice", "last_name": "Martin", "email": "alice@example.fr"})
        self.assertEqual(response.status_code, 201)
        pk = response.json()["id"]
        self.assertEqual(self.send(f"/api/owners/{pk}/", {"phone": "0123456789"}, "patch").status_code, 200)
        self.assertEqual(Owner.objects.get(pk=pk).first_name, "Alice")

    def test_lot_validation_and_decimal_total(self):
        for payload in [{"number": "1", "kind": "apartment", "shares": "-1"},
                        {"number": "1", "kind": "apartment", "shares": "1", "owner": 999},
                        {"number": "1", "kind": "invalid", "shares": "1"}]:
            self.assertEqual(self.send("/api/lots/", payload).status_code, 400)
        for num, shares in [("1", "0.10"), ("2", "0.20")]:
            self.assertEqual(self.send("/api/lots/", {"number": num, "kind": "apartment", "shares": shares}).status_code, 201)
        response = self.client.get("/api/overview/")
        self.assertEqual(response.json()["shares_total"], "0.30")
        self.assertEqual(response.json()["unassigned_count"], 2)
        self.assertEqual(self.send("/api/lots/", {"number": "1", "kind": "apartment", "shares": "5"}).status_code, 400)

    def test_owner_with_lots_is_protected(self):
        owner = Owner.objects.create(first_name="Alice", last_name="Martin")
        lot = Lot.objects.create(number="1", owner=owner)
        self.assertEqual(self.client.delete(f"/api/owners/{owner.pk}/").status_code, 409)
        self.assertEqual(self.send(f"/api/lots/{lot.pk}/", {"owner": None}, "patch").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/owners/{owner.pk}/").status_code, 200)

    def test_invalid_json_and_nested_data_are_rejected(self):
        for content in ["{", "[]", '{"first_name": {"x": 1}}']:
            self.assertEqual(self.client.post("/api/owners/", content, content_type="application/json").status_code, 400)

    def test_methods_and_missing_records(self):
        self.assertEqual(self.client.get("/api/logout/").status_code, 405)
        self.assertEqual(self.client.delete("/api/owners/999/").status_code, 404)

    def test_login_logout_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post("/api/login/", json.dumps({"username": "manager", "password": "test-password-long"}), content_type="application/json")
        self.assertEqual(response.status_code, 403)
        token = client.get("/api/session/").json()["csrfToken"]
        response = client.post("/api/login/", json.dumps({"username": "manager", "password": "test-password-long"}), content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertIn("copro_sessionid",client.cookies)
        self.assertIn("copro_csrftoken",client.cookies)
        client.cookies["sessionid"]="other-local-application-session"
        client.cookies["csrftoken"]="other-local-application-csrf"
        self.assertEqual(client.get("/api/lots/").status_code, 200)
        new_token = response.json()["csrfToken"]
        self.assertEqual(client.post("/api/logout/", HTTP_X_CSRFTOKEN=new_token).status_code, 200)
        self.assertEqual(client.get("/api/lots/").status_code, 401)
