"""
podcast-tool generator.py
输入：episode.json 路径
输出：visualization.html（完整单文件，可直接浏览器打开）

用法：
  python generator.py episode.json
  python generator.py episode.json output.html
"""

import json
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# ===== 默认 Quiz 题目（如果 episode.json 没有 quiz 字段）=====
DEFAULT_QUIZ = {
    "intro_title": "自测一下",
    "intro": "诚实地回答下面几个问题，看看你与自我的战斗打到了哪个阶段（不评判，纯好奇）",
    "questions": [
        {
            "id": "q1",
            "type": "choice",
            "text": "你有多少个「明天就开始」的计划？",
            "options": [
                {"label": "0个，我都做了", "score": 0},
                {"label": "1-2个", "score": 1},
                {"label": "3-5个", "score": 2},
                {"label": "太多了数不清", "score": 3}
            ]
        },
        {
            "id": "q2",
            "type": "choice",
            "text": "当你接近完成一件重要的事，你通常会……",
            "options": [
                {"label": "冲刺完成它", "score": 0},
                {"label": "拖慢节奏", "score": 1},
                {"label": "找借口暂停", "score": 2},
                {"label": "永远差那么一步", "score": 3}
            ]
        },
        {
            "id": "q3",
            "type": "choice",
            "text": "身边有人进步时，你的第一反应是？",
            "options": [
                {"label": "真心为他开心并受激励", "score": 0},
                {"label": "开心但略感焦虑", "score": 1},
                {"label": "有点不舒服", "score": 2},
                {"label": "开始挑他的毛病", "score": 3}
            ]
        },
        {
            "id": "q4",
            "type": "slider",
            "text": "你对「灵感」的依赖程度？",
            "slider_labels": ["从不等灵感", "偶尔", "经常等", "没灵感就不干"]
        },
        {
            "id": "q5",
            "type": "choice",
            "text": "当你害怕一件事时，你倾向于？",
            "options": [
                {"label": "把恐惧当信号，冲过去", "score": 0},
                {"label": "鼓励自己试试", "score": 1},
                {"label": "想很久但还是不做", "score": 2},
                {"label": "合理化回避理由", "score": 3}
            ]
        }
    ],
    "result_levels": [
        {
            "max_avg_score": 0.8,
            "level_label": "🏆 职业选手级",
            "description": "你对自身阻力有高度觉察，并已建立克服它的习惯。继续保持——职业选手的本质是持续出摊，不是偶尔爆发。"
        },
        {
            "max_avg_score": 1.5,
            "level_label": "✨ 觉醒中的业余选手",
            "description": "你已开始意识到阻力的存在，这是最关键的一步。试着把你最想做的那件事安排在明天的固定时间——就当上班，不管感受。"
        },
        {
            "max_avg_score": 2.2,
            "level_label": "😅 阻力的常客",
            "description": "阻力在你生活中很活跃，最喜欢的伪装是「等时机成熟」。今天选一件小事，花10分钟开始——不是完成，只是开始。"
        },
        {
            "max_avg_score": 99,
            "level_label": "🔥 重度患者（但这很正常）",
            "description": "你的阻力过得很滋润。但记住：你越害怕一件事，那件事对你就越重要。先坐下来，就已经赢了一半。"
        }
    ]
}


def _normalize_legacy(data: dict) -> dict:
    """兼容旧版 podcast_content_outline.json 格式（以 `podcast` 为顶层字段）"""
    if "podcast" not in data or "meta" in data:
        return data

    p = data["podcast"]
    data["meta"] = {
        "podcast_name": p.get("slogan", p.get("title", "")),
        "episode_number": p.get("episode"),
        "title": p.get("title", ""),
        "subtitle": p.get("book", ""),
        "published_date": "",
        "total_duration_sec": 0,
        "language": "zh",
    }
    data["participants"] = [
        {
            "id": h.get("id", f"host{i}"),
            "name": h.get("name", ""),
            "role": h.get("role", "主持人"),
            "bio": h.get("role", ""),
        }
        for i, h in enumerate(p.get("hosts", []))
    ]
    if "book" in p:
        data["featured_work"] = {
            "type": "book",
            "title": p["book"],
            "author": p.get("author", ""),
        }

    # 从最后一个非广告章节提取推荐书目（旧格式的 book-recommendations 章节）
    if "recommendations" not in data:
        data["recommendations"] = []

    return data


