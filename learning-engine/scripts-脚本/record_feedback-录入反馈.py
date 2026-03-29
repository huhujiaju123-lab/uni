#!/usr/bin/env python3
"""
录入学习反馈
用法:
  python record_feedback.py --channel ai-daily --score 4 --note "Agent那期很好，但例子太少"
  python record_feedback.py --channel english-coach --score 3 --note "太难了，只听懂50%"
"""
import json
import argparse
from pathlib import Path
from datetime import datetime, date

FEEDBACK_DIR = Path(__file__).parent.parent / "state-状态/feedback-反馈"
LEARNER_STATE = Path(__file__).parent.parent / "state-状态/learner_state-学习者状态.json"

def record(channel, score, note, concepts_mastered=None, concepts_weak=None):
    today = date.today().isoformat()
    feedback_file = FEEDBACK_DIR / f"{today}.jsonl"

    event = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "channel": channel,
        "event": "feedback",
        "score": score,
        "note": note,
    }
    if concepts_mastered:
        event["concepts_mastered"] = concepts_mastered
    if concepts_weak:
        event["concepts_weak"] = concepts_weak

    # 追加写入
    with open(feedback_file, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    # 更新 learner_state 的最后反馈
    state = json.loads(LEARNER_STATE.read_text())
    if channel in state["channels"]:
        state["channels"][channel]["last_feedback_note"] = note
        # 更新掌握的概念
        if concepts_mastered:
            existing = state["channels"][channel].get("mastered_concepts", [])
            state["channels"][channel]["mastered_concepts"] = list(set(existing + concepts_mastered))
        if concepts_weak:
            existing = state["channels"][channel].get("weak_areas", [])
            state["channels"][channel]["weak_areas"] = list(set(existing + concepts_weak))

        state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        LEARNER_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

    print(f"✅ 反馈已记录: {channel} | 评分={score}/5 | {note}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True)
    parser.add_argument("--score", type=int, required=True, help="1-5分")
    parser.add_argument("--note", default="", help="文字反馈")
    parser.add_argument("--mastered", nargs="*", help="已掌握的概念")
    parser.add_argument("--weak", nargs="*", help="还没懂的概念")
    args = parser.parse_args()
    record(args.channel, args.score, args.note, args.mastered, args.weak)
