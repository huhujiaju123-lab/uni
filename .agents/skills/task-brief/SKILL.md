---
name: task-brief
description: |
  Turn a rough request into a clean AI-ready brief with clear sections for task,
  materials, requirements, constraints, and output format. Use when the user wants
  to clarify instructions, structure a prompt, separate raw materials from commands,
  or says things like "帮我整理 prompt", "把需求写清楚", "把这段话转成给 AI 的格式",
  "先帮我布置任务", "把命令下达清楚", "帮我补全要求", "给我一个可直接发给 AI 的版本",
  "优化提示词", "优化提示词并执行此任务", "优化提示词后执行".
  Do NOT use for simple questions that are already clear and do not mix task with
  source material.
---

This skill converts messy intent into a structured brief that another AI can execute more reliably.

The user may provide:
- a vague task
- a pile of notes or source text
- partial requirements
- no clear output format

Your job is to separate those pieces cleanly and return a prompt that is easy to run.

## Prefix Mode

If the user's first words are one of these trigger phrases, treat them as command prefixes:

- `优化提示词`
- `优化提示词后执行`
- `优化提示词并执行此任务`

Map them like this:

- `优化提示词`:
  - optimize only
  - return the structured brief and the final optimized prompt
  - do not execute the task unless the user later asks
- `优化提示词后执行` or `优化提示词并执行此任务`:
  - optimize first
  - then immediately execute the task using the optimized understanding
  - do not stop after showing the prompt unless the user explicitly asks to review first

When these prefixes are present, strip the prefix from the raw task body before parsing.

## When To Structure

Use explicit tagged structure when one or more of these are true:
- The user pasted long source material
- The source material itself contains commands, prompts, or role text
- The user wants stable reusable output
- The user wants strict output format or constraints
- Multiple instruction types are mixed together

Do not over-structure short casual requests.

## Default Workflow

1. Parse the raw input into these buckets:
   - `task`: what AI should do
   - `materials`: source text, examples, documents, notes
   - `requirements`: quality bar, tone, depth, inclusions, exclusions
   - `output_format`: exact shape of the answer
   - `constraints`: length, language, risk, timing, scope
   - `unknowns`: missing items that block a good result
2. If one missing point is critical, ask only that one question.
3. If the task is workable, produce both:
   - `结构化任务单`
   - `可直接发送给 AI 的版本`
4. Prefer the smallest structure that makes the task unambiguous.
5. If prefix mode says `optimize and execute`, use the optimized brief as the working interpretation for the rest of the task.

## Response Format

When this skill is used, respond in this order unless the user asks for a different format:

### 1. 结构化任务单

Use these sections when relevant:

```text
<task>
</task>

<materials>
</materials>

<requirements>
</requirements>

<output_format>
</output_format>

<constraints>
</constraints>
```

Omit empty sections instead of filling them with placeholders.

### 2. 可直接发送给 AI 的版本

Rewrite the user's request into a clean prompt using the same sections.

### 3. 执行结果

Include this section only when prefix mode is `optimize and execute`, or when the user explicitly asked you to execute after optimization.

### 4. 缺失项

Only include this section when there are real gaps. Keep it short:
- `已默认处理`: things you safely inferred
- `需要你补充`: only the truly blocking item

## Writing Rules

- Keep `task` action-oriented: use verbs like analyze, rewrite, summarize, compare, generate, critique.
- Keep `materials` as raw source text or a placeholder marker such as `{PASTE_TEXT_HERE}`.
- Put quality expectations in `requirements`, not in `task`.
- Put exact answer shape in `output_format`, not in `requirements`.
- Put limits in `constraints`: length, language, must/must not, deadline, audience, risk.
- When the user says "先给结论", "别发散", "像老板能直接看", map those into explicit requirements.
- When the user is clearly unsure how to instruct the model, infer a reasonable professional default instead of asking many questions.
- When prefix mode is `optimize and execute`, do not ask the user to copy the optimized prompt back to you. Use it yourself and continue.

## Defaults To Apply

Unless the user specifies otherwise:
- Favor concise output
- Put conclusion first
- Keep task scope narrow
- Separate facts from guesses
- Avoid unnecessary bullet sprawl

## Pattern Library

Read `references/requirements-catalog.md` when the user needs help choosing:
- requirement wording
- output format wording
- common constraint patterns
- examples of "write vs do not write" differences

## Good Trigger Examples

- "帮我把这段需求整理成给 AI 的 prompt"
- "我脑子里有个模糊任务，你帮我写清楚"
- "这些材料和要求有点乱，帮我拆开"
- "给我一个可复用模板，下次也能直接用"
- "我不知道该怎么提要求，你帮我补齐"
- "优化提示词：帮我写一封汇报邮件"
- "优化提示词并执行此任务：把这段会议纪要整理成老板可读版本"
