import hashlib
import json
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.utils.crypto import salted_hmac
from documents.models import Version


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def media_inventory(*, validate=True):
    root = Path(settings.MEDIA_ROOT).resolve()
    files = {}
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError("Une pièce est un lien symbolique : sauvegarde refusée.")
            if path.is_file():
                files[path.relative_to(root).as_posix()] = {"size": path.stat().st_size, "sha256": file_hash(path)}
            elif not path.is_dir():
                raise ValueError("Type de fichier non pris en charge.")
    errors = document_errors(files)
    if errors and validate:
        raise ValueError(f"La version documentaire {errors[0]} est absente ou altérée.")
    return files


def document_errors(files):
    errors = []
    for version in Version.objects.all().iterator():
        name = version.file.name
        item = files.get(name)
        if not item or item["size"] != version.size or item["sha256"] != version.checksum:
            errors.append(version.pk)
    return errors


def inventory(*, allow_damaged=False):
    if connection.vendor != "postgresql":
        raise ValueError("Les sauvegardes complètes utilisent PostgreSQL.")
    models = {}
    # Include auto-created M2M through tables and sessions: every application row
    # is checked. Session revocation happens only AFTER a successful comparison.
    for model in sorted(apps.get_models(include_auto_created=True), key=lambda m: m._meta.label_lower):
        if model._meta.proxy or not model._meta.managed:
            continue
        digest = hashlib.sha256()
        count = 0
        for row in model.objects.order_by(model._meta.pk.name).values().iterator():
            digest.update((json.dumps(row, cls=DjangoJSONEncoder, sort_keys=True, separators=(",", ":")) + "\n").encode())
            count += 1
        models[model._meta.label_lower] = {"rows": count, "sha256": digest.hexdigest()}
    files = media_inventory(validate=not allow_damaged)
    return {"format": 1, "models": models, "files": files, "document_errors": document_errors(files),
            "authentication_key": salted_hmac("copro.backup.key.v1", "restore-check").hexdigest(),
            "migrations": sorted([list(row) for row in MigrationRecorder.Migration.objects.values_list("app", "name")])}
