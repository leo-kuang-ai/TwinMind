from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "skills" / "bootstrap-second-brain"
SOURCE_ROOT = REPO_ROOT / "我的第二大脑"
SCRIPT = SKILL_ROOT / "scripts" / "sync_starter_assets.py"
STARTER_MANIFEST = SKILL_ROOT / "manifests" / "starter-v1.json"
POLICY_MANIFEST = SKILL_ROOT / "manifests" / "inventory-policies-v1.json"

MANAGED_BLOCKS = {
    "AI协作协议.md": "ai-collaboration-policy",
    "知识库索引.md": "knowledge-index",
    "10_当前工作台/00_第二大脑启动契约.md": "startup-contract",
}
TOOLING_ADAPTERS = {
    "30_知识主题/第二大脑完整工具清单.md",
    "30_知识主题/工具选择与升级门禁.md",
}
EXCLUDED_SOURCE_PATHS = {"AGENTS.md"}
TASK_DEFINITION_PATHS = {
    "60_任务系统/10_任务定义/每日任务规划.md",
    "60_任务系统/10_任务定义/每日总结.md",
    "60_任务系统/10_任务定义/每日思考.md",
    "60_任务系统/10_任务定义/每日进化.md",
    "60_任务系统/10_任务定义/每周知识蒸馏.md",
    "60_任务系统/10_任务定义/每月健康检查.md",
    "60_任务系统/10_任务定义/每季度反熵审查.md",
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


def load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_starter_assets", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载同步脚本：{SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CanonicalAssetContractTests(unittest.TestCase):
    def test_sync_script_exists(self) -> None:
        self.assertTrue(SCRIPT.is_file(), "缺少 canonical-to-assets 同步脚本")

    def test_inventory_policy_v1_is_frozen(self) -> None:
        manifest = json.loads(POLICY_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "inventory-policies-v1")
        self.assertEqual(len(manifest["policies"]), 1)
        policy = manifest["policies"][0]
        self.assertEqual(policy["policy_id"], "personal-vault-v1")
        self.assertEqual(policy["limits"], EXPECTED_POLICY_LIMITS)
        self.assertEqual(
            policy["on_limit"],
            {
                "stop_new_reads": True,
                "inventory_status": "incomplete",
                "command_outcome": "action_required",
            },
        )
        self.assertEqual(manifest["effective_limits_rule"], "may-only-tighten")

    def test_canonical_managed_blocks_are_unique_and_paired(self) -> None:
        marker_pattern = re.compile(
            r"<!-- TWINMIND_MANAGED_(START|END):([a-z0-9-]+) -->"
        )
        for relative_path, block_id in MANAGED_BLOCKS.items():
            with self.subTest(path=relative_path):
                text = (SOURCE_ROOT / relative_path).read_text(encoding="utf-8")
                markers = marker_pattern.findall(text)
                self.assertEqual(
                    markers,
                    [("START", block_id), ("END", block_id)],
                    f"{relative_path} 必须恰好包含一对 {block_id} 标记",
                )

    def test_tool_tiers_match_product_contract(self) -> None:
        text = (SOURCE_ROOT / "30_知识主题/第二大脑完整工具清单.md").read_text(
            encoding="utf-8"
        )
        expected_rows = {
            "Python 3.11+": "runtime-required",
            "Git": "product-required",
            "WorkBuddy": "recommended",
            "Obsidian": "recommended",
            "社区插件": "optional",
        }
        for tool, tier in expected_rows.items():
            with self.subTest(tool=tool):
                self.assertRegex(
                    text,
                    rf"(?m)^\|\s*\*\*?{re.escape(tool)}\*\*?\s*\|\s*`?{re.escape(tier)}`?\s*\|",
                )

    def test_workbuddy_uses_current_official_entrypoint(self) -> None:
        text = (SOURCE_ROOT / "30_知识主题/第二大脑完整工具清单.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("https://www.workbuddy.ai/", text)
        self.assertNotIn("https://workbuddy.ai", text)

    def test_task_system_defaults_to_safe_unassigned_drafts(self) -> None:
        registry = (SOURCE_ROOT / "60_任务系统/00_任务注册表.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            registry.count("| scheduled | draft |"), len(TASK_DEFINITION_PATHS)
        )
        task_ids = set()
        for relative_path in TASK_DEFINITION_PATHS:
            with self.subTest(path=relative_path):
                text = (SOURCE_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertRegex(text, r"(?m)^type: task$")
                task_id = re.search(r"(?m)^task_id: ([a-z0-9-]+)$", text)
                self.assertIsNotNone(task_id)
                task_ids.add(task_id.group(1))
                self.assertRegex(text, r"(?m)^status: draft$")
                self.assertRegex(text, r"(?m)^scheduler_owner: unassigned$")
                self.assertRegex(text, r"(?m)^timezone: unassigned$")
                for heading in (
                    "## 目标",
                    "## 触发与事实源",
                    "## 输入与排除",
                    "## 执行指令",
                    "## 输出",
                    "## 权限与人工门禁",
                    "## 失败、停止与验证",
                ):
                    self.assertIn(heading, text)
                self.assertNotIn("/Users/", text)
                self.assertNotIn("open_id", text)
                self.assertNotIn("chat_id", text)
        self.assertEqual(len(task_ids), len(TASK_DEFINITION_PATHS))
        for task_id in task_ids:
            self.assertEqual(registry.count(f"`{task_id}`"), 1)

    def test_methodology_keeps_structure_logic_and_operation_separate(self) -> None:
        text = (SOURCE_ROOT / "30_知识主题/第二大脑建设与运行方法论.md").read_text(
            encoding="utf-8"
        )
        for anchor in (
            "五项成功条件",
            "物理结构",
            "逻辑模型",
            "运行机制",
            "真实问题 → 来源与证据 → Candidate",
            "维护成本",
            "也可以为零",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)
        self.assertRegex(text, r"(?m)^status: pilot$")
        self.assertNotIn("/Users/", text)

    def test_canonical_wikilinks_resolve_without_ambiguity(self) -> None:
        wikilink = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]+)?\]\]")
        markdown_files = sorted(
            path
            for path in SOURCE_ROOT.rglob("*.md")
            if path.relative_to(SOURCE_ROOT).as_posix() not in EXCLUDED_SOURCE_PATHS
        )
        for source in markdown_files:
            for raw_target in wikilink.findall(source.read_text(encoding="utf-8")):
                target = raw_target.strip()
                self.assertFalse(
                    Path(target).is_absolute()
                    or re.match(r"^[A-Za-z]:[\\/]", target)
                    or target.startswith("\\\\"),
                    f"Wiki 链接不得使用绝对路径：{target}",
                )
                self.assertNotIn("..", Path(target).parts, f"Wiki 链接不得越出 Vault：{target}")
                direct = SOURCE_ROOT / target
                candidates = []
                for candidate in (
                    direct,
                    direct.with_suffix(".md") if not direct.suffix else direct,
                    direct / "README.md",
                ):
                    if candidate.is_file() and candidate not in candidates:
                        candidates.append(candidate)
                if not candidates and "/" not in target:
                    local = source.parent / f"{target}.md"
                    candidates = [local] if local.is_file() else list(
                        SOURCE_ROOT.rglob(f"{target}.md")
                    )
                with self.subTest(
                    source=source.relative_to(SOURCE_ROOT).as_posix(), target=target
                ):
                    self.assertEqual(
                        len(candidates),
                        1,
                        f"Wiki 链接必须唯一解析：{target} -> {candidates}",
                    )

    def test_starter_manifest_declares_every_safe_canonical_file(self) -> None:
        manifest = json.loads(STARTER_MANIFEST.read_text(encoding="utf-8"))
        actual = {
            path.relative_to(SOURCE_ROOT).as_posix()
            for path in SOURCE_ROOT.rglob("*")
            if path.is_file()
            and not path.is_symlink()
            and path.relative_to(SOURCE_ROOT).as_posix()
            not in EXCLUDED_SOURCE_PATHS
        }
        declared = {entry["path"] for entry in manifest["files"]}
        self.assertEqual(declared, actual)
        for entry in manifest["files"]:
            with self.subTest(path=entry["path"]):
                expected_ownership = (
                    "managed-block"
                    if entry["path"] in MANAGED_BLOCKS
                    else "append-only"
                    if entry["path"] == "维护日志.md"
                    else "static"
                )
                expected_layer = (
                    "tooling-adapter"
                    if entry["path"] in TOOLING_ADAPTERS
                    else "portable-core"
                )
                self.assertEqual(entry["ownership"], expected_ownership)
                self.assertEqual(entry["layer"], expected_layer)
                self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")

    def test_manifest_source_commit_is_latest_canonical_change(self) -> None:
        manifest = json.loads(STARTER_MANIFEST.read_text(encoding="utf-8"))
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", "我的第二大脑"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(manifest["source"]["commit"], result.stdout.strip())


