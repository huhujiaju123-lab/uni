#!/bin/bash
# Lucky US 日报飞书推送 — cron 入口
#
# cron 配置示例（每天美东时间上午 10 点 = UTC 14:00 / 15:00）：
#   0 14 * * * /Users/xiaoxiao/Vibe\ coding/operations-运营分析/daily-report-日报/scripts-脚本/run_daily_feishu.sh >> /tmp/daily_feishu.log 2>&1
#
# 手动测试：
#   bash run_daily_feishu.sh            # 正式推送
#   bash run_daily_feishu.sh --dry-run  # 只看输出不发送

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

cd "$SCRIPT_DIR"
python3 send_to_feishu.py "$@"
