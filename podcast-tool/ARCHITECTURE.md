# Podcast Tool 架构设计文档

> 基于「一生之敌」可视化案例（EP.59）提取的通用模式

---

## 一、现有案例分析总结

### 1.1 JSON 内容结构分析（podcast_content_outline.json）

**文件总览**：308 行，结构清晰，层级为 2 层（podcast 元数据 + sections 数组）。

#### 通用字段（可复用于任意播客）

| 字段 | 位置 | 说明 |
|------|------|------|
| `podcast.title` | 顶层 | 本期标题 |
| `podcast.episode` | 顶层 | 期数编号 |
| `podcast.hosts[]` | 顶层 | 主持人/嘉宾数组，含 id/name/role |
| `podcast.slogan` | 顶层 | 播客口号 |
| `sections[].id` | 章节 | 章节唯一标识符（对应 HTML 锚点） |
| `sections[].title` | 章节 | 章节主标题 |
| `sections[].subtitle` | 章节 | 章节副标题 |
| `sections[].time_range` | 章节 | 时间区间（字符串格式 "MM:SS - MM:SS"） |
| `sections[].key_points[]` | 章节 | 核心观点列表 |
| `sections[].quotes[]` | 章节 | 本章节金句 |
| `sections[].stories[]` | 章节 | 个人故事/真实案例 |
| `sections[].is_ad` | 章节 | 是否为广告段 |
| `core_quotes[]` | 顶层 | 全集精选金句（跨章节提取） |
| `visual_metaphors[]` | 顶层 | 视觉比喻/隐喻列表，含 name + description |

#### 特定于本期的字段

| 字段 | 说明 |
|------|------|
| `podcast.book` + `podcast.author` | 这期讨论了一本书，不是所有播客都有 |
| `sections[].id` 的具体值 | "resistance-nature" 等是本期内容特定的 |
| `hosts[].id` 格式 "说话人0.0" | 是 Deepgram 转录软件生成的，不够通用 |

#### 现有结构的改进建议

1. **`time_range` 改为数值型**：`"start_sec": 488, "end_sec": 983`，字符串只做展示用，便于排序和验证
2. **缺少元数据字段**：
   - `podcast.cover_url`：封面图
   - `podcast.platform_links`：各平台链接（小宇宙、Apple Podcast 等）
   - `podcast.published_date`：发布日期
   - `podcast.total_duration_sec`：总时长
   - `podcast.language`：语言（zh/en 等）
3. **`hosts[].id` 标准化**：改为手动设置的简洁 ID（如 "via", "guxin"），与说话人识别结果解耦
4. **`visual_metaphors` 下移至 sections**：将比喻与其所属章节关联，便于模板按章节渲染
5. **`book_recommendations` 独立字段**：当前在最后一个 section 中混合，应提取为顶层字段，适配书评/影评类播客

---

### 1.2 网页模板分析（podcast_visualization.html）

**文件规模**：1575 行（HTML + CSS + JS 完全内联，单文件设计）

**页面结构（Section 序列）**：

| 序号 | ID | 内容类型 | 通用性 |
|------|----|----------|--------|
| 1 | `#hero` | 封面页（标题 + 开场金句） | ✅ 通用 |
| 2 | `#author` | 作者/嘉宾介绍 + 时间线 | ✅ 通用 |
| 3-8 | 各章节 | 核心内容章节 | 部分通用 |
| 9 | `#quiz` | 互动自测 | ✅ 通用（问题需参数化） |
| 10 | `#ending` | 书单推荐 + 播客名片 + 收尾 | ✅ 通用 |

#### 完全通用的框架组件（固定不变）

```
CSS 设计系统：
  - :root 颜色变量（--bg, --gold, --text 等），一处改主题色全局生效
  - 字体变量（--font 衬线体, --sans 无衬线体）
  - 动画类（.reveal, .reveal-delay-1/2/3/4）
  - 响应式 Media Query（768px 断点）

JS 交互系统：
  - 顶部进度条（scroll → width 更新）
  - Intersection Observer（reveal 动画触发）
  - 侧边点导航（section 高亮 + 平滑滚动）
  - 金句点击收藏系统（savedQuotes 数组 + 浮窗面板）
  - Quiz 逻辑框架（选项选择 + 滑块 + 评分 + 结果展示）
```

#### 需要动态填充的内容（参数化占位符）

