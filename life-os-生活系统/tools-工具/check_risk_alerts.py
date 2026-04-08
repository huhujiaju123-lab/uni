#!/usr/bin/env python3
"""L3: Check LifeOS energy risk alerts and write machine + human readable output."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import pstdev
from typing import Any


ENERGY_LOG = Path.home() / ".claude/life-os/state/energy-log.jsonl"
STATE_DIR = Path.home() / ".claude/life-os/state"
JSON_OUT = STATE_DIR / "risk-alerts.json"
MD_OUT = STATE_DIR / "risk-alerts-latest.md"

LOW_SCORE = 6.5
LOW_STREAK_DAYS = 3
VOLATILITY_THRESHOLD = 1.1
STRESS_TAGS = {
    "AI封号冲击",
    "网络排障",
    "生理期耗竭",
    "社交消耗",
    "上下文切换",
    "决策疲劳",
    "睡眠不足",
    "情绪劳动",
    "焦虑",
    "慌张",
}


@dataclass
class Entry:
    day: date
    score: float
    tags: list[str]


def parse_entry(raw: dict[str, Any]) -> Entry | None:
    try:
        day = datetime.strptime(str(raw["date"]), "%Y-%m-%d").date()
        score = float(raw["score"])
    except (KeyError, TypeError, ValueError):
        return None

    tags = raw.get("tags", [])
    safe_tags = [str(t).strip() for t in tags if str(t).strip()] if isinstance(tags, list) else []
    return Entry(day=day, score=score, tags=safe_tags)


def load_entries(path: Path) -> list[Entry]:
    if not path.exists():
        return []
    rows: list[Entry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        entry = parse_entry(raw)
        if entry:
            rows.append(entry)
    rows.sort(key=lambda x: x.day)
    return rows


def take_window(entries: list[Entry], days: int = 7) -> list[Entry]:
    if not entries:
        return []
    end = entries[-1].day
    start = end - timedelta(days=days - 1)
    return [e for e in entries if start <= e.day <= end]


def check_low_streak(entries: list[Entry]) -> int:
    streak = 0
    for e in reversed(entries):
        if e.score < LOW_SCORE:
            streak += 1
        else:
            break
    return streak


def check_stress_tag_count(entries: list[Entry]) -> int:
    count = 0
    for e in entries:
        if any(tag in STRESS_TAGS for tag in e.tags):
            count += 1
    return count


def build_payload(entries: list[Entry]) -> dict[str, Any]:
    today = entries[-1]
    scores = [e.score for e in entries]
    volatility = round(pstdev(scores), 2) if len(scores) > 1 else 0.0
    low_streak = check_low_streak(entries)
    stress_days = check_stress_tag_count(entries)
    first_half_avg = sum(scores[:3]) / len(scores[:3]) if len(scores) >= 3 else scores[0]
    last_half_avg = sum(scores[-3:]) / len(scores[-3:]) if len(scores) >= 3 else scores[-1]
    trend_down = (first_half_avg - last_half_avg) >= 0.8

    alerts: list[dict[str, Any]] = []
    if low_streak >= LOW_STREAK_DAYS:
        alerts.append(
            {
                "level": "high",
                "code": "LOW_STREAK",
                "message": f"连续 {low_streak} 天低于 {LOW_SCORE}",
            }
        )
    if volatility >= VOLATILITY_THRESHOLD:
        alerts.append(
            {
                "level": "medium",
                "code": "HIGH_VOLATILITY",
                "message": f"近7天波动较高（std={volatility}）",
            }
        )
    if stress_days >= 3:
        alerts.append(
            {
                "level": "medium",
                "code": "STRESS_TAG_CLUSTER",
                "message": f"近7天有 {stress_days} 天出现压力标签",
            }
        )
    if trend_down:
        alerts.append(
            {
                "level": "medium",
                "code": "DOWNWARD_TREND",
                "message": f"近3天均值 {last_half_avg:.1f}，较前段下降明显",
            }
        )

    status = "ok" if not alerts else "alert"
    return {
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "window_days": len(entries),
        "latest_date": str(today.day),
        "latest_score": today.score,
        "volatility_std": volatility,
        "low_streak": low_streak,
        "stress_tag_days": stress_days,
        "trend": {
            "first3_avg": round(first_half_avg, 2),
            "last3_avg": round(last_half_avg, 2),
        },
        "alerts": alerts,
        "suggestion": (
            "保持当前节奏，优先保护高分日动作。"
            if not alerts
            else "减少并发任务，优先睡眠与单焦点，连续2天恢复后再提速。"
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# LifeOS Risk Alerts (L3)",
        "",
        f"- status: `{payload['status']}`",
        f"- generated_at: `{payload['generated_at']}`",
        f"- latest_date: `{payload['latest_date']}`",
        f"- latest_score: `{payload['latest_score']}`",
        f"- volatility_std: `{payload['volatility_std']}`",
        f"- low_streak: `{payload['low_streak']}`",
        f"- stress_tag_days: `{payload['stress_tag_days']}`",
        f"- trend(first3 -> last3): `{payload['trend']['first3_avg']} -> {payload['trend']['last3_avg']}`",
        "",
        "## Alerts",
    ]
    if payload["alerts"]:
        for alert in payload["alerts"]:
            lines.append(f"- [{alert['level']}] {alert['code']}: {alert['message']}")
    else:
        lines.append("- No active alerts")

    lines.extend(["", "## Suggestion", f"- {payload['suggestion']}", ""])
    return "\n".join(lines)


def main() -> int:
    rows = load_entries(ENERGY_LOG)
    window = take_window(rows, days=7)
    if not window:
        print("No valid entries found in energy log.")
        return 1

    payload = build_payload(window)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    MD_OUT.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Risk alert status: {payload['status']}")
    print(f"JSON: {JSON_OUT}")
    print(f"Markdown: {MD_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
