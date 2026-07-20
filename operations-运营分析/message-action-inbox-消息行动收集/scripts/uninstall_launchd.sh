#!/usr/bin/env bash
set -euo pipefail

LABEL="com.xiaoxiao.message-action-inbox.hourly"
DST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl unload "$DST" >/dev/null 2>&1 || true
rm -f "$DST"
echo "unloaded $LABEL"
