# 外部目录迁移映射

## 已纳入 Vibe coding 的目录

| 原路径 | 处理方式 | 新位置 |
|--------|----------|--------|
| `/Users/xiaoxiao/Desktop/bedding-inventory-app` | 已迁入 | `tools-工具/bedding-inventory-床品库存应用/app/` |
| `/Users/xiaoxiao/Desktop/inventory-forecast-system` | 已迁入 | `tools-工具/inventory-forecast-库存预测/app/` |
| `/Users/xiaoxiao/Desktop/补货系统` | 已迁入 | `tools-工具/restock-system-补货系统/app/` |
| `/Users/xiaoxiao/Desktop/stock_analyzer` | 已迁入 | `tools-工具/stock-analyzer-库存分析/app/` |
| `/Users/xiaoxiao/Desktop/xiaohongshu-notes-collector` | 已迁入 | `tools-工具/xiaohongshu-notes-collector-小红书采集/app/` |
| `/Users/xiaoxiao/Desktop/member-mall-miniprogram` | 已迁入 | `creative-创意/member-mall-会员商城小程序/main/` |
| `/Users/xiaoxiao/Desktop/parenting-tracker` | 已迁入 | `creative-创意/parenting-tracker-育儿追踪/app/` |
| `/Users/xiaoxiao/Desktop/编程/nikedemo` | 已迁入 | `creative-创意/nikedemo-耐克小程序/app/` |
| `/Users/xiaoxiao/Desktop/编程/xiaohongshu-crawler` | 已迁入 | `tools-工具/xiaohongshu-crawler-小红书爬虫/app/` |
| `/Users/xiaoxiao/Desktop/sql` | 已迁入 | `knowledge-知识库/sql-资料库/desktop-sql-桌面SQL/` |
| `/Users/xiaoxiao/Desktop/podcast_transcripts` | 已迁入 | `podcast-播客/archive-transcripts-转录归档/desktop-podcast-transcripts/` |
| `/Users/xiaoxiao/Desktop/实验报告` | 已迁入 | `experiments-实验/archive-历史报告-桌面导入/desktop-实验报告/` |
| `/Users/xiaoxiao/Desktop/任务配置后台理解` | 已迁入 | `operations-运营分析/task-config-任务活动配置/reference-参考归档-桌面导入/任务配置后台理解/` |
| `/Users/xiaoxiao/Desktop/瑞幸后台配置存档` | 已迁入 | `operations-运营分析/task-config-任务活动配置/reference-参考归档-桌面导入/瑞幸后台配置存档/` |
| `/Users/xiaoxiao/Desktop/瑞幸ppt学习文件` | 已迁入 | `learning-学习/research-研究/desktop-study-桌面学习资料/瑞幸ppt学习文件/` |
| `/Users/xiaoxiao/WeChatProjects/miniprogram-1` | 已迁入 | `podcast-播客/wechat-projects-微信项目/miniprogram-1/` |
| `/Users/xiaoxiao/WeChatProjects/miniprogram-2` | 已迁入 | `podcast-播客/wechat-projects-微信项目/miniprogram-2/` |
| `/Users/xiaoxiao/cloudwork` | 清洁版迁入 + 原始仓库存档 | `tools-工具/cloudwork-云端Claude/` 与 `imports-外部导入-staging/external-repos-外部仓库/cloudwork-原始仓库/` |
| `/Users/xiaoxiao/piano-learning` | 已合并到现有音乐项目，原仓库存档 | `creative-创意/music-learning-音乐学习/` 与 `imports-外部导入-staging/external-repos-外部仓库/piano-learning-原始仓库/` |
| `/Users/xiaoxiao/Obsidian/KnowledgeOS` | 内容迁入 | `knowledge-知识库/obsidian-知识图谱/KnowledgeOS/` |
| `/Users/xiaoxiao/Calibre Library` | 只导入可版本化内容 | `knowledge-知识库/calibre-阅读资料/library-export/` |

## 被保留在原位置的目录

| 原路径 | 原因 |
|--------|------|
| `/Users/xiaoxiao/Obsidian/.obsidian` 与根目录草稿文件 | 属于 Obsidian 应用配置与个人草稿，不适合直接纳入主仓库 |
| `/Users/xiaoxiao/Calibre Library/metadata.db`、`.calnotes/` | 属于 Calibre 应用状态，不适合直接纳入主仓库 |
| `/Users/xiaoxiao/cloudbase-framework` | 当前只有日志目录，不具备项目迁移价值 |
| `/Users/xiaoxiao/Desktop/.claude`、`.playwright-mcp`、`node_modules` | 属于本地工具运行态，不应进入主仓库 |

## 已执行的清理

- 移除了导入项目中的嵌套 `.git`
- 移出了所有 `project.private.config.json` 到 `private-configs-私有配置/`
- 将 `cloudwork` 的旧计划文件移到 `external-repos-外部仓库/cloudwork-meta-归档/`
- 将 `piano-learning` 合并到现有 `music-learning-音乐学习/`
