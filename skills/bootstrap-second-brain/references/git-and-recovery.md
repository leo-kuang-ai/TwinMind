# Git 与恢复边界

Git baseline 是恢复语义分界，不是可选增强。baseline 前只允许删除当前 run 创建、哈希未变化且非 append-only 的文件；用户修改、未知文件和 append-only 收据全部保留。不存在目标时先在同一父目录 sibling staging 中完成写入、fsync 和摘要校验，确认目标仍不存在后才原子 rename；竞态时保留 staging 并返回 conflict。

baseline 后不得删除历史或宣称回到初始化前。只有当前 HEAD、tree、目标路径和用户触达状态都与 recovery plan 一致时，U4 才生成 `post_baseline_compensation` operations；实际 Git commit 由 U6 adapter 执行。其他情况返回 `manual_git_recovery`。

apply 必须先验证 plan digest、subject identity、授权 operation IDs、Starter manifest 和重新 probe 快照。每个文件使用 no-follow、`O_EXCL`、regular-file/link-count 检查，记录 operation ID、before/after SHA-256。相同路径相同摘要跳过；不同摘要、大小写冲突、symlink 或 managed-block 异常均停止且不覆盖。

host-tool plan 只允许一个固定参数 `open-source` 或 `open-app` 动作，并绑定 tool identity digest。未授权、跨工具、跨 action 或旧 identity 不触发外部副作用。

cleanup 使用独立 state-root/run 计划。`scope=all` 必须确认会永久失去该 state root 上的自动 resume/recover 能力；它不删除 Vault 收据或 Git 历史。
