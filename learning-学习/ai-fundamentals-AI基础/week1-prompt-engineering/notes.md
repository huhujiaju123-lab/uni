# Week 1：提示词工程笔记

> 来源：Anthropic Prompting Best Practices（2026 最新，覆盖 Claude 4.6）

## 一、通用原则（General Principles）

### 1. 清晰直接（Be Clear and Direct）
- 把 Claude 当成一个能力极强但缺乏你项目上下文的新同事
- **黄金法则**：把 prompt 给一个不了解任务背景的同事看，如果他也会困惑，Claude 也会
- 具体说明输出格式（output format）和约束条件（constraints）
- 需要顺序或完整性时，用编号列表

```
❌ 中："帮我做一个数据看板"
   EN: "Create an analytics dashboard"

✅ 中："帮我做一个数据看板，尽可能包含相关功能和交互。不要只做基础版本，做一个功能完整的实现。"
   EN: "Create an analytics dashboard. Include as many relevant features and interactions as possible. Go beyond the basics to create a fully-featured implementation."
```

### 2. 给上下文 / 说明动机（Add Context / Motivation）
- 告诉 Claude **为什么**要这样做，而不只是**要什么**
- Claude 够聪明，能从动机（motivation）泛化出更多合理行为

```
❌ 中："绝对不要用省略号"
   EN: "NEVER use ellipses"

✅ 中："你的回复会被文字转语音（TTS, Text-to-Speech）引擎朗读，所以不要用省略号，TTS 不知道怎么处理它。"
   EN: "Your response will be read aloud by a text-to-speech engine, so never use ellipses since the TTS engine will not know how to pronounce them."
```

### 3. 用好示例（Few-shot / Multishot Prompting）
- 3-5 个示例（examples）效果最佳
- 示例要：相关（relevant）、多样（diverse）、结构化（structured，用 XML tags 包裹）
- 可以让 Claude 帮你评估示例质量、生成补充示例

### 4. XML 标签结构化（Structure with XML Tags）
- 指令（instructions）、上下文（context）、示例（examples）、变量输入（variable input），各用不同 tag 包裹
- 标签名一致、有描述性
- 内容有层级时可嵌套（nested tags）

### 5. 角色设定（Role Prompting）
- system prompt 里一句话设定角色（role），就能聚焦行为和语气（tone）

```
中："你是一个专注于 Python 的编程助手。"
EN: "You are a helpful coding assistant specializing in Python."
```

### 6. 长上下文技巧（Long Context Prompting）
- **长文档放最前面**，查询（query）/指令放后面 → 响应质量可提升 30%
- 多文档用 `<documents><document index="1">` 结构化
- 让 Claude **先引用原文（quote）再作答**，减少噪音干扰

---

## 二、输出与格式控制（Output & Formatting）

### 7. 说「做什么」而不是「不做什么」（Positive Instructions）

```
❌ 中："回复里不要用 markdown"
   EN: "Do not use markdown in your response"

✅ 中："用流畅的散文段落来组织你的回复。"
   EN: "Your response should be composed of smoothly flowing prose paragraphs."
```

### 8. 用 XML 格式指示器（XML Format Indicators）

```
中："把回复的正文部分写在 <正文> 标签里。"
EN: "Write the prose sections of your response in <prose> tags."
```

### 9. Prompt 风格 ≈ 输出风格（Prompt Style Mirrors Output Style）
- 你 prompt 里用 markdown，输出就倾向 markdown
- 想要纯文本（plain text）？prompt 里也去掉 markdown

### 10. 控制详细格式（Verbosity Control）
- Claude 4.6 默认更简洁（concise）、更自然
- 如果需要更多可见度：

```
中："完成工具调用（tool use）任务后，给我一个简短的完成总结。"
EN: "After completing a task that involves tool use, provide a quick summary of the work you've done."
```

- 如果要减少列表/加粗，用 `<avoid_excessive_markdown_and_bullet_points>` 包裹详细指引

---

## 三、工具调用（Tool Use）

### 11. 明确要求行动（Be Explicit About Actions）

```
❌ 中："你能建议一些改进这个函数的方法吗？"  → Claude 只会建议（suggest）
   EN: "Can you suggest some changes to improve this function?"

✅ 中："修改这个函数，提升它的性能。"  → Claude 会实际改（implement）
   EN: "Change this function to improve its performance."
```

### 12. 控制行动倾向（Action Bias Control）
- 更主动（proactive）：`<default_to_action>` 标签
- 更谨慎（conservative）：`<do_not_act_before_instructions>` 标签

