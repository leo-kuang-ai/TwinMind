from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/bootstrap-second-brain/scripts/bootstrap_second_brain.py"
MANIFEST = ROOT / "skills/bootstrap-second-brain/manifests/tool-identities-v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("bootstrap_tools", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ToolReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bootstrap = load_module()

    def test_identity_manifest_is_complete_and_digest_valid(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls = self.bootstrap._load_contract_module()
        cls.validate_tool_identity_manifest(manifest)

    def test_git_missing_blocks_path_confirmation_without_target_probe(self) -> None:
        target_calls = []
        readiness = self.bootstrap.tool_probe_host(
            platform="macos", python_evidence={"status": "ready", "official_verified": True},
            git_evidence={"status": "missing", "official_verified": False},
            app_evidence={}, target_probe=lambda: target_calls.append(True),
        )
        self.assertFalse(readiness["path_confirmation_ready"])
        self.assertEqual(target_calls, [])
        self.assertEqual(readiness["tools"]["community_plugins"]["selected"], [])

    def test_tool_plan_cards_are_complete_and_have_no_side_effects(self) -> None:
        calls = []
        readiness = self.bootstrap.example_missing_recommended_readiness()
        plan = self.bootstrap.build_tool_plan(readiness, side_effect=lambda *args: calls.append(args))
        self.assertEqual(calls, [])
        required = {"official_url", "platform", "license_cost_review", "data_permissions",
                    "network_boundary", "logs_cache_secrets", "disable_uninstall", "verification", "next_action"}
        for tool_id in ("git", "workbuddy", "obsidian"):
            self.assertTrue(required <= set(plan["cards"][tool_id]))

    def test_official_url_validator_rejects_lookalikes_credentials_and_paths(self) -> None:
        valid = {"workbuddy": "https://www.workbuddy.ai/", "obsidian": "https://obsidian.md/"}
        for tool_id, url in valid.items():
            self.bootstrap.validate_official_url(tool_id, url)
        invalid = [
            ("workbuddy", "http://www.workbuddy.ai/"),
            ("workbuddy", "https://workbuddy.ai/"),
            ("workbuddy", "https://www.workbuddy.ai.evil.test/"),
            ("workbuddy", "https://user:pass@www.workbuddy.ai/"),
            ("workbuddy", "https://www.workbuddy.ai/download"),
            ("obsidian", "https://download.obsidian.md/"),
        ]
        for tool_id, url in invalid:
            with self.subTest(url=url), self.assertRaises(self.bootstrap.VERIFY.SafetyError):
                self.bootstrap.validate_official_url(tool_id, url)

    def test_recommended_tools_require_verified_or_explicit_defer(self) -> None:
        readiness = self.bootstrap.example_missing_recommended_readiness()
        result = self.bootstrap.verify_tool_readiness(readiness, choices={})
        self.assertEqual(result["command_outcome"], "action_required")
        result = self.bootstrap.verify_tool_readiness(
            readiness, choices={"workbuddy": "deferred_by_user", "obsidian": "deferred_by_user"})
        self.assertEqual(result["command_outcome"], "success")
        self.assertFalse(result["tools"]["workbuddy"]["ready"])

    def test_vault_scope_requires_selected_existing_target_and_never_reads_outside(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            (target / ".obsidian").mkdir()
            (target / ".obsidian" / "core-plugins.json").write_text("[]", encoding="utf-8")
            report = self.bootstrap.tool_probe_vault(target, selected_target=target)
            self.assertEqual(report["community_plugins"]["selected"], [])
            with self.assertRaises(self.bootstrap.VERIFY.SafetyError):
                self.bootstrap.tool_probe_vault(target, selected_target=None)


if __name__ == "__main__":
    unittest.main()
