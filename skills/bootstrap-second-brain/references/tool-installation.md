# 工具准备与安装引导

tool-prepare 是 create 的第一阶段，先由宿主原生能力解析并验证 Python 3.11+，再调用 CLI 探测 Git、WorkBuddy 和 Obsidian。Python 或 Git 未 verified 时不得询问、规范化探测或写入 Vault 路径。

工具分层固定为：Python `runtime-required`、Git `product-required`、WorkBuddy/Obsidian `recommended`、社区插件 `optional`。tool-plan 只生成安装卡，不打开浏览器、不下载、不调用 sudo/包管理器、不接受许可、不修改全局 Git 配置，也不创造授权。

每张卡必须包含当前状态、平台、identity manifest 官方初始 URL、许可/成本复核、数据与权限、联网/模型边界、日志/缓存/密钥、停用/卸载、派生数据清理、安装后身份验证和失败后的下一动作。

打开官网或应用使用独立 `subject_kind=host_tool` plan 和 authorization。URL 必须精确匹配无凭据、无 query/fragment 的 HTTPS 初始入口；打开收据只证明初始 URL 已交付给外部应用，不证明下载、安装、后续跳转或 ready。

WorkBuddy 和 Obsidian 缺失时，用户可以选择 `deferred_by_user` 并记录影响；未选择时保持 action_required。GUI opened 证据不能补偿 bundle/signing identity 缺失。
