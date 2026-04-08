#!/usr/bin/env python3
"""Wrap lark-cli docs commands into aily-doc style commands."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def ensure_lark_cli() -> str:
    path = shutil.which("lark-cli")
    if not path:
        raise SystemExit("未找到 lark-cli，请先安装并完成 auth login。")
    return path


def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    payload_text = stdout or stderr
    try:
        payload = json.loads(payload_text) if payload_text else None
    except json.JSONDecodeError:
        payload = None

    if result.returncode != 0:
        if payload:
            error = payload.get("error") or {}
            if error.get("type") == "missing_scope":
                hint = error.get("hint", "")
                raise SystemExit(f"{error.get('message')}\n{hint}".strip())
        message = stderr or stdout or f"command failed: {' '.join(cmd)}"
        raise SystemExit(message)

    if payload:
        error = payload.get("error") or {}
        if not payload.get("ok", True) and error.get("type") == "missing_scope":
            hint = error.get("hint", "")
            raise SystemExit(f"{error.get('message')}\n{hint}".strip())
    return stdout or stderr


def write_output(content: str, output_path: Optional[str]):
    if output_path:
        Path(output_path).expanduser().resolve().write_text(content + "\n", encoding="utf-8")
    print(content)


def load_markdown(inline_markdown: Optional[str], input_path: Optional[str]) -> str:
    if inline_markdown:
        return inline_markdown
    if input_path:
        return Path(input_path).expanduser().resolve().read_text(encoding="utf-8")
    raise SystemExit("必须提供 --markdown 或 --input")


def cmd_search(args):
    cli = ensure_lark_cli()
    cmd = [cli, "docs", "+search", "--query", args.query, "--format", args.format]
    output = run_cmd(cmd)
    write_output(output, args.output)


def cmd_create(args):
    cli = ensure_lark_cli()
    markdown = load_markdown(args.markdown, args.input)
    cmd = [cli, "docs", "+create", "--title", args.title, "--markdown", markdown]
    output = run_cmd(cmd)
    write_output(output, args.output)


def cmd_update(args):
    cli = ensure_lark_cli()
    markdown = load_markdown(args.markdown, args.input)
    cmd = [cli, "docs", "+update", "--doc", args.doc, "--mode", args.mode, "--markdown", markdown]
    if args.new_title:
        cmd.extend(["--new-title", args.new_title])
    output = run_cmd(cmd)
    write_output(output, args.output)


def build_parser():
    parser = argparse.ArgumentParser(description="aily-doc wrapper powered by lark-cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search-doc", help="搜索飞书文档")
    p.add_argument("--query", required=True)
    p.add_argument("--format", default="json", choices=["json", "pretty", "table", "csv", "ndjson"])
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("create-doc", help="创建飞书文档")
    p.add_argument("--title", required=True)
    p.add_argument("--markdown")
    p.add_argument("--input")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("update-doc", help="更新飞书文档")
    p.add_argument("--doc", required=True, help="文档 URL 或 token")
    p.add_argument("--mode", default="overwrite")
    p.add_argument("--new-title")
    p.add_argument("--markdown")
    p.add_argument("--input")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_update)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
