#!/usr/bin/env python3
"""校验 bootstrap-second-brain 的静态 eval 合同；模型行为由 skill-up 执行。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EVAL_ROOT = Path(__file__).resolve().parent
SUITES = ("trigger", "behavior", "safety", "claim")


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


def run_suite(name: str) -> dict:
    cases = json.loads((EVAL_ROOT / "cases" / f"{name}-cases.json").read_text(encoding="utf-8"))["cases"]
    if not cases:
        return {"status": "failed", "cases": 0, "reason": "empty-suite"}
    validated = [validate_case(name, case) for case in cases]
    return {"status": "validated", "cases": len(cases), "validated_cases": validated,
            "evidence_level": "static-eval-contract-only",
            "behavior_execution": "not-performed-use-skill-up"}


def run_all() -> dict:
    suites = {name: run_suite(name) for name in SUITES}
    return {"status": "validated" if all(item["status"] == "validated" for item in suites.values()) else "failed",
            "suites": suites,
            "claim_limit": "仅证明静态用例合同有效；模型行为由 skill-up forward eval 证明；用户价值需 field outcome"}


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
