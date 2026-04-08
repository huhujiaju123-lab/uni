#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$HOME/.claude/life-os"
STATE_DIR="$BASE_DIR/state"
ARCHIVE_DIR="$BASE_DIR/archive/daily"
EVOLUTION_DIR="$BASE_DIR/evolution"
WEEKLY_DIR="$BASE_DIR/weekly"
PROFILE_FILE="$BASE_DIR/profile.md"
TODAY_FILE="$STATE_DIR/today.md"
FOCUS_FILE="$STATE_DIR/focus-queue.md"
ENERGY_LOG="$STATE_DIR/energy-log.jsonl"

mkdir -p "$STATE_DIR" "$ARCHIVE_DIR" "$EVOLUTION_DIR" "$WEEKLY_DIR"

if [[ ! -f "$PROFILE_FILE" ]]; then
  cat > "$PROFILE_FILE" <<'MD'
# Profile

## 基本信息
- 年龄：
- 工作：
- 坐标：

## 精力模式
- 充电方式：
- 耗电信号：

## 沟通偏好
- 偏好风格：
- 雷区：
MD
fi

if [[ ! -f "$TODAY_FILE" ]]; then
  cat > "$TODAY_FILE" <<'MD'
# Today

## 日期
- date: YYYY-MM-DD

## 今日焦点
-

## 会话记录
-

## 晚间复盘
- score:
- tags:
- note:
MD
fi

if [[ ! -f "$FOCUS_FILE" ]]; then
  cat > "$FOCUS_FILE" <<'MD'
# Focus Queue

- date: YYYY-MM-DD
- focus:
MD
fi

touch "$ENERGY_LOG"

echo "LifeOS initialized at: $BASE_DIR"
echo "Created/checked:"
echo "- $PROFILE_FILE"
echo "- $TODAY_FILE"
echo "- $FOCUS_FILE"
echo "- $ENERGY_LOG"
