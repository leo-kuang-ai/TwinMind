from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/bootstrap-second-brain/scripts/bootstrap_second_brain.py"


def load_module():
    spec = importlib.util.spec_from_file_location("bootstrap_second_brain_apply", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 bootstrap_second_brain.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ApplyRecoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bootstrap = load_module()

    def authorization(self, plan: dict) -> dict:
        return self.bootstrap.authorize_plan(plan, [item["operation_id"] for item in plan["operations"]])

    def scaffold_plan(self, target: Path, *, allow_existing_projection: bool = False) -> dict:
        receipt = self.bootstrap.example_verified_tool_readiness_receipt("run-apply-test")
        return self.bootstrap.build_scaffold_plan(
            target, receipt, allow_existing_projection=allow_existing_projection)

    def test_plan_drift_fails_before_any_target_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            plan = self.scaffold_plan(target)
            (target / "user.md").write_text("new", encoding="utf-8")
            before = self.bootstrap.VERIFY.snapshot_tree(target)
            result = self.bootstrap.apply_scaffold(plan, self.authorization(plan))
            self.assertEqual(result["command_outcome"], "plan_stale")
            self.assertEqual(self.bootstrap.VERIFY.snapshot_tree(target), before)

    def test_starter_asset_drift_fails_before_any_target_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            target.mkdir()
            plan = self.scaffold_plan(target)
            copied_assets = root / "starter-kit"
            shutil.copytree(self.bootstrap.ASSET_ROOT, copied_assets)
            (copied_assets / "README.md").write_text("tampered", encoding="utf-8")
            original = self.bootstrap.ASSET_ROOT
            self.bootstrap.ASSET_ROOT = copied_assets
            try:
                result = self.bootstrap.apply_scaffold(plan, self.authorization(plan))
            finally:
                self.bootstrap.ASSET_ROOT = original
            self.assertEqual(result["command_outcome"], "plan_stale")
            self.assertEqual(list(target.iterdir()), [])

    def test_apply_is_idempotent_and_conflicts_do_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            plan = self.scaffold_plan(target)
            auth = self.authorization(plan)
            first = self.bootstrap.apply_scaffold(plan, auth)
            self.assertEqual(first["command_outcome"], "success")
            second_plan = self.scaffold_plan(target, allow_existing_projection=True)
            second = self.bootstrap.apply_scaffold(second_plan, self.authorization(second_plan))
            self.assertEqual(second["command_outcome"], "no_changes")
            file_path = target / "README.md"
            file_path.write_text("user changed", encoding="utf-8")
            conflict_plan = self.scaffold_plan(target, allow_existing_projection=True)
            conflict = self.bootstrap.apply_scaffold(conflict_plan, self.authorization(conflict_plan))
            self.assertEqual(conflict["command_outcome"], "conflict")
            self.assertEqual(file_path.read_text(encoding="utf-8"), "user changed")

    def test_casefold_conflict_in_parent_directory_stops_without_parallel_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            (target / "50_skills").mkdir()
            plan = self.scaffold_plan(target, allow_existing_projection=True)
            result = self.bootstrap.apply_scaffold(plan, self.authorization(plan))
            self.assertEqual(result["command_outcome"], "conflict")
            self.assertFalse(any(path.name == "50_Skills" for path in target.iterdir()))

    def test_partial_failure_records_only_completed_writes_and_can_recover(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            plan = self.scaffold_plan(target)
            result = self.bootstrap.apply_scaffold(plan, self.authorization(plan), fail_after=2)
            self.assertEqual(result["command_outcome"], "partial")
            self.assertEqual(len(result["completed_operations"]), 2)
            recovered = self.bootstrap.recover_pre_baseline(target, result["created_files"])
            self.assertEqual(recovered["command_outcome"], "success")
            self.assertEqual(list(target.iterdir()), [])

    def test_missing_target_uses_sibling_staging_and_atomic_rename(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "新 Vault"
            plan = self.scaffold_plan(target)
            result = self.bootstrap.apply_scaffold(plan, self.authorization(plan))
            self.assertEqual(result["command_outcome"], "success")
            self.assertTrue((target / "README.md").is_file())
            self.assertIsNone(result["staging_path"])

    def test_missing_target_race_keeps_staging_and_never_overwrites_winner(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "竞态 Vault"
            plan = self.scaffold_plan(target)

            def win_race() -> None:
                target.mkdir()
                (target / "winner.md").write_text("user", encoding="utf-8")

            result = self.bootstrap.apply_scaffold(plan, self.authorization(plan), before_rename=win_race)
            self.assertEqual(result["command_outcome"], "conflict")
            self.assertEqual((target / "winner.md").read_text(encoding="utf-8"), "user")
            self.assertTrue(Path(result["staging_path"]).is_dir())

    def test_recover_preserves_user_modified_and_append_only_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            plan = self.scaffold_plan(target)
            result = self.bootstrap.apply_scaffold(plan, self.authorization(plan))
            changed = target / "README.md"
            changed.write_text("user changed", encoding="utf-8")
            recovered = self.bootstrap.recover_pre_baseline(target, result["created_files"])
            self.assertTrue(changed.exists())
            self.assertTrue((target / "维护日志.md").exists())
            self.assertIn("README.md", recovered["preserved_paths"])
            self.assertIn("维护日志.md", recovered["preserved_paths"])

    def test_recover_rejects_absolute_or_parent_escape_receipt_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            target.mkdir()
            outside = root / "outside.md"
            outside.write_text("preserve", encoding="utf-8")
            digest = self.bootstrap._sha256(outside)
            result = self.bootstrap.recover_pre_baseline(target, [
                {"path": str(outside), "sha256": digest, "ownership": "static"},
                {"path": "../outside.md", "sha256": digest, "ownership": "static"},
            ])
            self.assertTrue(outside.exists())
            self.assertEqual(result["removed_paths"], [])
            self.assertTrue(all(path.startswith("unsafe-path-digest:") for path in result["preserved_paths"]))

    def test_host_tool_action_requires_exact_authorization(self) -> None:
        calls: list[tuple[str, str]] = []
        identity = self.bootstrap._tool_identity("workbuddy")
        plan = self.bootstrap.build_host_tool_plan(
            "workbuddy", self.bootstrap.VERIFY.digest_value(identity),
            "open-source", "https://www.workbuddy.ai/")
        denied = self.bootstrap.apply_host_tool(plan, None, lambda action, value: calls.append((action, value)))
        self.assertEqual(denied["command_outcome"], "action_required")
        self.assertEqual(calls, [])
        auth = self.authorization(plan)
        applied = self.bootstrap.apply_host_tool(plan, auth, lambda action, value: calls.append((action, value)))
        self.assertEqual(applied["command_outcome"], "success")
        self.assertEqual(calls, [("open-source", "https://www.workbuddy.ai/")])

    def test_post_baseline_recovery_never_deletes_history(self) -> None:
        compensation = self.bootstrap.build_post_baseline_recovery_plan(
            baseline_oid="a" * 40,
            current_head="a" * 40,
            tree_matches=True,
            user_touched_paths=False,
        )
        self.assertEqual(compensation["recovery_mode"], "post_baseline_compensation")
        manual = self.bootstrap.build_post_baseline_recovery_plan(
            baseline_oid="a" * 40,
            current_head="b" * 40,
            tree_matches=False,
            user_touched_paths=True,
        )
        self.assertEqual(manual["recovery_mode"], "manual_git_recovery")
        self.assertEqual(manual["operations"], [])

    def test_cleanup_is_run_scoped_and_all_requires_recovery_loss_ack(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "state"
            run = state / "run-1"
            other = state / "run-2"
            run.mkdir(parents=True)
            other.mkdir()
            (run / "interview-cache.json").write_text("{}", encoding="utf-8")
            (run / "plan.json").write_text("{}", encoding="utf-8")
            (other / "plan.json").write_text("other", encoding="utf-8")
            with self.assertRaises(self.bootstrap.VERIFY.SafetyError):
                self.bootstrap.build_cleanup_plan(state, "run-1", "all")
            plan = self.bootstrap.build_cleanup_plan(state, "run-1", "all", acknowledge_recovery_loss=True)
            result = self.bootstrap.apply_cleanup(plan, self.authorization(plan))
            self.assertEqual(result["command_outcome"], "success")
            self.assertTrue((other / "plan.json").exists())

    def test_cleanup_rejects_run_parent_replaced_by_symlink_after_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state"
            run = state / "run-1"
            outside = root / "outside"
            run.mkdir(parents=True)
            outside.mkdir()
            (run / "interview-cache.json").write_text("{}", encoding="utf-8")
            plan = self.bootstrap.build_cleanup_plan(state, "run-1", "interview")
            run.rename(state / "run-original")
            run.symlink_to(outside, target_is_directory=True)
            result = self.bootstrap.apply_cleanup(plan, self.authorization(plan))
            self.assertEqual(result["command_outcome"], "plan_stale")
            self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