```
Hero 区：
  - 播客名称、期数编号、主标题、副标题
  - 开场核心金句

导航点（#dot-nav）：
  - data-section 和 data-label（由 sections 数组生成）

各章节：
  - section[id] → 对应章节 id
  - section-label、section-title
  - 大引用金句（blockquote）
  - 特性卡片（feature-cards）/ 症状卡片（symptom-card）/ 故事卡片（story-card）
  - VS 对比表格（当涉及对比时）

Quiz 区：
  - 问题列表（quiz-question）
  - 每题选项（quiz-opt）
  - 评分区间和结果描述

结尾区：
  - 书单（book-cards）
  - 播客名片（podcast-card）
  - 最终口号（final-slogan）
```

#### 特定于本期的视觉元素

- **SVG 坡道示意图**（#resistance-nature 的内阻力↑图示）：这是根据「内阻力=单向阻力」概念手写的，其他播客不一定有类似概念，不宜通用化
- **`compensation-grid`**（代偿机制三格）：概念特定
- **红色系配色**（`#fear-success` 段用了 `--danger` 红色）：情感配色随内容调整

#### CSS 主题参数化建议

当前硬编码的金色主题可提炼为 3 个主题参数：
- `--primary`（当前 #d4a017 金色）
- `--bg`（当前 #0a0a0f 深黑）
- `--accent-secondary`（当前 #c07830 琥珀色）

---

### 1.3 转录脚本分析（transcribe_podcast.py）

**当前流程**：

```
1. 读取环境变量 DEEPGRAM_API_KEY
2. 调用 Deepgram Nova-2（中文）
   - diarize=True（说话人识别）
   - paragraphs=True（自动分段）
   - utterances=True（话语切割）
   - timeout=600（10分钟，支持长音频）
3. 输出：
   - podcast_transcript.txt（[时间戳] 说话人N\n文本）
   - podcast_transcript.json（Deepgram 原始响应）
```

**可复用的核心逻辑**：
- `DateTimeEncoder`：JSON 序列化时处理 datetime 对象
- Deepgram 调用参数组合（适合中文播客的参数已调优）
- 段落+说话人的文本格式化逻辑

**当前的硬编码问题**：
- `AUDIO_URL` 写死为特定音频 URL
- `OUTPUT_TXT` / `OUTPUT_JSON` 写死为固定文件名
- 标题文字写死在输出文件头部
- 语言固定为 `zh`

**参数化需求**：
```python
# 需要从外部传入的参数
audio_url: str          # 音频 URL
output_prefix: str      # 输出文件名前缀
language: str = "zh"    # 语言
model: str = "nova-2"   # Deepgram 模型（nova-3 更新更准）
```

---

## 二、通用 Podcast Episode 数据模型设计

### 2.1 设计原则

1. **内容与展示分离**：JSON 只描述内容，不包含样式决策
2. **渐进式丰富度**：必填字段最少，可选字段按需填充
3. **兼容多类型播客**：书评/对谈/访谈/独白均可适配
4. **AI 生成友好**：字段结构与 Claude 的输出习惯对齐

---

### 2.2 通用数据模型（TypeScript-like 伪代码）

