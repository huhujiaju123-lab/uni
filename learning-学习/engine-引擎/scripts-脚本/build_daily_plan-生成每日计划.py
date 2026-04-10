#!/usr/bin/env python3
"""根据当天收件批次生成 daily_learning_plan。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config-配置"
STATE_DIR = BASE_DIR / "state-状态"
INBOX_DIR = BASE_DIR / "inbox-收藏箱"
BATCHES_DIR = INBOX_DIR / "batches-批次"
RAW_DIR = INBOX_DIR / "raw-原始收件"

LEARNER_STATE = STATE_DIR / "learner_state-学习者状态.json"
CHANNELS_CONFIG = CONFIG_DIR / "channels-频道配置.json"
DISTRIBUTION_CONFIG = CONFIG_DIR / "distribution-分发映射.json"
PLANNING_RULES = CONFIG_DIR / "planning-编排规则.json"
PLAN_OUTPUT = STATE_DIR / "daily_learning_plan-每日学习计划.json"


def now_shanghai() -> datetime:
    return datetime.now(TZ)


def active_batch_id() -> str:
    now = now_shanghai()
    if now.hour >= 23:
        now = now + timedelta(days=1)
    return now.strftime("%Y-%m-%d")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for line in path.read_text().splitlines():
        if line.strip():
            result.append(json.loads(line))
    return result


def urgency_rank(urgency: str, priority: list[str]) -> int:
    try:
        return priority.index(urgency)
    except ValueError:
        return len(priority)


def sort_items(items: list[dict[str, Any]], priority: list[str]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            urgency_rank(item.get("urgency", "archive"), priority),
            item.get("captured_at", ""),
            item.get("id", ""),
        ),
    )


def build_output_entry(
    template: dict[str, Any],
    collected_items: list[dict[str, Any]],
    channels_cfg: dict[str, Any],
    plan_date: str,
) -> dict[str, Any]:
    estimated = 0
    for channel in template["channels"]:
        estimated += channels_cfg["channels"].get(channel, {}).get("target_minutes", 0)
    return {
        "output_id": f"{template['output_id']}-{plan_date}",
        "distribution_target": template["distribution_target"],
        "channels": template["channels"],
        "estimated_minutes": estimated,
        "items": collected_items,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", default=active_batch_id())
    args = parser.parse_args()

    learner_state = load_json(LEARNER_STATE)
    channels_cfg = load_json(CHANNELS_CONFIG)
    distribution_cfg = load_json(DISTRIBUTION_CONFIG)
    planning_rules = load_json(PLANNING_RULES)

    batch_path = BATCHES_DIR / f"{args.batch_id}.json"
    raw_path = RAW_DIR / f"{args.batch_id}.jsonl"
    if not batch_path.exists():
        raise SystemExit(f"批次文件不存在: {batch_path}")

    batch = load_json(batch_path)
    raw_items = load_jsonl(raw_path)

    excluded_statuses = set(planning_rules["excluded_statuses"])
    deferred_channels = set(planning_rules["deferred_channels"])
    allowed_statuses = set(planning_rules["allowed_planning_statuses"])
    urgency_priority = planning_rules["urgency_priority"]
    channel_rules = planning_rules["channel_output_rules"]

    excluded_items = []
    deferred_items = []
    grouped_items: dict[str, list[dict[str, Any]]] = {}

    for item in raw_items:
        status = item.get("status")
        channel = item.get("suggested_channel", "pending")

        if status in excluded_statuses or item.get("exclusion_reason"):
            excluded_items.append(item)
            continue
        if channel in deferred_channels:
            deferred_items.append(item)
            continue
        if status not in allowed_statuses:
            deferred_items.append(item)
            continue
        grouped_items.setdefault(channel, []).append(item)

    outputs = []
    planned_ids = set()
    for template in planning_rules["default_output_layout"]:
        planned_items = []
        for channel in template["channels"]:
            channel_items = sort_items(grouped_items.get(channel, []), urgency_priority)
            max_items = channel_rules.get(channel, {}).get("max_items_per_plan", len(channel_items))
            chosen = channel_items[:max_items]
            for item in chosen:
                planned_items.append(item)
                planned_ids.add(item["id"])
        outputs.append(build_output_entry(template, planned_items, channels_cfg, args.batch_id))

    for channel, items in grouped_items.items():
        for item in items:
            if item["id"] not in planned_ids:
                deferred_items.append(item)

    plan = {
        "plan_date": args.batch_id,
        "timezone": learner_state["global_preferences"]["batch_timezone"],
        "source_batch_id": args.batch_id,
        "generated_at": now_shanghai().isoformat(timespec="seconds"),
        "status": planning_rules["plan_status"],
        "inputs_summary": {
            "total_items": len(raw_items),
            "excluded_items": len(excluded_items),
            "ready_items": len(raw_items) - len(excluded_items),
        },
        "context": {
            "project_scope": learner_state["profile"]["project_scope"],
            "current_goals": learner_state["profile"]["current_goals"],
            "energy_today": learner_state["energy"]["today_score"],
            "energy_tags": learner_state["energy"]["today_tags"],
            "distribution_strategy": distribution_cfg["strategy"],
        },
        "outputs": outputs,
        "deferred_items": sort_items(deferred_items, urgency_priority),
        "excluded_items": excluded_items,
        "batch_status": batch["batch_status"],
    }

    PLAN_OUTPUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ 已生成每日学习计划: {PLAN_OUTPUT}")


if __name__ == "__main__":
    main()
