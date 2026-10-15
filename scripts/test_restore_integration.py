"""Opt-in Docker integration test. Creates only disposable projects/volumes, no published ports.

    python scripts/test_restore_integration.py --run-docker

Build backend first. The test uses the current Compose environment but overrides
the application secret and initial password; it never starts the production backend.
"""
import argparse
import json
from pathlib import Path
import secrets
import tempfile
import uuid
from unittest.mock import patch

from backup import ROOT, Compose, capture, opened, isolated_check, restore, locked


SEED = r'''
import hashlib
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from core.models import Owner, Lot
from documents.models import Document, Version
from finance.models import FiscalYear, Account, Entry, Line
from safety.models import Credential
from safety.authentication import encrypt, new_recovery_codes
import pyotp
user = get_user_model().objects.get(username="admin")
owner=Owner.objects.create(first_name="Fixture", last_name="Restoration")
Lot.objects.create(number="FIXTURE-A1", owner=owner, shares=100)
year=FiscalYear.objects.create(name="2026", starts_on="2026-01-01", ends_on="2026-12-31")
bank=Account.objects.create(code="512", name="Banque fictive")
capital=Account.objects.create(code="102", name="Provision fictive")
entry=Entry.objects.create(year=year, number=1, date="2026-01-01", journal="OD", label="Reprise fictive", created_by=user)
Line.objects.create(entry=entry, account=bank, debit=300)
Line.objects.create(entry=entry, account=capital, credit=300)
doc=Document.objects.create(title="Pièce fictive versionnée")
for number in [1,2]:
    content=("%PDF-1.7\nVersion fictive " + str(number)).encode()
    version=Version(document=doc, filename="piece.pdf", size=len(content), checksum=hashlib.sha256(content).hexdigest(), content_type="application/pdf", created_by=user)
    version.file.save("piece.pdf", ContentFile(content), save=False); version.save()
    doc.current=version; doc.save()
credential=Credential.objects.create(user=user, enabled=True, secret=encrypt(pyotp.random_base32()), revision=1)
new_recovery_codes(credential); credential.save()
'''

CHECK = r'''
from pathlib import Path
from core.models import Lot
from documents.models import Version
from finance.models import Entry, Line
from safety.models import Credential
from safety.authentication import decrypt
assert Lot.objects.get().number == "FIXTURE-A1"
assert Entry.objects.count() == 1 and Line.objects.count() == 2
assert Version.objects.count() == 2 and all(Path(v.file.path).exists() for v in Version.objects.all())
assert len(decrypt(Credential.objects.get().secret)) >= 32
print("Comptes, lots, deux versions et secret MFA restaurés.")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-docker", action="store_true", required=True)
    parser.parse_args()
    password = secrets.token_urlsafe(24)
    with locked(), tempfile.TemporaryDirectory(prefix="copro-integration-") as directory:
        temp = Path(directory)
        project = "copro-test-reprise-" + uuid.uuid4().hex[:10]
        marker = ROOT / ".local-data" / "restore-pending.json"
        if marker.exists():
            raise RuntimeError("Résolvez la maintenance en cours avant le test.")
        source = Compose()
        image = source.config["services"]["backend"].get("image", source.name + "-backend")
        override = temp / "fixture.json"
        override.write_text(json.dumps({"services": {"backend": {"image": image, "environment": {
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(48), "ADMIN_PASSWORD": secrets.token_urlsafe(24)}}}}), "utf-8")
        fixture = Compose([ROOT / "compose.yaml", override], project)
        try:
            fixture.call("up", "-d", "--wait", "backend")
            fixture.helper("python", "manage.py", "shell", "-c", SEED)
            fixture.pause()
            archive = temp / "fixture.coprobackup"
            manifest = capture(fixture, archive, password)
            fixture.resume()
            with opened(archive, password) as (opened_temp, metadata):
                isolated_check(fixture, opened_temp, metadata)
            fixture.helper("python", "manage.py", "shell", "-c", "from core.models import Lot; from documents.models import Version; Lot.objects.update(number='MODIFIE'); Version.objects.first().file.delete(save=False)")
            restore(fixture, archive, password, project, safety_directory=temp / "safety")
            print(fixture.helper("python", "manage.py", "shell", "-c", CHECK))
            original_helper = fixture.helper

            def fail_replacement(*args, **kwargs):
                if args == ("python", "maintenance.py", "replace-media"):
                    raise RuntimeError("Interruption simulée avant remplacement des pièces")
                return original_helper(*args, **kwargs)

            with patch.object(fixture, "helper", side_effect=fail_replacement):
                try:
                    restore(fixture, archive, password, project, safety_directory=temp / "safety")
                except RuntimeError as error:
                    if "Interruption simulée" not in str(error):
                        raise
                else:
                    raise AssertionError("L’interruption attendue n’a pas été signalée.")
            assert marker.exists() and not fixture.running(), "Une interruption doit maintenir l’application arrêtée."
            restore(fixture, archive, password, project, resume_interrupted=True, safety_directory=temp / "safety")
            assert not marker.exists() and fixture.running()
            print(fixture.helper("python", "manage.py", "shell", "-c", CHECK))
            print(f"OK : {manifest['database_rows']} lignes, {manifest['files']} fichiers ; perte d’une pièce et interruption/reprise vérifiées.")
        finally:
            fixture.call("down", "--volumes", "--remove-orphans")
            if marker.exists() and json.loads(marker.read_text("utf-8"))["target"] == project:
                marker.unlink()


if __name__ == "__main__":
    main()
