#!/usr/bin/env python3
"""把当天学习收件批次渲染成 Obsidian 记录。"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
BASE_DIR = Path(__file__).parent.parent
INBOX_DIR = BASE_DIR / "inbox-收藏箱"
BATCHES_DIR = INBOX_DIR / "batches-批次"
RAW_DIR = INBOX_DIR / "raw-原始收件"
OBSIDIAN_DIR = Path.home() / "Obsidian/KnowledgeOS/00-Inbox 收件箱"

CHANNEL_TITLES = {
    "english-coach": "英语",
    "news-daily": "新闻",
    "learning-digest": "知识",
    "pending": "待定",
    "excluded": "排除项",
}


def now_shanghai() -> datetime:
    return datetime.now(TZ)


def active_batch_id() -> str:
    now = now_shanghai()
    if now.hour >= 23:
        now = now + timedelta(days=1)
    return now.strftime("%Y-%m-%d")


def batch_path(batch_id: str) -> Path:
    return BATCHES_DIR / f"{batch_id}.json"


def raw_path(batch_id: str) -> Path:
    return RAW_DIR / f"{batch_id}.jsonl"


def load_batch(batch_id: str) -> dict[str, Any]:
    return json.loads(batch_path(batch_id).read_text())


def load_items(batch_id: str) -> list[dict[str, Any]]:
    path = raw_path(batch_id)
    if not path.exists():
        return []
    items = []
    for line in path.read_text().splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


def render_item(item: dict[str, Any]) -> str:
    parts = [f"- `{item['source_type']}` | `{item['content_format']}` | `{item['status']}`"]
    parts.append(f"  来源：{item['source_value']}")
    if item.get("user_note"):
      parts.append(f"  备注：{item['user_note']}")
    if item.get("asset_path"):
      parts.append(f"  附件：{item['asset_path']}")
    return "\n".join(parts)


def render_note(batch: dict[str, Any], items: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    excluded: list[dict[str, Any]] = []

    for item in items:
        if item.get("exclusion_reason"):
            excluded.append(item)
            continue
        grouped[item.get("suggested_channel", "pending")].append(item)

    lines = [
        f"# 学习收件 {batch['batch_id']}",
        "",
        "## 批次信息",
        f"- 时区：{batch['batch_timezone']}",
        f"- 开窗：{batch['opened_at']}",
        f"- 软截点：{batch['soft_cutoff_at']}",
        f"- 硬截点：{batch['hard_cutoff_at']}",
        f"- 当前状态：{batch['batch_status']}",
        f"- 收件总数：{batch['intake_count']}",
        f"- 排除总数：{batch['excluded_count']}",
        "",
        "## 今日收件",
    ]

    for key in ("english-coach", "news-daily", "learning-digest", "pending"):
        lines.append(f"### {CHANNEL_TITLES[key]}")
        section_items = grouped.get(key, [])
        if not section_items:
            lines.append("- 暂无")
        else:
            for item in section_items:
                lines.append(render_item(item))
        lines.append("")

    lines.append("## 排除项")
    if not excluded:
        lines.append("- 暂无")
    else:
        for item in excluded:
            lines.append(render_item(item))
    lines.append("")

    lines.append("## 明日处理候选")
    ready_items = [item for item in items if item.get("status") != "excluded_work"]
    if not ready_items:
        lines.append("- 暂无")
    else:
        for item in ready_items:
            lines.append(
                f"- [{item['suggested_channel']}] {item['content_format']} -> {item['status']} | {item['source_value']}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", default=active_batch_id())
    args = parser.parse_args()

    batch = load_batch(args.batch_id)
    items = load_items(args.batch_id)
    OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)
    output = OBSIDIAN_DIR / f"learning-intake-学习收件-{args.batch_id}.md"
    output.write_text(render_note(batch, items), encoding="utf-8")
    print(f"✅ 已渲染 Obsidian 收件记录: {output}")


if __name__ == "__main__":
    main()
