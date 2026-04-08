# Findings & Decisions

## Requirements
- 将 `/Users/xiaoxiao` 下 7 个目录纳入 `/Users/xiaoxiao/Vibe coding` 的新架构。
- 不是简单堆进去，而是按现有一级目录重新整理，必要时新增合理层级。
- 将独立 Git 仓库合并进 `Vibe coding` 主仓库管理。
- 处理知识库、阅读库、桌面资料、代码项目之间的边界。
- 清理 `.git`、日志、缓存、数据库、`node_modules`、私有配置等历史残留。
- 更新索引文档与全局规则，让后续更多项目可继续纳入。

## Research Findings
- `/Users/xiaoxiao/Obsidian` 的核心是 `KnowledgeOS/`，包含 `00-Inbox 收件箱` 到 `05-Outputs 产出`、`_MOC 导航地图`、`_Templates 模板`，属于知识图谱而非代码项目。
- `/Users/xiaoxiao/Obsidian` 同时存在根级 `.obsidian/` 和 `KnowledgeOS/.obsidian/`，说明有双 Vault/双配置边界，需要只保留一个主配置入口。
- `/Users/xiaoxiao/Calibre Library` 是 Calibre 托管的电子书库，包含 `metadata.db`、`.calnotes/notes.db` 和书籍目录，不适合作为代码项目整体纳入。
- `/Users/xiaoxiao/Desktop` 是混合工作台，既有代码仓库（如 `bedding-inventory-app/`、`member-mall-miniprogram/`、`补货系统/`），也有 `sql/`、`实验报告/`、PPT、截图、转录、`node_modules/` 等资料与残留。
- `/Users/xiaoxiao/WeChatProjects` 包含 `miniprogram-1/` 与 `miniprogram-2/`，其中 `miniprogram-2/README.md` 明确是微信云开发 quickstart。
- `/Users/xiaoxiao/cloudbase-framework` 几乎只有 `logs/`，不具备项目迁移价值。
- `/Users/xiaoxiao/piano-learning` 是独立 Git 项目，主文件 `index.html` 与现有 `creative-创意/music-learning-音乐学习/index.html` 的头部内容一致，极可能同源或重复。
- `/Users/xiaoxiao/cloudwork` 是完整的 Python 工具型项目，定位为“云端 Claude Code + Telegram 控制”，结构成熟，适合并入 `tools-工具/`。
- `cloudwork/.gitignore` 已明确排除了 `config/.env`、`logs/`、`data/*.json`、`workspace/*` 等运行态内容，可作为导入清理依据。
- `WeChatProjects/miniprogram-1/project.config.json` 含真实 `appid`，导入前要决定是否保留或改为私有配置。
- 实施后，`Vibe coding` 中已不存在嵌套 `.git/config` 与项目目录内的 `project.private.config.json`。
- `cloudwork` 最终采用“清洁版进入正式目录，原始仓库存入 staging”的模式，兼顾可运行性与可追溯性。
- `Desktop` 仍保留 `.claude`、`.playwright-mcp`、`node_modules` 等本地运行残留，属于刻意不并入主仓库的内容。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 新增 `knowledge-知识库/` | 承接 Obsidian、Calibre、SQL 资料、参考归档，避免污染代码型目录 |
| 新增 `imports-外部导入-staging/` | 先把 Desktop 和外部项目接入一个承接层，再分类并入正式结构 |
| `Obsidian` 迁入内容，不迁 `.obsidian` 默认配置 | Obsidian 配置是个人 UI/插件状态，适合局部保留或忽略 |
| `Calibre Library` 不直接整体纳入托管态数据库 | `metadata.db` 和 `.calnotes` 是应用状态，不适合直接纳入代码仓库 |
| `cloudwork` -> `tools-工具/cloudwork-云端Claude/` | 功能定位与工具型产品一致 |
| `WeChatProjects` -> `podcast-播客/wechat-projects-微信项目/` | 现有架构已经有微信小程序相关目录，便于统一导航 |
| `Desktop` 按“代码/知识/产出/残留”拆分导入 | 避免把桌面临时性结构原封不动带进新架构 |
| 小程序 `project.private.config.json` 统一移入 staging | 避免把本地私有开发配置散落到正式项目目录 |
| `music-learning-音乐学习` 吸收 `piano-learning` | 避免两个同源音乐项目并存 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| 多次误用 ReadFile 直接读目录 | 改为使用 `ls`/`Glob` 获取目录结构，再针对具体文件读取 |
| 外部项目类型混杂，无法一次性整体迁移 | 采用 staged import：先建立 `imports-外部导入-staging/`，再按一级目录拆分并入 |

## Resources
- `/Users/xiaoxiao/Obsidian/KnowledgeOS/`
- `/Users/xiaoxiao/Calibre Library/`
- `/Users/xiaoxiao/Desktop/`
- `/Users/xiaoxiao/WeChatProjects/`
- `/Users/xiaoxiao/cloudbase-framework/`
- `/Users/xiaoxiao/piano-learning/`
- `/Users/xiaoxiao/cloudwork/`
- `/Users/xiaoxiao/Vibe coding/README.md`
- `/Users/xiaoxiao/Vibe coding/.gitignore`
- `/Users/xiaoxiao/Vibe coding/VIBECODING_GLOBAL_RULES.md`

## Visual/Browser Findings
- 目录观察显示 `Desktop` 含多种项目形态：Python/Streamlit、微信小程序、浏览器插件、SQL 脚本、实验报告、PPT 学习资料和运行残留。
- `piano-learning` 与现有 `music-learning-音乐学习` 首屏内容一致，需优先去重，避免把同一项目并入两份。
