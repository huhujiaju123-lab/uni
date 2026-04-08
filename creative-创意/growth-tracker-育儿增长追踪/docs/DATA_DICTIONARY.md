# 数据字典 / Data Dictionary

方便在 Prisma Studio 中查看数据时对照。

---

## 数据表对照

| 英文表名 | 中文名称 | 说明 |
|----------|----------|------|
| Entry | 日志条目 | 用户输入的原始日志 |
| FactCard | 事实卡片 | Recorder Agent 生成的结构化数据 |
| ExpertAnalysis | 专家分析 | Expert Agent 生成的解读和建议 |
| AgentPrompt | 提示词版本 | Agent 的 System Prompt 版本管理 |
| WeeklySummary | 周摘要 | 每周自动生成的总结 |
| MonthlySummary | 月摘要 | 每月自动生成的总结 |
| Strategy | 策略库 | 已验证的有效/无效育儿策略 |
| ValuesPrinciple | 价值观原则 | 家庭育儿价值观 |
| ChildProfile | 孩子档案 | 孩子的基本信息配置 |

---

## Entry（日志条目）

| 字段 | 中文 | 类型 | 说明 |
|------|------|------|------|
| id | 编号 | String | 唯一标识 |
| rawText | 原始内容 | String | 用户输入的日志文本 |
| entryDate | 日志日期 | DateTime | 事件发生的日期 |
| childAge | 孩子年龄 | String? | 记录时的年龄快照，如"2岁3个月" |
| createdAt | 创建时间 | DateTime | 记录创建时间 |
| updatedAt | 更新时间 | DateTime | 最后更新时间 |

---

## FactCard（事实卡片）

| 字段 | 中文 | 类型 | 说明 |
|------|------|------|------|
| id | 编号 | String | 唯一标识 |
| entryId | 关联日志 | String | 关联的 Entry ID |
| oneLine | 一句话摘要 | String | AI 生成的简短摘要 |
| events | 事件列表 | JSON | 识别出的事件数组 |
| tags | 标签 | String[] | 自动生成的标签 |
| missingInfo | 缺失信息 | String[] | 可能需要补充的信息 |
| ageBucket | 年龄段 | String? | 0-6m, 6-12m, 1-2y, 2-3y... |
| embedding | 向量嵌入 | Vector? | 用于语义检索 |
| createdAt | 创建时间 | DateTime | 记录创建时间 |

### events 字段结构

```json
[
  {
    "type": "事件类型",      // behavior/emotion/milestone/health/social/cognitive/language/motor/sleep/feeding/other
    "description": "事件描述",
    "emotion": "情绪",       // positive/negative/neutral/mixed
    "context": "发生情境"
  }
]
```

**事件类型对照**:
| 英文 | 中文 |
|------|------|
| behavior | 行为 |
| emotion | 情绪 |
| milestone | 里程碑 |
| health | 健康 |
| social | 社交 |
| cognitive | 认知 |
| language | 语言 |
| motor | 运动 |
| sleep | 睡眠 |
| feeding | 饮食 |
| other | 其他 |

---

## ExpertAnalysis（专家分析）

| 字段 | 中文 | 类型 | 说明 |
|------|------|------|------|
| id | 编号 | String | 唯一标识 |
| factCardId | 关联事实卡 | String | 关联的 FactCard ID |
| interpretation | 专业解读 | String | AI 专家的解读分析 |
| suggestions | 建议列表 | JSON | 具体建议数组 |
| patterns | 模式识别 | JSON? | 识别到的行为模式 |
| riskFlags | 风险提示 | String[] | 需要关注的风险点 |
| createdAt | 创建时间 | DateTime | 记录创建时间 |

### suggestions 字段结构

```json
[
  {
    "category": "建议类别",  // action/observation/resource/caution
    "content": "建议内容",
    "priority": "优先级"     // high/medium/low
  }
]
```

