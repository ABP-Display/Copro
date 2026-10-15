"""Versioned streaming encrypted backup format. Authentication covers the whole tar.

AES-256-GCM with scrypt-derived key and a fresh salt/nonce for every archive.
The plaintext is never loaded in memory; a missing/tampered final tag is rejected.
"""
import hashlib
import json
import os
import tarfile
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"COPRO-BACKUP\x01"
BLOCK = 1024 * 1024
MEMBERS = {"database.dump", "media.tar", "inventory.json", "manifest.json"}
MAX_PLAINTEXT = 100 * 1024**3


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK), b""):
            digest.update(block)
    return digest.hexdigest()


def derive(password, salt):
    return Scrypt(salt=salt, length=32, n=2**17, r=8, p=1).derive(password.encode("utf-8"))


def encrypt_file(source, destination, password):
    salt, nonce = os.urandom(16), os.urandom(12)
    header = MAGIC + salt + nonce
    encryptor = Cipher(algorithms.AES(derive(password, salt)), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(header)
    with Path(source).open("rb") as plain, Path(destination).open("xb") as encrypted:
        encrypted.write(header)
        for block in iter(lambda: plain.read(BLOCK), b""):
            encrypted.write(encryptor.update(block))
        encrypted.write(encryptor.finalize())
        encrypted.write(encryptor.tag)


def decrypt_file(source, destination, password):
    source, destination = Path(source), Path(destination)
    header_size = len(MAGIC) + 28
    if source.stat().st_size < header_size + 16 or source.stat().st_size > MAX_PLAINTEXT + header_size + 16:
        raise ValueError("Taille d’archive invalide (maximum 100 Gio).")
    try:
        with source.open("rb") as encrypted:
            header = encrypted.read(header_size)
            if not header.startswith(MAGIC):
                raise ValueError("Format d’archive inconnu.")
            salt, nonce = header[len(MAGIC):len(MAGIC) + 16], header[-12:]
            encrypted.seek(-16, 2)
            tag = encrypted.read(16)
            encrypted.seek(header_size)
            decryptor = Cipher(algorithms.AES(derive(password, salt)), modes.GCM(nonce, tag)).decryptor()
            decryptor.authenticate_additional_data(header)
            remaining = source.stat().st_size - header_size - 16
            with destination.open("xb") as plain:
                while remaining:
                    block = encrypted.read(min(BLOCK, remaining))
                    if not block:
                        raise ValueError("Archive tronquée.")
                    remaining -= len(block)
                    plain.write(decryptor.update(block))
                plain.write(decryptor.finalize())
    except (InvalidTag, ValueError):
        destination.unlink(missing_ok=True)
        raise ValueError("Phrase secrète incorrecte ou archive altérée.") from None


def unpack(source, destination):
    destination = Path(destination)
    seen = set()
    total = 0
    with tarfile.open(source, "r:") as archive:
        for member in archive:
            if member.name not in MEMBERS or not member.isfile() or member.name in seen:
                raise ValueError("Structure d’archive invalide.")
            if member.name.endswith(".json") and member.size > 16 * 1024**2:
                raise ValueError("Métadonnées de sauvegarde trop volumineuses.")
            total += member.size
            if total > MAX_PLAINTEXT or member.size < 0:
                raise ValueError("Archive trop volumineuse.")
            seen.add(member.name)
            with archive.extractfile(member) as stream, (destination / member.name).open("xb") as target:
                import shutil
                shutil.copyfileobj(stream, target, BLOCK)
    if seen != MEMBERS:
        raise ValueError("Archive incomplète.")
    manifest = json.loads((destination / "manifest.json").read_text("utf-8"))
    if manifest.get("format") != 1 or set(manifest.get("contents", {})) != MEMBERS - {"manifest.json"}:
        raise ValueError("Manifeste invalide.")
    for name, expected in manifest["contents"].items():
        path = destination / name
        if expected != {"size": path.stat().st_size, "sha256": sha256(path)}:
            raise ValueError("L’empreinte d’un élément ne correspond pas au manifeste.")
    return manifest
