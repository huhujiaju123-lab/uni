# 对话专家模块 - 架构设计

## 功能定位

让家长可以随时和 AI 专家"聊天"，讨论孩子的发展情况、疑惑、具体问题。

### 与现有 Expert Agent 的区别

| 维度 | Expert Agent（现有） | Chat Agent（新增） |
|------|---------------------|-------------------|
| 触发方式 | 自动（日志提交后） | 手动（用户发起） |
| 交互模式 | 单次输出 | 多轮对话 |
| 上下文 | 单条日志 + 检索 | 全部历史 + 对话记忆 |
| 输出格式 | 结构化 JSON | 自然语言 |
| 目的 | 记录分析 | 答疑解惑 |

---

## 新增数据模型

### Conversation（对话会话）

```prisma
model Conversation {
  id          String    @id @default(cuid())
  title       String?   // 对话标题（可自动生成）
  summary     String?   // 对话摘要（用于后续检索）
  status      String    @default("active") // active / archived

  messages    Message[]

  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt
}
```

### Message（对话消息）

```prisma
model Message {
  id             String   @id @default(cuid())
  conversationId String
  conversation   Conversation @relation(fields: [conversationId], references: [id])

  role           String   // user / assistant
  content        String   @db.Text

  // 可选：记录这条回复参考了哪些数据
  referencedEntryIds String[]  // 引用的日志 ID

  createdAt      DateTime @default(now())
}
```

---

## 新增 Agent

### Chat Agent（对话专家）

**职责**：基于孩子的成长档案，与家长进行多轮对话

**System Prompt 设计要点**：

```markdown
你是一位资深的儿童发展专家，正在和家长讨论他们孩子的成长情况。

## 你拥有的信息
- 孩子档案：{childProfile}
- 最近记录摘要：{recentSummary}
- 相关历史记录：{relevantEntries}（根据对话内容动态检索）

## 对话原则
1. **循证回答**：尽量基于已有记录给出建议，必要时引用具体日期的记录
2. **适度追问**：如果信息不足，礼貌地询问更多细节
3. **发展视角**：从儿童发展规律解读，避免过度焦虑
4. **尊重价值观**：参考家长的育儿价值观原则
5. **坦诚局限**：对于医学问题建议咨询专业医生

## 回答风格
- 温和、专业、有同理心
- 先理解家长的担忧，再给出建议
- 建议要具体、可操作
```

---

## 对话流程

```
用户提问
    ↓
检索相关上下文
  - 最近 N 条记录摘要
  - 与问题语义相关的历史记录
  - 相关策略库条目
  - 对话历史（保持连贯）
    ↓
Chat Agent 生成回复
    ↓
存储 Message
    ↓
返回给用户
```

### 上下文检索策略

```typescript
interface ChatContext {
  // 孩子基本信息
  childProfile: ChildProfile

  // 最近记录概览（固定）
  recentSummary: {
    lastWeek: string      // 最近一周的摘要
    recentEntries: Entry[] // 最近 5 条记录的 oneLine
  }

  // 动态检索（根据用户问题）
  relevantEntries: Entry[] // 语义相关的 3-5 条记录
  relevantStrategies: Strategy[] // 相关策略

  // 对话历史（保持连贯）
  conversationHistory: Message[] // 最近 10 条对话
}
```

---

## API 设计

### POST /api/chat

**请求**：
```typescript
{
  conversationId?: string  // 可选，不传则创建新对话
  message: string          // 用户消息
}
```

**响应**：
```typescript
{
  conversationId: string
  reply: string            // AI 回复
  references?: string[]    // 引用的日志 ID（可选）
}
```

### GET /api/chat/conversations

获取对话列表

### GET /api/chat/conversations/:id

获取单个对话的所有消息

---

## 前端页面

### 新增页面：`/chat`

```
┌─────────────────────────────────────────────┐
│  💬 和专家聊聊                               │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ [历史对话列表]                       │   │
│  │ · 关于睡眠问题的讨论 (1月14日)       │   │
│  │ · 入园焦虑怎么办 (1月10日)           │   │
│  │ + 开始新对话                         │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 👤 最近孩子总是半夜醒来，有什么      │   │
│  │    办法吗？                          │   │
│  │                                      │   │
│  │ 🤖 根据最近两周的记录，我注意到      │   │
│  │    孩子在1月12日和1月14日都有夜醒    │   │
│  │    的情况。让我们来分析一下...       │   │
│  │                                      │   │
│  │ 👤 是的，而且醒来后很难再入睡        │   │
│  │                                      │   │
│  │ 🤖 这种情况可能和...                 │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 输入你的问题...                  [➤] │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 与现有系统的整合

### 1. Prompt Registry 扩展

新增 `chat` 类型的 Agent Prompt：

```typescript
agentName: 'chat'  // 新增
```

### 2. 检索系统复用

Chat Agent 复用现有的检索模块，但需要增强：
- 支持基于对话内容动态检索
- 支持引用具体日志

### 3. 导航更新

```
┌──────────────────────────────────┐
│ 📖 成长日记                      │
├──────────────────────────────────┤
│ [记录] [时间线] [💬 聊聊]        │
└──────────────────────────────────┘
```

---

## 对话记忆管理

### 短期记忆（对话内）
- 保留完整对话历史
- 传递给 LLM 的上下文窗口限制（最近 10 条）

### 长期记忆（跨对话）
- 对话结束后生成摘要
- 摘要存入 `Conversation.summary`
- 可用于后续检索

### 对话归档
- 超过 30 天的对话自动归档
- 归档对话只保留摘要，不加载详情

---

## 实现优先级

### Phase 1（MVP）
- [x] Conversation / Message 数据模型
- [x] Chat Agent 基础实现
- [x] POST /api/chat 接口
- [x] 简单聊天界面

### Phase 2
- [ ] 对话历史列表
- [ ] 引用日志功能（点击跳转）
- [ ] 对话摘要自动生成

### Phase 3
- [ ] 对话搜索
- [ ] 导出对话记录
- [ ] 对话分享
