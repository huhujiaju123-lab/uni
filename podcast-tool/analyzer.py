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
import concurrent.futures

try:
    from openai import OpenAI
except ImportError:
    print("❌ 缺少依赖，请运行：pip install openai")
    sys.exit(1)

# 通义千问 API 配置
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"

SYSTEM_PROMPT = """你是一位播客内容整理编辑，负责将播客转录文本整理为结构化内容。

## 核心原则

1. **忠于原文**：所有观点、数据、概念、案例必须来自播客原文，禁止编造、推测或补充原文没有的内容
2. **保留语感**：保持播客原有的表达风格和语气，可以精简和重组句子，但读者应能感受到原作的影子，避免学术化改写
3. **直接陈述**：大部分观点直接写结论，不用"他们认为""嘉宾提到"等间接引述；仅在需要区分不同说话人立场时标注人名
4. **区分原文与延伸**：原文中的观点正常呈现；编辑补充的背景知识或延伸解读必须在 extended_reading 模块中，不要混入 sections/arguments/key_concepts

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
        "type": "flow|comparison|icon-list|slope|layers|timeline|cycle|matrix|stats",
        "title": "图表标题",
        "description": "可选说明",
        "// flow 类型需要": "steps: [{label, desc}]",
        "// comparison 类型需要": "left: {label}, right: {label}, entries: [{left, right}]",
        "// icon-list 类型需要": "entries: [{icon, label, desc}]",
        "// slope 类型需要": "elements: [{label, level}]，level 为 low/barrier/high",
        "// layers 类型需要": "layers: [{label, desc, depth}]，depth 为 1/2/3",
        "// timeline 类型需要": "entries: [{label, desc, marker(可选)}]",
        "// cycle 类型需要": "entries: [{label, desc}]",
        "// matrix 类型需要": "x_axis: {low, high}, y_axis: {low, high}, entries: [{label, quadrant}]，quadrant 为 top-left/top-right/bottom-left/bottom-right",
        "// stats 类型需要": "entries: [{value, label, desc(可选)}]"
      },
      "section_context": "这段聊了什么（一句大白话，像跟朋友解释。禁用术语：解构/认知/升维/底层逻辑/方法论/锚点/张力/杠杆/范式/叙事/维度/框架/隐喻/收束/主体性。禁用句式：'为后续…奠定''全集…的核心''提供…支点'）"
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
    "one_sentence_summary": "一句话概括核心主旨（15-30字，用大白话，禁止用：本质/解构/认知/升维/范式 等分析术语）",
    "content_blocks": [
      {"id": "block-1", "title": "组块标题", "summary": "组块概要", "section_ids": ["section-id"], "icon": "🎯"}
    ],
    "block_connections": [
      {"from": "block-1", "to": "block-2", "relation": "延伸/因果/递进/对比（必填）", "description": "一句话说清两个组块之间的关系（必填，不能为空）"}
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
2. **章节划分**：按话题转换自然划分，通常 6-10 个章节。**广告识别是高优先级任务**：播客开头/中间/结尾的品牌口播、产品推广、赞助商内容必须标记 `is_ad: true`。广告段只需填 title/subtitle/start_sec/end_sec/section_context，不要填 key_points/key_points_grouped/diagram/stories/quotes
3. **参与者 ID**：使用简洁 ID（如 "host", "guest", "via", 或说话人名字的拼音缩写）
4. **key_points**：每章节 3-6 条，来自原文的核心观点
5. **core_quotes**：全集最精彩的 5-10 句原话，必须是播客中实际说出的句子，可微调语序但不改原意
6. **quiz**：5 道与本期主题紧密相关的自测题，让听众反思自身
7. **featured_work**：仅当本期明确围绕某书/电影/作品展开时填写，否则省略该字段
8. **recommendations**：收集节目中提到的书单/影单/播客推荐，可为空数组
9. **content_overview**：将章节归纳为 3-5 个组块。one_sentence_summary 用大白话，禁止"本质""解构""认知"等分析术语。**block_connections 的 relation 和 description 必须填写**，不能为空字符串，用一句话说清"A 跟 B 是什么关系"（如"聊完理论后举了实际案例"）
10. **arguments**：提取 8-12 个核心观点，必须是播客中明确表达的立场，evidence_type 为：个人经历/类比/引用/数据/逻辑推演/故事，strength 为 strong/moderate/anecdotal
11. **key_concepts**：提取 6-10 个播客中反复出现或重点讲解的概念，定义和解释必须基于播客原文的表述，不要替换为教科书定义
12. **extended_reading**：这是唯一允许超出播客原文的模块。延伸 4-6 个话题方向，deep_dive 可补充背景知识和延伸思考。**严禁编造具体学术论文、期刊名称、年份、项目名称、百分比数据。** 如需引用研究，只写"有研究发现..."等模糊表述，或引用播客中实际提到的来源
13. **mind_map**：2-3 层树状结构，type 为 theme/concept/argument/example，一级 3-5 个节点
14. **key_points_grouped**：将 key_points 按逻辑分组（2-4组），每组有 label 和 points。**text 必须是完整观点句（20-50字），禁止只写关键词！detail 以讲明白为原则（单条不超过200字），优先使用原文表述，可精简重组但不改原意。** 读者仅通过 key_points_grouped 就能理解本章 80% 的核心内容。visual_type 仅限：list（默认）、comparison（对比）、flow（流程）、icon-grid（图标网格）。**不要使用 matrix/stats/slope 等 diagram 专用类型，key_points_grouped 与 diagram 是独立模块。** 每组 points 数组不能为空，至少2条
15. **diagram**：当章节内容适合用图表辅助理解时添加，每期通常 3-5 个。**必须包含完整数据字段，不能只写 type/title/description！**根据内容语义选择最贴切的类型：
    - flow：`steps: [{label: "步骤名", desc: "说明"}]`（3-6步）— 适合线性流程、步骤序列
    - comparison：`left: {label: "左侧标签"}, right: {label: "右侧标签"}, entries: [{left: "左侧内容", right: "右侧内容"}]`（3-5行）— 适合二元对比、新旧对照
    - icon-list：`entries: [{icon: "emoji", label: "标签", desc: "说明"}]`（4-8项）— 适合并列概念、工具清单
    - slope：`elements: [{label: "标签", level: "low|barrier|high"}]`（3-5项）— 仅适合有明确"低→障碍→高"落差关系的场景（如：入门门槛低→中间有阻力→回报高），不要用于表达"程度梯度"或"重要性排序"
    - layers：`layers: [{label: "标签", desc: "说明", depth: 1|2|3}]`（3层）— 适合层级递进、由表及里
    - timeline：`entries: [{label: "事件", desc: "说明", marker: "时间标记(可选)"}]`（3-8项）— 适合时间序列、阶段划分、历史演变
    - cycle：`entries: [{label: "步骤", desc: "说明"}]`（3-6步）— 适合循环流程、反馈闭环、习惯回路
    - matrix：`x_axis: {low: "低", high: "高"}, y_axis: {low: "低", high: "高"}, entries: [{label: "项目", quadrant: "top-left|top-right|bottom-left|bottom-right"}]`（4-8项）— 适合二维分类、优先级矩阵
    - stats：`entries: [{value: "数字/百分比", label: "标签", desc: "补充说明(可选)"}]`（2-5项）— 适合关键数据、统计亮点、时间量化
16. **输出纯 JSON**：不要加 ```json 代码块标记，不要加解释文字

## 文字质量要求

- **禁止错别字**：转录文本有语音识别错误，你必须根据上下文纠正。人名前后一致，专业术语使用标准写法
- **禁止编造**：不要发明原文没有的数据（如"研究表明70%的人..."）、不要虚构术语、不要添加原文没有的案例。如果原文说"很多人"，就写"很多人"，不要改成具体百分比
- **保留原味**：优先使用说话人的原始措辞，可以去掉口头禅、重复、语气词，但核心表达不要替换为书面语同义词
- **text 字段**：完整观点句（20-50字），不能只写关键词
- **detail 字段**：以讲明白为原则，优先引用原文表述，单条不超过 200 字
- **stories 字段**：必须是播客中实际讲述的个人经历或案例，不要概括改写成抽象描述
"""


