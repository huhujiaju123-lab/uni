#!/usr/bin/env python3
"""Publish a markdown file as a Feishu docx document."""

import argparse
import os
import re
import subprocess
import time
from pathlib import Path

import requests

APP_ID = os.getenv("FEISHU_APP_ID", "cli_a937e91d7f38dbd8")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "r2Qm0OBs7cA7x9CpD29hwg1BMJpfx4Ze")
BASE = "https://open.feishu.cn/open-apis"
OPEN_BASE = os.getenv("FEISHU_DOC_BASE", "https://lkusco.feishu.cn/docx")


def get_token():
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


def txt(content, bold=False):
    element = {"text_run": {"content": content}}
    if bold:
        element["text_run"]["text_element_style"] = {"bold": True}
    return element


def heading(level, content):
    return {"block_type": level + 2, f"heading{level}": {"elements": [txt(content)]}}


def paragraph(content):
    return {"block_type": 2, "text": {"elements": [txt(content)]}}


def bullet(content):
    return {"block_type": 12, "bullet": {"elements": [txt(content)]}}


def ordered(content):
    return {"block_type": 13, "ordered": {"elements": [txt(content)]}}


def split_blocks(markdown_text):
    lines = markdown_text.splitlines()
    blocks = []
    paragraph_buffer = []

    def flush_paragraph():
        nonlocal paragraph_buffer
        if paragraph_buffer:
            content = " ".join(x.strip() for x in paragraph_buffer if x.strip())
            if content:
                blocks.append(paragraph(content))
            paragraph_buffer = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            blocks.append(heading(2, stripped[3:].strip()))
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            blocks.append(heading(1, stripped[2:].strip()))
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            blocks.append(bullet(stripped[2:].strip()))
            continue

        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            content = re.sub(r"^\d+\.\s+", "", stripped)
            blocks.append(ordered(content))
            continue

        paragraph_buffer.append(stripped)

    flush_paragraph()
    return blocks


def add_blocks(doc_id, parent_id, children, headers):
    batch_size = 20
    for i in range(0, len(children), batch_size):
        batch = children[i:i + batch_size]
        resp = requests.post(
            f"{BASE}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children",
            headers=headers,
            json={"children": batch, "index": -1},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"写入文档失败: {data}")
        time.sleep(0.2)


def create_doc(title, headers):
    resp = requests.post(
        f"{BASE}/docx/v1/documents",
        headers=headers,
        json={"title": title},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"创建文档失败: {data}")
    return data["data"]["document"]["document_id"]


def update_permission(doc_id, headers):
    payload = {
        "external_access": False,
        "security_entity": "anyone_can_view",
        "comment_entity": "anyone_can_view",
        "share_entity": "anyone",
        "link_share_entity": "tenant_readable",
        "invite_external": False,
    }
    resp = requests.patch(
        f"{BASE}/drive/v1/permissions/{doc_id}/public?type=docx",
        headers=headers,
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"更新权限失败: {data}")


def main():
    parser = argparse.ArgumentParser(description="Publish a markdown file to Feishu docx.")
    parser.add_argument("--title", required=True, help="Feishu document title")
    parser.add_argument("--input", required=True, help="Absolute path to the markdown file")
    parser.add_argument("--open", action="store_true", dest="open_doc", help="Open the created doc")
    parser.add_argument(
        "--no-permission-update",
        action="store_true",
        help="Skip the tenant-readable permission patch",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    markdown_text = input_path.read_text(encoding="utf-8")
    blocks = split_blocks(markdown_text)
    if not blocks:
        raise RuntimeError("输入文件没有可发布内容")

    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    doc_id = create_doc(args.title, headers)
    add_blocks(doc_id, doc_id, blocks, headers)

    if not args.no_permission_update:
        update_permission(doc_id, headers)

    url = f"{OPEN_BASE}/{doc_id}"
    print(url)

    if args.open_doc:
        subprocess.run(["open", url], check=False)


if __name__ == "__main__":
    main()