@unittest.skipUnless(SCRIPT.is_file(), "同步脚本尚未实现")
class SyncScriptBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sync = load_sync_module()

    def test_manifest_paths_reject_unsafe_forms(self) -> None:
        invalid_paths = [
            "/absolute.md",
            "../outside.md",
            "safe/../../outside.md",
            "./not-normal.md",
            "safe\\windows.md",
            "control\u0000.md",
        ]
        for path in invalid_paths:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    self.sync.validate_manifest_path(path)

    def test_managed_block_validator_rejects_missing_duplicate_and_nested(self) -> None:
        start = "<!-- TWINMIND_MANAGED_START:demo -->"
        end = "<!-- TWINMIND_MANAGED_END:demo -->"
        invalid_documents = [
            "无标记",
            f"{start}\n{start}\n{end}\n{end}",
            f"{end}\n{start}",
            (
                "<!-- TWINMIND_MANAGED_START:demo -->\n"
                "<!-- TWINMIND_MANAGED_START:other -->\n"
                "<!-- TWINMIND_MANAGED_END:other -->\n"
                "<!-- TWINMIND_MANAGED_END:demo -->"
            ),
        ]
        for text in invalid_documents:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    self.sync.validate_managed_blocks(text, "demo")

    def test_portable_core_vendor_lock_is_rejected_but_guidance_is_allowed(self) -> None:
        violations = self.sync.portable_vendor_violations(
            "必须使用 WorkBuddy 才能读取和维护这个 Vault。"
        )
        self.assertTrue(violations)
        self.assertEqual(
            self.sync.portable_vendor_violations(
                "Demo 推荐 WorkBuddy，但 Markdown 文件可由其他兼容工具维护。"
            ),
            [],
        )

    def test_effective_inventory_limits_can_only_tighten(self) -> None:
        canonical = dict(EXPECTED_POLICY_LIMITS)
        tighter = dict(canonical)
        tighter["entries"] = 10_000
        self.sync.validate_effective_limits(canonical, tighter)

        looser = dict(canonical)
        looser["entries"] = 60_000
        with self.assertRaises(ValueError):
            self.sync.validate_effective_limits(canonical, looser)

        crossing = dict(canonical)
        crossing["cross_filesystems"] = True
        with self.assertRaises(ValueError):
            self.sync.validate_effective_limits(canonical, crossing)

    def test_symlink_is_rejected_from_projection_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "regular.md").write_text("ok", encoding="utf-8")
            (root / "linked.md").symlink_to(root / "regular.md")
            with self.assertRaises(ValueError):
                self.sync.inventory_source_files(root)

    def test_check_mode_reports_clean_projection(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