def render(episode_json_path: str, output_path: str = None) -> str:
    """
    将 episode.json 渲染为可视化 HTML 文件。

    Args:
        episode_json_path: episode.json 的路径
        output_path: 输出 HTML 路径（默认与 json 同名，后缀改为 _visualization.html）

    Returns:
        输出文件的绝对路径
    """
    episode_path = Path(episode_json_path).resolve()

    with open(episode_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 兼容旧格式
    data = _normalize_legacy(data)

    # 确保可选字段有默认值
    data.setdefault("theme", {})
    data.setdefault("recommendations", [])
    data.setdefault("core_quotes", [])
    data.setdefault("participants", [])
    data.setdefault("sections", [])

    # v2.0 新字段默认值
    data.setdefault("content_overview", {
        "one_sentence_summary": "",
        "content_blocks": [],
        "block_connections": []
    })
    data.setdefault("arguments", [])
    data.setdefault("key_concepts", [])
    data.setdefault("extended_reading", [])
    data.setdefault("mind_map", {"central_theme": "", "nodes": []})

    # 将 mind_map.nodes（扁平 parent_id 格式）转为模板需要的 branches（嵌套格式）
    mind_map = data["mind_map"]
    if "branches" not in mind_map and mind_map.get("nodes"):
        nodes = mind_map["nodes"]
        if nodes and isinstance(nodes[0], dict):
            if "parent_id" in nodes[0]:
                # 扁平格式：按 parent_id 构建树
                by_id = {n["id"]: n for n in nodes}
                roots = [n for n in nodes if not n.get("parent_id")]
                branches = []
                for root in roots:
                    children_l2 = [n for n in nodes if n.get("parent_id") == root["id"]]
                    branch = {
                        "label": root.get("label", ""),
                        "detail": root.get("detail", ""),
                        "children": [],
                    }
                    for c in children_l2:
                        leaves = [n for n in nodes if n.get("parent_id") == c["id"]]
                        if leaves:
                            for lf in leaves:
                                branch["children"].append({"label": lf.get("label", ""), "detail": lf.get("detail", "")})
                        else:
                            branch["children"].append({"label": c.get("label", ""), "detail": c.get("detail", "")})
                    branches.append(branch)
                mind_map["branches"] = branches
            elif "children" in nodes[0]:
                # 嵌套格式：直接转为 branches
                branches = []
                for node in nodes:
                    branch = {"label": node.get("label", ""), "detail": node.get("detail", ""), "children": []}
                    for child in node.get("children", []):
                        for leaf in child.get("children", []):
                            branch["children"].append({"label": leaf.get("label", ""), "detail": leaf.get("detail", "")})
                        if not child.get("children"):
                            branch["children"].append({"label": child.get("label", ""), "detail": child.get("detail", "")})
                    branches.append(branch)
                mind_map["branches"] = branches

    # 确保每个 section 都有完整字段
    for s in data["sections"]:
        s.setdefault("is_ad", False)
        s.setdefault("quotes", [])
        s.setdefault("key_points", [])
        s.setdefault("stories", [])
        s.setdefault("key_points_grouped", [])
        # 为 key_points_grouped 中的 group 设置默认 visual_type
        for g in s.get("key_points_grouped", []):
            g.setdefault("visual_type", "list")
        s.setdefault("diagram", None)
        s.setdefault("section_context", "")

    # Quiz 配置
    quiz = data.get("quiz") or DEFAULT_QUIZ
    if not quiz.get("questions"):
        quiz = DEFAULT_QUIZ
    data["quiz"] = quiz

    # 预计算 quiz_config（供 JS 使用）
    required_ids = [q["id"] for q in quiz["questions"] if q["type"] == "choice"]
    slider_ids = [q["id"] for q in quiz["questions"] if q["type"] == "slider"]
    data["quiz_config"] = {
        "required": required_ids,
        "sliders": slider_ids,
        "results": [
            {
                "max": level["max_avg_score"],
                "label": level["level_label"],
                "desc": level["description"],
            }
            for level in quiz["result_levels"]
        ],
    }

    # 确定输出路径
    if output_path is None:
        output_path = episode_path.parent / f"{episode_path.stem}_visualization.html"
    output_path = Path(output_path)

    # 初始化 Jinja2 环境
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=True,  # 自动转义 HTML 特殊字符，防止 XSS
    )

    template = env.get_template("base.html.j2")
    html = template.render(**data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"✅ 已生成: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python generator.py <episode.json> [output.html]")
        print("示例: python generator.py examples/ep59_episode.json")
        sys.exit(1)

    out = sys.argv[2] if len(sys.argv) > 2 else None
    render(sys.argv[1], out)
