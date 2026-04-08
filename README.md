# Vibe Coding Workspace

个人 AI 协作工作区 — 数据分析、播客、学习系统、创意项目的统一基地。

## 目录结构 Directory Structure

```
.
├── experiments-实验/          # AB 实验与效果分析
│   ├── newcust-pricing-0119-新客涨价/   # 新客首杯涨价实验
│   ├── oldcust-pricing-0212-老客涨价/   # 老客三组涨价实验
│   ├── pricing-0311-涨价/               # 0311 涨价实验 + 子群交叉
│   ├── share-the-luck-分享有礼/         # Share The Luck 裂变活动
│   ├── coffee-pass-咖啡券/              # Coffee Pass 卖券复盘
│   ├── share-popup-0312-弹层实验/       # 弹层 AB 实验
│   ├── h5-delayed-login-延迟登录/       # H5 延迟登录效果
│   └── task-activity-0329-任务活动/     # 任务活动实验规则
│
├── operations-运营分析/       # 日常运营分析与策略
│   ├── daily-report-日报/               # 日报（含归因/天气）
│   ├── weekly-report-周报/              # 经营周报
│   ├── user-segmentation-用户分层/      # RFM / 生命周期分层
│   ├── user-ops-用户运营/               # 提频诊断 / 周末发券
│   ├── store-analysis-门店分析/         # 单店报告 / 合作邮件
│   ├── new-customer-retention-新客留存/ # 新客复购 / 留存提升
│   ├── frequency-boost-提频/            # 四象限分层 / 提频任务
│   ├── strategy-log-策略日志/           # 策略台账 / 动作日志
│   ├── task-config-任务活动配置/        # 任务活动配置手册
│   ├── hourly-analysis-分时段分析/      # 分时段订单分析
│   ├── methodology-方法论/              # 分析哲学 / SQL 总结
│   └── output-产出/                     # PPTX 等构建产出
│
├── podcast-播客/              # 播客生态
│   ├── ai-briefing-递归大师/            # AI 日报播客 pipeline
│   ├── viz-tool-可视化工具/             # 播客可视化（小宇宙→HTML）
│   ├── miniprogram-小程序/              # 微信小程序（原生版）
│   ├── viz-miniprogram-轻量小程序/      # 轻量版小程序（webview）
│   ├── screenshots-截图/                # UI 截图素材
│   └── assets-素材/                     # 头像等资源
│
├── knowledge-知识库/          # 跨项目知识、阅读与资料系统
│   ├── obsidian-知识图谱/               # Obsidian KnowledgeOS 内容迁入
│   ├── calibre-阅读资料/                # Calibre 可版本化导出内容
│   ├── sql-资料库/                      # 桌面 SQL 资料归档
│   └── reference-参考归档/              # 转录、说明、临时资料归档
│
├── imports-外部导入-staging/  # 外部目录导入承接区
│   ├── desktop-桌面导入/                # 桌面副本、未定类内容
│   ├── external-repos-外部仓库/         # 原始仓库归档与元数据
│   └── private-configs-私有配置/        # 移出的 project.private / 本地配置
│
├── learning-学习/             # 学习系统
│   ├── engine-引擎/                     # 学习引擎（消化→播客 + skill 演进）
│   ├── english-英语/                    # 宝宝英语日课 podcast pipeline
│   └── research-研究/                   # 学习理论与桌面学习资料
│
├── life-os-生活系统/          # 个人精力管理
│   ├── index.md                         # 索引
│   ├── runbook.md                       # 每日/每周 SOP
│   ├── setup-guide.md                   # 安装说明
│   ├── skill-pack.md                    # 角色协议（Alfred/Rem/Tyrion）
│   ├── tools-工具/                      # 自动周报 / 风险预警
│   └── reviews-复盘/                    # 周复盘 HTML 样例
│
├── creative-创意/             # 创意与独立项目
│   ├── yijing-易经/                     # 64 卦静态站
│   ├── sugarscape-糖景/                 # NetLogo 财富模拟
│   ├── openclaw-龙虾/                   # OpenClaw 大赛（PPT/演讲/Demo）
│   ├── fish-book-鱼不存在/              # 读书笔记
│   ├── photos-相册/                     # 家庭相册
│   ├── growth-tracker-增长追踪/         # Next.js 增长追踪 App
│   ├── member-mall-会员商城小程序/      # 桌面导入的小程序项目
│   ├── parenting-tracker-育儿追踪/      # 桌面导入的育儿追踪原型
│   ├── nikedemo-耐克小程序/             # 桌面导入的小程序 demo
│   └── music-learning-音乐学习/         # 音乐学习 App（已合并 piano-learning）
│
├── tools-工具/                # 工具与基础设施
│   ├── ppt-幻灯片/                      # PPT 生成（python-pptx / 讯飞）
│   ├── feishu-bot-飞书机器人/           # 飞书机器人"韩立"
│   ├── feishu-飞书/                     # 飞书文档发布工具
│   ├── notion-skill-Notion技能/         # Notion 辅助脚本
│   ├── uni-通用/                        # 通用小工具
│   ├── cloudwork-云端Claude/            # 云端 Telegram + Claude 工作空间
│   ├── bedding-inventory-床品库存应用/   # 桌面导入的库存工具
│   ├── inventory-forecast-库存预测/      # 桌面导入的库存预测系统
│   ├── restock-system-补货系统/          # 桌面导入的补货系统
│   ├── stock-analyzer-库存分析/          # 桌面导入的库存分析工具
│   ├── xiaohongshu-notes-collector-小红书采集/ # 桌面导入的采集工具
│   ├── xiaohongshu-crawler-小红书爬虫/   # 桌面导入的爬虫项目
│   └── skills-技能包/                   # 打包的 .skill 文件
│
├── libs-公共库/               # 跨项目公共模块（待抽取）
│   ├── cyberdata/                       # CyberData API client
│   └── ...
│
├── .claude/                   # Claude 工作区配置
├── .agents/                   # Agent Skills
└── VIBECODING_GLOBAL_RULES.md # 全局规范
```

