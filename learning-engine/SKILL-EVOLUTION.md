# Skill Evolution — 技能持续迭代项目

> 基于 Anthropic 内部 Skills 实战文章的启发，对当前所有 AI 编程相关 Skill 进行系统化优化。
> 这是一个长期项目，每次优化后在此文档更新进度。

---

## 一、项目起源

### 触发文章
- **标题**：构建 Claude Code 的经验：我们如何使用 Skills
- **作者**：Thariq Shihipar（Anthropic Claude Code 团队工程师）
- **原文**：`inbox-收藏箱/2026-03-23-构建Claude_Code的经验_Skills.txt`
- **博客**：`digested-已消化/2026-03-23-skills-blog.html`
- **播客**：`channels-频道/digest-收藏消化/output-输出/2026-03-23-skills-full-podcast.mp3`（14分25秒）

### 苏格拉底对话中的核心结论

**我对 Skill 的理解**：
> Skill 的本质不是"流程自动化"，而是**经验化扩展（Extension Points）**——人类把自己的经验输入给 AI。

**经验的三个层次**：
1. **该怎么做**（正面流程）→ 对应文章的 prompts / instructions
2. **不该怎么做**（踩坑点/护栏）→ 对应文章的 gotchas
3. **做了会怎样**（预期结果/验证标准）→ 对应文章的 validation

**我的理解边界**（诚实诊断）：
- 理解度约 40%，概念能跟上但不能落地成具体动作
- 原因：还没有从零完整构建过一个 Skill，缺乏动手经验
- 文章对我是 i+3 而非 i+1
- 解决方案：先动手做一个完整 Skill，再回来读文章

---

## 二、文章九种 Skill 类型 × 我的数据分析映射

| # | 文章类型 | 数据分析翻译 | 我已有的 Skill | 当前状态 |
|---|---------|-------------|--------------|---------|
| 1 | 库与API参考 | 表结构速查手册 | luckyus-data-query | ⚠️ 650行全量加载 |
| 2 | 产品验证 | 数据质量校验 | ab-experiment(部分) | ❌ 没有自动化验证 |
| 3 | 数据获取与分析 | 问题→数据的桥梁 | daily-report | ⚠️ 缺归因链路 |
| 4 | 业务流程自动化 | 日报/周报/月报 | daily-report, experiment-report | ⚠️ 无记忆机制 |
| 5 | 代码脚手架 | SQL 模板库 | ab-experiment(内嵌) | ✅ 已拆出模板文件 |
| 6 | 代码质量审查 | SQL 质量检查 | (散落在MEMORY) | ✅ 已建 shared-gotchas |
| 7 | CI/CD部署 | 报告部署 | (手动scp) | ❌ 待建 |
| 8 | 运维手册 | 异常排查手册 | daily-report(归因模块) | ❌ 未独立成 Skill |
| 9 | 基础设施运维 | 平台维护 | cyberdata-query | ⚠️ 低优先级 |

---

## 三、文章八个编写技巧 × 我的执行状态

| # | 技巧 | 核心要点 | 我的执行状态 |
|---|------|---------|-------------|
| 1 | 不要说显而易见的事 | 写 Claude 反复犯错的事，不写它已知的 | ⚠️ 部分做到 |
| 2 | 建踩坑点章节 | 逐步积累，每次犯错补一条 | ✅ 已建 shared-gotchas/gotchas.md（12条） |
| 3 | 渐进式披露 | 主文件精简，子文件按需加载 | ✅ ab-experiment 已重构 |
| 4 | 不要限制太死 | 区分硬规则和软指引 | ⚠️ 需逐个 Skill 检查 |
| 5 | 初始设置 | 动态配置存 config.json | ✅ ab-experiment 已加 config.json |
| 6 | description是触发条件 | 写"什么时候用"而非"做什么" | ⚠️ 部分 Skill 还是功能说明 |
| 7 | 记忆与数据存储 | 追加写入日志/JSON，实现 Skill 记忆 | ❌ daily-report 待加 history/ |
| 8 | 存储脚本与生成代码 | 固化原子模块，Claude 组合编排 | ❌ luckyus-data-query 待加 modules/ |

---

## 四、优化路线图

### 已完成

#### P3：shared-gotchas（新建）— 2026-03-23 ✅
- 创建 `~/.claude/skills/shared-gotchas/`
- `data-conventions.md`：13条数据口径硬规则
- `sql-patterns.md`：6个高频SQL模式
- `gotchas.md`：12条踩坑点（持续积累）
- 被 luckyus-data-query / ab-experiment / daily-report / share-the-luck / experiment-report 引用

#### P0：ab-experiment（重构）— 2026-03-23 ✅
- 原始：355行单文件 → 重构：62行主文件 + 9个子文件
- 上下文占用减少 83%
- 新增：`config.json`（当前实验动态配置）
- 新增：`references/`（4个能力拆分为独立文档）
- 新增：`templates/`（3个SQL模板文件）
- 踩坑点引用 shared-gotchas（不再重复维护）
- 备份：`skill.md.bak`

