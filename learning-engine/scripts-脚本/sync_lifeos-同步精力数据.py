#!/usr/bin/env python3
"""从 LifeOS 同步精力数据到 learner_state.json"""
import json
from pathlib import Path
from datetime import datetime

LIFEOS_ENERGY = Path.home() / ".claude/life-os/state/energy-log.jsonl"
LEARNER_STATE = Path(__file__).parent.parent / "state-状态/learner_state-学习者状态.json"

def sync():
    # 读取 LifeOS 最后一条精力记录
    if not LIFEOS_ENERGY.exists():
        print("⚠️  LifeOS energy-log.jsonl 不存在")
        return

    lines = LIFEOS_ENERGY.read_text().strip().split("\n")
    if not lines:
        print("⚠️  energy-log.jsonl 为空")
        return

    last_entry = json.loads(lines[-1])

    # 读取 learner_state
    state = json.loads(LEARNER_STATE.read_text())

    # 更新精力数据
    state["energy"]["today_score"] = last_entry.get("score")
    state["energy"]["today_tags"] = last_entry.get("tags", [])
    state["energy"]["source"] = "lifeos_sync"

    # 计算7天均值
    recent = [json.loads(l) for l in lines[-7:]]
    scores = [e["score"] for e in recent if "score" in e]
    state["energy"]["weekly_avg"] = round(sum(scores) / len(scores), 1) if scores else None

    # 根据精力动态调整难度
    score = last_entry.get("score", 7)
    for ch_name, ch_data in state["channels"].items():
        current = ch_data.get("difficulty_level", 3)
        if score < 6:
            ch_data["difficulty_level"] = max(1, current - 1)
        elif score >= 8.5:
            ch_data["difficulty_level"] = min(5, current + 1)

    state["updated_at"] = datetime.now().isoformat(timespec="seconds")

    # 写回
    LEARNER_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    print(f"✅ 同步完成: 精力={last_entry.get('score')}, 标签={last_entry.get('tags')}")

if __name__ == "__main__":
    sync()
