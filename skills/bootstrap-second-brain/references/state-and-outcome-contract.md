# 状态与结果合同

五个轴不得混用：

- `phase`：当前步骤。
- `lifecycle_state`：Vault 已取得的最高证据等级。
- `run_state`：本次 run 的控制状态。
- `health`：可选能力的降级状态。
- `command_outcome`：单次命令结果。

`partial`、`failed`、`action_required` 和 `degraded` 不是 lifecycle。run 失败时保留最后一个已验证 lifecycle。Git 缺失、仓库边界不明或 baseline 未验证不能降级通过 initialized。

`initialized` 必须同时具备 baseline commit OID、仓库边界摘要和 baseline tree 校验；`activated` 还必须具备用户确认来源、完整闭环清单和 Vault 相对证据路径。`inventory_status=incomplete` 强制总体 `command_outcome=action_required`。

任务契约的 `draft / pilot / active / paused / retired` 是独立状态轴，不是 Vault lifecycle。任务 `active` 至少需要可验证的调度事实 owner、时区、配置收据、受控试跑和运行证据；Starter 文件、manifest 或 Vault `initialized/activated` 都不能补偿。

state root identity、`storage_domain`、加密收据和 inventory policy digest 都是 plan 前置条件；apply/resume 前任一漂移即旧 plan 失效。
