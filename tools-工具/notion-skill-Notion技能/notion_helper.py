#!/usr/bin/env python3
"""
Notion API Helper Script
用于快速创建和管理 Notion 页面

使用前请确保设置环境变量：
  export NOTION_API_KEY="your-api-key"

或者在 ~/.claude/settings.json 中配置：
  {
    "env": {
      "NOTION_API_KEY": "your-api-key"
    }
  }
"""

import json
import os
import sys
import urllib.request
import urllib.error

# API 配置
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

# 用户自定义页面 ID（可在 config.json 中配置）
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
PAGES = {}

def load_config():
    """加载配置文件"""
    global PAGES, NOTION_API_KEY
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            PAGES.update(config.get("pages", {}))
            if not NOTION_API_KEY:
                NOTION_API_KEY = config.get("api_key")

def check_api_key():
    """检查 API Key 是否已配置"""
    if not NOTION_API_KEY:
        print("错误: 未设置 NOTION_API_KEY", file=sys.stderr)
        print("请通过以下方式之一设置:", file=sys.stderr)
        print("  1. 环境变量: export NOTION_API_KEY='your-key'", file=sys.stderr)
        print("  2. 配置文件: 在 config.json 中设置 api_key", file=sys.stderr)
        sys.exit(1)

def make_request(method: str, endpoint: str, data: dict = None) -> dict:
    """发送 API 请求"""
    check_api_key()
    url = f"{BASE_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(url, method=method, headers=headers)
    if data:
        req.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"API 错误: {e.code} - {error_body}", file=sys.stderr)
        sys.exit(1)

def search(query: str, page_size: int = 10) -> dict:
    """搜索 Notion 内容"""
    return make_request("POST", "search", {"query": query, "page_size": page_size})

def create_page(parent_id: str, title: str, icon: str = "📝", children: list = None) -> dict:
    """创建新页面"""
    data = {
        "parent": {"page_id": parent_id},
        "icon": {"type": "emoji", "emoji": icon},
        "properties": {
            "title": {"title": [{"text": {"content": title}}]}
        },
    }
    if children:
        data["children"] = children
    return make_request("POST", "pages", data)

def append_blocks(block_id: str, children: list) -> dict:
    """向页面追加内容"""
    return make_request("PATCH", f"blocks/{block_id}/children", {"children": children})

def get_blocks(block_id: str) -> dict:
    """获取页面内容"""
    return make_request("GET", f"blocks/{block_id}/children")

def get_page(page_id: str) -> dict:
    """获取页面信息"""
    return make_request("GET", f"pages/{page_id}")

# Block 构建辅助函数
def heading(level: int, text: str) -> dict:
    """创建标题块"""
    return {
        "object": "block",
        "type": f"heading_{level}",
        f"heading_{level}": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def paragraph(text: str) -> dict:
    """创建段落块"""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def bullet(text: str) -> dict:
    """创建无序列表项"""
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def numbered(text: str) -> dict:
    """创建有序列表项"""
    return {
        "object": "block",
        "type": "numbered_list_item",
        "numbered_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def code(text: str, language: str = "python") -> dict:
    """创建代码块"""
    return {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "language": language
        }
    }

def callout(text: str, icon: str = "💡", color: str = "blue_background") -> dict:
    """创建提示框"""
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": icon},
            "color": color,
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def divider() -> dict:
    """创建分隔线"""
    return {"object": "block", "type": "divider", "divider": {}}

def todo(text: str, checked: bool = False) -> dict:
    """创建待办事项"""
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "checked": checked
        }
    }

def quote(text: str) -> dict:
    """创建引用块"""
    return {
        "object": "block",
        "type": "quote",
        "quote": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def toggle(text: str) -> dict:
    """创建折叠块"""
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

# 模板函数
def create_knowledge_page(parent_id: str, title: str, description: str, sections: list) -> dict:
    """创建知识库页面模板

    Args:
        parent_id: 父页面 ID
        title: 页面标题
        description: 页面描述（显示在 Callout 中）
        sections: 章节列表，格式为 [{"title": "章节标题", "content": "内容", "items": ["列表项"]}]
    """
    children = [
        callout(description, "💡", "blue_background"),
        divider(),
    ]

    for section in sections:
        children.append(heading(2, section["title"]))
        if "content" in section:
            children.append(paragraph(section["content"]))
        if "items" in section:
            for item in section["items"]:
                children.append(bullet(item))

    return create_page(parent_id, title, "📚", children)

def create_note_page(parent_id: str, title: str, content: str) -> dict:
    """创建简单笔记页面"""
    children = [paragraph(content)]
    return create_page(parent_id, title, "📝", children)

# CLI 入口
def main():
    load_config()

    if len(sys.argv) < 2:
        print("Notion Helper - Notion API 命令行工具")
        print("")
        print("用法: notion_helper.py <command> [args]")
        print("")
        print("命令:")
        print("  search <query>              - 搜索内容")
        print("  create <parent> <title>     - 创建页面")
        print("  get <page_id>               - 获取页面信息")
        print("  list                        - 列出配置的页面")
        print("  init                        - 初始化配置文件")
        print("")
        print("示例:")
        print("  notion_helper.py search 'AI'")
        print("  notion_helper.py create abc123 '我的新页面'")
        sys.exit(0)

    command = sys.argv[1]

    if command == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        result = search(query)
        print(f"找到 {len(result.get('results', []))} 个结果:\n")
        for item in result.get("results", []):
            title = ""
            if item["object"] == "page":
                props = item.get("properties", {})
                # 尝试不同的标题字段
                for key in ["title", "Name", "标题"]:
                    if key in props and props[key].get("title"):
                        title = props[key]["title"][0].get("plain_text", "")
                        break
            elif item["object"] == "database":
                if item.get("title"):
                    title = item["title"][0].get("plain_text", "")
            print(f"  [{item['object']}] {title or 'Untitled'}")
            print(f"    ID: {item['id']}")
            print(f"    URL: {item.get('url', 'N/A')}")
            print()

    elif command == "create":
        if len(sys.argv) < 4:
            print("用法: notion_helper.py create <parent_key|id> <title>")
            sys.exit(1)
        parent = sys.argv[2]
        parent_id = PAGES.get(parent, parent)
        title = sys.argv[3]
        result = create_page(parent_id, title)
        print(f"✓ 页面创建成功!")
        print(f"  标题: {title}")
        print(f"  ID: {result['id']}")
        print(f"  URL: {result['url']}")

    elif command == "get":
        if len(sys.argv) < 3:
            print("用法: notion_helper.py get <page_id>")
            sys.exit(1)
        page_id = sys.argv[2]
        page_id = PAGES.get(page_id, page_id)
        result = get_page(page_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == "list":
        if not PAGES:
            print("未配置任何页面快捷方式")
            print("请在 config.json 中添加 pages 配置")
        else:
            print("已配置的页面快捷方式:\n")
            for key, page_id in PAGES.items():
                print(f"  {key}: {page_id}")

    elif command == "init":
        if os.path.exists(CONFIG_PATH):
            print(f"配置文件已存在: {CONFIG_PATH}")
            sys.exit(1)
        config = {
            "api_key": "",
            "pages": {
                "default": "your-default-page-id"
            }
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✓ 配置文件已创建: {CONFIG_PATH}")
        print("请编辑配置文件，填入你的 API Key 和页面 ID")

    else:
        print(f"未知命令: {command}")
        print("使用 notion_helper.py 查看帮助")
        sys.exit(1)

if __name__ == "__main__":
    main()
