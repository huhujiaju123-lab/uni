#!/usr/bin/env python3
"""根据 episode brief 生成可接 TTS 的播客脚本 JSON。"""

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

DAILY_PLAN = STATE_DIR / "daily_learning_plan-每日学习计划.json"
BRIEF_ROOT = STATE_DIR / "episode_briefs-节目简报"
SCRIPT_ROOT = STATE_DIR / "podcast_scripts-播客脚本"
PODCAST_TEMPLATES = CONFIG_DIR / "podcast_script_templates-播客脚本模板.json"


def now_shanghai() -> datetime:
    return datetime.now(TZ)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def segment(speaker: str, text: str, new_topic: bool = False) -> dict[str, Any]:
    return {
        "speaker": speaker,
        "text": text,
        "new_topic": new_topic,
    }


def source_text(item: dict[str, Any]) -> str:
    note = item.get("user_note", "")
    note_text = f"。你的备注是：{note}" if note else ""
    return (
        f"来源类型是 {item['source_type']}，格式是 {item['content_format']}，"
        f"当前处理状态是 {item['status']}。材料是：{item['source_value']}{note_text}"
    )


def build_script(brief: dict[str, Any], template: dict[str, Any]) -> list[dict[str, Any]]:
    speaker = template["speaker"]
    script = [
        segment(speaker, template["opening"], True),
        segment(
            speaker,
            f"今天这期对应的输出是 {brief['distribution_target']}，目标时长大约 {brief['estimated_minutes']} 分钟。",
        ),
    ]

    focus_map = brief.get("section_writing_focus", {})
    section_intro = template["section_intros"]
    for section in brief["section_template"]:
        section_id = section["section_id"]
        intro = section_intro.get(section_id, section["label"])
        focus = focus_map.get(section_id, section["goal"])
        script.append(segment(speaker, f"{intro} {focus}", True))

        matched_items = brief["source_items"]
        if section_id in {"input_focus", "news_brief", "knowledge_brief"} and matched_items:
            for item in matched_items:
                script.append(segment(speaker, source_text(item)))

    if brief.get("preflight_requirements"):
        waits = []
        for req in brief["preflight_requirements"]:
            waits.append(f"{req['step']}：{', '.join(req['item_ids'])}")
        script.append(segment(speaker, "正式成稿前，还需要处理这些材料：" + "；".join(waits), True))

    script.append(segment(speaker, template["closing"], True))
    return script


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", default=str(DAILY_PLAN))
    args = parser.parse_args()

    plan = load_json(Path(args.plan_file))
    plan_date = plan["plan_date"]
    brief_index_path = BRIEF_ROOT / plan_date / "index.json"
    if not brief_index_path.exists():
        raise SystemExit(f"节目简报索引不存在: {brief_index_path}")

    templates = load_json(PODCAST_TEMPLATES)["templates"]
    brief_index = load_json(brief_index_path)
    output_dir = ensure_dir(SCRIPT_ROOT / plan_date)

    script_index = {
        "plan_date": plan_date,
        "generated_at": now_shanghai().isoformat(timespec="seconds"),
        "source_brief_index": str(brief_index_path),
        "script_count": 0,
        "scripts": [],
    }

    for brief_meta in brief_index["briefs"]:
        brief = load_json(Path(brief_meta["json_path"]))
        target = brief["distribution_target"]
        script = build_script(brief, templates[target])
        script_path = output_dir / f"{brief['brief_id']}.json"
        script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n")
        script_index["scripts"].append(
            {
                "script_id": brief["brief_id"],
                "distribution_target": target,
                "path": str(script_path),
                "segment_count": len(script),
            }
        )

    script_index["script_count"] = len(script_index["scripts"])
    (output_dir / "index.json").write_text(json.dumps(script_index, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ 已生成播客脚本目录: {output_dir}")


if __name__ == "__main__":
    main()
