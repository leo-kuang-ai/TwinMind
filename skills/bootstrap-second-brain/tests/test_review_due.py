"""review_due.py 到期巡检的只读契约测试。

覆盖：到期判定、占位/非法日期跳过、零写入、错误路径退出码、输入加固与扫描预算。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "review_due.py"


def _load_module():
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


def _write_page(root: Path, relative: str, frontmatter_lines: list[str]) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n# 页面\n",
        encoding="utf-8",
    )


class ReviewDueContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="review_due_test_")
        self.vault = Path(self._tmp.name) / "vault"
        self.vault.mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-I", "-S", "-E", str(SCRIPT_PATH), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_due_listing_and_json_contract(self):
        _write_page(self.vault, "a.md", ["review_at: 2020-01-01", "authority: personal"])
        _write_page(self.vault, "b.md", ["review_at: 2999-01-01"])
        _write_page(self.vault, "c.md", ["authority: source"])
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["due_count"], 1)
        self.assertEqual(payload["due"][0]["path"], "a.md")
        self.assertEqual(payload["due"][0]["review_at"], "2020-01-01")
        self.assertGreaterEqual(payload["scanned_files"], 3)
        self.assertEqual(payload["skipped_malformed"], 0)

    def test_placeholder_and_malformed_dates_are_skipped(self):
        _write_page(self.vault, "placeholder.md", ["review_at: YYYY-MM-DD"])
        _write_page(self.vault, "garbage.md", ["review_at: 去年"])
        _write_page(self.vault, "badcal.md", ["review_at: 2020-13-45"])
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["due_count"], 0)
        self.assertEqual(payload["skipped_malformed"], 3)

    def test_zero_write_boundary(self):
        _write_page(self.vault, "due.md", ["review_at: 2020-01-01"])
        before = _tree_state(self.vault)
        self.assertEqual(self._run(str(self.vault)).returncode, 0)
        self.assertEqual(_tree_state(self.vault), before)

    def test_empty_vault_succeeds_with_empty_list(self):
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["due_count"], 0)

    def test_missing_path_exits_two_with_single_stderr_line(self):
        result = self._run(str(self.vault / "nope"))
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr.strip())
        self.assertEqual(len(result.stderr.strip().splitlines()), 1)

    def test_unsafe_path_tokens_rejected(self):
        for unsafe in ("~/vault", "some/$HOME", "vault*", "a?b", "x[y]"):
            with self.subTest(unsafe=unsafe):
                result = self._run(unsafe)
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_symlink_root_rejected_and_inner_symlinks_not_followed(self):
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        _write_page(outside, "hidden.md", ["review_at: 2020-01-01"])
        (self.vault / "link.md").symlink_to(outside / "hidden.md")
        _write_page(self.vault, "real.md", ["review_at: 2020-01-01"])
        result = self._run(str(self.vault), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        listed = {entry["path"] for entry in payload["due"]}
        self.assertEqual(listed, {"real.md"})
        link_root = Path(self._tmp.name) / "linkroot"
        link_root.symlink_to(self.vault, target_is_directory=True)
        self.assertEqual(self._run(str(link_root)).returncode, 2)

    def test_scan_file_budget_enforced(self):
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


if __name__ == "__main__":
    unittest.main()
