#!/usr/bin/env python3
"""Publish analysis output to Feishu and optionally hand it off to Airy."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import requests


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
WORKSPACE_ROOT = SKILL_DIR.parent.parent.parent
DEFAULT_CONFIG = SKILL_DIR / "config.local.json"
PUBLISHER = WORKSPACE_ROOT / ".agents" / "skills" / "feishu-doc-publisher" / "scripts" / "publish_feishu_doc.py"

APP_ID = os.getenv("FEISHU_APP_ID", "cli_a937e91d7f38dbd8")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "r2Qm0OBs7cA7x9CpD29hwg1BMJpfx4Ze")
BASE = "https://open.feishu.cn/open-apis"

DEFAULT_AIRY_PROMPT = """请基于这份原始分析材料，产出一版适合业务汇报的可视化飞书文档，并做排版美化。

标题：{title}
原始材料：{resource_url}

要求：
- 保留数据口径和核心结论
- 结构清晰，适合直接转发汇报
- 原始数据尽量整理成易读表格
- 高亮关键结论和建议
- 输出新的飞书文档链接"""


def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_token() -> str:
    resp = requests.post(
        f"{BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def publish_doc(title: str, input_path: Path) -> str:
    lark_cli = shutil.which("lark-cli")
    if lark_cli:
        markdown = input_path.read_text(encoding="utf-8")
        cmd = [
            lark_cli,
            "docs",
            "+create",
            "--title",
            title,
            "--markdown",
            markdown,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            try:
                payload = json.loads(result.stdout)
                if payload.get("ok") and payload.get("data", {}).get("doc_url"):
                    return payload["data"]["doc_url"]
            except json.JSONDecodeError:
                pass

    if not PUBLISHER.exists():
        raise FileNotFoundError(f"未找到飞书发布脚本: {PUBLISHER}")
    cmd = [
        "python3",
        str(PUBLISHER),
        "--title",
        title,
        "--input",
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    url = result.stdout.strip().splitlines()[-1].strip()
    if not url.startswith("http"):
        raise RuntimeError(f"发布结果异常: {result.stdout}")
    return url


def build_airy_message(title: str, resource_url: str, template: str) -> str:
    return template.format(title=title, resource_url=resource_url)


def send_text_message(receive_id: str, receive_id_type: str, text: str) -> dict:
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }
    resp = requests.post(
        f"{BASE}/im/v1/messages?receive_id_type={receive_id_type}",
        headers=headers,
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"发送 Airy 消息失败: {data}")
    return data


def main():
    parser = argparse.ArgumentParser(description="Publish Feishu analysis doc and hand it off to Airy.")
    parser.add_argument("--title", required=True, help="Analysis title")
    parser.add_argument("--input", help="Absolute path to local markdown draft")
    parser.add_argument("--resource-url", help="Existing Feishu doc/sheet URL to hand off")
    parser.add_argument("--skip-airy", action="store_true", help="Publish only, do not notify Airy")
    parser.add_argument("--airy-chat-id", help="Override Airy target receive_id")
    parser.add_argument(
        "--airy-receive-id-type",
        choices=["chat_id", "open_id", "user_id", "union_id", "email"],
        help="Override Airy receive_id_type",
    )
    parser.add_argument("--config", help="Path to config.local.json")
    args = parser.parse_args()

    if not args.input and not args.resource_url:
        raise SystemExit("必须提供 --input 或 --resource-url")

    config_path = Path(args.config).expanduser().resolve() if args.config else DEFAULT_CONFIG
    config = load_config(config_path)

    published_url = None
    if args.input:
        input_path = Path(args.input).expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        published_url = publish_doc(args.title, input_path)

    resource_url = args.resource_url or published_url
    result = {
        "title": args.title,
        "published_url": published_url,
        "resource_url": resource_url,
        "airy_status": "skipped",
    }

    if args.skip_airy:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    airy_chat_id = args.airy_chat_id or config.get("airy_chat_id")
    airy_receive_id_type = args.airy_receive_id_type or config.get("airy_receive_id_type", "chat_id")
    if not airy_chat_id:
        result["airy_reason"] = "missing airy_chat_id"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    template = config.get("airy_prompt_template", DEFAULT_AIRY_PROMPT)
    text = build_airy_message(args.title, resource_url, template)
    send_resp = send_text_message(airy_chat_id, airy_receive_id_type, text)

    result["airy_status"] = "sent"
    result["airy_receive_id_type"] = airy_receive_id_type
    result["airy_message_id"] = send_resp.get("data", {}).get("message_id")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
