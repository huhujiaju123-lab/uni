---
name: ppt-generator
description: 瑞幸美国 PPT 生成器。根据用户提供的文字内容，生成符合公司模板风格的 .pptx 文件。支持月报（封面+3页）和项目报告（灵活页数）。每次生成两版：实用版+深度版。
trigger: 当用户提到"生成PPT"、"做PPT"、"月报PPT"、"工作进展PPT"、"项目报告PPT"时使用。
---

# PPT Generator Skill

根据瑞幸美国公司模板风格，将用户提供的文字内容生成 .pptx 文件。

## 核心原则

1. **忠于用户内容** — 不发散、不加工、不创造内容，严格按用户文字排版
2. **稳定一致** — 每次输出遵循相同模板，配色/字体/布局不变
3. **双版本输出** — 每次生成实用版 + 深度版两个文件
4. **审核驱动** — 生成后以老板视角审核，不达标就修改重来
5. **可编辑输出** — .pptx 格式，所有文字/表格/图表均可二次编辑

## 双版本策略

每次生成 PPT 都输出两个版本：

### 实用版（主文件，用于直接汇报）
- 文件名后缀：`_实用版.pptx`
- 内容忠于用户原文，不额外发散
- 结构：封面 + 4-5页内容页
- 每页标准构成：结论框 + 1-2个章节（表格/图表）+ 脚注
- 最后一页包含：汇总对比 + 下一步计划 + 风险说明

### 深度版（参考文件，用于备问和深入讨论）
- 文件名后缀：`_深度版.pptx`
- 在实用版基础上增加：
  - **敏感性分析**：关键假设变化对结果的影响（参与率/成本/转化率）
  - **条件着色**：表格单元格按数据含义着色（正向绿/负向红/强调蓝/注意黄）
  - **环比趋势**：数据不是静态快照，而是展示变化方向
  - **压力测试结论**：即使最坏情况下方案是否仍可行
- 条件着色颜色：
  - `BG_GREEN = RGBColor(0xE8, 0xF5, 0xE9)` — 正向/推荐
  - `BG_RED = RGBColor(0xFF, 0xEB, 0xEE)` — 负向/警示
  - `BG_BLUE = RGBColor(0xE3, 0xF2, 0xFD)` — 中性强调/基准行
  - `BG_AMBER = RGBColor(0xFF, 0xF8, 0xE1)` — 需关注

## 审核流程（必须执行）

生成 PPT 后，Claude 以老板视角逐页审核，按5个维度评分：

| 维度 | 权重 | 关注点 |
|------|------|--------|
| 数据准确性 | 20% | 数据完整、口径一致、有精确数字 |
| 分析深度 | 25% | 有洞察非描述、分层分析、对比基准 |
| 逻辑完整性 | 20% | 页面递进、因果链、回答核心问题 |
| 策略对齐 | 15% | ROI分析、可执行建议、实施计划 |
| 视觉标准 | 20% | 字号合适、图表不压扁、间距舒适 |

- **≥85分**：通过，输出给用户
- **70-84分**：列出具体问题，修改后重新生成
- **<70分**：重新规划页面结构

审核必须引用具体内容，给出可操作的修改意见，不能只说"不错"。

## 工作流程

### 月报模式（用户说"月报"/"工作进展"）

1. 确认：标题、日期、3页的内容分配
2. 解析用户文字，提取结论/数据/要点
3. 生成实用版：封面 + 3页内容页
4. 审核 → 修改 → 达标
5. 在实用版基础上生成深度版（加敏感性/着色/趋势）
6. 输出到 `~/Vibe coding/output/`

### 项目报告模式

1. **必须先与用户确认**页面结构
2. 生成实用版 → 审核 → 修改 → 达标
3. 生成深度版
4. 输出两个文件

## 生成脚本用法

```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/.claude/skills/ppt-generator'))
from generate_ppt import LuckinPPT, Emu, Pt, RGBColor

ppt = LuckinPPT(title="标题", author="李宵霄", date="2026年3月")
ppt.add_cover()

slide, y = ppt.add_content_page("页面标题", subtitle="横线下方说明文字")
y = ppt.add_conclusion(slide, y, "结论：总结句", ["要点1 <red>(+9%)</red>", "要点2"])
y = ppt.add_section_title(slide, y, "章节标题")
y = ppt.add_table(slide, y, ["列1","列2"], [["A","B <red>(+5%)</red>"], ["C","D"]])
y = ppt.add_bar_chart(slide, y, "图表标题", ["Q1","Q2"], {"系列1": [10,20]})
ppt.add_footnote(slide, "*脚注说明")

ppt.save(os.path.expanduser("~/Vibe coding/output/报告.pptx"))
```

