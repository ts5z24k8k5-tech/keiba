import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_private_migration_export import validate_export


class PrivateMigrationExportValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.export = self.base / "export"
        self.export.mkdir()
        self.manifest_path = self.base / "manifest.json"
        self.body = b"synthetic-safe-source\n"
        self.digest = hashlib.sha256(self.body).hexdigest()
        self.write_export("scripts/example.py", self.body)
        self.write_manifest()

    def write_export(self, rel, body):
        target = self.export / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        return target

    def write_manifest(self, entries=None):
        payload = {
            "schema_version": 1,
            "source": {"repository": "example/private", "ref": "test", "commit": "a" * 40},
            "entries": entries or [{
                "path": "scripts/example.py",
                "source_git_blob_sha1": "b" * 40,
                "source_bytes": len(self.body),
                "status": "ALLOW_CANDIDATE",
                "export": True,
                "expected_sha256": self.digest,
            }],
        }
        self.manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    def result(self):
        return validate_export(self.export, self.manifest_path)

    def test_accepts_exact_allowlisted_file_with_matching_sha256(self):
        result = self.result()
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["sha256_checked"], 1)

    def test_rejects_unlisted_file(self):
        self.write_export("notes.txt", b"not approved")
        self.assertIn("UNAUTHORIZED_FILE: notes.txt", self.result()["findings"])

    def test_rejects_excluded_results_even_if_someone_adds_it_to_manifest(self):
        self.write_export("results/predictions.csv", b"synthetic")
        self.assertTrue(any(x.startswith("EXCLUDED_PATH: results/") for x in self.result()["findings"]))
        self.assertTrue(any(x.startswith("UNAUTHORIZED_FILE: results/") for x in self.result()["findings"]))

    def test_rejects_forbidden_extension_and_secret_names(self):
        self.write_export("private_input/manifest.json", b"{}")
        self.write_export(".env", b"FAKE=1")
        findings = self.result()["findings"]
        self.assertTrue(any(x.startswith("EXCLUDED_PATH: .env") for x in findings))
        self.assertTrue(any(x.startswith("EXCLUDED_PATH: private_input/") for x in findings))

    def test_detects_missing_allowlisted_file(self):
        (self.export / "scripts/example.py").unlink()
        self.assertIn("MISSING_FILE: scripts/example.py", self.result()["findings"])

    def test_detects_modified_bytes_by_sha256(self):
        (self.export / "scripts/example.py").write_bytes(b"tampered synthetic data")
        self.assertTrue(any(x.startswith("SHA256_MISMATCH: scripts/example.py") for x in self.result()["findings"]))

    def test_detects_size_mismatch_independently(self):
        (self.export / "scripts/example.py").write_bytes(b"x")
        self.assertTrue(any(x.startswith("SIZE_MISMATCH: scripts/example.py") for x in self.result()["findings"]))

    def test_fails_closed_when_sha256_is_not_pinned(self):
        entry = {
            "path": "scripts/example.py",
            "source_git_blob_sha1": "b" * 40,
            "source_bytes": len(self.body),
            "status": "ALLOW_CANDIDATE",
            "export": True,
            "expected_sha256": None,
        }
        self.write_manifest([entry])
        result = self.result()
        self.assertTrue(any(x.startswith(f"SHA256_UNPINNED: scripts/example.py: actual={self.digest}") for x in result["findings"]))
        self.assertEqual(result["sha256_checked"], 1)

    def test_rejects_duplicate_manifest_paths(self):
        entry = {
            "path": "scripts/example.py", "source_git_blob_sha1": "b" * 40,
            "source_bytes": len(self.body), "status": "ALLOW_CANDIDATE", "export": True, "expected_sha256": self.digest,
        }
        self.write_manifest([entry, entry])
        with self.assertRaisesRegex(ValueError, "duplicate manifest path"):
            self.result()

    def test_rejects_manifest_path_traversal(self):
        entry = {
            "path": "../outside.py", "source_git_blob_sha1": "b" * 40,
            "source_bytes": 1, "status": "ALLOW_CANDIDATE", "export": True, "expected_sha256": self.digest,
        }
        self.write_manifest([entry])
        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.result()

    def test_rejects_rewrite_required_entry_even_if_export_flag_is_set(self):
        entry = {
            "path": "scripts/example.py", "source_git_blob_sha1": "b" * 40,
            "source_bytes": len(self.body), "status": "REWRITE_REQUIRED",
            "export": True, "expected_sha256": self.digest,
        }
        self.write_manifest([entry])
        with self.assertRaisesRegex(ValueError, "cannot be exported"):
            self.result()

    def test_rejects_windows_drive_and_case_colliding_paths(self):
        entry = {
            "path": "C:/outside.py", "source_git_blob_sha1": "b" * 40,
            "source_bytes": 1, "status": "ALLOW_CANDIDATE", "export": True, "expected_sha256": self.digest,
        }
        self.write_manifest([entry])
        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.result()
        upper = {
            "path": "Scripts/example.py", "source_git_blob_sha1": "b" * 40,
            "source_bytes": len(self.body), "status": "ALLOW_CANDIDATE", "export": True, "expected_sha256": self.digest,
        }
        lower = dict(upper, path="scripts/example.py")
        self.write_manifest([upper, lower])
        with self.assertRaisesRegex(ValueError, "case-colliding"):
            self.result()

    def test_rejects_symlink(self):
        link = self.export / "scripts" / "linked.py"
        try:
            link.symlink_to(self.export / "scripts" / "example.py")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        findings = self.result()["findings"]
        self.assertIn("SYMLINK_REJECTED: scripts/linked.py", findings)

    def test_rejects_empty_or_malformed_manifest(self):
        self.manifest_path.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "cannot read manifest"):
            self.result()

    def test_rejects_unapproved_json_even_when_added_to_manifest(self):
        body = b"synthetic-json"
        self.write_export("docs/extra.json", body)
        entries = [{
            "path": "scripts/example.py", "source_git_blob_sha1": "b" * 40,
            "source_bytes": len(self.body), "status": "ALLOW_CANDIDATE", "export": True, "expected_sha256": self.digest,
        }, {
            "path": "docs/extra.json", "source_git_blob_sha1": "c" * 40,
            "source_bytes": len(body), "status": "ALLOW_CANDIDATE", "export": True,
            "expected_sha256": hashlib.sha256(body).hexdigest(),
        }]
        self.write_manifest(entries)
        self.assertTrue(any(x.startswith("EXCLUDED_PATH: docs/extra.json") for x in self.result()["findings"]))


if __name__ == "__main__":
    unittest.main()
