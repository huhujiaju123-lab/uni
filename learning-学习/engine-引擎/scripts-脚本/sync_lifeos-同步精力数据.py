#!/usr/bin/env python3
"""从 LifeOS 同步精力数据到 learner_state.json"""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LIFEOS_ENERGY = Path.home() / ".claude/life-os/state/energy-log.jsonl"
LEARNER_STATE = Path(__file__).parent.parent / "state-状态/learner_state-学习者状态.json"
TZ = ZoneInfo("Asia/Shanghai")


def sync():
    if not LIFEOS_ENERGY.exists():
        print("⚠️  LifeOS energy-log.jsonl 不存在")
        return

    lines = [line for line in LIFEOS_ENERGY.read_text().splitlines() if line.strip()]
    if not lines:
        print("⚠️  energy-log.jsonl 为空")
        return

    last_entry = json.loads(lines[-1])
    state = json.loads(LEARNER_STATE.read_text())

    state.setdefault("energy", {})
    state["energy"]["today_score"] = last_entry.get("score")
    state["energy"]["today_tags"] = last_entry.get("tags", [])
    state["energy"]["source"] = "lifeos_sync"

    recent = [json.loads(line) for line in lines[-7:]]
    scores = [entry["score"] for entry in recent if "score" in entry]
    state["energy"]["weekly_avg"] = round(sum(scores) / len(scores), 1) if scores else None

    # LifeOS 同步只负责写入原始状态，不负责做频道策略决策。
    state["updated_at"] = datetime.now(TZ).isoformat(timespec="seconds")

    LEARNER_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    print(
        f"✅ 同步完成: 精力={state['energy']['today_score']}, "
        f"标签={state['energy']['today_tags']}"
    )


if __name__ == "__main__":
    sync()
