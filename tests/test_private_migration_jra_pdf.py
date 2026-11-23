import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.validate_private_migration_export import validate_export

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate_private_migration_export.py"


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


    def run_cli(self, *extra):
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--export-dir", str(self.export),
             "--manifest", str(self.manifest_path), *map(str, extra)],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )

    def test_cli_success_and_json_report_are_valid_and_outside_export(self):
        report = self.base / "reports" / "validation.json"
        report.parent.mkdir()
        before = sorted(p.relative_to(self.export).as_posix() for p in self.export.rglob("*"))
        completed = self.run_cli("--report", report)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        stdout_result = json.loads(completed.stdout)
        report_result = json.loads(report.read_text(encoding="utf-8"))
        self.assertTrue(stdout_result["ok"])
        self.assertEqual(stdout_result, report_result)
        after = sorted(p.relative_to(self.export).as_posix() for p in self.export.rglob("*"))
        self.assertEqual(before, after)

    def test_cli_writes_machine_readable_failure_report_for_invalid_export(self):
        (self.export / "scripts/example.py").write_bytes(b"tampered synthetic content")
        report = self.base / "reports" / "failed-validation.json"
        report.parent.mkdir()
        completed = self.run_cli("--report", report)
        self.assertEqual(completed.returncode, 1)
        stdout_result = json.loads(completed.stdout)
        report_result = json.loads(report.read_text(encoding="utf-8"))
        self.assertFalse(stdout_result["ok"])
        self.assertEqual(stdout_result, report_result)
        self.assertTrue(any(x.startswith("SHA256_MISMATCH:") for x in report_result["findings"]))

    def test_cli_returns_json_and_nonzero_for_malformed_manifest(self):
        self.manifest_path.write_text("{", encoding="utf-8")
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 1)
        result = json.loads(completed.stdout)
        self.assertFalse(result["ok"])
        self.assertTrue(any(x.startswith("MANIFEST_OR_INPUT_ERROR:") for x in result["findings"]))

    def test_cli_refuses_report_inside_export_without_creating_it(self):
        report = self.export / "validation.json"
        completed = self.run_cli("--report", report)
        self.assertEqual(completed.returncode, 1)
        result = json.loads(completed.stdout)
        self.assertTrue(any(x.startswith("REPORT_WRITE_ERROR:") and "outside the export" in x for x in result["findings"]))
        self.assertFalse(report.exists())

    def test_cli_refuses_symlink_report_without_touching_target(self):
        target = self.base / "keep.txt"
        target.write_text("keep-me", encoding="utf-8")
        report = self.base / "report-link.json"
        try:
            report.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        completed = self.run_cli("--report", report)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(target.read_text(encoding="utf-8"), "keep-me")
        result = json.loads(completed.stdout)
        self.assertTrue(any(x.startswith("REPORT_WRITE_ERROR:") and "symlink" in x for x in result["findings"]))

    def test_cli_refuses_to_overwrite_existing_report(self):
        report = self.base / "existing-report.json"
        report.write_text("keep-me", encoding="utf-8")
        completed = self.run_cli("--report", report)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(report.read_text(encoding="utf-8"), "keep-me")
        result = json.loads(completed.stdout)
        self.assertTrue(any(x.startswith("REPORT_WRITE_ERROR:") and "refusing to overwrite" in x for x in result["findings"]))

    def test_cli_refuses_report_path_that_is_the_manifest(self):
        original = self.manifest_path.read_bytes()
        completed = self.run_cli("--report", self.manifest_path)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(self.manifest_path.read_bytes(), original)
        result = json.loads(completed.stdout)
        self.assertTrue(any(x.startswith("REPORT_WRITE_ERROR:") and "must not overwrite the manifest" in x for x in result["findings"]))

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

    def test_rejects_all_high_risk_directory_patterns_case_insensitively(self):
        forbidden_dirs = ("results", "private_input", "private-input", "output", "outputs",
                          "data", "datasets", "snapshots", "models", "logs", "cache",
                          ".git", ".ssh", ".aws", ".gnupg", "credentials", "secrets", "tokens")
        for directory in forbidden_dirs:
            self.write_export(f"{directory}/sample.py", b"synthetic")
        findings = self.result()["findings"]
        for directory in forbidden_dirs:
            with self.subTest(directory=directory):
                self.assertTrue(any(x.startswith(f"EXCLUDED_PATH: {directory}/") for x in findings))

    def test_rejects_private_data_and_model_file_extensions(self):
        forbidden_files = ("race.pdf", "state.sqlite", "state.db", "features.parquet",
                           "model.pkl", "model.joblib", "model.onnx", "model.pt",
                           "model.pth", "model.h5", "odds.csv", "manifest.json")
        for filename in forbidden_files:
            self.write_export(f"docs/{filename}", b"synthetic")
        findings = self.result()["findings"]
        for filename in forbidden_files:
            with self.subTest(filename=filename):
                self.assertTrue(any(x.startswith(f"EXCLUDED_PATH: docs/{filename}") for x in findings))

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

    def test_rejects_windows_reserved_names_and_alternate_stream_paths(self):
        for unsafe_path in ("CON.py", "notes.txt:stream.py", "folder./module.py"):
            entry = {
                "path": unsafe_path, "source_git_blob_sha1": "b" * 40,
                "source_bytes": 1, "status": "ALLOW_CANDIDATE",
                "export": True, "expected_sha256": self.digest,
            }
            self.write_manifest([entry])
            with self.subTest(path=unsafe_path), self.assertRaisesRegex(ValueError, "unsafe"):
                self.result()

    def test_rejects_boolean_as_source_byte_count(self):
        entry = {
            "path": "scripts/example.py", "source_git_blob_sha1": "b" * 40,
            "source_bytes": True, "status": "ALLOW_CANDIDATE",
            "export": True, "expected_sha256": self.digest,
        }
        self.write_manifest([entry])
        with self.assertRaisesRegex(ValueError, "byte count"):
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
