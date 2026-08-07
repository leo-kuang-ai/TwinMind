# TwinMind：本地优先的个人第二大脑 Starter Kit

TwinMind 把“搭建个人第二大脑”拆成两部分：一份可以直接复制的 Vault 示例，以及一个负责检查、规划、授权、初始化和验证的 Codex Skill。它适合希望先从可控的文件夹和 Markdown 开始，再逐步建立个人知识工作流的人。

- 想先看结构：直接浏览 [`我的第二大脑/`](我的第二大脑/)。
- 想自动初始化或验证：安装并使用 [`bootstrap-second-brain`](skills/bootstrap-second-brain/)。
- 想了解设计取舍：阅读文章[《个人第二大脑搭建指南：5万字讲透架构、AI协作与进化》](https://mp.weixin.qq.com/s/8Gq9vFm44EFm_7nBW7znAA)。

本项目采用 [MIT License](LICENSE) 开源发布。

## 你将得到什么

- 八区目录：`00 / 10 / 20 / 30 / 40 / 50 / 90 / 99`，每区自带一份用途 README
- 六个根控制文件：`AGENTS.md`、`AI协作协议.md`、`加载清单.md`、`知识库索引.md`、`维护日志.md`、`.gitignore`
- 一页启动契约
- 五个第一周模板：来源、知识、项目、决策、交付
- 一份建设与运行指南：四阶段路线、日/周/月/季度任务、知识与能力进化门禁
- 五份校准后的配套参考：字段状态、七天/三十天清单、完整工具清单、工具升级门禁、反熵检查

## 从哪里开始

| 目标 | 推荐入口 | 写入范围 |
| --- | --- | --- |
| 新建一个第二大脑 | `bootstrap-second-brain` 的 `create` | 仅写入你批准的 Vault 路径 |
| 检查已有 TwinMind Vault | `verify` | 零写入，生成外部私有报告 |
| 盘点其他非空 Vault | `adopt-existing` | 只读 inventory，不合并资料 |
| 继续已有初始化 | `resume` | 仅执行当前 run 中再次批准的操作 |

如果你只想手工体验，复制 [`我的第二大脑/`](我的第二大脑/) 即可；仍建议完成工具检查、Git 初始化、首次 baseline commit、差异审查和恢复演练。

## 五份原附录的取舍

- **A 目录与字段**：原目录已过时，不原样复制；保留校准后的 [字段与状态速查](我的第二大脑/90_模板/字段与状态速查.md)；
- **B 七天与三十天**：纳入 [七天冷启动与三十天验收清单](我的第二大脑/99_维护记录/七天冷启动与三十天验收清单.md)；
- **C Memory OS 命令**：不纳入假设命令，Demo 没有 `tools/memory.py`；有效概念已进入 [定时任务与知识进化](我的第二大脑/99_维护记录/定时任务与知识进化.md)；
- **D 工具技术栈**：移除易过期价格、版本、固定时间和错误字段口径；完整目录纳入 [第二大脑完整工具清单](我的第二大脑/30_知识主题/第二大脑完整工具清单.md)，升级判断纳入 [工具选择与升级门禁](我的第二大脑/30_知识主题/工具选择与升级门禁.md)；
- **E 失败与反熵**：修正旧路径和硬阈值，纳入 [每月检查与季度反熵清单](我的第二大脑/99_维护记录/每月检查与季度反熵清单.md)。

## 使用初始化 Skill

Canonical Skill 位于 `skills/bootstrap-second-brain/`。Codex 用户可以在仓库根目录执行：

```bash
skill_target="${CODEX_HOME:-$HOME/.codex}/skills/bootstrap-second-brain"
mkdir -p "$skill_target"
rsync -a --delete skills/bootstrap-second-brain/ "$skill_target/"
```

安装或更新后新建 Codex 会话，再使用下面的请求。如果没有进入“工具准备”阶段，先确认 `${CODEX_HOME:-$HOME/.codex}/skills/bootstrap-second-brain/SKILL.md` 存在并重新启动 Codex。Skill 不会自行修改宿主的 Skill 目录。

在 Codex 中可以直接提出：

```text
请使用 bootstrap-second-brain Skill，基于 TwinMind Demo 在 /你的/绝对路径 创建我的第二大脑。
```

也可以按目标选择请求：

- 新建：`请使用 bootstrap-second-brain，在 <绝对路径> 初始化我的第二大脑。`
- 验证：`请使用 bootstrap-second-brain，只读验证 <Vault 绝对路径>。`
- 接管盘点：`请使用 bootstrap-second-brain，只读盘点 <已有 Vault> 并生成接管计划。`
- 继续：`请使用 bootstrap-second-brain，继续 run <run-id>。`
- 撤销：`请使用 bootstrap-second-brain，为 run <run-id> 生成 recover plan；展示影响后等待我单独批准，不要直接执行。`

### 开始前准备

- Python 3.11+：运行时必需。
- Git：产品级硬门禁，用于版本管理、baseline commit 和恢复；缺失时不会开始创建 Vault。
- WorkBuddy、Obsidian：推荐工具，可以在明确知情后暂缓。
- Obsidian 社区插件：可选，默认不安装；只有真实需求出现后才逐项评估来源、权限、成本和维护风险。

### 标准工作流

1. 只读检查 Python、Git、WorkBuddy 和 Obsidian 的可信来源与可用状态；
2. 确认目标绝对路径、父级 Git 边界、隐私数据域和恢复方式；
3. 生成带摘要的 scaffold plan，展示预期文件、风险和 operation IDs；
4. 用户批准明确 operation 后生成 Starter；
5. 完成最小访谈，再单独审阅并批准 personalize/environment plan；
6. 建立只包含批准 Vault 路径的 Git baseline commit；
7. 运行只读 verify，并用一个真实问题跑通“来源 → 知识 → 项目/决策 → 交付 → 结果回写”。

每个写入阶段都需要独立计划与授权。Skill 不会静默安装软件、覆盖旧库、创建远程仓库、push、批量安装插件或修改全局 Git 配置。

## 维护者验证

```bash
python3 -I -S -E skills/bootstrap-second-brain/scripts/sync_starter_assets.py --check
python3 -m unittest discover -s skills/bootstrap-second-brain/tests -p 'test_*.py'
python3 skills/bootstrap-second-brain/evals/run_evals.py --suite all
python3 skills/bootstrap-second-brain/scripts/package_skill.py --check
python3 skills/bootstrap-second-brain/scripts/package_skill.py --write
```

`package_skill.py --write` 只生成本地 build-only 的确定性 ZIP 与 SHA-256，不是独立 ZIP 发布成功证据。独立 ZIP 必须在 `--verify-release` 完成 OpenSSH 双签名、包内容和许可证校验后，才能跨机器分发或安装；这与 GitHub 源码发布是两个证据层。

## 发布策略

- 发布许可：MIT，仓库根目录和 Skill 分发包内均携带完整许可证。
- 正式源码发布：先提交全部授权变更并确认 staged、unstaged、untracked 均为空，再冻结 `release_commit`。将该 commit 推送到 canonical GitHub 分支，核验远端 SHA 与 `release_commit` 一致，并确认该远端 commit 包含 `LICENSE`、`README.md` 和 `skills/bootstrap-second-brain/SOURCE.md`，才视为发布成功。
- 独立 ZIP 分发：SHA-256 只证明字节一致；未通过 `--verify-release` 的 ZIP 不得跨机器分发或安装。验证使用 bundle/attestation 双签名、独立渠道 Owner 公钥指纹和可信 OpenSSH verifier。
- 发布成功不等于真实用户成效已验证；`initialized`、`activated`、pilot 和 proven 仍按各自证据门禁判断。

## Skill 支持边界

- v0.1 正式支持 Codex、macOS 和 Python 3.11+；Linux 仅保留文件系统兼容候选，Windows 延后。
- 支持 create、verify、create-run resume，以及 adopt-existing 的只读 inventory/接管计划。
- 默认离线，不自动 sudo、下载、安装社区插件、修改全局 Git 配置、创建 remote 或 push。
- 源码与 Skill 采用 MIT 许可证；正式 GitHub 源码发布必须满足上述 `release_commit` 与远端核验门禁。
- 未完成外部签名验证的独立 ZIP 只能声明 `distribution_authentication=unverified`，不能宣称已验证发布者来源。
- 安装、结构生成、Git baseline 和 activated/proven 是不同证据层，不能相互补偿。

## 使用边界

第一版不需要 Memory OS、RAG、语义检索、插件或自动化。只有真实失败反复出现时再升级；原件不被摘要覆盖，Candidate 不自动变成事实，高风险操作保留人工确认。

## 加入群聊

👥 欢迎加入微信群聊：

<img src="docs/image.png" alt="群聊：研发效能（spec-first）" width="360" />

与业界大牛一起探讨 AI 与第二大脑、超级个体、企业研发效能的落地实践。
