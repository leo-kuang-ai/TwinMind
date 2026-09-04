#!/usr/bin/env python3
"""受控访谈状态与确定性个人 profile 渲染。"""

from __future__ import annotations

import importlib.util
import datetime as dt
import os
import re
import stat
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any


MINIMUM_FIELD_IDS = (
    "primary_scenario", "recent_problems", "fact_owners", "current_project_or_decision",
    "ai_permissions", "maintenance_budget", "seven_day_signal", "thirty_day_stop",
)
FIELD_REGISTRY = {
    "primary_scenario": ("10_当前工作台/01_个人运行地图.md", "首个真实场景"),
    "recent_problems": ("00_待处理/{profile_date}-三个真实问题.md", "最近三个真实问题"),
    "fact_owners": ("20_原始资料/00_来源与事实Owner清单.md", "事实 Owner"),
    "current_project_or_decision": ("10_当前工作台/01_个人运行地图.md", "当前项目或决定"),
    "ai_permissions": ("10_当前工作台/01_个人运行地图.md", "AI 权限"),
    "maintenance_budget": ("10_当前工作台/01_个人运行地图.md", "维护预算"),
    "seven_day_signal": ("99_维护记录/初始化/七天运行计划.md", "七天成功信号"),
    "thirty_day_stop": ("99_维护记录/初始化/七天运行计划.md", "三十天停止条件"),
    "knowledge_topics": ("30_知识主题/00_知识主题地图.md", "知识主题"),
    "outputs": ("40_输出成果/00_输出对象与交付地图.md", "输出对象"),
    "candidate_skills": ("50_Skills/00_候选能力清单.md", "候选能力"),
}


class InterviewError(ValueError):
    pass


def _load_contracts():
    path = Path(__file__).with_name("contract_validation.py")
    spec = importlib.util.spec_from_file_location("render_profile_contracts", path)
    if spec is None or spec.loader is None:
        raise InterviewError("无法加载访谈合同")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTRACTS = _load_contracts()


class InterviewSession:
    def __init__(self, run_id: str, *, host_permission_confirmed: bool = True,
                 storage: dict[str, Any] | None = None) -> None:
        self.run_id = run_id
        self.host_permission_confirmed = host_permission_confirmed
        self.storage = storage or {"storage_domain": "unknown", "encryption_status": "unavailable"}
        self._answers: dict[str, dict[str, Any]] = {}

    def update(self, answer: dict[str, Any]) -> None:
        try:
            CONTRACTS.validate_contract("interview-answer", answer)
        except CONTRACTS.ContractError as error:
            raise InterviewError(str(error)) from error
        field_id = answer["field_id"]
        if field_id not in FIELD_REGISTRY:
            raise InterviewError("未知 field_id")
        if answer.get("evidence_type") == "agent_inference" and answer["status"] == "confirmed":
            raise InterviewError("agent_inference 不能成为 confirmed")
        if answer["sensitivity"] == "restricted" and "value" in answer:
            raise InterviewError("restricted 只允许类别、占位符或本地引用")
        if answer["sensitivity"] == "confidential":
            if not self.host_permission_confirmed:
                raise InterviewError("尚未确认宿主处理 confidential 内容的许可")
            if answer["persistence"] == "runtime_state" and self.storage["storage_domain"] != "local_fixed":
                if self.storage.get("encryption_status") != "verified" or not self.storage.get("encryption_receipt_digest"):
                    raise InterviewError("非 local_fixed confidential runtime_state 需要已验证加密收据")
        if answer["status"] == "withdrawn":
            self._answers.pop(field_id, None)
            return
        self._answers[field_id] = dict(answer)

    def confirmed_answers(self) -> dict[str, str]:
        return {field_id: answer["value"] for field_id, answer in self._answers.items()
                if answer["status"] == "confirmed" and "value" in answer}

    def summary(self) -> dict[str, Any]:
        confirmed = set(self.confirmed_answers())
        return {"minimum_complete": set(MINIMUM_FIELD_IDS) <= confirmed,
                "deferred_to_seven_day_plan": sorted(set(FIELD_REGISTRY) - confirmed),
                "declined": sorted(key for key, value in self._answers.items() if value["status"] == "declined")}

    def public_state(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "fields": {key: {"status": value["status"],
                "sensitivity": value["sensitivity"], "persistence": value["persistence"]}
                for key, value in self._answers.items()}}

    def persistable_state(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "storage": dict(self.storage),
                "answers": {key: value for key, value in self._answers.items()
                            if value["persistence"] != "session_only"}}

    @classmethod
    def resume(cls, run_id: str, state: dict[str, Any],
               storage: dict[str, Any] | None = None) -> "InterviewSession":
        session = cls(run_id, storage=storage or state.get("storage"))
        for answer in state.get("answers", {}).values():
            session.update(answer)
        return session


def render_profile(answers: dict[str, str], *, profile_date: str | None = None) -> dict[str, dict[str, str]]:
    profile_date = profile_date or dt.datetime.now().astimezone().date().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", profile_date):
        raise InterviewError("profile_date 必须是 YYYY-MM-DD")
    grouped: dict[str, list[tuple[str, str]]] = {}
    for field_id in sorted(answers):
        if field_id not in FIELD_REGISTRY:
            continue
        path_template, label = FIELD_REGISTRY[field_id]
        path = path_template.format(profile_date=profile_date)
        grouped.setdefault(path, []).append((label, answers[field_id]))
    rendered = {}
    for path in sorted(grouped):
        title = Path(path).stem
        lines = [f"# {title}", ""]
        for label, value in grouped[path]:
            lines.extend([f"## {label}", "", value, ""])
        rendered[path] = {"ownership": "generated-once", "content": "\n".join(lines).rstrip() + "\n"}
    return rendered


def apply_rendered_profile(target: Path, rendered: dict[str, dict[str, str]]) -> dict[str, Any]:
    created, diff_only = [], []
    for relative_path, entry in rendered.items():
        relative = PurePosixPath(relative_path)
        if (relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_path
                or "\\" in relative_path or any(ord(character) < 32 for character in relative_path)):
            raise InterviewError("渲染目标相对路径不安全")
        current = target
        if current.is_symlink() or not current.is_dir():
            raise InterviewError("渲染目标必须是非 symlink 目录")
        for part in relative.parts[:-1]:
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                current.mkdir(mode=0o700)
                info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise InterviewError(f"渲染父目录是 symlink：{part}")
            if not stat.S_ISDIR(info.st_mode):
                raise InterviewError(f"渲染父路径不是目录：{part}")
        destination = current / relative.parts[-1]
        if destination.exists() or destination.is_symlink():
            diff_only.append(relative_path)
            continue
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(destination, flags, 0o600)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                raise InterviewError("渲染目标不是单链接普通文件")
            data = entry["content"].encode("utf-8")
            offset = 0
            while offset < len(data):
                offset += os.write(descriptor, data[offset:])
            os.fsync(descriptor)
        except Exception:
            os.close(descriptor)
            if destination.exists() and not destination.is_symlink():
                destination.unlink()
            raise
        else:
            os.close(descriptor)
        created.append(relative_path)
    return {"created": created, "diff_only": diff_only}
