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


def _validate_diagram(d: dict) -> bool:
    """校验 diagram 数据完整性：每种类型必须有对应的数据字段且至少2个条目"""
    dtype = d.get("type", "")
    min_items = 2

    if dtype == "flow":
        items = d.get("steps", [])
        return len(items) >= min_items and all(i.get("label") for i in items)

    elif dtype == "comparison":
        entries = d.get("entries", [])
        return (d.get("left") and d.get("right") and len(entries) >= min_items
                and all(i.get("left") and i.get("right") for i in entries))

    elif dtype in ("icon-list", "timeline", "cycle", "stats"):
        items = d.get("entries", [])
        if dtype == "stats":
            return len(items) >= min_items and all(i.get("value") and i.get("label") for i in items)
        return len(items) >= min_items and all(i.get("label") for i in items)

    elif dtype == "slope":
        items = d.get("elements", [])
        valid_levels = {"low", "barrier", "high"}
        return (len(items) >= min_items
                and all(i.get("label") and i.get("level") in valid_levels for i in items))

    elif dtype == "layers":
        items = d.get("layers", [])
        return len(items) >= min_items and all(i.get("label") for i in items)

    elif dtype == "matrix":
        items = d.get("entries", [])
        valid_quads = {"top-left", "top-right", "bottom-left", "bottom-right"}
        return (len(items) >= 2 and d.get("x_axis") and d.get("y_axis")
                and all(i.get("label") and i.get("quadrant") in valid_quads for i in items))

    return False


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


