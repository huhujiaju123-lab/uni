# English Coach Courseware 课后复习材料

总入口：[`../index.html`](../index.html)

## 固定流程

后续用户只需要提供每日 English Coach 课程内容。Codex 默认执行：

1. 读取每日课程内容。
2. 基于当前复习模板生成单文件 HTML。
3. 保存到当天独立文件夹。
4. 更新学习总目录。
5. 打开当天 `index.html` 和学习总目录。

## 当前产物原则

| 项目 | 规则 |
|---|---|
| 每日正式材料 | 只保留一个 HTML 复习材料 |
| 内容融合 | 互动课件 + 日课材料 + 教学日记 |
| Markdown 日课材料 | 默认不再新建 |
| Markdown 教学日记 | 默认不再新建 |
| 历史 Markdown | 作为历史归档保留 |
| 总目录链接 | 每节课只链接唯一 HTML |

## 当前固化版本

| 项目 | 路径 |
|---|---|
| Day01 复习材料 | `2026-07-10-Day01-driving-rainy-雨天开车通勤/index.html` |
| Day02 复习材料 | `2026-07-10-Day02-pretend-food-beans-passion-fruit-过家家豆子百香果/index.html` |
| Day03 复习材料 | `2026-07-11-Day03-morning-routine-anchor-早晨流程与anchor/index.html` |
| Day04 复习材料 | `2026-07-14-Day04-finding-an-anchor-安顿自己/index.html` |
| Day05 复习材料 | `2026-07-15-Day05-driving-plants-驾驶与植物/index.html` |
| Day01 原始生成文件 | `2026-07-10-Day01-Driving-to-Work-on-a-Rainy-Day.html`，仅作历史备份 |
| v1 模板参考 | `templates-课件模板/html-interactive-review-v1/frozen-day01-reference.html` |

## 后续生成规则

| 项目 | 规则 |
|---|---|
| 文件夹命名 | `YYYY-MM-DD-DayXX-topic-中文主题` |
| 主文件 | `index.html` |
| 技术形态 | 单文件 HTML，内含 CSS 和 JavaScript |
| 运行方式 | 可直接双击打开，不依赖后端 |
| 互动能力 | 导航、学习进度、已掌握、折叠答案、深浅色、返回顶部、打印 PDF |
| 内容原则 | 课后复习优先；前面放快速复习，后面放详细回看和成长记录 |

## 模板迭代

界面优化单独在 `templates-课件模板/` 下迭代。每日课件生成时默认沿用最新确认模板，不在内容生成任务里临时改版式。
