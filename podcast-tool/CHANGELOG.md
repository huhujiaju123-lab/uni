# Changelog

## v2.0.2 (2026-02-28)
修复 Deepgram 转录超时

### 修复
- **转录超时参数无效**：Deepgram SDK v6 的超时参数为 `timeout_in_seconds`（int），之前误用 `timeout`/`httpx.Timeout` 被 SDK 忽略，导致长音频转录超时。改为 `timeout_in_seconds=3600`（1小时）

---

## v2.0.1 (2026-02-28)
Diagram 渲染修复 + 健壮性加固

### 修复
- **修复 `builtin_function_or_method` 崩溃**：Jinja2 中 `dict['items']` 在 key 不存在时回退到 Python dict 的 `.items()` 方法，导致迭代报错。字段名从 `items` 统一改为 `entries`
- **空壳 diagram 防御**：AI 只生成 type/title/description 但无实际数据时，预处理阶段自动清除，避免空渲染
- **Prompt 补全 diagram 数据结构**：5 种 diagram 类型（flow/comparison/icon-list/slope/layers）均补充了必需的数据字段说明，确保 AI 生成完整数据

### 改动文件
- `analyzer.py`：prompt 增加 diagram 完整 schema + 数据字段要求
- `generator.py`：预处理 `items` → `entries` 重命名 + 空 diagram 清除
- `templates/base.html.j2`：`diagram['items']` → `diagram.entries`

---

## v2.0 (2026-02-28)
内容深度升级 + 可视化图表 + 导航重构

### 新增模块
- **内容概览**：3-5 个组块 + 逻辑连线，鸟瞰全集脉络
- **核心观点**：8-12 个论点卡片，标注论据类型和强度
- **关键概念**：概念词典，含定义、阐述、例子、关联概念
- **延伸阅读**：基于播客话题的深度延伸方向
- **思维导图**：2-3 层树状结构，可视化知识框架

### 内容结构优化
- **分组要点**：key_points 按逻辑分 2-4 组，带序号标签和层次缩进
- **章节上下文**：每章开头提示在全集逻辑链中的位置
- **visual_type**：分组支持 list/comparison/flow/icon-grid 四种布局
- **内联图表**：flow 流程图、comparison 对比图、icon-list 图标网格、slope 坡道模型、layers 层次图

### 导航系统
- 默认展开的左侧栏导航，按内容脉络/深度分析/互动三大区分组
- Hero 区自动隐藏，滚动到内容区后渐入
- 已阅读章节标记 + 当前章节高亮
- 移动端汉堡菜单

### 性能
- 转录超时提升至 1 小时，支持 3-4 小时超长音频
- AI 分析 max_tokens 提升至 16384
- Prompt 强化：要求完整观点句 + 详细论据引述

### 部署
- v2.0 独立部署于 8081 端口，与 v1.0 互不影响

## v1.0 (2026-02-27)
首个正式版本

- 核心功能：小宇宙链接 → 转录 → AI 分析 → 可视化
- AI 模型：通义千问 qwen-plus
- 安全加固：路径遍历防护、速率限制、并发限制、安全响应头
- 性能优化：去掉 utterances、直接函数调用
- 部署：非 root 用户、Gunicorn gthread
- 测试：后端 30 + 安全 20 + 并发 13
