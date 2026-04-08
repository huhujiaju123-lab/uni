#!/usr/bin/env python3
"""Expose lark-cli docs/sheets as simple MCP-style commands."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AILY_DOC = ROOT / "aily_doc.py"

SERVERS = [
    {
        "server_id": "docs",
        "description": "Feishu docs operations via lark-cli",
    },
    {
        "server_id": "sheets",
        "description": "Feishu sheets operations via lark-cli",
    },
]

TOOLS = {
    "docs": [
        {"tool_name": "search-doc", "description": "Search docs by keyword", "required": ["query"]},
        {"tool_name": "create-doc", "description": "Create a doc from markdown", "required": ["title", "markdown|input"]},
        {"tool_name": "update-doc", "description": "Update an existing doc", "required": ["doc", "markdown|input"]},
    ],
    "sheets": [
        {"tool_name": "create-sheet", "description": "Create a spreadsheet", "required": ["title"]},
        {"tool_name": "write-sheet", "description": "Overwrite values to a range", "required": ["url|spreadsheet_token", "range", "values"]},
        {"tool_name": "append-sheet", "description": "Append values to a range", "required": ["url|spreadsheet_token", "range", "values"]},
        {"tool_name": "read-sheet", "description": "Read values from a range", "required": ["url|spreadsheet_token", "range"]},
    ],
}


def ensure_lark_cli() -> str:
    path = shutil.which("lark-cli")
    if not path:
        raise SystemExit("未找到 lark-cli，请先安装并完成 auth login。")
    return path


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "command failed")
    output = result.stdout.strip() or result.stderr.strip()
    print(output)


def cmd_servers(_args):
    print(json.dumps(SERVERS, ensure_ascii=False, indent=2))


def cmd_tools(args):
    if args.server_id not in TOOLS:
        raise SystemExit(f"未知 server_id: {args.server_id}")
    print(json.dumps(TOOLS[args.server_id], ensure_ascii=False, indent=2))


def call_docs(tool_name: str, params: dict):
    py = sys.executable
    base = [py, str(AILY_DOC)]
    if tool_name == "search-doc":
        cmd = base + ["search-doc", "--query", params["query"]]
        if params.get("format"):
            cmd += ["--format", params["format"]]
        if params.get("output"):
            cmd += ["-o", params["output"]]
        run(cmd)
        return

    if tool_name == "create-doc":
        cmd = base + ["create-doc", "--title", params["title"]]
        if params.get("markdown"):
            cmd += ["--markdown", params["markdown"]]
        elif params.get("input"):
            cmd += ["--input", params["input"]]
        else:
            raise SystemExit("create-doc 需要 markdown 或 input")
        if params.get("output"):
            cmd += ["-o", params["output"]]
        run(cmd)
        return

    if tool_name == "update-doc":
        cmd = base + ["update-doc", "--doc", params["doc"]]
        if params.get("mode"):
            cmd += ["--mode", params["mode"]]
        if params.get("new_title"):
            cmd += ["--new-title", params["new_title"]]
        if params.get("markdown"):
            cmd += ["--markdown", params["markdown"]]
        elif params.get("input"):
            cmd += ["--input", params["input"]]
        else:
            raise SystemExit("update-doc 需要 markdown 或 input")
        if params.get("output"):
            cmd += ["-o", params["output"]]
        run(cmd)
        return

    raise SystemExit(f"docs 不支持工具: {tool_name}")


def call_sheets(tool_name: str, params: dict):
    cli = ensure_lark_cli()
    if tool_name == "create-sheet":
        cmd = [cli, "sheets", "+create", "--title", params["title"]]
        if params.get("headers") is not None:
            cmd += ["--headers", json.dumps(params["headers"], ensure_ascii=False)]
        if params.get("data") is not None:
            cmd += ["--data", json.dumps(params["data"], ensure_ascii=False)]
        run(cmd)
        return

    if tool_name in {"write-sheet", "append-sheet", "read-sheet"}:
        action = {
            "write-sheet": "+write",
            "append-sheet": "+append",
            "read-sheet": "+read",
        }[tool_name]
        cmd = [cli, "sheets", action]
        if params.get("url"):
            cmd += ["--url", params["url"]]
        elif params.get("spreadsheet_token"):
            cmd += ["--spreadsheet-token", params["spreadsheet_token"]]
        else:
            raise SystemExit(f"{tool_name} 需要 url 或 spreadsheet_token")
        if params.get("sheet_id"):
            cmd += ["--sheet-id", params["sheet_id"]]
        cmd += ["--range", params["range"]]
        if tool_name != "read-sheet":
            cmd += ["--values", json.dumps(params["values"], ensure_ascii=False)]
        elif params.get("value_render_option"):
            cmd += ["--value-render-option", params["value_render_option"]]
        run(cmd)
        return

    raise SystemExit(f"sheets 不支持工具: {tool_name}")


def cmd_call(args):
    if args.server_id not in TOOLS:
        raise SystemExit(f"未知 server_id: {args.server_id}")
    params = json.loads(args.params) if args.params else {}
    if args.server_id == "docs":
        call_docs(args.tool_name, params)
        return
    if args.server_id == "sheets":
        call_sheets(args.tool_name, params)
        return
    raise SystemExit(f"不支持 server: {args.server_id}")


def build_parser():
    parser = argparse.ArgumentParser(description="aily-mcp wrapper powered by lark-cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("servers", help="查看可用 MCP server")
    p.set_defaults(func=cmd_servers)

    p = sub.add_parser("tools", help="查看 server 的工具列表")
    p.add_argument("-s", "--server-id", required=True)
    p.set_defaults(func=cmd_tools)

    p = sub.add_parser("call", help="调用具体工具")
    p.add_argument("-s", "--server-id", required=True)
    p.add_argument("-t", "--tool-name", required=True)
    p.add_argument("-p", "--params", default="{}")
    p.set_defaults(func=cmd_call)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
