#!/usr/bin/env python3
"""根据 episode brief 生成公众号每日图文稿。"""

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
ARTICLE_ROOT = STATE_DIR / "wechat_articles-公众号推文"
WECHAT_TEMPLATES = CONFIG_DIR / "wechat_article_templates-公众号推文模板.json"


def now_shanghai() -> datetime:
    return datetime.now(TZ)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def title_for(brief: dict[str, Any], template: dict[str, Any]) -> str:
    return f"{template['title_prefix']}｜{brief['plan_date']}"


def image_prompt(slot: dict[str, str], template: dict[str, Any], brief: dict[str, Any]) -> str:
    visual_style = template["visual_style"].rstrip("。.")
    theme = brief["writing_goal"].rstrip("。.")
    return (
        f"{slot['purpose']}。风格：{visual_style}。"
        f"主题：{theme}"
    )


def source_list(brief: dict[str, Any]) -> list[str]:
    lines = []
    for item in brief["source_items"]:
        note = item.get("user_note", "")
        note_suffix = f"。备注：{note}" if note else ""
        lines.append(
            f"- `{item['suggested_channel']}`｜{item['content_format']}｜{item['status']}｜"
            f"{item['source_value']}{note_suffix}"
        )
    return lines


def concept_block(brief: dict[str, Any]) -> list[str]:
    constraints = brief.get("generation_constraints", {})
    must = constraints.get("must_include", [])
    lines = []
    for item in must:
        lines.append(f"- **{item}**：待正式成稿时结合原始材料展开。")
    if not lines:
        lines.append("- 暂无，需要在正式成稿时补充。")
    return lines


def build_article_markdown(brief: dict[str, Any], template: dict[str, Any]) -> str:
    lines = [
        f"# {title_for(brief, template)}",
        "",
        f"> {template['subtitle']}",
        "",
        "## 配图需求",
    ]
    for slot in template["image_slots"]:
        lines.append(f"- **{slot['label']}**：{image_prompt(slot, template, brief)}")

    lines.extend(
        [
            "",
            "## 今天这期听什么",
            f"这篇图文对应播客输出：`{brief['brief_id']}`。",
            f"建议先在通勤路上听播客，再用这篇文章补齐没听懂的背景、结构和关键词。",
            "",
            "## 来源材料",
        ]
    )
    lines.extend(source_list(brief))

    for section in template["sections"]:
        lines.extend(["", f"## {section}"])
        if section in {"没听懂时看这里", "听不懂的概念补充", "播客里最重要的表达"}:
            lines.extend(concept_block(brief))
        elif section in {"今天的练习动作", "复习清单"}:
            lines.extend(
                [
                    "- 听播客时先不暂停，完整听一遍。",
                    "- 第二遍只停在没听懂的地方。",
                    "- 看这篇图文，把关键词和结构补齐。",
                    "- 最后用自己的话复述一个要点。",
                ]
            )
        elif section in {"新闻输入", "知识输入"}:
            matched = [
                item for item in brief["source_items"]
                if item["suggested_channel"] in {"news-daily", "learning-digest"}
            ]
            if matched:
                for item in matched:
                    lines.append(f"- {item['source_value']}")
            else:
                lines.append("- 今天这一部分暂无来源材料。")
        else:
            lines.append("待正式成稿时结合来源材料展开。")

    lines.extend(
        [
            "",
            "## 发布前检查",
            "- 标题是否说明今天主题",
            "- 配图是否覆盖封面、结构和概念",
            "- 是否没有混入工作内容",
            "- 是否能补充播客里听不懂的地方",
        ]
    )
    return "\n".join(lines) + "\n"


def build_article_json(brief: dict[str, Any], template: dict[str, Any], md_path: Path) -> dict[str, Any]:
    return {
        "article_id": brief["brief_id"],
        "plan_date": brief["plan_date"],
        "generated_at": now_shanghai().isoformat(timespec="seconds"),
        "status": "draft",
        "distribution_target": brief["distribution_target"],
        "title": title_for(brief, template),
        "subtitle": template["subtitle"],
        "visual_style": template["visual_style"],
        "image_slots": [
            {
                **slot,
                "prompt": image_prompt(slot, template, brief),
            }
            for slot in template["image_slots"]
        ],
        "source_brief_id": brief["brief_id"],
        "markdown_path": str(md_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", default=str(DAILY_PLAN))
    args = parser.parse_args()

    plan = load_json(Path(args.plan_file))
    plan_date = plan["plan_date"]
    brief_index_path = BRIEF_ROOT / plan_date / "index.json"
    if not brief_index_path.exists():
        raise SystemExit(f"节目简报索引不存在: {brief_index_path}")

    templates = load_json(WECHAT_TEMPLATES)["templates"]
    brief_index = load_json(brief_index_path)
    output_dir = ensure_dir(ARTICLE_ROOT / plan_date)

    article_index = {
        "plan_date": plan_date,
        "generated_at": now_shanghai().isoformat(timespec="seconds"),
        "source_brief_index": str(brief_index_path),
        "article_count": 0,
        "articles": [],
    }

    for brief_meta in brief_index["briefs"]:
        brief = load_json(Path(brief_meta["json_path"]))
        target = brief["distribution_target"]
        template = templates[target]
        md_path = output_dir / f"{brief['brief_id']}.md"
        json_path = output_dir / f"{brief['brief_id']}.json"
        md_path.write_text(build_article_markdown(brief, template))
        article = build_article_json(brief, template, md_path)
        json_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n")
        article_index["articles"].append(
            {
                "article_id": article["article_id"],
                "distribution_target": target,
                "json_path": str(json_path),
                "markdown_path": str(md_path),
            }
        )

    article_index["article_count"] = len(article_index["articles"])
    (output_dir / "index.json").write_text(json.dumps(article_index, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ 已生成公众号推文目录: {output_dir}")


if __name__ == "__main__":
    main()
