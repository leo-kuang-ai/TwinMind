from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "skills" / "bootstrap-second-brain"
SCRIPT = SKILL_ROOT / "scripts" / "contract_validation.py"
SCHEMA_ROOT = SKILL_ROOT / "schemas"
SCHEMA_NAMES = [
    "bootstrap-state",
    "bootstrap-plan",
    "bootstrap-authorization",
    "bootstrap-event",
    "interview-answer",
    "tool-identity",
    "tool-readiness",
    "tool-choice",
    "tool-evidence",
    "release-attestation",
    "inventory-policy",
    "bootstrap-result",
]


def load_contracts():
    spec = importlib.util.spec_from_file_location("contract_validation", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 contract_validation.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not SCRIPT.is_file():
            raise AssertionError("缺少 contract_validation.py")
        cls.contracts = load_contracts()

    def assert_invalid(self, contract: str, payload: dict) -> None:
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.validate_contract(contract, payload)

    def test_all_schemas_parse_and_use_only_supported_offline_subset(self) -> None:
        for name in SCHEMA_NAMES:
            with self.subTest(schema=name):
                path = SCHEMA_ROOT / f"{name}.schema.json"
                schema = json.loads(path.read_text(encoding="utf-8"))
                self.contracts.validate_schema_definition(schema)
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.validate_schema_definition({"type": "string", "format": "date-time"})
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.validate_schema_definition({"$ref": "https://example.com/schema.json"})

    def test_state_axes_are_independent_and_unknown_version_fails_closed(self) -> None:
        state = {
            "schema_version": 1,
            "run_id": "bootstrap-20260807-demo",
            "journey": "create",
            "phase": "verify",
            "lifecycle_state": "initialized",
            "run_state": "completed",
            "health": "degraded",
            "command_outcome": "degraded",
            "state_storage": {
                "identity_digest": "a" * 64,
                "storage_domain": "local_fixed",
                "classification_evidence_digest": "b" * 64,
                "encryption_status": "unavailable",
            },
        }
        self.contracts.validate_contract("bootstrap-state", state)
        invalid = copy.deepcopy(state)
        invalid["schema_version"] = 2
        self.assert_invalid("bootstrap-state", invalid)
        invalid = copy.deepcopy(state)
        invalid["lifecycle_state"] = "partial"
        self.assert_invalid("bootstrap-state", invalid)

    def test_authorization_must_bind_plan_subject_and_operations(self) -> None:
        plan = self.contracts.example_plan()
        authorization = {
            "schema_version": 1,
            "authorization_id": "auth-demo",
            "plan_digest": plan["plan_digest"],
            "subject_kind": plan["subject_kind"],
            "subject_identity_digest": plan["subject_identity_digest"],
            "approved_operation_ids": ["copy-starter"],
            "confirmed_at": "2026-08-07T12:00:00+08:00",
        }
        self.contracts.validate_authorization_binding(plan, authorization)
        authorization["plan_digest"] = "f" * 64
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.validate_authorization_binding(plan, authorization)

    def test_plan_state_and_inventory_bindings_fail_closed_on_drift(self) -> None:
        state = {
            "state_storage": {
                "identity_digest": "a" * 64,
                "storage_domain": "local_fixed",
                "encryption_status": "unavailable",
            }
        }
        plan = self.contracts.example_plan()
        plan["state_binding"] = {
            "state_root_identity_digest": "a" * 64,
            "storage_domain": "local_fixed",
        }
        self.contracts.validate_plan_state_binding(plan, state)
        plan["state_binding"]["storage_domain"] = "network"
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.validate_plan_state_binding(plan, state)

        policy = json.loads(
            (SKILL_ROOT / "manifests/inventory-policies-v1.json").read_text(encoding="utf-8")
        )
        plan = self.contracts.example_plan()
        plan["inventory_policy_digest"] = "f" * 64
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.validate_plan_inventory_binding(plan, policy)

    def test_restricted_answer_cannot_contain_value(self) -> None:
        answer = {
            "schema_version": 1,
            "field_id": "customer-secret",
            "sensitivity": "restricted",
            "persistence": "session_only",
            "status": "confirmed",
            "category": "客户数据",
            "confirmed_at": "2026-08-07T12:00:00+08:00",
        }
        self.contracts.validate_contract("interview-answer", answer)
        answer["value"] = "不得落盘"
        self.assert_invalid("interview-answer", answer)

    def test_confidential_runtime_state_requires_safe_storage(self) -> None:
        answer = {
            "schema_version": 1,
            "field_id": "private-goal",
            "sensitivity": "confidential",
            "persistence": "runtime_state",
            "status": "confirmed",
            "value": "私密目标",
            "confirmed_at": "2026-08-07T12:00:00+08:00",
        }
        unsafe_storage = {
            "identity_digest": "a" * 64,
            "storage_domain": "cloud_synced",
            "classification_evidence_digest": "b" * 64,
            "encryption_status": "unavailable",
        }
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.validate_interview_storage(answer, unsafe_storage)
        unsafe_storage["encryption_status"] = "verified"
        unsafe_storage["encryption_receipt_digest"] = "c" * 64
        self.contracts.validate_interview_storage(answer, unsafe_storage)

    def test_activated_and_initialized_claims_require_non_compensable_evidence(self) -> None:
        result = self.contracts.example_result()
        result["lifecycle_state"] = "initialized"
        self.assert_invalid("bootstrap-result", result)
        result["git"] = {
            "repository_boundary_digest": "a" * 64,
            "baseline_commit_oid": "b" * 40,
            "baseline_tree_verified": True,
        }
        self.contracts.validate_contract("bootstrap-result", result)
        result["lifecycle_state"] = "activated"
        self.assert_invalid("bootstrap-result", result)
        result["activation"] = {
            "user_confirmation_source": "interactive_confirmation",
            "checklist_complete": True,
            "evidence_paths": ["40_输出成果/首个闭环.md"],
        }
        self.contracts.validate_contract("bootstrap-result", result)
        result["activation"]["evidence_paths"] = ["/Users/demo/secret.md"]
        self.assert_invalid("bootstrap-result", result)

    def test_inventory_incomplete_cannot_report_success(self) -> None:
        result = self.contracts.example_result()
        result["inventory"] = {
            "policy_id": "personal-vault-v1",
            "policy_digest": "a" * 64,
            "inventory_status": "incomplete",
            "limit_hit": "entries",
        }
        result["command_outcome"] = "success"
        self.assert_invalid("bootstrap-result", result)
        result["command_outcome"] = "action_required"
        self.contracts.validate_contract("bootstrap-result", result)

    def test_tool_readiness_preserves_required_tiers_and_truth(self) -> None:
        readiness = self.contracts.example_tool_readiness()
        self.contracts.validate_contract("tool-readiness", readiness)
        invalid = copy.deepcopy(readiness)
        invalid["tools"]["git"]["requirement"] = "optional"
        self.assert_invalid("tool-readiness", invalid)
        invalid = copy.deepcopy(readiness)
        invalid["tools"]["git"]["status"] = "missing"
        invalid["path_confirmation_ready"] = True
        self.assert_invalid("tool-readiness", invalid)
        invalid = copy.deepcopy(readiness)
        invalid["tools"]["workbuddy"]["status"] = "ready"
        invalid["tools"]["workbuddy"]["official_verified"] = False
        self.assert_invalid("tool-readiness", invalid)

    def test_tool_choice_and_evidence_do_not_create_authority(self) -> None:
        choice = {
            "schema_version": 1,
            "tool_id": "workbuddy",
            "choice": "deferred_by_user",
            "impact_disclosure_digest": "a" * 64,
            "confirmed_at": "2026-08-07T12:00:00+08:00",
            "idempotency_key": "choice-workbuddy-1",
            "input_digest": "b" * 64,
        }
        self.contracts.validate_contract("tool-choice", choice)
        choice["approved_operation_ids"] = ["open-app"]
        self.assert_invalid("tool-choice", choice)

        evidence = {
            "schema_version": 1,
            "tool_id": "obsidian",
            "observation_type": "ui_opened",
            "observed_at": "2026-08-07T12:00:00+08:00",
            "evidence_source": "user_confirmation",
            "external_action_receipt_ref": "receipt-open-obsidian",
            "official_verified": True,
        }
        self.assert_invalid("tool-evidence", evidence)

    def test_same_tool_choice_idempotency_key_creates_one_event(self) -> None:
        event = {
            "schema_version": 1,
            "event_id": "event-1",
            "run_id": "run-demo",
            "event_name": "tool_choice_recorded",
            "phase": "tool_prepare",
            "command_outcome": "success",
            "occurred_at": "2026-08-07T12:00:00+08:00",
            "idempotency_key": "choice-workbuddy-1",
            "input_digest": "a" * 64,
        }
        events = self.contracts.record_idempotent_event([], event)
        self.assertEqual(self.contracts.record_idempotent_event(events, event), events)
        changed = dict(event)
        changed["input_digest"] = "b" * 64
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.record_idempotent_event(events, changed)

    def test_host_tool_plan_cannot_contain_vault_target_or_operation(self) -> None:
        plan = self.contracts.example_plan(subject_kind="host_tool")
        self.contracts.validate_contract("bootstrap-plan", plan)
        plan["target_identity_digest"] = "d" * 64
        self.assert_invalid("bootstrap-plan", plan)
        plan = self.contracts.example_plan(subject_kind="host_tool")
        plan["operations"][0]["kind"] = "copy-starter"
        self.assert_invalid("bootstrap-plan", plan)

    def test_release_attestation_shape_does_not_claim_signature_verification(self) -> None:
        attestation = self.contracts.example_release_attestation()
        self.contracts.validate_contract("release-attestation", attestation)
        self.assertNotIn("signatures_verified", attestation)
        attestation["zip_namespace"] = "wrong"
        self.assert_invalid("release-attestation", attestation)

    def test_inventory_policy_and_effective_limits_are_frozen(self) -> None:
        policy = json.loads(
            (SKILL_ROOT / "manifests/inventory-policies-v1.json").read_text(encoding="utf-8")
        )
        self.contracts.validate_contract("inventory-policy", policy)
        effective = dict(policy["policies"][0]["limits"])
        effective["entries"] = 60_000
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.validate_effective_inventory_limits(policy, effective)

    def test_tool_identity_manifest_rejects_duplicates_and_weak_urls(self) -> None:
        manifest = self.contracts.example_tool_identity_manifest()
        self.contracts.validate_tool_identity_manifest(manifest)
        manifest["tools"].append(copy.deepcopy(manifest["tools"][0]))
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.validate_tool_identity_manifest(manifest)
        manifest = self.contracts.example_tool_identity_manifest()
        manifest["tools"][0]["official_url"] = "http://example.com"
        with self.assertRaises(self.contracts.ContractError):
            self.contracts.validate_tool_identity_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
