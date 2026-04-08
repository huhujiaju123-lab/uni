---
name: feishu-analysis-pipeline
description: Publish data-analysis outputs as Feishu docs and automatically hand them off to Airy for beautified report generation. Use when the user wants analysis results turned into a 飞书文档, sent to Airy / 艾里, or the whole “分析结果 -> 飞书文档 -> Airy 美化” chain automated.
---

# Feishu Analysis Pipeline

Use this skill when the user wants the analysis result to land directly in Feishu instead of stopping at local markdown or plain chat output.

## What This Skill Does

1. Publishes a local markdown draft as a Feishu doc.
2. Sends the Feishu link plus a beautification brief to Airy.
3. Returns the published link and Airy handoff status.

Default output is a Feishu doc. When the source material is table-heavy, keep the raw table in the markdown/doc and let Airy turn it into the polished report.

## Workflow

1. Make sure the analysis content already exists locally as a markdown file.
2. Run `scripts/publish_and_handoff.py`.
3. If `config.local.json` has an Airy target, the script sends the handoff automatically.
4. Return the doc link and whether Airy was notified.

## Command

```bash
python3 scripts/publish_and_handoff.py \
  --title "文档标题" \
  --input /abs/path/to/draft.md
```

Useful flags:

- `--skip-airy`: only publish the Feishu doc
- `--airy-chat-id xxx`: override Airy target for this run
- `--resource-url https://...`: skip publish and hand off an existing Feishu doc/sheet link
- `--config /abs/path/to/config.local.json`: use a non-default config

## Config

Default config path:

```text
config.local.json
```

Create it by copying `config.example.json` and filling:

- `airy_chat_id`
- `airy_receive_id_type` (`chat_id` by default)
- optional custom `airy_prompt_template`

## Notes

- Default Feishu app credentials reuse the existing internal app used elsewhere in this workspace.
- If Airy target config is missing, the script still publishes the doc and reports `airy_status=skipped`.
- Use this skill after the analysis is finished, not for data querying itself.
