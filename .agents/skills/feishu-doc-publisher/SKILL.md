---
name: feishu-doc-publisher
description: Create and publish Feishu/Lark docx documents from draft content, then set the doc to tenant-readable and optionally open it. Use when the user asks to write, publish, create, open, or update a 飞书文档 / Feishu doc / Lark doc in the Vibe coding workspace, especially when content should be turned into a shareable online document rather than a local markdown file.
---

# Feishu Doc Publisher

Use this skill when the user wants a Feishu document created from content in the current workspace.

## Workflow

1. Check whether the user already provided the content.
2. If needed, draft or update a local markdown file first.
3. Run `scripts/publish_feishu_doc.py` with a title and the markdown file path.
4. Return the Feishu link.
5. If the user asks to open it, run `open <url>`.

## Defaults

- Default to project-local content in `/Users/xiaoxiao/Vibe coding`.
- Default sharing mode is organization-only link access:
  - `link_share_entity = tenant_readable`
  - `security_entity = anyone_can_view`
- Do not make docs public to the internet unless the user explicitly asks.
- If a document already exists and the user asks to revise it, prefer creating a new version only when patching the existing one is more work than rewriting.

## Command

Use:

```bash
python3 scripts/publish_feishu_doc.py --title "文档标题" --input /abs/path/to/file.md
```

Optional flags:

- `--open`: open the created document in the local browser
- `--no-permission-update`: skip the tenant-readable permission patch

## Content Format

The script supports a lean markdown subset:

- `#` and `##` headings
- plain paragraphs
- `- ` bullet lists
- `1. ` ordered lists

Keep markdown simple. Avoid tables, nested lists, and complex formatting unless you are willing to extend the script.

## Files

- Script: `scripts/publish_feishu_doc.py`
- Reference: `references/permissions.md`

Read the reference only if you need to troubleshoot Feishu permission behavior.
