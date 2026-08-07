from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/bootstrap-second-brain/scripts/render_profile.py"
BOOTSTRAP_SCRIPT = ROOT / "skills/bootstrap-second-brain/scripts/bootstrap_second_brain.py"


def load_module():
    spec = importlib.util.spec_from_file_location("render_profile", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 render_profile.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InterviewRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not SCRIPT.is_file():
            raise AssertionError("缺少 render_profile.py")
        cls.render = load_module()

    def answer(self, field_id: str, value: str, **overrides) -> dict:
        answer = {
            "schema_version": 1, "field_id": field_id, "value": value,
            "sensitivity": "normal", "persistence": "vault_confirmed",
            "status": "confirmed", "evidence_type": "user_statement",
            "confirmed_at": "2026-08-07T12:00:00+08:00",
        }
        answer.update(overrides)
        return answer

    def test_minimum_first_round_converges_and_defers_unanswered_dimensions(self) -> None:
        session = self.render.InterviewSession("run-1")
        for field_id in self.render.MINIMUM_FIELD_IDS:
            session.update(self.answer(field_id, f"{field_id}-value"))
        summary = session.summary()
        self.assertTrue(summary["minimum_complete"])
        self.assertTrue(summary["deferred_to_seven_day_plan"])

    def test_agent_inference_cannot_be_confirmed(self) -> None:
        session = self.render.InterviewSession("run-1")
        with self.assertRaises(self.render.InterviewError):
            session.update(self.answer("primary_scenario", "推断", evidence_type="agent_inference"))

    def test_confidential_and_restricted_fail_closed_without_leakage(self) -> None:
        secret = "绝不能出现在状态中的秘密"
        session = self.render.InterviewSession("run-1", host_permission_confirmed=False)
        with self.assertRaises(self.render.InterviewError):
            session.update(self.answer("primary_scenario", secret, sensitivity="confidential"))
        with self.assertRaises(self.render.InterviewError):
            session.update(self.answer("primary_scenario", secret, sensitivity="restricted"))
        self.assertNotIn(secret, str(session.public_state()))

    def test_nonlocal_confidential_runtime_state_requires_verified_encryption(self) -> None:
        answer = self.answer("primary_scenario", "secret", sensitivity="confidential", persistence="runtime_state")
        with self.assertRaises(self.render.InterviewError):
            self.render.InterviewSession("run-default-unknown").update(answer)
        for domain in ("cloud_synced", "network", "removable", "unknown"):
            session = self.render.InterviewSession("run-1", host_permission_confirmed=True,
                storage={"storage_domain": domain, "encryption_status": "unavailable"})
            with self.subTest(domain=domain), self.assertRaises(self.render.InterviewError):
                session.update(answer)
            self.assertNotIn("secret", str(session.public_state()))
        session = self.render.InterviewSession("run-1", host_permission_confirmed=True,
            storage={"storage_domain": "local_fixed", "encryption_status": "unavailable"})
        session.update(answer)
        self.assertEqual(session.confirmed_answers()["primary_scenario"], "secret")

    def test_skip_correct_withdraw_and_resume_respect_persistence(self) -> None:
        session = self.render.InterviewSession("run-1")
        session.update(self.answer("primary_scenario", "old", persistence="session_only"))
        session.update(self.answer("maintenance_budget", "30 min"))
        session.update({"schema_version": 1, "field_id": "primary_scenario", "sensitivity": "normal",
                        "persistence": "session_only", "status": "withdrawn", "evidence_type": "user_statement",
                        "confirmed_at": "2026-08-07T12:01:00+08:00"})
        resumed = self.render.InterviewSession.resume("run-1", session.persistable_state())
        self.assertNotIn("primary_scenario", resumed.confirmed_answers())
        self.assertEqual(resumed.confirmed_answers()["maintenance_budget"], "30 min")

    def test_render_is_deterministic_and_generated_once_never_overwrites(self) -> None:
        answers = {field_id: f"值-{field_id}" for field_id in self.render.MINIMUM_FIELD_IDS}
        first = self.render.render_profile(answers)
        self.assertEqual(first, self.render.render_profile(dict(reversed(list(answers.items())))))
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            existing = target / "10_当前工作台/01_个人运行地图.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("用户内容", encoding="utf-8")
            result = self.render.apply_rendered_profile(target, first)
            self.assertEqual(existing.read_text(encoding="utf-8"), "用户内容")
            self.assertIn("10_当前工作台/01_个人运行地图.md", result["diff_only"])

    def test_render_rejects_symlinked_parent_directory(self) -> None:
        rendered = self.render.render_profile({"primary_scenario": "安全初始化"})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            (target / "10_当前工作台").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(self.render.InterviewError):
                self.render.apply_rendered_profile(target, rendered)
            self.assertEqual(list(outside.iterdir()), [])

    def test_personalize_plan_is_stable_and_independent_from_scaffold_authorization(self) -> None:
        spec = importlib.util.spec_from_file_location("bootstrap_for_personalize", BOOTSTRAP_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            target.mkdir()
            scaffold = module.build_scaffold_plan(target)
            answers = {"primary_scenario": "处理重复评审"}
            first = module.build_personalize_plan("run-1", target, answers)
            second = module.build_personalize_plan("run-1", target, answers)
            self.assertEqual(first, second)
            self.assertNotEqual(first["plan_digest"], scaffold["plan_digest"])
            self.assertEqual(first["plan_stage"], "personalize")


if __name__ == "__main__":
    unittest.main()
