#!/usr/bin/env python3
"""运行 bootstrap-second-brain 的确定性 trigger/behavior/safety/claim 合同 eval。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EVAL_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = EVAL_ROOT.parent
SUITES = ("trigger", "behavior", "safety", "claim")


def run_suite(name: str) -> dict:
    cases = json.loads((EVAL_ROOT / "cases" / f"{name}-cases.json").read_text(encoding="utf-8"))["cases"]
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not cases:
        return {"status": "failed", "cases": 0, "reason": "empty-suite"}
    anchors = {
        "trigger": ("初始化第二大脑", "adopt-existing", "resume"),
        "behavior": ("tool-probe", "一至三个", "明确暂缓", "不安装、注册、启用"),
        "safety": ("不可信数据", "创建 remote、push", "restricted"),
        "claim": ("inventory_status=incomplete", "initialized", "activated", "任务 `active`"),
    }
    missing = [anchor for anchor in anchors[name] if anchor not in skill]
    return {"status": "passed" if not missing else "failed", "cases": len(cases), "missing_anchors": missing,
            "evidence_level": "deterministic-contract"}


def run_all() -> dict:
    suites = {name: run_suite(name) for name in SUITES}
    return {"status": "passed" if all(item["status"] == "passed" for item in suites.values()) else "failed",
            "suites": suites, "claim_limit": "deterministic-contract; field outcome separate"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=(*SUITES, "all"), default="all")
    args = parser.parse_args()
    result = run_all() if args.suite == "all" else {args.suite: run_suite(args.suite)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    passed = result["status"] == "passed" if args.suite == "all" else result[args.suite]["status"] == "passed"
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
