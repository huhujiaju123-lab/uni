# Visual Report Spec Format

Use this JSON shape for `build_visual_report_assets.py`.

```json
{
  "title": "沉默31天首页塞券项目阶段复盘",
  "period": "2026-04-03 至 2026-04-11",
  "verdict": "没有看到明确正向效果，卡在来访启动环节。",
  "audience": "LKUSUG119131510753394688",
  "assumptions": [
    "实验组：用户 id 尾号 2、5",
    "对照组：用户 id 尾号 0、1、3、4、6、7、8、9"
  ],
  "metrics": [
    {"name": "实验组用户数", "value": 4140},
    {"name": "实验组来访率", "value": "3.45%"}
  ],
  "groups": [
    {"group": "实验组", "users": 4140, "visit_users": 143, "visit_rate": 0.0345, "order_users": 0, "order_rate": 0},
    {"group": "对照组", "users": 16693, "visit_users": 605, "visit_rate": 0.0362, "order_users": 0, "order_rate": 0}
  ],
  "diagnosis": [
    "来访率没有被拉动。",
    "下单链路没有形成有效样本。"
  ],
  "recommendations": [
    "不建议按当前口径放量。",
    "下一版改成站外触达 + 站内承接。"
  ]
}
```

Rules:

- `groups` is used for comparison charts.
- Rate fields should use decimals in JSON, such as `0.0345`, and will be displayed as percentages.
- Keep `diagnosis` and `recommendations` short and business-readable.
