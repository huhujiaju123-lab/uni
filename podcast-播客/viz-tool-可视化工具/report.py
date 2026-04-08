#!/usr/bin/env python3
"""
播客可视化日报 — 读取 JSONL 事件日志生成每日摘要

用法：
    python3 report.py              # 今天
    python3 report.py 2026-03-02   # 指定日期
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"


def load_events(date_str):
    log_file = LOG_DIR / f"{date_str}.jsonl"
    if not log_file.exists():
        return []
    events = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def generate_report(date_str):
    events = load_events(date_str)
    if not events:
        print(f"📊 播客可视化日报 {date_str}")
        print("━" * 36)
        print("  暂无数据")
        return

    # ── 访问量 ──
    page_views = [e for e in events if e["event"] == "page_view"]
    pv_by_path = Counter()
    uv_set = set()
    for pv in page_views:
        path = pv.get("path", "")
        if path == "/":
            pv_by_path["首页"] += 1
        elif path == "/progress":
            pv_by_path["进度页"] += 1
        elif path == "/view":
            pv_by_path["查看页"] += 1
        uid = pv.get("uid", "")
        if uid:
            uv_set.add(uid)

    # ── 生成任务 ──
    task_created = [e for e in events if e["event"] == "task_created"]
    cached_count = sum(1 for t in task_created if t.get("cached"))
    new_count = len(task_created) - cached_count

    task_done = [e for e in events if e["event"] == "task_done"]
    task_error = [e for e in events if e["event"] == "task_error"]

    total_secs = [t.get("total_sec", 0) for t in task_done if t.get("total_sec")]
    avg_sec = sum(total_secs) / len(total_secs) if total_secs else 0

    # ── 今日生成内容 ──
    episodes = []
    for td in task_done:
        eid = td.get("episode_id", "")
        total = td.get("total_sec", 0)
        title = td.get("title", eid)
        episodes.append((title, total))

    # ── 步骤耗时统计 ──
    step_durations = defaultdict(list)
    for e in events:
        if e["event"] == "step_done":
            step_durations[e.get("step_name", "")].append(e.get("duration_sec", 0))

    # ── 异常 ──
    rate_limited = [e for e in events if e["event"] == "rate_limited"]

    # ── 输出 ──
    print(f"📊 播客可视化日报 {date_str}")
    print("━" * 36)

    print(f"\n📈 访问量")
    print(f"  首页 PV: {pv_by_path.get('首页', 0)}    进度页 PV: {pv_by_path.get('进度页', 0)}    查看页 PV: {pv_by_path.get('查看页', 0)}")
    print(f"  独立用户(UV): {len(uv_set)}")

    print(f"\n🎙️ 生成任务")
    print(f"  提交: {len(task_created)}    缓存命中: {cached_count}    新生成: {new_count}    失败: {len(task_error)}")
    if avg_sec:
        print(f"  平均耗时: {fmt_duration(avg_sec)}")

    if episodes:
        print(f"\n📋 今日生成内容")
        for i, (title, sec) in enumerate(episodes, 1):
            print(f"  {i}. {title} — 耗时 {fmt_duration(sec)} ✅")

    if step_durations:
        print(f"\n⏱️ 步骤平均耗时")
        for name in ["获取元数据", "音频转录", "AI 内容分析", "生成可视化"]:
            durations = step_durations.get(name, [])
            if durations:
                avg = sum(durations) / len(durations)
                print(f"  {name}: {fmt_duration(avg)}")

    print(f"\n⚠️ 异常")
    print(f"  限流触发: {len(rate_limited)} 次")
    print(f"  Pipeline 错误: {len(task_error)} 次")
    if task_error:
        for err in task_error:
            print(f"    - [{err.get('ts', '')}] step={err.get('step', '?')} {err.get('error_msg', '')[:80]}")


def fmt_duration(sec):
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    m, s = divmod(sec, 60)
    return f"{m}m {s:02d}s"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    generate_report(date_str)
