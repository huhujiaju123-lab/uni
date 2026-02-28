# 播客可视化工具 (podcast-viz)

将小宇宙播客链接转化为精美的交互式可视化网页。

## 版本

| 版本 | Tag | 链接 | 端口 | 服务器路径 |
|------|-----|------|------|-----------|
| v2.0 | `podcast-viz/v2.0` | http://134.175.228.73:8081 | 8081 | /opt/podcast-viz-v2/ |
| v1.0 | `podcast-viz/v1.0` | http://134.175.228.73 | 80 | /opt/podcast-viz/ |

## 架构

```
小宇宙 URL
  → fetcher.py      获取元数据（标题、音频直链、封面）
  → transcribe.py   Deepgram Nova-2 音频转录（带时间戳+说话人）
  → analyzer.py     通义千问 qwen-plus 内容分析 → episode.json
  → generator.py    Jinja2 渲染 → 单文件交互式 HTML
```

## 项目结构

```
podcast-tool/
├── app.py                    Flask Web 后端（SSE 进度推送）
├── fetcher.py                小宇宙元数据抓取
├── transcribe.py             Deepgram 音频转录
├── analyzer.py               AI 内容分析（通义千问）
├── generator.py              HTML 渲染引擎
├── templates/
│   ├── base.html.j2          可视化主模板（暗色主题、滚动动画）
│   ├── index.html            首页（输入框）
│   └── progress.html         处理进度页
├── prompts/
│   └── extract_content.md    AI 分析的 System Prompt
├── examples/
│   └── ep59_episode_v2.json  测试数据（EP.59 一生之敌）
└── CHANGELOG.md              版本日志
```

## 数据模型（v2.0）

episode.json 核心字段：

| 字段 | 说明 |
|------|------|
| meta | 播客名称、期号、标题、封面 |
| participants | 主持人/嘉宾信息 |
| sections | 章节（key_points_grouped + diagram + quotes + stories） |
| content_overview | 内容组块 + 逻辑连线 |
| arguments | 核心观点（论据类型 + 强度） |
| key_concepts | 关键概念词典 |
| extended_reading | 延伸阅读方向 |
| mind_map | 思维导图（树状结构） |
| quiz | 互动自测题 |
| core_quotes | 全集精选金句 |

### 章节内特殊字段

- **key_points_grouped**：按逻辑分组的要点，支持 visual_type（list/comparison/flow/icon-grid）
- **diagram**：内联图表（flow/comparison/icon-list/slope/layers）
- **section_context**：本章在全集逻辑链中的位置

## 部署

### 环境变量

```bash
DASHSCOPE_API_KEY=xxx    # 通义千问 API（阿里云灵积）
DEEPGRAM_API_KEY=xxx     # Deepgram 转录 API
```

### 服务管理

```bash
# v2.0
systemctl restart podcast-viz-v2
systemctl status podcast-viz-v2
journalctl -u podcast-viz-v2 -f

# v1.0
systemctl restart podcast-viz
systemctl status podcast-viz
```

### 本地开发

```bash
pip install flask jinja2 openai deepgram-sdk httpx beautifulsoup4

# 生成测试 HTML
python3 podcast-tool/generator.py podcast-tool/examples/ep59_episode_v2.json /tmp/test.html

# 启动 Web 服务
cd podcast-tool && python3 app.py
```

## 性能参数

| 参数 | 值 |
|------|-----|
| 最大音频时长 | ~3-4 小时 |
| 转录超时 | 3600s |
| AI 分析 max_tokens | 16384 |
| Gunicorn 超时 | 3600s |

## GitHub

- 仓库：https://github.com/huhujiaju123-lab/uni
- Release：https://github.com/huhujiaju123-lab/uni/releases/tag/podcast-viz/v2.0
