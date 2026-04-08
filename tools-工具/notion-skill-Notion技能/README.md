# Notion Skill for Claude Code

让 Claude Code 能够直接与 Notion 交互，创建页面、写入内容、搜索文档。

## 功能

- 📝 创建 Notion 页面
- 🔍 搜索工作区内容
- 📚 使用预设模板快速创建知识库
- 🎨 支持多种内容格式（标题、列表、代码块、引用等）

## 安装步骤

### 1. 创建 Notion Integration

1. 访问 [Notion Integrations](https://www.notion.so/my-integrations)
2. 点击 **New integration**
3. 填写名称（如 "Claude Code"）
4. 选择你的工作区
5. 点击 **Submit**
6. 复制生成的 **Internal Integration Secret**（以 `ntn_` 或 `secret_` 开头）

### 2. 连接 Integration 到页面

1. 在 Notion 中打开你想要操作的页面
2. 点击右上角 `···` 菜单
3. 选择 **Connections** → **Connect to**
4. 找到并选择你创建的 Integration

### 3. 安装 Skill

将 `notion` 文件夹复制到 Claude Code 的 skills 目录：

```bash
# macOS / Linux
cp -r notion-skill ~/.claude/skills/notion

# 或者创建软链接
ln -s /path/to/notion-skill ~/.claude/skills/notion
```

### 4. 配置 API Key

**方式一：环境变量（推荐）**

在 `~/.zshrc` 或 `~/.bashrc` 中添加：

```bash
export NOTION_API_KEY="your-api-key"
```

**方式二：Claude Code 配置文件**

编辑 `~/.claude/settings.json`：

```json
{
  "env": {
    "NOTION_API_KEY": "your-api-key"
  }
}
```

**方式三：Skill 配置文件**

在 skill 目录下创建 `config.json`：

```json
{
  "api_key": "your-api-key",
  "pages": {
    "default": "your-default-page-id",
    "notes": "your-notes-page-id"
  }
}
```

### 5. 配置页面快捷方式（可选）

编辑 `~/.claude/skills/notion/config.json`：

```json
{
  "pages": {
    "notes": "2c18f0e3-ca82-8125-9d7d-c9a4f28bf053",
    "journal": "2752ea6f-d24f-4d72-a562-855ea10c6637",
    "projects": "your-projects-page-id"
  }
}
```

## 使用方法

### 在 Claude Code 中使用

启动 Claude Code 后，直接用自然语言：

```
在 Notion 创建一个关于 Python 技巧的页面
```

```
在 notes 页面下创建一个读书笔记
```

```
搜索 Notion 中关于 AI 的内容
```

### 使用命令行工具

```bash
# 查看帮助
python3 ~/.claude/skills/notion/notion_helper.py

# 搜索内容
python3 ~/.claude/skills/notion/notion_helper.py search "AI"

# 创建页面（使用配置的快捷方式）
python3 ~/.claude/skills/notion/notion_helper.py create notes "新笔记"

# 创建页面（使用页面 ID）
python3 ~/.claude/skills/notion/notion_helper.py create abc123-def456 "新页面"

# 列出配置的页面
python3 ~/.claude/skills/notion/notion_helper.py list

# 初始化配置文件
python3 ~/.claude/skills/notion/notion_helper.py init
```

## 获取页面 ID

页面 ID 可以从 Notion 页面 URL 中获取：

```
https://www.notion.so/My-Page-Title-2c18f0e3ca828125xxxx
                                    ^^^^^^^^^^^^^^^^^^^^^^^^
                                    这部分就是页面 ID
```

或者使用搜索命令：

```bash
python3 ~/.claude/skills/notion/notion_helper.py search "页面名称"
```

## 文件结构

```
notion-skill/
├── README.md           # 本说明文件
├── skill.md            # Skill 定义文件
├── notion_helper.py    # Python 辅助脚本
├── config.json         # 配置文件（需自己创建）
└── config.example.json # 配置文件示例
```

## 常见问题

### Q: 提示 "未设置 NOTION_API_KEY"

确保已通过环境变量或配置文件设置了 API Key。

### Q: API 返回 401 错误

1. 检查 API Key 是否正确
2. 确保 Integration 已连接到目标页面

### Q: API 返回 404 错误

1. 检查页面 ID 是否正确
2. 确保 Integration 有访问该页面的权限

### Q: 如何获取完整的页面 ID？

使用搜索命令可以获取页面的完整 ID：

```bash
python3 ~/.claude/skills/notion/notion_helper.py search "页面名称"
```

## 相关链接

- [Notion API 文档](https://developers.notion.com/)
- [Claude Code 文档](https://docs.anthropic.com/claude-code)
- [Notion Integrations](https://www.notion.so/my-integrations)

## License

MIT
