from __future__ import annotations

import importlib.util
import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills/bootstrap-second-brain"
PACKAGE_SCRIPT = SKILL / "scripts/package_skill.py"
EVAL_SCRIPT = SKILL / "evals/run_evals.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EndToEndFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not PACKAGE_SCRIPT.is_file() or not EVAL_SCRIPT.is_file():
            raise AssertionError("缺少 package_skill.py 或 run_evals.py")
        cls.package = load(PACKAGE_SCRIPT, "package_skill")
        cls.evals = load(EVAL_SCRIPT, "run_evals")

    def test_bundle_is_deterministic_complete_and_safe(self) -> None:
        first = self.package.build_bundle_bytes()
        second = self.package.build_bundle_bytes()
        self.assertEqual(first, second)
        with zipfile.ZipFile(BytesIO(first)) as archive:
            names = archive.namelist()
            self.assertIn("bootstrap-second-brain/LICENSE", names)
            self.assertIn("bootstrap-second-brain/assets/starter-kit/LICENSE", names)
            self.assertIn("bootstrap-second-brain/SKILL.md", names)
            self.assertIn("bootstrap-second-brain/schemas/tool-choice.schema.json", names)
            self.assertIn("bootstrap-second-brain/schemas/tool-evidence.schema.json", names)
            self.assertFalse(any("/tests/" in name or "/evals/" in name or ".." in Path(name).parts for name in names))
            self.assertFalse(any(info.is_dir() is False and (info.external_attr >> 16) & 0o170000 == 0o120000
                                 for info in archive.infolist()))

    def test_source_contract_matches_current_starter_and_public_mit_boundary(self) -> None:
        source = self.package.read_source_contract()
        starter = json.loads((SKILL / "manifests/starter-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(source["starter_source_commit"], starter["source"]["commit"])
        self.assertEqual(source["starter_digest"], starter["source"]["tree_digest"])
        self.assertEqual(source["distribution_boundary"], "public-github-mit")
        self.assertEqual(source["license_status"], "MIT")
        self.assertEqual((ROOT / "LICENSE").read_bytes(), (SKILL / "LICENSE").read_bytes())
        self.assertEqual((ROOT / "LICENSE").read_bytes(),
                         (ROOT / "我的第二大脑/LICENSE").read_bytes())

    def test_release_policy_rejects_license_or_boundary_drift(self) -> None:
        valid_license = (SKILL / "LICENSE").read_text(encoding="utf-8")
        with self.assertRaises(self.package.PackageError):
            self.package.validate_release_policy(
                {"distribution_boundary": "owner-private-pilot", "license_status": "MIT"},
                valid_license,
            )
        with self.assertRaises(self.package.PackageError):
            self.package.validate_release_policy(
                {"distribution_boundary": "public-github-mit", "license_status": "MIT"},
                "MIT License\n\n",
            )

    def test_package_write_is_build_only_until_release_verification(self) -> None:
        result = self.package.write_bundle()
        self.assertEqual(result["artifact_status"], "build-only")
        self.assertEqual(result["distribution_authentication"], "unverified")

    def test_all_eval_suites_pass_without_writing_results_into_bundle(self) -> None:
        report = self.evals.run_all()
        self.assertEqual(report["status"], "validated")
        self.assertIn("模型行为由 skill-up", report["claim_limit"])
        self.assertEqual(
            set(report["suites"]),
            {"trigger", "behavior", "safety", "claim", "yaml-registry", "safety-cross-source"},
        )
        self.assertIn("SKILL.md 安全锚点", report["claim_limit"])

    def test_eval_yaml_registry_contract_enforced(self) -> None:
        registry = self.evals.validate_yaml_registry()
        self.assertEqual(registry["status"], "validated")
        self.assertGreaterEqual(registry["files"], 11)

    def test_empty_assertion_case_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.evals.validate_case("behavior", {"id": "x", "prompt": "p", "must": [], "must_not": []})
        with self.assertRaises(ValueError):
            self.evals.validate_case("safety", {"id": "x", "prompt": "p", "must": ["a"], "must_not": []})

    def test_must_not_keyword_inside_own_prompt_rejected(self) -> None:
        case = {"id": "x", "prompt": "要求批量刷新掉", "must": ["拒绝"], "must_not": ["批量刷新"]}
        with self.assertRaises(ValueError):
            self.evals.validate_case("safety", case)

    def test_bundle_name_tracks_starter_version(self) -> None:
        manifest = json.loads((SKILL / "manifests/starter-v1.json").read_text(encoding="utf-8"))
        expected = f"bootstrap-second-brain-v{manifest['starter_version']}.zip"
        self.assertEqual(self.package.BUNDLE_NAME, expected)

    def test_untrusted_release_stays_local_and_does_not_execute_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            sentinel = Path(temp) / "executed"
            result = self.package.verify_release_trust(
                zip_path=Path(temp) / "candidate.zip",
                attestation_path=Path(temp) / "attestation.json",
                trusted_verifier=None,
                independent_fingerprint=None,
                execution_sentinel=sentinel,
            )
            self.assertEqual(result["distribution_authentication"], "unverified")
            self.assertEqual(result["command_outcome"], "action_required")
            self.assertFalse(sentinel.exists())

    def test_verify_release_cli_exposes_external_trust_inputs(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PACKAGE_SCRIPT), "--verify-release", "--help"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for option in (
            "--trusted-verifier", "--verifier-sha256", "--public-key", "--allowed-signers",
            "--principal", "--independent-fingerprint", "--zip", "--zip-signature",
            "--attestation", "--attestation-signature",
        ):
            self.assertIn(option, result.stdout)

    @unittest.skipUnless(shutil.which("ssh-keygen"), "需要 OpenSSH ssh-keygen")
    def test_external_openssh_double_signature_verifies_both_namespaces(self) -> None:
        verifier = Path(shutil.which("ssh-keygen")).resolve()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            key = root / "owner"
            subprocess.run([str(verifier), "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
            fingerprint_output = subprocess.run(
                [str(verifier), "-lf", str(key.with_suffix(".pub")), "-E", "sha256"],
                text=True, capture_output=True, check=True,
            ).stdout
            fingerprint = next(part for part in fingerprint_output.split() if part.startswith("SHA256:"))
            allowed = root / "allowed_signers"
            allowed.write_text(f"owner {key.with_suffix('.pub').read_text(encoding='utf-8')}", encoding="utf-8")
            bundle = root / "bundle.zip"
            bundle.write_bytes(self.package.build_bundle_bytes())
            attestation = root / "attestation.json"
            attestation.write_text(json.dumps(
                self.package.create_release_attestation(bundle.read_bytes(), fingerprint),
                ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            subprocess.run([str(verifier), "-Y", "sign", "-f", str(key), "-n", "twinmind-bundle-v1", str(bundle)], check=True)
            subprocess.run([str(verifier), "-Y", "sign", "-f", str(key), "-n", "twinmind-release-attestation-v1", str(attestation)], check=True)
            result = self.package.verify_signed_release(
                trusted_verifier=verifier,
                verifier_sha256=hashlib.sha256(verifier.read_bytes()).hexdigest(),
                public_key=key.with_suffix(".pub"), allowed_signers=allowed, principal="owner",
                independent_fingerprint=fingerprint, zip_path=bundle,
                zip_signature=Path(str(bundle) + ".sig"), attestation_path=attestation,
                attestation_signature=Path(str(attestation) + ".sig"),
            )
            self.assertEqual(result["distribution_authentication"], "verified")
            cli_result = subprocess.run(
                [
                    sys.executable, str(PACKAGE_SCRIPT), "--verify-release",
                    "--trusted-verifier", str(verifier),
                    "--verifier-sha256", hashlib.sha256(verifier.read_bytes()).hexdigest(),
                    "--public-key", str(key.with_suffix(".pub")),
                    "--allowed-signers", str(allowed),
                    "--principal", "owner",
                    "--independent-fingerprint", fingerprint,
                    "--zip", str(bundle),
                    "--zip-signature", str(bundle) + ".sig",
                    "--attestation", str(attestation),
                    "--attestation-signature", str(attestation) + ".sig",
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(cli_result.returncode, 0, cli_result.stdout + cli_result.stderr)
            self.assertEqual(json.loads(cli_result.stdout)["distribution_authentication"], "verified")

            invalid_bundle = root / "invalid.zip"
            invalid_bundle.write_bytes(b"signed but not a zip")
            invalid_attestation = root / "invalid-attestation.json"
            invalid_attestation.write_text(json.dumps(
                self.package.create_release_attestation(invalid_bundle.read_bytes(), fingerprint),
                ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            subprocess.run([str(verifier), "-Y", "sign", "-f", str(key),
                            "-n", "twinmind-bundle-v1", str(invalid_bundle)], check=True)
            subprocess.run([str(verifier), "-Y", "sign", "-f", str(key),
                            "-n", "twinmind-release-attestation-v1", str(invalid_attestation)], check=True)
            with self.assertRaises(self.package.PackageError):
                self.package.verify_signed_release(
                    trusted_verifier=verifier,
                    verifier_sha256=hashlib.sha256(verifier.read_bytes()).hexdigest(),
                    public_key=key.with_suffix(".pub"), allowed_signers=allowed,
                    principal="owner", independent_fingerprint=fingerprint,
                    zip_path=invalid_bundle,
                    zip_signature=Path(str(invalid_bundle) + ".sig"),
                    attestation_path=invalid_attestation,
                    attestation_signature=Path(str(invalid_attestation) + ".sig"),
                )

    def test_fixture_manifest_covers_required_matrix(self) -> None:
        manifest = json.loads((SKILL / "evals/fixtures/fixture-manifest.json").read_text(encoding="utf-8"))
        required = {"missing-target", "empty-target", "nonempty-vault", "existing-twinmind",
                    "python-missing", "python-312-no-alias", "git-missing", "parent-git",
                    "unicode", "case-conflict", "symlink", "readonly", "copy-interrupted",
                    "inventory-entries", "inventory-filesystem-boundary", "baseline-failed"}
        self.assertTrue(required <= {item["id"] for item in manifest["fixtures"]})


if __name__ == "__main__":
    unittest.main()