#### P1：luckyus-data-query（渐进式披露重构）— 2026-03-24 ✅
- 原始：SKILL.md 451行 + references 4文件共2104行 → 重构后：SKILL.md 111行 + references 8文件共1666行
- **SKILL.md 缩减 75%**（451→111行），日常查询只需读100行路由层
- **总行数减少 21%**（2104→1666行），三重重复→一处维护
- 删除：schema.md（100%冗余）、knowledge-base.md（拆散到6个新文件）、database-tables-catalog.md（枚举剥离后重写为 tables-catalog.md）
- 新建6个文件：enums.md / tables-core.md / kpi-dictionary.md / analysis-playbooks.md / user-segmentation.md / business-context.md
- 渐进式披露：L0(100行) → L1(+1子文件) → L2(+2-3子文件) → L3(探索性)
- modules/ 推迟（等观察1-2周再决定）

### 待执行

#### P2：daily-report（加记忆+自动验证）
**目标**：让日报 Skill 有记忆，能自动算周同比和标注异常

改造计划：
```
daily-report/
├── SKILL.md
├── references/sql_templates.md
├── history/                    # 新增：每日指标自动存档
│   └── YYYY-MM-DD.json        # {"cups":3420,"orders":2200,...}
├── validators/                 # 新增：数据质量校验规则
│   └── sanity_check.md        # 杯量>0 / 杯量<上周*2 / 新客占比<50%
└── scripts/
    └── save_history.py        # 新增：报告生成后自动存历史
```

验收标准：连续生成3天日报后，第4天自动算出周同比和趋势。

#### P4：experiment-report（配置外置）
**目标**：脚本顶部45行硬编码配置 → 外置为 JSON

改造计划：
```
experiment-report/
├── config/                     # 新增
│   ├── 0119-newcust.json
│   ├── 0212-oldcust.json
│   └── 0311-pricing.json
```

验收标准：新实验只需新建一个 JSON，不改 Python 代码。

#### P5：cyberdata-query（记忆自动更新）
**目标**：query_history 自动追加，auth 过期自动提醒

#### P6：share-the-luck（资源位配置外置）
**目标**：弹窗ID/Banner URL 从 skill.md 提取到 config.json

### 未来可能新增的 Skill

| Skill | 文章类型 | 说明 |
|-------|---------|------|
| investigate-drop | 类型8-运维手册 | "杯量为什么跌了"→自动走排查链路 |
| sql-reviewer | 类型6-质量审查 | 每次写完SQL自动检查口径 |
| deploy-report | 类型7-CI/CD | HTML报告一键部署到服务器 |
| production-mode | 按需钩子 | 生产数据防护（强制tenant/禁止DELETE/自动LIMIT） |

---

## 五、Skill 审计快照（2026-03-23）

### 现有 Skill 清单

| Skill | 主文件行数 | 文件夹结构 | 踩坑点 | 参考文件 | 脚本 | 配置 |
|-------|----------|---------|-------|---------|------|------|
| shared-gotchas | 16 | ✅ | ✅ 12条 | ✅ 3个 | — | — |
| ab-experiment | 62 | ✅ 重构 | ✅ 引用共享 | ✅ 4个 | — | ✅ config.json |
| luckyus-data-query | 451 | ✅ | ⚠️ 散落 | ✅ 3个 | ✅ 2个 | ✅ config.json |
| daily-report | 135 | ✅ 浅 | ✅ 有 | ✅ 1个 | ❌ | 依赖cyberdata |
| cyberdata-query | 210 | ✅ 中 | ✅ 有 | ✅ 2个 | ✅ 2个 | ✅ auth.json |
| share-the-luck | 129 | ✅ 浅 | ✅ 有 | ✅ 1个 | ✅ 1个 | ❌ |
| experiment-report | 158 | ✅ 中 | ✅ 有 | ✅ 1个 | ✅ 4个 | ⚠️ 硬编码 |
| ppt-generator | 166 | ✅ 中 | ✅ 有 | ✅ 2个 | ✅ 2个 | ✅ 4个assets |

### 跨 Skill 共享规则（已提取到 shared-gotchas）
- 租户过滤：`tenant = 'LKUS'`
- 成功订单：`status = 90`（DWD用 `order_status = 90`）
- 时区转换：ODS 用 `CONVERT_TZ`，DWD 用 `dt`/`local_dt`
- 排除测试店：`NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')`
- 用户剔除：`type NOT IN (3, 4, 5)`
- 杯量=COUNT(*) from order_item WHERE Drink，不是 COUNT(DISTINCT order_id)
- 实收仅饮品：`one_category_name = 'Drink'`

---

## 六、迭代原则

来自文章和我们对话的核心共识：

1. **不追求完美，先做一个** — 从最常踩的坑开始
2. **踩坑点逐步积累** — 每次 Claude 犯错补一条到 gotchas.md
3. **渐进式披露** — 主文件精简，详情按需加载
4. **一处维护，处处生效** — 公共规则放 shared-gotchas
5. **config 外置** — 动态配置不要硬编码在代码/文档里
6. **先手动再自动化** — 确认流程有价值了再写脚本
7. **一个活的 Skill 比一个完美但没人用的 Skill 有价值一万倍**

---

## 七、变更日志

### 2026-03-23（初始版本）
- 阅读 Anthropic Skills 实战文章，苏格拉底式对话消化
- 生成个性化博客 + 14分钟播客
- 审计全部 7 个核心 Skill
- 新建 shared-gotchas（P3）：13条口径 + 6个SQL模式 + 12条踩坑点
- 重构 ab-experiment（P0）：355行→62行 + 9个子文件
- 制定 P1-P6 优化路线图
