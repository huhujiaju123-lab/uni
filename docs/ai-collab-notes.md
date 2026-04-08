# AI 协作笔记

这个文档用于记录可迭代的协作偏好与试验结果。
需要强制执行的内容，应升级到 `.cursor/rules/collaboration-preferences.mdc`。

## 当前默认约定

- 解释风格：先术语，再自然语言解释。
- 协作目标：保持上下文干净，减少不必要流程复杂度。
- 偏好行为：常规步骤由助手自动判断，必要时再提问确认。

## 20% 精华落地（MVP Harness）

### 固定流程 A：日常分析流
- 需求澄清 -> SQL 拆分 -> 结果输出 -> 口径记录 -> checkpoint commit。

### 固定流程 B：收工复盘流
- 今日变更 -> 风险点 -> 明日第一步。

### 口径变更记录模板（Metric Definition Change Log）

```md
## 口径版本：vX.Y（YYYY-MM-DD）
- 字段（Fields）：
- 时间窗（Time Window）：
- 人群范围（Population）：
- 去重规则（Dedup Rule）：
- 变更原因（Why）：
- 影响指标（Impacted Metrics）：
```

## 每周复盘模板

建议每周一次（或一次重要项目后）填写：

```md
## YYYY-MM-DD

### 有效做法（What worked）
- 

### 摩擦点（Friction points）
- 

### 建议新增规则（Rule updates）
- 

### 保留 / 删除（Keep / Drop）
- Keep:
- Drop:
```

## ECC 按需参考清单（不默认接入）

**约定**：下列项**不**作为本仓库常驻规则或自动流程；**写项目时**若场景匹配，由助手主动建议「是否安装 / 是否按该 playbook 执行」，**经你确认后再动**。

**源码位置**（本地）：`imports-外部导入-staging/everything-claude-code/`；官方：<https://github.com/affaan-m/everything-claude-code>

### A. 已单独过完、结论为「不接入」、可口头等价

| 项 | 用途摘要 | 何时可考虑 |
|----|----------|------------|
| `commands/checkpoint.md` | 检查点 + `.claude/checkpoints.log` | 需要阶段锚点时：优先 **commit / `git tag`** |
| `commands/verify.md` | build / 类型 / lint / 测试全套 | 工程仓库发版或 PR 前；可口头按该顺序跑 |
| `commands/code-review.md` | 未提交 diff 安全 + 质量清单 | 改动面大或含敏感逻辑时 |
| `commands/plan.md` | 先规划、确认再写码 | 大功能 / 多文件 / 架构取舍时 |
| `skills/security-scan/SKILL.md` | AgentShield 扫 `.claude/` 配置 | 维护 **`.claude/`、MCP、hooks** 时：`npx ecc-agentshield scan` |
| `commands/learn.md`（`/learn`） | 抽模式写入 `~/.claude/skills/learned/` | 更推荐用本笔记 **复盘 + Living Spec** 升格规则 |

### B. 工程 / 测试向（按需）

| 项 | 用途摘要 | 何时可考虑 |
|----|----------|------------|
| `commands/tdd.md` | TDD + 覆盖率门禁 | 以自动化测试为主的前后端项目 |
| `commands/e2e.md` | Playwright 端到端 | 有关键用户链路的前端产品 |
| `commands/build-fix.md` | 逐项修构建与类型错误 | `build` / `tsc` 持续失败时 |
| `commands/refactor-clean.md` | knip/depcheck 等清死代码 | 明确要做依赖与死代码清理（**高风险，需确认**） |
| `commands/test-coverage.md` | 覆盖率分析 | 项目已接入测试套件且要看门禁 |

### C. 多模型 / 编排 / 自治环（重，默认不推荐）

| 项 | 用途摘要 | 何时可考虑 |
|----|----------|------------|
| `commands/multi-plan.md` 等 multi-* | 多模型规划/执行、`.claude/plan` | 已深度使用 **Claude Code + 外部 codeagent** 时 |
| `commands/orchestrate.md` | 固定代理链 + tmux/worktree | 复杂多阶段任务且愿意承担编排成本时 |
| `commands/loop-start.md` / `loop-status.md` | 托管自治循环 | 明确要跑自主循环且能接受风险与 hook 依赖时 |
| `commands/harness-audit.md` | 对 ECC 自身 harness 打分 | 仅在 **everything-claude-code 仓库内** 有对应脚本时 |

### D. 运维 / 文档 / Eval（按需）

