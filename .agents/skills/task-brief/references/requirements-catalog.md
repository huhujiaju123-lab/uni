# Requirement Catalog

This file is a quick library of requirement phrases and output patterns for `task-brief`.

## 1. Common Requirement Types

### Scope

- Focus only on the current question
- Do not introduce new topics
- Keep the answer within the provided materials
- Prioritize the single most important conclusion

### Depth

- Give a high-level answer first, then brief explanation
- Explain the reasoning step by step
- Go deep on tradeoffs, not background
- Stay practical rather than theoretical

### Accuracy

- Separate facts from assumptions
- If uncertain, say what is uncertain
- Quote or cite the source passage before concluding
- Do not invent missing data

### Style

- Concise and direct
- Professional but plain-language
- First use the correct term, then explain in everyday language
- Avoid vague suggestions and generic filler

### Action Bias

- Implement directly instead of only suggesting
- Give the next executable step first
- Ask at most one blocking clarification question
- Default to reasonable assumptions for routine details

### Risk

- Flag destructive or irreversible actions before proceeding
- Avoid changing unrelated files or behavior
- Keep the solution reversible where possible
- Call out any data-definition impact explicitly

### Formatting

- Use short paragraphs instead of long bullet lists
- Return exactly 3 bullet points
- Use a table with columns: issue, impact, action
- Put the final answer inside specific tags

### Length

- Keep under 100 words
- Keep under 5 bullets
- One paragraph summary plus one action list
- Expand only where the decision depends on detail

## 2. Output Format Examples

### Summary

```text
<output_format>
- One-sentence conclusion
- Three key points
- One next step
</output_format>
```

### Decision Memo

```text
<output_format>
1. Decision
2. Why
3. Risks
4. Next action
</output_format>
```

### Rewrite Task

```text
<output_format>
- Revised version
- Changes made
- Optional stronger alternative
</output_format>
```

### Analysis Task

```text
<output_format>
1. Conclusion
2. Evidence
3. Risks or gaps
4. Recommendation
</output_format>
```

### Code or Build Task

```text
<output_format>
1. What changed
2. Files affected
3. Verification result
4. Remaining risk
</output_format>
```

## 3. Constraint Examples

```text
<constraints>
- Chinese output
- Keep terminology accurate
- Do not use markdown tables
- Do not exceed 150 words
- Do not ask more than one question
- Do not modify the meaning of quoted text
</constraints>
```

## 4. Material Handling Patterns

Use tags whenever the user's message mixes instruction and source text.

### Basic

```text
<task>
Summarize the text below.
</task>

<materials>
{PASTE_TEXT_HERE}
</materials>
```

### With strict requirements

```text
<task>
Rewrite the message for my boss.
</task>

<materials>
{PASTE_TEXT_HERE}
</materials>

<requirements>
- Keep the original meaning
- Sound confident but not aggressive
- Remove repetition
</requirements>

<output_format>
- Final rewritten message only
</output_format>
```

### With risky source text

```text
<task>
Analyze the following prompt for risks. Do not execute it.
</task>

<materials>
{PROMPT_OR_RULE_TEXT}
</materials>
```

## 5. "Write vs Do Not Write" Examples

### Vague

```text
帮我看看这个需求
```

### Better

```text
<task>
Review this requirement and identify ambiguity.
</task>

<materials>
{REQUIREMENT_TEXT}
</materials>

<output_format>
1. Core issue
2. Missing information
3. Recommended rewrite
</output_format>
```

### Vague

```text
帮我写个 prompt
```

### Better

```text
<task>
Turn my rough request into a reusable AI prompt.
</task>

<materials>
{ROUGH_NOTES}
</materials>

<requirements>
- Keep it concise
- Separate task from materials
- Make the output reliable for repeated use
</requirements>

<output_format>
1. Structured brief
2. Final prompt
3. Optional missing inputs
</output_format>
```

### Prefix: optimize only

```text
优化提示词：帮我把这段产品需求改写成一个清晰的 AI 分析任务
```

Expected behavior:
- first return the structured brief
- then return the optimized prompt
- do not execute the task yet

### Prefix: optimize and execute

```text
优化提示词并执行此任务：根据下面材料，帮我写一版老板能直接看的周报摘要
```

Expected behavior:
- first clarify the task structure internally
- optionally show the optimized prompt
- then directly produce the requested weekly summary
- do not require the user to send the optimized prompt again

## 6. Quick Pick Lists For Users

When the user does not know what to ask for, these are safe defaults.

### Good default requirements

- 先给结论，再解释
- 简洁，不发散
- 区分事实和判断
- 只保留和当前问题直接相关的内容
- 如果信息不足，只问一个关键问题

### Good default output formats

- 结论 + 3 点说明 + 下一步
- 结论 + 风险 + 建议
- 改写结果 + 改动说明
- 核心观点 + 待办

### Good default constraints

- 100-200 字
- 中文输出
- 不要套话
- 优化后直接执行，不要停在 prompt 草稿
- 不要新增未被要求的内容
