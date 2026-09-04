# Workflow 合同

CLI 默认离线，stdout 在 `--json` 模式只输出一个 JSON object，诊断进入 stderr。路径和操作参数必须按数组传递，不经 shell 拼接。

create 顺序固定为：宿主原生 Python 3.11+ preflight → host tool-probe → tool-plan/choice/verify → Git product-required 门禁 → 路径确认 → scaffold plan/authorization/apply → interview → personalize/environment plan/authorization/apply → Git baseline → verify → receipt。

`tool-verify --run-id --state-dir` 成功后生成 `tool-readiness-receipt.json`；scaffold plan 与 apply 都必须重验并绑定其摘要。create 的 personalize、environment 和 verify 依次生成 `personalize-receipt.json`、`environment-receipt.json`、`verify-receipt.json` 与 `final-result.json`。`resume` 只接受当前仍能重验的收据，不以路径存在替代语义证据。

verify 与 adopt-existing 对目标保持零写入；运行状态、计划和报告位于目标外部私有 state root。host-tool plan 不绑定 Vault target，只允许 identity manifest 声明的 `open-source` 或 `open-app` operation。生成计划、记录选择或记录 GUI 观察都不构成执行授权或 readiness 证明。

verify 按 ownership 验证当前 Starter，并确认 Git baseline/tree；结果遵循 `bootstrap-result`。激活证据路径必须位于 Vault 内且是普通文件，但路径存在本身不足以得到 `activated`，还必须提供用户确认来源和完成的闭环清单。

授权必须绑定 plan digest、subject identity 和批准 operation IDs。scaffold 与 personalize/environment 使用独立不可变 plan 和 authorization。recover 以 baseline 为界；baseline 后只允许补偿提交或人工 Git 恢复。cleanup 只作用于外部 run state，不删除 Vault 收据或 Git 历史。

退出类别为：0 完成或降级完成；1 failed；2 action_required；3 conflict；4 unsafe_target；5 plan_stale；6 partial。最终语义以 JSON `command_outcome` 为准。
