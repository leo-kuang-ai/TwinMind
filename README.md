# TwinMind：本地优先的个人第二大脑 Starter Kit

TwinMind 把“搭建个人第二大脑”拆成两部分：一份可以直接复制的 Vault 示例，以及一个负责检查、规划、授权、初始化和验证的 Codex Skill。它适合希望先从可控的文件夹和 Markdown 开始，再逐步建立个人知识工作流的人。

从 15 分钟 Quick Start 开始（见下），或先读设计取舍长文[《个人第二大脑搭建指南：5万字讲透架构、AI协作与进化》](https://mp.weixin.qq.com/s/8Gq9vFm44EFm_7nBW7znAA)。

本项目采用 [MIT License](LICENSE) 开源发布。

## 15 分钟 Quick Start

**路径 A（零终端，任何人）**：GitHub 网页上点 **Code → Download ZIP** 解压取 [`我的第二大脑/`](我的第二大脑/) 文件夹（或 git clone 后取该目录），放到你喜欢的位置，然后按 [`我的第二大脑/README.md`](我的第二大脑/README.md) 的"第一次使用"五步走——读协议、填启动契约、写下三个真实问题、跑通一个闭环、留复盘。

全部能力（治理规则、模板、任务契约、巡检/周报/体检节奏）即刻可用，任选 AI 宿主协作。

**路径 B（终端 + Codex，推荐给想走完整工程链的人）**：安装 [`bootstrap-second-brain`](skills/bootstrap-second-brain/) Skill，它会先验证 Python 3.11+ 与 Git，再以可审查计划 + 逐项授权的方式初始化、打 Git baseline 并做只读验证——见下文"使用初始化 Skill"。

## 它解决什么

| 场景 | 裸 Markdown 文件夹 | 传统笔记工具 | TwinMind |
| --- | --- | --- | --- |
| 结构随使用演化 | 靠自律，易腐化 | 被产品形态锁定 | 九区职责 + 升级门禁（真实失败反复出现才扩容） |
| AI 协作边界 | 无，易越权 | 视产品而定 | 协议三档权限 + 证据分级 + 冲突/覆盖决策登记 |
| 可验收与可回滚 | 无 | 导出即终点 | Git baseline + 到期巡检 + 周报体检 + 三十天验收清单 |

## 常见问题

- **不用 Codex / 不装 Skill 能用吗？** 能。Skill 只负责检查、授权、初始化与验证这些工程动作；内容层（协议、模板、任务契约、流程文档）复制即用。
- **和自己建一堆 Markdown 文件夹有什么区别？** 区别在治理与节奏：证据分级让"检索到 ≠ 可作为依据"，冲突登记防静默合并，任务契约默认不接调度器，每周 30 分钟三步卡（[巡检 → 体检 → 周报](我的第二大脑/README.md#每周-30-分钟三步卡)）让库产生日常回报而非无限堆积。
- **我的数据在哪、会被上传吗？** 全部是本地文件夹 + 本地 Git；默认离线，不创建远程仓库、不 push、不装插件。
- **什么时候才需要语义检索/RAG？** 本项目刻意不预装：当"准确关键词仍稳定漏召回"的真实失败反复出现并登记后，才按[工具选择与升级门禁](我的第二大脑/30_知识主题/工具选择与升级门禁.md)评估升级——在那之前，先把每次"找不到"记到维护日志，这就是未来的升级依据。

## 小词典

Vault（你的第二大脑根目录）｜Demo（本仓库的 `我的第二大脑/` 示例文件夹）｜run / run-id（一次初始化或恢复流程的标识，用于 resume 与收据绑定）｜控制文件（协议/索引/加载清单/维护日志）｜Starter（本仓库的可复制初始内容）｜Candidate（候选知识，未经门禁不得当事实）｜任务状态五档 draft/pilot/active/paused/retired（默认 draft，不接调度器）｜数据域（restricted/confidential/session_only，管访谈数据持久化）｜managed-block（受同步保护的内容区块）｜收据 receipt（工具验证/授权的可校验凭证）｜Git baseline（首次批准提交，恢复的锚点）｜巡检（按 review_at 只读列出到期页）

## 你将得到什么

- 九区目录：`00 / 10 / 20 / 30 / 40 / 50 / 60 / 90 / 99`，每区自带一份用途 README
- 根目录随附文件：`AI协作协议.md`、`加载清单.md`、`知识库索引.md`、`维护日志.md`、`AGENTS.md`（仅随路径 A 的 Demo——即本仓库 `我的第二大脑/` 示例文件夹——提供，Skill `create` 不生成）、`.gitignore`
- 一页启动契约
- 五个第一周模板：来源、知识、项目、决策、交付；另有按需使用的学习回放、任务契约、周报与跟踪立项模板
- 一份建设与运行指南：四阶段路线、日/周/月/季度任务、知识与能力进化门禁
- 一个任务运行控制层：任务注册表、7 个默认 `draft` 的日/周/月/季度任务，以及调度、权限、失败和停止契约；任务定义带审计字段（prompt 快照/摘要哈希/事实源声明），每档状态迁移有门禁，WorkBuddy 接入有可选映射指南
- 治理规则：证据四级分级、冲突登记、覆盖决策登记（协议三节），知识页治理字段（authority / review_at / evidence_note）与内容级密级标注
- 运转节奏：到期巡检（含只读巡检脚本 `review_due.py`）、每周知识体检清单、周报模板（含维护耗时与收缩决定）、维护日志六段式
- 摄取与跟踪：来源包结构与完整性规范、轻摄取/决策级两档、跟踪型项目立项模板（基线+游标+验收闸门）
- 一份建设与运行方法论总纲：三层设计、一核五种协同能力、价值闭环、阶段验收与停止条件
- 七份校准后的配套参考：字段状态、七天/三十天清单、完整工具清单、工具升级门禁、反熵检查、七阶学习闭环、决策学习与三环进化

> 这套方法论来自一个经过 600+ 次真实提交验证的个人生产知识库的抽象（仅引用规模，不包含任何私人内容）。

## 从哪里开始

新建走上文 Quick Start 的路径 A 或路径 B；已有 Vault 用 Skill 的 `verify`（零写入体检）、`adopt-existing`（只读盘点，不合并资料）、`resume`（仅执行当前 run 中再次批准的操作）——各命令的写入范围与请求话术见下节。

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

### 开始前准备（按路径二选一）

- **路径 A（零终端）**：会复制文件夹、会用任意 AI 宿主读 Markdown 即可；Git 可稍后补（用于历史与恢复）。
- **路径 B（终端）**：
  - Python 3.11+：运行时必需。
  - Git：产品级硬门禁，用于版本管理、baseline commit 和恢复；缺失时不会开始创建 Vault。
  - WorkBuddy（[官网](https://www.workbuddy.ai/)）：推荐的协作调度入口，适合承接任务契约的定时执行，接入方式见 [WorkBuddy 接入映射](我的第二大脑/60_任务系统/20_WorkBuddy接入映射.md)；不接入也不影响任何功能。
  - Obsidian：推荐工具，可以在明确知情后暂缓；社区插件可选，默认不安装，只有真实需求出现后才逐项评估来源、权限、成本和维护风险。

### 标准工作流

1. 只读检查必需工具（Python、Git）与推荐工具（WorkBuddy、Obsidian）的可信来源与可用状态；
2. 确认目标绝对路径、父级 Git 边界、隐私数据域和恢复方式；
3. 生成带摘要的 scaffold plan，展示预期文件、风险和 operation IDs；
4. 用户批准明确 operation 后生成 Starter；
5. 完成最小访谈，再单独审阅并批准 personalize/environment plan；
6. 建立只包含批准 Vault 路径的 Git baseline commit；
7. 运行只读 verify，并用一个真实问题跑通“来源 → 知识 → 项目/决策 → 交付 → 结果回写”。

每个写入阶段都需要独立计划与授权。Skill 不会静默安装软件、覆盖旧库、创建远程仓库、push、批量安装插件或修改全局 Git 配置。

## 已初始化的库如何升级

已经用旧版 TwinMind 初始化过的 Vault，按"对照吸收"方式获得新内容，全程无自动迁移。对照入口：`CHANGELOG.md` 当前批次条目、Skill 包内 `manifests/starter-v1.json` 的 files 清单（新版全量文件表），以及 Demo `维护日志.md` 的收口条目；`知识库索引.md` 的 Starter 版本行可确认你差哪一版：

| 类别 | 处理方式 |
| --- | --- |
| 可安全对照更新 | 根控制文件（`AI协作协议.md`、`加载清单.md`、`知识库索引.md`）、`90_模板/` 下的模板、`30_知识主题/` 与 `99_维护记录/` 的流程文档；新增目录（如 `60_任务系统/`）按变更清单整目录对照——逐份对照新版差异，选择要吸收的部分；你的既有填写的字段不要被模板占位值覆盖 |
| 你的内容，不要动 | 九个分区里你自己写的页面（`00`~`40`、`90` 里已填的实例、`99` 的历史记录） |
| 辅助入口 | 用 `verify` 做一次零写入体检看结构差异；用 `adopt-existing` 只读盘点非 TwinMind 库；两者都不会合并或覆盖内容 |

升级后建议跑一次每周知识体检清单，把新增治理字段（authority / review_at / evidence_note）逐页补到高频知识页，而不是全量补齐。`维护日志.md` 只把头部六段式规范段并入你的现有日志顶部，历史条目原样保留、不回填。

## 版本口径

Starter 内容版本（`starter-v1.json` 的 `starter_version`，当前 0.2.0）与工程变更日志版本（仓库 `CHANGELOG.md` 的 v1.x 序列）是两套并存的口径：前者标识你库里的 Starter 内容代次，后者标识仓库工程演进。

## 使用边界

第一版不需要 Memory OS、RAG、语义检索、插件或自动化。只有真实失败反复出现时再升级；原件不被摘要覆盖，Candidate 不自动变成事实，高风险操作保留人工确认。

## 维护者与发布参考

### 维护者验证

```bash
python3 -I -S -E skills/bootstrap-second-brain/scripts/sync_starter_assets.py --check
python3 -m unittest discover -s skills/bootstrap-second-brain/tests -p 'test_*.py'
python3 skills/bootstrap-second-brain/evals/run_evals.py --suite all
python3 skills/bootstrap-second-brain/scripts/package_skill.py --check
python3 skills/bootstrap-second-brain/scripts/package_skill.py --write
```

其中 evals 命令是静态合同校验（含 SKILL.md 安全锚点核对），不执行模型行为；行为级证明由 skill-up forward eval 承担并另行排期。

`package_skill.py --write` 只生成本地 build-only 的确定性 ZIP 与 SHA-256，不是独立 ZIP 发布成功证据。独立 ZIP 必须在 `--verify-release` 完成 OpenSSH 双签名、包内容和许可证校验后，才能跨机器分发或安装；这与 GitHub 源码发布是两个证据层。

### 发布策略

- 发布许可：MIT，仓库根目录和 Skill 分发包内均携带完整许可证。
- 正式源码发布：先在 canonical 分支 `main` 上合入全部授权变更（未合并的分支提交须先合并/推送），确认 staged、unstaged、untracked 均为空，再冻结 `release_commit`。将该 commit 推送到 canonical GitHub 分支，核验远端 SHA 与 `release_commit` 一致，并确认该远端 commit 包含 `LICENSE`、`README.md` 和 `skills/bootstrap-second-brain/SOURCE.md`，才视为发布成功。
- 独立 ZIP 分发：SHA-256 只证明字节一致；未通过 `--verify-release` 的 ZIP 不得跨机器分发或安装。验证使用 bundle/attestation 双签名、独立渠道 Owner 公钥指纹和可信 OpenSSH verifier。
- 发布成功不等于真实用户成效已验证；`initialized`、`activated`、pilot 和 proven 仍按各自证据门禁判断。

### Skill 支持边界

- 当前版本（Starter 0.2.0）正式支持 Codex、macOS 和 Python 3.11+；Linux 仅保留文件系统兼容候选，Windows 延后。
- 支持 create、verify、create-run resume，以及 adopt-existing 的只读 inventory/接管计划。
- 默认离线，不自动 sudo、下载、安装社区插件、修改全局 Git 配置、创建 remote 或 push。
- 源码与 Skill 采用 MIT 许可证；正式 GitHub 源码发布必须满足上述 `release_commit` 与远端核验门禁。
- 未完成外部签名验证的独立 ZIP 只能声明 `distribution_authentication=unverified`，不能宣称已验证发布者来源。
- 安装、结构生成、Git baseline 和 activated/proven 是不同证据层，不能相互补偿。

### 五份原附录的取舍

- **A 目录与字段**：原目录已过时，不原样复制；保留校准后的 [字段与状态速查](我的第二大脑/90_模板/字段与状态速查.md)；
- **B 七天与三十天**：纳入 [七天冷启动与三十天验收清单](我的第二大脑/99_维护记录/七天冷启动与三十天验收清单.md)；
- **C Memory OS 命令**：不纳入假设命令，Demo 没有 `tools/memory.py`；运行方法见 [定时任务与知识进化](我的第二大脑/99_维护记录/定时任务与知识进化.md)，可执行契约见 [任务注册表](我的第二大脑/60_任务系统/00_任务注册表.md)；
- **D 工具技术栈**：移除易过期价格、版本、固定时间和错误字段口径；完整目录纳入 [第二大脑完整工具清单](我的第二大脑/30_知识主题/第二大脑完整工具清单.md)，升级判断纳入 [工具选择与升级门禁](我的第二大脑/30_知识主题/工具选择与升级门禁.md)；
- **E 失败与反熵**：修正旧路径和硬阈值，纳入 [每月检查与季度反熵清单](我的第二大脑/99_维护记录/每月检查与季度反熵清单.md)。

## 加入群聊

👥 欢迎加入微信群聊：

<img src="docs/image.png" alt="群聊：研发效能（spec-first）" width="360" />

与业界大牛一起探讨 AI 与第二大脑、超级个体、企业研发效能的落地实践。

## 反馈

- 问题与建议：[GitHub Issues](https://github.com/sunrain520/TwinMind/issues)，附上 `verify` 报告与复现步骤更易被处理；
- 交流：上方微信群。
