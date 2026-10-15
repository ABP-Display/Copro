import io
import json
import tarfile
import tempfile
from datetime import timedelta
from pathlib import Path

import pyotp
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from core.models import Owner
from .authentication import encrypt, decrypt, new_recovery_codes, establish_session
from .models import Credential, Policy, SecurityEvent

PASSWORD = "Secure-testing-passphrase!362"


class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("admin", email="admin@example.test", password=PASSWORD)
        self.client.force_login(self.user)

    def post(self, endpoint, data, client=None):
        return (client or self.client).post("/api/" + endpoint + "/", json.dumps(data), content_type="application/json")

    def enable(self):
        secret = pyotp.random_base32()
        credential, _ = Credential.objects.update_or_create(user=self.user, defaults={"enabled": True, "secret": encrypt(secret), "revision": 1})
        codes = new_recovery_codes(credential)
        credential.save()
        session = self.client.session
        session["security_revision"] = 1
        session.save()
        return credential, secret, codes

    def test_setup_requires_password_and_never_exposes_secret_in_status(self):
        self.assertEqual(self.post("security/setup", {"password": "wrong"}).status_code, 400)
        response = self.post("security/setup", {"password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        secret = response.json()["secret"]
        item = Credential.objects.get(user=self.user)
        self.assertNotIn(secret, item.pending_secret)
        self.assertEqual(decrypt(item.pending_secret), secret)
        self.assertTrue(response.json()["qr"].startswith("data:image/svg+xml;base64,"))
        status = self.client.get("/api/security/status/")
        self.assertNotIn(secret, status.content.decode())
        self.assertFalse(status.json()["mfa_enabled"])

    def test_confirm_requires_valid_pending_code_and_returns_recovery_once(self):
        setup = self.post("security/setup", {"password": PASSWORD}).json()
        self.assertEqual(self.post("security/confirm", {"code": "bad"}).status_code, 400)
        response = self.post("security/confirm", {"code": pyotp.TOTP(setup["secret"]).now()})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["user"]["mfa_enabled"])
        self.assertEqual(len(response.json()["recovery_codes"]), 10)
        item = Credential.objects.get(user=self.user)
        self.assertFalse(item.pending_secret)
        for code in response.json()["recovery_codes"]:
            self.assertNotIn(code.replace("-", ""), str(item.recovery_hashes))
        self.assertNotIn("recovery_codes", self.client.get("/api/security/status/").json())
        self.assertEqual(self.client.get("/api/owners/").status_code, 200)

    def test_expired_setup_is_refused(self):
        self.post("security/setup", {"password": PASSWORD})
        Credential.objects.filter(user=self.user).update(pending_until=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.post("security/confirm", {"code": "000000"}).status_code, 400)

    def test_password_step_does_not_create_authenticated_session(self):
        _, secret, _ = self.enable()
        client = Client()
        result = self.post("login", {"username": "admin", "password": PASSWORD}, client)
        self.assertTrue(result.json()["mfa_required"])
        self.assertNotIn("user", result.json())
        self.assertEqual(client.get("/api/owners/").status_code, 401)
        self.assertIsNone(client.get("/api/session/").json()["user"])
        self.assertEqual(self.post("login/verify", {"code": pyotp.TOTP(secret).now()}, client).status_code, 200)
        self.assertEqual(client.get("/api/owners/").status_code, 200)

    def test_totp_replay_is_refused_between_challenges(self):
        _, secret, _ = self.enable()
        code = pyotp.TOTP(secret).now()
        for expected in [200, 400]:
            client = Client()
            self.post("login", {"username": "admin", "password": PASSWORD}, client)
            self.assertEqual(self.post("login/verify", {"code": code}, client).status_code, expected)

    def test_recovery_code_is_single_use_and_needs_password(self):
        _, _, codes = self.enable()
        self.assertEqual(self.post("login/verify", {"code": codes[0]}, Client()).status_code, 400)
        for expected in [200, 400]:
            client = Client()
            self.post("login", {"username": "admin", "password": PASSWORD}, client)
            self.assertEqual(self.post("login/verify", {"code": codes[0]}, client).status_code, expected)
        self.assertEqual(len(Credential.objects.get(user=self.user).recovery_hashes), 9)

    def test_expired_or_password_changed_challenge_is_refused(self):
        self.enable()
        client = Client()
        self.post("login", {"username": "admin", "password": PASSWORD}, client)
        session = client.session
        challenge = session["mfa_challenge"]; challenge["expires"] = 1
        session["mfa_challenge"] = challenge; session.save()
        self.assertEqual(self.post("login/verify", {"code": "000000"}, client).status_code, 400)
        self.post("login", {"username": "admin", "password": PASSWORD}, client)
        self.user.set_password("Changed-secure-password!246"); self.user.save()
        self.assertEqual(self.post("login/verify", {"code": "000000"}, client).status_code, 400)

    def test_disabled_account_cannot_finish_challenge(self):
        _, secret, _ = self.enable(); client = Client()
        self.post("login", {"username": "admin", "password": PASSWORD}, client)
        self.user.is_active = False; self.user.save()
        self.assertEqual(self.post("login/verify", {"code": pyotp.TOTP(secret).now()}, client).status_code, 400)

    def test_login_rate_limit_shared_across_sessions(self):
        for _ in range(10):
            self.assertEqual(self.post("login", {"username": "admin", "password": "bad"}, Client()).status_code, 401)
        self.assertEqual(self.post("login", {"username": "ADMIN", "password": PASSWORD}, Client()).status_code, 429)

    def test_second_factor_rate_limit_shared_across_new_challenges(self):
        self.enable()
        for index in range(6):
            client = Client()
            self.post("login", {"username": "admin", "password": PASSWORD}, client)
            result = self.post("login/verify", {"code": "wrong"}, client)
            self.assertEqual(result.status_code, 429 if index == 5 else 400)

    def test_email_and_internal_login_share_the_same_rate_limit(self):
        owner_user = get_user_model().objects.create_user("owner-internal", email="owner@example.test", password=PASSWORD)
        Owner.objects.create(first_name="Alice", last_name="Test", email="owner@example.test", user=owner_user)
        for index in range(10):
            name = "owner@example.test" if index % 2 else "owner-internal"
            self.assertEqual(self.post("login", {"username": name, "password": "bad"}, Client()).status_code, 401)
        self.assertEqual(self.post("login", {"username": "owner@example.test", "password": PASSWORD}, Client()).status_code, 429)

    def test_unenrolled_admin_cannot_bypass_required_factor_through_policy(self):
        Policy.objects.create(pk=1, require_managers=True)
        self.assertEqual(self.post("security/policy", {"password": PASSWORD, "require_managers": False}).status_code, 400)
        self.assertEqual(self.client.get("/api/security/backups/").status_code, 403)
        self.assertTrue(Policy.objects.get(pk=1).require_managers)

    def test_failed_sensitive_actions_do_not_rollback_rate_limit(self):
        self.enable()
        for _ in range(5):
            self.assertEqual(self.post("security/disable", {"password": PASSWORD, "code": "wrong"}).status_code, 400)
        self.assertIn("Trop de tentatives", self.post("security/disable", {"password": PASSWORD, "code": "wrong"}).json()["error"])

    def test_regeneration_revokes_old_codes_and_other_sessions(self):
        _, _, codes = self.enable()
        other = Client(); other.force_login(self.user)
        session = other.session; session["security_revision"] = 1; session.save()
        response = self.post("security/recovery", {"password": PASSWORD, "code": codes[0]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["recovery_codes"]), 10)
        self.assertEqual(other.get("/api/owners/").status_code, 401)
        self.assertEqual(self.client.get("/api/owners/").status_code, 200)
        client = Client(); self.post("login", {"username": "admin", "password": PASSWORD}, client)
        self.assertEqual(self.post("login/verify", {"code": codes[1]}, client).status_code, 400)

    def test_disable_requires_password_and_factor(self):
        _, _, codes = self.enable()
        self.assertEqual(self.post("security/disable", {"password": "bad", "code": codes[0]}).status_code, 400)
        self.assertEqual(self.post("security/disable", {"password": PASSWORD, "code": codes[0]}).status_code, 200)
        self.assertFalse(Credential.objects.get(user=self.user).enabled)
        self.assertEqual(self.client.get("/api/owners/").status_code, 200)

    def test_policy_requires_admin_own_factor_then_gates_manager_business_data(self):
        self.assertEqual(self.post("security/policy", {"password": PASSWORD, "require_managers": True}).status_code, 400)
        _, _, codes = self.enable()
        response = self.post("security/policy", {"password": PASSWORD, "code": codes[0], "require_managers": True})
        self.assertEqual(response.status_code, 200)
        manager = get_user_model().objects.create_user("manager", password=PASSWORD, is_staff=True)
        client = Client(); self.post("login", {"username": "manager", "password": PASSWORD}, client)
        self.assertEqual(client.get("/api/owners/").json()["code"], "mfa_setup_required")
        self.assertEqual(client.get("/api/security/status/").status_code, 200)
        self.assertTrue(client.get("/api/session/").json()["user"]["mfa_required"])
        self.assertEqual(self.post("security/policy", {"password": PASSWORD, "require_managers": False}, client).status_code, 403)
        self.assertEqual(self.post("security/disable", {"password": PASSWORD, "code": codes[1]}).status_code, 400)

    def test_factor_activation_invalidates_existing_password_only_session(self):
        old = Client(); old.force_login(self.user)
        setup = self.post("security/setup", {"password": PASSWORD}).json()
        self.post("security/confirm", {"code": pyotp.TOTP(setup["secret"]).now()})
        self.assertIsNone(old.get("/api/session/").json()["user"])
        self.assertEqual(old.get("/api/owners/").status_code, 401)

    def test_emergency_access_forces_password_change_and_retains_policy(self):
        self.enable(); Policy.objects.create(pk=1, require_managers=True)
        output = io.StringIO()
        call_command("recover_access", username="admin", confirm="admin", reason="Téléphone perdu, vérification du titulaire", stdout=output)
        password = output.getvalue().strip().split(" : ")[-1]
        self.assertEqual(self.client.get("/api/owners/").status_code, 401)
        client = Client(); result = self.post("login", {"username": "admin", "password": password}, client)
        self.assertTrue(result.json()["user"]["must_change_password"])
        self.assertEqual(client.get("/api/security/status/").status_code, 403)
        result = self.post("password", {"old_password": password, "new_password": "Replacement-password!739"}, client)
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()["user"]["must_change_password"])
        self.assertTrue(result.json()["user"]["mfa_required"])
        self.assertTrue(Policy.objects.get(pk=1).require_managers)
        self.assertEqual(client.get("/api/owners/").status_code, 403)
        self.assertTrue(SecurityEvent.objects.filter(action="access.emergency").exists())

    def test_emergency_does_not_reactivate_suspended_account(self):
        self.user.is_active = False; self.user.save()
        with self.assertRaises(CommandError):
            call_command("recover_access", username="admin", confirm="admin", reason="Récupération de test")

    def test_security_routes_require_session_and_csrf(self):
        for endpoint in ["status", "backups"]:
            self.assertEqual(Client().get(f"/api/security/{endpoint}/").status_code, 401)
        strict = Client(enforce_csrf_checks=True); strict.force_login(self.user)
        self.assertEqual(self.post("security/setup", {"password": PASSWORD}, strict).status_code, 403)

    def test_factor_enabling_race_never_establishes_password_only_session(self):
        from django.test import RequestFactory
        self.enable()
        request = RequestFactory().post("/api/login/")
        request.session = self.client.session
        with self.assertRaises(ValueError):
            establish_session(request, self.user)

    def test_rotation_after_code_verification_refuses_old_revision(self):
        from django.test import RequestFactory
        self.enable()
        request = RequestFactory().post("/api/login/verify/")
        request.session = self.client.session
        Credential.objects.filter(user=self.user).update(revision=2)
        with self.assertRaises(ValueError):
            establish_session(request, self.user, verified_revision=1)

    def test_backup_status_is_admin_only_and_does_not_expose_secrets(self):
        manager = get_user_model().objects.create_user("manager", password=PASSWORD, is_staff=True)
        other = Client(); other.force_login(manager)
        self.assertEqual(other.get("/api/security/backups/").status_code, 403)
        self.assertEqual(self.client.get("/api/security/backups/").status_code, 200)
        self.assertNotIn("secret", self.client.get("/api/security/backups/").content.decode().lower())


class InventoryTests(TestCase):
    def test_document_bytes_and_metadata_must_match(self):
        import hashlib
        from django.core.files.base import ContentFile
        from documents.models import Document, Version
        from .inventory import media_inventory
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            user = get_user_model().objects.create_user("archive-user")
            document = Document.objects.create(title="Justificatif")
            content = b"%PDF-1.7\nprivate-document"
            version = Version.objects.create(document=document, filename="piece.pdf", size=len(content),
                                             content_type="application/pdf", checksum=hashlib.sha256(content).hexdigest(), created_by=user)
            version.file.save("piece.pdf", ContentFile(content))
            self.assertEqual(len(media_inventory()), 1)
            Path(version.file.path).write_bytes(b"modified")
            with self.assertRaises(ValueError):
                media_inventory()

    def test_import_rejects_traversal_and_symbolic_links(self):
        from maintenance import unpack_media
        for name, kind in [("../outside", tarfile.REGTYPE), ("documents/link", tarfile.SYMTYPE), (".restore-stage/file", tarfile.REGTYPE)]:
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode="w") as archive:
                item = tarfile.TarInfo(name); item.type = kind
                archive.addfile(item)
            data.seek(0)
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    unpack_media(data, Path(directory).resolve())
