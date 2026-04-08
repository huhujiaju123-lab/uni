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
  $(basename "$0") week-view YYYY-Wxx
  $(basename "$0") month-view YYYY-MM
  $(basename "$0") today-plan

Examples:
  $(basename "$0") add-log "周末提频" "周五上线支付返券" "running" "来访率;杯量" "与分享有礼对半流量"
  $(basename "$0") week-view 2026-W14
  $(basename "$0") month-view 2026-03
  $(basename "$0") today-plan
USAGE
}

ensure_week_file() {
  local week="$1"
  local f="$LOG_DIR/${week}.md"
  if [[ ! -f "$f" ]]; then
    cat > "$f" <<EOM
# ${week} 动作日志

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
  local iso_week
  iso_week="$(TZ=America/New_York date +%G-W%V)"
  local file="$LOG_DIR/${iso_week}.md"

  ensure_week_file "$iso_week"

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

week_view() {
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

today_plan() {
  local today dow iso_week week_file fallback_file
  today="$(TZ=America/New_York date +%F)"
  dow="$(TZ=America/New_York date +%u)"
  iso_week="$(TZ=America/New_York date +%G-W%V)"
  week_file="$LOG_DIR/${iso_week}.md"
  fallback_file="$(find "$LOG_DIR" -maxdepth 1 -name '20??-W??.md' | sort | tail -n 1)"

  echo "# 今日工作计划（${today} America/New_York）"
  echo

  echo "## 当前待办（李宵霄）"
  awk '
    /^## 当前待办（李宵霄）/ {flag=1; next}
    /^## / && flag {exit}
    flag && NF {print}
  ' "$BASE_DIR/07_工作待办.md"
  echo

  echo "## 今日固定任务"
  case "$dow" in
    1) echo "- 每周一：上线“上月已购 / 本月未购”策略" ;;
    4)
      echo "- 每周四：上线“来访未购”策略"
      echo "- 每周四：上线“上月已购 / 本月未购”策略"
      ;;
    7) echo "- 每周日：上线“来访未购”策略" ;;
  esac
  echo "- 每天：更换时段相关文案（工作日2条 + 周末2条，共4条）"
  echo

  echo "## 当前优先级"
  awk '
    /^## 当前优先级/ {flag=1; next}
    /^## / && flag {exit}
    flag && NF {print}
  ' "$BASE_DIR/00_项目总览.md"
  echo

  echo "## 进行中策略"
  python3 - "$LEDGER" <<'PY'
import csv, sys
with open(sys.argv[1], newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        status = row["status"]
        if status in {"running", "watching", "iterating"}:
            note = row["notes"].strip() or "无备注"
            print(f'- {row["strategy_name"]} [{status}]：{note}')
PY
  echo

  echo "## 待推进策略"
  python3 - "$LEDGER" <<'PY'
import csv, sys
with open(sys.argv[1], newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row["status"] == "planned":
            start = row["start_date_est"].strip() or "待定"
            note = row["notes"].strip() or "无备注"
            print(f'- {row["strategy_name"]} [planned]：预计 {start}，{note}')
PY
  echo

  echo "## 本周最近动作"
  if [[ -f "$week_file" ]]; then
    sed -n '1,240p' "$week_file"
  elif [[ -n "${fallback_file:-}" ]]; then
    echo "- 本周动作日志未创建，回退读取最近一份周日志：$(basename "$fallback_file")"
    echo
    sed -n '1,240p' "$fallback_file"
  else
    echo "- 本周动作日志未创建"
  fi
  echo

  echo "## 最近结论"
  awk '
    /^## 3\/31 周会结论/ {flag=1; next}
    /^## / && flag {exit}
    flag && NF {print}
  ' "$BASE_DIR/07_工作待办.md"
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
    week-view) week_view "$@" ;;
    month-view) month_view "$@" ;;
    today-plan) today_plan "$@" ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
