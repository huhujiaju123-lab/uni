#!/usr/bin/env python3
"""
播客内容分析器 — 用 Claude API 将转录文本转为结构化 JSON
输入：转录文本文件路径（.txt）
输出：符合通用数据模型的 episode.json
"""

import os
import sys
import json
import re

try:
    from openai import OpenAI
except ImportError:
    print("❌ 缺少依赖，请运行：pip install openai")
    sys.exit(1)

# 通义千问 API 配置
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"

SYSTEM_PROMPT = """你是一位专业的播客内容分析师，擅长将播客转录文本提炼为结构化内容。

你的任务：分析播客转录文本，输出严格的 JSON 格式数据。

## 输出格式

必须输出合法的 JSON，不加任何多余文字，严格按照以下结构：

```json
{
  "meta": {
    "podcast_name": "播客名称",
    "episode_number": 59,
    "title": "本期标题",
    "subtitle": "一句话描述本期主题",
    "total_duration_sec": 5400,
    "language": "zh"
  },
  "participants": [
    {
      "id": "host1",
      "name": "主持人名字",
      "role": "host",
      "bio": "简短介绍（可选）"
    }
  ],
  "featured_work": {
    "type": "book",
    "title": "书名（若本期讨论了某本书/电影）",
    "author": "作者名"
  },
  "sections": [
    {
      "id": "intro",
      "title": "章节主标题",
      "subtitle": "章节副标题",
      "start_sec": 0,
      "end_sec": 480,
      "is_ad": false,
      "key_points": ["核心观点1", "核心观点2", "核心观点3"],
      "quotes": ["金句1", "金句2"],
      "stories": [
        {
          "narrator_id": "host1",
          "text": "个人故事或案例描述"
        }
      ],
      "key_points_grouped": [{"label": "分组名", "visual_type": "list", "points": [{"text": "要点", "detail": "补充"}]}],
      "diagram": {
        "type": "flow|comparison|icon-list|slope|layers",
        "title": "图表标题",
        "description": "可选说明",
        "// flow 类型需要": "steps: [{label, desc}]",
        "// comparison 类型需要": "left: {label}, right: {label}, entries: [{left, right}]",
        "// icon-list 类型需要": "entries: [{icon, label, desc}]",
        "// slope 类型需要": "elements: [{label, level}]，level 为 low/barrier/high",
        "// layers 类型需要": "layers: [{label, desc, depth}]，depth 为 1/2/3"
      },
      "section_context": "本章在全集逻辑中的位置（一句话）"
    }
  ],
  "core_quotes": [
    "精选金句1（最有力量的5-10条，跨章节提取）",
    "精选金句2"
  ],
  "recommendations": [
    {
      "type": "book",
      "title": "书名",
      "author": "作者",
      "quote": "推荐理由"
    }
  ],
  "quiz": {
    "intro": "与本期主题相关的自测引导语",
    "questions": [
      {
        "id": "q1",
        "text": "问题文字",
        "type": "choice",
        "options": [
          {"label": "选项A", "score": 0},
          {"label": "选项B", "score": 1},
          {"label": "选项C", "score": 2},
          {"label": "选项D", "score": 3}
        ]
      }
    ],
    "result_levels": [
      {
        "max_avg_score": 1.0,
        "level_label": "新手级",
        "description": "结果描述"
      },
      {
        "max_avg_score": 2.0,
        "level_label": "进阶级",
        "description": "结果描述"
      },
      {
        "max_avg_score": 3.0,
        "level_label": "高手级",
        "description": "结果描述"
      }
    ]
  },
  "content_overview": {
    "one_sentence_summary": "一句话概括核心主旨（15-30字）",
    "content_blocks": [
      {"id": "block-1", "title": "组块标题", "summary": "组块概要", "section_ids": ["section-id"], "icon": "🎯"}
    ],
    "block_connections": [
      {"from": "block-1", "to": "block-2", "relation": "延伸", "description": "逻辑关系说明"}
    ]
  },
  "arguments": [
    {"id": "arg-1", "claim": "观点陈述", "evidence_type": "个人经历", "evidence": "论据概述", "source_section_id": "section-id", "strength": "strong"}
  ],
  "key_concepts": [
    {"id": "concept-1", "term": "概念名称", "definition": "简洁定义", "explanation": "播客中如何阐述", "examples": ["具体例子"], "related_concepts": ["concept-2"], "source_section_id": "section-id"}
  ],
  "extended_reading": [
    {"id": "ext-1", "topic": "延伸主题", "context": "话题背景", "deep_dive": "延伸解读", "related_concept_ids": ["concept-1"], "further_resources": "推荐方向"}
  ],
  "mind_map": {
    "central_theme": "核心主题",
    "nodes": [
      {"id": "node-1", "label": "节点标签", "type": "theme", "parent_id": null, "detail": "节点说明"},
      {"id": "node-1-1", "label": "子节点", "type": "concept", "parent_id": "node-1", "detail": "子节点说明"}
    ]
  }
}
```

## 注意事项

1. **时间戳**：转录文本中有 [MM:SS - MM:SS] 格式，将其转为秒数（如 [08:08] = 488秒）
2. **章节划分**：按话题转换自然划分，通常 6-10 个章节，广告段标记 is_ad: true
3. **参与者 ID**：使用简洁 ID（如 "host", "guest", "via", 或说话人名字的拼音缩写）
4. **key_points**：每章节 3-6 条，简洁有力
5. **core_quotes**：全集最精彩的 5-10 句话，可直接作为分享金句
6. **quiz**：5 道与本期主题紧密相关的自测题，让听众反思自身
7. **featured_work**：仅当本期明确围绕某书/电影/作品展开时填写，否则省略该字段
8. **recommendations**：收集节目中提到的书单/影单/播客推荐，可为空数组
9. **content_overview**：将章节归纳为 3-5 个组块，描述组块间逻辑关系（因果/递进/对比/延伸）
10. **arguments**：提取 8-12 个核心观点，evidence_type 为：个人经历/类比/引用/数据/逻辑推演/故事，strength 为 strong/moderate/anecdotal
11. **key_concepts**：提取 6-10 个反复出现的关键概念，含定义、播客中的阐述和具体例子
12. **extended_reading**：延伸 4-6 个话题方向，deep_dive 可超出播客内容
13. **mind_map**：2-3 层树状结构，type 为 theme/concept/argument/example，一级 3-5 个节点
14. **key_points_grouped**：将 key_points 按逻辑分组（2-4组），每组有 label 和 points。**text 必须是完整观点句（15-40字），禁止只写关键词！detail 必须包含具体论据、数据或原文引述（20-80字）。** 读者仅通过 key_points_grouped 就能理解本章 80% 的核心内容。visual_type 可选值：list（默认）、comparison（对比）、flow（流程）、icon-grid（图标网格）
15. **diagram**：当章节内容适合用图表辅助理解时添加，每期通常 3-5 个。**必须包含完整数据字段，不能只写 type/title/description！**各类型必需字段：
    - flow：`steps: [{label: "步骤名", desc: "说明"}]`（3-6步）
    - comparison：`left: {label: "左侧标签"}, right: {label: "右侧标签"}, entries: [{left: "左侧内容", right: "右侧内容"}]`（3-5行）
    - icon-list：`entries: [{icon: "emoji", label: "标签", desc: "说明"}]`（4-8项）
    - slope：`elements: [{label: "标签", level: "low|barrier|high"}]`（3-5项）
    - layers：`layers: [{label: "标签", desc: "说明", depth: 1|2|3}]`（3层）
16. **输出纯 JSON**：不要加 ```json 代码块标记，不要加解释文字
"""


