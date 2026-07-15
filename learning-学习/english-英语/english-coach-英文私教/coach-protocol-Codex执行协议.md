# Codex 执行协议：English Coach 英文私教

## 目标

把零散口语练习变成可持续积累的表达系统，重点提升：

| 能力 | 说明 |
|---|---|
| Fluency 流利度 | 能连续说，不被单词和语法频繁打断 |
| Naturalness 自然度 | 从中式可懂英语升级成母语者常说法 |
| Pronunciation 发音 | 记录高频发音问题，集中复练 |
| Retrieval 提取 | 让学过的表达在真实场景中能说出来 |
| Parent-child English 亲子英语 | 积累以后能和孩子一起使用的生活表达 |

## 每次收到练习材料后的处理流程

1. 判断场景：通勤、天气、亲子、工作、消费、旅行、社交。
2. 提取原句：保留用户真实表达，不美化。
3. 纠错分层：
   - Grammar 语法错误
   - Word choice 用词不自然
   - Collocation 搭配问题
   - Idiom / chunk 可复用表达块
   - Pronunciation 发音提醒
4. 生成当天唯一复习材料：单文件 HTML，保存为 `courseware-课件/YYYY-MM-DD-DayXX-topic-中文主题/index.html`。
5. 将以下内容融合到同一个 HTML 中：
   - 互动课件：导航、已掌握、练习答案折叠、打印 PDF、返回顶部
   - 日课材料：原句纠正、自然表达、词汇深挖、例句、跟读句
   - 教学日记：老师观察、学生进步、下一步教学策略，压缩为“成长记录”
6. 更新复习库：
   - `review-bank-复习库/natural-expressions-地道表达.md`
   - `review-bank-复习库/vocabulary-bank-词汇库.md`
   - `review-bank-复习库/pronunciation-notes-发音记录.md`
   - `review-bank-复习库/weak-areas-薄弱项.md`
7. 更新 `progress-tracker-学习进度.md`。
8. 更新项目总目录 `index.html`，每节课只保留一个“打开复习材料”入口。

## 唯一 HTML 复习材料结构

| 顺序 | 模块 | 内容原则 |
|---|---|---|
| 1 | Cover 封面 | Day、日期、主题、一句话总结、关键词 |
| 2 | 3-Minute Review 快速复习 | 最重要的 5-8 句、1 个 Deep Word、1 个纠错点、1 个口语任务 |
| 3 | Story 回放 | 真实情境，用 3-5 张场景卡串起来 |
| 4 | Original → Natural | 我的原句、自然表达、简短说明 |
| 5 | Key Expressions | 可标记已掌握，localStorage 保存 |
| 6 | Deep Word | Core Image、词义网络、搭配、误区、真实例句 |
| 7 | Fixes | 当天实际出现的语法、发音或用词修正；没有就不硬放 |
| 8 | Mini Practice | 选择、填空、改错、场景表达，答案默认折叠 |
| 9 | Speak It Yourself | 关键词提示 + 折叠参考答案 |
| 10 | Growth Note | 教学日记压缩版：观察、进步、下一步策略 |

## 输出与文件规则

| 项目 | 规则 |
|---|---|
| 每日正式产物 | 只有一个 `index.html` |
| Markdown 日课材料 | 默认不再单独生成 |
| Markdown 教学日记 | 默认不再单独生成 |
| 历史 Markdown | 保留为历史归档，不删除 |
| 总目录 | 每天只链接唯一 HTML 复习材料 |
| 使用场景 | 课后复习优先，不做展示型 PPT |

## 复习规则

| 时间点 | 复习内容 |
|---|---|
| D+1 | 昨天最重要的 5 句 |
| D+3 | 同一场景换一种说法复述 |
| D+7 | 用 2 分钟自由表达串起来 |
| D+14 | 放进工作或生活真实场景再用一次 |

## 输出要求

每次整理只输出三块：

1. 今日复习 HTML 已归档到哪里
2. 新增复习项
3. 明天最该练的 1 个场景或 1 个 Deep Word

不输出泛泛学习建议。
