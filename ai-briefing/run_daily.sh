#!/bin/bash
# AI Builders Daily — 每日定时执行脚本
# cron 调用入口

cd "/Users/xiaoxiao/Vibe coding/ai-briefing"

# 设置 PATH（cron 环境没有用户 PATH）
export PATH="/usr/local/bin:/usr/bin:/bin:/Library/Developer/CommandLineTools/usr/bin:$PATH"

# 日志
LOG_FILE="logs/$(date +%Y-%m-%d).log"
mkdir -p logs

echo "===== $(date) =====" >> "$LOG_FILE"
python3 daily_pipeline.py >> "$LOG_FILE" 2>&1
echo "===== Done =====" >> "$LOG_FILE"
