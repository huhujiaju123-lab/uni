# daily-report-日报

Lucky US 日报项目目录，按“脚本 / 配置 / SQL / 产出 / 会话备忘”分层整理。

## 目录结构

```text
daily-report-日报/
├── README.md
├── scripts-脚本/
│   ├── daily_report.py
│   ├── send_to_feishu.py
│   ├── run_daily_feishu.sh
│   ├── generate_attribution_html.py
│   └── generate_daily_report_v2.py
├── sql-查询/
│   └── 日报.sql
├── config-配置/
│   └── feishu_config.json
├── outputs-输出/
│   ├── reports-报告/
│   └── data-数据快照/
└── session-notes-会话备忘/
```

## 使用方式

生成 Markdown 日报：

```bash
python3 scripts-脚本/daily_report.py
```

飞书推送：

```bash
bash scripts-脚本/run_daily_feishu.sh --dry-run
bash scripts-脚本/run_daily_feishu.sh
```

归因 HTML：

```bash
python3 scripts-脚本/generate_attribution_html.py
python3 scripts-脚本/generate_daily_report_v2.py
```

## 约定

- 可执行脚本统一放在 `scripts-脚本/`
- 凭证与本地配置统一放在 `config-配置/`
- 查询 SQL 模板统一放在 `sql-查询/`
- 生成结果统一写入 `outputs-输出/`
- 会话过程与续接备忘统一放在 `session-notes-会话备忘/`
