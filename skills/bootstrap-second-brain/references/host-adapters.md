# 宿主适配

v0.1 正式支持 Codex + macOS。Linux 仅声明文件系统兼容候选；Windows 和其他 Agent 宿主返回 action_required，不外推已验证支持。

Python/Git/OpenSSH 候选发现与信任分类由宿主原生能力完成。执行任何候选前检查 realpath、普通文件、owner/mode、父目录可写性、SHA-256、平台签名/公证或包收据和来源类型。PATH 只是候选来源，不是信任根。

可信 Python 以参数数组运行 `-I -S -E`；环境删除 `PYTHONPATH` 与 Python 用户 site 影响，工作目录不得成为导入源。runtime receipt 记录 requested/resolved path、版本、摘要、trust class 和探测时间；resume 时重新验证，漂移则 plan_stale。

CLI stdout 在 `--json` 下只含一个 JSON object，诊断进入 stderr。宿主负责把 exit code 与 `command_outcome` 一起解释，不从自然语言猜测成功。
