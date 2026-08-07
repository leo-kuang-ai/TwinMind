# Schema 子集

v0.1 的 schema 只使用离线、可由标准库确定性解释的关键字：`$schema`、`type`、`required`、`properties`、`items`、`enum`、`const`、`pattern`、`minLength`、`maxLength`、`minItems`、`maxItems`、`minimum`、`maximum`、`additionalProperties`、`oneOf`、`title` 和 `description`。

禁止 `$ref`、远程解析、`format` 及其他未实现关键字。`contract_validation.py` 在读取 schema 时先验证关键字集合，遇到未知内容失败关闭。Schema 只裁决形状；授权绑定、状态转移、敏感数据、证据强度和完成声明由显式不变量函数裁决。

兼容规则：`schema_version: 1` 是 v0.1 唯一可读版本；未知版本返回 action_required，不猜测迁移。新增可选字段前必须同步更新 schema、validator、消费者和正负 fixtures。
