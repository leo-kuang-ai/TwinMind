---
type: knowledge
status: active
created: 2026-09-04
updated: 2026-09-04
as_of: 2026-09-04
evidence_level: verified
authority: owner-confirmed
review_at: 2026-12-04
evidence_note: "依据任务注册表迁移门禁与 TwinMind 宿主中立边界整理"
sources:
  - 60_任务系统/00_任务注册表.md
  - 30_知识主题/第二大脑完整工具清单.md
---

# WorkBuddy 接入映射（可选路径）

> WorkBuddy（https://www.workbuddy.ai/ ）是推荐的协作调度入口之一。接入它是可选项：不接入时任务契约保持 `draft`、由人工触发，一切功能不受影响。

## 这篇知识回答的问题

想让某个任务定时自动运行时，怎么用 WorkBuddy 承担调度、同时让库内登记保持审计准确。

## 三步接入

1. **WorkBuddy 侧建调度**：在 WorkBuddy 中创建定时任务，把任务定义页的"执行指令"节作为 prompt 内容使用；
2. **库内登记为审计副本**：在任务定义页 frontmatter 声明 `execution_source: workbuddy`（WorkBuddy 侧为事实源，本页为审计副本），并登记 `prompt_sha256`（对所配置 prompt 内容的摘要哈希）与 `prompt_snapshot`（完整 prompt 的存放位置回链）；
3. **按迁移门禁晋级**：状态仍从 `draft` 走 `pilot` 再到 `active`，五条启用门禁一条不少——WorkBuddy 已配置本身不构成启用证据。

## 核对

按注册表"双向核对"流程执行：用户在 WorkBuddy 侧导出任务清单或自查后手动提供，AI 只处理用户提供的内容，不因此获得 WorkBuddy 或任何外部系统的连接、读取或写入授权。

## 边界

- 失败告警、停用方式在 WorkBuddy 侧配置，库内只登记回查方式；
- 换用或停用 WorkBuddy 时，任务状态按迁移门禁处理（通常 `paused` 或 `retired`），登记迁移证据。
