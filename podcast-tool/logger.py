"""
轻量事件日志 — 每天一个 JSONL 文件
日志存储在 logs/ 目录下，文件名格式 YYYY-MM-DD.jsonl
"""

import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def log_event(event_type, **kwargs):
    """追加一条事件到当天的 JSONL 文件"""
    now = datetime.now()
    entry = {
        "ts": now.isoformat(timespec="seconds"),
        "event": event_type,
        **kwargs,
    }
    log_file = LOG_DIR / f"{now.strftime('%Y-%m-%d')}.jsonl"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 日志不能影响主流程
