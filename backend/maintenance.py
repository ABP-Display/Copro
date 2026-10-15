"""Internal binary protocol for the host backup CLI. No HTTP endpoint or Docker socket."""
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path, PurePosixPath

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def media_root():
    from django.conf import settings
    return Path(settings.MEDIA_ROOT).resolve()


def unpack_media(stream, root):
    root.mkdir(parents=True, exist_ok=True)
    seen = set()
    total = 0
    with tarfile.open(fileobj=stream, mode="r|") as archive:
        for member in archive:
            total += member.size
            if total > 100 * 1024**3 or member.size < 0:
                raise ValueError("Volume documentaire trop grand.")
            name = PurePosixPath(member.name)
            if (not member.isfile() or name.is_absolute() or ".." in name.parts or not name.parts
                    or name.parts[0].startswith(".restore-")
                    or "\\" in member.name or ":" in member.name or member.name in seen):
                raise ValueError("Chemin ou type de pièce invalide dans l’archive.")
            seen.add(member.name)
            target = root.joinpath(*name.parts)
            if not target.resolve().is_relative_to(root) or any(p.is_symlink() for p in [target, *target.parents]):
                raise ValueError("Chemin de pièce non sûr.")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open("xb") as destination:
                shutil.copyfileobj(source, destination)


def main():
    import django
    django.setup()
    command = sys.argv[1]
    root = media_root()
    if command == "export-media":
        root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as archive:
            for path in sorted(root.rglob("*")):
                if path.is_symlink():
                    raise ValueError("Lien symbolique refusé.")
                if path.is_file():
                    archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
    elif command == "import-media":
        if root.exists() and any(root.iterdir()):
            raise ValueError("Le volume documentaire cible doit être vide.")
        unpack_media(sys.stdin.buffer, root)
    elif command == "clear-interrupted-media":
        # Invoked only with --resume-interrupted after validating the host journal
        # and its encrypted safety archive. Confined to these two internal paths.
        for name in [".restore-stage", ".restore-previous"]:
            path = root / name
            if path.is_symlink():
                raise ValueError("Lien symbolique de maintenance refusé.")
            if path.exists():
                shutil.rmtree(path)
    elif command == "replace-media":
        # The backend is stopped. Keep the old tree until the replacement is complete.
        stage = root / ".restore-stage"
        previous = root / ".restore-previous"
        if stage.exists() or previous.exists():
            raise ValueError("Une restauration interrompue doit être examinée avant de continuer.")
        stage.mkdir(parents=True)
        try:
            unpack_media(sys.stdin.buffer, stage)
            previous.mkdir()
            for path in list(root.iterdir()):
                if path not in [stage, previous]:
                    path.rename(previous / path.name)
            try:
                for path in list(stage.iterdir()):
                    path.rename(root / path.name)
            except Exception:
                for path in list(root.iterdir()):
                    if path not in [stage, previous]:
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink()
                for path in previous.iterdir():
                    path.rename(root / path.name)
                raise
            shutil.rmtree(previous)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    elif command == "record":
        from safety.models import BackupRecord
        data = json.load(sys.stdin)
        BackupRecord.objects.create(**{key: data[key] for key in ["archive_id", "action", "filename", "database_rows", "files", "size"]})
    elif command == "revoke-sessions":
        from django.contrib.sessions.models import Session
        from safety.models import Attempt, Credential
        Session.objects.all().delete()
        Attempt.objects.all().delete()
        Credential.objects.exclude(pending_secret="").update(pending_secret="", pending_until=None)
    else:
        raise ValueError("Commande de maintenance inconnue.")


if __name__ == "__main__":
    main()