| 项 | 用途摘要 | 何时可考虑 |
|----|----------|------------|
| `commands/pm2.md` | 生成 PM2 配置 | 用 PM2 管多进程服务时 |
| `commands/skill-create.md` | 从 git 历史生成 SKILL.md | 团队规范成熟、希望批量沉淀技能时 |
| `commands/update-docs.md` / `update-codemaps.md` | 从代码/配置同步文档 | 大版本文档对齐、且愿意审 diff 时 |
| `commands/eval.md` + `skills/eval-harness` | EDD / pass@k | 大项目要量化代理稳定性时 |

### E. 与当前已接入项的关系（避免重复接）

- 提交前分析质量：已有 **轻量 `verification-loop`（4 步）** → 不必再接常驻版 `verify` / `quality-gate`。
- 上下文：`context-budget` 已从规则回退 → 需要时再**口头**做体检即可。
- 安全：`security-review` 未常驻 → `code-review` 清单与 `security-scan` **按需**。

### 助手触发方式（给你用的承诺）

当你在做具体项目且命中上表「何时可考虑」时，助手应：**先术语一句 + 自然语言一句说明必要性**，再问你是否要安装/执行；**不得默认展开新话题**。

## 变更记录

### v1
- 初始化协作笔记与每周复盘模板。

### v1.1
- 落地 20% 精华版本：双固定流程 + 口径变更记录模板。

### v1.2
- 增加协作演进协议：Living Spec、主动触发修正规则条件、固定提问格式、先确认后落地。

### v1.3
- 接入 `strategic-compact` 轻量版：仅纳入阶段性 `/compact` 决策规则，不启用自动 hook 提醒。

### v1.4
- 接入 `search-first` 轻量版：内搜优先、条件外搜、外搜质量过滤、实现前输出 `Adopt/Extend/Compose/Build` 决策。
- 以“可回滚试运行”方式执行，后续按使用反馈决定是否保留或回退。

### v1.5
- `rules-distill` 已阅读完成，当前阶段暂不接入。
- 备注：该能力在规则稳定后可用于月度规则收敛与去重。

### v1.6
- 接入 `verification-loop` 轻量版：提交前执行 4 步验证（可复现性、口径一致性、变更范围、输出完整性）。
- 执行策略：未通过先修复，不跳过验证直接进入下一任务。

### v1.7
- 接入 `context-budget` 轻量版：在新增较多技能/MCP、会话变慢或扩容前，按需触发上下文体检。
- 体检策略：仅人工触发，不启用自动脚本；输出负担来源与前三项优化建议。

### v1.8
- 新增协作总原则：如无必要，勿增实体（默认不新增规则、流程、文件、依赖、自动化脚本）。
- 适用方式：仅当明确收益与必要性成立时再增量接入。

### v1.9
- 执行“如无必要，勿增实体”清理：回退 `context-budget` 轻量接入，避免当前阶段流程冗余。

### v1.10
- `security-scan`（AgentShield / `ecc-agentshield`）已阅读完成，不接入常驻规则。
- 备注：维护 `.claude/`、MCP、hooks 时可按需手动执行 `npx ecc-agentshield scan`。

### v1.11
- ECC `commands/checkpoint.md`（`/checkpoint`）已阅读完成，不接入。
- 备注：检查点需求可用有意义 commit 或 `git tag` 替代；Cursor 无同名内置斜杠命令。

### v1.12
- ECC `commands/verify.md`（`/verify`）已阅读完成，不接入。
- 备注：工程向全量验证与已有分析向轻量 `verification-loop` 并存时易冗余；若需 build/test 闸门可临时口头按该顺序执行。

### v1.13
- ECC `commands/code-review.md` 已阅读完成，不接入。
- 备注：需要时对未提交变更按该清单做 diff 审查即可，不必常驻为规则。

### v1.14
- ECC `commands/plan.md`（`/plan`）已阅读完成，不接入。
- 备注：大任务可直接要求「先规划、确认后再改代码」，与现有协作规则等价；Cursor 无同名斜杠命令。

### v1.15
- ECC `commands/learn.md`（`/learn`）已阅读完成，不接入。
- 备注：模式沉淀优先用本笔记复盘与 Living Spec；若将来统一走 Claude Code skill 目录再议。

### v1.16
- 批量纳入 **「ECC 按需参考清单」** 至本文档「ECC 按需参考清单」章节，供后续写项目时按场景建议安装或执行；默认不接入。
