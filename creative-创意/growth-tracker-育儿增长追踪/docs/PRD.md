# 成长日记 - 产品需求文档 (PRD)

## 产品概述

**产品名称**: 成长日记 (Growth Tracker)

**产品定位**: AI 驱动的智能育儿日志与成长分析系统

**目标用户**: 希望科学记录和理解孩子成长的家长

**核心价值**: 将碎片化的育儿观察转化为可追溯、可分析、可学习的成长档案

---

## 核心需求

### 用户痛点

1. 育儿记录零散，难以回顾和发现规律
2. 缺乏专业视角解读孩子的行为和发展
3. 相似场景反复出现，但忘记之前的应对策略
4. 想坚持记录，但格式不统一、难以坚持

### 解决方案

通过 AI Agent 系统实现：
- **结构化记录**: 自动将随意的日志转为标准化事实卡
- **专业解读**: 基于儿童发展知识提供专家级分析
- **智能检索**: 快速找到相关历史记录和有效策略
- **持续学习**: 系统不断学习家庭的育儿模式和价值观

---

## 系统架构

### 🏗️ Prompt Registry（提示词注册中心）

| 字段 | 说明 |
|------|------|
| agentName | recorder / expert / values / orchestrator |
| promptVersion | v1.0.0、v1.0.1… |
| systemPrompt | Agent 的系统提示词 |
| enabled | true/false（支持回滚） |
| releaseNotes | 版本更新说明 |


**运行时策略**:
- Orchestrator 每次调用 Agent 时，根据 agentName 拉取当前启用版本
- 支持灰度发布：对部分日志使用新版本，观察效果再全量
- 关键收益：调整 Agent 行为只需改 Registry，不影响页面与数据结构

### 🧠 Agent 流水线

```
用户输入 → Recorder → FactCard → 检索上下文 → Expert → 分析建议 → 存储
```

| Agent | 输入 | 输出 | 职责 |
|-------|------|------|------|
| Recorder | rawText | FactCard (JSON) | 提取事实，结构化记录 |
| Expert | FactCard + 上下文 | 分析建议 | 专业解读，给出建议 |
| Values | FactCard + 原则库 | 价值观反思 | 确保决策符合价值观 |
| Orchestrator | - | - | 编排调用各 Agent |

### 📚 四层记忆系统

#### 1. 事实层（Event Store）
- 永远保存原始数据，是"真相来源"
- 存储：rawText、FactCard、entryDate、ageSnapshot

#### 2. 索引层（Retrieval Index）

**2.1 标签/结构化索引**
- 按 tags、ageBucket、场景、行为类型查询
- 用于"找同类事件"

**2.2 语义检索索引（Embedding）**
- 对 rawText + oneLine + 关键事件做 embedding
- 用于"语义相似"检索

**检索原则**:
- 每次给 Expert 的历史上下文：最多 6 条
- 组合策略：最近 3 条 + 相似 3 条（去重）

#### 3. 周期摘要层
- WeeklySummary: 本周亮点、关注点、进步、模式
- MonthlySummary: 里程碑、主题、成长概述、下月关注

#### 4. 原则库

**4.1 策略库（Strategy Library）**
```
category: sleep / emotion / behavior / feeding
description: "睡前故事比手机视频更有助入睡"
conditions: "困倦时效果下降；在家比在公共场合更好"
evidence: [entryId列表]
status: active / deprecated
```

**4.2 价值观原则库（Values Principles）**
- 版本化：V1/V2…
- 每条原则短句化
- 记录修改原因

---

## 数据模型

### Entry（原始日志）
```typescript
{
  id: string
  rawText: string      // 用户原始输入
  entryDate: Date      // 事件发生日期
  childAge: string     // 年龄快照
  createdAt: Date
}
```

### FactCard（结构化事实卡）
```typescript
{
  id: string
  entryId: string
  oneLine: string      // 一句话摘要
  events: Event[]      // 事件列表
  tags: string[]       // 标签
  missingInfo: string[] // 缺失信息提示
  ageBucket: string    // 年龄段
  embedding: vector    // 向量嵌入
}
```

### Event（事件）
```typescript
{
  type: 'behavior' | 'emotion' | 'milestone' | 'health' | 'social' | 'cognitive' | 'language' | 'motor' | 'sleep' | 'feeding' | 'other'
  description: string
  emotion: 'positive' | 'negative' | 'neutral' | 'mixed'
  context: string      // 发生情境
}
```

### ExpertAnalysis（专家分析）
```typescript
{
  id: string
  factCardId: string
  interpretation: string  // 专业解读
  suggestions: Suggestion[]
  patterns: Pattern[]
  riskFlags: string[]
}
```

---

## 功能模块

### MVP (V1.0)

- [x] 日志输入页面
- [x] Recorder Agent（文本 → FactCard）
- [x] Expert Agent（FactCard → 分析建议）
- [x] 时间线展示
- [x] 标签检索
- [x] Prompt Registry 热更新

### V1.1（计划中）

- [ ] 向量语义检索（pgvector）
- [ ] 周摘要自动生成
- [ ] 策略库 CRUD
- [ ] 孩子档案配置

### V1.2（计划中）

- [ ] Values Agent 集成
- [ ] 价值观原则编辑页
- [ ] 月度报告
- [ ] 数据导出

### V2.0（远期）

- [ ] 多孩子支持
- [ ] 知识包（Knowledge Pack）
- [ ] 家庭成员协作
- [ ] 移动端适配

---

## 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端 | Next.js 14 + React 18 | 全栈框架，Vercel 免费部署 |
| 样式 | TailwindCSS | 原子化 CSS |
| 数据库 | PostgreSQL + pgvector | Supabase 免费层 |
| ORM | Prisma | 类型安全的数据库访问 |
| LLM | OpenAI GPT-4o | Agent 驱动 |
| 部署 | Vercel | 免费层，支持扩展 |

---

## 非功能需求

### 数据安全
- 敏感配置（API Key、数据库密码）存储在 .env，不提交到代码库
- 数据库使用 SSL 连接
- 未来考虑端到端加密

### 性能
- Agent 调用异步处理，避免阻塞 UI
- 检索结果缓存
- 分页加载历史记录

### 可维护性
- Prompt 热更新，无需重新部署
- 模块化 Agent 设计，可独立升级
- TypeScript 类型安全

---

## 成功指标

1. **使用频率**: 用户每周记录 ≥ 3 次
2. **留存率**: 30 天留存 ≥ 50%
3. **满意度**: AI 分析有用评分 ≥ 4/5
4. **数据完整性**: 0 数据丢失事件
 