#!/usr/bin/env python3
"""Create, inspect, verify and restore encrypted database + document snapshots.

Run from the repository root. Requires Python 3.12+, scripts/requirements.txt and
Docker Compose v2. The maintenance helpers run with the application's volume UID.
"""
import argparse
import contextlib
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import uuid

from archive_format import encrypt_file, decrypt_file, sha256, unpack

ROOT = Path(__file__).resolve().parent.parent


def say(message):
    print(message, flush=True)


class Compose:
    def __init__(self, files=None, project=None):
        self.base = ["docker", "compose", "--project-directory", str(ROOT)]
        for file in files or [ROOT / "compose.yaml"]:
            self.base += ["-f", str(Path(file).resolve())]
        if project:
            self.base += ["-p", project]
        self.config = json.loads(self.call("config", "--format", "json"))
        self.name = self.config["name"]

    def call(self, *args, input_file=None, output_file=None, input_bytes=None):
        with contextlib.ExitStack() as stack:
            source = stack.enter_context(Path(input_file).open("rb")) if input_file else None
            target = stack.enter_context(Path(output_file).open("wb")) if output_file else subprocess.PIPE
            result = subprocess.run(self.base + list(args), cwd=ROOT, stdin=source,
                                    input=input_bytes, stdout=target, stderr=subprocess.PIPE)
        if result.returncode:
            # Config and environment can contain secrets. Never echo full Docker commands/config.
            diagnostic = result.stderr.decode("utf-8", errors="replace")[-1500:]
            # Docker error output normally contains service names only; redact known env values.
            for service in self.config.get("services", {}).values() if hasattr(self, "config") else []:
                for key, value in service.get("environment", {}).items():
                    if value and any(word in key for word in ("PASSWORD", "SECRET", "TOKEN", "KEY")):
                        diagnostic = diagnostic.replace(str(value), "[secret]")
            raise RuntimeError("Échec Docker Compose : " + diagnostic)
        return result.stdout.decode("utf-8") if output_file is None else None

    def helper(self, *args, **kwargs):
        return self.call("run", "--rm", "--no-deps", "-T", "--pull", "never", "backend", *args, **kwargs)

    def running(self):
        return bool(self.call("ps", "--status", "running", "-q", "backend").strip())

    def pause(self):
        running = self.running()
        if running:
            say("Pause de l’application pendant la capture cohérente…")
            self.call("stop", "-t", "60", "backend")
        return running

    def resume(self):
        self.call("up", "-d", "--no-deps", "--wait", "backend")

    def inventory(self, allow_damaged=False):
        options = ["--allow-damaged-documents"] if allow_damaged else []
        return json.loads(self.helper("python", "manage.py", "backup_inventory", *options))


@contextlib.contextmanager
def locked():
    path = ROOT / ".backup-lock"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise RuntimeError("Une maintenance est en cours, ou a été interrompue. Vérifiez l’état de l’instance avant de retirer .backup-lock.") from None
    os.write(descriptor, str(os.getpid()).encode())
    os.close(descriptor)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def passphrase(confirm=False):
    password = os.environ.get("COPRO_BACKUP_PASSPHRASE")
    if not password:
        password = getpass.getpass("Phrase secrète de la sauvegarde : ")
        if confirm and password != getpass.getpass("Confirmer la phrase secrète : "):
            raise ValueError("Les phrases secrètes ne correspondent pas.")
    if len(password) < 12:
        raise ValueError("Utilisez une phrase secrète d’au moins douze caractères.")
    return password


def record(compose, manifest, action, archive):
    data = {"archive_id": manifest["id"], "action": action, "filename": archive.name,
            "database_rows": manifest["database_rows"], "files": manifest["files"], "size": archive.stat().st_size}
    compose.helper("python", "maintenance.py", "record", input_bytes=json.dumps(data).encode())


def capture(compose, destination, password, *, allow_damaged=False):
    """Caller has stopped all application writers. PostgreSQL remains available."""
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ValueError("Le fichier de destination existe déjà ; aucun écrasement automatique.")
    with tempfile.TemporaryDirectory(prefix="copro-capture-") as directory:
        os.chmod(directory, 0o700)
        temp = Path(directory)
        version = compose.call("exec", "-T", "db", "psql", "-U", "copro", "-d", "copro", "-Atc", "SHOW server_version_num").strip()
        if int(version) // 10000 != 16:
            raise ValueError("Cet outil prend actuellement en charge PostgreSQL 16.")
        before = compose.inventory(allow_damaged)
        compose.call("exec", "-T", "db", "pg_dump", "-U", "copro", "-d", "copro", "--format=custom",
                     "--no-owner", "--no-privileges", output_file=temp / "database.dump")
        compose.helper("python", "maintenance.py", "export-media", output_file=temp / "media.tar")
        after = compose.inventory(allow_damaged)
        if before != after:
            raise ValueError("Les données ont changé pendant la sauvegarde. Archive refusée.")
        (temp / "inventory.json").write_text(json.dumps(before, sort_keys=True), "utf-8")
        manifest = {"format": 1, "id": str(uuid.uuid4()), "created_at": datetime.now(timezone.utc).isoformat(),
                    "postgres_major": 16, "database_rows": sum(item["rows"] for item in before["models"].values()),
                    "files": len(before["files"]), "document_errors": before.get("document_errors", []), "contents": {}}
        for name in ["database.dump", "media.tar", "inventory.json"]:
            path = temp / name
            manifest["contents"][name] = {"size": path.stat().st_size, "sha256": sha256(path)}
        (temp / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), "utf-8")
        with tarfile.open(temp / "snapshot.tar", "w:") as archive:
            for name in ["manifest.json", "inventory.json", "database.dump", "media.tar"]:
                archive.add(temp / name, arcname=name, recursive=False)
        partial = destination.with_name(destination.name + ".partial")
        try:
            encrypt_file(temp / "snapshot.tar", partial, password)
            os.chmod(partial, 0o600)
            # Read back and authenticate the entire encrypted archive before publishing it.
            decrypt_file(partial, temp / "readback.tar", password)
            if sha256(temp / "readback.tar") != sha256(temp / "snapshot.tar"):
                raise ValueError("La vérification après écriture a échoué.")
            partial.rename(destination)
        finally:
            partial.unlink(missing_ok=True)
    return manifest


