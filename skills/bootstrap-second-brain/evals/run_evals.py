#!/usr/bin/env python3
"""静态校验 bootstrap-second-brain 的 eval 合同：用例结构 + SKILL.md 安全锚点 + eval.yaml 注册完整性。

本脚本不执行模型行为（forward eval 由 skill-up 执行并另行排期）；
它必须能对两类漂移变红：用例合同损坏（空断言/字段缺失/双源关键词分叉）与
Skill 安全语义被剥离（锚点词从 SKILL.md 消失）。
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


def _norm(text: str) -> str:
    """NFKC + casefold + 剥离零宽/格式字符，防同形字与零宽字符骗过子串守卫。"""
    cleaned = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return unicodedata.normalize("NFKC", cleaned).casefold()


def _contains(haystack: str, needle: str) -> bool:
    return _norm(needle) in _norm(haystack)


EVAL_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = EVAL_ROOT.parent
SUITES = ("trigger", "behavior", "safety", "claim")

SKILL_ANCHORS = {
    "trigger": ("初始化第二大脑", "adopt-existing", "resume"),
    "behavior": ("tool-probe", "一至三个", "明确暂缓", "不安装、注册、启用"),
    "safety": ("不可信数据", "创建 remote、push", "restricted"),
    "claim": ("inventory_status=incomplete", "initialized", "activated", "任务 `active`"),
}


def _string_list(case: dict, field: str) -> list[str]:
    value = case.get(field, [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{case.get('id', '<unknown>')} 的 {field} 必须是非空字符串数组")
    return value


def validate_case(name: str, case: dict) -> dict:
    if not isinstance(case, dict) or not isinstance(case.get("id"), str):
        raise ValueError(f"{name} suite 含非法 case")
    if name == "trigger":
        if not isinstance(case.get("prompt"), str) or not isinstance(case.get("should_trigger"), bool):
            raise ValueError(f"{case['id']} 缺少 prompt/should_trigger")
        assertions = ["should_trigger"]
    elif name in {"behavior", "safety"}:
        if not isinstance(case.get("prompt"), str):
            raise ValueError(f"{case['id']} 缺少 prompt")
        must = _string_list(case, "must")
        must_not = _string_list(case, "must_not")
        if set(must) & set(must_not):
            raise ValueError(f"{case['id']} 的 must 与 must_not 冲突")
        if not must:
            raise ValueError(f"{case['id']} 的 must 不得为空（空断言 case 不得进入套件）")
        if name == "safety" and not must_not:
            raise ValueError(f"{case['id']} 属 safety 套件，must_not 不得为空")
        if any(word in case["prompt"] for word in must_not):
            raise ValueError(f"{case['id']} 的 must_not 关键词出现在自身 prompt 中（拒绝句必被误判）")
        assertions = [f"must:{len(must)}", f"must_not:{len(must_not)}"]
    else:
        if not isinstance(case.get("result"), dict):
            raise ValueError(f"{case['id']} 缺少 result fixture")
        assertion_fields = {"maximum_claim", "must", "must_not_claim"} & set(case)
        if not assertion_fields:
            raise ValueError(f"{case['id']} 缺少 claim assertion")
        for field in assertion_fields & {"must", "must_not_claim"}:
            _string_list(case, field)
        assertions = sorted(assertion_fields)
    return {"id": case["id"], "assertions": assertions,
            "execution": "delegated-to-skill-up"}


def validate_yaml_registry() -> dict:
    """eval.yaml 注册的前瞻 eval 素材必须存在且结构可信；PyYAML 可用时深度校验。

    深度校验四类守卫：键名合法、块非空且含肯定词（仅 not 的空块恒真，拒绝）、
    每块至少一个判定词不在题干中（防"复述题目即通过"的回声假绿）、
    expect.must_not_contain 词不得出现在题干（防合规拒绝句被误判）。
    """
    registry_path = EVAL_ROOT / "eval.yaml"
    if not registry_path.is_file():
        return {"status": "failed", "reason": "eval.yaml 缺失"}
    text = registry_path.read_text(encoding="utf-8")
    file_entries: list[str] = []
    try:
        import yaml  # type: ignore[import-not-found]
        registry = yaml.safe_load(text) or {}
        file_entries = list((registry.get("cases") or {}).get("files") or [])
        file_entries = [e for e in file_entries if isinstance(e, str) and e.startswith("evals/cases/") and e.endswith(".yaml")]
    except ImportError:
        file_entries = re.findall(r"^\s*-\s*(evals/cases/[\w.-]+\.yaml)\s*$", text, re.M)
    if not file_entries:
        return {"status": "failed", "reason": "eval.yaml 未注册任何 case 文件"}
    missing = [entry for entry in file_entries if not (EVAL_ROOT.parent / entry).is_file()]
    if missing:
        return {"status": "failed", "reason": f"注册文件缺失: {missing}"}
    deep_check = "existence-only"
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return {"status": "validated", "files": len(file_entries), "deep_check": deep_check}
    ids: set[str] = set()
    for entry in file_entries:
        payload = yaml.safe_load((EVAL_ROOT.parent / entry).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
            return {"status": "failed", "reason": f"{entry} 缺少 id"}
        if payload["id"] in ids:
            return {"status": "failed", "reason": f"{entry} id 重复: {payload['id']}"}
        ids.add(payload["id"])
        judge = payload.get("judge")
        if not isinstance(judge, dict) or judge.get("type") != "rule_based":
            return {"status": "failed", "reason": f"{entry} judge 非 rule_based"}
        payload_input = payload.get("input")
        prompt = payload_input.get("prompt") if isinstance(payload_input, dict) else None
        if not isinstance(prompt, str) or not prompt.strip():
            return {"status": "failed", "reason": f"{entry} input.prompt 必须是非空字符串"}
        must_not_contain = payload.get("expect", {}).get("must_not_contain", [])
        if not isinstance(must_not_contain, list) or not all(isinstance(w, str) for w in must_not_contain):
            return {"status": "failed", "reason": f"{entry} expect.must_not_contain 必须是字符串列表"}
        for word in must_not_contain:
            if _contains(prompt, word):
                return {"status": "failed", "reason": f"{entry} 的 must_not_contain 词 '{word}' 出现在题干中"}
        success_blocks = judge.get("success")
        if not isinstance(success_blocks, list) or not success_blocks:
            return {"status": "failed", "reason": f"{entry} judge.success 缺失或为空"}
        for block in success_blocks:
            cond = block.get("output_contains")
            if not isinstance(cond, dict):
                return {"status": "failed", "reason": f"{entry} 判定块缺 output_contains"}
            for key, value in cond.items():
                if key not in {"any", "all", "not"}:
                    return {"status": "failed", "reason": f"{entry} judge 键非法: {key}"}
                if not isinstance(value, list) or not value or not all(isinstance(w, str) and w for w in value):
                    return {"status": "failed", "reason": f"{entry} 的 {key} 必须是非空字符串列表"}
            if not cond.get("any") and not cond.get("all"):
                return {"status": "failed", "reason": f"{entry} 存在仅含 not 的空判定块"}
            discriminators = [w for key in ("any", "all") for w in cond.get(key, []) if not _contains(prompt, w)]
            if not discriminators:
                return {"status": "failed", "reason": f"{entry} 存在判定词全部是题干子串的回声块"}
            for word in cond.get("not", []):
                if _contains(prompt, word):
                    return {"status": "failed", "reason": f"{entry} 的 not 词 '{word}' 出现在自身 prompt 中"}
    deep_check = "structure-validated"
    return {"status": "validated", "files": len(file_entries), "ids": len(ids), "deep_check": deep_check}


def _safety_cross_source_checks() -> dict:
    """safety JSON 套件与同名 yaml 的双源一致性：must_not 逐词相等、must 与 yaml 判定词有交集。"""
    try:
        return _safety_cross_source_checks_inner()
    except Exception as exc:  # 结构损坏时给出干净的 failed 而非裸 traceback
        return {"status": "failed", "reason": f"双源校验异常: {exc}"}


def _safety_cross_source_checks_inner() -> dict:
    json_cases = {
        case["id"]: case
        for case in json.loads((EVAL_ROOT / "cases" / "safety-cases.json").read_text(encoding="utf-8"))["cases"]
    }
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return {"status": "skipped", "reason": "pyyaml 不可用"}
    for entry in re.findall(r"^\s*-\s*(evals/cases/[\w.-]+\.yaml)\s*$",
                            (EVAL_ROOT / "eval.yaml").read_text(encoding="utf-8"), re.M):
        payload = yaml.safe_load((EVAL_ROOT.parent / entry).read_text(encoding="utf-8"))
        json_case = json_cases.get(payload.get("id"))
        if json_case is None:
            continue
        yaml_not = list(payload.get("expect", {}).get("must_not_contain", []))
        if set(json_case.get("must_not", [])) != set(yaml_not):
            return {"status": "failed", "reason": f"{payload['id']} 双源 must_not 不一致"}
        yaml_vocab = {w for block in payload["judge"]["success"]
                      for key in ("any", "all") for w in block["output_contains"].get(key, [])}
        if not set(json_case.get("must", [])) & yaml_vocab:
            return {"status": "failed", "reason": f"{payload['id']} JSON must 与 yaml 判定词无交集"}
    return {"status": "validated"}


def run_suite(name: str) -> dict:
    cases = json.loads((EVAL_ROOT / "cases" / f"{name}-cases.json").read_text(encoding="utf-8"))["cases"]
    if not cases:
        return {"status": "failed", "cases": 0, "reason": "empty-suite"}
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    missing_anchors = [anchor for anchor in SKILL_ANCHORS[name] if anchor not in skill]
    validated = [validate_case(name, case) for case in cases]
    if missing_anchors:
        return {"status": "failed", "cases": len(cases), "missing_anchors": missing_anchors,
                "evidence_level": "static-eval-contract-only"}
    return {"status": "validated", "cases": len(cases), "validated_cases": validated,
            "evidence_level": "static-eval-contract-only",
            "behavior_execution": "not-performed-use-skill-up"}


def run_all() -> dict:
    suites = {name: run_suite(name) for name in SUITES}
    suites["yaml-registry"] = validate_yaml_registry()
    suites["safety-cross-source"] = _safety_cross_source_checks()
    ok = all(item["status"] in {"validated", "passed", "skipped"} for item in suites.values())
    return {"status": "validated" if ok else "failed",
            "suites": suites,
            "claim_limit": "仅证明静态用例合同、SKILL.md 安全锚点与 eval.yaml 注册有效；模型行为由 skill-up forward eval 证明；用户价值需 field outcome"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=(*SUITES, "all"), default="all")
    args = parser.parse_args()
    result = run_all() if args.suite == "all" else {args.suite: run_suite(args.suite)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    passed = result["status"] == "validated" if args.suite == "all" else result[args.suite]["status"] == "validated"
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