def prepare_episode_data(data: dict) -> dict:
    """预处理 episode.json 数据：兼容旧格式、填充默认值、转换 mind_map 等。
    供 HTML 渲染和 API 共用。"""
    data = _normalize_legacy(data)

    data.setdefault("theme", {})
    data.setdefault("recommendations", [])
    data.setdefault("core_quotes", [])
    data.setdefault("participants", [])
    data.setdefault("sections", [])
    data.setdefault("content_overview", {
        "one_sentence_summary": "",
        "content_blocks": [],
        "block_connections": []
    })
    data.setdefault("arguments", [])
    data.setdefault("key_concepts", [])
    data.setdefault("extended_reading", [])
    data.setdefault("mind_map", {"central_theme": "", "nodes": []})

    # ===== v2.1 新模块默认值 =====
    data.setdefault("detailed_timeline", [])
    data.setdefault("featured_quotes", [])
    data.setdefault("dialogue_flow", [])
    data.setdefault("knowledge_cards", [])

    # 自动补全 label（防止 AI 漏填）
    for item in data["detailed_timeline"]:
        if not item.get("label") and item.get("start_sec") is not None:
            s = int(item["start_sec"])
            e = int(item.get("end_sec", s))
            item["label"] = f"{s // 60:02d}:{s % 60:02d} – {e // 60:02d}:{e % 60:02d}"

    for item in data["featured_quotes"]:
        if not item.get("label") and item.get("start_sec") is not None:
            sec = int(item["start_sec"])
            item["label"] = f"{sec // 60:02d}:{sec % 60:02d}"

    for item in data["dialogue_flow"]:
        if not item.get("label") and item.get("start_sec") is not None:
            sec = int(item["start_sec"])
            item["label"] = f"{sec // 60:02d}:{sec % 60:02d}"

    # 将 mind_map.nodes（扁平 parent_id 格式）转为 branches（嵌套格式）
    mind_map = data["mind_map"]
    if "branches" not in mind_map and mind_map.get("nodes"):
        nodes = mind_map["nodes"]
        if nodes and isinstance(nodes[0], dict):
            if "parent_id" in nodes[0]:
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

    # 收集广告段 section id，用于过滤 knowledge_cards
    ad_section_ids = set()

    for s in data["sections"]:
        s.setdefault("is_ad", False)
        s.setdefault("quotes", [])
        s.setdefault("key_points", [])
        s.setdefault("stories", [])
        s.setdefault("key_points_grouped", [])

        # 广告段：清空详细内容，只保留标题和时间信息
        if s.get("is_ad"):
            ad_section_ids.add(s.get("id", ""))
            s["key_points"] = []
            s["key_points_grouped"] = []
            s["diagram"] = None
            s["stories"] = []
            s["quotes"] = []
            s.setdefault("section_context", "赞助广告")
            continue
        for g in s.get("key_points_grouped", []):
            g.setdefault("visual_type", "list")
            vt = g.get("visual_type", "list")

            # key_points_grouped 只支持这几种 visual_type，其他的 fallback 到 list
            SUPPORTED_KPG_TYPES = {"list", "comparison", "flow", "icon-list", "icon-grid"}
            if vt not in SUPPORTED_KPG_TYPES:
                g["visual_type"] = "list"
                vt = "list"

            # 空 points 的分组强制 fallback 到 list（避免只显示标题）
            if vt != "comparison" and not g.get("points"):
                g["visual_type"] = "list"
                vt = "list"

            if vt == "comparison":
                # AI 用 entries 而模板期望 comparisons
                if "entries" in g and "comparisons" not in g:
                    g["comparisons"] = g.pop("entries")
                if isinstance(g.get("left"), dict):
                    g["left_label"] = g["left"].get("label", "")
                if isinstance(g.get("right"), dict):
                    g["right_label"] = g["right"].get("label", "")

            elif vt == "flow":
                # AI 用 steps 而模板期望 points
                if "steps" in g and "points" not in g:
                    g["points"] = [
                        {"text": step.get("label", ""), "detail": step.get("desc", "")}
                        for step in g.pop("steps")
                    ]

            elif vt == "icon-list":
                # AI 用 entries 而模板 fallback 到 points
                if "entries" in g and "points" not in g:
                    g["points"] = [
                        {"text": entry.get("label", ""), "detail": entry.get("desc", "")}
                        for entry in g.pop("entries")
                    ]
        s.setdefault("diagram", None)
        s.setdefault("section_context", "")
        if s.get("diagram") and isinstance(s["diagram"], dict):
            d = s["diagram"]
            if "items" in d:
                d["entries"] = d.pop("items")
            if d.get("type") == "cycle" and "steps" in d and "entries" not in d:
                d["entries"] = d.pop("steps")
            has_data = any(k in d for k in ("steps", "entries", "elements", "layers", "left", "x_axis"))
            if not has_data:
                s["diagram"] = None

    # ===== 全局数据清洗 =====
    # 原则：有标题无内容→删除，类型越界→fallback，广告→全链路过滤，数据不完整→删除

    # -- 广告全链路过滤 --
    ad_time_ranges = [(s.get("start_sec", 0), s.get("end_sec", 0)) for s in data["sections"] if s.get("is_ad")]

    # 识别广告 timeline 段（按时间重叠比例 >50% 或 headline 含"广告"）
    ad_tl_ids = set()
    if ad_time_ranges:
        for tl in data.get("detailed_timeline", []):
            tl_start, tl_end = tl.get("start_sec", 0), tl.get("end_sec", tl.get("start_sec", 0))
            headline = tl.get("headline", "")
            tl_duration = max(tl_end - tl_start, 1)
            overlap = sum(max(0, min(tl_end, ae) - max(tl_start, as_)) for as_, ae in ad_time_ranges)
            if overlap / tl_duration > 0.5 or "广告" in headline:
                ad_tl_ids.add(tl.get("id", ""))
                tl["headline"] = "📢 " + headline.replace("📢 ", "")
                tl["narrative"] = "本段为赞助广告内容。"

    # 合并所有广告相关 ID（section id + timeline id）
    all_ad_ids = ad_section_ids | ad_tl_ids

    def _from_ad(item):
        """判断一个带 source_section_id 的条目是否来自广告段"""
        return item.get("source_section_id", "") in all_ad_ids

    # 过滤所有引用 source_section_id 的模块
    if all_ad_ids:
        data["knowledge_cards"] = [kc for kc in data.get("knowledge_cards", []) if not _from_ad(kc)]
        data["arguments"] = [a for a in data.get("arguments", []) if not _from_ad(a)]

    # content_overview: 过滤引用广告 section 的 blocks 和 connections
    if ad_section_ids:
        co = data.get("content_overview", {})
        if co.get("content_blocks"):
            co["content_blocks"] = [
                b for b in co["content_blocks"]
                if not any(sid in ad_section_ids for sid in b.get("section_ids", []))
            ]
            valid_block_ids = {b.get("id") for b in co["content_blocks"]}
            if co.get("block_connections"):
                co["block_connections"] = [
                    c for c in co["block_connections"]
                    if c.get("from") in valid_block_ids and c.get("to") in valid_block_ids
                ]

    # -- 空内容过滤：删除必要字段缺失的条目 --

    # core_quotes: 去掉空字符串
    data["core_quotes"] = [q for q in data.get("core_quotes", []) if q and q.strip()]

    # arguments: claim 不能为空
    data["arguments"] = [a for a in data.get("arguments", []) if a.get("claim", "").strip()]

    # arguments.strength: 校验枚举值
    for a in data["arguments"]:
        if a.get("strength") not in ("strong", "moderate", "anecdotal"):
            a["strength"] = "moderate"

    # key_concepts: term 和 definition 不能为空
    data["key_concepts"] = [
        kc for kc in data.get("key_concepts", [])
        if kc.get("term", "").strip() and kc.get("definition", "").strip()
    ]

    # extended_reading: topic 不能为空
    data["extended_reading"] = [
        er for er in data.get("extended_reading", [])
        if er.get("topic", "").strip()
    ]

    # knowledge_cards: claim 不能为空
    data["knowledge_cards"] = [
        kc for kc in data.get("knowledge_cards", [])
        if kc.get("claim", "").strip()
    ]

    # detailed_timeline: headline 和 narrative 不能为空
    data["detailed_timeline"] = [
        tl for tl in data.get("detailed_timeline", [])
        if tl.get("headline", "").strip() and tl.get("narrative", "").strip()
    ]

    # recommendations: title 不能为空
    data["recommendations"] = [
        r for r in data.get("recommendations", [])
        if r.get("title", "").strip()
    ]

    # content_overview.content_blocks: title 和 summary 不能为空
    co = data.get("content_overview", {})
    if co.get("content_blocks"):
        co["content_blocks"] = [
            b for b in co["content_blocks"]
            if b.get("title", "").strip() and b.get("summary", "").strip()
        ]

    # mind_map.branches: label 不能为空，过滤空 children
    mm = data.get("mind_map", {})
    if mm.get("branches"):
        cleaned_branches = []
        for branch in mm["branches"]:
            if not branch.get("label", "").strip():
                continue
            if branch.get("children"):
                branch["children"] = [
                    c for c in branch["children"]
                    if (c.get("label", "").strip() if isinstance(c, dict) else str(c).strip())
                ]
            cleaned_branches.append(branch)
        mm["branches"] = cleaned_branches

    # sections 内部清洗（非广告段）
    SUPPORTED_DIAGRAM_TYPES = {"flow", "comparison", "icon-list", "slope", "layers", "timeline", "cycle", "matrix", "stats"}
    for s in data["sections"]:
        if s.get("is_ad"):
            continue

        # quotes: 去掉空字符串
        s["quotes"] = [q for q in s.get("quotes", []) if q and q.strip()]

        # stories: text 不能为空
        stories = s.get("stories", [])
        s["stories"] = [
            st for st in stories
            if (st.get("text", "").strip() if isinstance(st, dict) else str(st).strip())
        ]

        # key_points_grouped: 删除空分组（comparison 看 comparisons，其他看 points）
        cleaned_groups = []
        for g in s.get("key_points_grouped", []):
            vt = g.get("visual_type", "list")
            if vt == "comparison":
                if g.get("comparisons") or g.get("entries"):
                    cleaned_groups.append(g)
            else:
                if g.get("points"):
                    cleaned_groups.append(g)
        s["key_points_grouped"] = cleaned_groups

        # diagram: 校验 type 白名单 + 每种类型必要字段
        d = s.get("diagram")
        if d and isinstance(d, dict):
            dtype = d.get("type", "")
            if dtype not in SUPPORTED_DIAGRAM_TYPES:
                s["diagram"] = None
            elif not _validate_diagram(d):
                s["diagram"] = None

    quiz = data.get("quiz") or DEFAULT_QUIZ
    if not quiz.get("questions"):
        quiz = DEFAULT_QUIZ
    data["quiz"] = quiz

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

    data = prepare_episode_data(data)

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
