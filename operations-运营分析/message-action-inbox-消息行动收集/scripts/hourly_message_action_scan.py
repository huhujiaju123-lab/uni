#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / "config.json"
STATE_DIR = ROOT / "state"
STATE_FILE = STATE_DIR / "state.json"
CANDIDATE_STATE_FILE = STATE_DIR / "candidates.json"
OUTPUT_DIR = ROOT / "outputs"
DIGEST_DIR = OUTPUT_DIR / "digests"
CANDIDATE_DIR = OUTPUT_DIR / "candidates"
CARD_DIR = OUTPUT_DIR / "cards"

NO_NOTICE_ENV = {
    "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
    "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
}

LARK_CLI_BIN = os.environ.get("LARK_CLI_BIN", "lark-cli")


ACTION_WORDS = [
    "看一下",
    "看看",
    "确认",
    "对下",
    "对齐",
    "安排",
    "跟进",
    "问下",
    "沟通",
    "需要",
    "计划",
    "时间",
    "排期",
    "修复",
]

SELF_COMMIT_WORDS = [
    "我去",
    "我来",
    "我看",
    "我问",
    "我确认",
    "我整理",
    "我跟",
    "明天",
    "周五",
    "和产品沟通",
    "得问下",
]

SCHEDULE_WORDS = [
    "明天",
    "今天",
    "周一",
    "周二",
    "周三",
    "周四",
    "周五",
    "周六",
    "周日",
    "上午",
    "下午",
    "晚上",
    "点",
    "会议",
    "日历",
    "时间方便",
]


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"processed_messages": {}, "last_runs": []}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def load_candidate_state() -> dict[str, Any]:
    if not CANDIDATE_STATE_FILE.exists():
        return {"candidates": {}}
    return json.loads(CANDIDATE_STATE_FILE.read_text(encoding="utf-8"))


def save_candidate_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CANDIDATE_STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CANDIDATE_STATE_FILE)


def run_lark(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        [LARK_CLI_BIN, *args],
        cwd=ROOT,
        env={**os.environ, **NO_NOTICE_ENV},
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stdout or "") + (proc.stderr or ""))
    return json.loads(proc.stdout)


def fetch_messages(chat_id: str, limit: int, page_size: int = 20) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    page_token = ""
    while len(messages) < limit:
        current_page_size = min(50, page_size, limit - len(messages))
        args = [
            "im",
            "+chat-messages-list",
            "--as",
            "user",
            "--chat-id",
            chat_id,
            "--page-size",
            str(current_page_size),
            "--order",
            "desc",
            "--format",
            "json",
        ]
        if page_token:
            args.extend(["--page-token", page_token])
        data = run_lark(args).get("data", {})
        messages.extend(data.get("messages") or [])
        page_token = data.get("page_token") or ""
        if not data.get("has_more") or not page_token:
            break
    return messages


def fetch_incremental_messages(
    chat_id: str,
    limit: int,
    page_size: int,
    probe_page_size: int,
    processed_messages: dict[str, Any],
) -> tuple[list[dict[str, Any]], int, bool]:
    messages: list[dict[str, Any]] = []
    page_token = ""
    api_pages = 0
    stopped_at_processed = False
    while len(messages) < limit:
        requested_page_size = probe_page_size if api_pages == 0 else page_size
        current_page_size = min(50, requested_page_size, limit - len(messages))
        args = [
            "im",
            "+chat-messages-list",
            "--as",
            "user",
            "--chat-id",
            chat_id,
            "--page-size",
            str(current_page_size),
            "--order",
            "desc",
            "--format",
            "json",
        ]
        if page_token:
            args.extend(["--page-token", page_token])
        data = run_lark(args).get("data", {})
        api_pages += 1
        page_messages = data.get("messages") or []
        for message in page_messages:
            message_id = message.get("message_id")
            if message_id in processed_messages:
                stopped_at_processed = True
                break
            messages.append(message)
            if len(messages) >= limit:
                break
        if stopped_at_processed or len(messages) >= limit:
            break
        page_token = data.get("page_token") or ""
        if not data.get("has_more") or not page_token or not page_messages:
            break
    messages.reverse()
    return messages, api_pages, stopped_at_processed


