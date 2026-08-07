# 个人第二大脑 Starter Kit

这是一份可直接复制的第一版骨架，对应文章[《个人第二大脑搭建指南：5万字讲透架构、AI协作与进化》](https://mp.weixin.qq.com/s/8Gq9vFm44EFm_7nBW7znAA)。

## 包含内容

- 八区目录：`00 / 10 / 20 / 30 / 40 / 50 / 90 / 99`，每区自带一份用途 README
- 六个根控制文件：`AGENTS.md`、`AI协作协议.md`、`加载清单.md`、`知识库索引.md`、`维护日志.md`、`.gitignore`
- 一页启动契约
- 五个第一周模板：来源、知识、项目、决策、交付
- 一份建设与运行指南：四阶段路线、日/周/月/季度任务、知识与能力进化门禁
- 五份校准后的配套参考：字段状态、七天/三十天清单、完整工具清单、工具升级门禁、反熵检查

## 五份原附录的取舍

- **A 目录与字段**：原目录已过时，不原样复制；保留校准后的 [[我的第二大脑/90_模板/字段与状态速查]]；
- **B 七天与三十天**：纳入 [[我的第二大脑/99_维护记录/七天冷启动与三十天验收清单]]；
- **C Memory OS 命令**：不纳入假设命令，Demo 没有 `tools/memory.py`；有效概念已进入 [[我的第二大脑/99_维护记录/定时任务与知识进化]]；
- **D 工具技术栈**：移除易过期价格、版本、固定时间和错误字段口径；完整目录纳入 [[我的第二大脑/30_知识主题/第二大脑完整工具清单]]，升级判断纳入 [[我的第二大脑/30_知识主题/工具选择与升级门禁]]；
- **E 失败与反熵**：修正旧路径和硬阈值，纳入 [[我的第二大脑/99_维护记录/每月检查与季度反熵清单]]。

## 15 分钟启动

推荐使用 `skills/bootstrap-second-brain/` 中的 Codex Skill：

1. 先完成可信 Python 3.11+、Git、WorkBuddy 和 Obsidian 的工具准备；Git 是 create 硬门禁，WorkBuddy 与 Obsidian 可以明确暂缓；
2. 让 Skill 只读探测目标，并审阅带摘要的 scaffold plan；
3. 批准明确 operation 后生成 Starter，再完成最小访谈和独立 personalize plan；
4. 建立只包含批准 Vault 路径的 Git baseline commit；
5. 运行 verify，并用一个真实问题跑通来源 → 知识 → 项目/决策 → 交付 → 结果回写。

也可以继续手工复制“我的第二大脑”，但不能跳过 Git 初始化、差异审查和恢复演练。

## Skill 支持边界

- v0.1 正式支持 Codex、macOS 和 Python 3.11+；Linux 仅保留文件系统兼容候选，Windows 延后。
- 支持 create、verify、create-run resume，以及 adopt-existing 的只读 inventory/接管计划。
- 默认离线，不自动 sudo、下载、安装社区插件、修改全局 Git 配置、创建 remote 或 push。
- 分发包当前仅允许 Owner 私有 pilot；许可证尚待 Owner 裁决，不能公开分发或宣称开源。
- 安装、结构生成、Git baseline 和 activated/proven 是不同证据层，不能相互补偿。

## 使用边界

第一版不需要 Memory OS、RAG、语义检索、插件或自动化。只有真实失败反复出现时再升级；原件不被摘要覆盖，Candidate 不自动变成事实，高风险操作保留人工确认。

## 加入群聊

👥 欢迎加入微信群聊：

<img src="docs/image.png" alt="群聊：研发效能（spec-first）" width="360" />

与业界大牛一起探讨 AI 与第二大脑、超级个体、企业研发效能的落地实践。
