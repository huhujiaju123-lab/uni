# 播客可视化工具 — 技术研究报告

> 研究日期：2026-02-26
> 目标：用户输入小宇宙播客链接 → 自动生成交互式可视化网页

---

## 1. 小宇宙平台研究

### 1.1 链接格式

| 类型 | 格式 | 示例 |
|------|------|------|
| 单集页面 | `https://www.xiaoyuzhoufm.com/episode/{episode_id}` | `/episode/674a16478d5d7e073a18b4cc` |
| 播客主页 | `https://www.xiaoyuzhoufm.com/podcast/{podcast_id}` | `/podcast/5e280fab418a84a046e7da72` |

**用户输入的是单集页面 URL**（`/episode/xxx`）是最直接的形式，也是工具的主要输入。

### 1.2 音频 URL 获取

**结论：可以通过页面 HTML 获取音频直链，无需官方 API。**

小宇宙单集页面包含标准 Open Graph 协议 meta 标签：

```html
<meta property="og:audio" content="https://media.xyzcdn.net/xxx.m4a" />
<meta property="og:title" content="播客标题" />
<meta property="og:description" content="节目描述" />
<meta property="og:image" content="https://fdfs.xmcdn.com/xxx.jpg" />
```

JSON-LD 结构化数据中也包含 `contentUrl` 字段，指向同一 CDN。

**音频 CDN 格式：**
```
https://media.xyzcdn.net/[文件标识符].m4a
```

**已验证可行性的开源工具：**
- `xyzfm-dlp`（Rust CLI）
- `xyz-dl`（Python）
- `xyzdownloader.xyz`（在线工具）

均通过解析 `og:audio` 或正则匹配 `media.xyzcdn.net` URL 实现。

### 1.3 可获取的元数据

通过 WebFetch 解析 `og:*` meta 标签，可以获取：

| 字段 | meta 属性 | 内容 |
|------|-----------|------|
| 标题 | `og:title` | 单集标题 |
| 描述 | `og:description` | 节目简介 |
| 封面图 | `og:image` | 封面图片 URL |
| 音频直链 | `og:audio` | `media.xyzcdn.net/*.m4a` |
| 播客名称 | `og:site_name` | 播客节目名 |

**注意：**
- 小宇宙是 Next.js SSR 应用，meta 标签在服务端渲染，WebFetch 可直接获取
- 付费内容无法通过此方式获取音频（会返回受保护链接或无音频链接）

### 1.4 官方 API

小宇宙**没有公开的官方开发者 API**。现有方案均基于页面解析（SSR meta 标签）。

---

## 2. 音频转录方案

### 2.1 现有技能

**已有完整的 Deepgram 技能，直接复用：**

```
~/.claude/skills/deepgram-transcription/Skill.md      # 使用文档
~/.claude/skills/deepgram-transcription/transcribe.py # 可执行脚本
```

**调用方式：**
```bash
python3 ~/.claude/skills/deepgram-transcription/transcribe.py "AUDIO_URL" \
  --language zh \
  --output-prefix podcast_transcript \
  --output-dir ./output
```

### 2.2 中文转录能力

| 项目 | 详情 |
|------|------|
| 模型 | Nova-2（中文）/ Nova-3（英文/日语等） |
| 中文代码 | `zh`, `zh-CN`, `zh-Hans` |
| 支持特性 | 说话人识别（diarize）、时间戳、分段、标点、段落 |
| URL 转录 | **支持**，直接传入音频 URL，无需下载到本地 |
| 费用 | $0.0043/分钟，90 分钟音频 ≈ $0.39 |
| 文件限制 | 最大 2GB，处理超时 10 分钟 |

### 2.3 转录输出格式

`transcribe.py` 输出两个文件：
- `.txt`：带时间戳 + 说话人标注的分段文本
- `.json`：完整 Deepgram 响应（含词级时间戳）

**TXT 格式示例：**
```
[00:00 - 02:35] 说话人0
欢迎来到今天的节目...

[02:35 - 05:10] 说话人1
今天我们要聊的这本书...
```

---

## 3. 内容分析方案

### 3.1 现有案例参考

`podcast_content_outline.json` 展示了目标数据结构：

```json
{
  "podcast": { "title", "episode", "hosts", "slogan", "book" },
  "sections": [
    {
      "id": "section_id",
      "title": "章节标题",
      "subtitle": "副标题",
      "time_range": "00:00 - 08:08",
      "key_points": ["观点1", "观点2"],
      "quotes": ["金句1", "金句2"],
      "stories": ["故事1"],
      "is_ad": false
    }
  ],
  "core_quotes": ["全局金句..."],
  "visual_metaphors": [{ "name", "description" }]
}
```

### 3.2 Claude API 分析流程

用 Claude API 将转录文本 → 结构化 JSON：

**Prompt 策略：**
1. 传入完整转录文本（带时间戳）
2. 要求输出上述 JSON 结构
3. 自动识别：章节划分、金句提取、广告段落标记、主持人角色

**模型建议：** `claude-sonnet-4-6`（速度快，中文理解好）

**处理长文本：**
- 90 分钟播客 ≈ 2-3 万字转录文本
- 在 Claude 200k context 范围内，可一次性处理
- 无需分段处理