def text_of(message: dict[str, Any]) -> str:
    return re.sub(r"\s+", " ", (message.get("content") or "").strip())


def mentioned_owner(message: dict[str, Any], owner_open_id: str, owner_name: str) -> bool:
    for mention in message.get("mentions") or []:
        if mention.get("id") == owner_open_id or mention.get("name") == owner_name:
            return True
    return owner_name in text_of(message)


def sender_name(message: dict[str, Any]) -> str:
    sender = message.get("sender") or {}
    return sender.get("name") or sender.get("id") or ""


def sender_id(message: dict[str, Any]) -> str:
    return (message.get("sender") or {}).get("id") or ""


def stable_candidate_id(message: dict[str, Any], candidate_type: str) -> str:
    raw = "|".join(
        [
            str(message.get("message_id") or ""),
            str(message.get("message_position") or ""),
            candidate_type,
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def classify_message(message: dict[str, Any], owner_open_id: str, owner_name: str) -> list[dict[str, Any]]:
    content = text_of(message)
    if not content or message.get("deleted"):
        return []
    if " invited " in content and " to the chat" in content:
        return []

    candidates: list[dict[str, Any]] = []
    is_owner_sender = sender_id(message) == owner_open_id
    is_mentioned = mentioned_owner(message, owner_open_id, owner_name)
    has_action_word = any(word in content for word in ACTION_WORDS)
    has_self_commit = is_owner_sender and any(word in content for word in SELF_COMMIT_WORDS)
    has_schedule = any(word in content for word in SCHEDULE_WORDS) and any(
        word in content for word in ["对下", "对齐", "会议", "时间方便", "沟通"]
    )

    if is_mentioned and has_action_word:
        candidates.append(
            {
                "type": "todo_candidate",
                "confidence": "high",
                "reason": "消息明确提到你，并包含动作词",
            }
        )
    elif is_mentioned:
        candidates.append(
            {
                "type": "todo_candidate",
                "confidence": "medium",
                "reason": "消息明确提到你",
            }
        )

    if has_self_commit:
        candidates.append(
            {
                "type": "follow_up_candidate",
                "confidence": "high",
                "reason": "你自己在群里承诺了后续动作",
            }
        )

    if is_owner_sender and "？" in content:
        candidates.append(
            {
                "type": "open_question",
                "confidence": "medium",
                "reason": "你提出了问题，需要确认是否已有回复闭环",
            }
        )

    if has_schedule:
        candidates.append(
            {
                "type": "calendar_candidate",
                "confidence": "medium",
                "reason": "消息包含时间安排或对齐/会议语义",
            }
        )

    for candidate in candidates:
        candidate["candidate_id"] = stable_candidate_id(message, candidate["type"])
        candidate.update(
            {
                "message_id": message.get("message_id"),
                "message_position": message.get("message_position"),
                "message_time": message.get("create_time"),
                "sender": sender_name(message),
                "content": content[:800],
                "message_link": message.get("message_app_link"),
            }
        )
    return candidates


def append_candidate_registry(run_id: str, candidates: list[dict[str, Any]]) -> None:
    state = load_candidate_state()
    registry = state.setdefault("candidates", {})
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        existing = registry.get(candidate_id, {})
        registry[candidate_id] = {
            **existing,
            **candidate,
            "first_seen_at": existing.get("first_seen_at") or run_id,
            "last_seen_at": run_id,
            "status": existing.get("status") or "pending",
            "decision": existing.get("decision"),
            "comment": existing.get("comment") or "",
        }
    save_candidate_state(state)


def card_action_value(candidate: dict[str, Any], action: str) -> dict[str, str]:
    return {
        "source": "message-action-inbox",
        "candidate_id": candidate["candidate_id"],
        "action": action,
    }


def button(text: str, action: str, candidate: dict[str, Any], style: str = "default") -> dict[str, Any]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": text},
        "type": style,
        "value": card_action_value(candidate, action),
    }


def build_candidate_card(run_id: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    shown = candidates[:10]
    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"本次扫描发现 **{len(candidates)}** 个候选事项，展示前 **{len(shown)}** 个。点击“建 Todo / 建日程”会执行对应飞书动作；“忽略 / 稍后”只记录决策。",
            },
        }
    ]
    if not shown:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "本次没有发现新的候选事项。"}})
    for idx, candidate in enumerate(shown, start=1):
        content = candidate["content"]
        if len(content) > 140:
            content = content[:137] + "..."
        elements.extend(
            [
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**{idx}. [{candidate['chat_name']}] {candidate['type']}｜{candidate['confidence']}**\n"
                            f"{candidate['sender']}｜{candidate['message_time']}\n"
                            f"原因：{candidate['reason']}\n"
                            f"内容：{content}"
                        ),
                    },
                },
                {
                    "tag": "action",
                    "actions": [
                        button("建 Todo", "create_todo", candidate, "primary"),
                        button("忽略", "ignore", candidate),
                        button("稍后", "snooze", candidate),
                        button("建日程", "create_calendar", candidate),
                    ],
                },
            ]
        )
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "消息行动候选"},
        },
        "elements": elements,
    }


