#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / "config.json"
STATE_DIR = ROOT / "state"
CANDIDATE_STATE_FILE = STATE_DIR / "candidates.json"
DECISION_FILE = STATE_DIR / "decisions.json"

NO_NOTICE_ENV = {
    "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
    "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
    "HTTPS_PROXY": "",
    "HTTP_PROXY": "",
    "ALL_PROXY": "",
    "https_proxy": "",
    "http_proxy": "",
    "all_proxy": "",
}

LARK_CLI_BIN = os.environ.get("LARK_CLI_BIN", "lark-cli")

ACTION_TO_STATUS = {
    "create_todo": "todo_requested",
    "ignore": "ignored",
    "snooze": "snoozed",
    "create_calendar": "calendar_requested",
}

ACTION_LABEL = {
    "create_todo": "建 Todo",
    "ignore": "忽略",
    "snooze": "稍后",
    "create_calendar": "建日程",
}

FEEDBACK_MARKER = "<message-action-inbox-feedback>"
CARD_ACTIONS = [
    ("建 Todo", "create_todo", "primary"),
    ("忽略", "ignore", "default"),
    ("稍后", "snooze", "default"),
    ("建日程", "create_calendar", "default"),
]


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_config() -> dict[str, Any]:
    return load_json(CONFIG_FILE, {})


