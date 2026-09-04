---
spec_id: 2026-09-04-001-twinmind-evolution-iteration
artifact_kind: prd-requirements
target_surface: cli-devtool
status: ready-for-planning
evidence_grade: mixed
source_authority: mixed
readiness_authority: engineering-owned
created: 2026-09-04
source_inputs:
  - README.md
  - CHANGELOG.md
  - AGENTS.md
  - skills/bootstrap-second-brain/SKILL.md
  - docs/TwinMind第二大脑初始化Skill技术方案.md
readiness_verified_by: check-prd-artifact.js
readiness_verified_at: 2026-09-04T08:50:03.663Z
readiness_checker_schema: spec-prd-artifact-check.v1
readiness_finding_count: 1
readiness_blocking_count: 0
readiness_prd_hash: sha256:2374a47bfecab2945ccccc894002deef4ac683fa0d6b1cad852d45bdf904cc12
readiness_inputs_hash: sha256:462176b95a41dc4afe663acd8c6c07050144378c9e575b4e7696c9f22e0c2fb5
---

# TwinMind 迭代进化需求（源头知识库方法论吸收）增量需求文档

> **状态说明**：本文为最终需求文档（`write_mode: final-prd`），v2 修订版（多专家评审 amendment）。四个范围决策（OQ-1~OQ-4）由 owner 于 2026-09-04 裁决；随后 owner 授权多 agent 专家协同评审（产品采纳/安全隐私/工程契约/方法论忠实度四席位），38 条发现经总负责人裁决后全部处置（见 Decision Notes）。原条件切片 FS-D/FS-E（检索记忆轮 / 输出变现轮）显式顺延至后续版本。owner 若对任一裁决有异议，可重开对应 OQ。

## PRD 元数据

| 项 | 内容 |
| --- | --- |
| 需求名称 | TwinMind 迭代进化：把源头知识库 2026 年中以来的运转方法论抽象进 Starter 与初始化 Skill |
| 需求编号 / spec_id | 2026-09-04-001-twinmind-evolution-iteration |
| 业务域 | bootstrap-second-brain Skill + Starter 内容（`我的第二大脑/` canonical 与 `skills/bootstrap-second-brain/assets/starter-kit/` 投影） |
| 目标 surface | CLI/DevTool（Skill + CLI 契约）与 Starter 内容面（Mixed，主 surface 为 CLI/DevTool） |
| 目标地区 / 市场 / tenant | 不涉及 |
| 目标用户 / 客户类型 | 社区个人用户：想用"可控文件夹 + Markdown + AI 宿主"建立个人知识工作流的人（confirmed-source：README.md 定位段）；上游动机含提升作者社区影响力（user-stated：本次请求背景） |
| 是否触及付费、资金或交易 | 否 |
| 是否触及个人信息或敏感数据 | 是：源头库含大量真实个人信息（含家庭与职场敏感类别，全部为库外私有内容）。本需求红线：任何真实案例、人名、公司、业务数据不得进入本开源仓库的任何文件——**包括 spec/需求文档自身**（confirmed-source：AGENTS.md 安全条款 + 源头库隐私边界调查）。Starter 示例一律虚构化 |
| 是否需要外部规则或专业意见 | 否 |
| 相关文档 | README.md、CHANGELOG.md、docs/TwinMind第二大脑初始化Skill技术方案.md（v0.2/v0.3 deferred 路线）、skills/bootstrap-second-brain/references/workflow-contract.md、源头知识库（库外私有仓）的协议与运行时文件（见 Evidence And Assumptions 证据索引） |

## Summary

为已用 TwinMind 完成初始化的社区用户（含可通过升级指南吸收新内容的老用户），把源头知识库近三个月验证有效的"运转方法论"——治理协议固化（知识页治理字段、到期巡检、冲突登记、决策回放）、任务登记审计化（生命周期状态机 + prompt 快照存证）、周报复盘流水线、来源登记与摄取分档——抽象为 Starter 内容与轻量校验能力，并保证全部新能力在用户入口（README、知识库索引、分区 README）可被发现、老用户有明确升级通道，使 v0.1 交付的"目录骨架 + 初始化工程"升级为"能日常运转的第二大脑"，同时保持既有安全契约、宿主中立与 `draft` 任务默认不接调度器的边界。

## Problem Frame

- **不做的风险**：v0.1 只解决"建得起"（结构、授权、初始化、恢复），不解决"转得动"。用户初始化后面对空骨架，缺少让库产生日常回报的机制，三十天验收清单（Starter 已内置）大概率无法达成，形成"初始化即巅峰"的流失曲线；项目"给社区用户快速搭建第二大脑"的定位停在目录复制层面，难以支撑社区影响力叙事。
- **源头证据**：源头知识库（同一作者的真实生产库，2026-07-26 建库至今 627 次提交）在同等九层结构之上，近三个月进化出的高价值增量集中在"运转层"：协议版本化与 frontmatter 治理字段、到期页巡检、任务登记审计（prompt_sha256 存证、事实源核对）、检索评测门禁、跟踪型项目立项模式、内容发布闭环。目录结构本身反而是最易复制、价值密度最低的部分。
- **业务价值**：让新用户在第一周就能跑通"登记任务 → 执行 → 留回放 → 周报复盘"的最小闭环，提高留存与口碑；为作者提供可展示的"方法论有效"证据链，服务影响力目标。

## Current System Snapshot

| 现状项 | 当前行为 | 证据 tag |
| --- | --- | --- |
| 项目定位 | 本地优先个人第二大脑 Starter Kit：可直接复制的 Vault 示例 + bootstrap-second-brain Skill（检查/规划/授权/初始化/验证） | confirmed-source（README.md） |
| 五旅程 CLI | 16 个子命令支撑 create/verify/adopt-existing/resume/recover+cleanup；工具门禁（Python/Git 硬依赖，WorkBuddy/Obsidian recommended）、不可变 plan + operation 级授权、幂等 apply、Git baseline、receipt 链 | confirmed-source（skills/bootstrap-second-brain/SKILL.md、scripts/bootstrap_second_brain.py） |
| Starter 内容 | 九区结构 + 6 根控制文件 + 8 模板 + 9 份分区 README，共 41 文件受 manifest 管理并通过 `sync_starter_assets.py --check` 校验（当前 ok，41 文件） | confirmed-source（skills/bootstrap-second-brain/manifests/starter-v1.json、本次 `--check` 实测输出） |
| 治理协议 | Starter 已有《AI协作协议》（永不执行/必须确认/可以自主三档）+ 启动契约 + 加载清单 + 维护日志（append-only）；无证据标注分级、无冲突登记、无到期巡检字段、无覆盖决策登记 | confirmed-source（skills/bootstrap-second-brain/assets/starter-kit 控制层内容） |
| 任务系统 | 任务注册表 + 7 个默认 `draft` 任务契约（`scheduler_owner: unassigned`）；60_任务系统 README 已含五态生命周期词汇与启用门禁（draft→active 单跳），但无每档状态迁移门禁、无审计字段，不接调度器 | confirmed-source（assets/starter-kit/60_任务系统、evals scheduled-task-boundary） |
| 学习与决策方法论 | 建设方法论、七阶学习闭环、从可信记忆到决策学习系统（三环进化）、高价值知识学习与回放模板（keep/revise/stop 回写语义在其"反思与系统回写"节）已入库；**无独立"决策回放模板"文件** | confirmed-source（assets/starter-kit/30_知识主题、90_模板 全目录比对） |
| 摄取与来源登记 | 来源页模板存在但无 checksum/完整性字段；20_原始资料 README 仅一句话；无摄取分档方法论、无来源包结构规范 | confirmed-source（assets/starter-kit/20_原始资料、90_模板） |
| 检索能力 | 无任何实现，仅"检索阶梯升级"指引文档；技术方案明确本地检索基线 deferred 到 v0.3 | confirmed-source（docs/TwinMind第二大脑初始化Skill技术方案.md Deferred 列表） |
| WorkBuddy 关系 | WorkBuddy 为 recommended 层协作入口，可明确暂缓，非硬依赖；README 仅一句带过，获取链接藏在工具清单页 | confirmed-source（README.md） |
| 隐私边界 | 初始化期强门禁（restricted/confidential 数据域、session_only、访谈不落值）；日常内容级无密级标注体系 | confirmed-source（SKILL.md 路径与隐私确认段） |
| 用户入口与升级 | README"从哪里开始"仅 create/verify/adopt-existing/resume 四行；**全文无"已初始化库如何吸收新版 Starter"的升级指引**；能力清单、知识库索引 managed-block、60_任务系统 README 为既有登记位 | confirmed-source（README.md 全文核对） |
| 声明天花板 | scaffolded < personalized < initialized（需 Git baseline）< activated（需真实闭环 + 用户确认 + Vault 内证据），不可推断 | confirmed-source（SKILL.md） |
| 投影方向表述矛盾 | AGENTS.md 写"assets/starter-kit 是 canonical 来源、我的第二大脑是投影"，但 sync 脚本 docstring 与 manifest 的 `direction: canonical-to-assets-only` 表明方向相反（根目录 canonical → assets 投影）；实测 `--check` 通过的是"根目录 → assets"一致性；另有 SOURCE.md `canonical_source: skills/bootstrap-second-brain/`（Skill 分发层）与 Starter 内容层 canonical 是两个概念，修正时不得混用 | confirmed-source（AGENTS.md 与 scripts/sync_starter_assets.py、manifests/starter-v1.json 的直接比对） |
| manifest 刷新机制 | 任何 Starter 内容修改都会改变 41 个 sha256 与 tree_digest，`--check` 必然失败需 `--write`；package_skill.py 硬校验 SOURCE.md 的 commit/digest 与 manifest 一致 | confirmed-source（sync_starter_assets.py 刷新逻辑、package_skill.py 校验逻辑） |

