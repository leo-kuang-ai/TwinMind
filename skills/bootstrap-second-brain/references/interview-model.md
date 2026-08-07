# 访谈模型

首轮只收敛首要场景、三个真实问题、事实 Owner、一个当前项目或决定、AI 权限、维护预算、七天成功信号和三十天停止条件。未回答维度进入七天计划，不继续追问以追求“完整画像”。

每次增量必须符合 interview-answer schema。`agent_inference` 不能 confirmed；declined 不保存拒绝内容；withdrawn 删除当前值。restricted 只接受类别、占位符或本地引用。confidential 默认 session_only，宿主许可和 storage domain/encryption 门禁在值落盘前执行。

公开 state、event、result 和收据只保留字段状态、敏感等级、persistence 和摘要，不包含答案值。跨会话只恢复 runtime_state 与 vault_confirmed；personalize plan 只消费 confirmed 字段。