## API 速查

| 方法 | 作用 | 返回 |
|------|------|------|
| `add_cover(title, subtitle)` | 封面页（深蓝背景+Logo+装饰） | slide |
| `add_content_page(title, subtitle)` | 内容页骨架（白底+双Logo+标题+横线+副标题） | (slide, y) |
| `add_conclusion(slide, y, title, points)` | 结论框（深蓝标题栏28pt + 浅蓝灰内容区20pt） | y |
| `add_section_title(slide, y, text)` | 深蓝色章节小标题 26pt + 左侧蓝色竖条 | y |
| `add_table(slide, y, headers, rows, cell_colors=None)` | 数据表格（深蓝表头20pt+斑马纹18pt+可选条件着色） | y |
| `add_bar_chart(slide, y, title, cats, series)` | 柱状图（柱顶标签14pt+100%间隙+默认6"高） | y |
| `add_line_chart(slide, y, title, cats, series)` | 折线图（2.5pt+圆形标记点+默认6"高） | y |
| `add_pie_chart(slide, y, title, cats, values)` | 饼图（类别+百分比标签16pt） | y |
| `add_text_block(slide, y, text)` | 通用文本段落 20pt | y |
| `add_footnote(slide, text)` | 底部灰色脚注 14pt | y |

## 条件着色用法（深度版专用）

```python
BG_GREEN = RGBColor(0xE8, 0xF5, 0xE9)
BG_RED   = RGBColor(0xFF, 0xEB, 0xEE)
BG_BLUE  = RGBColor(0xE3, 0xF2, 0xFD)
BG_AMBER = RGBColor(0xFF, 0xF8, 0xE1)

# cell_colors 与 rows 同 shape，None = 默认斑马纹
y = ppt.add_table(slide, y, headers, rows,
    cell_colors=[
        [None, BG_GREEN, BG_RED],   # 第1行：第2列绿，第3列红
        [None, None,     None],      # 第2行：默认
    ])
```

## 颜色标记语法（用在表格和结论中）

- `<red>+9.39%</red>` → 红色（正向/涨）
- `<green>-0.83pp</green>` → 绿色（负向/跌）
- `<gray>(差值)</gray>` → 灰色辅助
- `<bold>关键词</bold>` → 加粗

## 字号体系

| 元素 | 字号 | 粗细 |
|------|------|------|
| 封面主标题 | 54pt | Bold |
| 页面大标题 | 40pt | Bold |
| 副标题 | 20pt | Regular, #444444 |
| 结论标题栏 | 28pt | Bold, 白色 |
| 结论要点 | 20pt | Regular |
| 章节标题 | 26pt | Bold |
| 表格表头 | 20pt | Bold, 白色 |
| 表格内容 | 18pt | Regular |
| 图表标题 | 22pt | Bold |
| 图例/坐标轴 | 14-16pt | Regular |
| 脚注 | 14pt | Regular, #999 |

## 设计规范摘要

- **字体**：全局 STKaiti
- **颜色**：红涨(#D32F2F) 绿跌(#2E7D32)，正文#333333，标题#0F3460
- **结论框**：深蓝标题栏(#222773白字) + 浅蓝灰内容区(#EDF2F9)
- **表格**：深蓝表头(#222773)+白字，斑马纹(#F5F7FA)，边框#E0E0E0
- **图表**：默认6"高，柱状图100%间隙，图例顶部
- **间距**：结论→章节 0.3"，章节→表格 0.1"，表格→章节 0.3"
- **Logo**：每页必须有（左上鹿头 + 右下 luckin coffee）
- **封面**：固定深蓝紫背景(#222773) + 左侧装饰图 + 右上Logo
- **尺寸**：26.67" x 15.0"
- **输出目录**：`~/Vibe coding/output/`
- **完整规范**：`references/style_guide.md`
