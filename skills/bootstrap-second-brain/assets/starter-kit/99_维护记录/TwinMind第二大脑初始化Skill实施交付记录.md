# TwinMind 第二大脑初始化 Skill 实施交付记录

## 交付范围

- 日期：2026-08-07
- 执行权威：`docs/TwinMind第二大脑初始化Skill技术方案.md`
- Canonical Demo：`我的第二大脑/`
- Canonical Skill：`skills/bootstrap-second-brain/`
- 正式支持边界：Codex、macOS、Python 3.11+
- 分发边界：Owner 私有 pilot；许可证与正式信任材料仍待 Owner 裁决

## 已实现

1. tool-prepare 作为 create 第一业务阶段：Python runtime-required、Git product-required、WorkBuddy/Obsidian recommended、社区插件 optional 且默认不安装。
2. 完整 CLI 入口：tool probe/plan/choice/action/evidence/verify、Vault probe/plan/interview/authorize/apply/verify、resume/recover/cleanup。
3. scaffold、personalize、environment、inventory、recovery 与 cleanup 使用 canonical plan digest；authorize/apply 复核 plan、subject、operation 和 authorization 绑定。
4. Starter 复制在目标写入前完成安全源快照与 SHA-256 复核；目标 identity、snapshot、大小写冲突、symlink 和 no-follow 写入失败关闭。
5. Git baseline 绑定 Vault 快照、仓库边界、批准路径和预期 staged set；阻断父仓库未确认、既有 staged changes、嵌套 Git、hooks、filters、attributes、signing、fsmonitor 与高风险配置；提交后复核 commit 路径、blob、OID 和边界。
6. 外部私有状态支持默认平台路径和 `--state-dir`；文件为 0600、目录为 0700，拒绝 symlink、非预期 hardlink、owner/mode 漂移和无界 JSON。
7. tool choice/evidence 跨调用幂等持久化；resume 可恢复 tool-prepare、scaffold 与 interview 公共状态，且不输出访谈答案值。
8. confidential `runtime_state` 在 storage domain 缺少可验证证据时保持 `unknown` 并返回 `action_required`；不把 POSIX 私有权限误当作 local-fixed 或加密证明。
9. inventory 使用八项 canonical 预算、单调时钟、实际读取字节、no-follow 普通文件读取和有界报告；符号链接只输出类型与摘要，不泄漏原始绝对 link text。
10. pre-baseline recover 只删除本 run 创建、路径安全、内容未变化且非 append-only 的文件；missing-target partial staging 可删除空 staging root；baseline 后不改写历史。
11. package 由单次安全 source snapshot 构建；两次独立快照必须产生相同 zip 字节。release verification 安全读取并固定 bundle、attestation、公钥、allowed signers 与签名字节，复核可信 OpenSSH verifier 摘要并验证两个 namespace。

## 验证合同

```text
python3 --version
python3 -I -S -E skills/bootstrap-second-brain/scripts/sync_starter_assets.py --check
python3 -m unittest discover -s skills/bootstrap-second-brain/tests -p 'test_*.py'
python3 skills/bootstrap-second-brain/evals/run_evals.py --suite all
python3 skills/bootstrap-second-brain/scripts/package_skill.py --check
python3 skills/bootstrap-second-brain/scripts/package_skill.py --write
python3 <skill-creator-root>/scripts/quick_validate.py skills/bootstrap-second-brain
python3 skills/bootstrap-second-brain/scripts/package_skill.py --verify-release
git diff --check
```

精确 Starter 文件数、source tree digest、inventory policy digest、allowlist digest、bundle SHA-256 与 bundle size 不写入 canonical Demo，避免形成摘要自引用；以当前 manifest、`.sha256` 制品和最终交付回执为准。

## 证据分层

| 维度 | 当前结论 | 声明上限 |
|---|---|---|
| structure_contract | 已验证 | schema、CLI、文件系统、Git、inventory、恢复、打包与测试合同 |
| distribution_authentication fixture | 已验证 | 临时真实 OpenSSH 密钥完成 bundle 与 attestation 双 namespace 签名验证 |
| 正式 distribution_authentication | 未验证 | 缺少 Owner 外部可信 verifier、公钥指纹、正式签名与 attestation 材料 |
| behavior_quality | deterministic passed | 只证明固定 cases、rubric anchor 与本地行为合同，不是模型 forward test |
| runtime_cost | 本地记录 | 只覆盖本机命令时间、测试数量和 bundle size |
| field_outcome | 未验证 | 尚无独立真实用户、七天闭环、三十天停止条件或两个独立 proven 场景 |

## 未关闭门禁

- Owner 决定许可证、第三方归属和公开分发策略。
- 用外部可信材料执行正式 `--verify-release`；无材料时预期为 `distribution_authentication=unverified` 与 `command_outcome=action_required`。
- 宿主提供可验证的 volume、removable 与 sync-provider 分类 adapter；在此之前 confidential runtime state 不落盘。
- 由独立真实用户完成首次初始化、Git baseline、一个真实问题闭环与七天回写，再决定是否从 validated 推进到 pilot。
- 至少两个独立真实场景取得可复核结果，并由 Owner 裁决后，才可声明 proven。

## 非目标

- 不自动 sudo、下载、调用包管理器、批量安装社区插件、修改全局 Git 配置、创建 remote、push 或改写 Git 历史。
- 不把打开官网、打开应用、文件存在、GUI 确认或 schema-valid attestation 单独解释为官方、ready、签名已验证或真实效果已验证。
- 不把 Demo 原样复制、包摘要一致、测试全绿或单机 dogfood 外推为跨机器正式分发和真实用户成效。