**建议类别对照**:
| 英文 | 中文 |
|------|------|
| action | 行动建议 |
| observation | 观察建议 |
| resource | 学习资源 |
| caution | 注意事项 |

---

## AgentPrompt（提示词版本）

| 字段 | 中文 | 类型 | 说明 |
|------|------|------|------|
| id | 编号 | String | 唯一标识 |
| agentName | Agent名称 | String | recorder/expert/values/orchestrator |
| version | 版本号 | String | 如 v1.0.0 |
| systemPrompt | 系统提示词 | String | Agent 的完整 Prompt |
| enabled | 是否启用 | Boolean | 当前是否生效 |
| releaseNotes | 更新说明 | String? | 这次改了什么 |
| createdAt | 创建时间 | DateTime | 记录创建时间 |

---

## WeeklySummary（周摘要）

| 字段 | 中文 | 类型 | 说明 |
|------|------|------|------|
| id | 编号 | String | 唯一标识 |
| weekStart | 周开始 | DateTime | 本周第一天 |
| weekEnd | 周结束 | DateTime | 本周最后一天 |
| highlights | 亮点 | JSON | 本周亮点事件 |
| concerns | 关注点 | JSON | 需要关注的问题 |
| progress | 进步 | JSON | 观察到的进步 |
| patterns | 模式 | JSON | 识别的行为模式 |
| entryIds | 关联日志 | String[] | 本周的 Entry ID 列表 |
| createdAt | 创建时间 | DateTime | 记录创建时间 |

---

## MonthlySummary（月摘要）

| 字段 | 中文 | 类型 | 说明 |
|------|------|------|------|
| id | 编号 | String | 唯一标识 |
| monthStart | 月开始 | DateTime | 本月第一天 |
| monthEnd | 月结束 | DateTime | 本月最后一天 |
| milestones | 里程碑 | JSON | 重要的发展里程碑 |
| themes | 主题 | JSON | 本月主要主题 |
| growth | 成长概述 | JSON | 整体成长情况 |
| nextFocus | 下月关注 | JSON | 下个月的关注重点 |
| entryIds | 关联日志 | String[] | 本月的 Entry ID 列表 |
| createdAt | 创建时间 | DateTime | 记录创建时间 |

---

## Strategy（策略库）

| 字段 | 中文 | 类型 | 说明 |
|------|------|------|------|
| id | 编号 | String | 唯一标识 |
| category | 类别 | String | sleep/emotion/behavior/feeding... |
| description | 策略描述 | String | 具体的策略内容 |
| conditions | 适用条件 | String? | 什么情况下有效 |
| evidence | 证据 | String[] | 验证过的 Entry ID 列表 |
| status | 状态 | String | active(有效) / deprecated(弃用) |
| createdAt | 创建时间 | DateTime | 记录创建时间 |
| updatedAt | 更新时间 | DateTime | 最后更新时间 |

---

## ValuesPrinciple（价值观原则）

| 字段 | 中文 | 类型 | 说明 |
|------|------|------|------|
| id | 编号 | String | 唯一标识 |
| version | 版本 | String | V1, V2... |
| principle | 原则内容 | String | 具体的价值观原则 |
| reason | 修改原因 | String? | 为什么这样定 |
| isActive | 是否生效 | Boolean | 当前是否启用 |
| createdAt | 创建时间 | DateTime | 记录创建时间 |

---

## ChildProfile（孩子档案）

| 字段 | 中文 | 类型 | 说明 |
|------|------|------|------|
| id | 编号 | String | 唯一标识 |
| name | 姓名 | String | 孩子的名字 |
| birthday | 生日 | DateTime | 出生日期 |
| timezone | 时区 | String | 默认 Asia/Shanghai |
| focusAreas | 关注领域 | String[] | sleep/emotion/social... |
| createdAt | 创建时间 | DateTime | 记录创建时间 |
| updatedAt | 更新时间 | DateTime | 最后更新时间 |
