---
name: ppt-generator
description: PPT 生成器偏好：双版本输出、字号要求、Claude审核流程、图表不能压扁
type: feedback
---

## PPT 生成偏好（2026-03-12 确认）

### 双版本输出（必须）
每次生成 PPT 都输出两版：
1. **实用版**（`_实用版.pptx`）：忠于用户原文，结构清晰，直接用于汇报
2. **深度版**（`_深度版.pptx`）：在实用版基础上增加敏感性分析、条件着色、环比趋势、压力测试

### 字号要求（用户明确说"正文要到20的"）
- 正文/结论要点：20pt（不能小于这个）
- 结论标题：28pt Bold
- 章节标题：26pt Bold
- 表格表头：20pt Bold
- 表格内容：18pt
- 图表标题：22pt Bold
- 脚注：14pt

### 图表不能压扁
- 默认高度 6"（不是 5"）
- 柱状图间隙比 100%
- 图例在顶部，不占图表面积

### 审核流程
- 老板审核由 Claude 扮演，不是 Python 自动评分
- 必须读实际内容、给具体修改意见
- ≥85分通过，70-84修改重来，<70推翻重做
- V1→V2→V3 迭代直到达标

### 技能路径
`~/.claude/skills/ppt-generator/skill.md`
`~/.claude/skills/ppt-generator/generate_ppt.py`
`~/.claude/skills/ppt-generator/references/style_guide.md`