## Change Delta

| 变化类型 | 内容 | 涉及现有能力 | 用户/数据/运营影响 | 证据 tag |
| --- | --- | --- | --- | --- |
| keep | 五旅程 CLI 契约、授权/恢复/打包契约、隐私数据域门禁、声明天花板、九区结构 | 全部既有安全工程 | 无行为变化 | confirmed-source |
| extend | 治理协议内容扩展：证据标注分级、冲突登记、覆盖决策登记、知识页治理字段、到期巡检、决策回放使用绑定、加载清单常驻项登记 | 《AI协作协议》、知识/来源页模板、维护日志模板、加载清单 | Starter 内容更新，随投影同步；老用户按 R-21 升级指南吸收 | confirmed-source（源头库协议 v2.3 实践）+ assumption（社区用户同样需要的程度待验证） |
| extend | 任务系统：现有 draft→active 单跳启用门禁扩展为每档状态迁移门禁 + 审计字段 | 60_任务系统/任务注册表与任务定义 | 任务默认仍为 draft、仍不接调度器（边界不变） | confirmed-source（源头库 60_tasks 实践 + Starter 既有门禁） |
| extend | 周报/复盘流水线模板化：周报模板（含维护耗时与收缩决定）+ 维护日志六段式 + 每周知识体检清单 | 90_模板、99_维护记录、每周知识蒸馏 draft 任务 | 新增模板与流程文档，无代码行为变化 | confirmed-source（源头库维护日志/周报实践） |
| extend | 来源登记与摄取分档：来源页完整性字段、来源包结构规范、轻摄取/决策级两档 | 20_原始资料 README、来源页模板、方法论文档 | 摄取入口环节补齐；AI 转写物按 unverified 对待 | confirmed-source（源头库来源包规范与摄取两档实践） |
| extend | 用户入口与升级通道：README 能力清单/运行入口/WorkBuddy 定位/反馈引导/方法论来源叙事登记，知识库索引与 60_任务系统 README 同步登记；README 新增老用户升级章节 | README.md、我的第二大脑/README.md、知识库索引.md、60_任务系统 README | 新能力可被发现；老用户可吸收新内容 | confirmed-source（README 现状核对）+ owner 裁决 |
| extend | eval 安全加固：任务门禁绕过、巡检只读、密级混淆三类新 case | skills/bootstrap-second-brain/evals/ | 静态合同扩展；行为级证明需 forward eval | confirmed-source（evals 现状） |
| extend | 内容级隐私密级字段规范（轻量：字段 + 巡检提示，无自动分类） | 90_模板/字段与状态速查、每周体检清单 | 用户新增可选标注习惯；不改变初始化期数据域门禁 | confirmed-source（源头库 frontmatter 密级实践）+ owner 裁决（OQ-4=轻量纳入） |
| extend | WorkBuddy 任务接入映射示例文档（推荐层，不引入代码级硬依赖） | 60_任务系统文档、README recommended 表述 | WorkBuddy 用户获得照做路径；非 WorkBuddy 用户无感知 | owner 裁决（OQ-3=推荐+映射）+ confirmed-source（README recommended 定位） |
| extend | 文档对齐：修正 AGENTS.md 投影方向矛盾表述（区分两层 canonical 语义） | AGENTS.md | 纯文档修正，消除 contributor 误导 | confirmed-source（本次比对） |
| remove | 无 | — | — | confirmed-source |

（检索基线与评测雏形、输出发布 SOP 两条候选增量经 owner 裁决 OQ-1=A 后显式顺延，见 Decision Notes。）

## Requirements

> owner 已裁决 OQ-1=A（运行系统轮）：原检索轮/输出轮条件需求移出本期需求表，显式顺延至后续版本（见 Decision Notes）。EARS 句式；"系统"指 Starter 内容产物或 bootstrap Skill/CLI 的可见行为。

