#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"
PROMPT="$(printf '%s' "$INPUT" | jq -r '.prompt // ""')"

if [[ "$PROMPT" =~ task-activity|0329|任务活动|买3杯|买5杯|free[[:space:]]drink|50%[[:space:]]off|buy3|buy5 ]]; then
  cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "当前实验为 2025-03-29 至 2025-04-05 的任务活动实验。三组互斥：A=买3杯送5折券，B=买5杯送5折券，C=买5杯送1杯免费券。任务在首单后激活，只统计已取杯核销订单，取消单和未取单不计数，每个用户最多完成一次。分析时先确认数据源、时间窗、分群口径、实验是否结束、数据是否完整。"
  }
}
JSON
fi
