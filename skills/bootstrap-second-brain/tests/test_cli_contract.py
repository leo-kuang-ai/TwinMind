from __future__ import annotations

import json
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/bootstrap-second-brain/scripts/bootstrap_second_brain.py"
CONTRACT_SCRIPT = ROOT / "skills/bootstrap-second-brain/scripts/contract_validation.py"


class CliContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("cli_contract_validation", CONTRACT_SCRIPT)
        cls.contracts = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.contracts)
        bootstrap_spec = importlib.util.spec_from_file_location("cli_bootstrap_module", SCRIPT)
        cls.bootstrap = importlib.util.module_from_spec(bootstrap_spec)
        bootstrap_spec.loader.exec_module(cls.bootstrap)

    def run_cli(self, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-I", "-S", "-E", str(SCRIPT), *args],
            cwd=ROOT,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def prepare_tool_readiness(self, root: Path, state: Path, run_id: str) -> None:
        readiness = self.bootstrap.example_missing_recommended_readiness()
        tool_plan_path = root / f"{run_id}-tool-plan.json"
        tool_plan_path.write_text(
            json.dumps(self.bootstrap.build_tool_plan(readiness)), encoding="utf-8")
        choices_path = root / f"{run_id}-tool-choices.json"
        choices_path.write_text(json.dumps({
            "workbuddy": "deferred_by_user",
            "obsidian": "deferred_by_user",
        }), encoding="utf-8")
        verified = self.run_cli(
            "tool-verify", "--plan", str(tool_plan_path), "--choices", str(choices_path),
            "--run-id", run_id, "--state-dir", str(state), "--json",
        )
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

    def test_all_documented_subcommands_are_exposed_under_isolated_python(self) -> None:
        commands = {
            "tool-probe", "tool-plan", "tool-choice-update", "tool-action-plan",
            "tool-evidence-update", "tool-verify", "probe", "plan", "interview-update",
            "authorize", "apply", "verify", "resume", "recover-plan", "recover",
            "cleanup-plan", "cleanup",
        }
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for command in commands:
            with self.subTest(command=command):
                self.assertIn(command, result.stdout)
                help_result = self.run_cli(command, "--help")
                self.assertEqual(help_result.returncode, 0, help_result.stdout + help_result.stderr)

    def test_tool_plan_and_authorize_emit_one_json_object(self) -> None:
        readiness = {
            "schema_version": 1,
            "platform": "macos",
            "observed_at": "2026-08-07T12:00:00+08:00",
            "path_confirmation_ready": True,
            "tools": {
                "python": {"requirement": "runtime-required", "status": "ready", "official_verified": True},
                "git": {"requirement": "product-required", "status": "ready", "official_verified": True},
                "workbuddy": {"requirement": "recommended", "status": "missing", "official_verified": False},
                "obsidian": {"requirement": "recommended", "status": "missing", "official_verified": False},
                "community_plugins": {"requirement": "optional", "status": "not_selected", "official_verified": False},
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            probe_path = root / "probe.json"
            probe_path.write_text(json.dumps(readiness), encoding="utf-8")
            planned = self.run_cli("tool-plan", "--from-probe", str(probe_path), "--json")
            self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
            tool_plan = json.loads(planned.stdout)
            self.assertFalse(tool_plan["plan"]["creates_authorization"])

            target = root / "Vault"
            target.mkdir()
            state = root / "state"
            run_id = "run-tool-authorize"
            self.prepare_tool_readiness(root, state, run_id)
            scaffolded = self.run_cli(
                "plan", "--target", str(target), "--run-id", run_id,
                "--journey", "create", "--stage", "scaffold",
                "--state-dir", str(state), "--json"
            )
            self.assertEqual(scaffolded.returncode, 0, scaffolded.stdout + scaffolded.stderr)
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps(json.loads(scaffolded.stdout)["plan"]), encoding="utf-8")
            operation_id = json.loads(scaffolded.stdout)["plan"]["operations"][0]["operation_id"]
            authorized = self.run_cli(
                "authorize", "--plan", str(plan_path), "--approve", operation_id, "--json"
            )
            self.assertEqual(authorized.returncode, 0, authorized.stdout + authorized.stderr)
            self.assertEqual(json.loads(authorized.stdout)["authorization"]["approved_operation_ids"], [operation_id])

    def test_tool_choice_and_evidence_persist_idempotently_when_state_dir_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state"
            run_id = "run-tool-state"
            choice = {
                "schema_version": 1,
                "tool_id": "obsidian",
                "choice": "deferred_by_user",
                "impact_disclosure_digest": "a" * 64,
                "confirmed_at": "2026-08-07T12:00:00+08:00",
                "idempotency_key": "choice-obsidian-defer",
                "input_digest": "b" * 64,
            }
            first = self.run_cli(
                "tool-choice-update", "--run-id", run_id, "--input", "-",
                "--state-dir", str(state), "--json", input_text=json.dumps(choice),
            )
            second = self.run_cli(
                "tool-choice-update", "--run-id", run_id, "--input", "-",
                "--state-dir", str(state), "--json", input_text=json.dumps(choice),
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(len(json.loads(second.stdout)["events"]), 1)

            evidence = {
                "schema_version": 1,
                "tool_id": "obsidian",
                "observation_type": "ui_opened",
                "observed_at": "2026-08-07T12:01:00+08:00",
                "evidence_source": "user_confirmation",
                "external_action_receipt_ref": "receipt-open-obsidian",
            }
            for _ in range(2):
                recorded = self.run_cli(
                    "tool-evidence-update", "--run-id", run_id, "--input", "-",
                    "--state-dir", str(state), "--json", input_text=json.dumps(evidence),
                )
                self.assertEqual(recorded.returncode, 0, recorded.stdout + recorded.stderr)
            stored = json.loads((state / run_id / "tool-evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["observations"], [evidence])
            self.assertEqual((state / run_id / "tool-choices.json").stat().st_mode & 0o777, 0o600)

    def test_create_scaffold_requires_persisted_verified_tool_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            state = root / "state"
            target.mkdir()
            run_id = "run-tool-gate"

            unprepared = self.run_cli(
                "plan", "--target", str(target), "--run-id", run_id,
                "--journey", "create", "--stage", "scaffold",
                "--state-dir", str(state), "--json",
            )
            self.assertEqual(unprepared.returncode, 2, unprepared.stdout + unprepared.stderr)
            self.assertEqual(json.loads(unprepared.stdout)["command_outcome"], "action_required")

            readiness = self.bootstrap.example_missing_recommended_readiness()
            tool_plan_path = root / "tool-plan.json"
            tool_plan_path.write_text(
                json.dumps(self.bootstrap.build_tool_plan(readiness)), encoding="utf-8"
            )
            choices_path = root / "choices.json"
            choices_path.write_text(json.dumps({
                "workbuddy": "deferred_by_user",
                "obsidian": "deferred_by_user",
            }), encoding="utf-8")
            verified = self.run_cli(
                "tool-verify", "--plan", str(tool_plan_path), "--choices", str(choices_path),
                "--run-id", run_id, "--state-dir", str(state), "--json",
            )
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

            prepared = self.run_cli(
                "plan", "--target", str(target), "--run-id", run_id,
                "--journey", "create", "--stage", "scaffold",
                "--state-dir", str(state), "--json",
            )
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            plan = json.loads(prepared.stdout)["plan"]
            self.assertRegex(plan["tool_readiness_receipt_digest"], r"^[0-9a-f]{64}$")

            plan_path = root / "scaffold-plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            authorized = self.run_cli(
                "authorize", "--plan", str(plan_path),
                *sum(((["--approve", item["operation_id"]] for item in plan["operations"])), []),
                "--json",
            )
            self.assertEqual(authorized.returncode, 0, authorized.stdout + authorized.stderr)
            authorization_path = root / "scaffold-authorization.json"
            authorization_path.write_text(authorized.stdout, encoding="utf-8")
            receipt_path = state / run_id / "tool-readiness-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["choices"]["obsidian"] = "tampered"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            receipt_path.chmod(0o600)
            rejected_apply = self.run_cli(
                "apply", "--plan", str(plan_path),
                "--authorization", str(authorization_path),
                "--state-dir", str(state), "--json",
            )
            self.assertEqual(
                rejected_apply.returncode, 5,
                rejected_apply.stdout + rejected_apply.stderr)
            self.assertEqual(list(target.iterdir()), [])

    def test_resume_keeps_partial_scaffold_action_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            state = root / "state"
            target.mkdir()
            run_id = "run-partial-resume"
            self.prepare_tool_readiness(root, state, run_id)

            planned = self.run_cli(
                "plan", "--target", str(target), "--run-id", run_id,
                "--journey", "create", "--stage", "scaffold",
                "--state-dir", str(state), "--json",
            )
            self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
            plan = json.loads(planned.stdout)["plan"]
            authorization = self.bootstrap.authorize_plan(
                plan, [item["operation_id"] for item in plan["operations"]])
            partial = self.bootstrap.apply_scaffold(plan, authorization, fail_after=1)
            self.assertEqual(partial["command_outcome"], "partial")

            receipt_probe = self.bootstrap.VERIFY.probe_target(target)
            self.bootstrap.VERIFY.write_private_json(
                state / run_id, "scaffold-receipt.json", {
                    "schema_version": 1,
                    "run_id": run_id,
                    "target": str(target),
                    "requested_target": str(target),
                    "target_identity_digest": receipt_probe["identity_digest"],
                    "starter_manifest_digest": plan["starter_manifest_digest"],
                    "tool_readiness_receipt_digest": plan["tool_readiness_receipt_digest"],
                    "apply_outcome": partial["command_outcome"],
                    "created_files": partial["created_files"],
                }, target)

            resumed = self.run_cli(
                "resume", "--run-id", run_id, "--state-dir", str(state), "--json")
            self.assertEqual(resumed.returncode, 2, resumed.stdout + resumed.stderr)
            result = json.loads(resumed.stdout)
            self.assertEqual(result["lifecycle_state"], "planned")
            self.assertEqual(result["scaffold_outcome"], "partial")

    def test_authorize_rejects_noncanonical_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plan_path = Path(temp) / "plan.json"
            plan_path.write_text(json.dumps({
                "subject_kind": "vault",
                "subject_identity_digest": "a" * 64,
                "operations": [{"operation_id": "copy:x", "kind": "copy-starter"}],
                "plan_digest": "b" * 64,
            }), encoding="utf-8")
            result = self.run_cli(
                "authorize", "--plan", str(plan_path), "--approve", "copy:x", "--json")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["command_outcome"], "failed")

    def test_verify_rejects_ordinary_directory_and_reports_starter_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ordinary = root / "ordinary"
            ordinary.mkdir()
            (ordinary / "unrelated.md").write_text("不是 TwinMind Vault", encoding="utf-8")
            rejected = self.run_cli("verify", "--target", str(ordinary), "--json")
            self.assertEqual(rejected.returncode, 2, rejected.stdout + rejected.stderr)
            result = json.loads(rejected.stdout)
            self.contracts.validate_contract("bootstrap-result", result)
            self.assertEqual(result["lifecycle_state"], "new")
            self.assertTrue(any(item.startswith("starter_missing:") for item in result["evidence"]))

            projection = root / "projection"
            shutil.copytree(self.bootstrap.ASSET_ROOT, projection)
            (projection / "README.md").write_text("已漂移", encoding="utf-8")
            managed = projection / "AI协作协议.md"
            managed.write_text(
                managed.read_text(encoding="utf-8").replace(
                    "<!-- TWINMIND_MANAGED_END:ai-collaboration-policy -->", ""),
                encoding="utf-8")
            drifted = self.run_cli("verify", "--target", str(projection), "--json")
            self.assertEqual(drifted.returncode, 2, drifted.stdout + drifted.stderr)
            evidence = json.loads(drifted.stdout)["evidence"]
            self.assertIn("static_drift:README.md", evidence)
            self.assertIn("managed_block_invalid:AI协作协议.md", evidence)

    def test_verify_rejects_vault_paths_through_symlinked_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            shutil.copytree(self.bootstrap.ASSET_ROOT, target)
            external = root / "external-output"
            (target / "40_输出成果").rename(external)
            (target / "40_输出成果").symlink_to(external, target_is_directory=True)

            issues, _ = self.bootstrap.verify_starter_projection(target)
            self.assertTrue(
                any(item.startswith("starter_unsafe:40_输出成果/") for item in issues),
                issues,
            )
            evidence = external / "首个闭环.md"
            evidence.write_text("外部文件", encoding="utf-8")
            with self.assertRaises(self.bootstrap.VERIFY.SafetyError):
                self.bootstrap.validate_activation_evidence(
                    target, ["40_输出成果/首个闭环.md"])

    @unittest.skipUnless(shutil.which("git"), "需要本机 Git")
    def test_verify_rejects_baseline_tree_that_does_not_match_starter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Vault"
            shutil.copytree(self.bootstrap.ASSET_ROOT, target)
            readme = target / "README.md"
            canonical = readme.read_bytes()
            readme.write_text("错误 baseline", encoding="utf-8")
            subprocess.run([shutil.which("git"), "init", "-q"], cwd=target, check=True)
            subprocess.run([shutil.which("git"), "add", "."], cwd=target, check=True)
            subprocess.run([
                shutil.which("git"), "-c", "user.name=TwinMind Test",
                "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "bad baseline",
            ], cwd=target, check=True)
            readme.write_bytes(canonical)

            rejected = self.run_cli("verify", "--target", str(target), "--json")
            self.assertEqual(rejected.returncode, 2, rejected.stdout + rejected.stderr)
            result = json.loads(rejected.stdout)
            self.contracts.validate_contract("bootstrap-result", result)
            self.assertIn("baseline_static_drift:README.md", result["evidence"])
            self.assertFalse(result["git"]["baseline_tree_verified"])

    def test_personalize_apply_rejects_target_drift_after_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            target.mkdir()
            (target / "README.md").write_text("base", encoding="utf-8")
            answers = {"primary_scenario": "处理重复评审"}
            answers_path = root / "answers.json"
            answers_path.write_text(json.dumps(answers), encoding="utf-8")
            planned = self.run_cli(
                "plan", "--target", str(target), "--run-id", "run-drift",
                "--journey", "create", "--stage", "personalize",
                "--input", str(answers_path), "--json",
            )
            self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
            plan = json.loads(planned.stdout)["plan"]

            missing_date_plan = dict(plan)
            missing_date_plan.pop("profile_date")
            missing_date_plan["plan_digest"] = self.bootstrap._plan_digest(missing_date_plan)
            missing_date_path = root / "missing-date-plan.json"
            missing_date_path.write_text(json.dumps(missing_date_plan), encoding="utf-8")
            missing_date_authorization = self.bootstrap.authorize_plan(
                missing_date_plan,
                [item["operation_id"] for item in missing_date_plan["operations"]],
            )
            missing_date_auth_path = root / "missing-date-authorization.json"
            missing_date_auth_path.write_text(
                json.dumps(missing_date_authorization), encoding="utf-8")
            missing_date_apply = self.run_cli(
                "apply", "--plan", str(missing_date_path),
                "--authorization", str(missing_date_auth_path),
                "--input", str(answers_path), "--json",
            )
            self.assertEqual(
                missing_date_apply.returncode, 5,
                missing_date_apply.stdout + missing_date_apply.stderr)

            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            authorized = self.run_cli(
                "authorize", "--plan", str(plan_path),
                *sum((["--approve", item["operation_id"]] for item in plan["operations"]), []),
                "--json",
            )
            auth_path = root / "authorization.json"
            auth_path.write_text(authorized.stdout, encoding="utf-8")
            (target / "user-change.md").write_text("drift", encoding="utf-8")
            applied = self.run_cli(
                "apply", "--plan", str(plan_path), "--authorization", str(auth_path),
                "--input", str(answers_path), "--json",
            )
            self.assertEqual(applied.returncode, 5, applied.stdout + applied.stderr)
            self.assertEqual(json.loads(applied.stdout)["command_outcome"], "plan_stale")
            self.assertFalse((target / "10_当前工作台/01_个人运行地图.md").exists())

    def test_recover_plan_replaces_scaffold_operation_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            target.mkdir()
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({
                "target": str(target),
                "created_files": [{
                    "path": "README.md", "sha256": "a" * 64,
                    "ownership": "static", "operation_id": "copy:README.md",
                }],
            }), encoding="utf-8")
            result = self.run_cli(
                "recover-plan", "--run-id", "run-recover", "--receipt", str(receipt), "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            operation = json.loads(result.stdout)["plan"]["operations"][0]
            self.assertEqual(operation["operation_id"], "recover:README.md")
            self.assertEqual(operation["kind"], "recover-file")

    def test_resume_recovers_tool_prepare_state_without_creating_unknown_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state"
            choice = {
                "schema_version": 1, "tool_id": "workbuddy", "choice": "deferred_by_user",
                "impact_disclosure_digest": "a" * 64,
                "confirmed_at": "2026-08-07T12:00:00+08:00",
                "idempotency_key": "workbuddy-defer", "input_digest": "b" * 64,
            }
            updated = self.run_cli(
                "tool-choice-update", "--run-id", "run-tool-resume", "--input", "-",
                "--state-dir", str(state), "--json", input_text=json.dumps(choice),
            )
            self.assertEqual(updated.returncode, 0, updated.stdout + updated.stderr)
            resumed = self.run_cli(
                "resume", "--run-id", "run-tool-resume", "--state-dir", str(state), "--json")
            self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
            payload = json.loads(resumed.stdout)
            self.assertEqual(payload["phase"], "tool_prepare")
            self.assertEqual(payload["tool_choices"]["workbuddy"]["choice"], "deferred_by_user")

            unknown = self.run_cli(
                "resume", "--run-id", "unknown-run", "--state-dir", str(state), "--json")
            self.assertEqual(unknown.returncode, 2, unknown.stdout + unknown.stderr)
            self.assertFalse((state / "unknown-run").exists())

    def test_confidential_runtime_state_fails_closed_without_verified_storage_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            state = root / "state"
            target.mkdir()
            secret = "绝不落盘的 confidential 值"
            answer = {
                "schema_version": 1, "field_id": "primary_scenario", "value": secret,
                "sensitivity": "confidential", "persistence": "runtime_state",
                "status": "confirmed", "evidence_type": "user_statement",
                "confirmed_at": "2026-08-07T12:00:00+08:00",
            }
            result = self.run_cli(
                "interview-update", "--run-id", "run-confidential", "--input", "-",
                "--target", str(target), "--state-dir", str(state), "--json",
                input_text=json.dumps(answer),
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["command_outcome"], "action_required")
            self.assertNotIn(secret, result.stdout + result.stderr)
            interview_path = state / "run-confidential" / "interview.json"
            self.assertFalse(interview_path.exists())

    def test_partial_missing_target_recover_removes_private_staging_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            plan = self.bootstrap.build_scaffold_plan(
                target, self.bootstrap.example_verified_tool_readiness_receipt("run-partial"))
            auth = self.bootstrap.authorize_plan(
                plan, [item["operation_id"] for item in plan["operations"]])
            partial = self.bootstrap.apply_scaffold(plan, auth, fail_after=2)
            staging = Path(partial["staging_path"])
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({
                "target": str(staging), "requested_target": str(target),
                "created_files": partial["created_files"],
            }), encoding="utf-8")
            planned = self.run_cli(
                "recover-plan", "--run-id", "run-partial", "--receipt", str(receipt), "--json")
            self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
            recover_plan = json.loads(planned.stdout)["plan"]
            self.assertTrue(recover_plan["remove_root_if_empty"])
            plan_path = root / "recover-plan.json"
            plan_path.write_text(json.dumps(recover_plan), encoding="utf-8")
            authorized = self.run_cli(
                "authorize", "--plan", str(plan_path),
                *sum((["--approve", item["operation_id"]] for item in recover_plan["operations"]), []),
                "--json",
            )
            auth_path = root / "recover-auth.json"
            auth_path.write_text(authorized.stdout, encoding="utf-8")
            recovered = self.run_cli(
                "recover", "--plan", str(plan_path), "--authorization", str(auth_path), "--json")
            self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
            self.assertTrue(json.loads(recovered.stdout)["removed_staging_root"])
            self.assertFalse(staging.exists())

    @unittest.skipUnless(shutil.which("git"), "需要本机 Git")
    def test_create_interview_personalize_git_verify_resume_and_cleanup_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Vault"
            state = root / "state"
            target.mkdir()
            run_id = "run-cli-smoke"
            self.prepare_tool_readiness(root, state, run_id)

            scaffolded = self.run_cli(
                "plan", "--target", str(target), "--run-id", run_id,
                "--journey", "create", "--stage", "scaffold",
                "--state-dir", str(state), "--json",
            )
            self.assertEqual(scaffolded.returncode, 0, scaffolded.stdout + scaffolded.stderr)
            scaffold_plan = json.loads(scaffolded.stdout)["plan"]
            self.contracts.validate_contract("bootstrap-plan", scaffold_plan)
            scaffold_plan_path = root / "scaffold-plan.json"
            scaffold_plan_path.write_text(json.dumps(scaffold_plan), encoding="utf-8")
            scaffold_auth = self.run_cli(
                "authorize", "--plan", str(scaffold_plan_path),
                *sum((["--approve", item["operation_id"]] for item in scaffold_plan["operations"]), []),
                "--json",
            )
            scaffold_auth_path = root / "scaffold-auth.json"
            scaffold_auth_path.write_text(scaffold_auth.stdout, encoding="utf-8")
            applied = self.run_cli(
                "apply", "--plan", str(scaffold_plan_path), "--authorization", str(scaffold_auth_path),
                "--state-dir", str(state), "--json",
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            answer = {
                "schema_version": 1, "field_id": "primary_scenario", "value": "处理重复评审",
                "sensitivity": "normal", "persistence": "runtime_state", "status": "confirmed",
                "evidence_type": "user_statement", "confirmed_at": "2026-08-07T12:00:00+08:00",
            }
            updated = self.run_cli(
                "interview-update", "--run-id", run_id, "--input", "-", "--target", str(target),
                "--state-dir", str(state), "--json", input_text=json.dumps(answer),
            )
            self.assertEqual(updated.returncode, 0, updated.stdout + updated.stderr)
            self.assertNotIn(answer["value"], updated.stdout)

            personalized = self.run_cli(
                "plan", "--run-id", run_id, "--journey", "create", "--stage", "personalize",
                "--state-dir", str(state), "--json",
            )
            self.assertEqual(personalized.returncode, 0, personalized.stdout + personalized.stderr)
            personalize_plan = json.loads(personalized.stdout)["plan"]
            self.contracts.validate_contract("bootstrap-plan", personalize_plan)
            personalize_plan_path = root / "personalize-plan.json"
            personalize_plan_path.write_text(json.dumps(personalize_plan), encoding="utf-8")
            personalize_auth = self.run_cli(
                "authorize", "--plan", str(personalize_plan_path),
                *sum((["--approve", item["operation_id"]] for item in personalize_plan["operations"]), []),
                "--json",
            )
            personalize_auth_path = root / "personalize-auth.json"
            personalize_auth_path.write_text(personalize_auth.stdout, encoding="utf-8")
            personalized_apply = self.run_cli(
                "apply", "--plan", str(personalize_plan_path), "--authorization", str(personalize_auth_path),
                "--state-dir", str(state), "--json",
            )
            self.assertEqual(personalized_apply.returncode, 0, personalized_apply.stdout + personalized_apply.stderr)

            git_planned = self.run_cli(
                "plan", "--target", str(target), "--run-id", run_id, "--journey", "create",
                "--stage", "environment", "--git-executable", shutil.which("git"), "--json",
            )
            self.assertEqual(git_planned.returncode, 0, git_planned.stdout + git_planned.stderr)
            git_plan = json.loads(git_planned.stdout)["plan"]
            self.contracts.validate_contract("bootstrap-plan", git_plan)
            git_plan_path = root / "git-plan.json"
            git_plan_path.write_text(json.dumps(git_plan), encoding="utf-8")
            git_auth = self.run_cli(
                "authorize", "--plan", str(git_plan_path),
                *sum((["--approve", item["operation_id"]] for item in git_plan["operations"]), []),
                "--json",
            )
            git_auth_path = root / "git-auth.json"
            git_auth_path.write_text(git_auth.stdout, encoding="utf-8")
            identity_path = root / "identity.json"
            identity_path.write_text(json.dumps({"name": "TwinMind User", "email": "twinmind@example.invalid"}), encoding="utf-8")
            git_applied = self.run_cli(
                "apply", "--plan", str(git_plan_path), "--authorization", str(git_auth_path),
                "--input", str(identity_path), "--state-dir", str(state), "--json",
            )
            self.assertEqual(git_applied.returncode, 0, git_applied.stdout + git_applied.stderr)
            self.assertEqual(json.loads(git_applied.stdout)["lifecycle_state"], "initialized")

            verified = self.run_cli(
                "verify", "--target", str(target), "--run-id", run_id,
                "--journey", "create", "--state-dir", str(state), "--json")
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            verified_result = json.loads(verified.stdout)
            self.contracts.validate_contract("bootstrap-result", verified_result)
            self.assertEqual(verified_result["lifecycle_state"], "initialized")

            activation_path = target / "40_输出成果" / "首个闭环.md"
            activation_path.write_text("已完成首个真实闭环", encoding="utf-8")
            path_only = self.run_cli(
                "verify", "--target", str(target), "--run-id", run_id,
                "--journey", "create", "--activation-evidence", "40_输出成果/首个闭环.md",
                "--state-dir", str(state), "--json")
            self.assertEqual(path_only.returncode, 0, path_only.stdout + path_only.stderr)
            self.assertEqual(json.loads(path_only.stdout)["lifecycle_state"], "initialized")
            activated = self.run_cli(
                "verify", "--target", str(target), "--run-id", run_id,
                "--journey", "create", "--activation-evidence", "40_输出成果/首个闭环.md",
                "--activation-confirmation-source", "interactive_user_confirmation",
                "--activation-checklist-complete", "--state-dir", str(state), "--json")
            self.assertEqual(activated.returncode, 0, activated.stdout + activated.stderr)
            self.assertEqual(json.loads(activated.stdout)["lifecycle_state"], "activated")
            resumed = self.run_cli("resume", "--run-id", run_id, "--state-dir", str(state), "--json")
            self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
            self.assertNotIn(answer["value"], resumed.stdout)
            self.assertEqual(json.loads(resumed.stdout)["lifecycle_state"], "activated")
            for receipt_name in (
                    "tool-readiness-receipt.json", "scaffold-receipt.json",
                    "personalize-receipt.json", "environment-receipt.json",
                    "verify-receipt.json", "final-result.json"):
                self.assertTrue((state / run_id / receipt_name).is_file(), receipt_name)

            readme = target / "README.md"
            canonical_readme = readme.read_bytes()
            readme.write_text("漂移", encoding="utf-8")
            stale_resume = self.run_cli(
                "resume", "--run-id", run_id, "--state-dir", str(state), "--json")
            self.assertEqual(stale_resume.returncode, 5, stale_resume.stdout + stale_resume.stderr)
            readme.write_bytes(canonical_readme)

            activation_path.unlink()
            stale_activation = self.run_cli(
                "resume", "--run-id", run_id, "--state-dir", str(state), "--json")
            self.assertEqual(
                stale_activation.returncode, 5,
                stale_activation.stdout + stale_activation.stderr)
            self.assertIn("verify 证据已漂移", json.loads(stale_activation.stdout)["reason"])
            activation_path.write_text("已完成首个真实闭环", encoding="utf-8")

            cleanup_planned = self.run_cli(
                "cleanup-plan", "--run-id", run_id, "--scope", "interview",
                "--state-dir", str(state), "--json",
            )
            self.assertEqual(cleanup_planned.returncode, 0, cleanup_planned.stdout + cleanup_planned.stderr)
            cleanup_plan = json.loads(cleanup_planned.stdout)["plan"]
            self.contracts.validate_contract("bootstrap-plan", cleanup_plan)
            cleanup_plan_path = root / "cleanup-plan.json"
            cleanup_plan_path.write_text(json.dumps(cleanup_plan), encoding="utf-8")
            cleanup_auth = self.run_cli(
                "authorize", "--plan", str(cleanup_plan_path),
                *sum((["--approve", item["operation_id"]] for item in cleanup_plan["operations"]), []),
                "--json",
            )
            cleanup_auth_path = root / "cleanup-auth.json"
            cleanup_auth_path.write_text(cleanup_auth.stdout, encoding="utf-8")
            cleaned = self.run_cli(
                "cleanup", "--plan", str(cleanup_plan_path), "--authorization", str(cleanup_auth_path), "--json",
            )
            self.assertEqual(cleaned.returncode, 0, cleaned.stdout + cleaned.stderr)


if __name__ == "__main__":
    unittest.main()
