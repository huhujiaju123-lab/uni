#!/usr/bin/env python3
"""L2: Generate LifeOS weekly review markdown from energy-log.jsonl."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ENERGY_LOG = Path.home() / ".claude/life-os/state/energy-log.jsonl"
WEEKLY_DIR = Path.home() / ".claude/life-os/weekly"


@dataclass
class EnergyEntry:
    day: date
    score: float
    tags: list[str]
    note: str
    timestamp: str


def parse_entry(raw: dict[str, Any]) -> EnergyEntry | None:
    try:
        day = datetime.strptime(str(raw["date"]), "%Y-%m-%d").date()
        score = float(raw["score"])
    except (KeyError, ValueError, TypeError):
        return None

    tags_raw = raw.get("tags", [])
    tags = [str(t).strip() for t in tags_raw if str(t).strip()] if isinstance(tags_raw, list) else []
    note = str(raw.get("note", "")).strip()
    ts = str(raw.get("timestamp", "")).strip()
    return EnergyEntry(day=day, score=score, tags=tags, note=note, timestamp=ts)


def read_entries(path: Path) -> list[EnergyEntry]:
    if not path.exists():
        return []
    entries: list[EnergyEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        parsed = parse_entry(raw)
        if parsed:
            entries.append(parsed)
    entries.sort(key=lambda x: x.day)
    return entries


def iso_week_label(d: date) -> str:
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def pick_window(entries: list[EnergyEntry], days: int) -> list[EnergyEntry]:
    if not entries:
        return []
    end = entries[-1].day
    start = end - timedelta(days=days - 1)
    return [e for e in entries if start <= e.day <= end]


def top_tags(entries: list[EnergyEntry], *, high: bool) -> list[tuple[str, int]]:
    c: Counter[str] = Counter()
    for e in entries:
        if high and e.score >= 8:
            c.update(e.tags)
        if (not high) and e.score < 7:
            c.update(e.tags)
    return c.most_common(5)


def format_review(entries: list[EnergyEntry]) -> str:
    start = entries[0].day
    end = entries[-1].day
    avg = sum(e.score for e in entries) / len(entries)
    hi = max(entries, key=lambda x: x.score)
    lo = min(entries, key=lambda x: x.score)
    high_days = [e for e in entries if e.score >= 8]
    low_days = [e for e in entries if e.score < 7]

    high_tags = top_tags(entries, high=True)
    low_tags = top_tags(entries, high=False)

    lines = [
        f"# LifeOS Weekly Review | {start} -> {end}",
        "",
        f"- Week: `{iso_week_label(end)}`",
        f"- Entries: `{len(entries)}`",
        f"- Avg Score: `{avg:.1f}`",
        f"- Highest: `{hi.day} / {hi.score}`",
        f"- Lowest: `{lo.day} / {lo.score}`",
        "",
        "## Trend",
        f"- Start -> End: `{entries[0].score} -> {entries[-1].score}`",
        f"- 8+ days: `{len(high_days)}`",
        f"- <7 days: `{len(low_days)}`",
        "",
        "## Energy Boosters (from 8+ days)",
    ]

    if high_tags:
        for tag, count in high_tags:
            lines.append(f"- {tag}: {count}")
    else:
        lines.append("- No 8+ day tags yet")

    lines.extend(["", "## Energy Drainers (from <7 days)"])
    if low_tags:
        for tag, count in low_tags:
            lines.append(f"- {tag}: {count}")
    else:
        lines.append("- No <7 day tags")

    lines.extend(["", "## Daily Snapshot"])
    for e in entries:
        note = e.note if e.note else "-"
        tags = " / ".join(e.tags) if e.tags else "-"
        lines.append(f"- {e.day} | {e.score} | {tags} | {note}")

    lines.extend(
        [
            "",
            "## One Question",
            "这周你最该保护的能量来源是什么？下周如何确保它至少出现 2 次？",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate LifeOS weekly review markdown.")
    parser.add_argument("--days", type=int, default=7, help="Window size ending at latest logged day.")
    parser.add_argument("--output", type=str, default="", help="Custom output markdown path.")
    args = parser.parse_args()

    entries = read_entries(ENERGY_LOG)
    window = pick_window(entries, args.days)
    if not window:
        print("No valid entries found in energy log.")
        return 1

    content = format_review(window)
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    default_name = f"{iso_week_label(window[-1].day)}-auto-review.md"
    out = Path(args.output).expanduser() if args.output else WEEKLY_DIR / default_name
    out.write_text(content, encoding="utf-8")
    print(f"Weekly review generated: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