## 根目录配置文件说明 Root Config Files（勿删 DO NOT DELETE）

| 文件/文件夹 File | 用途 Purpose | 说明 Note |
|---|---|---|
| `.agents/` | AI 技能包 Agent Skills | Cursor/Codex 自动读取，含 claude-to-im 桥接、前端设计等技能 |
| `.claude/` | Claude 配置 Claude Config | Claude Code 的权限设置、技能定义、会话记忆，删了 Claude 会丢配置 |
| `.gitignore` | Git 忽略规则 Git Ignore Rules | 定义哪些文件不提交（数据文件、密钥、node_modules 等），删了会导致敏感文件误提交 |
| `README.md` | 项目说明首页 Project Homepage | 你正在看的这个文件，整个工作区的导航地图 |
| `requirements.txt` | Python 依赖清单 Python Dependencies | `pip install -r requirements.txt` 一键安装所有公共 Python 库 |
| `VIBECODING_GLOBAL_RULES.md` | 全局规范 Global Rules | 所有 AI 模型遵守的顶层规则（链接规范、文档结构、合并规则等） |

## 公共依赖 Dependencies

- **Python**: requests, pandas, openpyxl, matplotlib, scipy, jinja2, python-pptx, edge-tts, lark-oapi
- **Node**: axios, cheerio, playwright

## 约定 Conventions

- 目录采用 `english-中文` 双语命名
- Python 脚本使用 `os.path.dirname(os.path.abspath(__file__))` 获取脚本所在目录，避免硬编码绝对路径
- 凭证统一走 `~/.claude/skills/cyberdata-query/auth.json` 或 `.env`，禁止硬编码在源码中
- 数据文件（.csv, .xlsx）通过 `.gitignore` 排除，不入 Git
- 知识库、阅读库、桌面导入内容优先进入 `knowledge-知识库/` 与 `imports-外部导入-staging/`，避免直接污染业务代码目录
- 外部项目并入主仓库时必须移除嵌套 `.git`、`node_modules`、日志、数据库、私有配置
- 详见 `VIBECODING_GLOBAL_RULES.md`
