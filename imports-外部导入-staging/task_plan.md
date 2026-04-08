# Task Plan: Merge Xiaoxiao Folders Into Vibe Coding

## Goal
将 `/Users/xiaoxiao` 下的外部目录并入 `/Users/xiaoxiao/Vibe coding`，形成统一的代码、知识、资料与运行时边界清晰的总架构，并完成目录迁移、去重、Git 清理和索引更新。

## Current Phase
Phase 5

## Phases

### Phase 1: Requirements & Discovery
- [x] Understand user intent
- [x] Identify constraints and requirements
- [x] Document findings in findings.md
- **Status:** complete

### Phase 2: Structure & Mapping
- [x] Define technical approach
- [x] Create import staging and knowledge layer
- [x] Map each external directory to a target location
- **Status:** complete

### Phase 3: Migration & Cleanup
- [x] Import code projects and knowledge/content in batches
- [x] Remove nested `.git`, logs, caches, and runtime data
- [x] Deduplicate overlapping projects and archives
- **Status:** complete

### Phase 4: Indexes & Rules
- [x] Update top-level indexes and routing docs
- [x] Expand `.gitignore` for imported systems
- [x] Update global rules for knowledge/content boundaries
- **Status:** complete

### Phase 5: Verification & Delivery
- [x] Verify resulting structure
- [x] Review residual risks and manual follow-ups
- [ ] Deliver migration summary to user
- **Status:** in_progress

## Key Questions
1. 哪些外部目录属于“代码项目”，哪些属于“知识/资料系统”？
2. `piano-learning` 是否与现有 `creative-创意/music-learning-音乐学习/` 同源？
3. `Calibre Library` 是否应完整迁入，还是只迁入可版本化的内容导出？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 新增 `knowledge-知识库/` 一级目录 | `Obsidian` 与 `Calibre Library` 都是内容系统，不适合塞入代码型目录 |
| 新增 `imports-外部导入-staging/` 承接区 | 桌面混合内容较多，需要先分拣再并入正式架构 |
| 所有独立仓库并入主仓库时去除嵌套 `.git` | 用户明确要求合并进 `Vibe coding` 主仓库 |
| `cloudwork` 落到 `tools-工具/` | 它是可部署的工具型产品，不是业务实验项目 |
| `WeChatProjects` 优先落到 `podcast-播客/` 的微信项目承接区 | 现有架构里已经有多个小程序目录，便于统一管理 |
| `piano-learning` 先比对再决定合并/并列 | 与现有 `music-learning-音乐学习` 首页内容高度相似 |
| `cloudwork` 采用“双轨导入” | `tools-工具/` 保留清洁版，staging 保留原始仓库归档 |
| `Obsidian` 与 `Calibre` 只迁内容导出，不动原应用状态目录 | 避免直接破坏现有 Obsidian/Calibre 使用环境 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| 用 ReadFile 读取目录路径时报错 “Path is a directory” | 1 | 改为用 `ls`/`Glob` 获取目录内容，再读具体文件 |

## Notes
- 外部目录中存在大量 `.git`、日志、数据库、`node_modules`、本地配置，需要统一清理。
- `Desktop` 不能整体迁移，必须拆分为代码项目、报告资料和运行残留三类。
- 仍保留在外部原路径的主要是 Obsidian/Calibre 的应用状态目录，以及 Desktop 的本地工具运行残留。
