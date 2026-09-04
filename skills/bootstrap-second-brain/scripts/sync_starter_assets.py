#!/usr/bin/env python3
"""从 canonical Demo 单向生成并校验 TwinMind Starter Kit 投影。"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "skills" / "bootstrap-second-brain"
SOURCE_ROOT = REPO_ROOT / "我的第二大脑"
ASSET_ROOT = SKILL_ROOT / "assets" / "starter-kit"
STARTER_MANIFEST = SKILL_ROOT / "manifests" / "starter-v1.json"
POLICY_MANIFEST = SKILL_ROOT / "manifests" / "inventory-policies-v1.json"

STARTER_VERSION = "0.2.0"
MANIFEST_SCHEMA_VERSION = "starter-manifest-v1"
POLICY_SCHEMA_VERSION = "inventory-policies-v1"
POLICY_ID = "personal-vault-v1"

MANAGED_BLOCKS = {
    "AI协作协议.md": "ai-collaboration-policy",
    "知识库索引.md": "knowledge-index",
    "10_当前工作台/00_第二大脑启动契约.md": "startup-contract",
}
TOOLING_ADAPTERS = {
    "30_知识主题/第二大脑完整工具清单.md",
    "30_知识主题/工具选择与升级门禁.md",
}
APPEND_ONLY_PATHS = {"维护日志.md"}
ALLOWED_OWNERSHIP = {"static", "generated-once", "managed-block", "append-only", "user-owned"}
ALLOWED_LAYERS = {"portable-core", "tooling-adapter"}

EXCLUSIONS = {
    "exact_paths": [
        "AGENTS.md",
        "99_维护记录/TwinMind Starter 宿主中立化交付记录.md",
        "99_维护记录/TwinMind第二大脑初始化Skill实施交付记录.md",
    ],
    "directory_names": [
        ".git",
        ".obsidian",
        ".twinmind",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
    ],
    "file_globs": [
        ".DS_Store",
        ".env",
        ".env.*",
        "*.key",
        "*.log",
        "*.p12",
        "*.pem",
        "*.pfx",
        "*.swo",
        "*.swp",
        "*.tmp",
    ],
}

EXPECTED_POLICY_LIMITS = {
    "entries": 50_000,
    "depth": 64,
    "single_file_bytes": 1_073_741_824,
    "cumulative_read_bytes": 10_737_418_240,
    "elapsed_seconds": 600,
    "report_bytes": 33_554_432,
    "open_file_descriptors": 32,
    "cross_filesystems": False,
}
EXPECTED_ON_LIMIT = {
    "stop_new_reads": True,
    "inventory_status": "incomplete",
    "command_outcome": "action_required",
}

_MANAGED_BLOCKS = None


def load_managed_blocks_module():
    """加载共享 managed-block 标记模块（标记语法唯一事实源；校验语义仍在本文件）。"""
    global _MANAGED_BLOCKS
    if _MANAGED_BLOCKS is None:
        import importlib.util

        path = Path(__file__).resolve().with_name("managed_blocks.py")
        spec = importlib.util.spec_from_file_location("twinmind_managed_blocks", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("无法加载 managed_blocks.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MANAGED_BLOCKS = module
    return _MANAGED_BLOCKS


MARKER_PATTERN = load_managed_blocks_module().MARKER_PATTERN_STR
TOOL_ROWS = {
    "Python 3.11+": "runtime-required",
    "Git": "product-required",
    "WorkBuddy": "recommended",
    "Obsidian": "recommended",
    "社区插件": "optional",
}
VENDOR_NAMES = r"(?:WorkBuddy|Obsidian|Codex)"
MANDATORY_VENDOR_PATTERNS = [
    re.compile(rf"(?:必须|只能|仅能|务必|要求).{{0,30}}{VENDOR_NAMES}", re.IGNORECASE),
    re.compile(rf"{VENDOR_NAMES}.{{0,30}}(?:才能|才可|唯一|不可替换|必需)", re.IGNORECASE),
]


class ProjectionError(ValueError):
    """表示 canonical、manifest 或投影违反发布合同。"""


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest_path(raw_path: str) -> str:
    if not isinstance(raw_path, str) or not raw_path:
        raise ProjectionError("manifest path 必须是非空字符串")
    if any(ord(character) < 32 or ord(character) == 127 for character in raw_path):
        raise ProjectionError(f"manifest path 含控制字符：{raw_path!r}")
    if "\\" in raw_path:
        raise ProjectionError(f"manifest path 必须使用 POSIX 分隔符：{raw_path!r}")
    path = PurePosixPath(raw_path)
    if path.is_absolute() or raw_path.startswith("/"):
        raise ProjectionError(f"manifest path 不得为绝对路径：{raw_path!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ProjectionError(f"manifest path 含非规范化片段：{raw_path!r}")
    if path.as_posix() != raw_path:
        raise ProjectionError(f"manifest path 未规范化：{raw_path!r}")
    return raw_path


def validate_managed_blocks(text: str, expected_block_id: str) -> None:
    markers = MARKER_PATTERN.findall(text)
    expected = [("START", expected_block_id), ("END", expected_block_id)]
    if markers != expected:
        raise ProjectionError(
            f"受管区块必须恰好为 {expected_block_id} 的一对顺序标记，实际为 {markers}"
        )

    depth = 0
    for marker_type, _ in markers:
        if marker_type == "START":
            if depth:
                raise ProjectionError("受管区块不得嵌套")
            depth = 1
        else:
            if depth != 1:
                raise ProjectionError("受管区块结束标记没有对应开始标记")
            depth = 0
    if depth:
        raise ProjectionError("受管区块没有闭合")


def portable_vendor_violations(text: str) -> list[str]:
    violations: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern in MANDATORY_VENDOR_PATTERNS:
            if pattern.search(line):
                violations.append(f"line {line_number}: {line.strip()}")
                break
    return violations


def validate_effective_limits(canonical: dict[str, Any], effective: dict[str, Any]) -> None:
    if set(effective) != set(canonical):
        raise ProjectionError("effective limits 必须完整保留 canonical 八项键")
    for key, canonical_value in canonical.items():
        effective_value = effective[key]
        if key == "cross_filesystems":
            if canonical_value is False and effective_value is not False:
                raise ProjectionError("run-local policy 不得放宽文件系统边界")
            continue
        if isinstance(effective_value, bool) or not isinstance(effective_value, int):
            raise ProjectionError(f"{key} 必须是整数")
        if effective_value < 0 or effective_value > canonical_value:
            raise ProjectionError(f"run-local {key} 只能收紧，不能高于 canonical")


def validate_inventory_policy(manifest: dict[str, Any]) -> str:
    if manifest.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise ProjectionError("inventory policy schema_version 不匹配")
    policies = manifest.get("policies")
    if not isinstance(policies, list) or len(policies) != 1:
        raise ProjectionError("inventory policy manifest 必须只包含一个 policy")
    policy = policies[0]
    if policy.get("policy_id") != POLICY_ID:
        raise ProjectionError(f"inventory policy 必须为 {POLICY_ID}")
    if policy.get("limits") != EXPECTED_POLICY_LIMITS:
        raise ProjectionError(f"{POLICY_ID} 八项冻结限制发生变化")
    if policy.get("on_limit") != EXPECTED_ON_LIMIT:
        raise ProjectionError("inventory 超限语义必须为 incomplete/action_required 并停止新增读取")
    if manifest.get("effective_limits_rule") != "may-only-tighten":
        raise ProjectionError("run-local effective limits 必须只能逐项收紧")
    validate_effective_limits(EXPECTED_POLICY_LIMITS, EXPECTED_POLICY_LIMITS)
    return sha256_bytes(canonical_json_bytes(manifest))


def path_is_excluded(relative_path: str, *, is_directory: bool) -> bool:
    validate_manifest_path(relative_path)
    if relative_path in EXCLUSIONS["exact_paths"]:
        return True
    path = PurePosixPath(relative_path)
    if is_directory and path.name in EXCLUSIONS["directory_names"]:
        return True
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in EXCLUSIONS["file_globs"])


def inventory_source_files(root: Path) -> list[Path]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ProjectionError(f"canonical source 不是目录：{root}")
    files: list[Path] = []
    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in sorted(directory_names):
            candidate = current_path / name
            relative = candidate.relative_to(root).as_posix()
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ProjectionError(f"canonical source 不得包含 symlink：{relative}")
            if not stat.S_ISDIR(mode):
                raise ProjectionError(f"canonical source 目录项类型异常：{relative}")
            if not path_is_excluded(relative, is_directory=True):
                kept_directories.append(name)
        directory_names[:] = kept_directories

        for name in sorted(file_names):
            candidate = current_path / name
            relative = candidate.relative_to(root).as_posix()
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ProjectionError(f"canonical source 不得包含 symlink：{relative}")
            if not stat.S_ISREG(mode):
                raise ProjectionError(f"canonical source 只允许普通文件：{relative}")
            if path_is_excluded(relative, is_directory=False):
                continue
            files.append(candidate)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def ownership_for(relative_path: str) -> str:
    if relative_path in MANAGED_BLOCKS:
        return "managed-block"
    if relative_path in APPEND_ONLY_PATHS:
        return "append-only"
    return "static"


def layer_for(relative_path: str) -> str:
    return "tooling-adapter" if relative_path in TOOLING_ADAPTERS else "portable-core"


def build_file_entries(source_root: Path = SOURCE_ROOT) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in inventory_source_files(source_root):
        relative_path = path.relative_to(source_root.resolve()).as_posix()
        validate_manifest_path(relative_path)
        entries.append(
            {
                "path": relative_path,
                "ownership": ownership_for(relative_path),
                "layer": layer_for(relative_path),
                "sha256": sha256_file(path),
            }
        )
    return entries


def compute_tree_digest(entries: Iterable[dict[str, str]]) -> str:
    normalized = [
        {
            "path": entry["path"],
            "ownership": entry["ownership"],
            "layer": entry["layer"],
            "sha256": entry["sha256"],
        }
        for entry in entries
    ]
    return sha256_bytes(canonical_json_bytes(normalized))


def canonical_source_commit() -> str:
    dirty = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", "我的第二大脑"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if dirty.returncode != 0:
        raise ProjectionError("无法检查 canonical source 工作树")
    if dirty.stdout:
        raise ProjectionError("canonical source 存在未提交变更；请先提交再同步")
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", "我的第二大脑"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}\n?", result.stdout):
        raise ProjectionError("无法取得 canonical source commit")
    return result.stdout.strip()


def expected_starter_manifest(entries: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "starter_version": STARTER_VERSION,
        "source": {
            "root": "我的第二大脑",
            "commit": canonical_source_commit(),
            "tree_digest": compute_tree_digest(entries),
        },
        "projection": {
            "root": "assets/starter-kit",
            "direction": "canonical-to-assets-only",
        },
        "exclusions": EXCLUSIONS,
        "files": entries,
    }


def validate_tool_contract(text: str) -> None:
    violations: list[str] = []
    for tool, tier in TOOL_ROWS.items():
        row_pattern = re.compile(
            rf"(?m)^\|\s*\*\*?{re.escape(tool)}\*\*?\s*\|\s*`?{re.escape(tier)}`?\s*\|"
        )
        if not row_pattern.search(text):
            violations.append(f"{tool} 缺少 {tier} 分层行")
    if "https://www.workbuddy.ai/" not in text or "https://workbuddy.ai" in text:
        violations.append("WorkBuddy 必须使用 https://www.workbuddy.ai/ 官方初始入口")
    if violations:
        raise ProjectionError("；".join(violations))


def validate_canonical_contract(entries: list[dict[str, str]]) -> None:
    entry_paths = {entry["path"] for entry in entries}
    missing_managed = set(MANAGED_BLOCKS) - entry_paths
    if missing_managed:
        raise ProjectionError(f"缺少 managed-block canonical 文件：{sorted(missing_managed)}")

    for relative_path, block_id in MANAGED_BLOCKS.items():
        text = (SOURCE_ROOT / relative_path).read_text(encoding="utf-8")
        validate_managed_blocks(text, block_id)

    for entry in entries:
        if entry["layer"] != "portable-core":
            continue
        text = (SOURCE_ROOT / entry["path"]).read_text(encoding="utf-8", errors="strict")
        violations = portable_vendor_violations(text)
        if violations:
            raise ProjectionError(
                f"portable core 出现厂商强制绑定：{entry['path']}：{'；'.join(violations)}"
            )

    tool_guide = (SOURCE_ROOT / "30_知识主题/第二大脑完整工具清单.md").read_text(
        encoding="utf-8"
    )
    validate_tool_contract(tool_guide)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProjectionError(f"无法读取 JSON {path.relative_to(REPO_ROOT)}：{error}") from error
    if not isinstance(value, dict):
        raise ProjectionError(f"JSON 顶层必须是 object：{path.relative_to(REPO_ROOT)}")
    return value


def validate_starter_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ProjectionError("starter manifest schema_version 不匹配")
    if manifest.get("starter_version") != STARTER_VERSION:
        raise ProjectionError("starter semver 不匹配")
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ProjectionError("starter manifest 缺少 source")
    if source.get("root") != "我的第二大脑":
        raise ProjectionError("starter source root 不匹配")
    if not re.fullmatch(r"[0-9a-f]{40}", str(source.get("commit", ""))):
        raise ProjectionError("starter source commit 必须是完整 Git OID")
    if not re.fullmatch(r"[0-9a-f]{64}", str(source.get("tree_digest", ""))):
        raise ProjectionError("starter source tree digest 必须是 SHA-256")
    if manifest.get("projection") != {
        "root": "assets/starter-kit",
        "direction": "canonical-to-assets-only",
    }:
        raise ProjectionError("starter projection 必须保持 canonical-to-assets-only")
    if manifest.get("exclusions") != EXCLUSIONS:
        raise ProjectionError("starter exclusions 与冻结规则不一致")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ProjectionError("starter manifest 必须声明投影文件")
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise ProjectionError("starter file entry 必须是 object")
        relative_path = validate_manifest_path(entry.get("path"))
        if relative_path in seen:
            raise ProjectionError(f"starter manifest 路径重复：{relative_path}")
        seen.add(relative_path)
        if entry.get("ownership") not in ALLOWED_OWNERSHIP:
            raise ProjectionError(f"非法 ownership：{relative_path}")
        if entry.get("layer") not in ALLOWED_LAYERS:
            raise ProjectionError(f"非法 layer：{relative_path}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", ""))):
            raise ProjectionError(f"非法 SHA-256：{relative_path}")
    if compute_tree_digest(files) != source["tree_digest"]:
        raise ProjectionError("starter source tree digest 与 files 不匹配")


def assert_safe_asset_root() -> None:
    if ASSET_ROOT.exists() and ASSET_ROOT.is_symlink():
        raise ProjectionError("asset root 不得是 symlink")
    resolved_parent = ASSET_ROOT.parent.resolve(strict=True)
    if resolved_parent != (SKILL_ROOT / "assets").resolve(strict=True):
        raise ProjectionError("asset root 越出 Skill assets 边界")


def inventory_asset_files() -> list[Path]:
    if not ASSET_ROOT.exists():
        return []
    root = ASSET_ROOT.resolve(strict=True)
    files: list[Path] = []
    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directory_names.sort()
        file_names.sort()
        for name in directory_names:
            candidate = current_path / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise ProjectionError(
                    f"Starter assets 目录项类型异常：{candidate.relative_to(root).as_posix()}")
        for name in file_names:
            candidate = current_path / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
                raise ProjectionError(
                    f"Starter assets 只允许普通文件：{candidate.relative_to(root).as_posix()}")
            files.append(candidate)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def sync_assets(entries: list[dict[str, str]]) -> None:
    assert_safe_asset_root()
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    expected_paths = {entry["path"] for entry in entries}

    for entry in entries:
        source = SOURCE_ROOT / entry["path"]
        destination = ASSET_ROOT / entry["path"]
        atomic_write(destination, source.read_bytes())

    for existing in sorted(inventory_asset_files(), reverse=True):
        relative_path = existing.relative_to(ASSET_ROOT.resolve()).as_posix()
        if relative_path not in expected_paths:
            existing.unlink()
    for directory in sorted(
        (path for path in ASSET_ROOT.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass


def check_assets(entries: list[dict[str, str]]) -> None:
    assert_safe_asset_root()
    expected_by_path = {entry["path"]: entry for entry in entries}
    actual_files = inventory_asset_files()
    actual_paths = {
        path.relative_to(ASSET_ROOT.resolve()).as_posix(): path for path in actual_files
    }
    if set(actual_paths) != set(expected_by_path):
        missing = sorted(set(expected_by_path) - set(actual_paths))
        extra = sorted(set(actual_paths) - set(expected_by_path))
        raise ProjectionError(f"Starter 投影路径漂移：missing={missing}, extra={extra}")
    for relative_path, path in actual_paths.items():
        if sha256_file(path) != expected_by_path[relative_path]["sha256"]:
            raise ProjectionError(f"Starter 投影摘要漂移：{relative_path}")


def run_check() -> dict[str, Any]:
    policy = load_json(POLICY_MANIFEST)
    policy_digest = validate_inventory_policy(policy)
    entries = build_file_entries()
    validate_canonical_contract(entries)
    expected = expected_starter_manifest(entries)
    actual = load_json(STARTER_MANIFEST)
    validate_starter_manifest(actual)
    if actual != expected:
        raise ProjectionError("canonical source 与 starter manifest 不一致；请运行 --write")
    check_assets(entries)
    return {
        "status": "ok",
        "mode": "check",
        "starter_version": STARTER_VERSION,
        "source_tree_digest": expected["source"]["tree_digest"],
        "inventory_policy_digest": policy_digest,
        "files": len(entries),
    }


def run_write() -> dict[str, Any]:
    policy = load_json(POLICY_MANIFEST)
    policy_digest = validate_inventory_policy(policy)
    entries = build_file_entries()
    validate_canonical_contract(entries)
    manifest = expected_starter_manifest(entries)
    sync_assets(entries)
    atomic_write(STARTER_MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    checked = run_check()
    checked["mode"] = "write"
    checked["inventory_policy_digest"] = policy_digest
    return checked


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="只读校验 canonical、manifest 和 assets")
    mode.add_argument("--write", action="store_true", help="从 canonical 单向重建 manifest 和 assets")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = run_check() if args.check else run_write()
    except (OSError, ProjectionError, UnicodeError) as error:
        print(
            json.dumps(
                {"status": "error", "reason": str(error)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
