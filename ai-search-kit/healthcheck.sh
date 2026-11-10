#!/bin/bash
# ai-search-kit 健康检查：异常推 IM webhook（飞书/钉钉/企业微信机器人均可），正常静默。
# 定时执行示例（crontab -e）：*/15 * * * * sh /path/to/ai-search-kit/healthcheck.sh
WEBHOOK="${KHOJ_ALERT_WEBHOOK:-}"          # 建议用环境变量注入，勿写死入库
ALERT_LOG="$(dirname "$0")/.health_alerts.log"
MSG=""

# ① khoj Web 存活
curl -s --max-time 5 http://127.0.0.1:42110/ >/dev/null || MSG+="khoj Web 无响应; "
# ② Ollama 存活
curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null || MSG+="Ollama 无响应; "
# ③ 容器状态（应为 2 个 running）
[ "$(docker ps --filter name=khoj --filter status=running -q | wc -l | tr -d ' ')" = "2" ] || MSG+="khoj 容器异常; "
# ④ 磁盘水位
[ "$(df -g / | awk 'NR==2{print $5}' | tr -d '%')" -lt 92 ] || MSG+="磁盘超92%; "

if [ -n "$MSG" ]; then
  # 同一故障 2 小时防重发
  NOW=$(date +%s); LAST=$(tail -1 "$ALERT_LOG" 2>/dev/null)
  echo "$NOW|$MSG" >> "$ALERT_LOG"
  if [ -n "$LAST" ] && [ $((NOW - ${LAST%%|*})) -lt 7200 ]; then exit 0; fi
  [ -z "$WEBHOOK" ] && echo "[healthcheck] $MSG (未配 KHOJ_ALERT_WEBHOOK，仅本地记录)" && exit 0
  curl -s "$WEBHOOK" -H 'Content-Type: application/json' \
    -d "{\"msg_type\":\"text\",\"content\":{\"text\":\"[第二大脑检索栈] $MSG\"}}"
fi