def analyze_transcript(transcript_path: str, output_path: str = None, metadata: dict = None) -> dict:
    """
    使用 Claude 分析转录文本，生成结构化 JSON

    Args:
        transcript_path: 转录文本文件路径（.txt）
        output_path: 输出 JSON 文件路径，None 则自动推断
        metadata: 可选的元数据 dict（podcast_name, cover_url 等）

    Returns:
        dict: 结构化的 episode 数据
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("❌ DASHSCOPE_API_KEY 环境变量未设置（通义千问 API Key）")

    if not os.path.exists(transcript_path):
        raise FileNotFoundError(f"转录文件不存在：{transcript_path}")

    print(f"📖 读取转录文本：{transcript_path}")
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    char_count = len(transcript_text)
    print(f"   字符数：{char_count:,}")

    # 构建用户消息
    meta_hint = ""
    if metadata:
        meta_hint = f"""
## 已知元数据（直接使用，无需从文本中推断）
- 播客名称：{metadata.get('podcast_name', '未知')}
- 本期标题：{metadata.get('title', '未知')}
- 简介：{metadata.get('description', '无')[:200]}

"""

    user_message = f"""{meta_hint}## 转录文本

{transcript_text}

请分析以上转录文本，输出符合要求的 JSON 结构。"""

    print(f"🤖 调用通义千问分析中（{QWEN_MODEL}）...")
    print(f"   预计耗时：30-120 秒...")

    client = OpenAI(api_key=api_key, base_url=QWEN_BASE_URL)

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL,
            max_tokens=16384,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception as e:
        raise RuntimeError(f"通义千问 API 调用失败：{e}")

    raw_output = response.choices[0].message.content.strip()

    # 解析 JSON（有时 Claude 会加 ```json 代码块）
    episode_data = _parse_json_output(raw_output)

    # 注入封面 URL（Claude 无法从文本中获取）
    if metadata:
        if "meta" not in episode_data:
            episode_data["meta"] = {}
        if metadata.get("cover_url"):
            episode_data["meta"]["cover_url"] = metadata["cover_url"]
        if metadata.get("audio_url"):
            episode_data["meta"]["audio_url"] = metadata["audio_url"]
        if metadata.get("source_url"):
            episode_data["meta"]["platform_links"] = {
                "xiaoyuzhou": metadata["source_url"]
            }

    # 确定输出路径
    if not output_path:
        base = os.path.splitext(transcript_path)[0]
        output_path = base.replace("transcript", "episode") + ".json"
        if output_path == transcript_path:
            output_path = os.path.splitext(transcript_path)[0] + "_episode.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(episode_data, f, ensure_ascii=False, indent=2)

    sections_count = len(episode_data.get("sections", []))
    quotes_count = len(episode_data.get("core_quotes", []))
    print(f"✅ 内容分析完成")
    print(f"   章节数：{sections_count}")
    print(f"   精选金句：{quotes_count} 条")
    print(f"   输出文件：{output_path}")

    return episode_data


def _parse_json_output(raw: str) -> dict:
    """解析 Claude 的 JSON 输出，兼容带代码块的情况"""
    # 去除 ```json ... ``` 包裹
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # 尝试找到第一个 { 到最后一个 } 之间的内容
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"无法解析 Claude 输出为 JSON：{e}\n原始输出前 500 字符：\n{raw[:500]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python3 analyzer.py <转录文本路径> [输出JSON路径]")
        print("示例：python3 analyzer.py ./output/abc123/transcript.txt")
        sys.exit(1)

    transcript_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = analyze_transcript(transcript_path, output_path)
    print(f"\n分析结果摘要：{result.get('meta', {}).get('title', '无标题')}")