```typescript
interface PodcastEpisode {
  // ===== 元数据（必填）=====
  meta: {
    podcast_name: string;          // 播客名称，如"进步是一件性感的事"
    episode_number: number | null; // 期数，访谈类可为 null
    title: string;                 // 本期标题
    subtitle: string;              // 副标题（一句话描述）
    published_date: string;        // "YYYY-MM-DD"
    total_duration_sec: number;    // 总时长（秒）
    language: "zh" | "en" | string;
    cover_url?: string;            // 封面图 URL
    audio_url?: string;            // 音频 URL
    platform_links?: {             // 各平台收听链接
      [platform: string]: string;  // "xiaoyuzhou": "...", "apple": "..."
    };
  };

  // ===== 参与者（必填）=====
  participants: {
    id: string;           // 简洁 ID，如 "host1", "via", "guxin"
    name: string;         // 显示名
    role: "host" | "guest" | "narrator";
    bio?: string;         // 简介（嘉宾时常用）
    avatar_url?: string;
  }[];

  // ===== 主题/参考资料（可选）=====
  // 书评/影评类播客特有
  featured_work?: {
    type: "book" | "film" | "album" | "article";
    title: string;
    author?: string;
    year?: number;
    description?: string;  // 一句话点评
  };

  // ===== 章节（必填）=====
  sections: {
    id: string;              // URL 锚点 ID，如 "intro", "chapter-1"
    title: string;           // 主标题
    subtitle?: string;       // 副标题
    start_sec: number;       // 开始时间（秒）
    end_sec: number;         // 结束时间（秒）
    is_ad: boolean;          // 是否广告段

    key_points: string[];    // 核心观点（3-8条）
    quotes: string[];        // 本章节金句
    stories: {               // 个人故事/案例
      narrator_id: string;   // 对应 participants[].id
      text: string;
    }[];

    visual_metaphors?: {     // 视觉比喻（可选，AI 生成或手动填写）
      name: string;
      description: string;
      icon?: string;         // emoji 或图标
    }[];
  }[];

  // ===== 全集精选（必填）=====
  core_quotes: string[];     // 跨章节精选，5-10条，用于 Hero 区展示

  // ===== 延伸推荐（可选）=====
  recommendations?: {
    type: "book" | "film" | "podcast" | "article";
    title: string;
    author?: string;
    quote?: string;          // 推荐理由或摘录
    recommender_id?: string; // 推荐人（对应 participants[].id）
  }[];

  // ===== 自测题（可选）=====
  // 若无此字段，网页可用通用默认题目
  quiz?: {
    intro: string;           // 自测引导语
    questions: {
      id: string;
      text: string;
      type: "choice" | "slider";
      options?: {            // type=choice 时
        label: string;
        score: number;       // 0-3，分数越高阻力越大
      }[];
      slider_labels?: [string, string, string, string]; // type=slider 时
    }[];
    result_levels: {         // 评分区间与结果
      max_avg_score: number; // 平均分上限（含）
      level_label: string;   // 如 "职业选手级"
      description: string;
    }[];
  };

  // ===== 主题配置（可选）=====
  // 覆盖默认金色主题
  theme?: {
    primary_color?: string;   // 主色，默认 #d4a017
    bg_color?: string;        // 背景色，默认 #0a0a0f
    accent_color?: string;    // 强调色，默认 #c07830
    final_slogan?: string;    // 页面最底部大字，默认取 podcast_name
  };
}
```

---

### 2.3 现有 JSON 与通用模型的映射

| 现有字段 | 通用模型字段 | 变更说明 |
|----------|-------------|---------|
| `podcast.title` | `meta.title` | 路径变更 |
| `podcast.episode` | `meta.episode_number` | 路径变更 |
| `podcast.hosts[]` | `participants[]` | 结构扩展，id 改为手动设置 |
| `podcast.slogan` | `meta.podcast_name`（+`theme.final_slogan`） | 拆分 |
| `podcast.book` + `.author` | `featured_work.title` + `.author` | 结构化 |
| `sections[].id` | `sections[].id` | 不变 |
| `sections[].time_range` | `sections[].start_sec` + `.end_sec` | 从字符串改为数值 |
| `sections[].stories[]` (字符串) | `sections[].stories[].narrator_id + .text` | 结构化 |
| `visual_metaphors[]` (顶层) | `sections[].visual_metaphors[]` | 下移至章节 |
| `core_quotes[]` | `core_quotes[]` | 不变 |
| 缺失 | `meta.published_date/cover_url/platform_links` | 新增 |
| 缺失 | `recommendations[]` | 从最后一章节独立出来 |
| 缺失 | `quiz` | 独立结构化 |

---

## 三、产品化流程设计

### 3.1 整体流程

```
音频 URL
   ↓ [Step 1: 转录]
transcribe_podcast.py
   → transcript.txt（带时间戳 + 说话人）
   → transcript.json（原始 Deepgram 响应）

   ↓ [Step 2: AI 内容提取]
Claude (LLM)：读取转录文本
   → 输出符合通用数据模型的 episode.json

   ↓ [Step 3: 网页渲染]
模板引擎（Jinja2 或 JS 模板）：读取 episode.json
   → 输出 {episode_id}_visualization.html（单文件，可直接分享）
```

### 3.2 每个步骤的可复用组件

| 步骤 | 可复用 | 需定制 |
|------|--------|--------|
| 转录 | Deepgram 调用逻辑、格式化 | 参数（URL、语言、输出路径） |
| AI 提取 | System prompt 模板、JSON Schema | 无（LLM 自适应内容） |
| 网页渲染 | CSS 框架、JS 交互系统（进度条/收藏/导航/动画）| 每个 section 的具体渲染逻辑 |

