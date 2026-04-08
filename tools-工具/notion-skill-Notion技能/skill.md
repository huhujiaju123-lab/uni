---
name: notion
description: 与 Notion 交互：创建页面、写入内容、搜索文档。支持创建知识库、笔记、任务等各种页面类型。
---

# Notion 知识库管理 Skill

通过 Notion API 直接在你的 Notion 工作区中创建和管理内容。

## 功能特点

- 📝 **创建页面**：在任意位置创建新页面，支持丰富的内容格式
- 🔍 **搜索内容**：搜索工作区中的页面和数据库
- 📚 **知识库管理**：快速创建结构化的知识库页面
- 🎨 **丰富格式**：支持标题、列表、代码块、引用等多种块类型

## 前置要求

1. **Notion Integration**：需要创建 Notion Integration 并获取 API Token
2. **环境变量**：设置 `NOTION_API_KEY` 环境变量

## 使用方法

### 创建新页面

```
在 Notion 创建一个关于 [主题] 的页面
```

### 在指定位置创建

```
在 [父页面名称] 下创建一个 [主题] 的页面
```

### 搜索内容

```
在 Notion 中搜索关于 [关键词] 的内容
```

### 添加内容到现有页面

```
在 [页面名称] 页面中添加 [内容]
```

## API 调用示例

### 搜索页面

```bash
curl -X POST "https://api.notion.com/v1/search" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{"query": "搜索关键词", "page_size": 10}'
```

### 创建页面

```bash
curl -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": { "page_id": "父页面ID" },
    "icon": { "type": "emoji", "emoji": "📝" },
    "properties": {
      "title": {
        "title": [{ "text": { "content": "页面标题" } }]
      }
    },
    "children": [
      {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
          "rich_text": [{ "type": "text", "text": { "content": "标题内容" } }]
        }
      },
      {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
          "rich_text": [{ "type": "text", "text": { "content": "段落内容" } }]
        }
      }
    ]
  }'
```

### 获取页面内容

```bash
curl -X GET "https://api.notion.com/v1/blocks/{block_id}/children" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28"
```

### 追加内容到页面

```bash
curl -X PATCH "https://api.notion.com/v1/blocks/{block_id}/children" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{
    "children": [
      {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
          "rich_text": [{ "type": "text", "text": { "content": "新内容" } }]
        }
      }
    ]
  }'
```

## 支持的块类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `paragraph` | 普通段落 | 正文内容 |
| `heading_1/2/3` | 标题 | 章节标题 |
| `bulleted_list_item` | 无序列表 | 要点列表 |
| `numbered_list_item` | 有序列表 | 步骤说明 |
| `to_do` | 待办事项 | 任务清单 |
| `toggle` | 折叠块 | FAQ |
| `code` | 代码块 | 代码示例 |
| `quote` | 引用 | 名言引用 |
| `callout` | 提示框 | 重要提示 |
| `divider` | 分隔线 | 内容分隔 |
| `table` | 表格 | 数据表格 |

## 知识库模板

### 技术学习笔记模板

创建包含以下结构的页面：
- 概述（Callout 提示框）
- 核心概念（标题 + 段落）
- 使用示例（代码块）
- 常见问题（Toggle 折叠）
- 参考资源（链接列表）

### 项目记录模板

- 项目背景
- 技术栈
- 实现步骤
- 遇到的问题
- 解决方案
- 总结反思

## 注意事项

1. **权限检查**：确保 Integration 已连接到目标页面
2. **父页面**：创建页面时必须指定有效的父页面 ID
3. **API 版本**：使用 `Notion-Version: 2022-06-28`
4. **速率限制**：API 有请求频率限制，避免短时间内大量请求

## 相关链接

- [Notion API 官方文档](https://developers.notion.com/)
- [Block 类型参考](https://developers.notion.com/reference/block)
