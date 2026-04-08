---
name: feishu-cli-mcp
description: Use local aily-mcp and aily-doc wrappers to access Feishu docs and sheets through lark-cli. Use when the user asks to search Feishu docs, create/update Feishu docs, create/write/read spreadsheets, or says aily-mcp / aily-doc / MCP 对接 / 文档搜索 / 表格写入.
---

# Feishu CLI MCP

This skill standardizes Feishu access behind two local commands:

- `aily-doc`
- `aily-mcp`

Both are wrappers over `lark-cli`, so they reuse your existing Feishu CLI login instead of managing tokens separately.

## Commands

### Search docs

```bash
aily-doc search-doc --query "季度报告" -o results.json
```

### Create a doc

```bash
aily-doc create-doc --title "标题" --input /abs/path/to/draft.md
```

### Generic MCP-style calls

```bash
aily-mcp servers
aily-mcp tools -s docs
aily-mcp call -s docs -t search-doc -p '{"query":"季度报告"}'
aily-mcp call -s sheets -t create-sheet -p '{"title":"日报表","headers":["日期","杯量"]}'
```

## Current Servers

- `docs`
  - `search-doc`
  - `create-doc`
  - `update-doc`
- `sheets`
  - `create-sheet`
  - `write-sheet`
  - `append-sheet`
  - `read-sheet`

## Important Notes

- `aily-doc search-doc` depends on Feishu scope `search:docs:read`.
- If search returns `missing required scope(s): search:docs:read`, re-run:

```bash
lark-cli auth login --scope "search:docs:read"
```

- These wrappers live in the workspace source directory and are linked into `~/bin`, which is already on PATH.