def check_inventory(compose, temp):
    expected = json.loads((temp / "inventory.json").read_text("utf-8"))
    actual = compose.inventory()
    if actual != expected:
        raise ValueError("La base ou les documents restaurés diffèrent de l’inventaire sauvegardé.")


def isolated_check(source, temp, manifest):
    """Restore only into a fresh project with no published ports, then destroy it."""
    if manifest.get("document_errors"):
        raise ValueError("Cette archive de secours conserve un état documentaire endommagé. Une remise en service exige de réparer ses pièces.")
    project = "copro-check-" + uuid.uuid4().hex[:12]
    service = source.config["services"]["backend"]
    image = service.get("image", source.name + "-backend")
    override = temp / "isolated.json"
    override.write_text(json.dumps({"services": {"backend": {"image": image, "pull_policy": "never"}}}), "utf-8")
    files = [*source_files(source), override]
    target = Compose(files, project)
    if target.call("ps", "-a", "-q").strip():
        raise ValueError("Le projet de vérification existe déjà.")
    # Never use external or explicitly named storage/networks from a custom deployment.
    for section in ["volumes", "networks"]:
        for name, value in target.config.get(section, {}).items():
            if value.get("external") or not value.get("name", "").startswith(project + "_"):
                raise ValueError("La vérification exige des volumes et réseaux propres au projet isolé.")
    say("Restauration de contrôle dans un projet isolé sans port publié…")
    try:
        target.call("up", "-d", "--wait", "db")
        target.call("exec", "-T", "db", "pg_restore", "-U", "copro", "-d", "copro", "--single-transaction",
                    "--exit-on-error", "--no-owner", "--no-privileges", input_file=temp / "database.dump")
        target.helper("python", "maintenance.py", "import-media", input_file=temp / "media.tar")
        target.helper("python", "manage.py", "check")
        check_inventory(target, temp)
    finally:
        # project is generated here and passed explicitly; production volumes are never selected.
        target.call("down", "--volumes", "--remove-orphans")
    say(f"Restauration vérifiée : {manifest['database_rows']} lignes et {manifest['files']} fichier(s) identiques.")


def source_files(compose):
    return [compose.base[index + 1] for index, value in enumerate(compose.base) if value == "-f"]


@contextlib.contextmanager
def opened(archive, password):
    with tempfile.TemporaryDirectory(prefix="copro-open-") as directory:
        os.chmod(directory, 0o700)
        temp = Path(directory)
        decrypt_file(archive, temp / "snapshot.tar", password)
        manifest = unpack(temp / "snapshot.tar", temp)
        if manifest.get("postgres_major") != 16:
            raise ValueError("Version majeure PostgreSQL incompatible.")
        yield temp, manifest


