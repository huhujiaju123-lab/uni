#!/usr/bin/env python3
"""根据 program manifest 生成可直接写稿的节目简报。"""

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
SCRIPT_BRIEF_TEMPLATES = CONFIG_DIR / "script_brief_templates-写稿简报模板.json"
MANIFEST_ROOT = STATE_DIR / "program_manifests-节目骨架"
BRIEF_ROOT = STATE_DIR / "episode_briefs-节目简报"


def now_shanghai() -> datetime:
    return datetime.now(TZ)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def summarise_items(items: list[dict[str, Any]]) -> list[str]:
    lines = []
    for idx, item in enumerate(items, start=1):
        note = item.get("user_note", "")
        note_suffix = f" | 备注: {note}" if note else ""
        lines.append(
            f"{idx}. [{item['suggested_channel']}] {item['source_type']} / "
            f"{item['content_format']} / {item['status']} / {item['source_value']}{note_suffix}"
        )
    return lines


def build_prompt_text(
    brief: dict[str, Any],
    brief_template: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    lines = [
        f"# {brief['label']} - {brief['manifest_id']}",
        "",
        "## 任务",
        brief_template["writing_goal"],
        "",
        "## 节目定位",
        f"- 分发目标：{brief['distribution_target']}",
        f"- 节目形态：{brief['output_family']}",
        f"- 目标时长：{brief['estimated_minutes']} 分钟",
        f"- 受众：{brief_template['audience']}",
        f"- 语言：{brief_template['default_language']}",
        f"- 叙述风格：{brief_template['narrator_style']}",
        f"- 脚本形式：{brief_template['script_shape']}",
        "",
        "## 必须覆盖",
    ]
    lines.extend(f"- {item}" for item in brief_template["must_cover"])
    lines.extend(
        [
            "",
            "## 节目章节",
        ]
    )
    for section in manifest["section_template"]:
        focus = brief_template["section_writing_focus"].get(section["section_id"], section["goal"])
        lines.append(f"- {section['label']}：{focus}")

    lines.extend(
        [
            "",
            "## 处理前依赖",
        ]
    )
    if brief["preflight_requirements"]:
        for req in brief["preflight_requirements"]:
            lines.append(f"- {req['step']}：{', '.join(req['item_ids'])}")
    else:
        lines.append("- 无")

    lines.extend(
        [
            "",
            "## 来源材料",
        ]
    )
    lines.extend(f"- {line}" for line in brief["source_summary_lines"])

    lines.extend(
        [
            "",
            "## 写稿约束",
        ]
    )
    lines.extend(f"- 必含：{item}" for item in manifest["generation_constraints"]["must_include"])
    lines.extend(f"- 禁含：{item}" for item in manifest["generation_constraints"]["must_exclude"])

    lines.extend(
        [
            "",
            "## 输出要求",
            "- 先给完整节目脚本结构，再给每一段正文。",
            "- 直接面向播客成稿，不写分析过程。",
            "- 不要混入工作内容、运营分析、AB实验。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_brief(
    manifest: dict[str, Any],
    learner_state: dict[str, Any],
    program_template: dict[str, Any],
    brief_template: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    channel_feedback = {}
    for channel in manifest["channels"]:
        channel_state = learner_state["channels"].get(channel, {})
        channel_feedback[channel] = {
            "avg_feedback_score": channel_state.get("avg_feedback_score"),
            "last_feedback_score": channel_state.get("last_feedback_score"),
            "last_feedback_at": channel_state.get("last_feedback_at"),
            "last_feedback_note": channel_state.get("last_feedback_note", ""),
            "weak_areas": channel_state.get("weak_areas", []),
            "mastered_concepts": channel_state.get("mastered_concepts", []),
        }

    return {
        "brief_id": manifest["manifest_id"],
        "manifest_id": manifest["manifest_id"],
        "plan_date": manifest["plan_date"],
        "timezone": manifest["timezone"],
        "generated_at": now_shanghai().isoformat(timespec="seconds"),
        "status": "ready_for_writing",
        "label": brief_template["label"],
        "distribution_target": manifest["distribution_target"],
        "output_family": manifest["output_family"],
        "estimated_minutes": manifest["estimated_minutes"],
        "channels": manifest["channels"],
        "writing_goal": brief_template["writing_goal"],
        "audience": brief_template["audience"],
        "default_language": brief_template["default_language"],
        "narrator_style": brief_template["narrator_style"],
        "script_shape": brief_template["script_shape"],
        "context": {
            "project_scope": learner_state["profile"]["project_scope"],
            "current_goals": learner_state["profile"]["current_goals"],
            "energy_today": learner_state["energy"]["today_score"],
            "energy_tags": learner_state["energy"]["today_tags"],
            "distribution_strategy": plan["context"]["distribution_strategy"],
        },
        "channel_feedback": channel_feedback,
        "section_template": manifest["section_template"],
        "section_writing_focus": brief_template["section_writing_focus"],
        "must_cover": brief_template["must_cover"],
        "generation_constraints": manifest["generation_constraints"],
        "preflight_requirements": manifest["preflight_requirements"],
        "source_summary_lines": summarise_items(manifest["source_items"]),
        "source_items": manifest["source_items"],
        "source_template_label": program_template["label"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", default=str(DAILY_PLAN))
    args = parser.parse_args()

    plan = load_json(Path(args.plan_file))
    learner_state = load_json(LEARNER_STATE)
    program_templates = load_json(PROGRAM_TEMPLATES)["templates"]
    brief_templates = load_json(SCRIPT_BRIEF_TEMPLATES)["templates"]

    plan_date = plan["plan_date"]
    manifest_dir = MANIFEST_ROOT / plan_date
    index_path = manifest_dir / "index.json"
    if not index_path.exists():
        raise SystemExit(f"节目骨架索引不存在: {index_path}")

    manifest_index = load_json(index_path)
    brief_dir = ensure_dir(BRIEF_ROOT / plan_date)

    brief_index = {
        "plan_date": plan_date,
        "generated_at": now_shanghai().isoformat(timespec="seconds"),
        "source_manifest_index": str(index_path),
        "brief_count": 0,
        "briefs": [],
    }

    for manifest_meta in manifest_index["manifests"]:
        manifest_path = Path(manifest_meta["path"])
        manifest = load_json(manifest_path)
        target = manifest["distribution_target"]
        brief = build_brief(
            manifest,
            learner_state,
            program_templates[target],
            brief_templates[target],
            plan,
        )
        json_path = brief_dir / f"{brief['brief_id']}.json"
        md_path = brief_dir / f"{brief['brief_id']}.md"
        json_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n")
        md_path.write_text(build_prompt_text(brief, brief_templates[target], manifest))
        brief_index["briefs"].append(
            {
                "brief_id": brief["brief_id"],
                "distribution_target": brief["distribution_target"],
                "json_path": str(json_path),
                "markdown_path": str(md_path),
            }
        )

    brief_index["brief_count"] = len(brief_index["briefs"])
    (brief_dir / "index.json").write_text(json.dumps(brief_index, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ 已生成节目简报目录: {brief_dir}")


if __name__ == "__main__":
    main()
