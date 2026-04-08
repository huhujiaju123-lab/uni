# 🦞 超级龙虾 — OpenClaw 运营大脑模板

## 这是什么

一套 OpenClaw workspace 改造模板，让你的 AI 助手从「通用聊天机器人」变成「越用越聪明的运营专家」。

## 核心能力

1. **负反馈闭环**：被纠正后自动记录，犯过的错永远不再犯
2. **知识晋升**：临时笔记 → 长期记忆 → 永久规则，自动进化
3. **团队共享**：一个人的学习，全团队受益
4. **严谨自检**：不确定就说不确定，不编造数字

## 文件说明

```
super-lobster-template/
├── SOUL.md              ← 运营专家人格 + 决策框架
├── AGENTS.md            ← 操作规则 + 学习系统 + 严谨性规则
├── USER.md              ← 团队信息（需填写）
├── MEMORY.md            ← 长期记忆（使用中积累）
├── .learnings/
│   ├── ERRORS.md        ← 错误记录（自动追加）
│   ├── LEARNINGS.md     ← 学习记录（自动追加）
│   └── PATTERNS.md      ← 模式记录（自动追加）
└── memory/
    ├── team/            ← 团队共享记忆（git 同步）
    └── personal/        ← 个人日志（不同步）
```

## 安装方法

### 第 1 步：备份现有 workspace

```bash
cp -r ~/.openclaw/workspace ~/.openclaw/workspace-backup
```

### 第 2 步：复制模板文件

```bash
# 复制核心文件（不覆盖已有的 IDENTITY.md 等个性化文件）
cp SOUL.md AGENTS.md USER.md MEMORY.md ~/.openclaw/workspace/
cp -r .learnings/ ~/.openclaw/workspace/
cp -r memory/ ~/.openclaw/workspace/
```

### 第 3 步：填写 USER.md

打开 `~/.openclaw/workspace/USER.md`，填入团队成员信息。

### 第 4 步：开始使用

正常对话即可。当你纠正它时，它会自动记录到 `.learnings/`。

## 团队同步（可选）

如果 3 人团队想共享学习成果：

```bash
# 在 workspace 目录初始化 git
cd ~/.openclaw/workspace
git init
git remote add origin <你的私有仓库>

# 日常同步
git pull  # 获取队友的学习
git add .learnings/ memory/team/ MEMORY.md
git commit -m "sync learnings"
git push  # 分享你的学习
```

## 注意事项

- SOUL.md 中的领域知识需要根据你的实际业务调整
- .learnings/ 中的记录是自动追加的，不要手动删除
- 晋升到 AGENTS.md / SOUL.md 需要人工确认
- MEMORY.md 仅在主会话加载，群聊中不会泄露
