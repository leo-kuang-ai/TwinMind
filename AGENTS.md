<!-- spec-first:lang:start -->
## 语言与治理策略
**语言设置：** `Chinese / 中文`
语言规则为绝对硬执行要求：除非用户在当前请求中明确要求其他语言、翻译、双语输出或保留原文，所有面向用户的新生成自然语言内容必须使用简体中文。
适用范围覆盖回答、状态更新、澄清问题、总结、评审、生成文档、需求、计划、任务、变更说明、commit message 和 PR 文案。
代码标识符、命令、路径、配置键、环境变量、API 名称、协议名、日志、工具输出和引用材料可以保留原文；围绕它们新增的解释、结论和说明仍按本语言设置输出。
skill、agent、模板、历史上下文或示例文本的原文语言不得覆盖本设置；新增代码注释也按本设置，只说明非显然意图。
### Workflow 入口治理
<!-- spec-first:workflow-entry:using-spec-first -->
- 在执行实质性工作前，加载当前宿主已安装的 `using-spec-first` skill；完整入口路由与边界由该 skill 提供。
<!-- spec-first:lang:end -->

# Repository Guidelines

## 项目结构与模块组织

核心 Skill 位于 `skills/bootstrap-second-brain/`：`scripts/` 存放 Python CLI 与校验工具，`tests/` 存放单元和端到端测试，`evals/` 存放行为评测，`schemas/` 与 `manifests/` 定义数据契约。Starter 内容的 canonical 来源是根目录 `我的第二大脑/`，`skills/bootstrap-second-brain/assets/starter-kit/` 是由同步脚本生成的单向投影（方向与 `manifests/starter-v1.json` 的 `direction: canonical-to-assets-only` 一致）；修改 Starter 后应通过同步脚本刷新投影，不得直接改投影。注意区分两层 canonical：Starter 内容层的事实源是根目录 `我的第二大脑/`，Skill 分发层的事实源是 `skills/bootstrap-second-brain/SOURCE.md`，两者不是同一概念。设计说明位于 `docs/`，用户入口见 `README.md`。

## 构建、测试与开发命令

- `python3 -I -S -E skills/bootstrap-second-brain/scripts/sync_starter_assets.py --check`：检查 canonical Starter 与投影是否一致。
- `python3 -m unittest discover -s skills/bootstrap-second-brain/tests -p 'test_*.py'`：运行完整测试套件。
- `python3 skills/bootstrap-second-brain/evals/run_evals.py --suite all`：静态校验 eval 用例合同（结构完整性、SKILL.md 安全锚点核对、eval.yaml 注册有效性）；模型行为由 skill-up forward eval 执行并另行排期。
- `python3 skills/bootstrap-second-brain/scripts/package_skill.py --check`：校验打包契约；仅在需要生成本地构建物时使用 `--write`。

项目要求 Python 3.11+。提交前至少运行与改动相关的测试；修改 Starter、schema 或发布逻辑时运行以上全部检查。

## 编码风格与命名约定

Python 使用 4 空格缩进、UTF-8、类型注解和标准库优先原则。函数、变量及文件采用 `snake_case`，类采用 `PascalCase`，常量采用 `UPPER_SNAKE_CASE`。保持 CLI 输出和异常信息明确；新增中文注释只解释非显然意图。JSON/YAML 字段延续既有 `snake_case`，不要无依据改变 schema。

## 测试指南

测试框架为 `unittest`，文件命名为 `test_*.py`，测试方法命名为 `test_<行为>`。优先覆盖正常路径、安全边界、失败恢复和 CLI 契约。仓库未设固定覆盖率阈值，但修复缺陷时应添加可复现该问题的回归测试。

## Commit 与 Pull Request

历史提交遵循 Conventional Commits 风格，如 `feat: 新增…`、`fix: 修复…`、`docs: 更新…`、`chore: 刷新…`。每个提交聚焦一个可审查变更。PR 应说明目的、影响路径和验证命令，关联相关 issue；涉及可见文档或 Vault 结构变化时附前后对比或截图，并注明兼容性、迁移及恢复影响。

## 安全与配置

不得提交个人 Vault 内容、凭据、私钥或本地绝对路径。高风险写入必须保持显式授权、可审查计划与可恢复边界；不要通过测试夹具弱化这些门禁。

### 发布前脱敏检查清单（必执行）

本清单适用于本仓库的**全部待发布变更文件**——包括 Starter 内容、`docs/`（需求/计划/方案文档）、eval case、测试夹具、README、commit message 与 PR 描述。逐项检查，零命中方可发布；检查规则本身不得内嵌任何真实实体清单（避免检查工具自身泄密）。留痕要求：在维护日志或 PR 描述中登记实际扫描的文件集与逐项结果，"登记了去向"不等于逐字复核过内容，抽样检查须声明抽样范围。

- 真实人名（含拼音、昵称、家庭关系称谓）
- 真实公司、客户、团队、项目代号
- 真实业务数据（绩效、薪酬、组织、客户往来）
- 私有仓路径或远程地址
- 可识别个人处境的案例细节（健康、家庭、在职状态等）
