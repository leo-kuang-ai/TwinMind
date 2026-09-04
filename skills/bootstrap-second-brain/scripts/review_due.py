#!/usr/bin/env python3
"""TwinMind 到期巡检：按 review_at 列出到期待复核页面。

只读契约：不写入 Vault 内外任何文件；stdlib-only；建议以 -I -S -E 隔离调用。
用法：python3 -I -S -E review_due.py <vault-root> [--json]
退出码：0 正常（含零到期项与单文件跳过）；2 参数/路径错误或扫描预算中断（中断时仍输出部分结果，JSON 含 partial/budget_exceeded 字段）。建议以 -B 或 -I -S -E 调用。
结果为扫描时点近似：扫描间隙发生的变化不重试、不标记。
预算说明：本脚本预算独立于 manifests/inventory-policies-v1.json（10GiB/600s）并刻意更紧
——巡检只需读取 frontmatter（每页至多 64KiB），不放宽；如需调整，以 inventory policy 为上限。
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

MAX_SCAN_FILES = 50_000
MAX_READ_BYTES = 64 * 1024 * 1024
MAX_ELAPSED_SECONDS = 600.0
FRONTMATTER_BYTES_LIMIT = 64 * 1024
READ_CHUNK = FRONTMATTER_BYTES_LIMIT + 16

_STRICT_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REVIEW_AT_TOP = re.compile(r"^review_at:[ \t]*(.+?)[ \t]*$")

_VERIFY_VAULT = None


class SafetyError(ValueError):
    """目标路径不安全（未解析变量、通配符、symlink、越界根）。"""


class ScanBudgetError(RuntimeError):
    """扫描超出文件数/读取字节/耗时预算。"""


def _verify_vault_module():
    """复用 verify_vault 的 normalize_target_path，避免同仓两份漂移实现。"""
    global _VERIFY_VAULT
    if _VERIFY_VAULT is None:
        path = Path(__file__).resolve().parent / "verify_vault.py"
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True  # 只读契约含自身依赖的加载，不落 __pycache__
        try:
            spec = importlib.util.spec_from_file_location("twinmind_verify_vault", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        _VERIFY_VAULT = module
    return _VERIFY_VAULT


def normalize_target_path(raw: str) -> Path:
    """共享实现 + resolve 后复检：防 ..组合/中间 symlink 解析出 home 或根。"""
    try:
        resolved = _verify_vault_module().normalize_target_path(raw)
    except ValueError as exc:
        raise SafetyError(str(exc)) from exc
    home = Path.home().resolve()
    if resolved == home or resolved == Path("/").resolve():
        raise SafetyError("目标路径不得是主目录或文件系统根")
    return resolved


def _local_timezone_offset() -> str:
    return dt.datetime.now().astimezone().strftime("%z")


def _frontmatter_slice(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return text[3:end]


def _parse_review_at(frontmatter: str) -> str | None:
    """仅接受顶层（无缩进）review_at；重复或值冲突视为非法返回 None。"""
    values: list[str] = []
    for line in frontmatter.splitlines():
        match = _REVIEW_AT_TOP.match(line)
        if match is None:
            continue
        value = match.group(1).strip().strip("\"'")
        if _STRICT_DATE.fullmatch(value) is None:
            return None
        try:
            parsed = dt.date.fromisoformat(value)
        except ValueError:
            return None
        if parsed.isoformat() != value:
            return None
        values.append(value)
    if not values:
        return None
    if len(set(values)) != 1:
        return None
    return values[0]


def _read_frontmatter_bounded(path: Path) -> tuple[str, int]:
    """O_NOFOLLOW+O_NONBLOCK 有界读取：只读解析所需头部字节，返回 (文本, 实读字节数)。

    非 regular 文件（FIFO/设备等）抛 TypeError 由调用方按不可读跳过，
    避免 open 在特殊文件上无限阻塞。
    """
    import stat
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise TypeError("非普通文件")
        raw = os.read(fd, READ_CHUNK)
    finally:
        os.close(fd)
    return raw.decode("utf-8-sig", errors="replace"), len(raw)


def collect_due_pages(root: Path, today: str | None = None) -> dict:
    today = today or dt.date.today().isoformat()
    due: list[dict[str, str]] = []
    skipped_pages: list[dict[str, str]] = []
    skipped_malformed = 0
    skipped_unreadable = 0
    scanned_files = 0
    bytes_read = 0
    started = time.monotonic()
    budget_error: str | None = None
    skipped_dirs: list[str] = []
    skipped_symlink_dirs = 0

    def _walk_error(error: OSError) -> None:
        skipped_dirs.append(getattr(error, "filename", str(error)))

    try:
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False, onerror=_walk_error):
            pruned = []
            for name in dirnames:
                full = Path(dirpath) / name
                if full.is_symlink():
                    skipped_symlink_dirs += 1
                else:
                    pruned.append(name)
            dirnames[:] = sorted(pruned)
            for name in sorted(filenames):
                if not name.endswith(".md"):
                    continue
                scanned_files += 1
                if scanned_files > MAX_SCAN_FILES:
                    raise ScanBudgetError(f"扫描文件数超出预算 {MAX_SCAN_FILES}")
                if time.monotonic() - started > MAX_ELAPSED_SECONDS:
                    raise ScanBudgetError(f"耗时超出预算 {MAX_ELAPSED_SECONDS}s")
                path = Path(dirpath) / name
                try:
                    text, read_bytes = _read_frontmatter_bounded(path)
                except (OSError, TypeError):
                    skipped_unreadable += 1
                    continue
                bytes_read += read_bytes
                if bytes_read > MAX_READ_BYTES:
                    raise ScanBudgetError(f"累计读取超出预算 {MAX_READ_BYTES} 字节")
                frontmatter = _frontmatter_slice(text)
                if frontmatter is None:
                    if text.startswith("---"):
                        skipped_malformed += 1
                        skipped_pages.append({"path": path.relative_to(root).as_posix(), "reason": "frontmatter 未闭合或超读取窗"})
                    continue
                if len(frontmatter.encode("utf-8", errors="replace")) > FRONTMATTER_BYTES_LIMIT:
                    skipped_malformed += 1
                    skipped_pages.append({"path": path.relative_to(root).as_posix(), "reason": "frontmatter 过长"})
                    continue
                review_at = _parse_review_at(frontmatter)
                if review_at is None:
                    if "review_at:" in frontmatter:
                        skipped_malformed += 1
                        skipped_pages.append({"path": path.relative_to(root).as_posix(), "reason": "review_at 缺失或非严格 YYYY-MM-DD"})
                    continue
                if review_at < today:
                    due.append({
                        "path": path.relative_to(root).as_posix(),
                        "review_at": review_at,
                    })
    except ScanBudgetError as exc:
        budget_error = str(exc)
    due.sort(key=lambda entry: (entry["review_at"], entry["path"]))
    result = {
        "root": str(root),
        "today": today,
        "timezone": _local_timezone_offset(),
        "due": due,
        "due_count": len(due),
        "skipped_pages": skipped_pages,
        "skipped_malformed": skipped_malformed,
        "skipped_unreadable": skipped_unreadable,
        "skipped_dirs": skipped_dirs,
        "skipped_symlink_dirs": skipped_symlink_dirs,
        "scanned_files": scanned_files,
    }
    if budget_error is not None:
        result["partial"] = True
        result["budget_exceeded"] = budget_error
    return result


def _escape(text: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", lambda m: m.group(0).encode("unicode_escape").decode(), text)


def _render_human(result: dict) -> str:
    lines = [f"到期巡检（基准日 {result['today']} {result['timezone']}，根 {result['root']}）"]
    for entry in result["due"]:
        lines.append(f"- {_escape(entry['path'])}（review_at {entry['review_at']}）")
    if not result["due"]:
        lines.append("- 无到期页面")
    lines.append(
        f"扫描 {result['scanned_files']} 个 markdown；"
        f"到期 {result['due_count']}；占位/非法日期跳过 {result['skipped_malformed']}；"
        f"不可读跳过 {result['skipped_unreadable']}；不可遍历目录 {len(result['skipped_dirs'])}；symlink 目录跳过 {result['skipped_symlink_dirs']}"
    )
    for page in result["skipped_pages"][:20]:
        lines.append(f"  跳过: {_escape(page['path'])}（{_escape(page['reason'])}）")
    if len(result["skipped_pages"]) > 20:
        lines.append(f"  …等共 {len(result['skipped_pages'])} 页被跳过，--json 可取完整清单")
    if result.get("partial"):
        lines.append(f"预算中断（{result['budget_exceeded']}）：以上为部分结果，退出码 2")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="按 review_at 列出到期待复核页面（只读）",
        epilog=(
            "用法示例：python3 -I -S -E review_due.py /path/to/vault --json\n"
            "退出码：0 正常（含零到期与单文件跳过）；2 参数/路径/预算错误。\n"
            "零写入承诺：本脚本不写入 Vault 内外任何文件。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("vault_root", help="Vault 根目录的绝对或相对路径")
    parser.add_argument("--json", action="store_true", help="默认人类可读文本；--json 输出供 AI 宿主/脚本解析的 JSON 单对象")
    args = parser.parse_args(argv)
    try:
        root = normalize_target_path(args.vault_root)
        if not root.is_dir():
            raise SafetyError(f"目标不是目录：{root}，请确认路径正确（若为符号链接请改用解析后的真实路径）")
        result = collect_due_pages(root)
    except (SafetyError, ScanBudgetError) as exc:
        print(f"review_due: {exc}", file=sys.stderr)
        return 2
    if result.get("partial"):
        result["partial_note"] = "预算中断：以上为中断前已扫描部分的结果"
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(_render_human(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
