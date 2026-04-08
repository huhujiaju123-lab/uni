# 递归大师 — AI Builders Daily

> 每日自动化 AI 播客，面向 AI Builder 群体，8-10 分钟中文对话式播报。

## 项目概述

**产品定位**：让 AI Builder（数据分析 + 增长运营 + Vibe Coding 从业者）每天用 8-10 分钟沉浸式学习，跟上 AI 发展、理解背后原理、获得实践指引。

**核心角色**：
- **递归**（longcheng 阳光男声）— 好奇的年轻 Builder，快节奏提问，善用类比，40-100 字/段
- **大师**（longshu 知性男声）— 资深技术人，费曼式教学（类比→白话→定义），50-120 字/段

**收听地址**：
- RSS：`http://podcast.huhu.world/podcast/feed.xml`
- 小宇宙：搜索「递归大师」

---

## 全链路状态（2026-03-22）

| # | 环节 | 状态 | 说明 |
|---|------|------|------|
| 1 | Cron 定时 | ✅ | `0 0 * * *` CST，每天北京午夜触发 |
| 2 | Feed 拉取 | ✅ | 3 次重试 + 指数退避，稳定拿到 30+ 条推文 |
| 3 | LLM 生成 | ✅ | qwen-plus 规划 + qwen-max 脚本，40+ 段通过质量检查 |
| 4 | TTS 合成 | ✅ | CosyVoice 1.2x，longcheng + longshu |
| 5 | 上传+RSS | ✅ | on_server=True，本地文件操作，不依赖 sshpass |
| 6 | 飞书推送 | ✅ | 含质量报告 + 时长预警 |
| 7 | Web 服务 | ✅ | Gunicorn 端口 8081 |
| 8 | 域名 | ✅ | podcast.huhu.world，Caddy + HTTPS |
| 9 | RSS | ✅ | 自动更新，域名 podcast.huhu.world |
| 10 | 小宇宙 | ✅ | RSS 自动轮询（~7h 间隔）|

---

## Pipeline v2 架构

### 全链路流程图

```
GitHub Feeds (X + Podcasts)
        ↓
   [1] Fetch feeds — 3次重试 + 指数退避
        ↓
   [2] Pre-filter — 去噪音、按互动量加权排序
        ↓
   [3] Call 1: qwen-plus 话题规划
       四象限筛选 S/A/B/C，听众画像 AI Builder
        ↓
   [4] Call 2: qwen-max 脚本生成
       双人对话，人物介绍 + 术语解释 + 知识锚点
        ↓
   [5] 质量检查（不合格自动重试，最多2次）
       段数≥25 / 字数≥2500 / 说话比例 / AI套话 / 介绍标记
        ↓
   [6] CosyVoice TTS 合成
       1.2倍速，3次重试/段，Edge TTS 回退 + 可变停顿
        ↓
   [7] 上传服务器 + RSS 更新 + 飞书推送
        ↓
   [8] 小宇宙自动拉取 RSS
```

### 数据源

- **X/Twitter Feed**：follow-builders 项目，25+ AI Builder 推文
- **Podcast Feed**：follow-builders 项目，播客转录
- 来源：GitHub Raw JSON

---

## 内容质量体系

### 四象限分级

| 级别 | 段数 | 定位 | 示例 |
|------|------|------|------|
| S级 | 10-12段 | 核心突破、深度概念 | CoT、RAG、Scaling Laws、重要论文 |
| A级 | 4-6段 | 公司战略、行业变局 | 融资、合作、重大决策 |
| B级 | 2-3段 | 工具发布、功能更新 | 新特性、版本发布 |
| C级 | 跳过 | 跑分、AI末日论、八卦 | — |

选题规则：**1-2 个 S + 1-2 个 A + 1-2 个 B = 每集最多 5 个话题**

### S级话题深度展开模板

1. 引出（谁/发生了什么）
2. 行业背景说明
3. 概念拆解 + 类比
4. 技术原理（论文/模型设计）
5. **知识锚点**（记忆框架，如 "API = 点对点，协议 = 全网级"）
6. 现实影响
7. 行动建议

### 质量门禁

| 检查项 | 标准 |
|--------|------|
| 段数 | ≥25（理想 40-50）|
| 字数 | ≥2,500（理想 3,500+）|
| 说话比例 | 每人 25%-75% |
| AI 套话 | 14 条黑名单检测 |
| 介绍标记 | 人物/公司首次出现必须有背景 |
| 段落长度 | 单段 >200 字预警 |
| S级深度 | ≥10 段展开 |

**AI 套话黑名单**：让我们一起、值得注意、赋能、抓手、闭环、由此可见、不言而喻……（共 14 条）

**强制规则**：
- 人物/公司首次出现加背景介绍（标记："——" 或 "就是"）
- 专有名词前置解释（递归问→大师答格式）

---

## TTS 语音合成

### 发音预处理（5 类词典）

| 类别 | 条目数 | 示例 |
|------|--------|------|
| 人名音译 | 29 | Sam Altman → 山姆·奥特曼 |
| 缩写展开 | 33 | MCP → M C P，RLHF → R L H F |
| 产品名 | — | Claude Code → 克劳德 Code |
| 公司名 | — | Anthropic → 安索匹克 |
| 术语翻译 | — | fine-tuning → 微调 |

