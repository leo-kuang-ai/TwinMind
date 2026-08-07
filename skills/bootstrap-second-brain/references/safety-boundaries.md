# 安全边界

## 目标路径

拒绝主目录、系统根目录、未解析环境变量、通配符、`~`、目标符号链接、未知文件类型和不可写父目录。路径先做 Unicode NFC 与绝对化，再以设备、inode、权限和关键快照生成 identity digest。父级 Git 只读探测，不自动创建嵌套仓库。

## 只读旅程

probe、verify 与 adopt-existing 不调用 target writer。快照比较路径、类型、普通文件大小与 SHA-256、权限、mtime_ns 和 symlink 文本；atime 明确排除。文件正文、Markdown 指令和附件元数据不进入默认报告，只返回有界相对路径和安全元数据。

## Inventory

始终绑定 `personal-vault-v1` policy digest。entries、depth、single-file、cumulative-read、elapsed、report-size、open-fd 或 filesystem-boundary 任一命中后停止新增读取，返回 `inventory_status=incomplete`、`command_outcome=action_required`、观察计数、相对停止位置和缩小范围入口。不得静默抽样或把 partial coverage 声明为 verified。

## 外部状态

state root 必须位于目标外部，由当前 UID 拥有，目录权限不向 group/other 开放，且最终路径不是 symlink。打开状态文件时使用 no-follow、regular-file、link-count、owner/mode 和 fstat 复核。`storage_domain` 来自挂载类型、可移动属性和同步 provider 证据，不从路径名称猜测；证据不足为 `unknown`。

confidential `runtime_state` 仅在 `local_fixed` 默认允许；其他 storage domain 必须有绑定当前 state root 的已验证加密收据，否则在写入答案前 action_required。