def send_card_to_owner(owner_open_id: str, card: dict[str, Any], run_id: str) -> dict[str, Any]:
    return run_lark(
        [
            "im",
            "+messages-send",
            "--as",
            "bot",
            "--user-id",
            owner_open_id,
            "--msg-type",
            "interactive",
            "--content",
            json.dumps(card, ensure_ascii=False),
            "--idempotency-key",
            f"mai-card-{hashlib.sha1(run_id.encode('utf-8')).hexdigest()[:20]}",
            "--format",
            "json",
        ]
    )


def build_digest(run_id: str, candidates: list[dict[str, Any]], scanned: list[dict[str, Any]]) -> str:
    lines = [
        f"# 消息行动扫描｜{run_id}",
        "",
        "## 扫描范围",
        "",
        "| 群 | 新读消息数 | API 页数 | 遇到已处理消息 | 候选事项数 |",
        "|---|---:|---:|---|---:|",
    ]
    by_chat: dict[str, dict[str, int]] = {}
    for item in scanned:
        by_chat.setdefault(item["chat_name"], {"messages": 0, "api_pages": 0, "stopped": 0, "candidates": 0})
        by_chat[item["chat_name"]]["messages"] += item["message_count"]
        by_chat[item["chat_name"]]["api_pages"] += item["api_pages"]
        by_chat[item["chat_name"]]["stopped"] = 1 if item["stopped_at_processed"] else by_chat[item["chat_name"]]["stopped"]
    for candidate in candidates:
        by_chat.setdefault(candidate["chat_name"], {"messages": 0, "api_pages": 0, "stopped": 0, "candidates": 0})
        by_chat[candidate["chat_name"]]["candidates"] += 1
    for chat_name, stat in by_chat.items():
        stopped = "是" if stat["stopped"] else "否"
        lines.append(f"| {chat_name} | {stat['messages']} | {stat['api_pages']} | {stopped} | {stat['candidates']} |")

    lines.extend(["", "## 高优先级", ""])
    high = [c for c in candidates if c["confidence"] == "high"]
    if high:
        for idx, item in enumerate(high, start=1):
            lines.append(f"{idx}. **[{item['chat_name']}] {item['type']}**｜{item['message_time']}｜{item['sender']}")
            lines.append(f"   - 原因：{item['reason']}")
            lines.append(f"   - 内容：{item['content']}")
            lines.append(f"   - 链接：{item['message_link']}")
    else:
        lines.append("无。")

    lines.extend(["", "## 其他候选", ""])
    others = [c for c in candidates if c["confidence"] != "high"]
    if others:
        for idx, item in enumerate(others, start=1):
            lines.append(f"{idx}. **[{item['chat_name']}] {item['type']}**｜{item['message_time']}｜{item['sender']}")
            lines.append(f"   - 原因：{item['reason']}")
            lines.append(f"   - 内容：{item['content']}")
            lines.append(f"   - 链接：{item['message_link']}")
    else:
        lines.append("无。")

    return "\n".join(lines) + "\n"


