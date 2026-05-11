---
name: feishu-visual-report
description: |
  Create polished visual Feishu/Lark analysis reports from confirmed analysis data,
  including executive summary cards, metric tables, chart assets, local Markdown
  drafts, Feishu doc publishing, and optional Airy beautification handoff.
  Use when the user wants a 飞书文档 or 飞书表格 output to be more visual,
  图文结合, 好看, less plain, suitable for internal reporting, or based on a
  reference sample.
---

# Feishu Visual Report

Use this skill when analysis is already done or the user has provided confirmed data, and the task is to turn it into a polished Feishu-facing report.

This skill does not replace data querying or metric validation. First confirm data source, period, audience, and decision scenario when they are missing; then build the visual report.

## Default Decision

- Prefer a reusable local report draft plus chart assets when the user wants consistency across future reports.
- Use Airy handoff when the user explicitly wants a more designed visual style, or when the current Feishu publisher cannot insert native image/table blocks.
- Use direct Feishu doc publishing for fast internal drafts where text structure is more important than native visual blocks.

## Workflow

1. Confirm or reuse the analysis assumptions: data source, period, audience, experiment groups, and internal/external usage.
2. Write a local Markdown report under the project output directory, not the workspace root.
3. Convert dense tables into:
   - conclusion card: one sentence verdict
   - metric cards: 3-6 key numbers
   - comparison chart: bar or funnel chart
   - diagnostic section: which funnel layer moved or failed to move
4. Generate chart image assets with `scripts/build_visual_report_assets.py` when numeric data is available.
5. Publish the Markdown draft through `feishu-doc-publisher` or `lark-cli docs +create`.
6. Insert local chart images with `lark-cli docs +media-insert` when the report needs real图文结合 output.
7. Optionally hand off the doc link and chart assets to `feishu-analysis-pipeline` / Airy for further beautification.
8. Return the Feishu link, local draft path, and chart asset paths.

## Report Structure

Use this structure for experiment or campaign reviews:

1. 结论卡片：一句话说明是否有效，以及卡在哪个环节。
2. 数据总览：只放原始数字，不加解读。
3. 漏斗诊断：触达、来访、曝光、领券、核销、下单、实收逐层说明。
4. 图表说明：每张图只回答一个问题。
5. 原因总结：用业务语言解释为什么没动或为什么有效。
6. 建议：给出明确动作，不写模糊建议。

For internal reporting, use Chinese as the primary language. Add English only for field names or when the target table/doc is bilingual.

## Visual Rules

- Use 1 headline verdict, not a long opening paragraph.
- Use no more than 6 key metrics in the top card area.
- Use bar charts for A/B comparison, line charts for daily trend, and funnel charts for lifecycle drop-off.
- Label charts in business language: “来访率” is better than “visit_rate”.
- Avoid decorative charts. Every visual must support a decision.
- When a difference is not statistically significant, write “方向不显著”, not “提升/下降带来收益”.

## Scripts

Generate a visual-report bundle from a small JSON spec:

```bash
python3 .agents/skills/feishu-visual-report/scripts/build_visual_report_assets.py \
  --spec /abs/path/to/report_spec.json \
  --out-dir /abs/path/to/output_dir
```

The script creates:

- `report.md`: Markdown draft
- `charts/*.png`: chart assets for Airy or manual Feishu insertion
- `airy_brief.md`: beautification brief for Airy

See `references/spec-format.md` for the JSON format.

## Integration Notes

- Current `feishu-doc-publisher` supports headings, paragraphs, bullets, and ordered lists. For Markdown tables, prefer `lark-cli docs +create`.
- To insert native image blocks, use `lark-cli docs +media-insert` from the image directory and pass a relative image path, for example:
  `lark-cli docs +media-insert --doc <doc_url> --file ./visit_rate.png --caption "图1：来访率对比" --align center`
- For further visual polish, publish the structured draft first, insert chart assets, then hand off the Feishu link to Airy.
- When a user provides a reference sample, capture its layout rules in `references/style-notes.md` before generating the report.
