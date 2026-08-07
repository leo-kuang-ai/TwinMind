#!/usr/bin/env python3
"""TwinMind Vault 的只读探测、快照与有界 inventory。"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import time
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Callable


SKILL_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = SKILL_ROOT / "manifests" / "inventory-policies-v1.json"
STARTER_MANIFEST_PATH = SKILL_ROOT / "manifests" / "starter-v1.json"
LIMIT_IDS = (
    "entries", "depth", "single_file_bytes", "cumulative_read_bytes",
    "elapsed_seconds", "report_bytes", "open_file_descriptors", "filesystem_boundary",
)


class SafetyError(ValueError):
    pass


class InventoryBudgetError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def canonical_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def canonical_limits() -> dict[str, Any]:
    return dict(canonical_policy()["policies"][0]["limits"])


def policy_digest() -> str:
    return digest_value(canonical_policy())


def normalize_target_path(raw: str | os.PathLike[str]) -> Path:
    text = os.fspath(raw)
    if not text or any(token in text for token in ("$", "*", "?", "[", "]")) or text.startswith("~"):
        raise SafetyError("目标路径含未解析环境变量、通配符或主目录缩写")
    normalized = unicodedata.normalize("NFC", text)
    path = Path(normalized)
    if not path.is_absolute():
        path = Path.cwd() / path
    if path == Path.home() or path == Path("/"):
        raise SafetyError("不得把主目录或系统根目录作为目标")
    if path.is_symlink():
        raise SafetyError("目标路径不得是符号链接")
    return path.resolve(strict=False)


def _sha256_file_counted(path: Path, expected: os.stat_result | None = None,
                         max_bytes: int | None = None) -> tuple[str | None, int, bool]:
    digest = hashlib.sha256()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    total = 0
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise SafetyError("读取目标不是普通文件")
        if expected is not None and (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino):
            raise SafetyError("读取目标在 lstat/open 之间发生替换")
        while True:
            remaining = 1024 * 1024 if max_bytes is None else min(1024 * 1024, max_bytes - total + 1)
            if remaining <= 0:
                return None, total, True
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            total += len(chunk)
            if max_bytes is not None and total > max_bytes:
                return None, total, True
            digest.update(chunk)
        final = os.fstat(descriptor)
        if ((final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
                != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)):
            raise SafetyError("读取目标在哈希期间发生漂移")
    finally:
        os.close(descriptor)
    return digest.hexdigest(), total, False


def _sha256_file(path: Path, expected: os.stat_result | None = None) -> str:
    digest, _, overflow = _sha256_file_counted(path, expected)
    if overflow or digest is None:
        raise SafetyError("普通文件哈希读取异常")
    return digest


def read_regular_bytes(path: Path, maximum: int = 8 * 1024 * 1024) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size > maximum:
            raise SafetyError("读取目标不是有界单链接普通文件")
        data = bytearray()
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, maximum - len(data) + 1))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > maximum:
                raise SafetyError("读取目标在读取期间超过上限")
        final = os.fstat(descriptor)
        if ((final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
                != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)):
            raise SafetyError("读取目标在读取期间发生漂移")
        return bytes(data)
    finally:
        os.close(descriptor)


def snapshot_tree(root: Path) -> dict[str, Any]:
    root = normalize_target_path(root)
    if not root.is_dir():
        raise SafetyError("快照目标必须是已存在目录")
    entries: list[dict[str, Any]] = []
    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directory_names.sort()
        file_names.sort()
        for name in [*directory_names, *file_names]:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            info = path.lstat()
            item = {
                "path": relative,
                "mode": stat.S_IMODE(info.st_mode),
                "mtime_ns": info.st_mtime_ns,
            }
            if stat.S_ISLNK(info.st_mode):
                item.update({"type": "symlink", "link_text": os.readlink(path)})
            elif stat.S_ISDIR(info.st_mode):
                item.update({"type": "directory"})
            elif stat.S_ISREG(info.st_mode):
                item.update({"type": "file", "size": info.st_size, "sha256": _sha256_file(path, info)})
            else:
                item.update({"type": "other"})
            entries.append(item)
    return {"entries": entries, "digest": digest_value(entries)}


def _relative(path: Path, root: Path) -> str:
    value = path.relative_to(root).as_posix()
    if PurePosixPath(value).is_absolute() or ".." in PurePosixPath(value).parts:
        raise SafetyError("inventory 产生越界路径")
    return value


def _symlink_inventory_metadata(path: Path) -> dict[str, Any]:
    raw = os.readlink(path)
    return {
        "type": "symlink",
        "link_text_kind": "absolute" if Path(raw).is_absolute() else "relative",
        "link_text_sha256": hashlib.sha256(raw.encode("utf-8", errors="surrogateescape")).hexdigest(),
    }


def inventory_vault(
    root: Path,
    *,
    effective_limits: dict[str, Any] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    device_for: Callable[[Path, os.stat_result], int] | None = None,
) -> dict[str, Any]:
    root = normalize_target_path(root)
    if not root.is_dir():
        raise SafetyError("inventory 目标必须是目录")
    canonical = canonical_limits()
    limits = dict(canonical if effective_limits is None else effective_limits)
    if set(limits) != set(canonical):
        raise SafetyError("effective limits 必须包含完整八项预算")
    for key, value in canonical.items():
        if key == "cross_filesystems":
            if value is False and limits[key] is not False:
                raise SafetyError("不得放宽文件系统边界")
        elif limits[key] > value or limits[key] < 0:
            raise SafetyError(f"effective {key} 只能收紧")

    start = monotonic()
    root_device = root.stat().st_dev
    observed = {"entries": 0, "bytes_read": 0, "max_depth": 0, "elapsed_seconds": 0.0,
                "peak_open_file_descriptors": 0, "skipped": 0, "errors": 0}
    items: list[dict[str, Any]] = []
    limit_hit: str | None = None
    stop_path = "."

    def hit(limit_id: str, relative: str) -> bool:
        nonlocal limit_hit, stop_path
        limit_hit, stop_path = limit_id, relative
        return True

    def report_shape(candidate_items: list[dict[str, Any]], candidate_limit: str | None,
                     candidate_stop: str, candidate_observed: dict[str, Any]) -> dict[str, Any]:
        incomplete = candidate_limit is not None
        return {
            "policy_id": "personal-vault-v1",
            "policy_digest": policy_digest(),
            "canonical_limits": canonical,
            "effective_limits": limits,
            "inventory_status": "incomplete" if incomplete else "complete",
            "command_outcome": "action_required" if incomplete else "success",
            "limit_hit": candidate_limit,
            "stop_relative_path": candidate_stop,
            "observed": candidate_observed,
            "items": candidate_items,
            "next_action": "缩小目标范围后重新规划" if incomplete else "继续只读验证",
        }

    minimum_report = report_shape([], "report_bytes", ".", dict(observed))
    if len(canonical_json_bytes(minimum_report)) > limits["report_bytes"]:
        raise InventoryBudgetError("effective report_bytes 小于最小安全报告 envelope")

    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directory_names.sort()
        file_names.sort()
        names = [(name, True) for name in directory_names] + [(name, False) for name in file_names]
        for name, is_directory in names:
            path = current_path / name
            relative = _relative(path, root)
            depth = len(PurePosixPath(relative).parts)
            elapsed = monotonic() - start
            if observed["entries"] + 1 > limits["entries"] and hit("entries", relative):
                break
            if depth > limits["depth"] and hit("depth", relative):
                break
            if elapsed > limits["elapsed_seconds"] and hit("elapsed_seconds", relative):
                break
            info = path.lstat()
            observed_device = info.st_dev if device_for is None else device_for(path, info)
            if not limits["cross_filesystems"] and observed_device != root_device and hit("filesystem_boundary", relative):
                break
            observed["entries"] += 1
            observed["max_depth"] = max(observed["max_depth"], depth)
            if stat.S_ISLNK(info.st_mode):
                item = {"path": relative, **_symlink_inventory_metadata(path)}
            elif is_directory and stat.S_ISDIR(info.st_mode):
                item = {"path": relative, "type": "directory"}
            elif stat.S_ISREG(info.st_mode):
                if info.st_size > limits["single_file_bytes"] and hit("single_file_bytes", relative):
                    break
                if observed["bytes_read"] + info.st_size > limits["cumulative_read_bytes"] and hit("cumulative_read_bytes", relative):
                    break
                if 1 > limits["open_file_descriptors"] and hit("open_file_descriptors", relative):
                    break
                observed["peak_open_file_descriptors"] = max(observed["peak_open_file_descriptors"], 1)
                remaining_bytes = limits["cumulative_read_bytes"] - observed["bytes_read"]
                maximum_read = min(limits["single_file_bytes"], remaining_bytes)
                file_digest, actual_bytes, overflow = _sha256_file_counted(path, info, maximum_read)
                if overflow:
                    limiting = "single_file_bytes" if limits["single_file_bytes"] <= remaining_bytes else "cumulative_read_bytes"
                    hit(limiting, relative)
                    break
                observed["bytes_read"] += actual_bytes
                item = {"path": relative, "type": "file", "size": actual_bytes, "sha256": file_digest}
            else:
                item = {"path": relative, "type": "other"}
            candidate = [*items, item]
            provisional = report_shape(candidate, None, ".", dict(observed))
            if len(canonical_json_bytes(provisional)) > limits["report_bytes"] and hit("report_bytes", relative):
                break
            items.append(item)
        if limit_hit:
            directory_names[:] = []
            break
    observed["elapsed_seconds"] = max(0.0, monotonic() - start)
    report = report_shape(items, limit_hit, stop_path, observed)
    while items and len(canonical_json_bytes(report)) > limits["report_bytes"]:
        removed = items.pop()
        limit_hit = "report_bytes"
        stop_path = removed["path"]
        report = report_shape(items, limit_hit, stop_path, observed)
    if len(canonical_json_bytes(report)) > limits["report_bytes"] and limit_hit is None:
        report = report_shape([], "report_bytes", stop_path, observed)
    return report


def _find_parent_git(path: Path) -> Path | None:
    start = path if path.exists() and path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def probe_target(raw: str | os.PathLike[str]) -> dict[str, Any]:
    path = normalize_target_path(raw)
    exists = path.exists()
    if exists and not path.is_dir():
        raise SafetyError("目标必须是目录")
    if exists:
        shape = "empty" if not any(path.iterdir()) else "nonempty"
        info = path.stat()
        identity_facts = {"path": unicodedata.normalize("NFC", str(path)), "device": info.st_dev,
                          "inode": info.st_ino, "mode": stat.S_IMODE(info.st_mode)}
    else:
        parent = path.parent
        if not parent.is_dir() or not os.access(parent, os.W_OK):
            raise SafetyError("目标不存在且父目录不可写")
        shape = "missing"
        info = parent.stat()
        identity_facts = {"path": unicodedata.normalize("NFC", str(path)), "parent_device": info.st_dev,
                          "parent_inode": info.st_ino}
    parent_git = _find_parent_git(path)
    return {
        "requested_path": os.fspath(raw),
        "normalized_path": str(path),
        "shape": shape,
        "identity_digest": digest_value(identity_facts),
        "parent_git_detected": parent_git is not None,
        "parent_git_boundary_digest": digest_value(str(parent_git)) if parent_git else None,
        "snapshot_digest": snapshot_tree(path)["digest"] if exists else digest_value([]),
    }


def classify_storage(evidence: dict[str, Any], path_hint: str | None = None) -> str:
    del path_hint
    if evidence.get("sync_provider"):
        return "cloud_synced"
    if evidence.get("mount_kind") == "network":
        return "network"
    if evidence.get("removable") is True:
        return "removable"
    if evidence.get("mount_kind") == "local" and evidence.get("removable") is False:
        return "local_fixed"
    return "unknown"


def validate_state_root(state_root: Path, target: Path | None,
                        expected_uid: int | None = None) -> dict[str, Any]:
    if state_root.is_symlink():
        raise SafetyError("state root 不得是 symlink")
    root = state_root.resolve(strict=True)
    normalized_target = normalize_target_path(target) if target is not None else None
    if (root in {Path("/"), Path.home()}
            or normalized_target is not None and (root == normalized_target or normalized_target in root.parents)):
        raise SafetyError("state root 不得位于目标内部或系统/主目录根")
    info = root.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise SafetyError("state root 必须是目录")
    uid = os.getuid() if expected_uid is None else expected_uid
    if info.st_uid != uid:
        raise SafetyError("state root owner 不匹配")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise SafetyError("state root 权限必须为当前用户私有")
    return {"identity_digest": digest_value({"device": info.st_dev, "inode": info.st_ino, "uid": info.st_uid,
                                              "mode": stat.S_IMODE(info.st_mode)})}


def write_private_json(state_root: Path, relative_name: str, payload: dict[str, Any],
                       target: Path | None) -> Path:
    validate_state_root(state_root, target)
    relative = PurePosixPath(relative_name)
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
        raise SafetyError("state 文件名必须是单层相对路径")
    destination = state_root / relative_name
    if destination.is_symlink():
        raise SafetyError("state 文件不得是 symlink")
    flags = os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    existing = False
    try:
        descriptor = os.open(destination, flags | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing = True
        descriptor = os.open(destination, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_uid != os.getuid() or opened.st_nlink != 1:
            raise SafetyError("state 文件类型、owner 或 link count 不安全")
        if existing and stat.S_IMODE(opened.st_mode) != 0o600:
            raise SafetyError("已有 state 文件权限不安全")
        if not existing:
            os.fchmod(descriptor, 0o600)
        os.ftruncate(descriptor, 0)
        data = canonical_json_bytes(payload)
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    final = destination.lstat()
    if not stat.S_ISREG(final.st_mode) or final.st_nlink != 1 or stat.S_IMODE(final.st_mode) != 0o600:
        raise SafetyError("state 文件写后复核失败")
    return destination


def build_readonly_plan(probe: dict[str, Any], journey: str, storage: dict[str, Any]) -> dict[str, Any]:
    if journey not in {"verify", "adopt-existing"}:
        raise SafetyError("只读 plan 只支持 verify/adopt-existing")
    starter = json.loads(STARTER_MANIFEST_PATH.read_text(encoding="utf-8"))
    core = {
        "plan_schema_version": 1,
        "journey": journey,
        "subject_kind": "vault",
        "subject_identity_digest": probe["identity_digest"],
        "target_identity_digest": probe["identity_digest"],
        "requested_path": probe["requested_path"],
        "normalized_path": probe["normalized_path"],
        "probe_snapshot_digest": probe["snapshot_digest"],
        "parent_git_detected": probe["parent_git_detected"],
        "parent_git_boundary_digest": probe["parent_git_boundary_digest"],
        "starter_version": starter["starter_version"],
        "starter_source_commit": starter["source"]["commit"],
        "starter_source_tree_digest": starter["source"]["tree_digest"],
        "starter_manifest_digest": digest_value(starter),
        "inventory_policy_id": "personal-vault-v1",
        "inventory_policy_digest": policy_digest(),
        "effective_limits": canonical_limits(),
        "state_storage": storage,
        "operations": [],
        "claim_ceiling": "read-only-inventory",
    }
    return {**core, "plan_digest": digest_value(core)}
