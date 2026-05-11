#!/usr/bin/env python3
"""Call Feishu Aily multi-turn OpenAPI with session -> message -> run -> messages."""

import argparse
import json
import os
import time
import uuid
from pathlib import Path

import requests


BASE = os.getenv("FEISHU_OPENAPI_BASE", "https://open.feishu.cn/open-apis")
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "EXPIRED", "CANCELLED"}


def request(method, path, token, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    resp = requests.request(method, f"{BASE}{path}", headers=headers, timeout=30, **kwargs)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Aily API failed: {data}")
    return data.get("data", {})


def create_session(token, biz_user_id=None):
    headers = {}
    if biz_user_id:
        headers["X-aily-BizUserID"] = biz_user_id
    data = request("POST", "/aily/v1/sessions", token, headers=headers, json={})
    return data["session"]["id"]


def create_message(token, session_id, content, content_type="MDX"):
    payload = {
        "idempotent_id": str(uuid.uuid4()),
        "content_type": content_type,
        "content": content,
    }
    data = request("POST", f"/aily/v1/sessions/{session_id}/messages", token, json=payload)
    return data["message"]["id"]


def create_run(token, session_id, app_id, skill_id=None, skill_input=None, metadata=None):
    payload = {"app_id": app_id}
    if skill_id:
        payload["skill_id"] = skill_id
    if skill_input is not None:
        payload["skill_input"] = skill_input if isinstance(skill_input, str) else json.dumps(skill_input, ensure_ascii=False)
    if metadata is not None:
        payload["metadata"] = metadata if isinstance(metadata, str) else json.dumps(metadata, ensure_ascii=False)
    data = request("POST", f"/aily/v1/sessions/{session_id}/runs", token, json=payload)
    return data["run"]["id"], data["run"].get("status")


def get_run(token, session_id, run_id):
    data = request("GET", f"/aily/v1/sessions/{session_id}/runs/{run_id}", token)
    return data["run"]


def list_messages(token, session_id, run_id=None, with_partial_message=False):
    params = {}
    if run_id:
        params["run_id"] = run_id
    if with_partial_message:
        params["with_partial_message"] = "true"
    data = request("GET", f"/aily/v1/sessions/{session_id}/messages", token, params=params)
    return data.get("messages", [])


def poll_run(token, session_id, run_id, interval, timeout):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        run = get_run(token, session_id, run_id)
        status = run.get("status")
        last = run
        if status in TERMINAL_STATUSES or status == "REQUIRES_MESSAGE":
            return run
        time.sleep(interval)
    raise TimeoutError(f"Aily run timed out. last_run={last}")


def main():
    parser = argparse.ArgumentParser(description="Call Feishu Aily API.")
    parser.add_argument("--app-id", default=os.getenv("AILY_APP_ID"), help="Aily app ID, e.g. spring_xxx__c")
    parser.add_argument("--token-env", default="FEISHU_USER_ACCESS_TOKEN", help="Env var containing access token")
    parser.add_argument("--prompt", help="Prompt text")
    parser.add_argument("--prompt-file", help="Path to prompt text file")
    parser.add_argument("--content-type", default="MDX", choices=["MDX", "TEXT"])
    parser.add_argument("--skill-id", help="Optional Aily skill ID")
    parser.add_argument("--skill-input", help="Optional JSON string for skill input")
    parser.add_argument("--metadata", help="Optional JSON string metadata")
    parser.add_argument("--biz-user-id", help="Optional X-aily-BizUserID")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args()

    token = os.getenv(args.token_env)
    if not token:
        raise SystemExit(f"Missing access token env var: {args.token_env}")
    if not args.app_id:
        raise SystemExit("Missing --app-id or AILY_APP_ID")
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    elif args.prompt:
        prompt = args.prompt
    else:
        raise SystemExit("Missing --prompt or --prompt-file")

    session_id = create_session(token, args.biz_user_id)
    message_id = create_message(token, session_id, prompt, args.content_type)
    run_id, initial_status = create_run(
        token,
        session_id,
        args.app_id,
        skill_id=args.skill_id,
        skill_input=args.skill_input,
        metadata=args.metadata,
    )
    run = poll_run(token, session_id, run_id, args.interval, args.timeout)
    messages = list_messages(token, session_id, run_id=run_id, with_partial_message=True)
    assistant_messages = [
        msg for msg in messages
        if msg.get("sender", {}).get("sender_type") == "ASSISTANT"
    ]
    print(json.dumps({
        "session_id": session_id,
        "message_id": message_id,
        "run_id": run_id,
        "initial_status": initial_status,
        "final_status": run.get("status"),
        "assistant_messages": assistant_messages,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
