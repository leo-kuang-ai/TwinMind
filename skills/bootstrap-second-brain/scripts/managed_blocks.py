#!/usr/bin/env python3
"""managed-block 标记的共享正则与提取器（零依赖叶模块）。

语义边界：本模块只负责标记的识别与提取，是标记语法的唯一事实源；
成对/嵌套/闭合的校验语义由各消费方持有——sync_starter_assets 做 canonical
全量校验，bootstrap_second_brain 做候选↔canonical 比对，tests/test_assets
刻意保留独立内联正则作对照 oracle（不复用生产实现，防共享模式腐坏时双盲）。
"""

from __future__ import annotations

import re

MARKER_PATTERN_STR = re.compile(
    r"<!-- TWINMIND_MANAGED_(START|END):([a-z0-9-]+) -->"
)
MARKER_PATTERN_BYTES = re.compile(
    rb"<!-- TWINMIND_MANAGED_(START|END):([a-z0-9-]+) -->"
)


def extract_markers(text: str) -> list[tuple[str, str]]:
    return MARKER_PATTERN_STR.findall(text)


def extract_markers_bytes(data: bytes) -> list[tuple[bytes, bytes]]:
    return MARKER_PATTERN_BYTES.findall(data)