### 3.3 网页模板参数化策略

**方案一：Jinja2 Python 模板**
- 优点：服务端渲染，单文件输出，无需构建工具
- 缺点：需要安装 Python 依赖

**方案二：JS 客户端渲染**
- 将 `episode.json` 内嵌在 HTML 中，用 JS 动态渲染
- 优点：单文件分发，浏览器打开即用
- 缺点：SEO 不友好（但播客分享场景不需要 SEO）

**推荐：方案一（Python Jinja2）**
- 与现有 Python 技术栈一致（transcribe_podcast.py）
- 单文件输出，易于分享

---

## 四、页面章节渲染策略

### 4.1 章节类型映射

不同类型的章节对应不同的 HTML 模板片段：

| 章节类型 | 触发条件 | 渲染组件 |
|----------|---------|---------|
| `intro` | id = "intro" 或位置第一 | Hero 变体（书/作者信息） |
| `comparison` | key_points 含【vs】或【对比】 | VS 对比表格 |
| `symptoms` / `list` | key_points 数量 ≥ 5，含【症状】 | 症状卡片网格 |
| `solution` | 含"如何"/"克服"/"职业" | Action Items 列表 |
| `fear` / `emotional` | 含"恐惧"/"最深" | 情感聚焦版式（居中大字） |
| `generic` | 默认 | 大引用 + 故事卡片 |
| `ad` | `is_ad: true` | 跳过（不渲染） |
| `ending` | id = "ending" 或位置最后 | 书单 + 播客名片 |

### 4.2 自测题默认模板

若 `episode.json` 中无 `quiz` 字段，使用通用默认题目：
1. "你有多少个'明天就开始'的计划？"
2. "接近完成一件重要的事时，你的行为？"
3. "身边有人进步时，你的第一反应？"
4. "你对'灵感'的依赖程度？"（slider）
5. "面对恐惧，你的倾向？"

---

## 五、文件结构规划

```
podcast-tool/
├── ARCHITECTURE.md          # 本文档
├── transcribe.py            # 参数化转录脚本（复用现有逻辑）
├── extract_content.py       # 调用 Claude API 提取 episode.json
├── render_html.py           # Jinja2 渲染 HTML
├── templates/
│   ├── base.html.j2         # 完整 HTML 框架（CSS + JS）
│   ├── sections/
│   │   ├── hero.html.j2
│   │   ├── author.html.j2
│   │   ├── generic.html.j2  # 通用章节
│   │   ├── comparison.html.j2
│   │   ├── symptoms.html.j2
│   │   ├── solution.html.j2
│   │   ├── fear.html.j2
│   │   ├── quiz.html.j2
│   │   └── ending.html.j2
│   └── components/
│       ├── quote_card.html.j2
│       ├── story_card.html.j2
│       ├── feature_card.html.j2
│       └── book_card.html.j2
├── schema/
│   └── episode.schema.json  # JSON Schema 用于验证
├── prompts/
│   └── extract_content.md   # Claude 提取内容的 System Prompt
└── examples/
    ├── ep59_episode.json    # 本期的规范化数据
    └── ep59_output.html     # 对应生成的 HTML
```

---

## 六、关键设计决策

### 决策 1：保持单文件 HTML 输出

**原因**：分享场景下，单文件比需要 CDN 的多文件更可靠。CSS 和 JS 内联，接收者直接打开浏览器即用。

### 决策 2：AI 负责内容提取，不负责格式化

**原因**：JSON 结构固定后，LLM 生成 JSON（结构化提取）更稳定。HTML 渲染交给确定性的模板系统，不引入随机性。

### 决策 3：广告段默认跳过渲染

**原因**：可视化的价值是内容精华，广告内容在知识型网页中是噪音。`is_ad: true` 的 section 在生成 HTML 时忽略。

### 决策 4：quiz 问题可配置但有默认值

**原因**：每期播客的主题不同，理想情况下自测题与主题相关（如「你的内阻力水平」）。但通用默认题目也可接受，降低内容准备门槛。

### 决策 5：视觉比喻独立存储，不强制渲染

**原因**：当前案例的 SVG 内阻力坡道图是手工绘制的，通用化成本高。`visual_metaphors` 字段存储文字描述，未来可接入图表生成服务（如 D3.js 模板库），当前版本中仅做展示文字。

---

*文档版本：v0.1 | 2026-02-26 | 基于 EP.59「一生之敌」案例提取*
