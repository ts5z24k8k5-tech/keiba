from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class WorkflowSecurityPolicyTests(unittest.TestCase):
    def _read(self, name: str) -> str:
        return (WORKFLOWS / name).read_text(encoding="utf-8")

    def _assert_private_gate_precedes(self, source: str, protected_step: str) -> None:
        gate = source.index("Require private repository")
        secret_or_data = source.index(protected_step)
        self.assertLess(gate, secret_or_data)
        self.assertIn("GH_TOKEN: ${{ github.token }}", source)
        self.assertIn('gh api "repos/${GITHUB_REPOSITORY}" --jq .visibility', source)
        self.assertIn('if [ "$visibility" != "private" ]; then', source)
        self.assertIn("exit 1", source[gate:secret_or_data])

    def test_pdf_acquisition_gates_before_secret_restore(self) -> None:
        source = self._read("research-acquire-jra-pdfs.yml")
        self._assert_private_gate_precedes(source, "Restore private manifest")
        self.assertIn("if: success()", source)
        self.assertNotIn("if: always()", source)

    def test_historical_dataset_gates_before_download_and_uploads_only_on_success(self) -> None:
        source = self._read("collect-jra.yml")
        self._assert_private_gate_precedes(source, "Download source CSVs")
        self.assertIn("if: success()", source)
        self.assertNotIn("if: always()", source)

    def test_odds_capture_is_private_manual_only_and_narrowly_published(self) -> None:
        source = self._read("fetch-current-odds.yml")
        self._assert_private_gate_precedes(source, "Fetch odds for the race ID")
        trigger = source.split("permissions:", 1)[0]
        self.assertIn("workflow_dispatch:", trigger)
        self.assertNotIn("  push:", trigger)
        self.assertIn("if: success()", source)
        self.assertIn("results/live_odds/all_pools_snapshot.json", source)
        self.assertIn("results/live_odds/snapshot_audit.json", source)
        self.assertIn("git add results/live_odds/all_pools_snapshot.json results/live_odds/snapshot_audit.json", source)
        self.assertNotIn("git push || true", source)
        self.assertNotIn("git commit -m", source.split("if: success()", 1)[0])

    def test_local_inputs_and_generated_outputs_are_gitignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (
            "private_input/",
            "output/",
            ".env",
            ".env.*",
            "*.pem",
            "*.key",
            "*.sqlite",
            "*.sqlite3",
            "*.db",
            "*.parquet",
            "*.pkl",
            "*.joblib",
            "*.onnx",
            "*.pt",
            "*.pth",
            "*.h5",
        ):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, ignore)

    def test_pdf_artifact_not_uploaded_on_failed_acquisition(self) -> None:
        source = self._read("research-acquire-jra-pdfs.yml")
        upload = source.index("uses: actions/upload-artifact@v4")
        self.assertIn("if: success()", source[max(0, upload - 100):upload])


if __name__ == "__main__":
    unittest.main()
