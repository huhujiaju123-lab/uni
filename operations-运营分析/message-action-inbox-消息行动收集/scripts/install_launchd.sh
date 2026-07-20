#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.xiaoxiao.message-action-inbox.hourly"
SRC="$ROOT/launchd/$LABEL.plist"
DST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/state"
cp "$SRC" "$DST"
launchctl unload "$DST" >/dev/null 2>&1 || true
launchctl load "$DST"
launchctl start "$LABEL" || true
echo "loaded $LABEL"
echo "$DST"