def restore(compose, archive, password, confirmation, resume_interrupted=False, *, safety_directory=None):
    if confirmation != compose.name:
        raise ValueError("Restauration refusée : --confirm doit contenir le nom exact du projet Compose cible (" + compose.name + ").")
    with opened(archive, password) as (temp, manifest):
        isolated_check(compose, temp, manifest)
        # No modification of the target before the candidate was actually restored and checked.
        marker = ROOT / ".local-data" / "restore-pending.json"
        if marker.exists() != resume_interrupted:
            raise ValueError("Une restauration interrompue exige --resume-interrupted ; ce drapeau exige un journal d’interruption.")
        previous = json.loads(marker.read_text("utf-8")) if marker.exists() else None
        if previous and previous["target"] != compose.name:
            raise ValueError("Le journal d’interruption concerne un autre projet.")
        safety_directory = Path(safety_directory) if safety_directory else ROOT / "backups"
        safety = Path(previous["safety_archive"]) if previous else safety_directory / ("avant-restauration-" + uuid.uuid4().hex + ".coprobackup")
        if previous:
            # Keep a readable safety archive before allowing any interrupted retry.
            with opened(safety, password):
                pass
        running = compose.pause()
        if previous:
            running = previous.get("was_running", False)
        modifying = bool(previous)
        try:
            if not previous:
                safety_manifest = capture(compose, safety, password, allow_damaged=True)
                if safety_manifest.get("document_errors"):
                    say("L’état précédent contenait des pièces absentes ou altérées : conservé pour secours, sans validation de remise en service.")
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps({"target": compose.name, "safety_archive": str(safety),
                                          "candidate": str(archive.resolve()), "was_running": running}), "utf-8")
            modifying = True
            if previous:
                compose.helper("python", "maintenance.py", "clear-interrupted-media")
            compose.call("exec", "-T", "db", "pg_restore", "-U", "copro", "-d", "copro", "--clean", "--if-exists",
                         "--single-transaction", "--exit-on-error", "--no-owner", "--no-privileges", input_file=temp / "database.dump")
            compose.helper("python", "maintenance.py", "replace-media", input_file=temp / "media.tar")
            check_inventory(compose, temp)
            compose.helper("python", "maintenance.py", "revoke-sessions")
            record(compose, manifest, "restored", archive)
            marker.unlink()
        except BaseException:
            if modifying:
                say("RESTAURATION INTERROMPUE : l’application reste arrêtée pour éviter un accès à des données incohérentes.")
                say("Sauvegarde de retour disponible : " + str(safety))
                say("Consultez docs/guides/SAUVEGARDE-SECURITE.md avant de redémarrer.")
            elif running:
                compose.resume()
            raise
        else:
            if running:
                compose.resume()
        say("Base et documents restaurés. Toutes les sessions ont été révoquées ; reconnectez-vous.")
        say("Sauvegarde de l’état précédent : " + str(safety))


def prune_verified(directory, keep):
    """Retention only touches this tool's archives with a successful verification receipt."""
    candidates = []
    for receipt in directory.glob("copro-*.coprobackup.verified.json"):
        archive = receipt.with_name(receipt.name.removesuffix(".verified.json"))
        if archive.is_file() and not archive.is_symlink():
            data = json.loads(receipt.read_text("utf-8"))
            if data.get("created_at") and data.get("sha256") == sha256(archive):
                candidates.append((data["created_at"], archive, receipt))
    for _, archive, receipt in sorted(candidates, reverse=True)[keep:]:
        archive.unlink()
        receipt.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Nom Compose cible ; celui de compose.yaml par défaut")
    parser.add_argument("--file", action="append", help="Fichier Compose ; répétable pour une surcharge")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="Créer une sauvegarde chiffrée ; contrôle de restauration conseillé via --verify")
    create.add_argument("--output-dir", type=Path, default=ROOT / "backups")
    create.add_argument("--verify", action="store_true")
    create.add_argument("--keep", type=int, help="Après vérification, conserver les N dernières archives vérifiées de ce dossier")
    for command in ["inspect", "verify", "restore"]:
        item = sub.add_parser(command)
        item.add_argument("archive", type=Path)
        if command == "restore":
            item.add_argument("--confirm", required=True)
            item.add_argument("--resume-interrupted", action="store_true", help="Reprendre une restauration interrompue avec le journal et la sauvegarde de retour conservés")
    args = parser.parse_args()
    password = passphrase(confirm=args.command == "create")
    if args.command == "inspect":
        with opened(args.archive, password) as (_, manifest):
            say(json.dumps({key: manifest[key] for key in ["id", "created_at", "postgres_major", "database_rows", "files"]}, indent=2))
        return
    if args.command == "create" and args.keep is not None and (not args.verify or args.keep < 1):
        raise ValueError("--keep exige --verify et un nombre supérieur à zéro.")
    with locked():
        compose = Compose(args.file, args.project)
        if args.command == "create":
            if (ROOT / ".local-data" / "restore-pending.json").exists():
                raise ValueError("Une restauration interrompue doit être résolue avant une nouvelle sauvegarde.")
            archive = args.output_dir.resolve() / ("copro-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8] + ".coprobackup")
            running = compose.pause()
            try:
                manifest = capture(compose, archive, password)
                record(compose, manifest, "created", archive)
            finally:
                if running:
                    compose.resume()
            say("Sauvegarde chiffrée créée : " + str(archive))
            if not args.verify:
                say("Intégrité vérifiée après écriture. La restauration reste à tester avec la commande verify.")
                return
        else:
            archive = args.archive.resolve()
        if args.command == "restore":
            restore(compose, archive, password, args.confirm, args.resume_interrupted)
            return
        with opened(archive, password) as (temp, manifest):
            isolated_check(compose, temp, manifest)
        record(compose, manifest, "verified", archive)
        receipt = archive.with_name(archive.name + ".verified.json")
        receipt.write_text(json.dumps({"id": manifest["id"], "sha256": sha256(archive),
                                      "created_at": manifest["created_at"],
                                      "verified_at": datetime.now(timezone.utc).isoformat()}), "utf-8")
        if args.command == "create" and args.keep:
            prune_verified(archive.parent, args.keep)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, tarfile.TarError) as error:
        print("Erreur : " + str(error), file=sys.stderr)
        sys.exit(1)
