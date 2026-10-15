import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from archive_format import encrypt_file, decrypt_file, sha256, unpack
from backup import prune_verified


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "plain"
        self.source.write_bytes(b"private-data" * 200000)
        self.encrypted = self.root / "backup.coprobackup"
        self.password = "Test-only-backup-passphrase!"

    def test_stream_roundtrip_and_no_plaintext_in_archive(self):
        encrypt_file(self.source, self.encrypted, self.password)
        self.assertNotIn(b"private-data", self.encrypted.read_bytes())
        decrypt_file(self.encrypted, self.root / "restored", self.password)
        self.assertEqual(sha256(self.source), sha256(self.root / "restored"))

    def test_wrong_password_tampering_and_truncation_rejected_and_plaintext_removed(self):
        encrypt_file(self.source, self.encrypted, self.password)
        original = self.encrypted.read_bytes()
        for data, password in [(original, "wrong"), (original[:100] + bytes([original[100] ^ 1]) + original[101:], self.password), (original[:-20], self.password)]:
            self.encrypted.write_bytes(data)
            destination = self.root / "restored"
            with self.assertRaises(ValueError):
                decrypt_file(self.encrypted, destination, password)
            self.assertFalse(destination.exists())

    def test_unknown_members_links_duplicates_and_missing_files_rejected(self):
        for names in [["../outside"], ["database.dump", "database.dump"], ["database.dump"]]:
            path = self.root / "snapshot.tar"
            with tarfile.open(path, "w") as archive:
                for name in names:
                    archive.addfile(tarfile.TarInfo(name))
            directory = self.root / "out"; directory.mkdir(exist_ok=True)
            for file in directory.iterdir():
                file.unlink()
            with self.assertRaises(ValueError):
                unpack(path, directory)

    def test_retention_preserves_unverified_and_unrelated_files(self):
        for index in range(3):
            archive = self.root / f"copro-{index}.coprobackup"; archive.write_bytes(str(index).encode())
            archive.with_name(archive.name + ".verified.json").write_text(json.dumps({"sha256": sha256(archive), "verified_at": str(3-index), "created_at": str(index)}))
        untouched = self.root / "copro-unverified.coprobackup"; untouched.write_bytes(b"keep")
        safety = self.root / "avant-restauration-safe.coprobackup"; safety.write_bytes(b"keep")
        prune_verified(self.root, 1)
        self.assertEqual(len(list(self.root.glob("*.coprobackup"))), 3)
        self.assertTrue((self.root / "copro-2.coprobackup").exists())
        self.assertTrue(untouched.exists()); self.assertTrue(safety.exists())


if __name__ == "__main__":
    unittest.main()
