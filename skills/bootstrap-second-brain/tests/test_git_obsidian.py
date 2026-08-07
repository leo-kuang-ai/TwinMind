from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/bootstrap-second-brain/scripts/bootstrap_second_brain.py"
GIT = shutil.which("git")


def load_module():
    spec = importlib.util.spec_from_file_location("bootstrap_git", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(GIT, "需要本机 Git")
class GitObsidianTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bootstrap = load_module()

    def git(self, cwd: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([GIT, *args], cwd=cwd, text=True, capture_output=True, check=False)

    def test_git_boundaries_distinguish_none_independent_parent_and_worktree_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            none = root / "none"
            none.mkdir()
            self.assertEqual(self.bootstrap.inspect_git_boundary(none, GIT)["kind"], "none")
            repo = root / "repo"
            repo.mkdir()
            self.git(repo, "init", "-q")
            self.assertEqual(self.bootstrap.inspect_git_boundary(repo, GIT)["kind"], "independent")
            child = repo / "Vault"
            child.mkdir()
            self.assertEqual(self.bootstrap.inspect_git_boundary(child, GIT)["kind"], "parent")
            pointer = root / "pointer"
            pointer.mkdir()
            (pointer / ".git").write_text("gitdir: /tmp/example", encoding="utf-8")
            self.assertEqual(self.bootstrap.inspect_git_boundary(pointer, GIT)["kind"], "worktree_pointer")

    def test_parent_git_requires_explicit_choice_and_never_creates_nested_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            target = repo / "Vault"
            target.mkdir(parents=True)
            self.git(repo, "init", "-q")
            plan = self.bootstrap.build_git_baseline_plan(target, GIT, use_parent_repo=False)
            self.assertEqual(plan["command_outcome"], "action_required")
            self.assertFalse((target / ".git").exists())

    def test_explicit_parent_git_baseline_commits_only_target_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            target = repo / "Vault"
            target.mkdir(parents=True)
            self.git(repo, "init", "-q")
            self.git(repo, "config", "user.name", "Fixture")
            self.git(repo, "config", "user.email", "fixture@example.invalid")
            (repo / "existing.md").write_text("existing", encoding="utf-8")
            self.git(repo, "add", "existing.md")
            self.git(repo, "commit", "-q", "-m", "existing")
            (target / "README.md").write_text("vault", encoding="utf-8")
            plan = self.bootstrap.build_git_baseline_plan(target, GIT, use_parent_repo=True)
            self.assertEqual(plan["command_outcome"], "planned", plan)
            auth = self.bootstrap.authorize_plan(plan, [item["operation_id"] for item in plan["operations"]])
            result = self.bootstrap.apply_git_baseline(plan, auth)
            self.assertEqual(result["command_outcome"], "success", result)
            changed = self.git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout.splitlines()
            self.assertEqual(changed, ["Vault/README.md"])
            self.assertFalse((target / ".git").exists())

    def test_preexisting_staged_changes_block_without_being_committed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            self.git(target, "init", "-q")
            self.git(target, "config", "user.name", "Fixture")
            self.git(target, "config", "user.email", "fixture@example.invalid")
            (target / "user-staged.md").write_text("user", encoding="utf-8")
            self.git(target, "add", "user-staged.md")
            (target / "README.md").write_text("vault", encoding="utf-8")
            plan = self.bootstrap.build_git_baseline_plan(target, GIT)
            self.assertEqual(plan["command_outcome"], "action_required")
            self.assertIn("preexisting_staged_changes", plan["blockers"])
            self.assertNotEqual(self.git(target, "rev-parse", "--verify", "HEAD").returncode, 0)

    def test_content_drift_after_authorization_blocks_before_git_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            readme = target / "README.md"
            readme.write_text("planned", encoding="utf-8")
            plan = self.bootstrap.build_git_baseline_plan(target, GIT)
            auth = self.bootstrap.authorize_plan(plan, [item["operation_id"] for item in plan["operations"]])
            readme.write_text("changed after authorization", encoding="utf-8")
            result = self.bootstrap.apply_git_baseline(
                plan, auth, local_identity=("TwinMind User", "twinmind@example.invalid"))
            self.assertEqual(result["command_outcome"], "plan_stale")
            self.assertFalse((target / ".git").exists())

    def test_nested_git_boundary_blocks_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            nested = target / "nested"
            nested.mkdir(parents=True)
            self.git(nested, "init", "-q")
            (nested / "README.md").write_text("nested", encoding="utf-8")
            plan = self.bootstrap.build_git_baseline_plan(target, GIT)
            self.assertEqual(plan["command_outcome"], "action_required")
            self.assertIn("nested_git_boundary", plan["blockers"])

    def test_baseline_requires_authorization_and_uses_only_local_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            (target / "README.md").write_text("ok", encoding="utf-8")
            plan = self.bootstrap.build_git_baseline_plan(target, GIT)
            denied = self.bootstrap.apply_git_baseline(plan, None)
            self.assertEqual(denied["command_outcome"], "action_required")
            self.assertFalse((target / ".git").exists())
            auth = self.bootstrap.authorize_plan(plan, [item["operation_id"] for item in plan["operations"]])
            result = self.bootstrap.apply_git_baseline(plan, auth, local_identity=("TwinMind User", "twinmind@example.invalid"))
            self.assertEqual(result["lifecycle_state"], "initialized")
            self.assertRegex(result["baseline_commit_oid"], r"^[0-9a-f]{40}$")
            self.assertEqual(self.git(target, "config", "--local", "user.email").stdout.strip(), "twinmind@example.invalid")

    def test_secret_or_unrelated_staged_change_blocks_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            (target / "secret.pem").write_text("PRIVATE KEY", encoding="utf-8")
            plan = self.bootstrap.build_git_baseline_plan(target, GIT)
            self.assertEqual(plan["command_outcome"], "action_required")
            self.assertIn("secret", plan["blockers"])

    def test_hook_and_filter_are_blocked_and_never_execute(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            self.git(target, "init", "-q")
            sentinel = target / "hook-ran"
            hook = target / ".git/hooks/pre-commit"
            hook.write_text(f"#!/bin/sh\ntouch '{sentinel}'\n", encoding="utf-8")
            hook.chmod(0o755)
            (target / "README.md").write_text("ok", encoding="utf-8")
            plan = self.bootstrap.build_git_baseline_plan(target, GIT)
            self.assertEqual(plan["command_outcome"], "action_required")
            self.assertFalse(sentinel.exists())

    def test_component_states_do_not_overclaim(self) -> None:
        self.assertEqual(self.bootstrap.component_state(installed=False)["status"], "unavailable")
        self.assertEqual(self.bootstrap.component_state(installed=True)["status"], "detected")
        self.assertEqual(self.bootstrap.component_state(installed=True, opened=True)["status"], "opened")
        obsidian = self.bootstrap.obsidian_user_confirmation(
            ["File Explorer", "Search", "Quick Switcher", "Backlinks", "Templates"], "90_模板")
        self.assertEqual(obsidian["status"], "user_verified")
        self.assertEqual(obsidian["community_plugins"], [])


if __name__ == "__main__":
    unittest.main()
