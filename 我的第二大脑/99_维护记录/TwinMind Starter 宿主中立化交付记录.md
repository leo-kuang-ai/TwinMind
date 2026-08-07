# TwinMind Starter 宿主中立化交付记录

## 交付范围

- 日期：2026-08-07
- 实施单元：`U1. Separate Portable Core from Demo Tooling and Build Asset Projection`
- Canonical source：`我的第二大脑/`
- 发布投影：`skills/bootstrap-second-brain/assets/starter-kit/`
- Starter manifest：`skills/bootstrap-second-brain/manifests/starter-v1.json`
- Inventory policy：`skills/bootstrap-second-brain/manifests/inventory-policies-v1.json`

## 已完成

1. `AI协作协议.md`、`知识库索引.md` 和启动契约分别建立唯一、成对、不可嵌套的 managed-block 标记。
2. portable core 与 Demo tooling adapter 分层；WorkBuddy、Obsidian 或 Codex 不构成 Vault 格式依赖。
3. Python 3.11+ 标为 `runtime-required`，Git 标为 create 的 `product-required`，WorkBuddy 与 Obsidian 标为 `recommended`，社区插件标为 `optional` 且默认不安装。
4. WorkBuddy 官方初始入口更新为 `https://www.workbuddy.ai/`。
5. Starter manifest 记录语义版本、source commit、source tree digest、文件 SHA-256、所有权、层级和排除规则。
6. `personal-vault-v1` 固定 entries、depth、single-file、cumulative-read、elapsed、report-size、open-fd 和 filesystem-boundary 八项预算；run-local effective limits 只能逐项收紧。
7. 同步器只允许从 canonical 生成 assets，并拒绝绝对路径、`..`、控制字符、symlink、非法所有权、厂商强制绑定和 manifest 漂移。

## 验证证据

```text
python3 -m unittest skills/bootstrap-second-brain/tests/test_assets.py -v
python3 skills/bootstrap-second-brain/scripts/sync_starter_assets.py --write
python3 skills/bootstrap-second-brain/scripts/sync_starter_assets.py --check
```

- focused tests：12/12 通过。
- 重复 `--check`：无 canonical、manifest 或 assets diff。
- 最终文件数、source tree digest 和 inventory policy digest：以当前 `starter-v1.json` 和命令输出为准，避免在 canonical 文件内形成摘要自引用。

## 声明边界

- 本记录只证明 U1 的 canonical、manifest、inventory policy 和资产投影合同成立。
- 尚不证明 create、verify、adopt-existing、resume、Git baseline、工具安装引导、打包验签或真实用户 pilot 已完成。
- U2-U9 的后续本地实施证据见 `TwinMind第二大脑初始化Skill实施交付记录.md`；真实用户 pilot、正式分发验签与许可证仍保持独立门禁。

## 恢复方式

恢复 canonical 的本次变更后重新运行 `sync_starter_assets.py --write`，再运行 `--check`。不得手工修改 assets 后反向覆盖 canonical，也不得用 manifest 代替 Git 版本历史。
