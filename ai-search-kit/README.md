# ai-search-kit：可选的语义检索升级配件

> 当"准确关键词仍稳定漏召回"的真实失败反复出现并登记后（见 [工具选择与升级门禁](../我的第二大脑/30_知识主题/工具选择与升级门禁.md)），用这套配件把第二大脑升级为 **本地向量检索 + RAG 问答**。在那之前，请先用 Obsidian 全文搜索——把每次"找不到"记到维护日志，那就是你的升级依据与评测题来源。

## 这套配件是什么

一套经过生产验证的本地语义检索编排（全部开源组件，数据不出本机——云端只接触"检索后的少量片段"，且可整体换成全本地）：

- **khoj**（Docker）：增量索引调度、检索重排、问答编排
- **Postgres + pgvector**：条目原文 + 向量同库存储
- **Ollama + qwen3-embedding:0.6b**：本地嵌入（639MB / 1024 维 / 中文效果好）
- **云端 LLM**（OpenAI 兼容端点，可选）：只做最后一步回答生成
- **golden set 评测**：换模型/调阈值/升级前后跑 Recall@5 与 MRR，回归超 5 个百分点不合入

```
Obsidian（内容源，唯一事实源）
  └─ khoj 插件约 5 分钟一轮推变更全文
       └─ khoj-server：hash 增量 → 32 条/批 → Ollama 向量化 → pgvector
            └─ 查询：向量检索 top10（阈值 0.7）→ cross-encoder 重排 → LLM 生成带引用回答
```

## 启用前五问（对应升级门禁）

1. 解决了哪个可复现的真实失败？——需先在维护日志登记漏召回样本
2. 它会读取、上传或修改什么数据？——读你的 Markdown 全文；云端 LLM 只见检索片段
3. 索引、缓存写到哪里？——Docker 卷（`khoj_db` / `khoj_models`），可删除重建
4. 失败如何被发现？——`healthcheck.sh` 定时巡检 + 告警
5. 如何停用并恢复？——`docker compose down`；内容层零污染，向量库整体可弃

## 快速启用（5 步）

```bash
# ① Ollama 嵌入服务
brew install ollama && ollama pull qwen3-embedding:0.6b
curl http://localhost:11434/v1/embeddings -d '{"model":"qwen3-embedding:0.6b","input":"测试"}'
#    ↑ 应返回 1024 维 embedding 数组

# ② 密钥（不进 Git）
cd ai-search-kit
echo "KHOJ_DB_PASSWORD=$(openssl rand -hex 16)" > .env
echo "KHOJ_DJANGO_SECRET_KEY=$(openssl rand -hex 32)" >> .env

# ③ 起服务（补丁已通过 entrypoint 挂载自动应用）
docker compose up -d
#    打开 http://127.0.0.1:42110

# ④ 配模型：检索模型指向 http://host.docker.internal:11434（qwen3-embedding:0.6b），
#    阈值 0.7；聊天模型配任意 OpenAI 兼容端点

# ⑤ 先建评测基线，再连 Obsidian（khoj 插件指向 127.0.0.1:42110）
cp eval/golden_set.example.json eval/golden_set.json   # 改成你自己的真实问题
python3 eval/eval_khoj.py --label baseline
```

## 三个必踩坑（生产实测换来的）

| 坑 | 症状 | 修法（本 kit 已内置） |
| --- | --- | --- |
| 嵌入批量过大 | 索引同步 413/400 反复失败，甚至静默失败 | `patches/apply_patch.sh` 由 compose entrypoint 启动时幂等降为 32 条/批 |
| 阈值不随模型走 | 聊天答不出知识库内容，检索日志正常 | qwen3 用 0.7（bge 系默认 0.18 会滤光结果） |
| 换模型不重嵌 | 新旧向量空间混用，检索污染 | 换模型 = 改配置 → 全量重嵌 → 重调阈值 → 重跑评测，四步缺一不可 |

## 评测门禁纪律

- golden set 从**日常真实提问**攒 15-25 题；`expect` 用不出现在问题里的文件路径关键词（防背题）
- 换向量模型 / 调阈值 / 升级 khoj 前后各跑一次 `eval_khoj.py`，**Recall@5 回退超 5 个百分点不得合入**
- 结果报告落盘在 `eval/`，作为下次变更的对照基线

## 安全与边界

- **敏感内容默认不进云端生成链路**：需要更强隔离时，把聊天模型换成本地 Ollama（暴露面即收窄到本机）
- 凭据走 `.env`（已 gitignore），永不入库
- 向量库、嵌入缓存是**可删除重建的投影**——与内容层冲突时永远以内容为准
- 升级镜像后补丁模式需复核：启动日志出现 `WARN: upstream file changed` 时人工检查 `apply_patch.sh`

## 文件清单

| 文件 | 用途 |
| --- | --- |
| `compose.yml` | khoj + pgvector 编排（端口只绑 127.0.0.1，补丁自动挂载） |
| `patches/apply_patch.sh` | 嵌入批量 1000→32 幂等补丁 |
| `eval/eval_khoj.py` | Recall@5 / MRR 评测脚本 |
| `eval/golden_set.example.json` | 评测集示例（替换为你自己的真实问题） |
| `healthcheck.sh` | 存活/容器/磁盘巡检骨架，异常推 IM webhook |

> 组件版本锚点：`ghcr.io/khoj-ai/khoj:2.0.0-beta.28` + `pgvector/pgvector:pg15` + `qwen3-embedding:0.6b`。换用 latest 时，补丁脚本的模式匹配需先验证。