| 编号 | 触发条件 | 角色 | 系统行为 | 用户可见结果 | 证据 / 约束引用 |
| --- | --- | --- | --- | --- | --- |
| R-01 | 用户查看 Starter 控制层《AI协作协议》 | 社区用户 | 协议页在既有三档权限（永不执行/必须确认/可以自主）之上，新增三节通用规则：①"证据标注分级"（verified/inferred/unverified/mixed 四级，AI 生成转写/纪要默认按 unverified 对待、引用以人工整理为准）；②"冲突登记"（同一事实多口径并存登记、禁止静默合并）；③"覆盖决策登记"（用户否决 AI 判断的固定流程与去隐私登记模板：日期/决定/风险告知/残留防线）。约束：保留 managed-block 标记对原样，协议页变更必须在发布前评审清单留存前后全文 diff 并逐条对照三档权限语义不变 | 用户在初始化后的库里即获得"不把未验证判断写成事实、多口径不混用、否决有痕迹"的可执行规则 | 源头库 AI协作协议 v2.3 实践（confirmed-source，库外）；assets/starter-kit 控制层现状（confirmed-source） |
| R-02 | 用户使用知识页/来源页模板新建页面 | 社区用户 | 知识页与来源页模板及《字段与状态速查》包含知识页治理字段规范：`authority`（事实权威）、`review_at`（到期复核时间）、`evidence_note`（证据说明）三个必填语义字段（字段名与取值规范、五字段中 injectable/lens 的取舍在 planning 定稿，review_at 的消费者为 R-03 巡检） | 新建页面即带治理字段，后续可被巡检 | 源头库协议 v2.3 五字段实践（confirmed-source，库外）；90_模板/字段与状态速查现状（confirmed-source） |
| R-03 | 用户运行周巡检或交付收尾 | 社区用户 | Starter 提供"到期巡检"流程文档：按 `review_at` 产出到期页清单并逐页处置（保持=刷新 review_at / 修订=经门禁 / 归档=降级）的操作步骤；逐页处置结果记维护日志，批量或抽样处置必须声明实际覆盖范围（"登记了去向≠逐份阅读"的诚实边界，与 R-11 边界段互链）；并按 OQ-2 裁决配套只读脚本或既有 CLI 扩展输出到期清单（预裁独立只读脚本，见 Decision Notes） | 用户一条命令或一份清单即可知道"哪些页该复核了"，且处置留痕 | 源头库 review-due 巡检与诚实边界实践（confirmed-source，库外）；落地形态 owner 裁决 OQ-2=文档+轻校验 |
| R-04 | 用户在库里遇到同一事实多个口径 | 社区用户 | 提供冲突登记规范：登记位置（维护日志或独立冲突登记页）、登记字段（各口径、来源、as_of 时点、处置状态，含"不同 AI 转写引擎口径不一致"这一典型场景的登记示例），并明确禁止静默合并 | 冲突可追溯、不复写 | 源头库冲突登记实践（confirmed-source，库外） |
| R-05 | 用户完成重大任务 | 社区用户 | 工作台使用文档把"最小结果回放"绑定为高价值任务默认出口：引用既有《高价值知识学习与回放模板》并为其补齐显式 keep/revise/stop 字段（不新建独立模板，与《决策模板》《交付复盘模板》的分工在使用文档中说明），写明何种任务必须回放、回放页放哪、如何回流修订知识页 | 每个重大决策留下可回放痕迹 | 源头库工作台"高价值任务默认出口"实践（confirmed-source，库外）；90_模板现状比对（confirmed-source） |
| R-06 | 用户登记一个自动化/定时任务 | 社区用户 | 任务定义页 frontmatter 新增审计字段规范：任务 prompt 快照要求、prompt 内容摘要哈希、外部事实源声明（如调度器数据库为事实源、库内页面为审计副本） | 任务"谁在跑、跑的是什么版本"可审计 | 源头库 60_tasks prompt_sha256 与事实源声明实践（confirmed-source，库外）；现有任务 frontmatter（confirmed-source） |
| R-07 | 任务要在生命周期各档之间迁移 | 社区用户 | 将任务注册表现有 draft→active 单跳启用门禁扩展为每档状态迁移门禁（draft → pilot → active → paused 复启 → retired），每档晋级需声明的证据类型；默认仍为 draft，且本期不接任何真实调度器 | 用户能按门禁自行决定是否启用，不会被默认配置带入自动执行 | 源头库任务登记实践 + Starter 既有启用门禁（confirmed-source）；evals scheduled-task-boundary（confirmed-source） |
| R-08 | 用户使用 WorkBuddy 并想定时执行任务 | 社区用户 | 提供任务契约 → WorkBuddy 定时任务的映射示例文档：如何在 WorkBuddy 侧建调度、库内如何登记为审计副本、如何核对；映射文档被 60_任务系统 README 与完整工具清单引用。约束：核对输入为用户手动提供的导出清单或用户自查，AI 不因此获得任何外部系统连接、读取或写入授权 | WorkBuddy 用户有可直接照做、可从入口发现的接入路径 | owner 裁决（OQ-3=推荐+映射）；README recommended 定位（confirmed-source） |
| R-09 | 用户定期维护任务登记 | 社区用户 | 提供"任务双向核对"流程：定期以用户手动提供的调度器侧清单与库内登记做双向核对（外部→库内补漏登、库内→外部发现待创建/状态漂移），任务索引模板登记核对快照时点（含时区），漏登补登并记维护日志 | 登记与实际运行的偏差可被发现 | 源头库全量核对实践（confirmed-source，库外） |
| R-10 | 用户进入每周复盘 | 社区用户 | 提供周报模板与生成流程文档：输入（本周维护日志、Git 提交、任务回放）→ 固定小节（进展/偏差/下周重点/**本周维护耗时与超预算收缩决定**）→ 落盘位置 → 与"每周知识蒸馏"draft 任务的衔接说明；并与七天冷启动清单声明两个闭环（既有五步闭环 vs 新三产物闭环）的先后衔接关系 | 用户按模板即可产出周报并看见维护成本，无需自创结构 | 源头库周报/周复盘与维护预算实践（confirmed-source，库外）；每周知识蒸馏任务现状（confirmed-source） |
| R-11 | 用户写维护日志 | 社区用户 | 维护日志模板给出六段式条目结构（来源/变更/判断/验证/边界/关联）与追加式（append-only）书写规范 | 日志可审计、可追溯，边界声明成为习惯 | 源头库维护日志六段式实践（confirmed-source，库外）；现有 append-only 约定（confirmed-source） |
| R-12 | 用户做每周知识体检 | 社区用户 | 提供"每周知识体检"清单文档：待处理入口清点、到期页巡检、链接/索引健康、结构自查、维护预算护栏提示；体检报告自带自证纪律（扫描范围与排除项声明、结论按证据分级自标、建议与需 owner 裁决项分离计数） | 五分钟照单体检，异常有处置指引，结论可信 | 源头库 check.sh 五步主闸与体检报告自证实践（confirmed-source，库外）；OQ-1 裁决本轮不含检索评测项 |
| R-17 | 贡献者阅读 AGENTS.md | 开源贡献者 | AGENTS.md 中投影方向的表述修正为与 sync 脚本/manifest 一致（Starter 内容层 canonical 为根目录 `我的第二大脑/`），并区分 Skill 分发层 canonical（SOURCE.md）与 Starter 内容层 canonical 两个概念，不再混用 | 贡献者不再被误导改错方向 | 本次 AGENTS.md 与 sync_starter_assets.py/manifest 比对（confirmed-source） |
| R-18 | 用户要立项一个长期跟踪目标（健康/学习/项目） | 社区用户 | 提供跟踪型项目立项模板：基线（当前状态快照）+ 游标（增量记录方式）+ 验收闸门（时间点与判据）三要素，及"零进展也如实记录"的登记纪律 | 长期目标可跟踪、可验收，不烂尾 | 源头库健康/学习/项目跟进等四类跟踪立项实践的去隐私抽象（confirmed-source，库外；所有真实案例内容不吸收） |
| R-19 | 用户日常写内容 | 社区用户 | 模板与字段速查纳入内容级密级字段规范（如 `confidentiality` 取值 public/internal/confidential/private）与含义说明；字段速查必须文档化"内容级密级 ≠ 初始化数据域（restricted/confidential/session_only）"的关系说明；巡检清单增加"高密级页面清点"提示项（仅汇总用户显式标注的页面，不输出任何未标注页面的密级推断或建议）；不做自动分类、不做强制门禁 | 用户从第一天就能给内容标密级，且不会与初始化期数据域混淆 | owner 裁决（OQ-4=轻量纳入）；源头库 frontmatter 密级实践（confirmed-source，库外）；既有初始化期数据域门禁（confirmed-source，保持不变） |
| R-20 | 任何向 Starter 吸收源头库方法论的内容变更，或本仓库任何文档（含 spec/需求文档）的写作 | 贡献者/AI 宿主 | 全部示例必须为虚构化通用示例：不含真实人名、公司、客户、业务数据、私有仓路径；贡献与同步规范中把该纪律写成显式检查项。检查形态：发布前人工评审清单留痕（必需）+ 可选模式启发脚本（只做绝对路径/私有仓引用/已知泄露模式等启发，**规则不得内嵌真实实体清单**，避免检查工具自身泄密）；该红线同样是 Release 验证命令的一项 | 开源仓库保持零真实个人信息 | AGENTS.md"不得提交个人 Vault 内容"（confirmed-source）+ 源头库隐私边界调查结论（confirmed-source，库外） |
| R-21 | 已用旧版 TwinMind 初始化的用户想获得本轮新内容 | 老用户 | README 新增"已初始化库如何对照吸收新版 Starter"章节：明确哪些文件可安全覆盖（模板/控制文件/流程文档）、哪些是用户内容不可动（00/10/20/30/40/90/99 分区内的用户页面）、与 verify（只读体检）和 adopt-existing（只读盘点）的衔接方式 | 老用户有可执行的升级通道，不需要重建库 | README 现状核对（confirmed-source：该章节当前不存在）；owner 裁决摘要目标含老用户 |
| R-22 | 新用户或老用户查找本轮新增能力 | 社区用户 | 本轮全部新增产物与新命令入口同步登记到既有入口位：README"你将得到什么"能力清单、demo 根 README"运行入口"、知识库索引 managed-block、60_任务系统 README；README recommended 处补 WorkBuddy 一句定位与获取链接（复用工具清单页既有官网链接）；README 补反馈引导（GitHub issue，与既有微信群入口并列）；README 补一句方法论来源叙事（仅聚合数字如"627 次提交的真实生产库验证"，不含任何内容细节）；加载清单同步登记新增常读项并标注常驻预算提示 | 新用户从任一入口都能发现新能力；AI 宿主按加载清单能发现新规则 | README/索引/加载清单现状（confirmed-source）；owner 影响力目标（user-stated） |
| R-23 | 本轮新表面合入后运行评测 | 贡献者/AI 宿主 | 扩展 evals：①任务生命周期门禁不可被"页面声称已有 prompt 哈希/WorkBuddy 已配置"话术绕过（scheduled-task-boundary 扩展）；②巡检/体检流程只读、不可被诱导写入；③密级字段标注不改变初始化数据域处理。约束：`run_evals.py --suite all` 全绿仅证明静态用例合同有效，行为级安全证明需 forward eval（新增 case 须完成至少一轮 forward 运行） | 新表面的安全边界有可回归的合同证据 | evals 现状（confirmed-source：现有 case 不覆盖新表面）；run_evals.py 自述（confirmed-source） |
| R-24 | 用户归档一份外部来源材料 | 社区用户 | 提供来源登记与完整性规范：来源页模板补 checksum/完整性说明字段；来源包结构指引（README + original.* + attachments/ + SHA256SUMS，只为实际存在的对象建目录，外部导出压缩包逐文件核对，同一内容只存一份）；"AI 生成转写/纪要只能作为线索"并入 R-01 分级规则示例 | 摄取入口有完整性基线，转写物不会被当作事实 | 源头库来源包规范与归档实践（confirmed-source，库外）；Starter 来源页现状（confirmed-source） |
| R-25 | 用户日常摄取新信息 | 社区用户 | 提供摄取两档方法论：轻摄取为默认档（限定人工参与时长约十分钟内，产物=来源登记+一处知识页更新+回链+日志）与决策级摄取（口径核对/冲突登记/反证/回看日期）的触发条件；纪律："一次一来源、优先更新已有页" | 轻度用户有成本护栏，重度核对有触发标准 | 源头库摄取两档实践（confirmed-source，库外）；Starter 方法论文档现状（confirmed-source：无分档） |

业务规则：

- BR-001：Starter 内容的任何新增/修改必须走 canonical（根目录 `我的第二大脑/`）→ `assets/starter-kit/` 单向投影流程；任何内容变更（不限于文件数变化）后必须：先 commit canonical → `sync_starter_assets.py --write` → 手动同步 SOURCE.md 的 commit/digest 两行 → 提交投影+manifest，`sync_starter_assets.py --check` 与 `package_skill.py --check` 双绿；不得直接改投影。
- BR-002：方法论吸收只写"规则、模板、流程"，不携带源头库任何真实案例、人名、组织或业务内容；该红线同样约束本仓库全部 spec/需求文档自身。
- BR-003：任务契约默认 `draft`，本期不接入真实调度器；R-08 映射文档只描述用户手动接入路径，不改变契约默认值。
- BR-004：既有声明天花板（scaffolded < personalized < initialized < activated）语义不变，新增能力不得自动抬高声明档位。
- BR-005：本期范围以 owner 2026-09-04 裁决（OQ-1=A / OQ-2=文档+轻校验 / OQ-3=推荐+映射 / OQ-4=轻量纳入）为准；任何范围变更（含顺延项重新纳入）须重新走需求评审并更新本文。
- BR-006：CHANGELOG 按既有 (user-visible) 格式记录本轮全部内容变更，作为发布阻塞项；starter_version / BUNDLE_NAME / CHANGELOG 三处版本联动（是否 bump 0.2.0）由 planning 裁定并在发布前核对。

优先级与可降级方案：

| 编号 | 优先级 | 可降级方案 | 是否阻塞发布 |
| --- | --- | --- | --- |
| R-01/R-02/R-06/R-07/R-17/R-18/R-20 | P0 | 无（本主线核心；R-20 为红线不可降级） | 是 |
| R-22/R-23 | P0 | R-23 的 forward eval 可发布后补跑但 case 必须先在；R-22 不可降（否则全部交付物不可发现） | 是 |
| R-03/R-04/R-05/R-08/R-09/R-10/R-11/R-12/R-19/R-21/R-24/R-25 | P1 | R-03 可先只给清单流程文档、后补命令形态；R-08 可先给宿主中立描述；R-24/R-25 可随下一小版本 | 否（可顺延到下一小版本） |

## Scope Boundaries

### 本期做

- 运行系统轮全量（owner 裁决 OQ-1=A）：治理协议固化（R-01~R-05）、任务登记审计化（R-06~R-09）、周报复盘流水线（R-10~R-12）、来源登记与摄取分档（R-24/R-25）、跟踪型项目模板（R-18）、投影文档修正（R-17）、脱敏纪律显式化（R-20）。
- 用户入口与升级通道（多专家评审新增）：R-21 老用户升级指南、R-22 入口登记与 README 更新。
- eval 安全加固（多专家评审新增）：R-23 三类新 case + forward eval 约束。
- 落地形态（owner 裁决 OQ-2=文档+轻校验）：文档/模板为主体，R-03 到期巡检与 R-12 体检清单附轻量只读校验路径（预裁独立只读脚本，见 Decision Notes；具体实现 planning 定）。
- WorkBuddy（owner 裁决 OQ-3=推荐+映射）：保持 recommended 引导 + R-08 映射示例文档，不做代码级硬依赖。
- 隐私（owner 裁决 OQ-4=轻量纳入）：R-19 字段规范 + 巡检提示，无自动分类、无强制门禁。
- 全部 Starter 内容变更按 BR-001 四步投影流程同步（commit canonical → --write → SOURCE.md 两行 → 提交）。

### 本期不做（Non-Goals，防止 AI/研发自行扩展）

- 不实现 RAG/向量检索、Memory OS、语义索引，不做本地检索基线与评测雏形（维持 v0.3 deferred；owner 裁决 OQ-1=A 后显式顺延）。
- 不接入任何真实任务调度器，不把 draft 任务自动升级 active。
- 不做内容自动发布、平台 API 集成与输出生产 SOP（owner 裁决顺延至后续版本）。
- 不做对外发布物料与公告动作（顺延候选；R-22 仅含一句聚合数字叙事）。
- 不做多宿主扩展（Windows/Linux、新宿主支持维持原 deferred 路线）。
- 不做旧库批量迁移/合并（adopt-existing 维持只读盘点边界；R-21 是"对照吸收指引"不是自动迁移）。
- 不做隐私自动分类与强制密级门禁（owner 裁决 OQ-4=轻量纳入）。
- 不吸收源头库的个人化配置（AI 虚拟团队角色卡、具体飞书/微信集成、真实项目内容）。

### 与其它模块/需求的关系

- `docs/TwinMind第二大脑初始化Skill技术方案.md` Deferred 列表：本轮维持检索基线 v0.3 原路线，无需改路线表述。
- `skills/bootstrap-second-brain/references/workflow-contract.md` 与 `schemas/`：预裁轻校验为独立只读脚本（零契约触碰）；若 planning 论证后改走既有 CLI 子命令扩展，属 contract-change，须列全 schema/workflow-contract 退出码/test_cli_contract/evals/package 四面联动后再动。
- `skills/bootstrap-second-brain/evals/`：R-23 承载的新 case 与 forward eval 约束。
- `skills/bootstrap-second-brain/tests/test_assets.py`：任务定义页 frontmatter/表格断言（scheduled/draft 计数、结构）需随 R-06/R-07 同步修订；轻校验脚本落地时新增零写入可自动化断言。
- AGENTS.md 构建命令与仓库指南：R-17 修正后需保持与代码一致，后续 AGENTS.md 改动需过同样的比对。

### 跨地区 / 市场 / tenant 边界

不涉及（本地单用户工具，无多地区/租户语义）。

## Acceptance Examples

```text
AE-01（对应 R-01、R-04）
Given 用户已完成 create 初始化并打开《AI协作协议》
When 查看"证据标注分级""冲突登记""覆盖决策登记"三节
Then 三节存在且各含可执行规则（分级取值、登记字段、禁止静默合并的显式禁令、
     覆盖决策登记模板字段），且协议其余三档权限内容未被改动

AE-02（对应 R-01，异常）
When 贡献者提交的 Starter 协议页删除了"冲突登记"节或破坏了 managed-block 标记对
Then 发布前评审清单（或模式启发脚本）能发现该页与规范章节清单不一致并留痕报错，
     不产生静默通过

AE-03（对应 R-02）
Given 用户复制知识页模板新建一页
When 检查该页 frontmatter
Then authority/review_at/evidence_note 三个治理字段存在且《字段与状态速查》
     对每个字段给出取值说明

AE-04（对应 R-03）
Given 库内存在至少一页 review_at 早于今天
When 用户按到期巡检流程执行（或运行只读校验形态）
Then 输出包含该页路径的到期清单；运行前后 Vault 目录树与文件哈希一致，
     不生成 plan/authorization/receipt 等任何持久化产物（零写入含 Vault 外）

AE-05（对应 R-06）
Given 用户按新规范登记一个定时任务
When 检查任务定义页
Then frontmatter 含 prompt 快照位置、prompt 摘要哈希、外部事实源声明三项审计字段

AE-06（对应 R-07，异常）
Given 任务契约某页被改为 active 且声称"已接入调度"或"已有 prompt 哈希故可视为启用"
When 对照任务注册表生命周期门禁
Then 该页缺少晋级证据的说明应被识别为违规示例；
     同时 Starter 默认产物中不存在任何 active 任务与真实调度器引用

AE-07（对应 R-05/R-09/R-10，每周复盘批次）
Given 用户完成一周使用且本周至少有一个重大任务
When 按周报模板流程操作
Then 产出周报页含固定小节（进展/偏差/下周重点/本周维护耗时与超预算收缩决定）
     且落盘位置与文档一致；
     该重大任务在《高价值知识学习与回放模板》补齐的 keep/revise/stop 字段下留有回放页（R-05）；
     任务双向核对步骤能对照用户提供的调度器侧清单逐条勾稽并登记快照时点（R-09）

AE-08（对应 R-11）
Given 用户按六段式写一条维护日志
When 检查该条目
Then 来源/变更/判断/验证/边界/关联六段齐备，且为追加写入（未改写历史条目）

AE-09（对应 R-17）
Given 贡献者阅读 AGENTS.md 与 sync 脚本
When 比对两者对 canonical/投影方向的描述
Then 两处表述一致（与 manifest direction 字段同向），且 Skill 分发层与 Starter 内容层
     两个 canonical 概念被区分使用，不再互相矛盾

AE-10（对应 R-18）
Given 用户要立项一个三个月跟踪目标
When 按跟踪型项目模板立项
Then 项目页含基线、游标、验收闸门三要素小节，且模板示例全部为虚构内容

AE-11（对应 R-20，异常）
Given 一次内容变更把源头库真实案例（含人名/公司/业务数据）带入 Starter 示例或本仓库文档
When 执行脱敏检查（评审清单形态=评审记录留痕并要求替换；脚本形态=非零退出码）
Then 该变更在合并前被拦下并要求替换为虚构示例；
     且检查规则本身不含任何真实实体清单

AE-12（对应 R-19）
Given 用户按轻量隐私规范给一页标注 confidentiality: private
When 执行每周体检清单
Then 高密级页面清点项仅汇总用户显式标注的页面路径，
     不输出任何未标注页面的密级推断或建议，且不做任何自动改级或外发

AE-13（对应 R-12）
Given 用户库内存在到期页与失效链接各一处
When 按每周知识体检清单逐项执行
Then 清单能引导用户发现这两类异常，且每项异常有对应处置指引；
     体检报告含扫描范围与排除项声明；全程对 Vault 零写入（含 Vault 外持久化产物）

AE-14（对应 R-08）
Given 用户按映射示例文档在 WorkBuddy 侧创建一个定时任务
When 对照库内任务登记页并查找映射文档入口
Then 登记页含外部事实源声明与审计副本说明；
     映射文档可从 60_任务系统 README 与完整工具清单的引用发现；
     且示例文档未要求 Starter 产物默认引用任何调度器、未授权 AI 连接外部系统

AE-15（对应 R-22）
Given 一个新库按本轮内容完成初始化
When 从 README 能力清单、demo 根 README 运行入口、知识库索引、60_任务系统 README
     任一入口出发查找 FS-A/B/C/F/G 各产物与 R-03 新命令入口
Then 每个产物至少能从一个入口被发现；README 含 WorkBuddy 定位与获取链接、
     反馈引导、一句聚合数字方法论来源叙事；加载清单含新增常读项与预算提示

AE-16（对应 R-21）
Given 一个用 v0.1 初始化的旧库
When 用户按 README"已初始化库如何对照吸收新版 Starter"章节操作
Then 章节能明确区分可安全覆盖文件与用户内容不可动文件，
     并说明与 verify/adopt-existing 的衔接；全程无自动迁移行为

AE-17（对应 R-23）
Given 本轮新增的三类 eval case（任务门禁绕过/巡检只读/密级不改变数据域）已按 R-23 定义编写
When case 合入并运行 `run_evals.py --suite all`
Then 全绿且新 case 被执行；
     发布记录注明"全绿仅证明静态合同，行为级证明待 forward eval"且新 case 已排入 forward 运行

AE-18（对应 R-24）
Given 用户归档一份外部导出的会议材料压缩包
When 按来源登记与完整性规范操作
Then 来源页含 checksum/完整性字段；来源包按规范结构落盘（只为实际存在对象建目录）；
     压缩包逐文件核对通过；同一内容未重复存储；
     AI 生成的转写/纪要在页面中被按 unverified 对待且注明以人工整理为准

AE-19（对应 R-25）
Given 用户收到一批新资料但只有十分钟
When 按轻摄取档操作
Then 产物为来源登记+一处知识页更新+回链+日志四件套；
     流程文档写明决策级摄取的触发条件与"一次一来源、优先更新已有页"纪律
```

## Goals / Success Metrics

| 目标类型 | 目标描述 | 衡量口径 | 数据来源 |
| --- | --- | --- | --- |
| 采纳目标（维护者演练代理） | 新库第一周能跑通"登记任务 → 回放 → 周报"最小闭环 | 闭环三产物（任务登记页、回放页、周报页）在 7 天内出现的示例演练可在纯新库上照文档完成（如实标注：当前为维护者干净目录自测代理，非真实用户行为度量） | 发布前用干净目录按 README 实测演练（可观察信号，不预置数值） |
| 产品目标 | Starter 从"结构骨架"升级为"运转系统"，任务/周报复盘/摄取登记三档从"雏形"升为"已覆盖" | 发布后独立的能力面盘点对照（不引用本文档自证） | 下一轮盘点 |
| 传播目标 | 支撑"方法论来自真实生产库"的社区叙事且零隐私泄露 | 开源仓库内检索不到源头库真实实体（R-20 检查项）；README 含一句聚合数字叙事（R-22） | 仓库内容审查（AE-11）；发布后 GitHub issue/讨论区反馈（R-22 反馈引导落地后可用） |
| 工程目标 | 内容扩张不破坏既有契约 | `sync_starter_assets.py --check`、unittest 全套、`run_evals.py --suite all`、`package_skill.py --check` 全绿；限定：run_evals 全绿仅证明静态用例合同有效，行为级安全证明以 forward eval 为准（R-23） | 仓库既有命令（confirmed-source） |

## Change Topology

Primary topology: extend（Starter 能力面扩展 + 文档对齐），次级候选：workflow-change（任务生命周期与巡检流程）、contract-change（仅当轻校验落地为 CLI 子命令扩展时触发；预裁为独立只读脚本以规避）。

Why this topology matters: extend 必须显式声明"哪些既有默认不变"（draft 默认、不接调度器、声明天花板、隐私门禁），否则容易被"增强"掩盖为边界变化；contract-change 候选决定了测试/eval/打包面的联动范围，预裁独立脚本将联动面收敛为零。

## Negative Acceptance

```text
NA-01
Given Starter 任意内容变更
When 投影同步执行
Then 不得绕过 canonical → assets 单向投影直接改 assets 产物（BR-001）

NA-02
Given 本轮全部新增内容（含本 PRD 及其它 spec 文档）
When 对源头库真实信息做全文核对
Then 仓库中不出现真实人名、公司、客户数据、私有仓路径或可识别个人处境的案例细节（R-20/AE-11）

NA-03
Given 7 个默认任务契约
When 初始化完成
Then 默认产物中不存在 active 任务、真实调度器引用或自动执行入口（BR-003）

NA-04
Given 新增能力落地
When 校验声明天花板
Then 不得出现"文档写入即宣称 activated"或自动抬升声明档位的行为（BR-004）

NA-05
Given 既有五旅程 CLI 与授权/恢复契约
When 本轮变更合入
Then 既有子命令行为、退出码与授权语义保持不变（Change Delta keep 行）

NA-06
Given 轻校验的任何实现形态
When 用户或 AI 运行巡检/体检
Then 不产生对 Vault 或 Vault 外的任何持久化写入，不触发外部系统连接授权（R-03/R-12/R-08/R-09）
```

## Evidence And Assumptions

| 主张 | 类型 | 证据来源 / 为何是假设 | 确认路径 |
| --- | --- | --- | --- |
| TwinMind v0.1 能力面与 deferred 路线（见 Current System Snapshot） | confirmed-source | README.md、CHANGELOG.md、SKILL.md、docs/技术方案 直接读取（含多专家代理独立复核） | 已确认，无需再查 |
| 源头库近三月进化主题（协议 v2.3、到期巡检、任务审计、检索评测、跟踪立项、发布闭环、来源包规范、摄取两档） | confirmed-source（库外） | 对源头知识库文件的直接只读读取（库外私有仓，路径见下方证据索引）；仅吸收方法论，不引入内容 | 已确认；开源侧只需 R-20 纪律 |
| 社区新用户同样需要"运转层"方法论 | assumption | 源头库是重度个人化实践，社区用户需求强度未经第二库验证（源头库自己的通用框架自述也处于 pilot 状态） | 发布后以 issue/讨论区反馈与演练完成率观察 |
| Starter 现状细节（既有生命周期门禁、无独立决策回放模板、README 无升级章节、manifest 刷新机制） | confirmed-source | 四专家代理对仓库源文件的直接比对（各自独立） | 已确认 |
| AGENTS.md 投影方向表述为笔误（代码方向为准） | confirmed-source | sync 脚本 docstring、manifest `direction: canonical-to-assets-only`、`--check` 实测一致指向"根目录 canonical"；工程与方法论席位三源复核 | R-17 修正即可，无需 owner 裁决 |
| 本期范围四项裁决 | user-stated（owner-answered） | owner 2026-09-04 会话回复「继续完成」（响应含四项推荐默认值的提问总结），按推荐项采纳，见 Owner Decision Trace | 已裁决（BR-005 锚定） |
| 多专家协同评审授权 | user-stated（owner-answered） | owner 2026-09-04 消息「你作为项目总负责人，协调多种agent专家协同完成」 | 已裁决（见 Owner Decision Trace 第 5 行） |

权限/数据敏感性标注：本需求触及"个人信息不外泄"红线（R-20/AE-11/NA-02，且约束文档自身）；不触及资金交易。源头库隐私边界调查确认其"全量入库 + 私有仓"姿态与本仓库开源方向相反，因此 BR-002/R-20 是本迭代的硬约束而非可选项。

支撑证据索引：

| ref_id | source_type | authority | freshness | consumed_by | notes |
| --- | --- | --- | --- | --- | --- |
| REF-01 | source-code | 高（本仓库） | 2026-09-04 读取（含 4 专家代理复核） | Current System Snapshot 全表 | README.md / CHANGELOG.md / AGENTS.md / skills/bootstrap-second-brain/** |
| REF-02 | prior-artifact | 高（本仓库） | 2026-09-04 读取 | deferred 路线、检索 Non-Goal | docs/TwinMind第二大脑初始化Skill技术方案.md |
| REF-03 | prior-artifact | 高（内容事实）/ 库外私有 | 2026-09-04 读取（含方法论席位逐项核对） | R-01~R-12、R-18/R-19/R-24/R-25 的方法论来源 | 源头知识库：AI协作协议.md（v2.3）、知识库索引.md、维护日志.md、60_tasks/README、tools/check.sh、通用知识库建设框架.md、20_原始资料/README 来源包规范（库外路径，不入库） |
| REF-04 | external-research | 中 | 2026-09-04 | Problem Frame 提交量叙事 | 源头库 git log（2026-07-26 起 627 提交，聚合数字） |
| REF-05 | owner-answer | 高 | 2026-09-04「继续完成」+「协调多agent专家」 | OQ-1~OQ-4 裁决、BR-005、多专家授权 | Owner Decision Trace 五行逐条绑定 |
| REF-06 | fresh-source-eval | 高（本仓库+库外只读） | 2026-09-04 四席位并行 | v2 修订的全部输入 | 四专家评审报告（对话内交付，未落盘为独立工件；发现已按写入目标合入本文） |

Coverage Pack（P0 必需项）：

| coverage_item | status | source_tag | evidence_ref | deferred_owner | deferred_unblock_condition |
| --- | --- | --- | --- | --- | --- |
| source_authority | filled | mixed | 本表 + Frontmatter source_authority | — | — |
| current_state | filled | confirmed-source | Current System Snapshot（4 席位复核） | — | — |
| change_delta | filled | mixed | Change Delta 表 | — | — |
| requirements_acceptance | filled | mixed | Requirements/Acceptance Examples/追溯矩阵 | — | — |
| owner_oq_trace | filled | owner-answer | Outstanding Questions + Owner Decision Trace 五行 | — | — |
| evidence_refs | filled | mixed | 支撑证据索引 | — | — |

## 需求追溯矩阵

| 需求编号 | 关联业务规则 | 验收编号 | 约束 / 风险 | 证据 / 规则依据 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| R-01 | BR-002 | AE-01/AE-02 | 不得改变既有三档权限；managed-block diff 留痕 | REF-03 | P0 |
| R-02 | BR-001 | AE-03 | 字段名与 injectable/lens 取舍规划期定稿 | REF-03 | P0 |
| R-03 | BR-001 | AE-04 | 只读零写入（含 Vault 外） | REF-03 + OQ-2 裁决 | P1 |
| R-04 | BR-002 | AE-01 | — | REF-03 | P1 |
| R-05 | BR-004 | AE-07 | 引用既有模板不新建 | REF-01/REF-03 | P1 |
| R-06 | BR-003 | AE-05 | — | REF-03 | P0 |
| R-07 | BR-003 | AE-06 | 默认 draft 不变；扩展既有门禁 | REF-01/REF-03 | P0 |
| R-08 | BR-003 | AE-14 | 无外部系统授权 | REF-05 | P1 |
| R-09 | BR-003 | AE-07 | 双向核对、用户手动供数 | REF-03 | P1 |
| R-10 | BR-001 | AE-07 | 维护耗时小节 | REF-03 | P1 |
| R-11 | BR-001 | AE-08 | append-only | REF-03 | P1 |
| R-12 | BR-001 | AE-13 | 报告自证纪律 | REF-03 | P1 |
| R-17 | BR-001 | AE-09 | 区分两层 canonical | REF-01 | P0 |
| R-18 | BR-002 | AE-10 | — | REF-03 | P0 |
| R-19 | BR-001 | AE-12 | 无自动分类；与数据域关系说明（OQ-4 裁决） | REF-03/REF-01/REF-05 | P1 |
| R-20 | BR-002 | AE-11/NA-02 | 红线不可降级；约束文档自身；检查规则无实体清单 | REF-01/REF-03 | P0 |
| R-21 | BR-004 | AE-16 | 无自动迁移 | REF-01 | P1 |
| R-22 | BR-006 | AE-15 | 全入口登记 | REF-01/REF-05 | P0 |
| R-23 | BR-006 | AE-17 | forward eval 限定说明 | REF-01 | P0 |
| R-24 | BR-002 | AE-18 | — | REF-03 | P1 |
| R-25 | BR-002 | AE-19 | 轻摄取为默认档 | REF-03 | P1 |

## Feature Slices

```text
feature_id: FS-A
title: 治理协议固化与摄取规范
summary: 证据分级、冲突登记、覆盖决策登记、治理字段、到期巡检、决策回放绑定、来源登记完整性、摄取两档（R-01~R-05、R-24、R-25）
requirement_refs: R-01, R-02, R-03, R-04, R-05, R-24, R-25
acceptance_refs: AE-01, AE-02, AE-03, AE-04, AE-18, AE-19
source_excerpt_or_claim: 源头库协议 v2.3 + review-due + 冲突/覆盖登记 + 决策回放 + 来源包规范 + 摄取两档实践
evidence: REF-03
candidate_modules_or_source_refs: skills/bootstrap-second-brain/assets/starter-kit 控制层、30_知识主题、20_原始资料、90_模板、99_维护记录
risk_signals: 内容面大；字段命名需规划期定稿；协议页 managed-block 变更需 diff 留痕；常驻加载负载上涨需预算提示

feature_id: FS-B
title: 任务系统登记审计化
summary: 审计字段、每档生命周期门禁、WorkBuddy 映射、双向核对（R-06~R-09）
requirement_refs: R-06, R-07, R-08, R-09
acceptance_refs: AE-05, AE-06, AE-14
source_excerpt_or_claim: 源头库 60_tasks prompt_sha256 + 事实源声明 + 双向核对实践
evidence: REF-03
candidate_modules_or_source_refs: assets/starter-kit/60_任务系统
risk_signals: 不得触碰"不接调度器"边界；evals scheduled-task-boundary 与 tests/test_assets.py 断言需同步加固

feature_id: FS-C
title: 周报复盘流水线
summary: 周报模板（含维护耗时）、维护日志六段式、每周知识体检（R-10~R-12）
requirement_refs: R-10, R-11, R-12
acceptance_refs: AE-07, AE-08, AE-13
source_excerpt_or_claim: 源头库周报复盘与 check.sh 五步主闸的文档化抽象
evidence: REF-03
candidate_modules_or_source_refs: 90_模板、99_维护记录、每周知识蒸馏任务
risk_signals: 与 FS-A 到期巡检有共用素材，规划时合并排布；周常堆叠需预算护栏（已并入 R-10/R-12）

feature_id: FS-F
title: 横切修复、安全加固与红线
summary: AGENTS.md 对齐（R-17）、跟踪型项目模板（R-18）、隐私轻量字段（R-19）、脱敏纪律（R-20）、eval 安全加固（R-23）
requirement_refs: R-17, R-18, R-19, R-20, R-23
acceptance_refs: AE-09, AE-10, AE-11, AE-12, AE-17
source_excerpt_or_claim: 文档-代码比对 + 源头库跟踪立项与密级实践 + evals 现状缺口
evidence: REF-01, REF-03
candidate_modules_or_source_refs: AGENTS.md、assets/starter-kit/10_当前工作台、90_模板、skills/bootstrap-second-brain/evals
risk_signals: R-20 检查形态（清单+可选脚本）在发布前必须落地；R-23 forward eval 需排期

feature_id: FS-G
title: 用户入口与升级通道
summary: README 能力清单/入口登记/WorkBuddy 定位/反馈引导/来源叙事（R-22）、老用户升级指南（R-21）
requirement_refs: R-21, R-22
acceptance_refs: AE-15, AE-16
source_excerpt_or_claim: 多专家评审：交付物可发现性与老用户可达性缺口
evidence: REF-01, REF-06
candidate_modules_or_source_refs: README.md、我的第二大脑/README.md、知识库索引.md、加载清单.md、60_任务系统 README
risk_signals: 入口登记遗漏任一位即形成孤儿文档；升级指南必须区分可覆盖与不可动文件
```

（原条件切片 FS-D 检索与评测雏形、FS-E 输出与发布 SOP 经 owner 裁决 OQ-1=A 顺延至后续版本，已移出本期切片清单。）

## Outstanding Questions

| id | question | PRD write target | owner_status | blocks_planning | closure_disposition | planning_would_invent_what | closure_state | recommended_default/deferred_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OQ-1 | 本期主打哪条主线：A 运行系统轮；B 检索记忆轮；C 输出变现轮；D 三线并进 | Requirements 优先级列、Scope Boundaries、Feature Slices 激活 | answered | 否 | owner-answered | 无 | closed | 已裁决：A 运行系统轮；B/C 顺延 |
| OQ-2 | 落地形态：纯文档/模板；文档+轻校验；CLI 能力为主 | Acceptance Examples 形态、R-03/R-12 命令形态、contract-change 是否触发 | answered | 否 | owner-answered | 无 | closed | 已裁决：文档+轻校验 |
| OQ-3 | WorkBuddy 角色：深度绑定；推荐+映射；淡化中立 | R-08 存废、README 表述、BR-003 措辞 | answered | 否 | owner-answered | 无 | closed | 已裁决：推荐+映射 |
| OQ-4 | 内容级隐私分级：轻量纳入；本期不做；完整做 | R-19 存废与深度、Data / Compliance Boundaries 深度 | answered | 否 | owner-answered | 无 | closed | 已裁决：轻量纳入 |

## Owner Decision Trace

| question | owner_answer/source | chosen_answer | PRD write target | consequence | closure_state |
| --- | --- | --- | --- | --- | --- |
| OQ-1：本期主打哪条主线（A 运行系统轮 / B 检索记忆轮 / C 输出变现轮 / D 三线并进） | owner 2026-09-04 会话回复「继续完成」，系对含四项推荐默认值提问总结的响应，按推荐项采纳 | A 运行系统轮 | Requirements 优先级、Scope Boundaries、Feature Slices | FS-D/FS-E 与原检索/输出条件需求顺延，移出本期 | closed |
| OQ-2：落地形态（纯文档 / 文档+轻校验 / CLI 为主） | 同上（同一次「继续完成」回复，按推荐项采纳） | 文档+轻校验 | R-03/R-12 验收形态、contract-change 触发条件 | R-03/R-12 附只读校验路径；具体命令形态 planning 定 | closed |
| OQ-3：WorkBuddy 角色（深度绑定 / 推荐+映射 / 淡化中立） | 同上（同一次「继续完成」回复，按推荐项采纳） | 推荐+映射 | R-08、README 表述 | R-08 映射示例文档保留，无代码级硬依赖 | closed |
| OQ-4：内容级隐私分级深度（轻量纳入 / 本期不做 / 完整做） | 同上（同一次「继续完成」回复，按推荐项采纳） | 轻量纳入 | R-19、Data / Compliance Boundaries | R-19 保留为字段规范+巡检提示，无自动分类 | closed |
| 多专家协同评审授权：是否由总负责人调度多 agent 专家完成本轮需求迭代 | owner 2026-09-04 消息「你作为项目总负责人，协调多种agent专家协同完成」 | 授权四席位并行评审 + 总负责人裁决修订 | 全文 v2 修订（Decision Notes 裁决摘要） | 38 条发现全部处置（3 阻断全修、18 应修全合入、16 建议合入、1 收缩为顺延候选）；本文升版为 amendment | closed |

## Decision Notes

- 2026-09-04 owner 以「继续完成」响应四项范围提问，采纳全部推荐默认值（OQ-1=A / OQ-2=文档+轻校验 / OQ-3=推荐+映射 / OQ-4=轻量纳入），由 BR-005 锚定为本期范围基线。
- 2026-09-04 owner 授权多 agent 专家协同。worker_dispatch 记录：authorization=owner 本轮消息原文；capability=Agent 工具 4 个只读并行子代理；context_isolation=各自自包含提示词、无共享会话；model_override=继承未覆盖；bounded_parallelism=4；outcome=completed（4/4 返回结构化发现，共 38 条：产品采纳 8、安全隐私 10、工程契约 8、方法论忠实度 12）。
- 裁决摘要：3 条阻断（老用户通道证据失实 C-01；本文自身违反脱敏红线 S-01；决策回放模板指称错误 F-01）全部修复；18 条应修全部按写入目标合入（含 Snapshot 两处事实修正 F-02、manifest 刷新口径修正 F1、零写入可观测判据 S-06、密级术语冲突 S-03 等）；17 条建议中 16 条合入（含双向核对 F-09、加载预算提示 F-07、术语对照 F-11 等），1 条收缩（C-08 对外发布物料动作转为顺延候选，仅保留 R-22 一句聚合数字叙事）；无整体拒绝项。
- 总负责人预裁（OQ-2 框架内，不重开 OQ）：轻校验默认走"独立只读脚本"路径（零契约触碰）；若 planning 论证后改走 CLI 子命令扩展，必须先列全 schema/workflow-contract 退出码/test_cli_contract/evals/package 四面联动清单。
- 检索与评测雏形（原检索轮两条候选需求、FS-D）与输出发布 SOP（原输出轮两条候选需求、FS-E）显式顺延：前者维持技术方案 v0.3 deferred 原路线，后者待运行系统轮落地后按社区反馈再评估；两者重新纳入须走 BR-005 的范围变更流程。
- 范围裁决解释口径：owner 回复针对的是"四问 + 推荐项"的总结消息，本稿按"采纳推荐默认值"记录；若 owner 本意不同，任一 OQ 可重开（见文档头部状态说明）。
- v2 修订的 receipt 处理：v1 receipt 因内容修订失效，按 producer 纪律重开为 `status: draft` 并移除失效 receipt 字段，由 `finalize-prd-artifact.js` 重新签发；receipt 内容始终由脚本独占写入。

## Data / Compliance Boundaries

| 数据/记录 | 类型 | 展示规则 | 操作规则 | 留痕/保存口径 | 待确认项 |
| --- | --- | --- | --- | --- | --- |
| 源头库真实内容（案例、人名、组织、业务数据） | 高敏个人信息/业务机密（库外） | 不得进入本仓库任何文件（含测试夹具、示例、commit message、spec/需求文档） | 仅允许"方法论级"抽象后入库；脱敏检查规则自身不得内嵌真实实体清单 | 无 | 无（红线由 R-20/NA-02 承载） |
| Starter 用户库内容 | 用户本地数据 | 不出本机；confidential 数据域默认 session_only（现状不变）；内容级密级为可选标注且与数据域语义分列文档化（OQ-4 裁决） | 用户自主标注，系统不自动分类、不强制；密级标注不改变数据域处理（R-23 case 锚定） | 用户自主 | 无 |

## Planning Recheck

| item | why recheck | required before | blocks planning? |
| --- | --- | --- | --- |
| canonical/投影方向以代码为准的最终确认 | AGENTS.md 表述与代码矛盾（R-17 修正对象）；规划改动 Starter 前必须锁定真实方向 | 任何 FS 规划动工前重跑 `sync_starter_assets.py --check` 并读 sync 脚本头部 | 否（HOW/事实源核对，不改变本稿 WHAT） |
| 治理字段与密级字段命名定稿 | R-02 只定语义三字段（五字段中 injectable/lens 取舍未记录）；R-19 密级字段与初始化数据域同名异义，需文档化关系并定最终名（含是否改名 sensitivity） | FS-A 规划期，与 90_模板/字段与状态速查对齐 | 否（命名属契约细节，WHAT 已闭合为语义字段） |
| 轻校验形态联动清单 | 预裁独立只读脚本（零契约触碰）；若改 CLI 扩展须列全 schema/workflow-contract 退出码/test_cli_contract/evals/package 四面 | FS-A/FS-C 规划期 | 否（HOW 归属，不改变"只读零写入"的 WHAT 边界） |
| 脱敏检查形态细化 | 评审清单（必需）+ 可选模式启发脚本的分工、规则约束（无真实实体清单）、与 Release 验证命令的挂接方式 | FS-F 规划期、发布前 | 否（形态选择，红线 WHAT 已定） |
| 版本联动 | starter_version（sync 脚本硬编码）/BUNDLE_NAME（package）/CHANGELOG 三处是否 bump 0.2.0 | 发布前（BR-006） | 否（发布协调项） |
| 字段与术语对照表 | PRD"治理字段/审计字段"与 Starter 既有 scheduler_owner、字段速查词汇、两库任务状态枚举需一张对照表防双命名并存 | FS-A/FS-B 规划期产出 | 否（HOW 文档，语义已定） |

## Readiness Self-Check

write_mode: final-prd
clarification_evidence: asked-owner
preflight_sweep_closure: closed
decision_card_highest_risk_gap: 已闭合——四项范围决策 owner 裁决 + 多专家评审 3 条阻断（老用户通道/脱敏红线自伤/模板指称）全部修复；剩余最高风险为 R-20 脱敏检查形态的发布前落地（已入 Planning Recheck 与 Release 验证命令）
decision_card_next_action: final-prd
decision_card_why_no_invention: 所有 load-bearing 分支均已到达合法停止点（OQ-1~OQ-4 owner-answered 且逐条绑定 Trace；四席位 38 条发现全部裁决处置；现状 Snapshot 经多源复核修正；顺延项显式记录）；plan 只需在已定边界内选择实现方式，无需发明产品行为
design_source_coverage: not-applicable
readiness_verified_by:
readiness_checker_schema:
readiness_prd_hash:
readiness_inputs_hash:
first_unclosed_owner_question: none
recommended default: 无（四项均已裁决；多专家授权已执行）
can_enter_spec_plan: yes
why_not: —

handoff_context_slice:

- confirmed WHAT: owner 裁决后的运行系统轮全量（FS-A/B/C/F/G）；九区骨架与安全契约保持不变（keep）；现状 Snapshot 经四席位独立复核
- top requirement / acceptance refs: R-22（AE-15 入口可发现性）、R-20（AE-11 脱敏红线）、R-07（AE-06 任务门禁）、R-23（AE-17 eval 加固）
- must-preserve behaviors: BR-003 默认 draft 不接调度器；BR-004 声明天花板；BR-001 四步投影流程；NA-06 轻校验零写入含 Vault 外
- owner decisions: OQ-1=A 运行系统轮；OQ-2=文档+轻校验；OQ-3=推荐+映射；OQ-4=轻量纳入；多专家协同授权（均 2026-09-04，见 Owner Decision Trace）
- accepted assumptions: "社区用户需要运转层方法论"为 assumption，发布后验证
- source refs to re-read: Planning Recheck 六项
- unresolved WHAT blockers: 无
- planning recheck items: 6（见 Planning Recheck）
- degraded facts: 源头库证据均为库外私有仓读取，本仓库内不可复核原文，只能复核抽象产物；四专家报告为对话内交付未落盘（发现已全部合入本文，REF-06）

## Release / Operation Readiness

| 项 | 结论 | 证据 / 决定路径 | 是否阻塞发布 |
| --- | --- | --- | --- |
| 必要专业审阅 | 不涉及（无合规/法务/资金面） | — | 否 |
| 老用户兼容 | R-21 README 升级章节承载（当前不存在，新增后老用户可对照吸收；无自动迁移） | README 现状核对（confirmed-source） | 是（R-21 合入前不得发布） |
| 存量数据处理 | 不触碰已初始化产物；任何 Starter 内容变更走 BR-001 四步：commit canonical → `--write` → SOURCE.md commit/digest 两行 → 提交投影+manifest | BR-001 + sync/package 校验逻辑（confirmed-source） | 是（双 check 绿） |
| 验证命令 | `sync_starter_assets.py --check`、unittest 全套、`run_evals.py --suite all`、`package_skill.py --check` 全绿 + 脱敏检查（R-20 形态）通过；限定：run_evals 全绿仅证明静态合同，行为级以 forward eval 为准（R-23） | AGENTS.md 构建命令 + R-20/R-23 | 是 |
| 发布记录 | CHANGELOG 按既有 (user-visible) 格式记录全部内容变更（BR-006）；版本联动核对 | CHANGELOG 格式（confirmed-source） | 是 |
| 回滚 | 内容回退走 Git revert；无运行时状态 | 仓库机制 | 否 |

requirements_lifecycle: amendment
supersedes: 无（原地修订 v1）
reopened_reason: owner 授权多专家协同评审，评审发现 3 项阻断级问题（见 Decision Notes）
last_validated: 2026-09-04（v1 finalize receipt）
downstream_sync_impact: downstream_sync_unknown（尚无 plan/task 工件消费本文）

## 变更记录

| 日期 | 修改人 | 变更内容 |
| --- | --- | --- |
| 2026-09-04 | spec-prd（agent） | 基于源头知识库进化调查与本仓库现状盘点建立 checkpoint 初稿；四个 owner 决策未应答，保留为阻塞 OQ |
| 2026-09-04 | spec-prd（agent） | owner 回复「继续完成」→ 采纳四项推荐裁决；闭合全部 OQ；升级为最终需求文档 v1（finalize receipt 签发） |
| 2026-09-04 | spec-prd（agent，总负责人） | owner 授权多专家协同：四席位（产品采纳/安全隐私/工程契约/方法论忠实度）并行评审 38 条发现，全部裁决处置；新增 R-21~R-25 与 AE-15~AE-19；修正 Snapshot 两处事实、manifest 刷新口径、老用户兼容证据、脱敏红线自伤；升版 amendment v2 并重开 draft 待 finalize 重签 receipt |

## Handoff

- 本文档 v2（amendment）已完成多专家评审闭环，待 finalize 重签 receipt 后即可进入 `spec-plan` 做实现规划。
- 需要审查完整性/一致性 → `spec-doc-review`。
- 若 owner 对四项裁决或多专家处置有异议 → 重开对应 OQ / Decision Note 并回到 refine。
- 不要跳过规划直接进入 `spec-work`。