def save_json(path: Path, payload: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def parse_json_maybe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def normalize_event(raw: dict[str, Any]) -> dict[str, Any] | None:
    action_value = parse_json_maybe(raw.get("action_value"))
    form_value = parse_json_maybe(raw.get("form_value"))
    if not isinstance(action_value, dict):
        return None
    if action_value.get("source") != "message-action-inbox":
        return None
    candidate_id = action_value.get("candidate_id")
    action = action_value.get("action")
    if not candidate_id or action not in ACTION_TO_STATUS:
        return None
    comment = ""
    if isinstance(form_value, dict):
        comment = str(form_value.get("comment") or "")
    return {
        "event_id": raw.get("event_id"),
        "candidate_id": candidate_id,
        "action": action,
        "status": ACTION_TO_STATUS[action],
        "comment": comment,
        "operator_id": raw.get("operator_id"),
        "message_id": raw.get("message_id"),
        "chat_id": raw.get("chat_id"),
        "received_at": dt.datetime.now().isoformat(timespec="seconds"),
    }


def apply_decision(decision: dict[str, Any]) -> None:
    decision_state = load_json(DECISION_FILE, {"decisions": {}})
    event_id = decision.get("event_id") or f"manual-{decision['candidate_id']}-{decision['received_at']}"
    if event_id in decision_state.setdefault("decisions", {}):
        return
    decision_state["decisions"][event_id] = decision
    save_json(DECISION_FILE, decision_state)

    candidate_state = load_json(CANDIDATE_STATE_FILE, {"candidates": {}})
    candidate = candidate_state.setdefault("candidates", {}).get(decision["candidate_id"])
    if candidate:
        candidate["status"] = decision["status"]
        candidate["decision"] = decision["action"]
        if decision.get("comment"):
            candidate["comment"] = decision["comment"]
        candidate["decided_at"] = decision["received_at"]
        candidate["decided_by"] = decision.get("operator_id")
        save_json(CANDIDATE_STATE_FILE, candidate_state)


def candidate_summary(candidate_id: str) -> str:
    candidate_state = load_json(CANDIDATE_STATE_FILE, {"candidates": {}})
    candidate = candidate_state.get("candidates", {}).get(candidate_id) or {}
    content = str(candidate.get("content") or candidate_id)
    return content[:48] + ("..." if len(content) > 48 else "")


def get_candidate(candidate_id: str) -> dict[str, Any]:
    return load_candidates().get(candidate_id) or {}


def update_candidate(candidate_id: str, updates: dict[str, Any]) -> None:
    state = load_json(CANDIDATE_STATE_FILE, {"candidates": {}})
    candidate = state.setdefault("candidates", {}).setdefault(candidate_id, {})
    candidate.update(updates)
    save_json(CANDIDATE_STATE_FILE, state)


def load_candidates() -> dict[str, dict[str, Any]]:
    candidate_state = load_json(CANDIDATE_STATE_FILE, {"candidates": {}})
    return candidate_state.get("candidates", {})


def action_value(candidate_id: str, action: str) -> dict[str, str]:
    return {
        "source": "message-action-inbox",
        "candidate_id": candidate_id,
        "action": action,
    }


def candidate_pool_for_anchor(candidates: dict[str, dict[str, Any]], anchor_candidate_id: str) -> dict[str, dict[str, Any]]:
    anchor = candidates.get(anchor_candidate_id) or {}
    batch = anchor.get("last_seen_at") or anchor.get("first_seen_at")
    if not batch:
        return candidates
    pool = {
        candidate_id: candidate
        for candidate_id, candidate in candidates.items()
        if candidate.get("last_seen_at") == batch or candidate.get("first_seen_at") == batch
    }
    return pool or candidates


def find_candidate_for_text(text: str, candidates: dict[str, dict[str, Any]], used_ids: set[str]) -> str:
    best_id = ""
    best_score = 0
    for candidate_id, candidate in candidates.items():
        if candidate_id in used_ids:
            continue
        score = 0
        for field in ("content", "sender", "reason", "type", "confidence"):
            value = str(candidate.get(field) or "")
            if value and value[:80] in text:
                score += 1
        if score > best_score:
            best_score = score
            best_id = candidate_id
    return best_id


def restore_button_values(card: dict[str, Any], anchor_candidate_id: str) -> None:
    candidates = load_candidates()
    candidates = candidate_pool_for_anchor(candidates, anchor_candidate_id)
    current_candidate_id = ""
    used_ids: set[str] = set()
    for element in card.get("elements") or []:
        if not isinstance(element, dict):
            continue
        if element.get("tag") == "div":
            text = element.get("text") or {}
            content = text.get("content", "") if isinstance(text, dict) else ""
            if isinstance(content, str):
                matched_id = find_candidate_for_text(content, candidates, used_ids)
                if matched_id:
                    current_candidate_id = matched_id
                    used_ids.add(matched_id)
        if element.get("tag") != "action" or not current_candidate_id:
            continue
        actions = element.get("actions") or []
        for idx, action_element in enumerate(actions):
            if not isinstance(action_element, dict) or idx >= len(CARD_ACTIONS):
                continue
            label, action, style = CARD_ACTIONS[idx]
            action_element["value"] = action_value(current_candidate_id, action)
            action_element["type"] = action_element.get("type") or style
            action_element["text"] = action_element.get("text") or {"tag": "plain_text", "content": label}


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


def extract_task_id(response: dict[str, Any]) -> str:
    data = response.get("data") or {}
    task = data.get("task") if isinstance(data, dict) else {}
    if isinstance(task, dict):
        return task.get("guid") or task.get("id") or task.get("task_id") or ""
    return data.get("guid") or data.get("id") or data.get("task_id") or ""


def create_feishu_todo(decision: dict[str, Any]) -> dict[str, str]:
    candidate = get_candidate(decision["candidate_id"])
    existing_task_id = candidate.get("todo_task_id")
    if existing_task_id:
        return {"status": "exists", "message": f"飞书 Todo 已存在：{existing_task_id}", "id": existing_task_id}

    owner = load_config().get("owner") or {}
    owner_open_id = owner.get("open_id") or decision.get("operator_id") or ""
    content = str(candidate.get("content") or decision["candidate_id"])
    summary = "消息待办：" + (content[:40] + ("..." if len(content) > 40 else ""))
    description = "\n".join(
        [
            "来源：消息行动候选",
            f"发送人：{candidate.get('sender') or ''}",
            f"群/会话：{candidate.get('chat_name') or ''}",
            f"原因：{candidate.get('reason') or ''}",
            "",
            "原消息：",
            content,
            "",
            f"候选ID：{decision['candidate_id']}",
            f"记录时间：{decision['received_at']}",
        ]
    )
    idempotency = "mai-todo-" + hashlib.sha1(decision["candidate_id"].encode("utf-8")).hexdigest()[:20]
    args = [
        "task",
        "+create",
        "--as",
        "user",
        "--summary",
        summary,
        "--description",
        description,
        "--idempotency-key",
        idempotency,
        "--format",
        "json",
    ]
    if owner_open_id:
        args.extend(["--assignee", owner_open_id])
    response = run_lark(args)
    task_id = extract_task_id(response)
    update_candidate(
        decision["candidate_id"],
        {
            "todo_task_id": task_id,
            "todo_created_at": decision["received_at"],
            "todo_create_response": response.get("data") or response,
        },
    )
    return {"status": "created", "message": "飞书 Todo 已创建", "id": task_id}


def parse_calendar_time(content: str) -> tuple[str, str] | None:
    import re

    match = re.search(r"(?:(今天|明天)\s*)?(\d{1,2})[:：](\d{2})", content)
    if not match:
        return None
    day_word, hour_text, minute_text = match.groups()
    base = dt.datetime.now().astimezone()
    if day_word == "明天":
        base = base + dt.timedelta(days=1)
    start = base.replace(hour=int(hour_text), minute=int(minute_text), second=0, microsecond=0)
    end = start + dt.timedelta(minutes=30)
    return start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


def create_calendar_event(decision: dict[str, Any]) -> dict[str, str]:
    candidate = get_candidate(decision["candidate_id"])
    existing_event_id = candidate.get("calendar_event_id")
    if existing_event_id:
        return {"status": "exists", "message": f"飞书日程已存在：{existing_event_id}", "id": existing_event_id}

    content = str(candidate.get("content") or "")
    parsed = parse_calendar_time(content)
    if not parsed:
        return {"status": "skipped", "message": "已记录建日程请求；原消息缺少可解析的明确时间，未自动创建日程", "id": ""}
    start, end = parsed
    summary = "消息日程：" + (content[:32] + ("..." if len(content) > 32 else ""))
    description = "\n".join(
        [
            "来源：消息行动候选",
            f"发送人：{candidate.get('sender') or ''}",
            f"原因：{candidate.get('reason') or ''}",
            "",
            "原消息：",
            content,
            "",
            f"候选ID：{decision['candidate_id']}",
        ]
    )
    response = run_lark(
        [
            "calendar",
            "+create",
            "--as",
            "user",
            "--summary",
            summary,
            "--description",
            description,
            "--start",
            start,
            "--end",
            end,
            "--format",
            "json",
        ]
    )
    data = response.get("data") or {}
    event_id = data.get("event_id") or data.get("id") or data.get("calendar_event_id") or ""
    update_candidate(
        decision["candidate_id"],
        {
            "calendar_event_id": event_id,
            "calendar_created_at": decision["received_at"],
            "calendar_create_response": data or response,
        },
    )
    return {"status": "created", "message": "飞书日程已创建", "id": event_id}


def perform_action(decision: dict[str, Any]) -> dict[str, str]:
    if decision["action"] == "create_todo":
        return create_feishu_todo(decision)
    if decision["action"] == "create_calendar":
        return create_calendar_event(decision)
    if decision["action"] == "snooze":
        return {"status": "recorded", "message": "已记录为稍后处理", "id": ""}
    if decision["action"] == "ignore":
        return {"status": "recorded", "message": "已记录为忽略", "id": ""}
    return {"status": "recorded", "message": "已记录", "id": ""}


def send_feedback_message(raw: dict[str, Any], decision: dict[str, Any], outcome: dict[str, str]) -> None:
    chat_id = raw.get("chat_id")
    if not chat_id:
        return
    action_label = ACTION_LABEL.get(decision["action"], decision["action"])
    candidate = get_candidate(decision["candidate_id"])
    content = str(candidate.get("content") or decision["candidate_id"])
    lines = [
        f"✅ **已处理：{action_label}**",
        "",
        f"**结果：** {outcome.get('message') or '已记录'}",
    ]
    if outcome.get("id"):
        lines.append(f"**ID：** `{outcome['id']}`")
    lines.extend(
        [
            "",
            f"**事项：** {content[:160]}",
            f"**时间：** {decision['received_at']}",
        ]
    )
    run_lark(
        [
            "im",
            "+messages-send",
            "--as",
            "bot",
            "--chat-id",
            chat_id,
            "--markdown",
            "\n".join(lines),
            "--idempotency-key",
            "mai-feedback-" + hashlib.sha1(str(decision.get("event_id") or decision["candidate_id"]).encode("utf-8")).hexdigest()[:20],
            "--format",
            "json",
        ]
    )


def update_card_feedback(raw: dict[str, Any], decision: dict[str, Any]) -> None:
    token = raw.get("token")
    operator_id = raw.get("operator_id")
    card = parse_json_maybe(raw.get("card_content"))
    if not token or not operator_id or not isinstance(card, dict):
        return

    action_label = ACTION_LABEL.get(decision["action"], decision["action"])
    item_summary = candidate_summary(decision["candidate_id"])
    feedback = {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                f"{FEEDBACK_MARKER}\n"
                f"✅ **已记录：{action_label}**\n"
                f"事项：{item_summary}\n"
                f"时间：{decision['received_at']}"
            ),
        },
    }
    divider = {"tag": "hr"}
    elements = card.get("elements") or []
    cleaned: list[dict[str, Any]] = []
    skip_next_hr = False
    for element in elements:
        text = element.get("text", {}) if isinstance(element, dict) else {}
        content = text.get("content", "") if isinstance(text, dict) else ""
        if isinstance(content, str) and FEEDBACK_MARKER in content:
            skip_next_hr = True
            continue
        if skip_next_hr and isinstance(element, dict) and element.get("tag") == "hr":
            skip_next_hr = False
            continue
        skip_next_hr = False
        cleaned.append(element)
    card["elements"] = cleaned
    restore_button_values(card, decision["candidate_id"])
    card["elements"] = [feedback, divider, *cleaned]
    card["open_ids"] = [operator_id]

    run_lark(
        [
            "api",
            "POST",
            "/open-apis/interactive/v1/card/update",
            "--as",
            "bot",
            "--data",
            json.dumps({"token": token, "card": card}, ensure_ascii=False),
        ]
    )