额外处理：
- 中英文边界自动插入空格（辅助 TTS 断句）
- 重复标点清理
- "'s" → "的"

### 合成引擎

**主引擎：CosyVoice**（DashScope SDK）

| 角色 | 音色 ID | 风格 |
|------|---------|------|
| 递归 | longcheng | 阳光男声 |
| 大师 | longshu | 知性男声 |

- 每段 3 次重试，指数退避（3s → 6s → 9s）
- 全局 1.2 倍速（ffmpeg atempo 滤镜）

**备用引擎：Edge TTS**（微软 Azure 异步）

| 角色 | 音色 | 语速 |
|------|------|------|
| 递归 | YunxiNeural | +26% |
| 大师 | YunyangNeural | +22% |

- 3 段一批，限速处理

### 可变停顿系统

| 场景 | 停顿时长 |
|------|----------|
| 话题切换 | 600ms |
| 说话人切换 | 300ms |
| 同一说话人 | 150ms |

**音频组装**：ffmpeg concat → 192kbps MP3

### 音色选型记录

测试了 5+ 种 CosyVoice 音色（voice-samples/ 目录），最终确定：
- longhua 女声 AI 感太强 ❌
- CosyVoice v2 API 返回 418 ❌
- **最终方案**：longcheng + longshu 双男声 ✅

---

## 基础设施

### 服务器

| 项目 | 详情 |
|------|------|
| 域名 | podcast.huhu.world |
| Web 服务 | Gunicorn，端口 8081 |
| 反代 | Caddy + HTTPS（Let's Encrypt）|
| 定时任务 | `0 0 * * *` CST（北京午夜 = 美东中午12点）|
| 日志 | `/opt/ai-podcast/logs/{DATE}.log` |
| 音频存放 | `/opt/ai-podcast/episodes/{DATE}.mp3` + `{DATE}.json` |

### 部署方式

- 非 git 部署，手动 scp/rsync
- 服务器端 cron 场景：检测 `/opt/ai-podcast` 存在后直接本地文件操作
- systemd 管理 Gunicorn 进程

### 小宇宙发布

- 播客名：「递归大师」
- RSS 自动对接，小宇宙轮询间隔约 7 小时
- 当前已发布 3 集

---

## 技术栈

| 层 | 技术 |
|-----|------|
| 内容源 | GitHub Raw（follow-builders feed）|
| 规划 LLM | 通义千问 qwen-plus |
| 脚本 LLM | 通义千问 qwen-max |
| TTS 主引擎 | CosyVoice（DashScope SDK）|
| TTS 备用 | Edge TTS（微软 Azure）|
| 音频处理 | ffmpeg |
| Web 服务 | Gunicorn + Caddy |
| 定时调度 | cron |
| 通知 | 飞书 Bot API |
| 分发 | RSS → 小宇宙 |
| 服务器 | 腾讯云 OpenCloudOS |
| 语言 | Python 3.9+ |

---

## 文件结构

```
ai-briefing/
├── daily_pipeline.py          # 主流水线脚本 v2（~1,175 行）
├── run_daily.sh               # cron 入口
├── test_pipeline.py           # 测试套件
├── cover.html                 # 播客封面（3000×3000px）
├── PROJECT.md                 # 本文件
│
├── podcast-v2.py              # 历史：手动脚本 + SSML
├── podcast-v3.py              # 历史：简化版 Edge TTS
├── podcast-script-2026-03-20.py  # 历史：v1 女声方案
│
├── podcast-script-*.txt       # 生成的对话脚本
├── meta-*.json                # 剧集元数据
├── ai-builders-daily-*.mp3    # 最终音频文件
├── *.html                     # 剧集页面
│
├── podcast-output/            # v1 音频片段
├── podcast-output-v2/         # v2 音频片段（SSML）
├── podcast-output-v3/         # v3 音频片段
├── podcast-output-2026-*/     # 按日期的音频片段
└── voice-samples/             # 音色测试样本
```

---

## 已发布剧集

| 集数 | 日期 | 标题 | 时长 | 段数 |
|------|------|------|------|------|
| EP01 | 2026-03-20 | AI Builders Daily — Claude Code Channels & Token Economics | ~10 min | 62 |
| EP02 | 2026-03-21 | 重构代理栈：当 RAG 退场，Agent OS 进场 | 7:44 | 48 |
| EP03 | 2026-03-22 | — | — | 42 |

---

## 版本演进

| 日期 | 版本 | 里程碑 |
|------|------|--------|
| 2026-03-20 | v1 | 首集发布，Edge TTS 女声方案 |
| 2026-03-20 | v1.1-v1.3 | 音色实验（SSML / 简化 / 双男声）|
| 2026-03-21 | **v2** | 内容质量优化 + CosyVoice 语音包升级 |
| 2026-03-21 | — | 小宇宙手动发布首批 2 集 |
| 2026-03-22 | v2.1 | Feed 重试机制 + 服务器端本地操作 |
| 2026-03-22 | — | 域名切换 podcast.huhu.world |

---

## 待办

- [ ] 飞书推送修复验证
- [ ] 小宇宙新集自动发布验证
- [ ] 清理历史调试文件（74.4 MB v2 音频、历史 output 目录）
- [ ] Pipeline 监控告警（失败时自动通知）
