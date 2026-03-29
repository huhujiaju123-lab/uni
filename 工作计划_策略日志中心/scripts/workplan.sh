#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$BASE_DIR/03_动作日志"
LEDGER="$BASE_DIR/01_策略台账.csv"

usage() {
  cat <<USAGE
Usage:
  $(basename "$0") add-log "项目" "动作" "状态" "目标指标" [备注]
  $(basename "$0") add-strategy "strategy_id" "strategy_name" "goal" "audience" "trigger_channel" "offer_or_action" "ab_design" "core_metrics" "secondary_metrics" "status" "start_date" "owner" [notes]
  $(basename "$0") month-view YYYY-MM

Examples:
  $(basename "$0") add-log "周末提频" "周五上线支付返券" "running" "来访率;杯量" "与分享有礼对半流量"
  $(basename "$0") month-view 2026-03
USAGE
}

ensure_month_file() {
  local month="$1"
  local f="$LOG_DIR/${month}.md"
  if [[ ! -f "$f" ]]; then
    cat > "$f" <<EOM
# ${month} 动作日志

EOM
  fi
}

add_log() {
  if [[ $# -lt 4 ]]; then
    usage; exit 1
  fi
  local project="$1"
  local action="$2"
  local status="$3"
  local metrics="$4"
  local note="${5:-}"

  local date_est
  date_est="$(TZ=America/New_York date +%F)"
  local month
  month="$(TZ=America/New_York date +%Y-%m)"
  local file="$LOG_DIR/${month}.md"

  ensure_month_file "$month"

  {
    echo "## ${date_est}（America/New_York）"
    echo "- 项目：${project}"
    echo "- 动作：${action}"
    echo "- 状态：${status}"
    echo "- 目标指标：${metrics}"
    [[ -n "$note" ]] && echo "- 备注：${note}" || true
    echo
  } >> "$file"

  echo "Logged to: $file"
}

add_strategy() {
  if [[ $# -lt 12 ]]; then
    usage; exit 1
  fi

  local notes="${13:-}"
  printf '%s,"%s","%s","%s","%s","%s","%s","%s","%s",%s,%s,,%s,"%s"\n' \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "$10" "$11" "$12" "$notes" >> "$LEDGER"

  echo "Added strategy into: $LEDGER"
}

month_view() {
  if [[ $# -ne 1 ]]; then
    usage; exit 1
  fi
  local file="$LOG_DIR/$1.md"
  if [[ ! -f "$file" ]]; then
    echo "No log file: $file"
    exit 1
  fi
  sed -n '1,260p' "$file"
}

main() {
  if [[ $# -lt 1 ]]; then
    usage; exit 1
  fi

  local cmd="$1"
  shift

  case "$cmd" in
    add-log) add_log "$@" ;;
    add-strategy) add_strategy "$@" ;;
    month-view) month_view "$@" ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
