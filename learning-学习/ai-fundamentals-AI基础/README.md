# AI 基础学习计划（4 周）

> 实践者路线：不从零学 ML，围绕「已有实践」往下一层补原理。  
> 每周 3h 左右，学完一块立刻在自己项目里用一次。

## 进度追踪

| 周 | 主题 | 状态 | 练手产出 |
|----|------|------|----------|
| 1 | 提示词工程 | 待开始 | 优化一版 Cursor 规则 |
| 2 | LLM 原理 | 待开始 | 写 5 条原理备忘 |
| 3 | AI Agent | 待开始 | 龙虾 AGENTS.md 对照笔记 |
| 4 | RAG 基础 | 待开始 | 用自己知识库跑通一个 QA |

---

## Week 1：提示词工程 — 从直觉到方法论

**目标**：把「凭感觉写 prompt / Cursor 规则」升级成有章法的。

| # | 资源 | 形式 | 时间 | 说明 |
|---|------|------|------|------|
| 1 | [Anthropic Prompt Engineering 文档](https://docs.anthropic.com/en/docs/intro-to-prompting) | 文档 | 40min | 日常用 Claude，这是最对口的官方指南 |
| 2 | [Anthropic 交互式教程（9 章 Jupyter）](https://github.com/anthropics/courses/tree/master/prompt_engineering_interactive_tutorial/Anthropic%201P) | 动手 | 90min | 重点 Ch4/5/6/8；Ch1-3 快速扫 |
| 3 | [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering/) | 文档 | 30min | 和 Anthropic 对比读，看共识与差异 |

**练手**：拿 `.cursor/rules/collaboration-preferences.mdc` 和 Anthropic 最佳实践对照，改一版提交。

---

## Week 2：LLM 原理 — 够用的那一层

**目标**：理解 token / 上下文 / temperature / embedding，解释「AI 怎么突然变笨了」。

| # | 资源 | 形式 | 时间 | 说明 |
|---|------|------|------|------|
| 1 | [Karpathy: Deep Dive into LLMs like ChatGPT](https://www.youtube.com/watch?v=7xTGNNLPyMI) | 视频 | 60min | 2025 最新版 3.5h，**先看前 1h**：训练、tokenization、窗口、temperature、幻觉 |
| 2 | [Jay Alammar: The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/) | 图文 | 40min | 全网最好 Transformer 可视化，看懂注意力矩阵即可 |
| 3 | [Karpathy: Intro to LLMs（1h 精简版）](https://www.youtube.com/watch?v=zjkBMFhNj_g) | 视频 | 可选 | 上面那个太长时的替代，2023 版更浓缩 |

**练手**：在 `docs/ai-collab-notes.md` 或本目录加一节「LLM 原理备忘」，用自己的话写 5 条理解。

---

## Week 3：AI Agent — 把已有实践系统化

**目标**：Cursor 规则里的 verification-loop、龙虾的 `.learnings/` 记忆系统——本质就是 Agent 模式。和行业框架对上号。

| # | 资源 | 形式 | 时间 | 说明 |
|---|------|------|------|------|
| 1 | [Anthropic: Building Effective Agents](https://www.anthropic.com/index/building-effective-agents) | 文章 | 45min | **最值得读**。简单可组合模式、Workflow vs Agent、agentic loop |
| 2 | [Lilian Weng: LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/) | 博客 | 60min | Planning / Memory / Tool Use 三大模块，框架性认知至今最好 |
| 3 | [OpenAI Function Calling 文档](https://platform.openai.com/docs/guides/function-calling) | 文档 | 30min | 工具调用技术实现：Schema → 模型决策 → 执行 → 回传 |
| 4 | [Anthropic Tool Use 教程](https://docs.anthropic.com/en/docs/tool-use-examples) | 文档 | 30min | Claude 侧工具调用，和 OpenAI 对比 |

**练手**：把 `super-lobster-template/AGENTS.md` 和 *Building Effective Agents* 对照，写几行笔记。

---

## Week 4：RAG 基础 — 让知识库可被 AI 查询

**目标**：理解 RAG 并跑通一个最小 demo。Obsidian 图谱、口径模板、SQL 资料都是理想输入。

| # | 资源 | 形式 | 时间 | 说明 |
|---|------|------|------|------|
| 1 | [LangChain 官方 RAG 教程](https://python.langchain.com/docs/tutorials/rag) | 动手 | 60min | 最精简入门：加载 → 切块 → embedding → 向量库 → 查询，40 行跑通 |
| 2 | [RAG Tutorial 2026: LangChain + ChromaDB](https://dev.to/ragavis-techjournali/rag-tutorial-2026-build-ai-chatbot-with-langchain-chromadb-step-by-step-guide-2hi) | 动手 | 45min | 带 Streamlit 前端的完整 demo |
| 3 | [Anthropic Search & Retrieval 附录](https://github.com/anthropics/courses/tree/master/prompt_engineering_interactive_tutorial/Anthropic%201P) | Notebook | 30min | Week 1 教程的附录，专讲检索 |

**练手**：拿 `knowledge-知识库/` 里几个 md 文件跑本地 RAG demo，试「问自己的知识库」。

---

## 不在本计划范围（以后按需）

| 内容 | 什么时候再学 |
|------|-------------|
| ML 经典算法 / 数学基础 | 想训模型或做算法岗时 |
| 微调（Fine-tuning） | API + prompt 不够用、需要领域专用模型时 |
| 完整 ML 课程（吴恩达等） | 想系统转 AI 工程师时 |
| 多模态 / 语音 / 视觉 | 有具体多模态项目需求时 |
