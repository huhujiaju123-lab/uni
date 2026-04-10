#!/usr/bin/env python3
"""终端学习收件脚本。

用法示例：
  python capture_terminal_intake-终端收件.py start
  python capture_terminal_intake-终端收件.py add --source-type url --source-value "https://example.com"
  python capture_terminal_intake-终端收件.py add --source-type text --source-value "一段内容" --channel 英语
  python capture_terminal_intake-终端收件.py status
  python capture_terminal_intake-终端收件.py close
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


TZ = ZoneInfo("Asia/Shanghai")
BASE_DIR = Path(__file__).parent.parent
INBOX_DIR = BASE_DIR / "inbox-收藏箱"
BATCHES_DIR = INBOX_DIR / "batches-批次"
RAW_DIR = INBOX_DIR / "raw-原始收件"
ASSETS_DIR = INBOX_DIR / "assets-附件"
OBSIDIAN_DIR = Path.home() / "Obsidian/KnowledgeOS/00-Inbox 收件箱"

WORK_KEYWORDS = (
    "瑞幸",
    "luckin",
    "lucky us",
    "数据分析",
    "业务运营",
    "经营分析",
    "ab实验",
    "ab test",
    "sql",
    "报表",
    "增长运营",
)

CHANNEL_MAP = {
    "英语": "english-coach",
    "english": "english-coach",
    "新闻": "news-daily",
    "news": "news-daily",
    "知识": "learning-digest",
    "digest": "learning-digest",
    "待定": "pending",
    "pending": "pending",
}


@dataclass
class BatchWindow:
    batch_id: str
    batch_date: str
    open_at: datetime
    soft_cutoff_at: datetime
    hard_cutoff_at: datetime


def now_shanghai() -> datetime:
    return datetime.now(TZ)


def ensure_dirs() -> None:
    for path in (BATCHES_DIR, RAW_DIR, ASSETS_DIR, OBSIDIAN_DIR):
        path.mkdir(parents=True, exist_ok=True)


def make_window(for_date: datetime) -> BatchWindow:
    base = for_date.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    batch_id = base.strftime("%Y-%m-%d")
    return BatchWindow(
        batch_id=batch_id,
        batch_date=batch_id,
        open_at=base.replace(hour=6),
        soft_cutoff_at=base.replace(hour=22),
        hard_cutoff_at=base.replace(hour=23),
    )


def window_for_capture(now: datetime | None = None) -> BatchWindow:
    now = now or now_shanghai()
    today_window = make_window(now)
    if now >= today_window.hard_cutoff_at:
        return make_window(now + timedelta(days=1))
    if load_batch(today_window.batch_id) and load_batch(today_window.batch_id)["batch_status"] in {
        "frozen",
        "processing",
        "closed",
    }:
        return make_window(now + timedelta(days=1))
    return today_window


def window_for_today(now: datetime | None = None) -> BatchWindow:
    now = now or now_shanghai()
    return make_window(now)


def batch_path(batch_id: str) -> Path:
    return BATCHES_DIR / f"{batch_id}.json"


def raw_path(batch_id: str) -> Path:
    return RAW_DIR / f"{batch_id}.jsonl"


def load_batch(batch_id: str) -> dict[str, Any] | None:
    path = batch_path(batch_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_batch(data: dict[str, Any]) -> None:
    batch_path(data["batch_id"]).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def create_batch(window: BatchWindow, status: str = "collecting") -> dict[str, Any]:
    data = {
        "batch_id": window.batch_id,
        "batch_timezone": "Asia/Shanghai",
        "batch_date": window.batch_date,
        "opened_at": window.open_at.isoformat(timespec="seconds"),
        "soft_cutoff_at": window.soft_cutoff_at.isoformat(timespec="seconds"),
        "hard_cutoff_at": window.hard_cutoff_at.isoformat(timespec="seconds"),
        "batch_status": status,
        "intake_count": 0,
        "excluded_count": 0,
        "last_captured_at": None,
        "closed_at": None,
        "obsidian_note_path": str(OBSIDIAN_DIR / f"learning-intake-学习收件-{window.batch_id}.md"),
    }
    save_batch(data)
    return data


def start_batch() -> None:
    ensure_dirs()
    window = window_for_capture()
    batch = load_batch(window.batch_id)
    if batch is None:
        batch = create_batch(window)
        print(f"✅ 已开启学习收件: {window.batch_id}")
        return
    if batch["batch_status"] == "collecting":
        print(f"ℹ️ 今日批次已在收件中: {window.batch_id}")
        return
    batch["batch_status"] = "collecting"
    batch["closed_at"] = None
    save_batch(batch)
    print(f"✅ 已重新打开学习收件: {window.batch_id}")


def detect_content_format(source_type: str, source_value: str) -> str:
    lower = source_value.lower()
    if source_type == "url":
        if any(key in lower for key in ("youtube.com", "youtu.be", "bilibili.com", "b23.tv")):
            return "video"
        if any(key in lower for key in ("xiaoyuzhoufm.com", "podcast", "podcasts.apple.com")):
            return "podcast"
        if lower.endswith(".pdf"):
            return "pdf"
        return "article"
    if source_type == "file":
        suffix = Path(source_value).suffix.lower()
        if suffix == ".pdf":
            return "pdf"
        if suffix in {".md", ".markdown"}:
            return "markdown"
        if suffix == ".txt":
            return "text"
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
            return "image"
        return "file"
    if source_type == "image":
        return "image"
    if source_type == "text":
        return "pasted_text"
    return "unknown"


def detect_language(text: str) -> str:
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    if any("a" <= ch.lower() <= "z" for ch in text):
        return "en"
    return "unknown"


def infer_language(source_value: str, note: str) -> str:
    source_language = detect_language(source_value)
    if source_language != "unknown":
        return source_language
    return detect_language(note)


def infer_channel(channel: str | None, source_value: str, note: str) -> str:
    if channel:
        return CHANNEL_MAP.get(channel.strip().lower(), CHANNEL_MAP.get(channel.strip(), "pending"))
    probe = f"{source_value} {note}".lower()
    if "英语" in note or "english" in probe:
        return "english-coach"
    return "pending"


def detect_exclusion(source_value: str, note: str) -> str | None:
    probe = f"{source_value} {note}".lower()
    for keyword in WORK_KEYWORDS:
        if keyword.lower() in probe:
            return "excluded_work"
    return None


def default_status(content_format: str, exclusion_reason: str | None) -> str:
    if exclusion_reason:
        return exclusion_reason
    if content_format in {"video", "podcast"}:
        return "needs_transcript"
    if content_format == "image":
        return "needs_ocr"
    if content_format in {"article", "pdf"}:
        return "needs_fetch"
    return "ready_for_planning"


def append_raw(item: dict[str, Any]) -> None:
    path = raw_path(item["batch_id"])
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def recalculate_batch_counters(batch_id: str) -> tuple[int, int]:
    items = load_jsonl(raw_path(batch_id))
    intake_count = len(items)
    excluded_count = sum(1 for item in items if item.get("exclusion_reason") == "excluded_work")
    return intake_count, excluded_count


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for line in path.read_text().splitlines():
        if line.strip():
            result.append(json.loads(line))
    return result


def copy_asset_if_needed(source_type: str, source_value: str, item_id: str) -> str | None:
    if source_type not in {"file", "image"}:
        return None
    src = Path(source_value).expanduser()
    if not src.exists() or not src.is_file():
        return None
    dest_name = f"{item_id}{src.suffix.lower()}"
    dest = ASSETS_DIR / dest_name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return str(dest)


def capture_item(args: argparse.Namespace) -> None:
    ensure_dirs()
    now = now_shanghai()
    window = window_for_capture(now)
    batch = load_batch(window.batch_id) or create_batch(window)

    source_value = args.source_value.strip()
    note = args.note.strip()
    exclusion_reason = detect_exclusion(source_value, note)
    content_format = detect_content_format(args.source_type, source_value)
    suggested_channel = infer_channel(args.channel, source_value, note)
    if exclusion_reason:
        suggested_channel = "excluded"

    raw_id = hashlib.sha1(
        f"{window.batch_id}|{args.source_type}|{source_value}|{now.isoformat()}".encode("utf-8")
    ).hexdigest()[:12]
    asset_path = copy_asset_if_needed(args.source_type, source_value, raw_id)

    item = {
        "id": raw_id,
        "batch_id": window.batch_id,
        "captured_at": now.isoformat(timespec="seconds"),
        "source_type": args.source_type,
        "source_value": source_value,
        "content_format": content_format,
        "language_hint": infer_language(source_value, note),
        "suggested_channel": suggested_channel,
        "urgency": args.urgency,
        "status": default_status(content_format, exclusion_reason),
        "user_note": note,
        "obsidian_note_path": batch["obsidian_note_path"],
        "exclusion_reason": exclusion_reason,
        "asset_path": asset_path,
    }

    append_raw(item)
    batch["intake_count"], batch["excluded_count"] = recalculate_batch_counters(window.batch_id)
    batch["last_captured_at"] = now.isoformat(timespec="seconds")
    save_batch(batch)
    print(
        f"✅ 已收件: {item['id']} | 批次={item['batch_id']} | "
        f"频道={item['suggested_channel']} | 状态={item['status']}"
    )


def current_batch_for_status() -> dict[str, Any] | None:
    today = load_batch(window_for_today().batch_id)
    next_batch = load_batch(window_for_capture().batch_id)
    return next_batch or today


def find_collecting_batch() -> dict[str, Any] | None:
    candidate_ids = []
    for batch_id in (window_for_capture().batch_id, window_for_today().batch_id):
        if batch_id not in candidate_ids:
            candidate_ids.append(batch_id)

    for batch_id in candidate_ids:
        batch = load_batch(batch_id)
        if batch and batch.get("batch_status") == "collecting":
            return batch

    for path in sorted(BATCHES_DIR.glob("*.json"), reverse=True):
        batch = json.loads(path.read_text())
        if batch.get("batch_status") == "collecting":
            return batch
    return None


def show_status() -> None:
    batch = find_collecting_batch() or current_batch_for_status()
    if batch is None:
        print("ℹ️ 当前还没有学习收件批次")
        return
    print(json.dumps(batch, ensure_ascii=False, indent=2))


def close_batch() -> None:
    ensure_dirs()
    batch = find_collecting_batch()
    if batch is None:
        print("ℹ️ 今天没有正在收件的批次")
        return
    batch["batch_status"] = "frozen"
    batch["closed_at"] = now_shanghai().isoformat(timespec="seconds")
    save_batch(batch)
    print(f"✅ 已结束学习收件: {batch['batch_id']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("start")
    sub.add_parser("status")
    sub.add_parser("close")

    add = sub.add_parser("add")
    add.add_argument("--source-type", required=True, choices=["url", "file", "text", "image"])
    add.add_argument("--source-value", required=True)
    add.add_argument("--channel", default="")
    add.add_argument("--urgency", default="today", choices=["today", "this_week", "archive"])
    add.add_argument("--note", default="")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "start":
        start_batch()
    elif args.command == "status":
        show_status()
    elif args.command == "close":
        close_batch()
    elif args.command == "add":
        capture_item(args)


if __name__ == "__main__":
    main()
