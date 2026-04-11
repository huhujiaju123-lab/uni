#!/usr/bin/env python3
"""聚合当天播客脚本和公众号推文，生成每日交付入口。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
BASE_DIR = Path(__file__).parent.parent.resolve()
STATE_DIR = BASE_DIR / "state-状态"

DAILY_PLAN = STATE_DIR / "daily_learning_plan-每日学习计划.json"
PODCAST_ROOT = STATE_DIR / "podcast_scripts-播客脚本"
WECHAT_ROOT = STATE_DIR / "wechat_articles-公众号推文"
DELIVERY_ROOT = STATE_DIR / "daily_delivery-每日交付"


def now_shanghai() -> datetime:
    return datetime.now(TZ)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def by_target(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items}


def display_path(path_text: str) -> str:
    path = Path(path_text).resolve()
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def build_markdown(delivery: dict[str, Any]) -> str:
    lines = [
        f"# 每日学习交付 {delivery['plan_date']}",
        "",
        "## 使用方式",
        "- 上班路上先听播客。",
        "- 没听懂的地方，回到对应公众号图文稿补结构、背景和关键词。",
        "- 听完后用反馈脚本记录评分和薄弱点。",
        "",
        "## 今日交付",
    ]

    for item in delivery["outputs"]:
        lines.extend(
            [
                "",
                f"### {item['distribution_target']}",
                f"- 播客脚本：{display_path(item['podcast_script_path'])}",
                f"- 公众号推文：{display_path(item['wechat_article_markdown_path'])}",
                f"- 公众号配置：{display_path(item['wechat_article_json_path'])}",
            ]
        )

    lines.extend(
        [
            "",
            "## 下一步处理",
            "- 播客脚本可继续接 TTS 生成音频。",
            "- 公众号推文可继续补正文细节和配图。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", default=str(DAILY_PLAN))
    args = parser.parse_args()

    plan = load_json(Path(args.plan_file))
    plan_date = plan["plan_date"]

    podcast_index_path = PODCAST_ROOT / plan_date / "index.json"
    wechat_index_path = WECHAT_ROOT / plan_date / "index.json"
    if not podcast_index_path.exists():
        raise SystemExit(f"播客脚本索引不存在: {podcast_index_path}")
    if not wechat_index_path.exists():
        raise SystemExit(f"公众号推文索引不存在: {wechat_index_path}")

    podcast_index = load_json(podcast_index_path)
    wechat_index = load_json(wechat_index_path)
    podcasts = by_target(podcast_index["scripts"], "distribution_target")
    articles = by_target(wechat_index["articles"], "distribution_target")

    outputs = []
    for target, podcast in podcasts.items():
        article = articles.get(target)
        if not article:
            continue
        outputs.append(
            {
                "distribution_target": target,
                "podcast_script_path": podcast["path"],
                "podcast_segment_count": podcast["segment_count"],
                "wechat_article_json_path": article["json_path"],
                "wechat_article_markdown_path": article["markdown_path"],
            }
        )

    delivery = {
        "plan_date": plan_date,
        "generated_at": now_shanghai().isoformat(timespec="seconds"),
        "timezone": plan["timezone"],
        "source_plan_file": str(Path(args.plan_file)),
        "source_podcast_index": str(podcast_index_path),
        "source_wechat_index": str(wechat_index_path),
        "output_count": len(outputs),
        "outputs": outputs,
    }

    output_dir = ensure_dir(DELIVERY_ROOT / plan_date)
    (output_dir / "index.json").write_text(json.dumps(delivery, ensure_ascii=False, indent=2) + "\n")
    (output_dir / "README.md").write_text(build_markdown(delivery))
    print(f"✅ 已生成每日交付目录: {output_dir}")


if __name__ == "__main__":
    main()