### 13. 并行工具调用（Parallel Tool Calling）
- Claude 4.6 天然擅长并行调用（同时搜索、同时读文件、同时执行命令）
- 用 `<use_parallel_tool_calls>` 可以提到接近 100% 并行率
- 想要串行（sequential）：

```
中："按顺序逐步执行，每步之间稍作停顿。"
EN: "Execute operations sequentially with brief pauses between each step."
```

---

## 四、思考与推理（Thinking & Reasoning）

### 14. Adaptive Thinking（自适应思考，Claude 4.6 新特性）
- 自动根据 effort 参数 + 问题复杂度，决定是否 & 多深地思考（think）
- 替代了之前的 `budget_tokens` 手动控制
- effort 档位：low / medium / high / max

### 15. 减少过度思考（Reduce Overthinking）

```
中："选定一个方向就坚持执行，除非遇到直接推翻你判断的新信息，否则不要反复重新考虑。"
EN: "Choose an approach and commit to it. Avoid revisiting decisions unless you encounter new information that directly contradicts your reasoning."
```

### 16. 引导思考方向（Guide Reasoning）

```
中："拿到工具调用结果后，先仔细评估质量，确定最优的下一步，再继续行动。"
EN: "After receiving tool results, carefully reflect on their quality and determine optimal next steps before proceeding."
```

- 可以在 few-shot 示例里放 `<thinking>` 标签，演示推理模式（reasoning pattern）

### 17. 自我检查（Self-verification）

```
中："完成之前，对照 [验收标准] 自查一遍。"
EN: "Before you finish, verify your answer against [test criteria]."
```

- 对代码和数学任务特别有效

---

## 五、Agent 系统（Agentic Systems）

### 18. 长程推理 & 状态追踪（Long-horizon Reasoning & State Tracking）
- Claude 4.6 有上下文感知（context awareness）能力，能追踪剩余 token 预算（token budget）
- 多窗口工作流（multi-context window workflow）：第一个窗口建框架 → 后续窗口迭代 todo list
- 用 JSON 追踪结构化状态（structured state），用纯文本记录进展（progress notes）

### 19. 自主性 vs 安全性（Autonomy vs Safety）
- 默认 Claude 可能会删文件、force push 等高风险操作
- 加提示让它区分：可逆本地操作（reversible local actions，放行）vs 破坏性/外部可见操作（destructive / externally visible actions，先确认）

### 20. 子 agent 编排（Subagent Orchestration）
- Claude 4.6 天然会委派（delegate）子 agent
- 可能过度使用 → 加指引：

```
中："简单任务、串行操作、单文件修改 → 直接做，不要派子 agent。"
EN: "For simple tasks, sequential operations, single-file edits → work directly rather than delegating to subagents."
```

### 21. Prompt Chaining（提示词链）
- 有了 adaptive thinking，多数多步推理（multi-step reasoning）Claude 内部就能处理
- 显式 chaining 的价值：需要检查中间输出（intermediate outputs）、或强制特定流水线结构时
- 最常用模式：生成（generate）→ 审核（review）→ 优化（refine）

---

## 六、与你现有实践的对照

| Anthropic 建议 | 你的 `.cursor/rules/` 现状 | 差距/机会 |
|---------------|--------------------------|----------|
| 给上下文 & 动机（context & motivation） | collaboration-preferences 有「双层解释」 | ✅ 已对齐 |
| XML 结构化（XML structuring） | 部分规则用了标签 | 可以更系统化 |
| 角色设定（role prompting） | 无显式 system role | 可补充 |
| 行动倾向控制（action bias） | 有「先实现再解释」 | ✅ 已对齐 |
| 自我检查（self-verification） | 有 Verification-Loop 4 步验证 | ✅ 已对齐 |
| 安全升级（risk escalation） | 有 risk-escalation 规则 | ✅ 已对齐 |
| 减少过度工程（over-engineering） | 有「如无必要勿增实体」 | ✅ 已对齐 |
| 子 agent 控制（subagent orchestration） | 无 | 暂不加，影响有限 |
| 任务边界提示（task boundary signal） | 新增：任务切换时主动提示开新对话 | ✅ 已落地 |

---

## 学习进度

- [x] 资源 1：Anthropic Prompt Engineering 文档
- [ ] 资源 2：Anthropic 交互式教程（Ch4/5/6/8 重点）
- [ ] 资源 3：OpenAI Prompt Engineering Guide（对比读）
- [x] 练手：对照最佳实践改一版 Cursor 规则（新增任务边界提示）