SYSTEM_PROMPT_EXTENDED = """你是播客内容整理编辑。基于播客转录文本，输出2个扩展模块的 JSON 数据。

必须输出合法 JSON，顶层包含以下2个字段：

```json
{
  "detailed_timeline": [
    {
      "id": "tl-1",
      "start_sec": 0,
      "end_sec": 480,
      "label": "00:00 – 08:00",
      "headline": "段落小标题（10字内）",
      "narrative": "这段讲了什么（严格控制在50-100字）。只写：聊了什么话题、说了什么观点。禁止散文体、禁止描写情绪氛围、禁止文学修辞。像备忘录，不像书评。",
      "topics": ["话题标签1", "话题标签2"]
    }
  ],
  "knowledge_cards": [
    {
      "id": "kc-1",
      "claim": "论点一句话（完整句子，来自播客原文）",
      "evidence_summary": "论据摘要（50-80字，来自原文）",
      "extension": "延伸解释（50-100字）：基于播客内容做合理延伸，可补充背景知识。严禁编造具体论文、期刊、年份、项目名称、百分比数据。",
      "tags": ["标签1"],
      "related_card_ids": ["kc-2"],
      "source_section_id": "section-id"
    }
  ]
}
```

## 数量要求
- detailed_timeline：每5-10分钟一段，narrative 严格50-100字，像备忘录而非书评，只写"聊了什么、说了什么"
- knowledge_cards：12-20张，extension 字段提供延伸视角但不编造学术引用

## 参与者信息
label 格式为 "MM:SS"（由 start_sec 换算），detailed_timeline 的 label 格式为 "MM:SS – MM:SS"。
时间戳来自转录文本中的 [MM:SS - MM:SS] 标记，将其转为秒数。

## 核心原则（与主分析一致）
- **忠于原文**：claim 和 evidence_summary 必须来自播客原文，禁止编造
- **保留语感**：保持播客的表达风格，不要学术化改写
- **禁止编造**：不要发明原文没有的数据、不要虚构论文/期刊/年份/项目名称。如需引用研究，只写"有研究发现..."等模糊表述
- **纠正错别字**：语音识别错误必须根据上下文修正
- **过滤广告**：播客中的品牌口播、产品推广、赞助商内容属于广告，不要从广告内容中提取 knowledge_cards。detailed_timeline 中的广告段落，narrative 简写为"本段为赞助广告"即可

## 输出纯 JSON，不要加 ```json 代码块标记，不要加解释文字
"""


def _call_qwen(client, system_prompt, user_message):
    """单次通义千问 API 调用"""
    response = client.chat.completions.create(
        model=QWEN_MODEL,
        max_tokens=16384,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return _parse_json_output(response.choices[0].message.content.strip())


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
    print(f"   并发执行：基础分析 + 扩展模块（详细时间轴/金句/对话/知识卡片）")
    print(f"   预计耗时：30-120 秒...")

    client = OpenAI(api_key=api_key, base_url=QWEN_BASE_URL)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_call_qwen, client, SYSTEM_PROMPT, user_message)
            f2 = pool.submit(_call_qwen, client, SYSTEM_PROMPT_EXTENDED, user_message)
            episode_data = f1.result()
            print(f"   ✓ 基础分析完成")
            extended_data = f2.result()
            print(f"   ✓ 扩展模块完成")
        episode_data.update(extended_data)
    except Exception as e:
        raise RuntimeError(f"通义千问 API 调用失败：{e}")

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
