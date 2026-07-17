#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_DIR = ROOT / "contexts"
RAW_DIR = ROOT / "raw"
BRIDGE_OUTBOX_DIR = ROOT / "bridge-outbox"
TASK_PROMPT_DIR = ROOT / "task-prompts"
TASK_OUTBOX_DIR = ROOT / "task-outbox"
FEISHU_PUSH_OUTBOX_DIR = ROOT / "feishu-push-outbox"
PENDING_FILE = ROOT / "pending-missing-minutes.md"
DEFAULT_FEISHU_BASE_URL = "https://ucnanv7ihnmu.feishu.cn"

NO_NOTICE_ENV = {
    "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
    "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
}


def run_lark(args: list[str], check: bool = False) -> tuple[int, dict[str, Any] | None, str]:
    env = os.environ.copy()
    env.update(NO_NOTICE_ENV)
    proc = subprocess.run(
        ["lark-cli", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    parsed = parse_json_from_output(out)
    if check and proc.returncode != 0:
        raise RuntimeError(out.strip())
    return proc.returncode, parsed, out


def parse_json_from_output(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def current_user_open_id() -> str:
    code, data, raw = run_lark(["auth", "status", "--json", "--verify"])
    if code != 0 or not data:
        raise RuntimeError(f"无法读取飞书登录态：\n{raw}")
    user = data.get("identities", {}).get("user", {})
    open_id = user.get("openId")
    if not open_id:
        raise RuntimeError(f"未找到当前用户 open_id：\n{raw}")
    return open_id


def agenda(start: str, end: str) -> list[dict[str, Any]]:
    code, data, raw = run_lark(
        ["calendar", "+agenda", "--start", start, "--end", end, "--format", "json"]
    )
    if code != 0 or not data or not data.get("ok"):
        raise RuntimeError(f"读取日历失败：\n{raw}")
    return data.get("data", [])


def is_feishu_vc(event: dict[str, Any]) -> bool:
    vchat = event.get("vchat") or {}
    return vchat.get("vc_type") == "vc" and bool(vchat.get("meeting_url"))


def can_edit_event(event: dict[str, Any], me_open_id: str) -> bool:
    organizer = (event.get("event_organizer") or {}).get("user_id")
    attendee_ability = event.get("attendee_ability")
    return organizer == me_open_id or attendee_ability == "can_modify_event"


def patch_auto_record(event: dict[str, Any], apply: bool) -> tuple[str, str]:
    event_id = event["event_id"]
    data = {
        "need_notification": False,
        "vchat": {"vc_type": "vc", "meeting_settings": {"auto_record": True}},
    }
    args = [
        "calendar",
        "events",
        "patch",
        "--params",
        json.dumps({"calendar_id": "primary", "event_id": event_id}, ensure_ascii=False),
        "--data",
        json.dumps(data, ensure_ascii=False),
        "--format",
        "json",
    ]
    if not apply:
        args.append("--dry-run")
    code, parsed, raw = run_lark(args)
    if code == 0:
        return ("applied" if apply else "dry-run", raw)
    return ("failed", raw)


def recording_tokens_by_event(event_id: str) -> tuple[list[str], str | None]:
    code, data, raw = run_lark(
        ["vc", "+recording", "--calendar-event-ids", event_id, "--format", "json"]
    )
    if code != 0:
        missing = missing_scope_message(data)
        return [], missing or raw.strip()
    tokens: list[str] = []
    payload = data.get("data") if data else None
    if isinstance(payload, dict):
        text = json.dumps(payload, ensure_ascii=False)
        tokens = sorted(set(re.findall(r"obc[a-zA-Z0-9]+", text)))
    return tokens, None


def missing_scope_message(data: dict[str, Any] | None) -> str | None:
    if not data:
        return None
    err = data.get("error") or {}
    scopes = err.get("missing_scopes") or []
    if not scopes:
        return None
    return "缺少飞书授权：" + ", ".join(scopes)


def search_minutes_candidates(title: str, start: str, end: str) -> tuple[list[str], str | None]:
    code, data, raw = run_lark(
        [
            "minutes",
            "+search",
            "--participant-ids",
            "me",
            "--query",
            title,
            "--start",
            start,
            "--end",
            end,
            "--page-size",
            "10",
            "--format",
            "json",
        ]
    )
    if code != 0:
        return [], missing_scope_message(data) or raw.strip()
    text = json.dumps(data.get("data", {}), ensure_ascii=False)
    return sorted(set(re.findall(r"obc[a-zA-Z0-9]+", text))), None


def fetch_minute(minute_token: str) -> dict[str, Any]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_dir = RAW_DIR / minute_token
    out_dir.mkdir(parents=True, exist_ok=True)
    code, data, raw = run_lark(
        [
            "minutes",
            "+detail",
            "--minute-tokens",
            minute_token,
            "--summary",
            "--todo",
            "--chapter",
            "--keyword",
            "--transcript",
            "--overwrite",
            "--output-dir",
            str(out_dir.relative_to(ROOT)),
            "--format",
            "json",
        ]
    )
    if code != 0 or not data or not data.get("ok"):
        raise RuntimeError(f"读取妙记失败 {minute_token}：\n{raw}")
    minutes = data.get("data", {}).get("minutes", [])
    if not minutes:
        raise RuntimeError(f"妙记无返回内容：{minute_token}")
    return minutes[0]


def slugify(text: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|#]+", "-", text.strip())
    text = re.sub(r"\s+", "-", text)
    return text[:80] or "untitled"


def write_context(minute: dict[str, Any], title: str | None = None, event: dict[str, Any] | None = None) -> Path:
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    token = minute.get("minute_token", "unknown")
    artifacts = minute.get("artifacts") or {}
    doc_title = title or minute.get("title") or (event or {}).get("summary") or "未命名会议"
    today = dt.datetime.now().strftime("%Y-%m-%d")
    path = CONTEXT_DIR / f"{today}_{slugify(doc_title)}_{token}.md"

    lines: list[str] = []
    lines.append(f"# {doc_title}")
    lines.append("")
    lines.append("## Codex Context")
    lines.append("")
    lines.append(f"- 来源：飞书妙记 `{token}`")
    if event:
        lines.append(f"- 日程 ID：`{event.get('event_id', '')}`")
        lines.append(f"- 会议时间：{event.get('start_time', {}).get('datetime', '')} - {event.get('end_time', {}).get('datetime', '')}")
        lines.append(f"- 组织者：{(event.get('event_organizer') or {}).get('display_name', '')}")
    lines.append("")

    keywords = artifacts.get("keywords") or []
    if keywords:
        lines.append("## 关键词")
        lines.append("")
        lines.append("、".join(keywords))
        lines.append("")

    summary = artifacts.get("summary")
    if summary:
        lines.append("## 核心摘要")
        lines.append("")
        lines.append(summary.strip())
        lines.append("")

    chapters = artifacts.get("chapters") or []
    if chapters:
        lines.append("## 章节脉络")
        lines.append("")
        for item in chapters:
            lines.append(f"### {item.get('title', '未命名章节')}")
            lines.append("")
            lines.append((item.get("summary_content") or "").strip())
            lines.append("")

    todos = artifacts.get("todos") or []
    if todos:
        lines.append("## 待办")
        lines.append("")
        for todo in todos:
            box = "x" if todo.get("is_done") else " "
            lines.append(f"- [{box}] {todo.get('content', '')}")
        lines.append("")

    transcript_file = artifacts.get("transcript_file")
    if transcript_file:
        lines.append("## 原始转写")
        lines.append("")
        lines.append(f"- 本地文件：`{transcript_file}`")
        lines.append("")

    lines.append("## 后续可让 Codex 继续处理的问题")
    lines.append("")
    lines.append("- 基于这场会议提取行动清单和 owner。")
    lines.append("- 将会议结论整理成飞书文档或周报片段。")
    lines.append("- 对关键数字、口径和待确认事项做二次核对。")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def first_sentence(text: str, max_len: int = 180) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def push_summary(artifacts: dict[str, Any]) -> str:
    chapters = artifacts.get("chapters") or []
    if chapters:
        parts = []
        for item in chapters[:3]:
            title = item.get("title") or ""
            content = first_sentence(item.get("summary_content") or "", 70)
            if title and content:
                parts.append(f"{title}：{content}")
        if parts:
            return "；".join(parts)
    return first_sentence(artifacts.get("summary") or "", 220)


def meeting_time_text(event: dict[str, Any] | None) -> str:
    if not event:
        return ""
    start = event.get("start_time", {}).get("datetime", "")
    end = event.get("end_time", {}).get("datetime", "")
    if start and end:
        return f"{start} - {end}"
    return start or end


def minute_url(token: str) -> str:
    feishu_base_url = os.environ.get("FEISHU_BASE_URL", DEFAULT_FEISHU_BASE_URL).rstrip("/")
    return f"{feishu_base_url}/minutes/{token}"


def build_feishu_push_markdown(
    minute: dict[str, Any],
    context_path: Path,
    task_prompt_path: Path | None,
    title: str | None = None,
    event: dict[str, Any] | None = None,
    task_status: str | None = None,
) -> str:
    token = minute.get("minute_token", "unknown")
    artifacts = minute.get("artifacts") or {}
    doc_title = title or minute.get("title") or (event or {}).get("summary") or "未命名会议"
    summary = push_summary(artifacts)
    chapters = artifacts.get("chapters") or []
    todos = artifacts.get("todos") or []

    core_items: list[str] = []
    for item in chapters[:3]:
        chapter_title = item.get("title") or ""
        chapter_summary = first_sentence(item.get("summary_content") or "", 90)
        if chapter_title and chapter_summary:
            core_items.append(f"{chapter_title}：{chapter_summary}")
        elif chapter_title:
            core_items.append(chapter_title)
    if not core_items and summary:
        core_items.append(first_sentence(summary, 180))
    if not core_items:
        core_items.append("妙记已整理成 Codex context，可以继续推进后续任务。")

    actions = [
        "提取行动清单：整理 owner、截止时间、依赖和待确认事项",
        "生成飞书纪要：把 context 改写成可分享版本",
        "写入项目上下文：沉淀到对应项目记录",
    ]
    if todos:
        first_todo = first_sentence(todos[0].get("content", ""), 52)
        suffix = f" 等 {len(todos)} 项" if len(todos) > 1 else ""
        actions.insert(0, f"跟进妙记待办：{first_todo}{suffix}")

    lines = [
        f"## {doc_title}｜会后总结",
        "",
        f"**会议：** {doc_title}",
    ]
    time_text = meeting_time_text(event)
    if time_text:
        lines.append(f"**时间：** {time_text}")
    lines.extend(
        [
            "",
            "**核心信息**",
            "",
        ]
    )
    for item in core_items[:4]:
        lines.append(f"- {item}")
    lines.extend(["", "**我可以帮你推进**", ""])
    for idx, item in enumerate(actions[:4], start=1):
        lines.append(f"{idx}. {item}")
    lines.extend(
        [
            "",
            "**入口**",
            "",
            f"- 飞书妙记：{minute_url(token)}",
            f"- Codex context：`{context_path}`",
        ]
    )
    if task_prompt_path:
        lines.append(f"- 任务入口：`{task_prompt_path}`")
    if task_status:
        lines.append(f"- 飞书任务：{task_status}")
    return "\n".join(lines)


def write_feishu_push_outbox(markdown: str, title: str, token: str) -> Path:
    FEISHU_PUSH_OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now().strftime("%Y-%m-%d")
    path = FEISHU_PUSH_OUTBOX_DIR / f"{today}_{slugify(title)}_{token}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def send_feishu_push(
    markdown: str,
    apply: bool,
    user_id: str | None = None,
    chat_id: str | None = None,
    identity: str = "bot",
    idempotency_key: str | None = None,
) -> tuple[str, str]:
    if not user_id and not chat_id:
        raise ValueError("发送飞书推送需要 user_id 或 chat_id")
    args = ["im", "+messages-send", "--as", identity, "--markdown", markdown, "--format", "json"]
    if user_id:
        args.extend(["--user-id", user_id])
    if chat_id:
        args.extend(["--chat-id", chat_id])
    if idempotency_key:
        args.extend(["--idempotency-key", idempotency_key[:120]])
    if not apply:
        args.append("--dry-run")
    code, data, raw = run_lark(args)
    if code == 0:
        return ("sent" if apply else "dry-run", raw)
    return ("failed", missing_scope_message(data) or raw)


def write_bridge_handoff(
    minute: dict[str, Any],
    context_path: Path,
    title: str | None = None,
    event: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    BRIDGE_OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    TASK_PROMPT_DIR.mkdir(parents=True, exist_ok=True)

    token = minute.get("minute_token", "unknown")
    artifacts = minute.get("artifacts") or {}
    doc_title = title or minute.get("title") or (event or {}).get("summary") or "未命名会议"
    today = dt.datetime.now().strftime("%Y-%m-%d")
    stem = f"{today}_{slugify(doc_title)}_{token}"
    outbox_path = BRIDGE_OUTBOX_DIR / f"{stem}.md"
    task_path = TASK_PROMPT_DIR / f"{stem}.md"

    summary = push_summary(artifacts)
    chapters = artifacts.get("chapters") or []
    todos = artifacts.get("todos") or []
    keywords = artifacts.get("keywords") or []
    top_chapters = [c.get("title", "") for c in chapters[:5] if c.get("title")]

    out_lines: list[str] = []
    out_lines.append(f"# AI 助手推送稿｜{doc_title}")
    out_lines.append("")
    out_lines.append("这场会议的妙记已经整理成 Codex context，可以继续处理。")
    out_lines.append("")
    out_lines.append("## 摘要")
    out_lines.append("")
    out_lines.append(summary or "已生成会议上下文，建议打开 context 查看完整内容。")
    out_lines.append("")
    if keywords:
        out_lines.append("## 关键词")
        out_lines.append("")
        out_lines.append("、".join(keywords[:12]))
        out_lines.append("")
    if top_chapters:
        out_lines.append("## 重点脉络")
        out_lines.append("")
        for item in top_chapters:
            out_lines.append(f"- {item}")
        out_lines.append("")
    if todos:
        out_lines.append("## 待办预览")
        out_lines.append("")
        for todo in todos[:5]:
            out_lines.append(f"- {todo.get('content', '')}")
        out_lines.append("")
    out_lines.append("## 可执行动作")
    out_lines.append("")
    out_lines.append("回复下面任一编号给桥接 AI 助手：")
    out_lines.append("")
    out_lines.append("1. 提取行动清单：整理 owner、截止时间、依赖和待确认事项。")
    out_lines.append("2. 生成飞书纪要：把 context 改写成可分享的飞书文档。")
    out_lines.append("3. 写入项目上下文：把会议结论并入对应项目记录。")
    out_lines.append("4. 生成跟进消息：产出可发给相关人的中文跟进话术。")
    out_lines.append("")
    out_lines.append("## Codex context")
    out_lines.append("")
    out_lines.append(f"- `{context_path}`")
    out_lines.append(f"- 妙记 token：`{token}`")
    out_lines.append("")
    out_lines.append("## 给桥接 AI 助手的执行提示")
    out_lines.append("")
    out_lines.append("请读取上面的 Codex context，根据我的编号回复执行对应任务；涉及发送消息、发布文档、改权限、修改正式记录时，先给出风险说明并等待确认。")
    out_lines.append("")
    outbox_path.write_text("\n".join(out_lines), encoding="utf-8")

    task_lines: list[str] = []
    task_lines.append(f"# Codex 执行入口｜{doc_title}")
    task_lines.append("")
    task_lines.append(f"请先读取会议上下文：`{context_path}`")
    task_lines.append("")
    task_lines.append("## 任务菜单")
    task_lines.append("")
    task_lines.append("### 1. 提取行动清单")
    task_lines.append("输出 owner / action / due date / dependency / risk 表格；缺失 owner 或时间时标记“待确认”。")
    task_lines.append("")
    task_lines.append("### 2. 生成飞书纪要")
    task_lines.append("按“核心结论、关键数字、讨论要点、待办、风险/待确认”整理；发布前需确认。")
    task_lines.append("")
    task_lines.append("### 3. 写入项目上下文")
    task_lines.append("判断应归入哪个项目目录；只生成草稿，不直接改正式项目台账。")
    task_lines.append("")
    task_lines.append("### 4. 生成跟进消息")
    task_lines.append("输出可复制给相关人的消息草稿；不直接发送。")
    task_lines.append("")
    task_lines.append("## 安全边界")
    task_lines.append("")
    task_lines.append("- 不自动发送 IM。")
    task_lines.append("- 不自动发布飞书文档。")
    task_lines.append("- 不自动修改正式数据口径。")
    task_lines.append("- 外部可见动作必须等待确认。")
    task_lines.append("")
    task_path.write_text("\n".join(task_lines), encoding="utf-8")
    return outbox_path, task_path


def build_task_payload(
    minute: dict[str, Any],
    context_path: Path,
    task_prompt_path: Path,
    title: str | None = None,
    event: dict[str, Any] | None = None,
    assignee_open_id: str | None = None,
) -> dict[str, Any]:
    token = minute.get("minute_token", "unknown")
    feishu_base_url = os.environ.get("FEISHU_BASE_URL", DEFAULT_FEISHU_BASE_URL).rstrip("/")
    minute_url = f"{feishu_base_url}/minutes/{token}"
    artifacts = minute.get("artifacts") or {}
    doc_title = title or minute.get("title") or (event or {}).get("summary") or "未命名会议"
    keywords = artifacts.get("keywords") or []
    todos = artifacts.get("todos") or []
    summary = push_summary(artifacts)

    description_lines = [
        f"会议妙记已整理为 Codex context。",
        "",
        f"会议：{doc_title}",
        f"妙记 token：{token}",
        f"Context：{context_path}",
        f"任务入口：{task_prompt_path}",
        "",
        "摘要：",
        summary or "已生成会议上下文，请打开 context 查看完整内容。",
    ]
    if keywords:
        description_lines.extend(["", "关键词：", "、".join(keywords[:12])])
    if todos:
        description_lines.extend(["", "妙记待办预览："])
        for todo in todos[:5]:
            description_lines.append(f"- {todo.get('content', '')}")
    description_lines.extend(
        [
            "",
            "建议执行动作：",
            "1. 提取行动清单：整理 owner、截止时间、依赖和待确认事项。",
            "2. 生成飞书纪要：把 context 改写成可分享的飞书文档。",
            "3. 写入项目上下文：把会议结论并入对应项目记录。",
            "4. 生成跟进消息：产出可发给相关人的中文跟进话术。",
            "",
            "安全边界：涉及发送消息、发布文档、改权限、修改正式记录时，先给出风险说明并等待确认。",
        ]
    )

    payload: dict[str, Any] = {
        "summary": f"处理会议妙记：{doc_title}",
        "description": "\n".join(description_lines)[:3000],
        "client_token": f"meeting-minutes-{token}",
        "origin": {
            "href": {
                "title": f"飞书妙记：{doc_title}",
                "url": minute_url,
            },
            "platform_i18n_name": {
                "zh_cn": "飞书妙记",
                "en_us": "Feishu Minutes",
            },
        },
        "extra": json.dumps(
            {
                "source": "meeting-codex-inbox",
                "minute_token": token,
                "minute_url": minute_url,
                "context_path": str(context_path),
                "task_prompt_path": str(task_prompt_path),
            },
            ensure_ascii=False,
        ),
    }
    if assignee_open_id:
        payload["members"] = [{"id": assignee_open_id, "type": "user", "role": "assignee"}]
    return payload


def write_task_outbox(payload: dict[str, Any], title: str, token: str) -> Path:
    TASK_OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now().strftime("%Y-%m-%d")
    path = TASK_OUTBOX_DIR / f"{today}_{slugify(title)}_{token}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def create_feishu_task(payload: dict[str, Any], apply: bool) -> tuple[str, str]:
    args = [
        "task",
        "+create",
        "--data",
        json.dumps(payload, ensure_ascii=False),
        "--format",
        "json",
    ]
    if not apply:
        args.append("--dry-run")
    code, data, raw = run_lark(args)
    if code == 0:
        return ("created" if apply else "dry-run", raw)
    return ("failed", raw)


def append_pending(event: dict[str, Any], reason: str) -> None:
    if not PENDING_FILE.exists():
        PENDING_FILE.write_text("# 待补妙记会议\n\n", encoding="utf-8")
    event_id = event.get("event_id", "")
    existing = PENDING_FILE.read_text(encoding="utf-8")
    if event_id and f"event_id=`{event_id}`" in existing:
        return
    line = (
        f"- {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"{event.get('summary', '未命名会议')} | "
        f"{event.get('start_time', {}).get('datetime', '')} | "
        f"event_id=`{event_id}` | {reason}\n"
    )
    with PENDING_FILE.open("a", encoding="utf-8") as f:
        f.write(line)


def scan(args: argparse.Namespace) -> int:
    me = current_user_open_id()
    events = [e for e in agenda(args.start, args.end) if is_feishu_vc(e)]
    processed_tokens: set[str] = set()
    print(f"找到飞书 VC 会议：{len(events)} 场")
    for event in events:
        title = event.get("summary", "未命名会议")
        event_id = event.get("event_id")
        editable = can_edit_event(event, me)
        print(f"\n- {title}")
        print(f"  event_id: {event_id}")
        print(f"  editable: {editable}")

        if editable:
            status, raw = patch_auto_record(event, apply=args.apply_recording)
            print(f"  auto_record: {status}")
            if status == "failed":
                print(indent(raw.strip(), "    "))
        else:
            print("  auto_record: skipped participant-only")

        if not args.process_minutes:
            continue

        tokens, err = recording_tokens_by_event(event_id)
        if err:
            print(f"  recording lookup: {err}")
        if not tokens and args.search_minutes_fallback and title.strip():
            candidates, search_err = search_minutes_candidates(title, args.start, args.end)
            if search_err:
                print(f"  minutes search fallback: {search_err}")
            tokens = candidates
            if tokens:
                print(f"  minutes candidates: {', '.join(tokens)}")

        if not tokens:
            append_pending(event, err or "未找到妙记")
            print("  context: pending missing minutes")
            continue

        for token in tokens:
            if token in processed_tokens:
                print(f"  context: skipped duplicate minute {token}")
                continue
            processed_tokens.add(token)
            minute = fetch_minute(token)
            path = write_context(minute, title=title, event=event)
            print(f"  context: {path.relative_to(ROOT)}")
            task_path = None
            task_status = None
            if args.bridge_handoff:
                outbox_path, task_path = write_bridge_handoff(minute, path, title=title, event=event)
                print(f"  bridge outbox: {outbox_path.relative_to(ROOT)}")
                print(f"  task prompt: {task_path.relative_to(ROOT)}")
                if args.create_task:
                    assignee = current_user_open_id() if args.assign_to_me else None
                    payload = build_task_payload(minute, path, task_path, title=title, event=event, assignee_open_id=assignee)
                    task_outbox = write_task_outbox(payload, title, token)
                    print(f"  task outbox: {task_outbox.relative_to(ROOT)}")
                    status, raw = create_feishu_task(payload, apply=args.apply_task)
                    print(f"  feishu task: {status}")
                    task_status = status
                    if status == "failed":
                        print(indent(raw.strip(), "    "))
            if args.push_feishu:
                push_user_id = args.push_user_id or (current_user_open_id() if not args.push_chat_id else None)
                push_markdown = build_feishu_push_markdown(
                    minute,
                    path,
                    task_path,
                    title=title,
                    event=event,
                    task_status=task_status,
                )
                push_outbox = write_feishu_push_outbox(push_markdown, title, token)
                print(f"  feishu push outbox: {push_outbox.relative_to(ROOT)}")
                status, raw = send_feishu_push(
                    push_markdown,
                    apply=args.apply_push,
                    user_id=push_user_id,
                    chat_id=args.push_chat_id,
                    identity=args.push_as,
                    idempotency_key=f"meeting-minutes-push-{token}",
                )
                print(f"  feishu push: {status}")
                if status == "failed":
                    print(indent(raw.strip(), "    "))
    return 0


def indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())


def process_single_minute(args: argparse.Namespace) -> int:
    minute = fetch_minute(args.minute_token)
    path = write_context(minute, title=args.title)
    print(path)
    task_path = None
    if args.bridge_handoff:
        outbox_path, task_path = write_bridge_handoff(minute, path, title=args.title)
        print(outbox_path)
        print(task_path)
    if args.create_task:
        doc_title = args.title or minute.get("title") or "未命名会议"
        if task_path is None:
            _, task_path = write_bridge_handoff(minute, path, title=args.title)
        assignee = current_user_open_id() if args.assign_to_me else None
        payload = build_task_payload(minute, path, task_path, title=args.title, assignee_open_id=assignee)
        task_outbox = write_task_outbox(payload, doc_title, args.minute_token)
        print(task_outbox)
        status, raw = create_feishu_task(payload, apply=args.apply_task)
        print(f"feishu task: {status}")
        if status == "failed":
            print(raw.strip())
            return 1
    if args.push_feishu:
        doc_title = args.title or minute.get("title") or "未命名会议"
        push_user_id = args.push_user_id or (current_user_open_id() if not args.push_chat_id else None)
        push_markdown = build_feishu_push_markdown(
            minute,
            path,
            task_path,
            title=args.title,
            task_status="created" if args.create_task and args.apply_task else None,
        )
        push_outbox = write_feishu_push_outbox(push_markdown, doc_title, args.minute_token)
        print(push_outbox)
        status, raw = send_feishu_push(
            push_markdown,
            apply=args.apply_push,
            user_id=push_user_id,
            chat_id=args.push_chat_id,
            identity=args.push_as,
            idempotency_key=f"meeting-minutes-push-{args.minute_token}",
        )
        print(f"feishu push: {status}")
        if status == "failed":
            print(raw.strip())
            return 1
    return 0


def default_dates() -> tuple[str, str]:
    today = dt.date.today()
    tomorrow = today + dt.timedelta(days=1)
    return today.isoformat(), tomorrow.isoformat()


def build_parser() -> argparse.ArgumentParser:
    start, end = default_dates()
    p = argparse.ArgumentParser(description="Sync Feishu meetings/minutes into Codex context files.")
    p.add_argument("--start", default=start, help="扫描开始日期或 ISO 时间，默认今天")
    p.add_argument("--end", default=end, help="扫描结束日期或 ISO 时间，默认明天")
    p.add_argument("--apply-recording", action="store_true", help="真实写入 auto_record=true；默认只 dry-run")
    p.add_argument("--process-minutes", action="store_true", help="尝试查找并处理会后妙记")
    p.add_argument("--no-search-minutes-fallback", dest="search_minutes_fallback", action="store_false", help="关闭按标题搜索妙记候选")
    p.add_argument("--no-bridge-handoff", dest="bridge_handoff", action="store_false", help="不生成桥接 AI 助手推送稿和任务入口")
    p.add_argument("--create-task", action="store_true", help="生成飞书任务草稿，并调用 task +create；默认 dry-run")
    p.add_argument("--apply-task", action="store_true", help="真实创建飞书任务；必须和 --create-task 一起使用")
    p.add_argument("--no-assign-to-me", dest="assign_to_me", action="store_false", help="创建任务时不自动分配给当前登录用户")
    p.add_argument("--push-feishu", action="store_true", help="生成飞书 IM 推送稿，并调用 im +messages-send；默认 dry-run")
    p.add_argument("--apply-push", action="store_true", help="真实发送飞书 IM 推送；必须和 --push-feishu 一起使用")
    p.add_argument("--push-user-id", help="推送到个人 open_id；默认当前登录用户")
    p.add_argument("--push-chat-id", help="推送到指定群聊 chat_id；传入后优先群聊")
    p.add_argument("--push-as", choices=["bot", "user"], default="bot", help="发送身份，默认 bot")
    p.add_argument("--minute-token", help="直接处理指定妙记 token")
    p.add_argument("--title", help="直接处理妙记时指定标题")
    p.set_defaults(search_minutes_fallback=True, bridge_handoff=True, assign_to_me=True)
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.minute_token:
        return process_single_minute(args)
    return scan(args)


if __name__ == "__main__":
    raise SystemExit(main())
