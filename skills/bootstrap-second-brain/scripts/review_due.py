#!/usr/bin/env python3
"""TwinMind 到期巡检：按 review_at 列出到期待复核页面。

只读契约：不写入 Vault 内外任何文件；stdlib-only；建议以 -I -S -E 隔离调用。
用法：python3 -I -S -E review_due.py <vault-root> [--json]
退出码：0 正常（含零到期项）；2 参数/路径/预算错误。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

MAX_SCAN_FILES = 50_000
MAX_READ_BYTES = 64 * 1024 * 1024
MAX_ELAPSED_SECONDS = 600.0
FRONTMATTER_BYTES_LIMIT = 64 * 1024

_STRICT_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REVIEW_AT_KEY = re.compile(r"^review_at:\s*(.+?)\s*$")


class SafetyError(ValueError):
    """目标路径不安全（未解析变量、通配符、symlink、越界根）。"""


class ScanBudgetError(RuntimeError):
    """扫描超出文件数/读取字节/耗时预算。"""


def normalize_target_path(raw: str) -> Path:
    text = os.fspath(raw)
    if not text or any(token in text for token in ("$", "*", "?", "[", "]")) or text.startswith("~"):
        raise SafetyError("目标路径含未解析环境变量、通配符或主目录缩写")
    normalized = unicodedata.normalize("NFC", text)
    path = Path(normalized)
    if not path.is_absolute():
        path = Path.cwd() / path
    if path == Path.home() or path == Path("/"):
        raise SafetyError("目标路径不得是主目录或文件系统根")
    if path.is_symlink():
        raise SafetyError("目标路径不得是 symlink")
    return path.resolve(strict=False)


def _parse_review_at(text: str) -> str | None:
    """从 markdown 正文解析 frontmatter 的 review_at；无或非严格日期返回 None。"""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    frontmatter = text[3:end]
    if len(frontmatter.encode("utf-8")) > FRONTMATTER_BYTES_LIMIT:
        return None
    for line in frontmatter.splitlines():
        match = _REVIEW_AT_KEY.match(line.strip())
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
        return value
    return None


def collect_due_pages(root: Path, today: str | None = None) -> dict:
    today = today or dt.date.today().isoformat()
    due: list[dict[str, str]] = []
    skipped_malformed = 0
    scanned_files = 0
    bytes_read = 0
    started = time.monotonic()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if not (Path(dirpath) / name).is_symlink())
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            scanned_files += 1
            if scanned_files > MAX_SCAN_FILES:
                raise ScanBudgetError(f"扫描文件数超出预算 {MAX_SCAN_FILES}")
            path = Path(dirpath) / name
            if path.is_symlink():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                raise SafetyError(f"读取失败：{path.relative_to(root)}（{exc}）") from exc
            bytes_read += len(text.encode("utf-8", errors="replace"))
            if bytes_read > MAX_READ_BYTES:
                raise ScanBudgetError(f"累计读取超出预算 {MAX_READ_BYTES} 字节")
            if time.monotonic() - started > MAX_ELAPSED_SECONDS:
                raise ScanBudgetError(f"耗时超出预算 {MAX_ELAPSED_SECONDS}s")
            review_at = _parse_review_at(text)
            if review_at is None:
                if "review_at:" in text[:FRONTMATTER_BYTES_LIMIT]:
                    skipped_malformed += 1
                continue
            if review_at < today:
                due.append({
                    "path": path.relative_to(root).as_posix(),
                    "review_at": review_at,
                })
    return {
        "today": today,
        "due": due,
        "due_count": len(due),
        "skipped_malformed": skipped_malformed,
        "scanned_files": scanned_files,
    }


def _render_human(result: dict) -> str:
    lines = [f"到期巡检（基准日 {result['today']}）"]
    for entry in result["due"]:
        lines.append(f"- {entry['path']}（review_at {entry['review_at']}）")
    if not result["due"]:
        lines.append("- 无到期页面")
    lines.append(
        f"扫描 {result['scanned_files']} 个 markdown；"
        f"到期 {result['due_count']}；占位/非法日期跳过 {result['skipped_malformed']}"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按 review_at 列出到期待复核页面（只读）")
    parser.add_argument("vault_root", help="Vault 根目录的绝对或相对路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 单对象")
    args = parser.parse_args(argv)
    try:
        root = normalize_target_path(args.vault_root)
        if not root.is_dir():
            raise SafetyError(f"目标不是目录：{root}")
        result = collect_due_pages(root)
    except (SafetyError, ScanBudgetError) as exc:
        print(f"review_due: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(_render_human(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
