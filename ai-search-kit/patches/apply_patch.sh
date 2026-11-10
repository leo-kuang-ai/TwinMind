# khoj 嵌入批量补丁（幂等，容器每次启动自动执行）
# 根因: khoj 原版按 1000 条/批调用 embedding 接口，Ollama 的 llama-server
# 处理大批量时内部过载(413/400)，导致索引同步持续静默失败。
# 修复: 降为 32 条/批（实测安全值）。
F=/app/src/khoj/processor/embeddings.py
if grep -q 'range(0, len(docs), 1000)' "$F"; then
  sed -i 's/range(0, len(docs), 1000)/range(0, len(docs), 32)/; s/docs\[i : i + 1000\]/docs[i : i + 32]/; s/pbar.update(1000)/pbar.update(32)/' "$F"
  echo "[patch] applied: embed_documents batch 1000 -> 32"
elif grep -q 'range(0, len(docs), 32)' "$F"; then
  echo "[patch] already patched (batch=32)"
else
  echo "[patch] WARN: upstream file changed, batch pattern not found - manual review needed"
fi
