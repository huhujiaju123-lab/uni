#!/usr/bin/env python3
"""根据 daily_learning_plan 生成每个节目的结构化骨架。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config-配置"
STATE_DIR = BASE_DIR / "state-状态"

LEARNER_STATE = STATE_DIR / "learner_state-学习者状态.json"
DAILY_PLAN = STATE_DIR / "daily_learning_plan-每日学习计划.json"
PROGRAM_TEMPLATES = CONFIG_DIR / "program_templates-节目模板.json"
MANIFEST_ROOT = STATE_DIR / "program_manifests-节目骨架"


def now_shanghai() -> datetime:
    return datetime.now(TZ)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def ensure_manifest_dir(plan_date: str) -> Path:
    output_dir = MANIFEST_ROOT / plan_date
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def preflight_for_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapping = {
        "needs_fetch": "fetch",
        "needs_transcript": "transcript",
        "needs_ocr": "ocr",
        "ready_for_planning": "ready",
    }
    grouped: dict[str, list[str]] = {}
    for item in items:
        stage = mapping.get(item.get("status"), "ready")
        grouped.setdefault(stage, []).append(item["id"])
    return [
        {
            "step": stage,
            "item_ids": ids,
        }
        for stage, ids in grouped.items()
    ]


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "source_type": item["source_type"],
        "source_value": item["source_value"],
        "content_format": item["content_format"],
        "suggested_channel": item["suggested_channel"],
        "urgency": item["urgency"],
        "status": item["status"],
        "user_note": item.get("user_note", ""),
    }


def build_manifest(
    output_entry: dict[str, Any],
    learner_state: dict[str, Any],
    templates: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    target = output_entry["distribution_target"]
    template = templates[target]
    items = output_entry.get("items", [])
    channels = output_entry.get("channels", [])

    channel_context = {}
    for channel in channels:
        channel_context[channel] = learner_state["channels"].get(channel, {})

    return {
        "manifest_id": output_entry["output_id"],
        "plan_date": plan["plan_date"],
        "timezone": plan["timezone"],
        "generated_at": now_shanghai().isoformat(timespec="seconds"),
        "status": "outline",
        "distribution_target": target,
        "label": template["label"],
        "output_family": template["output_family"],
        "estimated_minutes": output_entry["estimated_minutes"],
        "channels": channels,
        "narrative_goal": template["narrative_goal"],
        "tone": template["tone"],
        "context": {
            "project_scope": learner_state["profile"]["project_scope"],
            "current_goals": learner_state["profile"]["current_goals"],
            "energy_today": learner_state["energy"]["today_score"],
            "energy_tags": learner_state["energy"]["today_tags"],
        },
        "channel_context": channel_context,
        "section_template": template["section_template"],
        "generation_constraints": template["generation_constraints"],
        "preflight_requirements": preflight_for_items(items),
        "source_items": [compact_item(item) for item in items],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", default=str(DAILY_PLAN))
    args = parser.parse_args()

    learner_state = load_json(LEARNER_STATE)
    plan = load_json(Path(args.plan_file))
    templates = load_json(PROGRAM_TEMPLATES)["templates"]
    output_dir = ensure_manifest_dir(plan["plan_date"])

    manifests = []
    for output in plan.get("outputs", []):
        manifest = build_manifest(output, learner_state, templates, plan)
        manifest_path = output_dir / f"{manifest['manifest_id']}.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        manifests.append(
            {
                "manifest_id": manifest["manifest_id"],
                "distribution_target": manifest["distribution_target"],
                "path": str(manifest_path),
            }
        )

    index = {
        "plan_date": plan["plan_date"],
        "generated_at": now_shanghai().isoformat(timespec="seconds"),
        "source_plan_file": str(Path(args.plan_file)),
        "manifest_count": len(manifests),
        "manifests": manifests,
    }
    index_path = output_dir / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ 已生成节目骨架目录: {output_dir}")


if __name__ == "__main__":
    main()
