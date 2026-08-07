# Obsidian 与插件

Obsidian 是推荐工作台，不是 portable core。macOS official verification 必须同时匹配 identity manifest 中的 bundle ID、可执行文件名、TeamIdentifier 和 designated requirement；名称、图标、路径或任意有效签名均不足以证明官方身份。

scaffold 后才允许 vault-scope 探测，只读取用户已选择目标内 `.obsidian` 的受控配置摘要，不读取插件正文、密钥或目标外目录。第一阶段引导 File Explorer、Search、Quick Switcher、Backlinks、Templates，并把模板目录设为 `90_模板`；v0.1 不直接写 `.obsidian`。

社区插件默认 `selected=[]`。只有反复出现的真实失败才能触发单项计划；每项必须记录插件 ID、来源、用途、版本、读写目录、联网、密钥、派生数据、停用残留和独立授权。缺任一项不得进入 planned，不批量安装或旁加载。