---

## 4. 网页生成方案

### 4.1 现有网页分析

`podcast_visualization.html`（1575 行）是一个完整的交互式单页应用：

**核心特性：**
- 全屏滚动（每 section min-height: 100vh）
- 右侧圆点导航（固定定位）
- 顶部进度条
- Reveal 动画（IntersectionObserver）
- 点击金句弹出分享模态框
- 黑金配色 CSS 变量系统

**配色方案（CSS 变量）：**
```css
--bg: #0a0a0f;       /* 深黑背景 */
--gold: #d4a017;     /* 金色主色 */
--gold-light: #f0c040;
--text: #e8e0d0;     /* 暖白文字 */
```

**Section 结构：**
```
hero → 作者介绍 → 主题内容(多个) → 测验/互动 → 结尾
```

### 4.2 模板化策略

**方案：Python 字符串模板 + JSON 数据注入**

核心思路：
1. 将 `podcast_visualization.html` 拆分为**布局骨架**（CSS + JS 不变）+ **数据部分**（动态填充）
2. Python 脚本读取 `content_outline.json`，生成最终 HTML
3. Section 类型映射（不同内容类型对应不同 HTML 模板块）

**Section 类型对应的模板块：**

| Section 类型 | HTML 模板 | 特征 |
|-------------|-----------|------|
| `intro` | hero 大图 + 书名 + 核心金句 | 全屏，渐入动画 |
| `content` | 要点列表 + 引语卡片 | 左图右文，可点击金句 |
| `story` | 故事卡片 | 对话气泡或时间线 |
| `ad` | 广告标记区块（可选隐藏） | 弱化显示 |
| `ending` | 推荐书目 + 关注二维码 | 全屏收尾 |

---

## 5. 技术架构建议

### 5.1 推荐方案：Python 本地脚本（MVP）

**整体流程：**

```
用户输入小宇宙链接
    ↓
[Step 1] 获取元数据
  WebFetch 解析 og:audio / og:title / og:image
    ↓
[Step 2] 音频转录
  调用 transcribe.py → 输出 podcast_transcript.txt
    ↓
[Step 3] 内容分析
  Claude API 分析转录文本 → 输出 content_outline.json
    ↓
[Step 4] 网页生成
  Python 模板引擎 → 输出 podcast_visualization.html
    ↓
用户打开 HTML 文件 / 部署到 Vercel
```

### 5.2 技术栈

| 组件 | 技术选型 | 理由 |
|------|---------|------|
| 入口脚本 | Python 3 | 已有 transcribe.py，保持一致 |
| 页面抓取 | `httpx` + BeautifulSoup | 轻量，解析 og: 标签 |
| 音频转录 | 复用现有 `transcribe.py` | 开箱即用 |
| 内容分析 | `anthropic` Python SDK | 调用 Claude API |
| 网页模板 | Python `string.Template` 或 Jinja2 | 无需引入前端框架 |
| 输出部署 | 静态 HTML（可选 Vercel） | 零依赖，分享便捷 |

### 5.3 目录结构

```
podcast-tool/
├── main.py                    # 主入口：输入链接 → 输出 HTML
├── fetcher.py                 # 获取小宇宙元数据（og: 解析）
├── analyzer.py                # Claude API 内容分析
├── generator.py               # HTML 网页生成
├── templates/
│   ├── base.html              # 基础骨架（CSS + JS）
│   ├── section_content.html   # 内容区块模板
│   └── section_hero.html      # 开场区块模板
└── RESEARCH.md                # 本文档
```

### 5.4 用户体验流程

```bash
# 最简单的用法（目标）
python3 main.py "https://www.xiaoyuzhoufm.com/episode/xxx"

# 输出：
# ✅ 获取音频：media.xyzcdn.net/xxx.m4a
# ✅ 转录完成：podcast_transcript.txt（时长 89:04，置信度 94%）
# ✅ 内容分析：content_outline.json（8 个章节，42 条金句）
# ✅ 网页生成：podcast_visualization.html
#
# 请用浏览器打开：podcast_visualization.html
```

### 5.5 关键风险与应对

| 风险 | 概率 | 应对方案 |
|------|------|---------|
| 小宇宙 og:audio 被屏蔽 | 低 | 备选：JS 渲染抓取（Playwright）|
| 中文转录准确率不足 | 中 | 可替换为 Whisper API |
| 内容分析结构不稳定 | 低 | 严格 JSON Schema 约束 + 重试 |
| 音频超时（>10分钟处理） | 低 | Deepgram 异步 API 模式 |

---

## 6. 关键结论

1. **技术路径可行**：小宇宙页面 SSR 输出 og:audio，可直接获取音频直链
2. **核心技能已有**：Deepgram 转录技能开箱即用，支持 URL 直接转录
3. **现有案例可复用**：`podcast_visualization.html` 直接作为视觉模板基础
4. **最小可行方案**：Python 单脚本，3 步（获取→转录→分析→生成），约 200-300 行代码
5. **建议 MVP 优先**：先跑通完整流程，再考虑 Web UI 和部署

---

*研究员：Claude (podcast-tool 团队)*
*参考资料：现有 Deepgram 技能文档、小宇宙开源下载工具、现有播客可视化案例*