def scan(args: argparse.Namespace) -> int:
    config = load_config()
    state = load_state()
    owner = config["owner"]
    limit = args.limit or config.get("scan", {}).get("limit_per_chat", 100)
    page_size = args.page_size or config.get("scan", {}).get("page_size", 20)
    probe_page_size = config.get("scan", {}).get("probe_page_size", 1)
    run_id = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")

    all_candidates: list[dict[str, Any]] = []
    scanned: list[dict[str, Any]] = []

    for chat in config["chats"]:
        if args.include_processed:
            messages = fetch_messages(chat["chat_id"], limit, page_size=page_size)
            api_pages = (len(messages) + page_size - 1) // page_size if messages else 0
            stopped_at_processed = False
        else:
            messages, api_pages, stopped_at_processed = fetch_incremental_messages(
                chat["chat_id"],
                limit,
                page_size,
                probe_page_size,
                state.get("processed_messages", {}),
            )
        scanned.append(
            {
                "chat_name": chat["name"],
                "message_count": len(messages),
                "api_pages": api_pages,
                "stopped_at_processed": stopped_at_processed,
            }
        )
        for message in messages:
            candidates = classify_message(message, owner["open_id"], owner["name"])
            for candidate in candidates:
                candidate["chat_name"] = chat["name"]
                candidate["chat_id"] = chat["chat_id"]
                all_candidates.append(candidate)
            state.setdefault("processed_messages", {})[message.get("message_id")] = {
                "chat_name": chat["name"],
                "message_position": message.get("message_position"),
                "seen_at": run_id,
            }

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    digest = build_digest(run_id, all_candidates, scanned)
    digest_path = DIGEST_DIR / f"{run_id}.md"
    candidate_path = CANDIDATE_DIR / f"{run_id}.json"
    digest_path.write_text(digest, encoding="utf-8")
    candidate_path.write_text(json.dumps(all_candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    append_candidate_registry(run_id, all_candidates)
    card = build_candidate_card(run_id, all_candidates)
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    card_path = CARD_DIR / f"{run_id}.json"
    card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")

    state.setdefault("last_runs", []).append(
        {
            "run_id": run_id,
            "candidate_count": len(all_candidates),
            "digest_path": str(digest_path.relative_to(ROOT)),
            "candidate_path": str(candidate_path.relative_to(ROOT)),
            "card_path": str(card_path.relative_to(ROOT)),
        }
    )
    state["last_runs"] = state["last_runs"][-50:]
    save_state(state)

    print(f"scanned_chats={len(config['chats'])}")
    print(f"new_messages={sum(item['message_count'] for item in scanned)}")
    print(f"api_pages={sum(item['api_pages'] for item in scanned)}")
    print(f"candidates={len(all_candidates)}")
    print(f"digest={digest_path.relative_to(ROOT)}")
    print(f"candidates_json={candidate_path.relative_to(ROOT)}")
    print(f"card_json={card_path.relative_to(ROOT)}")
    if args.send_card:
        sent = send_card_to_owner(owner["open_id"], card, run_id)
        message_id = (sent.get("data") or {}).get("message_id") or ""
        print(f"send_card=sent message_id={message_id}")
    if args.send_digest:
        print("send_digest=skipped_observation_mode")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan configured Feishu chats and collect action candidates.")
    parser.add_argument("--limit", type=int, help="每个群读取最近 N 条消息，默认读取 config.json")
    parser.add_argument("--page-size", type=int, help="每次 API 读取的消息页大小，默认读取 config.json")
    parser.add_argument("--include-processed", action="store_true", help="忽略状态去重，重新分析已处理消息")
    parser.add_argument("--send-digest", action="store_true", help="预留参数；当前观察模式不发送飞书消息")
    parser.add_argument("--send-card", action="store_true", help="发送飞书交互卡片给 owner；这是外部可见写操作")
    return parser


def main() -> int:
    return scan(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
