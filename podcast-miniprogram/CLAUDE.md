# podcast-miniprogram 项目记忆

## 项目定位

播客可视化小程序 — 原生渲染版。与 `podcast-tool/`（Web 版）共享数据模型和后端逻辑，但 UI 完全用小程序原生组件重写。

## 与 Web 版的关系

| 维度 | Web 版 (podcast-tool/) | 小程序版 (本项目) |
|------|----------------------|------------------|
| 前端 | Jinja2 → 单文件 HTML | 微信小程序原生组件 |
| 后端 | Flask + Gunicorn | 微信云开发（云函数） |
| 数据库 | 文件系统 (output/) | 云数据库 |
| 部署 | 腾讯云 134.175.228.73:8081 | 微信云托管 |
| 数据模型 | episode.json | **完全一致** |
| AI 分析 | 通义千问 qwen-plus | **完全一致** |
| 转录 | Deepgram Nova-2 | **完全一致** |

## 共享文档（symlinks in docs/）

- `docs/ARCHITECTURE.md` → 数据模型定义（PodcastEpisode 接口）— **两端的契约**
- `docs/PRECOMPUTE_STRATEGY.md` → 降本策略（faster-whisper 等）
- `docs/research/` → 用户需求研究（4 份文档，需求优先级）
- `docs/WEB_README.md` → Web 版说明

## 技术栈

- 小程序框架：微信原生（非 uni-app/Taro）
- 云开发环境 ID：待配置
- 云函数运行时：Node.js 16+
- 云数据库：MongoDB（微信云开发内置）
- AI：通义千问 qwen-plus（dashscope API）
- 转录：Deepgram Nova-2

## 数据模型（共享契约）

episode.json 结构定义在 `docs/ARCHITECTURE.md` 第二章。核心字段：

```
meta          → 播客名称、期号、标题、封面、时长
participants  → 主持人/嘉宾
sections[]    → 章节（key_points_grouped + diagram + quotes + stories）
content_overview → 内容组块 + 逻辑连线
arguments     → 核心观点（论据类型 + 强度）
key_concepts  → 关键概念词典
mind_map      → 思维导图（树状结构）
quiz          → 互动自测题
core_quotes   → 全集精选金句
```

**任何对数据模型的修改必须同步两端。**

## 云数据库集合设计

| 集合 | 说明 | 索引 |
|------|------|------|
| episodes | 单集完整数据（= episode.json） | episode_id, podcast_name, created_at |
| tasks | 处理任务队列 | task_id, status, created_at |
| user_favorites | 用户收藏的金句 | _openid, episode_id |
| user_history | 用户浏览历史 | _openid, episode_id, last_read_at |

## 云函数清单

| 函数 | 触发方式 | 超时 | 说明 |
|------|---------|------|------|
| processEpisode | 小程序调用 | 600s（异步） | fetch → transcribe → analyze → 存入云数据库 |
| getEpisode | 小程序调用 | 5s | 按 ID 读取单集 |
| listEpisodes | 小程序调用 | 5s | 列表/搜索/历史 |

## 页面结构

| 页面 | 路径 | 说明 |
|------|------|------|
| 首页 | pages/index | 精选列表 + 搜索/粘贴链接 |
| 内容页 | pages/episode | **核心** — 原生渲染可视化（章节/观点/金句/图表/导图/自测） |
| 进度页 | pages/progress | 处理进度（4 步骤动画） |
| 我的 | pages/profile | 收藏金句 + 浏览历史 |

## 组件清单

| 组件 | 说明 | 对应 Web 版模块 |
|------|------|----------------|
| preview-card | 30 秒听前预览 | Web 版待做（Phase 1） |
| section-card | 章节内容卡片 | base.html.j2 各 section |
| quote-card | 金句卡片（可收藏） | quote_card 模板 |
| mind-map | 思维导图（canvas 或 SVG） | mind-map section |
| diagram | 内联图表（9 种类型） | diagram 渲染 |
| quiz | 互动自测 | quiz section |
| share-poster | 分享海报生成 | Web 版待做（Phase 1） |
| episode-list | 集列表卡片 | index.html 列表 |

## 同步开发约定

1. **数据模型变更** → 先改 `docs/ARCHITECTURE.md`，再同步两端实现
2. **AI Prompt 变更** → 同步 `podcast-tool/prompts/extract_content.md` 和云函数中的 prompt
3. **新功能优先级** → 参考 `docs/research/04-feature-recommendations.md`
4. **版本号** → 小程序独立版本号，CHANGELOG 记录与 Web 版的对应关系

## 开发注意事项

- 小程序 AppID：wx8455d9c3b3e70865
- 云函数异步调用最长 20 分钟，processEpisode 需用异步模式
- 云数据库单条记录上限 16MB，episode.json 通常 < 100KB，无问题
- 图片域名需在小程序后台配置白名单（小宇宙封面 CDN）
- 分享海报用 canvas 绘制，不依赖 html2canvas
