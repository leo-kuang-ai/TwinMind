#!/usr/bin/env python3
"""TwinMind v0.1 离线合同验证器与跨字段不变量。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = SKILL_ROOT / "schemas"
SUPPORTED_KEYWORDS = {
    "$schema", "type", "required", "properties", "items", "enum", "const",
    "pattern", "minLength", "maxLength", "minimum", "maximum", "minItems",
    "maxItems", "additionalProperties", "oneOf", "description", "title",
}
SCHEMA_VERSION = 1
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
OID_PATTERN = re.compile(r"^[0-9a-f]{40}$")
TIMESTAMP = "2026-08-07T12:00:00+08:00"


class ContractError(ValueError):
    pass


def _fail(message: str, path: str = "$") -> None:
    raise ContractError(f"{path}: {message}")


def validate_schema_definition(schema: Any, path: str = "$") -> None:
    if not isinstance(schema, dict):
        _fail("schema 节点必须是 object", path)
    unknown = set(schema) - SUPPORTED_KEYWORDS
    if unknown:
        _fail(f"含未支持 keyword：{sorted(unknown)}", path)
    if "$ref" in schema:
        _fail("禁止 $ref 和联网解析", path)
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        _fail("properties 必须是 object", path)
    for name, child in properties.items():
        validate_schema_definition(child, f"{path}.properties.{name}")
    if "items" in schema:
        validate_schema_definition(schema["items"], f"{path}.items")
    one_of = schema.get("oneOf", [])
    if not isinstance(one_of, list):
        _fail("oneOf 必须是 array", path)
    for index, child in enumerate(one_of):
        validate_schema_definition(child, f"{path}.oneOf[{index}]")


def _is_type(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def validate_instance(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    if "oneOf" in schema:
        matches = 0
        for candidate in schema["oneOf"]:
            try:
                validate_instance(value, candidate, path)
            except ContractError:
                continue
            matches += 1
        if matches != 1:
            _fail(f"oneOf 必须恰好匹配一个分支，实际 {matches}", path)
    expected_type = schema.get("type")
    if expected_type and not _is_type(value, expected_type):
        _fail(f"类型必须为 {expected_type}", path)
    if "const" in schema and value != schema["const"]:
        _fail(f"必须等于 {schema['const']!r}", path)
    if "enum" in schema and value not in schema["enum"]:
        _fail(f"不在允许枚举中：{value!r}", path)
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            _fail("字符串过短", path)
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            _fail("字符串过长", path)
        if "pattern" in schema and not re.search(schema["pattern"], value):
            _fail("字符串不匹配 pattern", path)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            _fail("数值低于 minimum", path)
        if "maximum" in schema and value > schema["maximum"]:
            _fail("数值高于 maximum", path)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            _fail("数组元素不足", path)
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            _fail("数组元素过多", path)
        if "items" in schema:
            for index, item in enumerate(value):
                validate_instance(item, schema["items"], f"{path}[{index}]")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [name for name in required if name not in value]
        if missing:
            _fail(f"缺少 required 字段：{missing}", path)
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = set(value) - set(properties)
            if extras:
                _fail(f"含未知字段：{sorted(extras)}", path)
        for name, child in properties.items():
            if name in value:
                validate_instance(value[name], child, f"{path}.{name}")


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_ROOT / f"{name}.schema.json"
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"无法加载 schema {name}：{error}") from error
    validate_schema_definition(schema)
    return schema


def validate_contract(name: str, payload: dict[str, Any]) -> None:
    validate_instance(payload, load_schema(name))
    if payload.get("schema_version") != SCHEMA_VERSION and name != "inventory-policy":
        _fail("未知 schema_version，必须 action_required")
    invariants = {
        "bootstrap-state": validate_state,
        "bootstrap-plan": validate_plan,
        "interview-answer": validate_interview_answer,
        "tool-readiness": validate_tool_readiness,
        "tool-choice": validate_tool_choice,
        "tool-evidence": validate_tool_evidence,
        "release-attestation": validate_release_attestation,
        "inventory-policy": validate_inventory_policy,
        "bootstrap-result": validate_result,
    }
    if name in invariants:
        invariants[name](payload)


def _relative_evidence_path(raw: str) -> bool:
    if not raw or "\\" in raw or any(ord(char) < 32 for char in raw):
        return False
    path = PurePosixPath(raw)
    return not path.is_absolute() and ".." not in path.parts and path.as_posix() == raw


def validate_state(state: dict[str, Any]) -> None:
    lifecycle = state["lifecycle_state"]
    if lifecycle in {"action_required", "partial", "failed", "degraded"}:
        _fail("command outcome 或 health 不得写入 lifecycle_state")
    storage = state["state_storage"]
    if not SHA256_PATTERN.fullmatch(storage["classification_evidence_digest"]):
        _fail("storage classification evidence digest 缺失")


def validate_plan(plan: dict[str, Any]) -> None:
    unsigned = dict(plan)
    declared = unsigned.pop("plan_digest")
    actual = hashlib.sha256(
        (json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    if declared != actual:
        _fail("plan_digest 与 canonical plan 内容不匹配")
    kinds = {operation["kind"] for operation in plan["operations"]}
    if plan["subject_kind"] == "host_tool":
        if "target_identity_digest" in plan:
            _fail("host_tool plan 不得绑定 Vault target")
        if not kinds <= {"open-source", "open-app"}:
            _fail("host_tool plan 只允许 open-source/open-app")
    elif "target_identity_digest" not in plan and plan["subject_kind"] == "vault":
        _fail("vault plan 必须绑定 target identity")


def validate_authorization_binding(plan: dict[str, Any], authorization: dict[str, Any]) -> None:
    validate_contract("bootstrap-plan", plan)
    validate_contract("bootstrap-authorization", authorization)
    for field in ("plan_digest", "subject_kind", "subject_identity_digest"):
        if authorization[field] != plan[field]:
            _fail(f"authorization {field} 与 plan 不匹配")
    allowed = {operation["operation_id"] for operation in plan["operations"]}
    if not set(authorization["approved_operation_ids"]) <= allowed:
        _fail("authorization 含 plan 外 operation")


def validate_plan_state_binding(plan: dict[str, Any], state: dict[str, Any]) -> None:
    binding = plan.get("state_binding")
    if not binding:
        return
    storage = state["state_storage"]
    for plan_key, state_key in (
        ("state_root_identity_digest", "identity_digest"),
        ("storage_domain", "storage_domain"),
        ("encryption_receipt_digest", "encryption_receipt_digest"),
    ):
        if plan_key in binding and binding[plan_key] != storage.get(state_key):
            _fail(f"plan state binding 漂移：{plan_key}")


def validate_plan_inventory_binding(plan: dict[str, Any], policy: dict[str, Any]) -> None:
    validate_inventory_policy(policy)
    digest = _load_sync_module().validate_inventory_policy(policy)
    if plan.get("inventory_policy_digest") != digest:
        _fail("plan inventory policy digest 不匹配")


def record_idempotent_event(events: list[dict[str, Any]], event: dict[str, Any]) -> list[dict[str, Any]]:
    validate_contract("bootstrap-event", event)
    key = event.get("idempotency_key")
    if not key:
        return [*events, event]
    for existing in events:
        if existing.get("idempotency_key") != key:
            continue
        if existing.get("input_digest") != event.get("input_digest"):
            _fail("同一 idempotency_key 不得绑定不同输入")
        return list(events)
    return [*events, event]


def validate_interview_answer(answer: dict[str, Any]) -> None:
    if answer["sensitivity"] == "restricted" and "value" in answer:
        _fail("restricted answer 不得包含 value")
    if answer["status"] in {"declined", "withdrawn"} and "value" in answer:
        _fail("declined/withdrawn 不得保留 value")


def validate_interview_storage(answer: dict[str, Any], storage: dict[str, Any]) -> None:
    validate_contract("interview-answer", answer)
    if answer["sensitivity"] != "confidential" or answer["persistence"] != "runtime_state":
        return
    if storage["storage_domain"] == "local_fixed":
        return
    if storage.get("encryption_status") != "verified" or not SHA256_PATTERN.fullmatch(
        str(storage.get("encryption_receipt_digest", ""))
    ):
        _fail("非 local_fixed 的 confidential runtime_state 需要已验证加密收据")


def validate_result(result: dict[str, Any]) -> None:
    inventory = result.get("inventory")
    if inventory and inventory["inventory_status"] == "incomplete":
        if result["command_outcome"] != "action_required":
            _fail("inventory incomplete 必须使总体结果为 action_required")
    if result["lifecycle_state"] in {"initialized", "activated"}:
        git = result.get("git")
        if not git or not OID_PATTERN.fullmatch(git.get("baseline_commit_oid", "")):
            _fail("initialized 需要 baseline commit OID")
        if not git.get("baseline_tree_verified") or not SHA256_PATTERN.fullmatch(
            git.get("repository_boundary_digest", "")
        ):
            _fail("initialized 需要仓库边界和 baseline tree 证据")
    if result["lifecycle_state"] == "activated":
        activation = result.get("activation")
        if not activation or not activation.get("checklist_complete"):
            _fail("activated 需要完整闭环检查表")
        if not activation.get("user_confirmation_source"):
            _fail("activated 需要 user_confirmation_source")
        paths = activation.get("evidence_paths", [])
        if not paths or not all(_relative_evidence_path(path) for path in paths):
            _fail("activated 证据必须是 Vault 相对路径")


def validate_tool_readiness(readiness: dict[str, Any]) -> None:
    tools = readiness["tools"]
    expected = {
        "python": "runtime-required", "git": "product-required",
        "workbuddy": "recommended", "obsidian": "recommended",
        "community_plugins": "optional",
    }
    for tool_id, tier in expected.items():
        if tools[tool_id]["requirement"] != tier:
            _fail(f"{tool_id} requirement 不得降级")
    if readiness["path_confirmation_ready"]:
        for tool_id in ("python", "git"):
            if tools[tool_id]["status"] != "ready" or not tools[tool_id]["official_verified"]:
                _fail("Python/Git 未就绪时不得允许 path confirmation")
    for tool_id in ("workbuddy", "obsidian"):
        item = tools[tool_id]
        if item["status"] == "ready" and not item["official_verified"]:
            _fail(f"{tool_id} 未验证 official 时不得标记 ready")


def validate_tool_choice(choice: dict[str, Any]) -> None:
    forbidden = {"approved_operation_ids", "operation_approval", "ready", "official_verified"}
    if forbidden & set(choice):
        _fail("tool choice 不得携带 operation approval 或 readiness 结论")


def validate_tool_evidence(evidence: dict[str, Any]) -> None:
    weak = {"ui_opened", "downloaded", "file_exists"}
    if evidence["observation_type"] in weak and (
        evidence.get("official_verified") or evidence.get("ready")
    ):
        _fail("opened/UI/file evidence 不能单独证明 official 或 ready")


def validate_release_attestation(attestation: dict[str, Any]) -> None:
    if attestation["zip_namespace"] != "twinmind-bundle-v1":
        _fail("zip namespace 不匹配")
    if attestation["attestation_namespace"] != "twinmind-release-attestation-v1":
        _fail("attestation namespace 不匹配")
    if "signatures_verified" in attestation or "trust_root_verified" in attestation:
        _fail("schema-valid attestation 不得自称签名或信任根已验证")


def validate_inventory_policy(manifest: dict[str, Any]) -> None:
    sync = _load_sync_module()
    try:
        sync.validate_inventory_policy(manifest)
    except ValueError as error:
        raise ContractError(str(error)) from error


def validate_effective_inventory_limits(manifest: dict[str, Any], effective: dict[str, Any]) -> None:
    validate_inventory_policy(manifest)
    sync = _load_sync_module()
    try:
        sync.validate_effective_limits(manifest["policies"][0]["limits"], effective)
    except ValueError as error:
        raise ContractError(str(error)) from error


def _load_sync_module():
    module_name = "bootstrap_second_brain_sync_starter_assets"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).with_name("sync_starter_assets.py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ContractError("无法加载 inventory policy canonical validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def validate_tool_identity_manifest(manifest: dict[str, Any]) -> None:
    required_tools = {"python", "git", "ssh-keygen", "workbuddy", "obsidian"}
    tools = manifest.get("tools")
    if not isinstance(tools, list):
        _fail("tool identity manifest 缺少 tools")
    keys: set[tuple[str, str]] = set()
    present: set[str] = set()
    for item in tools:
        validate_contract("tool-identity", item)
        key = (item["tool_id"], item["platform"])
        if key in keys:
            _fail(f"重复 tool/platform：{key}")
        keys.add(key)
        present.add(item["tool_id"])
        if not re.fullmatch(r"https://[^\s]+", item["official_url"]):
            _fail("official_url 必须是精确 HTTPS URL")
        if item["kind"] == "app" and not item.get("app_identity"):
            _fail("app 工具缺少 bundle/signing identity")
        if item["kind"] == "cli" and not item.get("cli_source_types"):
            _fail("CLI 工具缺少来源类型")
    if not required_tools <= present:
        _fail(f"缺少 v0.1 tool identity：{sorted(required_tools - present)}")
    declared = manifest.get("manifest_digest")
    unsigned = dict(manifest)
    unsigned.pop("manifest_digest", None)
    actual = hashlib.sha256(
        (json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    if declared != actual:
        _fail("tool identity manifest digest 不匹配")


def example_plan(subject_kind: str = "vault") -> dict[str, Any]:
    plan = {
        "schema_version": 1, "plan_id": "plan-demo", "run_id": "run-demo",
        "subject_kind": subject_kind,
        "subject_identity_digest": "b" * 64, "generated_at": TIMESTAMP,
        "operations": [{"operation_id": "copy-starter", "kind": "copy-starter"}],
    }
    if subject_kind == "vault":
        plan["target_identity_digest"] = "c" * 64
    else:
        plan["operations"] = [{"operation_id": "open-source", "kind": "open-source"}]
    plan["plan_digest"] = hashlib.sha256(
        (json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    return plan


def example_result() -> dict[str, Any]:
    return {
        "schema_version": 1, "run_id": "run-demo", "journey": "create",
        "phase": "verify", "lifecycle_state": "planned", "run_state": "active",
        "health": "healthy", "command_outcome": "success", "evidence": [],
    }


def example_tool_readiness() -> dict[str, Any]:
    def item(requirement: str, status: str = "ready", official: bool = True) -> dict[str, Any]:
        return {"requirement": requirement, "status": status, "official_verified": official}
    return {
        "schema_version": 1, "platform": "macos", "observed_at": TIMESTAMP,
        "path_confirmation_ready": True,
        "tools": {
            "python": item("runtime-required"), "git": item("product-required"),
            "workbuddy": item("recommended", "missing", False),
            "obsidian": item("recommended", "missing", False),
            "community_plugins": item("optional", "not_selected", False),
        },
    }


def example_release_attestation() -> dict[str, Any]:
    return {
        "schema_version": 1, "package_name": "bootstrap-second-brain-v0.1.zip",
        "package_sha256": "a" * 64, "package_size": 1234,
        "starter_source_commit": "b" * 40,
        "starter_digest": "c" * 64, "allowlist_digest": "d" * 64,
        "builder_version": "0.1.0", "release_boundary": "public-github-mit",
        "zip_namespace": "twinmind-bundle-v1",
        "attestation_namespace": "twinmind-release-attestation-v1",
        "signer_fingerprint": "SHA256:owner-demo",
    }


def example_tool_identity_manifest() -> dict[str, Any]:
    tools = []
    for tool_id in ("python", "git", "ssh-keygen"):
        tools.append({
            "schema_version": 1, "tool_id": tool_id, "platform": "macos", "kind": "cli",
            "official_url": f"https://example.com/{tool_id}", "source_as_of": "2026-08-07",
            "rotation_policy": "发布者身份变化时重新取证并生成新 digest",
            "cli_source_types": ["system-signed", "package-receipt"],
        })
    for tool_id in ("workbuddy", "obsidian"):
        tools.append({
            "schema_version": 1, "tool_id": tool_id, "platform": "macos", "kind": "app",
            "official_url": f"https://example.com/{tool_id}/", "source_as_of": "2026-08-07",
            "rotation_policy": "发布者身份变化时重新取证并生成新 digest",
            "app_identity": {"bundle_id": f"example.{tool_id}", "executable_name": tool_id,
                             "team_identifier": "OWNERTEAM", "designated_requirement": "anchor trusted"},
        })
    unsigned = {"schema_version": 1, "tools": tools}
    digest = hashlib.sha256(
        (json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    return {**unsigned, "manifest_digest": digest}
