"""review_due.py 到期巡检的只读契约测试。

覆盖：到期判定、BOM/嵌套/重复/占位日期、零写入（临时根全观察面）、错误路径退出码、
输入加固（token/home/相对路径/symlink）、三类扫描预算、不可读文件跳过、JSON root/timezone 字段。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "review_due.py"


def _load_module() -> object:
    spec = importlib.util.spec_from_file_location("review_due", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tree_state(root: Path) -> dict[str, str]:
    state: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            state[relative] = "symlink:" + str(path.readlink())
        elif path.is_file():
            state[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            state[relative] = "dir"
    return state


def _write_page(root: Path, relative: str, frontmatter_lines: list[str], bom: bool = False) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n# 页面\n"
    if bom:
        body = "\ufeff" + body
    target.write_text(body, encoding="utf-8")


class ReviewDueContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="review_due_test_")
        self.sandbox = Path(self._tmp.name)
        self.vault = self.sandbox / "vault"
        self.vault.mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def _run(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-I", "-S", "-E", str(SCRIPT_PATH), *args],
            capture_output=True,
            text=True,
            check=False,
            cwd=None if cwd is None else str(cwd),
        )

    def test_due_listing_and_json_contract(self) -> None:
        _write_page(self.vault, "a.md", ["review_at: 2020-01-01", "authority: personal"])
        _write_page(self.vault, "b.md", ["review_at: 2999-01-01"])
        _write_page(self.vault, "c.md", ["authority: source"])
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["due_count"], 1)
        self.assertEqual(payload["due"][0]["path"], "a.md")
        self.assertEqual(payload["due"][0]["review_at"], "2020-01-01")
        self.assertIn("root", payload)
        self.assertRegex(payload["timezone"], r"^[+-]\d{4}$")
        self.assertGreaterEqual(payload["scanned_files"], 3)
        self.assertEqual(payload["skipped_malformed"], 0)

    def test_bom_page_is_still_parsed(self) -> None:
        _write_page(self.vault, "bom.md", ["review_at: 2020-01-01"], bom=True)
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["due_count"], 1)
        self.assertEqual(payload["due"][0]["path"], "bom.md")

    def test_placeholder_and_malformed_dates_are_skipped(self) -> None:
        _write_page(self.vault, "placeholder.md", ["review_at: YYYY-MM-DD"])
        _write_page(self.vault, "garbage.md", ["review_at: 去年"])
        _write_page(self.vault, "badcal.md", ["review_at: 2020-13-45"])
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["skipped_malformed"], 3)

    def test_nested_and_duplicate_review_at_rejected(self) -> None:
        _write_page(self.vault, "nested.md", ["type: knowledge", "policy:", "  review_at: 2020-01-01"])
        _write_page(self.vault, "dup.md", ["review_at: 2999-01-01", "review_at: 2020-01-01"])
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["due_count"], 0)
        self.assertEqual(payload["skipped_malformed"], 2)

    def test_review_at_equal_today_is_not_due(self) -> None:
        module = _load_module()
        _write_page(self.vault, "today.md", ["review_at: 2026-01-01"])
        result = module.collect_due_pages(self.vault, today="2026-01-01")
        self.assertEqual(result["due_count"], 0)
        result_next = module.collect_due_pages(self.vault, today="2026-01-02")
        self.assertEqual(result_next["due_count"], 1)

    def test_body_only_mention_not_counted_malformed(self) -> None:
        page = self.vault / "body.md"
        page.write_text("---\ntype: knowledge\n---\n正文提到 review_at: 2020-01-01\n", encoding="utf-8")
        result = self._run(str(self.vault), "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["due_count"], 0)
        self.assertEqual(payload["skipped_malformed"], 0)

    def test_unreadable_file_skipped_without_abort(self) -> None:
        _write_page(self.vault, "due.md", ["review_at: 2020-01-01"])
        locked = self.vault / "locked.md"
        _write_page(self.vault, "locked.md", ["review_at: 2020-01-01"])
        os.chmod(locked, 0o000)
        self.addCleanup(os.chmod, locked, 0o644)
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["due_count"], 1)
        self.assertEqual(payload["skipped_unreadable"], 1)

    def test_zero_write_boundary_observes_whole_sandbox(self) -> None:
        _write_page(self.vault, "due.md", ["review_at: 2020-01-01"])
        outside = self.sandbox / "outside"
        outside.mkdir()
        _write_page(outside, "hidden.md", ["review_at: 2020-01-01"])
        before = _tree_state(self.sandbox)
        self.assertEqual(self._run(str(self.vault)).returncode, 0)
        self.assertEqual(self._run(str(self.vault), "--json").returncode, 0)
        self.assertEqual(self._run(str(self.vault / "nope")).returncode, 2)
        self.assertEqual(_tree_state(self.sandbox), before)

    def test_empty_vault_succeeds_with_empty_list(self) -> None:
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["due_count"], 0)

    def test_missing_path_exits_two_with_single_stderr_line(self) -> None:
        result = self._run(str(self.vault / "nope"))
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr.strip())
        self.assertEqual(len(result.stderr.strip().splitlines()), 1)

    def test_unsafe_path_tokens_rejected(self) -> None:
        for unsafe in ("~/vault", "some/$HOME", "vault*", "a?b", "x[y]"):
            with self.subTest(unsafe=unsafe):
                result = self._run(unsafe)
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_home_and_root_absolute_paths_rejected(self) -> None:
        self.assertEqual(self._run(str(Path.home())).returncode, 2)
        self.assertEqual(self._run("/").returncode, 2)

    def test_relative_path_resolved_against_cwd(self) -> None:
        _write_page(self.vault, "due.md", ["review_at: 2020-01-01"])
        result = self._run("vault", cwd=self.sandbox)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("due.md", result.stdout)

    def test_symlink_root_rejected_and_inner_symlinks_not_followed(self) -> None:
        outside = self.sandbox / "outside"
        outside.mkdir()
        _write_page(outside, "hidden.md", ["review_at: 2020-01-01"])
        (self.vault / "link.md").symlink_to(outside / "hidden.md")
        _write_page(self.vault, "real.md", ["review_at: 2020-01-01"])
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        listed = {entry["path"] for entry in payload["due"]}
        self.assertEqual(listed, {"real.md"})
        link_root = self.sandbox / "linkroot"
        link_root.symlink_to(self.vault, target_is_directory=True)
        self.assertEqual(self._run(str(link_root)).returncode, 2)

    def test_scan_file_budget_enforced(self) -> None:
        module = _load_module()
        _write_page(self.vault, "one.md", ["review_at: 2020-01-01"])
        _write_page(self.vault, "two.md", ["review_at: 2020-01-01"])
        original = module.MAX_SCAN_FILES
        module.MAX_SCAN_FILES = 1
        try:
            with self.assertRaises(module.ScanBudgetError):
                module.collect_due_pages(self.vault)
        finally:
            module.MAX_SCAN_FILES = original

    def test_read_bytes_budget_enforced(self) -> None:
        module = _load_module()
        _write_page(self.vault, "one.md", ["review_at: 2020-01-01"])
        original = module.MAX_READ_BYTES
        module.MAX_READ_BYTES = 1
        try:
            with self.assertRaises(module.ScanBudgetError):
                module.collect_due_pages(self.vault)
        finally:
            module.MAX_READ_BYTES = original

    def test_elapsed_budget_enforced(self) -> None:
        module = _load_module()
        _write_page(self.vault, "one.md", ["review_at: 2020-01-01"])
        original = module.MAX_ELAPSED_SECONDS
        module.MAX_ELAPSED_SECONDS = -1.0
        try:
            with self.assertRaises(module.ScanBudgetError):
                module.collect_due_pages(self.vault)
        finally:
            module.MAX_ELAPSED_SECONDS = original


class ReviewDueOutputDetailTests(unittest.TestCase):
    """第二波审查补充：skipped_pages 清单、排序新行为与 help 冒烟。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="review_due_detail_")
        self.vault = Path(self._tmp.name) / "vault"
        self.vault.mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-I", "-S", "-E", str(SCRIPT_PATH), *args],
            capture_output=True, text=True, check=False,
        )

    def test_skipped_pages_listed_with_reason_and_truncation(self) -> None:
        for i in range(25):
            (self.vault / f"p{i:02d}.md").write_text("---\nreview_at: YYYY-MM-DD\n---\n", encoding="utf-8")
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["skipped_malformed"], 25)
        self.assertEqual(len(payload["skipped_pages"]), 25)
        for entry in payload["skipped_pages"]:
            self.assertEqual(set(entry), {"path", "reason"})
            self.assertFalse(entry["path"].startswith("/"))
        human = self._run(str(self.vault))
        skip_lines = [line for line in human.stdout.splitlines() if line.strip().startswith("跳过:")]
        self.assertEqual(len(skip_lines), 20)
        self.assertIn("等共 25 页被跳过", human.stdout)

    def test_due_sorted_by_date_then_path(self) -> None:
        pages = {"b.md": "2020-01-02", "a.md": "2020-01-01", "c.md": "2020-01-01"}
        for name, date in pages.items():
            (self.vault / name).write_text(f"---\nreview_at: {date}\n---\n", encoding="utf-8")
        result = self._run(str(self.vault), "--json")
        payload = json.loads(result.stdout)
        self.assertEqual([entry["path"] for entry in payload["due"]], ["a.md", "c.md", "b.md"])

    def test_help_smoke_mentions_contract(self) -> None:
        result = self._run("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("退出码", result.stdout)
        self.assertIn("零写入", result.stdout)
        self.assertIn("-I -S -E", result.stdout)

    def test_unclosed_frontmatter_counted_as_malformed(self) -> None:
        (self.vault / "unclosed.md").write_text("---\nreview_at: 2020-01-01\n没有闭合标记", encoding="utf-8")
        result = self._run(str(self.vault), "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["skipped_malformed"], 1)
        self.assertEqual(payload["skipped_pages"][0]["reason"], "frontmatter 未闭合或超读取窗")


if __name__ == "__main__":
    unittest.main()
