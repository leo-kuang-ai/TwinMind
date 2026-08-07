#!/usr/bin/env python3
"""TwinMind 第二大脑初始化的确定性 CLI。"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from urllib.parse import urlsplit


def load_verify_module():
    path = Path(__file__).with_name("verify_vault.py")
    spec = importlib.util.spec_from_file_location("bootstrap_verify_vault", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 verify_vault.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFY = load_verify_module()
SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = SKILL_ROOT / "assets" / "starter-kit"
STARTER_MANIFEST_PATH = SKILL_ROOT / "manifests" / "starter-v1.json"
TOOL_IDENTITIES_PATH = SKILL_ROOT / "manifests" / "tool-identities-v1.json"


def _load_contract_module():
    path = Path(__file__).with_name("contract_validation.py")
    spec = importlib.util.spec_from_file_location("bootstrap_contract_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tool_manifest() -> dict:
    manifest = json.loads(TOOL_IDENTITIES_PATH.read_text(encoding="utf-8"))
    _load_contract_module().validate_tool_identity_manifest(manifest)
    return manifest


def _tool_identity(tool_id: str, platform: str = "macos", manifest: dict | None = None) -> dict:
    manifest = _tool_manifest() if manifest is None else manifest
    for item in manifest["tools"]:
        if item["tool_id"] == tool_id and item["platform"] == platform:
            return item
    raise VERIFY.SafetyError(f"identity manifest 缺少 {tool_id}/{platform}")


def validate_official_url(tool_id: str, candidate: str, platform: str = "macos",
                          manifest: dict | None = None) -> None:
    expected = _tool_identity(tool_id, platform, manifest)["official_url"]
    parsed = urlsplit(candidate)
    if parsed.username or parsed.password or parsed.fragment or parsed.query or candidate != expected:
        raise VERIFY.SafetyError("URL 必须精确匹配 identity manifest 的无凭据 HTTPS 初始入口")


def _readiness_item(requirement: str, evidence: dict | None = None) -> dict:
    evidence = evidence or {}
    return {"requirement": requirement, "status": evidence.get("status", "missing"),
            "official_verified": bool(evidence.get("official_verified", False))}


def tool_probe_host(*, platform: str, python_evidence: dict, git_evidence: dict,
                    app_evidence: dict, target_probe=None) -> dict:
    del target_probe
    if platform != "macos":
        return {"schema_version": 1, "platform": platform, "command_outcome": "action_required",
                "owner": "user", "next_action": "使用 macOS 正式路径或进入后续平台适配"}
    tools = {
        "python": _readiness_item("runtime-required", python_evidence),
        "git": _readiness_item("product-required", git_evidence),
        "workbuddy": _readiness_item("recommended", app_evidence.get("workbuddy")),
        "obsidian": _readiness_item("recommended", app_evidence.get("obsidian")),
        "community_plugins": {"requirement": "optional", "status": "not_selected",
                              "official_verified": False, "selected": []},
    }
    ready = all(tools[name]["status"] == "ready" and tools[name]["official_verified"]
                for name in ("python", "git"))
    return {"schema_version": 1, "platform": platform, "observed_at": "runtime-probe",
            "path_confirmation_ready": ready, "tools": tools}


def example_missing_recommended_readiness() -> dict:
    return tool_probe_host(platform="macos",
        python_evidence={"status": "ready", "official_verified": True},
        git_evidence={"status": "ready", "official_verified": True}, app_evidence={})


def build_tool_plan(readiness: dict, side_effect=None) -> dict:
    del side_effect
    manifest = _tool_manifest()
    cards = {}
    for tool_id in ("git", "workbuddy", "obsidian"):
        identity = _tool_identity(tool_id, readiness["platform"], manifest)
        cards[tool_id] = {
            "requirement": readiness["tools"][tool_id]["requirement"],
            "current_status": readiness["tools"][tool_id]["status"],
            "official_url": identity["official_url"], "platform": readiness["platform"],
            "license_cost_review": "打开前复核当前许可与成本",
            "data_permissions": "复核读取、写入目录和最小权限",
            "network_boundary": "复核联网、模型提供方与数据路径",
            "logs_cache_secrets": "确认日志、缓存、密钥和派生数据位置",
            "disable_uninstall": "记录停用、卸载和派生数据清理步骤",
            "verification": "安装后重新采集 executable 或 bundle/signing identity",
            "next_action": "选择安装引导、明确暂缓或继续复核",
            "source_as_of": identity["source_as_of"],
        }
    plan = {"subject_kind": "tool_guidance", "identity_manifest_digest": manifest["manifest_digest"],
            "readiness": readiness, "cards": cards, "creates_authorization": False}
    plan["plan_digest"] = _plan_digest(plan)
    return plan


def verify_tool_readiness(readiness: dict, choices: dict[str, str]) -> dict:
    tools = json.loads(json.dumps(readiness["tools"]))
    if not readiness["path_confirmation_ready"]:
        return {"command_outcome": "action_required", "path_confirmation_ready": False, "tools": tools}
    for tool_id in ("workbuddy", "obsidian"):
        item = tools[tool_id]
        item["ready"] = item["status"] == "ready" and item["official_verified"]
        if not item["ready"] and choices.get(tool_id) != "deferred_by_user":
            return {"command_outcome": "action_required", "path_confirmation_ready": True, "tools": tools}
        if choices.get(tool_id) == "deferred_by_user":
            item["user_choice"] = "deferred_by_user"
    return {"command_outcome": "success", "path_confirmation_ready": True, "tools": tools}


def tool_probe_vault(target: Path, *, selected_target: Path | None) -> dict:
    if selected_target is None:
        raise VERIFY.SafetyError("vault scope 需要用户已选择目标")
    normalized = VERIFY.normalize_target_path(target)
    selected = VERIFY.normalize_target_path(selected_target)
    if normalized != selected or not normalized.is_dir():
        raise VERIFY.SafetyError("vault scope 目标不存在或越界")
    config = normalized / ".obsidian"
    plugins: list[str] = []
    community = config / "community-plugins.json"
    if community.is_file() and not community.is_symlink():
        value = json.loads(VERIFY.read_regular_bytes(community).decode("utf-8"))
        if isinstance(value, list):
            plugins = [item for item in value if isinstance(item, str)][:128]
    return {"scope": "vault", "target_identity_digest": VERIFY.probe_target(normalized)["identity_digest"],
            "obsidian_config_detected": config.is_dir() and not config.is_symlink(),
            "community_plugins": {"selected": plugins}}


def _git(git_executable: str, cwd: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    command_env = os.environ.copy()
    command_env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                        "GIT_ATTR_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    if env:
        command_env.update(env)
    return subprocess.run([git_executable, *args], cwd=cwd, env=command_env,
                          text=True, capture_output=True, check=False)


def inspect_git_boundary(target: Path, git_executable: str) -> dict:
    dot_git = target / ".git"
    if dot_git.is_file():
        return {"kind": "worktree_pointer", "repository_root": str(target)}
    if dot_git.is_dir():
        return {"kind": "independent", "repository_root": str(target)}
    result = _git(git_executable, target, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return {"kind": "none", "repository_root": None}
    root = Path(result.stdout.strip()).resolve()
    return {"kind": "independent" if root == target.resolve() else "parent", "repository_root": str(root)}


def _git_environment_facts(target: Path, git_executable: str, boundary: dict) -> tuple[dict, list[str]]:
    facts = {"boundary": boundary, "hooks": [], "config": [], "staged": [], "attributes": []}
    blockers: list[str] = []
    if boundary["kind"] in {"independent", "parent", "worktree_pointer"}:
        repo = Path(boundary["repository_root"])
        git_dir_result = _git(git_executable, repo, "rev-parse", "--git-dir")
        if git_dir_result.returncode != 0:
            return facts, ["git_boundary_unreadable"]
        git_dir = (repo / git_dir_result.stdout.strip()).resolve()
        hooks = git_dir / "hooks"
        if hooks.is_dir():
            facts["hooks"] = sorted(path.name for path in hooks.iterdir()
                                    if path.is_file() and os.access(path, os.X_OK) and not path.name.endswith(".sample"))
            if facts["hooks"]:
                blockers.append("executable_hooks")
        config = _git(git_executable, repo, "config", "--local", "--list", "--show-origin")
        facts["config"] = sorted(line for line in config.stdout.splitlines() if line)
        risky = ("filter.", "include.", "core.hookspath", "core.attributesfile", "commit.gpgsign",
                 "gpg.program", "core.fsmonitor", "core.autocrlf", "core.eol")
        if any(any(token in line.lower() for token in risky) for line in facts["config"]):
            blockers.append("executable_git_config")
        staged = _git(git_executable, repo, "diff", "--cached", "--name-only", "-z")
        facts["staged"] = sorted(item for item in staged.stdout.split("\0") if item)
        if facts["staged"]:
            blockers.append("preexisting_staged_changes")
        for attributes in (repo / ".gitattributes", git_dir / "info" / "attributes"):
            if attributes.is_symlink():
                blockers.append("git_attributes")
                continue
            if attributes.is_file():
                active = [line.strip() for line in attributes.read_text(encoding="utf-8", errors="replace").splitlines()
                          if line.strip() and not line.lstrip().startswith("#")]
                if active:
                    facts["attributes"].append({"path": str(attributes), "sha256": _sha256(attributes)})
                    blockers.append("git_attributes")
    return facts, blockers


def _repository_root(target: Path, boundary: dict) -> Path:
    if boundary["kind"] == "parent":
        return Path(boundary["repository_root"]).resolve()
    return target.resolve()


def _git_paths(target: Path, repo: Path, approved_files: list[str]) -> list[str]:
    return sorted((target / relative).resolve().relative_to(repo).as_posix() for relative in approved_files)


def build_git_baseline_plan(target: Path, git_executable: str, use_parent_repo: bool = False) -> dict:
    if not git_executable or not Path(git_executable).is_file():
        return {"command_outcome": "action_required", "blockers": ["git_missing"], "operations": []}
    boundary = inspect_git_boundary(target, git_executable)
    if boundary["kind"] == "parent" and not use_parent_repo:
        return {"command_outcome": "action_required", "blockers": ["parent_git_requires_choice"], "operations": []}
    facts, blockers = _git_environment_facts(target, git_executable, boundary)
    approved_files = []
    for path in sorted(target.rglob("*")):
        relative_parts = path.relative_to(target).parts
        if ".git" in relative_parts:
            if relative_parts[0] != ".git":
                blockers.append("nested_git_boundary")
            continue
        if path.is_symlink():
            blockers.append("symlink")
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(target).as_posix()
        lowered = path.name.lower()
        if lowered.startswith(".env") or lowered.endswith((".pem", ".key", ".p12", ".pfx")):
            blockers.append("secret")
        if path.stat().st_size > 100 * 1024 * 1024:
            blockers.append("oversized_file")
        approved_files.append(relative)
    repo = _repository_root(target, boundary)
    approved_git_paths = _git_paths(target, repo, approved_files)
    expected_staged_files = list(approved_git_paths)
    if boundary["kind"] != "none":
        head = _git(git_executable, repo, "rev-parse", "--verify", "HEAD")
        if head.returncode == 0:
            modified = _git(git_executable, repo, "diff", "--name-only", "-z", "HEAD", "--", *approved_git_paths)
            untracked = _git(git_executable, repo, "ls-files", "--others", "--exclude-standard", "-z", "--", *approved_git_paths)
            expected_staged_files = sorted(set(
                [item for item in modified.stdout.split("\0") if item]
                + [item for item in untracked.stdout.split("\0") if item]
            ))
        ignored = _git(git_executable, repo, "check-ignore", "-z", "--", *approved_git_paths)
        if ignored.stdout:
            blockers.append("ignored_file")
    operations = []
    if boundary["kind"] == "none":
        operations.append({"operation_id": "git-init", "kind": "git-init"})
    operations.extend([
        {"operation_id": "git-local-identity", "kind": "git-local-identity"},
        {"operation_id": "git-add-approved", "kind": "git-add"},
        {"operation_id": "git-baseline-commit", "kind": "git-baseline-commit"},
    ])
    probe = VERIFY.probe_target(target)
    plan = {"subject_kind": "vault", "subject_identity_digest": probe["identity_digest"],
            "target_identity_digest": probe["identity_digest"], "normalized_path": str(target.resolve()),
            "probe_snapshot_digest": probe["snapshot_digest"],
            "git_executable": str(Path(git_executable).resolve()), "boundary": boundary,
            "repository_root": str(repo),
            "environment_digest": VERIFY.digest_value(facts), "approved_files": approved_files,
            "approved_git_paths": approved_git_paths, "expected_staged_files": expected_staged_files,
            "operations": operations, "blockers": sorted(set(blockers)),
            "command_outcome": "action_required" if blockers else "planned"}
    plan["plan_digest"] = _plan_digest(plan)
    return plan


def apply_git_baseline(plan: dict, authorization: dict | None,
                       local_identity: tuple[str, str] | None = None) -> dict:
    if not _authorization_valid(plan, authorization):
        return {"command_outcome": "action_required", "lifecycle_state": "personalized"}
    if plan.get("blockers"):
        return {"command_outcome": "action_required", "lifecycle_state": "personalized", "blockers": plan["blockers"]}
    target = Path(plan["normalized_path"])
    repo = Path(plan["repository_root"])
    git_executable = plan["git_executable"]
    current_probe = VERIFY.probe_target(target)
    if (current_probe["identity_digest"] != plan.get("target_identity_digest")
            or current_probe["snapshot_digest"] != plan.get("probe_snapshot_digest")):
        return {"command_outcome": "plan_stale", "lifecycle_state": "personalized"}
    boundary_now = inspect_git_boundary(target, git_executable)
    facts, blockers = _git_environment_facts(target, git_executable, boundary_now)
    if blockers or boundary_now != plan["boundary"] or VERIFY.digest_value(facts) != plan["environment_digest"]:
        return {"command_outcome": "plan_stale", "lifecycle_state": "personalized"}
    with tempfile.TemporaryDirectory() as temp:
        isolation = Path(temp)
        hooks = isolation / "hooks"
        template = isolation / "template"
        hooks.mkdir()
        template.mkdir()
        if plan["boundary"]["kind"] == "none":
            result = _git(git_executable, target, "-c", f"init.templateDir={template}", "init", "-q")
            if result.returncode != 0:
                return {"command_outcome": "partial", "lifecycle_state": "personalized"}
            repo = target
        if local_identity:
            name, email = local_identity
            if _git(git_executable, target, "config", "--local", "user.name", name).returncode != 0:
                return {"command_outcome": "partial", "lifecycle_state": "personalized"}
            if _git(git_executable, target, "config", "--local", "user.email", email).returncode != 0:
                return {"command_outcome": "partial", "lifecycle_state": "personalized"}
        add = _git(git_executable, repo, "add", "--", *plan["approved_git_paths"])
        if add.returncode != 0:
            return {"command_outcome": "partial", "lifecycle_state": "personalized"}
        staged = _git(git_executable, repo, "diff", "--cached", "--name-only", "-z")
        staged_files = sorted(item for item in staged.stdout.split("\0") if item)
        if staged_files != sorted(plan["expected_staged_files"]) or not staged_files:
            return {"command_outcome": "action_required", "lifecycle_state": "personalized", "blockers": ["staged_set_mismatch"]}
        commit = _git(git_executable, repo, "-c", f"core.hooksPath={hooks}", "-c", "commit.gpgSign=false",
                      "-c", "core.fsmonitor=false", "commit", "-q", "--no-verify", "-m", "初始化 TwinMind 第二大脑")
        if commit.returncode != 0:
            return {"command_outcome": "partial", "lifecycle_state": "personalized", "reason": commit.stderr.strip()}
    oid = _git(git_executable, repo, "rev-parse", "HEAD").stdout.strip()
    parent = _git(git_executable, repo, "rev-parse", "HEAD^")
    if parent.returncode == 0:
        committed_files = sorted(item for item in _git(
            git_executable, repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", "HEAD"
        ).stdout.split("\0") if item)
    else:
        committed_files = sorted(item for item in _git(
            git_executable, repo, "ls-tree", "-r", "--name-only", "-z", "HEAD"
        ).stdout.split("\0") if item)
    content_verified = True
    for git_path in plan["approved_git_paths"]:
        working = _git(git_executable, repo, "hash-object", "--no-filters", "--", git_path)
        committed = _git(git_executable, repo, "rev-parse", f"HEAD:{git_path}")
        if working.returncode != 0 or committed.returncode != 0 or working.stdout.strip() != committed.stdout.strip():
            content_verified = False
            break
    if (not re.fullmatch(r"[0-9a-f]{40}", oid)
            or committed_files != sorted(plan["expected_staged_files"]) or not content_verified):
        return {"command_outcome": "failed", "lifecycle_state": "personalized",
                "reason": "baseline_post_commit_verification_failed",
                "committed_files": committed_files,
                "expected_staged_files": sorted(plan["expected_staged_files"]),
                "content_verified": content_verified}
    return {"command_outcome": "success", "lifecycle_state": "initialized",
            "baseline_commit_oid": oid, "baseline_tree_verified": True,
            "repository_boundary_digest": VERIFY.digest_value(inspect_git_boundary(target, git_executable))}


def component_state(*, installed: bool, opened: bool = False, user_verified: bool = False,
                    deferred_by_user: bool = False) -> dict:
    if deferred_by_user:
        return {"status": "deferred_by_user"}
    if not installed:
        return {"status": "unavailable"}
    if user_verified:
        return {"status": "user_verified"}
    if opened:
        return {"status": "opened"}
    return {"status": "detected"}


def obsidian_user_confirmation(core_plugins: list[str], template_folder: str) -> dict:
    required = {"File Explorer", "Search", "Quick Switcher", "Backlinks", "Templates"}
    if set(core_plugins) != required or template_folder != "90_模板":
        return {"status": "action_required", "community_plugins": []}
    return {"status": "user_verified", "core_plugins": sorted(required),
            "template_folder": template_folder, "community_plugins": []}


def _starter_manifest() -> dict:
    return json.loads(STARTER_MANIFEST_PATH.read_text(encoding="utf-8"))


def _plan_digest(plan: dict) -> str:
    core = dict(plan)
    core.pop("plan_digest", None)
    return VERIFY.digest_value(core)


def build_scaffold_plan(target: Path, allow_existing_projection: bool = False) -> dict:
    probe = VERIFY.probe_target(target)
    if probe["shape"] == "nonempty" and not allow_existing_projection:
        raise VERIFY.SafetyError("非空目标不得进入 scaffold")
    manifest = _starter_manifest()
    operations = []
    for entry in manifest["files"]:
        operations.append({
            "operation_id": f"copy:{entry['path']}",
            "kind": "copy-starter",
            "relative_path": entry["path"],
            "sha256": entry["sha256"],
            "ownership": entry["ownership"],
        })
    plan = {
        "plan_schema_version": 1,
        "subject_kind": "vault",
        "subject_identity_digest": probe["identity_digest"],
        "target_identity_digest": probe["identity_digest"],
        "normalized_path": probe["normalized_path"],
        "probe_snapshot_digest": probe["snapshot_digest"],
        "starter_manifest_digest": VERIFY.digest_value(manifest),
        "operations": operations,
    }
    plan["plan_digest"] = _plan_digest(plan)
    return plan


def authorize_plan(plan: dict, operation_ids: list[str]) -> dict:
    allowed = {item["operation_id"] for item in plan["operations"]}
    if not operation_ids or len(operation_ids) != len(set(operation_ids)) or not set(operation_ids) <= allowed:
        raise VERIFY.SafetyError("授权含计划外 operation")
    return {
        "schema_version": 1,
        "authorization_id": f"auth-{plan['plan_digest'][:16]}",
        "plan_digest": plan["plan_digest"],
        "subject_kind": plan["subject_kind"],
        "subject_identity_digest": plan["subject_identity_digest"],
        "approved_operation_ids": list(operation_ids),
        "confirmed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def _authorization_valid(plan: dict, authorization: dict | None) -> bool:
    if not authorization or _plan_digest(plan) != plan.get("plan_digest"):
        return False
    for field in ("plan_digest", "subject_kind", "subject_identity_digest"):
        if authorization.get(field) != plan.get(field):
            return False
    allowed = {item["operation_id"] for item in plan["operations"]}
    approved = authorization.get("approved_operation_ids", [])
    return bool(approved) and len(approved) == len(set(approved)) and set(approved) <= allowed


def _sha256(path: Path) -> str:
    return VERIFY._sha256_file(path)


def _safe_parent(target: Path, relative_path: str) -> Path:
    relative = PurePosixPath(relative_path)
    if (not relative_path or relative.is_absolute() or ".." in relative.parts
            or relative.as_posix() != relative_path or "\\" in relative_path
            or any(ord(character) < 32 for character in relative_path)):
        raise VERIFY.SafetyError("目标相对路径不安全")
    destination = target / relative_path
    current = target
    for part in relative.parts[:-1]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            current.mkdir(mode=0o700)
            info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise VERIFY.SafetyError(f"路径组件是 symlink：{part}")
        if not stat.S_ISDIR(info.st_mode):
            raise VERIFY.SafetyError(f"路径组件不是目录：{part}")
    return destination


def _exclusive_write(data: bytes, destination: Path) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(destination, flags, 0o600)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise VERIFY.SafetyError("新建目标不是单链接普通文件")
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


def apply_scaffold(plan: dict, authorization: dict | None, fail_after: int | None = None,
                   before_rename=None) -> dict:
    if not _authorization_valid(plan, authorization):
        return {"command_outcome": "action_required", "created_files": [], "completed_operations": []}
    target = Path(plan["normalized_path"])
    current_probe = VERIFY.probe_target(target)
    if (current_probe["identity_digest"] != plan.get("target_identity_digest")
            or current_probe["snapshot_digest"] != plan["probe_snapshot_digest"]):
        return {"command_outcome": "plan_stale", "created_files": [], "completed_operations": []}
    if VERIFY.digest_value(_starter_manifest()) != plan["starter_manifest_digest"]:
        return {"command_outcome": "plan_stale", "created_files": [], "completed_operations": []}
    source_payloads: dict[str, bytes] = {}
    for operation in plan["operations"]:
        source = ASSET_ROOT / operation["relative_path"]
        if source.is_symlink() or not source.is_file():
            return {"command_outcome": "plan_stale", "created_files": [], "completed_operations": []}
        try:
            data = VERIFY.read_regular_bytes(source)
        except (OSError, VERIFY.SafetyError):
            return {"command_outcome": "plan_stale", "created_files": [], "completed_operations": []}
        if hashlib.sha256(data).hexdigest() != operation["sha256"]:
            return {"command_outcome": "plan_stale", "created_files": [], "completed_operations": []}
        source_payloads[operation["relative_path"]] = data
    target_was_missing = not target.exists()
    write_root = target
    staging_path = None
    if target_was_missing:
        staging_path = target.parent / f".{target.name}.twinmind-stage-{plan['plan_digest'][:12]}"
        if staging_path.is_symlink():
            return {"command_outcome": "unsafe_target", "created_files": [], "completed_operations": []}
        staging_path.mkdir(mode=0o700, exist_ok=True)
        staging_info = staging_path.stat()
        if (staging_info.st_uid != os.getuid() or stat.S_IMODE(staging_info.st_mode) & 0o077
                or not stat.S_ISDIR(staging_info.st_mode)):
            return {"command_outcome": "unsafe_target", "created_files": [], "completed_operations": []}
        write_root = staging_path
    created: list[dict] = []
    completed: list[str] = []
    approved = set(authorization["approved_operation_ids"])
    existing_casefold = {
        path.relative_to(write_root).as_posix().casefold(): path.relative_to(write_root).as_posix()
        for path in write_root.rglob("*")
    }
    for operation in plan["operations"]:
        if operation["operation_id"] not in approved:
            continue
        relative = operation["relative_path"]
        relative_parts = PurePosixPath(relative).parts
        for index in range(1, len(relative_parts) + 1):
            prefix = PurePosixPath(*relative_parts[:index]).as_posix()
            folded_prefix = prefix.casefold()
            if folded_prefix in existing_casefold and existing_casefold[folded_prefix] != prefix:
                return {"command_outcome": "conflict", "created_files": created, "completed_operations": completed}
        folded = relative.casefold()
        destination = _safe_parent(write_root, relative)
        if destination.exists() or destination.is_symlink():
            if destination.is_file() and not destination.is_symlink() and _sha256(destination) == operation["sha256"]:
                if target_was_missing:
                    receipt = {"path": relative, "sha256": operation["sha256"],
                               "ownership": operation["ownership"], "operation_id": operation["operation_id"]}
                    created.append(receipt)
                    completed.append(operation["operation_id"])
                    existing_casefold[folded] = relative
                continue
            return {"command_outcome": "conflict", "created_files": created, "completed_operations": completed}
        _exclusive_write(source_payloads[relative], destination)
        receipt = {"path": relative, "sha256": _sha256(destination), "ownership": operation["ownership"],
                   "operation_id": operation["operation_id"]}
        created.append(receipt)
        completed.append(operation["operation_id"])
        for index in range(1, len(relative_parts) + 1):
            prefix = PurePosixPath(*relative_parts[:index]).as_posix()
            existing_casefold[prefix.casefold()] = prefix
        if fail_after is not None and len(completed) >= fail_after:
            return {"command_outcome": "partial", "created_files": created,
                    "completed_operations": completed, "staging_path": str(staging_path) if staging_path else None}
    if target_was_missing:
        if before_rename is not None:
            before_rename()
        if target.exists():
            return {"command_outcome": "conflict", "created_files": created,
                    "completed_operations": completed, "staging_path": str(staging_path)}
        staging_path.rename(target)
    return {"command_outcome": "success" if created else "no_changes", "created_files": created,
            "completed_operations": completed, "staging_path": None}


def recover_pre_baseline(target: Path, created_files: list[dict]) -> dict:
    target = VERIFY.normalize_target_path(target)
    preserved: list[str] = []
    removed: list[str] = []
    for item in reversed(created_files):
        raw = item.get("path", "")
        relative = PurePosixPath(raw)
        if (not raw or relative.is_absolute() or ".." in relative.parts or relative.as_posix() != raw
                or "\\" in raw or any(ord(character) < 32 for character in raw)):
            preserved.append(f"unsafe-path-digest:{VERIFY.digest_value(raw)}")
            continue
        if item["ownership"] == "append-only" or not _unlink_verified_file(target, relative, item["sha256"]):
            preserved.append(raw)
            continue
        removed.append(raw)
    for directory in sorted((path for path in target.rglob("*") if path.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    return {"command_outcome": "success", "removed_paths": removed, "preserved_paths": preserved}


def build_host_tool_plan(tool_id: str, identity_digest: str, action: str, value: str) -> dict:
    if action not in {"open-source", "open-app"}:
        raise VERIFY.SafetyError("host tool action 不允许")
    if action == "open-source":
        validate_official_url(tool_id, value)
    operation = {"operation_id": f"{tool_id}:{action}", "kind": action, "value": value}
    plan = {"plan_schema_version": 1, "subject_kind": "host_tool",
            "subject_identity_digest": identity_digest, "tool_id": tool_id,
            "identity_manifest_digest": _tool_manifest()["manifest_digest"], "operations": [operation]}
    plan["plan_digest"] = _plan_digest(plan)
    return plan


def build_personalize_plan(run_id: str, target: Path, confirmed_answers: dict[str, str],
                           state_storage: dict | None = None) -> dict:
    render_path = Path(__file__).with_name("render_profile.py")
    spec = importlib.util.spec_from_file_location("bootstrap_render_profile", render_path)
    if spec is None or spec.loader is None:
        raise VERIFY.SafetyError("无法加载 profile renderer")
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    probe = VERIFY.probe_target(target)
    rendered = renderer.render_profile(confirmed_answers)
    operations = [{"operation_id": f"personalize:{path}", "kind": "render-profile",
                   "relative_path": path, "content_digest": VERIFY.digest_value(entry["content"])}
                  for path, entry in sorted(rendered.items())]
    plan = {"plan_schema_version": 1, "run_id": run_id, "journey": "create", "plan_stage": "personalize",
            "subject_kind": "vault", "subject_identity_digest": probe["identity_digest"],
            "target_identity_digest": probe["identity_digest"],
            "normalized_path": probe["normalized_path"],
            "probe_snapshot_digest": probe["snapshot_digest"], "answers_digest": VERIFY.digest_value(confirmed_answers),
            "operations": operations}
    if state_storage is not None:
        binding = {
            "state_root_identity_digest": state_storage["identity_digest"],
            "storage_domain": state_storage["storage_domain"],
        }
        if state_storage.get("encryption_receipt_digest"):
            binding["encryption_receipt_digest"] = state_storage["encryption_receipt_digest"]
        plan["state_binding"] = binding
    plan["plan_digest"] = _plan_digest(plan)
    return plan


def apply_host_tool(plan: dict, authorization: dict | None, executor) -> dict:
    if not _authorization_valid(plan, authorization):
        return {"command_outcome": "action_required"}
    manifest = _tool_manifest()
    if plan.get("identity_manifest_digest") != manifest["manifest_digest"]:
        return {"command_outcome": "plan_stale"}
    if len(plan.get("operations", [])) != 1:
        return {"command_outcome": "plan_stale"}
    operation = plan["operations"][0]
    identity = _tool_identity(plan["tool_id"], manifest=manifest)
    if plan.get("subject_identity_digest") != VERIFY.digest_value(identity):
        return {"command_outcome": "plan_stale"}
    if operation["kind"] == "open-source":
        validate_official_url(plan["tool_id"], operation["value"], manifest=manifest)
    elif (operation["kind"] != "open-app" or identity["kind"] != "app"
          or operation["value"] != identity["app_identity"]["bundle_id"]):
        return {"command_outcome": "plan_stale"}
    executor(operation["kind"], operation["value"])
    return {"command_outcome": "success", "external_action_receipt": {
        "tool_id": plan["tool_id"], "operation_id": operation["operation_id"], "action": operation["kind"]}}


def record_tool_choice(events: list[dict], choice: dict, *, run_id: str = "tool-prepare") -> list[dict]:
    contracts = _load_contract_module()
    contracts.validate_contract("tool-choice", choice)
    event = {"schema_version": 1, "event_id": f"choice-{choice['idempotency_key']}",
             "run_id": run_id, "event_name": "tool_choice_recorded",
             "phase": "tool_prepare", "command_outcome": "success", "occurred_at": choice["confirmed_at"],
             "idempotency_key": choice["idempotency_key"], "input_digest": choice["input_digest"]}
    return contracts.record_idempotent_event(events, event)


def record_tool_evidence(evidence: dict) -> dict:
    _load_contract_module().validate_contract("tool-evidence", evidence)
    return dict(evidence)


def build_post_baseline_recovery_plan(*, baseline_oid: str, current_head: str,
                                      tree_matches: bool, user_touched_paths: bool) -> dict:
    safe = baseline_oid == current_head and tree_matches and not user_touched_paths
    return {
        "recovery_mode": "post_baseline_compensation" if safe else "manual_git_recovery",
        "baseline_commit_oid": baseline_oid,
        "current_head": current_head,
        "operations": [{"operation_id": "git-compensation", "kind": "compensation-commit"}] if safe else [],
        "claim_ceiling": "history-preserving-compensation" if safe else "manual-only",
    }


def build_cleanup_plan(state_root: Path, run_id: str, scope: str, acknowledge_recovery_loss: bool = False) -> dict:
    if scope not in {"interview", "all"}:
        raise VERIFY.SafetyError("cleanup scope 不允许")
    if scope == "all" and not acknowledge_recovery_loss:
        raise VERIFY.SafetyError("scope=all 必须确认永久失去自动 resume/recover 能力")
    _validate_run_id(run_id)
    run_candidate = state_root / run_id
    if run_candidate.is_symlink():
        raise VERIFY.SafetyError("cleanup run 不得是 symlink")
    run_root = run_candidate.resolve(strict=True)
    root = state_root.resolve(strict=True)
    if root not in run_root.parents or run_root.is_symlink():
        raise VERIFY.SafetyError("cleanup run 越界")
    files = []
    for path in sorted(run_root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        if scope == "interview" and "interview" not in path.name:
            continue
        files.append({"operation_id": f"cleanup:{relative}", "kind": "cleanup-state", "relative_path": relative,
                      "sha256": _sha256(path)})
    plan = {"plan_schema_version": 1, "subject_kind": "state_cleanup",
            "subject_identity_digest": VERIFY.digest_value({"root": str(root), "run_id": run_id}),
            "state_root": str(root), "run_id": run_id, "scope": scope,
            "state_root_identity_digest": _path_identity_digest(root),
            "run_identity_digest": _path_identity_digest(run_root),
            "recovery_loss_acknowledged": acknowledge_recovery_loss, "operations": files}
    plan["plan_digest"] = _plan_digest(plan)
    return plan


def apply_cleanup(plan: dict, authorization: dict | None) -> dict:
    if not _authorization_valid(plan, authorization):
        return {"command_outcome": "action_required", "removed": []}
    root = Path(plan["state_root"]).resolve(strict=True)
    run_root = root / plan["run_id"]
    if (root.is_symlink() or run_root.is_symlink() or not run_root.is_dir()
            or _path_identity_digest(root) != plan.get("state_root_identity_digest")
            or _path_identity_digest(run_root) != plan.get("run_identity_digest")):
        return {"command_outcome": "plan_stale", "removed": []}
    removed = []
    approved = set(authorization["approved_operation_ids"])
    for operation in plan["operations"]:
        if operation["operation_id"] not in approved:
            continue
        relative = PurePosixPath(operation["relative_path"])
        if (relative.is_absolute() or ".." in relative.parts or relative.as_posix() != operation["relative_path"]
                or not relative.parts or relative.parts[0] != plan["run_id"]):
            return {"command_outcome": "plan_stale", "removed": removed}
        if not _unlink_verified_file(root, relative, operation["sha256"]):
            return {"command_outcome": "plan_stale", "removed": removed}
        removed.append(operation["relative_path"])
    return {"command_outcome": "success", "removed": removed}


def _path_identity_digest(path: Path) -> str:
    info = path.lstat()
    return VERIFY.digest_value({
        "device": info.st_dev,
        "inode": info.st_ino,
        "mode": stat.S_IMODE(info.st_mode),
        "uid": info.st_uid,
    })


def _unlink_verified_file(root: Path, relative: PurePosixPath, expected_sha256: str) -> bool:
    required = ("O_DIRECTORY", "O_NOFOLLOW")
    if any(not hasattr(os, name) for name in required):
        raise VERIFY.SafetyError("当前平台缺少 cleanup no-follow 安全原语")
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(current)
        for part in relative.parts[:-1]:
            current = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            descriptors.append(current)
            info = os.fstat(current)
            if not stat.S_ISDIR(info.st_mode):
                return False
        name = relative.parts[-1]
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current)
        descriptors.append(descriptor)
        opened = os.fstat(descriptor)
        listed = os.stat(name, dir_fd=current, follow_symlinks=False)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or (opened.st_dev, opened.st_ino) != (listed.st_dev, listed.st_ino)):
            return False
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        if digest.hexdigest() != expected_sha256:
            return False
        os.unlink(name, dir_fd=current)
        return True
    except (FileNotFoundError, NotADirectoryError, OSError):
        return False
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _json_argument(command: argparse.ArgumentParser) -> None:
    command.add_argument("--json", action="store_true", required=True)


def _state_argument(command: argparse.ArgumentParser) -> None:
    command.add_argument("--state-dir")


def _read_json_input(reference: str) -> dict:
    if reference == "-":
        data = sys.stdin.buffer.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise VERIFY.SafetyError("JSON stdin 超过 8 MiB 上限")
        text = data.decode("utf-8")
    else:
        path = Path(reference)
        if path.is_symlink() or not path.is_file():
            raise VERIFY.SafetyError("JSON 输入必须是非 symlink 普通文件")
        text = VERIFY.read_regular_bytes(path).decode("utf-8")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise VERIFY.SafetyError("JSON 输入必须是 object")
    return value


def _unwrap(payload: dict, key: str) -> dict:
    value = payload.get(key, payload)
    if not isinstance(value, dict):
        raise VERIFY.SafetyError(f"{key} 输入必须是 object")
    return value


def _load_render_module():
    path = Path(__file__).with_name("render_profile.py")
    spec = importlib.util.spec_from_file_location("bootstrap_render_profile_cli", path)
    if spec is None or spec.loader is None:
        raise VERIFY.SafetyError("无法加载 render_profile.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_state_root(raw: str, *, create: bool = True) -> Path:
    root = Path(raw)
    if not root.is_absolute():
        raise VERIFY.SafetyError("state-dir 必须是绝对路径")
    if root.exists():
        if root.is_symlink() or not root.is_dir():
            raise VERIFY.SafetyError("state-dir 必须是普通目录")
        info = root.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise VERIFY.SafetyError("已有 state-dir owner/mode 不安全")
    else:
        if not create:
            raise FileNotFoundError(raw)
        root.mkdir(mode=0o700, parents=True)
    return root.resolve(strict=True)


def _state_dir(raw: str | None) -> str:
    if raw:
        return raw
    if sys.platform == "darwin":
        return str(Path.home() / "Library" / "Application Support" / "TwinMind" / "runs")
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        return str(Path(xdg_state) / "twinmind")
    return str(Path.home() / ".local" / "state" / "twinmind")


def _validate_run_id(run_id: str) -> None:
    relative = PurePosixPath(run_id)
    if (relative.is_absolute() or len(relative.parts) != 1 or relative.as_posix() != run_id
            or ".." in relative.parts or any(ord(character) < 32 for character in run_id)):
        raise VERIFY.SafetyError("run-id 不安全")


def _run_state_root(raw: str, run_id: str) -> Path:
    root = _prepare_state_root(raw)
    _validate_run_id(run_id)
    run_root = root / run_id
    if run_root.exists():
        if run_root.is_symlink() or not run_root.is_dir():
            raise VERIFY.SafetyError("run state 不是普通目录")
        info = run_root.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise VERIFY.SafetyError("已有 run state owner/mode 不安全")
    else:
        run_root.mkdir(mode=0o700)
    return run_root


def _existing_run_state_root(raw: str, run_id: str) -> Path:
    root = _prepare_state_root(raw, create=False)
    _validate_run_id(run_id)
    run_root = root / run_id
    if run_root.is_symlink() or not run_root.is_dir():
        raise FileNotFoundError(run_id)
    info = run_root.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise VERIFY.SafetyError("已有 run state owner/mode 不安全")
    return run_root


def _unknown_state_storage(state_root: Path, target: Path) -> dict:
    identity = VERIFY.validate_state_root(state_root, target)
    evidence = {
        "adapter": "unavailable",
        "storage_domain": "unknown",
        "reason": "v0.1 未取得可验证的卷类型、removable 与 sync provider 证据",
    }
    return {
        "identity_digest": identity["identity_digest"],
        "storage_domain": "unknown",
        "classification_evidence_digest": VERIFY.digest_value(evidence),
        "encryption_status": "unavailable",
    }


def _read_private_json(path: Path) -> dict:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) & 0o077):
            raise VERIFY.SafetyError("私有状态文件 identity 不安全")
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > 16 * 1024 * 1024:
                raise VERIFY.SafetyError("私有状态文件超过 16 MiB 上限")
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    value = json.loads(b"".join(chunks).decode("utf-8"))
    if not isinstance(value, dict):
        raise VERIFY.SafetyError("私有状态必须是 JSON object")
    return value


def _plan_with_context(plan: dict, *, run_id: str, journey: str, stage: str) -> dict:
    plan = dict(plan)
    plan.update({"run_id": run_id, "journey": journey, "plan_stage": stage})
    plan.setdefault("schema_version", 1)
    plan.setdefault("plan_id", f"plan-{run_id}-{stage}")
    plan.setdefault("generated_at", dt.datetime.now(dt.timezone.utc).isoformat())
    plan["plan_digest"] = _plan_digest(plan)
    return plan


def _execute_macos_open(action: str, value: str) -> None:
    if sys.platform != "darwin":
        raise VERIFY.SafetyError("open-source/open-app v0.1 只支持 macOS host adapter")
    executable = Path("/usr/bin/open")
    info = executable.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) & 0o022):
        raise VERIFY.SafetyError("macOS open executable identity 不安全")
    arguments = [str(executable), value] if action == "open-source" else [str(executable), "-b", value]
    result = subprocess.run(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, check=False)
    if result.returncode != 0:
        raise VERIFY.SafetyError(f"host tool action 执行失败：{result.stderr.strip()}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    tool_probe = commands.add_parser("tool-probe")
    tool_probe.add_argument("--scope", choices=("host", "vault"), required=True)
    tool_probe.add_argument("--target")
    tool_probe.add_argument("--input")
    _json_argument(tool_probe)

    tool_plan = commands.add_parser("tool-plan")
    tool_plan.add_argument("--from-probe", required=True)
    _json_argument(tool_plan)

    tool_choice = commands.add_parser("tool-choice-update")
    tool_choice.add_argument("--run-id", required=True)
    tool_choice.add_argument("--input", required=True)
    _state_argument(tool_choice)
    _json_argument(tool_choice)

    tool_action = commands.add_parser("tool-action-plan")
    tool_action.add_argument("--run-id", required=True)
    tool_action.add_argument("--tool", choices=("git", "workbuddy", "obsidian"), required=True)
    tool_action.add_argument("--action", choices=("open-source", "open-app"), required=True)
    _json_argument(tool_action)

    tool_evidence = commands.add_parser("tool-evidence-update")
    tool_evidence.add_argument("--run-id", required=True)
    tool_evidence.add_argument("--input", required=True)
    _state_argument(tool_evidence)
    _json_argument(tool_evidence)

    tool_verify = commands.add_parser("tool-verify")
    tool_verify.add_argument("--plan", required=True)
    tool_verify.add_argument("--choices")
    _json_argument(tool_verify)

    probe = commands.add_parser("probe")
    probe.add_argument("--target", required=True)
    _json_argument(probe)

    plan = commands.add_parser("plan")
    plan.add_argument("--target")
    plan.add_argument("--run-id")
    plan.add_argument("--input")
    plan.add_argument("--journey", choices=("create", "verify", "adopt-existing"), required=True)
    plan.add_argument("--stage", choices=("scaffold", "personalize", "environment", "inventory"), required=True)
    plan.add_argument("--git-executable")
    plan.add_argument("--use-parent-repo", action="store_true")
    _state_argument(plan)
    _json_argument(plan)

    interview = commands.add_parser("interview-update")
    interview.add_argument("--run-id", required=True)
    interview.add_argument("--input", required=True)
    interview.add_argument("--target")
    _state_argument(interview)
    _json_argument(interview)

    authorize = commands.add_parser("authorize")
    authorize.add_argument("--plan", required=True)
    authorize.add_argument("--approve", action="append", required=True)
    _json_argument(authorize)

    apply = commands.add_parser("apply")
    apply.add_argument("--plan", required=True)
    apply.add_argument("--authorization", required=True)
    apply.add_argument("--input")
    _state_argument(apply)
    _json_argument(apply)

    verify = commands.add_parser("verify")
    verify.add_argument("--target", required=True)
    verify.add_argument("--activation-evidence", action="append", default=[])
    _json_argument(verify)

    resume = commands.add_parser("resume")
    resume.add_argument("--run-id", required=True)
    _state_argument(resume)
    _json_argument(resume)

    recover_plan = commands.add_parser("recover-plan")
    recover_plan.add_argument("--run-id", required=True)
    recover_plan.add_argument("--receipt")
    _state_argument(recover_plan)
    _json_argument(recover_plan)

    recover = commands.add_parser("recover")
    recover.add_argument("--plan", required=True)
    recover.add_argument("--authorization", required=True)
    _json_argument(recover)

    cleanup_plan = commands.add_parser("cleanup-plan")
    cleanup_plan.add_argument("--run-id", required=True)
    cleanup_plan.add_argument("--scope", choices=("interview", "all"), required=True)
    cleanup_plan.add_argument("--acknowledge-recovery-loss", action="store_true")
    _state_argument(cleanup_plan)
    _json_argument(cleanup_plan)

    cleanup = commands.add_parser("cleanup")
    cleanup.add_argument("--plan", required=True)
    cleanup.add_argument("--authorization", required=True)
    _json_argument(cleanup)
    return root


def create_plan(probe: dict) -> dict:
    if probe["shape"] not in {"missing", "empty"}:
        raise VERIFY.SafetyError("非空目录不能进入 create；请使用 adopt-existing")
    core = {
        "plan_schema_version": 1,
        "journey": "create",
        "plan_stage": "scaffold",
        "subject_kind": "vault",
        "target_identity_digest": probe["identity_digest"],
        "probe_snapshot_digest": probe["snapshot_digest"],
        "starter_manifest": "manifests/starter-v1.json",
        "operations": [],
        "claim_ceiling": "planned",
    }
    return {**core, "plan_digest": VERIFY.digest_value(core)}


def execute(args: argparse.Namespace) -> dict:
    if args.command == "tool-probe":
        if args.scope == "vault":
            if not args.target:
                raise VERIFY.SafetyError("vault scope 需要 --target")
            return {"command_outcome": "success", "readiness": tool_probe_vault(
                Path(args.target), selected_target=Path(args.target))}
        evidence = _read_json_input(args.input) if args.input else {}
        readiness = tool_probe_host(
            platform=evidence.get("platform", "macos"),
            python_evidence=evidence.get("python_evidence", {"status": "detected", "official_verified": False}),
            git_evidence=evidence.get("git_evidence", {
                "status": "detected" if shutil.which("git") else "missing", "official_verified": False}),
            app_evidence=evidence.get("app_evidence", {}),
        )
        outcome = "success" if readiness.get("path_confirmation_ready") else "action_required"
        return {"command_outcome": outcome, "readiness": readiness}
    if args.command == "tool-plan":
        payload = _read_json_input(args.from_probe)
        readiness = _unwrap(payload, "readiness")
        _load_contract_module().validate_contract("tool-readiness", readiness)
        return {"command_outcome": "success", "plan": build_tool_plan(readiness)}
    if args.command == "tool-choice-update":
        choice = _read_json_input(args.input)
        events: list[dict] = []
        choices: dict[str, dict] = {}
        run_root = _run_state_root(_state_dir(args.state_dir), args.run_id)
        try:
            stored = _read_private_json(run_root / "tool-choices.json")
        except FileNotFoundError:
            stored = {}
        events = stored.get("events", [])
        choices = stored.get("choices", {})
        if not isinstance(events, list) or not isinstance(choices, dict):
            raise VERIFY.SafetyError("tool choice state 形状不安全")
        if len(events) >= 1024 and not any(
                event.get("idempotency_key") == choice["idempotency_key"] for event in events):
            return {"command_outcome": "action_required", "run_id": args.run_id,
                    "reason": "tool choice event 已达到 1024 条上限，请先 cleanup"}
        events = record_tool_choice(events, choice, run_id=args.run_id)
        choice_summary = dict(choice)
        choices[choice["tool_id"]] = choice_summary
        VERIFY.write_private_json(run_root, "tool-choices.json", {
            "events": events, "choices": choices,
        }, None)
        return {"command_outcome": "success", "run_id": args.run_id,
                "choice": choice_summary, "events": events}
    if args.command == "tool-action-plan":
        identity = _tool_identity(args.tool)
        if args.action == "open-app" and identity["kind"] != "app":
            raise VERIFY.SafetyError("CLI 工具不支持 open-app")
        value = identity["official_url"] if args.action == "open-source" else identity["app_identity"]["bundle_id"]
        plan = build_host_tool_plan(args.tool, VERIFY.digest_value(identity), args.action, value)
        return {"command_outcome": "success", "plan": _plan_with_context(
            plan, run_id=args.run_id, journey="create", stage="tool_prepare")}
    if args.command == "tool-evidence-update":
        evidence = _read_json_input(args.input)
        evidence_summary = record_tool_evidence(evidence)
        run_root = _run_state_root(_state_dir(args.state_dir), args.run_id)
        try:
            stored = _read_private_json(run_root / "tool-evidence.json")
        except FileNotFoundError:
            stored = {}
        observations = stored.get("observations", [])
        if not isinstance(observations, list):
            raise VERIFY.SafetyError("tool evidence state 形状不安全")
        if len(observations) >= 1024 and evidence_summary not in observations:
            return {"command_outcome": "action_required", "run_id": args.run_id,
                    "reason": "tool evidence 已达到 1024 条上限，请先 cleanup"}
        if evidence_summary not in observations:
            observations.append(evidence_summary)
        VERIFY.write_private_json(run_root, "tool-evidence.json", {
            "observations": observations,
        }, None)
        return {"command_outcome": "success", "run_id": args.run_id,
                "evidence": evidence_summary}
    if args.command == "tool-verify":
        plan = _unwrap(_read_json_input(args.plan), "plan")
        if (_plan_digest(plan) != plan.get("plan_digest")
                or plan.get("identity_manifest_digest") != _tool_manifest()["manifest_digest"]):
            return {"command_outcome": "plan_stale"}
        readiness = plan.get("readiness")
        if not isinstance(readiness, dict):
            raise VERIFY.SafetyError("tool plan 缺少 readiness")
        choices = _read_json_input(args.choices) if args.choices else {}
        return verify_tool_readiness(readiness, choices)
    if args.command == "probe":
        return {"command_outcome": "success", "probe": VERIFY.probe_target(args.target)}
    if args.command == "authorize":
        plan = _unwrap(_read_json_input(args.plan), "plan")
        contracts = _load_contract_module()
        contracts.validate_contract("bootstrap-plan", plan)
        authorization = authorize_plan(plan, args.approve)
        contracts.validate_authorization_binding(plan, authorization)
        return {"command_outcome": "success", "authorization": authorization}
    if args.command == "interview-update":
        renderer = _load_render_module()
        answer = _read_json_input(args.input)
        stored = None
        run_root = _run_state_root(_state_dir(args.state_dir), args.run_id)
        state_path = run_root / "interview.json"
        if state_path.exists():
            stored = _read_private_json(state_path)
        target_raw = args.target or (stored or {}).get("target")
        if not target_raw:
            raise VERIFY.SafetyError("首次持久化 interview 需要 --target")
        storage = _unknown_state_storage(run_root.parent, Path(target_raw))
        stored_storage = (stored or {}).get("interview", {}).get("storage")
        if stored_storage is not None and stored_storage != storage:
            return {"command_outcome": "plan_stale", "run_id": args.run_id,
                    "reason": "state root identity 或 storage classification 已漂移"}
        session = renderer.InterviewSession.resume(
            args.run_id, (stored or {}).get("interview", {}), storage=storage)
        try:
            session.update(answer)
        except renderer.InterviewError as error:
            return {"command_outcome": "action_required", "run_id": args.run_id, "reason": str(error)}
        VERIFY.write_private_json(run_root, "interview.json", {
            "target": str(VERIFY.normalize_target_path(target_raw)),
            "interview": session.persistable_state(),
        }, Path(target_raw))
        return {"command_outcome": "success", "run_id": args.run_id,
                "interview": session.public_state(), "summary": session.summary()}
    if args.command == "apply":
        plan = _unwrap(_read_json_input(args.plan), "plan")
        authorization = _unwrap(_read_json_input(args.authorization), "authorization")
        _load_contract_module().validate_authorization_binding(plan, authorization)
        kinds = {operation["kind"] for operation in plan.get("operations", [])}
        if kinds == {"copy-starter"}:
            result = apply_scaffold(plan, authorization)
            if plan.get("run_id") and result.get("created_files"):
                run_root = _run_state_root(_state_dir(args.state_dir), plan["run_id"])
                recovery_target = result.get("staging_path") or plan["normalized_path"]
                receipt_probe = VERIFY.probe_target(recovery_target)
                VERIFY.write_private_json(run_root, "scaffold-receipt.json", {
                    "target": recovery_target,
                    "requested_target": plan["normalized_path"],
                    "target_identity_digest": receipt_probe["identity_digest"],
                    "starter_manifest_digest": plan["starter_manifest_digest"],
                    "apply_outcome": result["command_outcome"],
                    "created_files": result["created_files"],
                },
                    Path(plan["normalized_path"]))
            return result
        if kinds == {"render-profile"}:
            if not _authorization_valid(plan, authorization):
                return {"command_outcome": "action_required"}
            current_probe = VERIFY.probe_target(plan["normalized_path"])
            if (current_probe["identity_digest"] != plan.get("target_identity_digest")
                    or current_probe["snapshot_digest"] != plan.get("probe_snapshot_digest")):
                return {"command_outcome": "plan_stale"}
            stored = None
            current_storage = None
            if plan.get("state_binding"):
                if not plan.get("run_id"):
                    return {"command_outcome": "action_required",
                            "reason": "该 personalize plan 缺少 run-id"}
                try:
                    run_root = _existing_run_state_root(_state_dir(args.state_dir), plan["run_id"])
                    stored = _read_private_json(run_root / "interview.json")
                except FileNotFoundError:
                    return {"command_outcome": "plan_stale"}
                stored_storage = stored.get("interview", {}).get("storage", {})
                current_storage = _unknown_state_storage(run_root.parent, Path(stored["target"]))
                binding = plan["state_binding"]
                if (stored_storage != current_storage
                        or binding.get("state_root_identity_digest") != current_storage["identity_digest"]
                        or binding.get("storage_domain") != current_storage["storage_domain"]
                        or binding.get("encryption_receipt_digest")
                        != current_storage.get("encryption_receipt_digest")):
                    return {"command_outcome": "plan_stale"}
            if args.input:
                answers = _read_json_input(args.input)
            elif plan.get("run_id"):
                if stored is None:
                    try:
                        run_root = _existing_run_state_root(_state_dir(args.state_dir), plan["run_id"])
                        stored = _read_private_json(run_root / "interview.json")
                    except FileNotFoundError:
                        return {"command_outcome": "plan_stale"}
                    current_storage = stored.get("interview", {}).get("storage")
                answers = _load_render_module().InterviewSession.resume(
                    plan["run_id"], stored.get("interview", {}),
                    storage=current_storage).confirmed_answers()
            else:
                return {"command_outcome": "action_required", "reason": "personalize apply 需要 --input 或 --state-dir"}
            if VERIFY.digest_value(answers) != plan.get("answers_digest"):
                return {"command_outcome": "plan_stale"}
            renderer = _load_render_module()
            rendered = renderer.render_profile(answers)
            expected_operations = [{
                "operation_id": f"personalize:{path}",
                "kind": "render-profile",
                "relative_path": path,
                "content_digest": VERIFY.digest_value(entry["content"]),
            } for path, entry in sorted(rendered.items())]
            if plan.get("operations") != expected_operations:
                return {"command_outcome": "plan_stale"}
            return {"command_outcome": "success", **renderer.apply_rendered_profile(
                Path(plan["normalized_path"]), rendered)}
        git_kinds = {"git-init", "git-local-identity", "git-add", "git-baseline-commit"}
        if kinds and kinds <= git_kinds:
            identity = None
            if args.input:
                identity_payload = _read_json_input(args.input)
                if set(identity_payload) != {"name", "email"}:
                    raise VERIFY.SafetyError("Git local identity 输入只允许 name/email")
                identity = (identity_payload["name"], identity_payload["email"])
            return apply_git_baseline(plan, authorization, local_identity=identity)
        if kinds in ({"open-source"}, {"open-app"}):
            return apply_host_tool(plan, authorization, _execute_macos_open)
        return {"command_outcome": "action_required", "reason": "该 plan kind 需要宿主 adapter 执行"}
    if args.command == "verify":
        probe = VERIFY.probe_target(args.target)
        if probe["shape"] == "missing":
            raise VERIFY.SafetyError("verify 目标不存在")
        evidence = []
        for raw in args.activation_evidence:
            relative = PurePosixPath(raw)
            if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != raw:
                raise VERIFY.SafetyError("activation evidence 必须是 Vault 相对路径")
            candidate = Path(args.target) / raw
            if candidate.is_symlink() or not candidate.is_file():
                raise VERIFY.SafetyError("activation evidence 必须是目标内普通文件")
            evidence.append(raw)
        return {"command_outcome": "success", "probe": probe,
                "inventory": VERIFY.inventory_vault(Path(args.target)), "activation_evidence": evidence}
    if args.command == "resume":
        try:
            run_root = _existing_run_state_root(_state_dir(args.state_dir), args.run_id)
        except FileNotFoundError:
            return {"command_outcome": "action_required", "reason": "未知或不可恢复的 run"}
        result = {"command_outcome": "success", "run_id": args.run_id, "phase": "tool_prepare"}
        try:
            choices = _read_private_json(run_root / "tool-choices.json")
        except FileNotFoundError:
            choices = None
        if choices is not None:
            result["tool_choices"] = choices.get("choices", {})
        try:
            evidence = _read_private_json(run_root / "tool-evidence.json")
        except FileNotFoundError:
            evidence = None
        if evidence is not None:
            result["tool_evidence"] = evidence.get("observations", [])
        try:
            scaffold = _read_private_json(run_root / "scaffold-receipt.json")
        except FileNotFoundError:
            scaffold = None
        if scaffold is not None:
            current = VERIFY.probe_target(scaffold["target"])
            if (current["identity_digest"] != scaffold.get("target_identity_digest")
                    or VERIFY.digest_value(_starter_manifest()) != scaffold.get("starter_manifest_digest")):
                return {"command_outcome": "plan_stale", "run_id": args.run_id,
                        "reason": "scaffold target 或 source 已漂移"}
            for item in scaffold.get("created_files", []):
                raw = item.get("path", "")
                relative = PurePosixPath(raw)
                if (not raw or relative.is_absolute() or ".." in relative.parts
                        or relative.as_posix() != raw or "\\" in raw):
                    return {"command_outcome": "plan_stale", "run_id": args.run_id,
                            "reason": "scaffold receipt 路径不安全"}
                candidate = Path(scaffold["target"]) / raw
                if candidate.is_symlink() or not candidate.is_file():
                    return {"command_outcome": "plan_stale", "run_id": args.run_id,
                            "reason": "scaffold 文件缺失或身份漂移"}
                if item.get("ownership") != "append-only" and _sha256(candidate) != item.get("sha256"):
                    return {"command_outcome": "plan_stale", "run_id": args.run_id,
                            "reason": "scaffold 文件内容漂移"}
            result.update({"phase": "scaffold", "probe": current,
                           "scaffold_outcome": scaffold.get("apply_outcome")})
        try:
            stored = _read_private_json(run_root / "interview.json")
        except FileNotFoundError:
            stored = None
        if stored is not None:
            current = VERIFY.probe_target(stored["target"])
            result.update({"phase": "personalize", "probe": current,
                           "interview": _load_render_module().InterviewSession.resume(
                               args.run_id, stored.get("interview", {})).public_state()})
        if len(result) == 3:
            return {"command_outcome": "action_required", "run_id": args.run_id,
                    "reason": "run state 不含可恢复内容"}
        return result
    if args.command == "recover-plan":
        if args.receipt:
            receipt = _read_json_input(args.receipt)
        else:
            try:
                run_root = _existing_run_state_root(_state_dir(args.state_dir), args.run_id)
                receipt = _read_private_json(run_root / "scaffold-receipt.json")
            except FileNotFoundError:
                return {"command_outcome": "action_required", "reason": "未知或不可恢复的 run"}
        operations = [{**item, "operation_id": f"recover:{item['path']}", "kind": "recover-file"}
                      for item in receipt.get("created_files", []) if item.get("ownership") != "append-only"]
        if not operations:
            return {"command_outcome": "action_required", "reason": "没有可自动恢复的 pre-baseline 文件"}
        recovery_root = VERIFY.normalize_target_path(receipt["target"])
        requested_target = VERIFY.normalize_target_path(receipt.get("requested_target", receipt["target"]))
        staging_name = f".{requested_target.name}.twinmind-stage-"
        remove_root_if_empty = (recovery_root.parent == requested_target.parent
                                and recovery_root.name.startswith(staging_name))
        recovery_probe = VERIFY.probe_target(recovery_root)
        plan = {"subject_kind": "recovery", "subject_identity_digest": VERIFY.digest_value({
            "run_id": args.run_id, "target": str(recovery_root)}), "run_id": args.run_id,
            "normalized_path": str(recovery_root), "requested_target": str(requested_target),
            "recovery_root_identity_digest": recovery_probe["identity_digest"],
            "remove_root_if_empty": remove_root_if_empty,
            "recovery_mode": "pre_baseline_delete", "operations": operations}
        return {"command_outcome": "success", "plan": _plan_with_context(
            plan, run_id=args.run_id, journey="create", stage="recovery")}
    if args.command == "recover":
        plan = _unwrap(_read_json_input(args.plan), "plan")
        authorization = _unwrap(_read_json_input(args.authorization), "authorization")
        _load_contract_module().validate_authorization_binding(plan, authorization)
        if not _authorization_valid(plan, authorization):
            return {"command_outcome": "action_required"}
        if plan.get("recovery_mode") != "pre_baseline_delete":
            return {"command_outcome": "action_required", "reason": "baseline 后恢复需要 Git adapter"}
        recovery_root = Path(plan["normalized_path"])
        current_probe = VERIFY.probe_target(recovery_root)
        if current_probe["identity_digest"] != plan.get("recovery_root_identity_digest"):
            return {"command_outcome": "plan_stale"}
        created = [{key: operation[key] for key in ("path", "sha256", "ownership", "operation_id")}
                   for operation in plan["operations"]]
        result = recover_pre_baseline(recovery_root, created)
        removed_root = False
        if plan.get("remove_root_if_empty") and not result["preserved_paths"]:
            requested_target = Path(plan["requested_target"])
            expected_prefix = f".{requested_target.name}.twinmind-stage-"
            if (recovery_root.parent != requested_target.parent
                    or not recovery_root.name.startswith(expected_prefix)
                    or VERIFY.probe_target(recovery_root)["identity_digest"]
                    != plan.get("recovery_root_identity_digest")):
                return {**result, "command_outcome": "plan_stale"}
            try:
                recovery_root.rmdir()
            except OSError:
                pass
            else:
                removed_root = True
        return {**result, "removed_staging_root": removed_root}
    if args.command == "cleanup-plan":
        try:
            state_root = _prepare_state_root(_state_dir(args.state_dir), create=False)
            cleanup_plan = build_cleanup_plan(
                state_root, args.run_id, args.scope, args.acknowledge_recovery_loss)
        except FileNotFoundError:
            return {"command_outcome": "action_required", "reason": "未知或不可恢复的 run"}
        return {"command_outcome": "success", "plan": _plan_with_context(
            cleanup_plan, run_id=args.run_id, journey="create", stage="cleanup")}
    if args.command == "cleanup":
        plan = _unwrap(_read_json_input(args.plan), "plan")
        authorization = _unwrap(_read_json_input(args.authorization), "authorization")
        _load_contract_module().validate_authorization_binding(plan, authorization)
        return apply_cleanup(plan, authorization)
    target_argument = args.target
    stored_interview = None
    if (args.command == "plan" and args.journey == "create" and args.stage == "personalize"
            and not target_argument and args.run_id):
        try:
            run_root = _existing_run_state_root(_state_dir(args.state_dir), args.run_id)
            stored_interview = _read_private_json(run_root / "interview.json")
        except FileNotFoundError:
            return {"command_outcome": "action_required", "reason": "未知或不可恢复的 run"}
        target_argument = stored_interview.get("target")
        current_storage = _unknown_state_storage(run_root.parent, Path(target_argument))
        if stored_interview.get("interview", {}).get("storage") != current_storage:
            return {"command_outcome": "plan_stale",
                    "reason": "state root identity 或 storage classification 已漂移"}
    if not target_argument:
        raise VERIFY.SafetyError("该 plan stage 需要 --target 或可恢复 state")
    probe = VERIFY.probe_target(target_argument)
    if args.journey == "create":
        run_id = args.run_id or f"run-{probe['identity_digest'][:16]}"
        if args.stage == "scaffold":
            return {"command_outcome": "success", "plan": _plan_with_context(
                build_scaffold_plan(Path(target_argument)), run_id=run_id, journey="create", stage="scaffold")}
        if args.stage == "personalize":
            state_storage = None
            if args.input:
                answers = _read_json_input(args.input)
            elif stored_interview:
                state_storage = stored_interview.get("interview", {}).get("storage")
                answers = _load_render_module().InterviewSession.resume(
                    run_id, stored_interview.get("interview", {}),
                    storage=state_storage).confirmed_answers()
            else:
                return {"command_outcome": "action_required", "reason": "personalize plan 需要 --input 或可恢复 state"}
            return {"command_outcome": "success", "plan": _plan_with_context(
                build_personalize_plan(run_id, Path(target_argument), answers, state_storage),
                run_id=run_id, journey="create", stage="personalize")}
        if args.stage == "environment":
            git_executable = args.git_executable or shutil.which("git")
            if not git_executable:
                return {"command_outcome": "action_required", "reason": "Git executable 未提供"}
            git_plan = _plan_with_context(
                build_git_baseline_plan(Path(target_argument), git_executable, args.use_parent_repo),
                run_id=run_id, journey="create", stage="environment")
            outcome = "action_required" if git_plan.get("command_outcome") == "action_required" else "success"
            return {"command_outcome": outcome, "plan": git_plan}
        raise VERIFY.SafetyError("create 不支持该 plan stage")
    if probe["shape"] != "nonempty":
        raise VERIFY.SafetyError("verify/adopt-existing 需要非空目录")
    storage = {"identity_digest": "0" * 64, "storage_domain": "unknown", "classification_evidence_digest": "0" * 64}
    run_id = args.run_id or f"run-{probe['identity_digest'][:16]}"
    return {"command_outcome": "success", "plan": _plan_with_context(
        VERIFY.build_readonly_plan(probe, args.journey, storage),
        run_id=run_id, journey=args.journey, stage="inventory")}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = execute(args)
    except VERIFY.InventoryBudgetError as error:
        print(json.dumps({"command_outcome": "action_required", "reason": str(error)}, ensure_ascii=False), file=sys.stdout)
        return 2
    except VERIFY.SafetyError as error:
        print(json.dumps({"command_outcome": "unsafe_target", "reason": str(error)}, ensure_ascii=False), file=sys.stdout)
        return 4
    except Exception as error:
        print(json.dumps({"command_outcome": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stdout)
        return 1
    outcome = result.get("inventory", {}).get("command_outcome", result["command_outcome"])
    result["command_outcome"] = outcome
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return {
        "success": 0, "no_changes": 0, "degraded": 0, "action_required": 2,
        "conflict": 3, "unsafe_target": 4, "plan_stale": 5, "partial": 6,
        "failed": 1,
    }.get(outcome, 1)


if __name__ == "__main__":
    raise SystemExit(main())
