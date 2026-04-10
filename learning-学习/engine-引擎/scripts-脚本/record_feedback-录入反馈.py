#!/usr/bin/env python3
"""录入学习反馈并回写 learner_state。"""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

FEEDBACK_DIR = Path(__file__).parent.parent / "state-状态/feedback-反馈"
LEARNER_STATE = Path(__file__).parent.parent / "state-状态/learner_state-学习者状态.json"
TZ = ZoneInfo("Asia/Shanghai")


def now_shanghai() -> datetime:
    return datetime.now(TZ)


def feedback_date_shanghai(now: Optional[datetime] = None) -> str:
    now = now or now_shanghai()
    if now.hour >= 23:
        now = now + timedelta(days=1)
    return now.strftime("%Y-%m-%d")


def ensure_feedback_dir(feedback_dir: Path) -> None:
    feedback_dir.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_feedback_history(feedback_dir: Path, channel: str) -> list[dict[str, Any]]:
    events = []
    for feedback_file in sorted(feedback_dir.glob("*.jsonl")):
        for line in feedback_file.read_text().splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("channel") == channel and event.get("event") == "feedback":
                events.append(event)
    return events


def compute_avg_score(current_events: list[dict[str, Any]], new_score: int) -> float:
    scores = [event["score"] for event in current_events] + [new_score]
    return round(sum(scores) / len(scores), 2)


def merge_unique(existing: list[str], incoming: list[str] | None) -> list[str]:
    values = list(existing)
    for item in incoming or []:
        if item not in values:
            values.append(item)
    return values


def record(
    channel: str,
    score: int,
    note: str,
    concepts_mastered: list[str] | None = None,
    concepts_weak: list[str] | None = None,
    output_id: str = "",
    learner_state_path: Path = LEARNER_STATE,
    feedback_dir: Path = FEEDBACK_DIR,
) -> None:
    ensure_feedback_dir(feedback_dir)
    today = feedback_date_shanghai()
    feedback_file = feedback_dir / f"{today}.jsonl"
    now = now_shanghai()
    history = load_feedback_history(feedback_dir, channel)

    event = {
        "ts": now.isoformat(timespec="seconds"),
        "feedback_date": today,
        "channel": channel,
        "event": "feedback",
        "score": score,
        "note": note,
        "output_id": output_id,
    }
    if concepts_mastered:
        event["concepts_mastered"] = concepts_mastered
    if concepts_weak:
        event["concepts_weak"] = concepts_weak

    with feedback_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    state = load_json(learner_state_path)
    if channel in state["channels"]:
        channel_state = state["channels"][channel]
        channel_state["last_feedback_note"] = note
        channel_state["last_feedback_score"] = score
        channel_state["last_feedback_at"] = now.isoformat(timespec="seconds")
        channel_state["avg_feedback_score"] = compute_avg_score(history, score)
        channel_state["mastered_concepts"] = merge_unique(
            channel_state.get("mastered_concepts", []),
            concepts_mastered,
        )
        channel_state["weak_areas"] = merge_unique(
            channel_state.get("weak_areas", []),
            concepts_weak,
        )

        state["updated_at"] = now.isoformat(timespec="seconds")
        learner_state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    print(f"✅ 反馈已记录: {channel} | 评分={score}/5 | 均分={compute_avg_score(history, score)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True)
    parser.add_argument("--score", type=int, required=True, help="1-5分")
    parser.add_argument("--note", default="", help="文字反馈")
    parser.add_argument("--mastered", nargs="*", help="已掌握的概念")
    parser.add_argument("--weak", nargs="*", help="还没懂的概念")
    parser.add_argument("--output-id", default="", help="对应的节目输出 ID")
    parser.add_argument("--state-file", default=str(LEARNER_STATE), help="learner_state 路径")
    parser.add_argument("--feedback-dir", default=str(FEEDBACK_DIR), help="feedback 目录路径")
    args = parser.parse_args()
    record(
        args.channel,
        args.score,
        args.note,
        args.mastered,
        args.weak,
        args.output_id,
        Path(args.state_file),
        Path(args.feedback_dir),
    )