def iter_stdin_events() -> Iterable[dict[str, Any]]:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def iter_lark_events(timeout: str | None) -> Iterable[dict[str, Any]]:
    args = [LARK_CLI_BIN, "event", "consume", "card.action.trigger", "--as", "bot", "--quiet"]
    args.extend(["--timeout", timeout or "55m"])
    proc = subprocess.Popen(
        args,
        cwd=ROOT,
        env={**os.environ, **NO_NOTICE_ENV},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    stderr_text = ""
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
    finally:
        if proc.stderr is not None:
            stderr_text = proc.stderr.read()
        proc.terminate()
        return_code = proc.wait(timeout=5)
        if "context canceled" not in stderr_text and return_code not in (0, -15):
            raise RuntimeError(stderr_text or f"lark-cli event consume exited with code {return_code}")


def run(args: argparse.Namespace) -> int:
    handled = 0
    while True:
        source = iter_stdin_events() if args.stdin else iter_lark_events(args.timeout)
        for raw in source:
            decision = normalize_event(raw)
            if not decision:
                continue
            apply_decision(decision)
            action_error = ""
            feedback_error = ""
            outcome = {"status": "recorded", "message": "已记录", "id": ""}
            try:
                outcome = perform_action(decision)
            except Exception as exc:  # Keep local decision durable even if card update token expires.
                action_error = str(exc)
                outcome = {"status": "failed", "message": f"动作执行失败：{action_error}", "id": ""}
            try:
                send_feedback_message(raw, decision, outcome)
            except Exception as exc:
                feedback_error = str(exc)
            handled += 1
            print(
                json.dumps(
                    {
                        "handled": True,
                        "candidate_id": decision["candidate_id"],
                        "action": decision["action"],
                        "status": decision["status"],
                        "outcome": outcome,
                        "action_error": action_error,
                        "feedback_sent": not bool(feedback_error),
                        "feedback_error": feedback_error,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            if args.max_events and handled >= args.max_events:
                return 0
        if args.stdin:
            return 0
        time.sleep(2)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Listen to Feishu interactive card actions and record candidate decisions.")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读取 ndjson 事件，便于本地测试")
    parser.add_argument("--timeout", help="传给 lark-cli event consume 的超时时间，例如 60s")
    parser.add_argument("--max-events", type=int, help="处理 N 个事件后退出")
    return parser


def main() -> int:
    return run(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
