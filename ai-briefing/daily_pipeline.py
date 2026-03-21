#!/usr/bin/env python3
"""
AI Builders Daily — 每日自动化流水线 v2
1. 拉取 follow-builders feed
2. 内容预过滤（去噪音、按互动量加权）
3. 两步 LLM 生成（qwen-plus 规划 → qwen-max 脚本）
4. 质量检查（段数/字数/比例/套话检测，不合格自动重试）
5. CosyVoice TTS 合成（回退 Edge TTS）+ 可变停顿
6. 上传服务器 + 更新 RSS
7. 飞书推送（含质量报告）
"""

import asyncio
import http.client
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

# ============================================================
# 配置
# ============================================================
BASE_DIR = Path(__file__).parent
TODAY = datetime.now().strftime("%Y-%m-%d")
DASHSCOPE_API_KEY = "sk-e1151b380b82414d9b29470dd5ec448f"

# follow-builders feed URLs
FEED_X_URL = "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json"
FEED_PODCAST_URL = "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-podcasts.json"

# 服务器
SERVER = "134.175.228.73"
SERVER_PASS = "Yumoshucheng@"
SERVER_PODCAST_DIR = "/opt/ai-podcast"

# 飞书 Bot 2
FEISHU_APP_ID = "cli_a931766ee7789cc7"
FEISHU_APP_SECRET = "4rw86K89yOjmFGavvx4ZKhXMSVXhOQ2m"
FEISHU_USER_OPEN_ID = "ou_d6c763932edf1695f18399f0e4387ec4"

# TTS 配置 —— "cosyvoice" 或 "edge_tts"
TTS_ENGINE = "cosyvoice"

# 音色方案（可切换：default / mixed / dual_female）
VOICE_PROFILE = "current"

# 全局语速倍率（1.0=原速，1.2=加速20%）
TTS_SPEED_RATIO = 1.2

VOICE_PROFILES = {
    "current": {    # 递归=阳光男声, 大师=知性（偏男）
        "desc": "递归=longcheng阳光男声, 大师=longshu知性",
        "cosyvoice": {"递归": "longcheng", "大师": "longshu"},
        "edge_tts": {
            "递归": ("zh-CN-YunxiNeural", "+26%"),
            "大师": ("zh-CN-YunyangNeural", "+22%"),
        },
    },
    "default": {    # 两男（原版，沉稳风格）
        "desc": "递归=阳光男声, 大师=沉稳男声",
        "cosyvoice": {"递归": "longcheng", "大师": "longshuo"},
        "edge_tts": {
            "递归": ("zh-CN-YunxiNeural", "+22%"),
            "大师": ("zh-CN-YunyangNeural", "+18%"),
        },
    },
}

_profile = VOICE_PROFILES[VOICE_PROFILE]
COSYVOICE_VOICES = _profile["cosyvoice"]
EDGE_TTS_VOICES = _profile["edge_tts"]

# ============================================================
# TTS 发音预处理词典（分类管理，按优先级依次替换）
# ============================================================

# 1️⃣ 人名音译 — 英文人名 → 中文音译（TTS 直接读中文最自然）
TTS_PERSON_NAMES = {
    # 全名（优先匹配，避免被姓氏规则截断）
    "Guillermo Rauch": "吉列尔莫·劳奇",
    "Sam Altman": "山姆·奥特曼",
    "Dario Amodei": "达里奥·阿莫代伊",
    "Daniela Amodei": "丹妮拉·阿莫代伊",
    "Demis Hassabis": "德米斯·哈萨比斯",
    "Andrej Karpathy": "安德烈·卡帕西",
    "Ilya Sutskever": "伊利亚·苏茨克维",
    "Elon Musk": "埃隆·马斯克",
    "Mark Zuckerberg": "马克·扎克伯格",
    "Satya Nadella": "萨提亚·纳德拉",
    "Sundar Pichai": "桑达尔·皮查伊",
    "Jensen Huang": "黄仁勋",
    "Aaron Levie": "亚伦·莱维",
    "Greg Brockman": "格雷格·布罗克曼",
    "Peter Yang": "彼得·杨",
    "Kevin Weil": "凯文·维尔",
    "Harrison Chase": "哈里森·切斯",
    "Emad Mostaque": "埃马德·莫斯塔克",
    "Arthur Mensch": "亚瑟·门施",
    "Noam Shazeer": "诺姆·沙泽尔",
    # 单姓名（仅当全名未匹配时触发）
    "Altman": "奥特曼",
    "Karpathy": "卡帕西",
    "Hassabis": "哈萨比斯",
    "Sutskever": "苏茨克维",
    "Nadella": "纳德拉",
    "Pichai": "皮查伊",
    "Zuckerberg": "扎克伯格",
    "Thariq": "塔里克",
    "Swyx": "斯维克斯",
}

# 2️⃣ 缩写 → 逐字母读（加空格让 TTS 逐字发音）
TTS_ACRONYMS = {
    "RLHF": "R L H F",
    "RLAIF": "R L A I F",
    "MCP": "M C P",
    "MVP": "M V P",
    "RAG": "R A G",
    "LLM": "L L M",
    "PRD": "P R D",
    "TTS": "T T S",
    "API": "A P I",
    "CEO": "C E O",
    "CTO": "C T O",
    "COO": "C O O",
    "IDE": "I D E",
    "SDK": "S D K",
    "URL": "U R L",
    "GPT": "G P T",
    "RSS": "R S S",
    "MoE": "M o E",
    "CoT": "C o T",
    "SFT": "S F T",
    "DPO": "D P O",
    "PPO": "P P O",
    "AGI": "A G I",
    "ASI": "A S I",
    "NLP": "N L P",
    "USB": "U S B",
    "SaaS": "S a a S",
    "SOTA": "S O T A",
    "TPU": "T P U",
    "GPU": "G P U",
    "VRAM": "V R A M",
    "CUDA": "C U D A",
    "MLOps": "M L Ops",
}

# 3️⃣ 产品名 → 发音优化（保留英文但拆分辅助 TTS 断词）
TTS_PRODUCT_NAMES = {
    "Claude Code": "克劳德 Code",
    "Claude Opus": "克劳德 Opus",
    "Claude Sonnet": "克劳德 Sonnet",
    "Claude Haiku": "克劳德 Haiku",
    "Claude": "克劳德",
    "ChatGPT": "Chat G P T",
    "GPT-4o": "G P T 4o",
    "GPT-4": "G P T 4",
    "GPT-5": "G P T 5",
    "Gemini": "Gemini",
    "Llama": "Llama",
    "Mistral": "Mistral",
    "Next.js": "Next JS",
    "Node.js": "Node JS",
    "Vue.js": "View JS",
    "React": "React",
    "Cursor": "Cursor",
    "Windsurf": "Wind surf",
    "Copilot": "Copilot",
    "Midjourney": "Mid journey",
    "Stable Diffusion": "Stable Diffusion",
    "LangChain": "Lang Chain",
    "LlamaIndex": "Llama Index",
    "Hugging Face": "Hugging Face",
    "v0.dev": "v zero dev",
    "Bolt.new": "Bolt new",
}

# 4️⃣ 公司名 → 发音优化
TTS_COMPANY_NAMES = {
    "OpenAI": "Open A I",
    "Anthropic": "安索匹克",
    "DeepMind": "Deep Mind",
    "DeepSeek": "Deep Seek",
    "GitHub": "Git Hub",
    "GitLab": "Git Lab",
    "Microsoft": "微软",
    "Google": "谷歌",
    "Meta": "Meta",
    "Apple": "苹果",
    "Vercel": "Vercel",
    "Replit": "Replit",
    "Figma": "Figma",
    "Notion": "Notion",
    "Perplexity": "Perplexity",
    "Cohere": "Cohere",
    "xAI": "x A I",
    "Stability AI": "Stability A I",
    "Databricks": "Data bricks",
    "Snowflake": "Snow flake",
    "Scale AI": "Scale A I",
    "Roblox": "Roblox",
}

# 5️⃣ 英文术语 → 中文翻译（TTS 读中文比读英文自然得多）
TTS_TERMS = {
    "agent-native": "代理原生",
    "Agent-native": "代理原生",
    "open source": "开源",
    "open-source": "开源",
    "fine-tuning": "微调",
    "fine-tune": "微调",
    "pre-training": "预训练",
    "pre-train": "预训练",
    "post-training": "后训练",
    "in-context learning": "上下文学习",
    "chain-of-thought": "思维链",
    "retrieval-augmented generation": "检索增强生成",
    "reinforcement learning": "强化学习",
    "multi-modal": "多模态",
    "multimodal": "多模态",
    "text-to-speech": "语音合成",
    "speech-to-text": "语音识别",
    "text-to-image": "文生图",
    "Scaling Laws": "规模定律",
    "scaling laws": "规模定律",
    "benchmark": "基准测试",
    "benchmarks": "基准测试",
    "hallucination": "幻觉",
    "hallucinations": "幻觉",
    "transformer": "Transformer架构",
    "embeddings": "向量嵌入",
    "embedding": "向量嵌入",
    "inference": "推理",
    "latency": "延迟",
    "throughput": "吞吐量",
    "distillation": "蒸馏",
    "quantization": "量化",
    "tokenizer": "分词器",
    "prompt engineering": "提示词工程",
    "context window": "上下文窗口",
    "agentic": "智能体式的",
    "workflow": "工作流",
    "workflows": "工作流",
}

# 可变停顿（毫秒）
PAUSE_MS = {
    "topic_change": 600,     # 话题切换
    "speaker_change": 300,   # 换人说话
    "same_speaker": 150,     # 同人连续
}

# 噪音过滤正则
NOISE_PATTERNS = [
    r"(?i)^(happy|merry|blessed).*(birthday|christmas|thanksgiving|holiday|new year)",
    r"^(祝|节日快乐|新年快乐|生日快乐)",
    r"^https?://\S+$",
    r"(?i)^(just watched|看了|刚看完|推荐一部).*(movie|film|电影|剧|综艺)",
    r"^(gm|gn|good morning|good night)\s*[!.]*$",
]

# AI 套话黑名单
AI_CLICHES = [
    "让我们一起", "值得注意的是", "毋庸置疑", "综上所述", "不难发现",
    "赋能", "抓手", "闭环", "由此可见", "让我们深入了解",
    "接下来让我们", "首先让我们", "最后让我们", "不可忽视的是",
]


# ============================================================
# 工具函数
# ============================================================
def preprocess_for_tts(text):
    """预处理文本，优化多语种发音和断句。

    处理顺序（长词优先，避免子串冲突）：
    1. 人名音译（最长匹配）
    2. 产品名发音优化
    3. 公司名发音优化
    4. 英文术语翻译
    5. 缩写逐字母展开
    6. 兜底：剩余全大写缩写自动加空格
    7. 中英文边界插入空格（辅助 TTS 断句）
    8. 清理（去重复标点、's → 的）
    """

    # 1. 人名音译（全名优先于姓氏，所以按长度降序）
    for name in sorted(TTS_PERSON_NAMES, key=len, reverse=True):
        text = text.replace(name, TTS_PERSON_NAMES[name])

    # 2. 产品名
    for name in sorted(TTS_PRODUCT_NAMES, key=len, reverse=True):
        text = text.replace(name, TTS_PRODUCT_NAMES[name])

    # 3. 公司名
    for name in sorted(TTS_COMPANY_NAMES, key=len, reverse=True):
        text = text.replace(name, TTS_COMPANY_NAMES[name])

    # 4. 术语翻译
    for term in sorted(TTS_TERMS, key=len, reverse=True):
        text = text.replace(term, TTS_TERMS[term])

    # 5. 缩写逐字母展开
    for acr in sorted(TTS_ACRONYMS, key=len, reverse=True):
        text = text.replace(acr, TTS_ACRONYMS[acr])

    # 6. 兜底：剩余全大写缩写（2-5字母）自动加空格
    text = re.sub(r'\b([A-Z]{2,5})\b', lambda m: ' '.join(m.group(1)), text)

    # 7. 中英文边界断句：在中文和英文字母之间确保有空格
    #    帮助 TTS 识别语言切换点，产生自然的微停顿
    #    也覆盖缩写展开后的单字母（如 "M C P是" → "M C P 是"）
    text = re.sub(r'([\u4e00-\u9fff])([A-Za-z])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z])([\u4e00-\u9fff])', r'\1 \2', text)

    # 8. 清理
    text = re.sub(r'\s{2,}', ' ', text)      # 合并多余空格
    text = re.sub(r'[，,]{2,}', '，', text)   # 合并多余逗号
    text = text.replace("'s", "的")

    return text


def call_dashscope(model, prompt, max_tokens=8000):
    """统一的 DashScope LLM 调用"""
    conn = http.client.HTTPSConnection("dashscope.aliyuncs.com")
    payload = json.dumps({
        "model": model,
        "input": {"messages": [{"role": "user", "content": prompt}]},
        "parameters": {"result_format": "message", "max_tokens": max_tokens}
    })
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json"
    }
    conn.request("POST", "/api/v1/services/aigc/text-generation/generation", payload, headers)
    resp = conn.getresponse()
    data = json.loads(resp.read().decode())

    try:
        content = data["output"]["choices"][0]["message"]["content"]
        return content
    except Exception as e:
        print(f"  LLM 调用失败 ({model}): {e}")
        print(f"  响应: {json.dumps(data, ensure_ascii=False)[:500]}")
        return None


def extract_json(content):
    """从 LLM 响应中提取 JSON"""
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    return json.loads(content.strip())


# ============================================================
# Step 1: 拉取 feed 数据
# ============================================================
def fetch_feeds():
    print("[1/7] 拉取 follow-builders feed...")
    feeds = {}
    for name, url in [("x", FEED_X_URL), ("podcasts", FEED_PODCAST_URL)]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AI-Briefing/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                feeds[name] = json.loads(resp.read().decode())
            print(f"  {name}: OK")
        except Exception as e:
            print(f"  {name}: FAILED - {e}")
            feeds[name] = {}
    return feeds


# ============================================================
# Step 2: 内容预过滤
# ============================================================
def filter_feed_content(feeds):
    """过滤噪音推文，按互动量加权排序"""
    print("[2/7] 内容预过滤...")

    x_data = feeds.get("x", {}).get("x", [])
    total_before = sum(len(b.get("tweets", [])) for b in x_data)
    filtered_builders = []

    for builder in x_data:
        good_tweets = []
        for tweet in builder.get("tweets", []):
            text = tweet.get("text", "").strip()
            # 过滤规则
            if len(text) < 10:
                continue
            if any(re.match(p, text) for p in NOISE_PATTERNS):
                continue
            good_tweets.append(tweet)

        if good_tweets:
            # 按互动量排序
            good_tweets.sort(key=lambda t: t.get("likes", 0), reverse=True)
            filtered_builders.append({**builder, "tweets": good_tweets})

    # 按最高互动量排序 builders
    filtered_builders.sort(
        key=lambda b: max((t.get("likes", 0) for t in b["tweets"]), default=0),
        reverse=True
    )

    feeds["x"]["x"] = filtered_builders
    total_after = sum(len(b.get("tweets", [])) for b in filtered_builders)
    print(f"  推文: {total_before} → {total_after}（过滤 {total_before - total_after} 条噪音）")
    return feeds


# ============================================================
# Step 3: 格式化 feed 数据
# ============================================================
def format_feed_for_prompt(feeds):
    """把 feed 数据格式化为 prompt 文本"""
    lines = []

    # X/Twitter
    x_data = feeds.get("x", {}).get("x", [])
    if x_data:
        lines.append(f"### Twitter/X 动态（{len(x_data)} 位 Builder）\n")
        for builder in x_data:
            name = builder.get("name", "")
            handle = builder.get("handle", "")
            bio = builder.get("bio", "")
            lines.append(f"**{name}** (@{handle}) — {bio}")
            for tweet in builder.get("tweets", []):
                text = tweet.get("text", "")
                likes = tweet.get("likes", 0)
                lines.append(f"  - [{likes} likes] {text}")
            lines.append("")

    # Podcasts
    podcasts = feeds.get("podcasts", {}).get("podcasts", [])
    if podcasts:
        lines.append(f"\n### 播客（{len(podcasts)} 集）\n")
        for ep in podcasts:
            name = ep.get("name", "")
            title = ep.get("title", "")
            transcript = ep.get("transcript", "")[:3000]
            lines.append(f"**{name}**: {title}")
            if transcript:
                lines.append(f"  转录摘要: {transcript[:2000]}...")
            lines.append("")

    return "\n".join(lines)


# ============================================================
# Step 4: 两步 LLM 生成
# ============================================================
def plan_content(feed_summary):
    """Call 1: qwen-plus 话题规划 + 深度分级 + 标题/描述"""
    prompt = f"""你是播客「递归大师」的内容策划。根据以下 AI 圈动态数据，筛选话题并规划内容。

## 听众画像
**AI Builder 同行**（有 AI 工具使用经验和一定开发基础）。因此：
- 基础概念（如"什么是API"）不需要解释
- 但前沿术语（如 MCP、RLHF、MoE）仍需解释，因为即使是 Builder 也未必都跟进最新概念
- 人物/公司介绍侧重"为什么他说的话值得听"而非公司基本介绍

## 四象限分级（影响大小 × 离生产力远近）
- **S 级**（深度投入，10-12段）：核心 AI 工具突破、核心概念（CoT/RAG/Scaling Laws/多模态/幻觉）、论文/模型设计原理、能直接提升生产力的技术
  ★ 时效性加权：如果某条动态是今天刚发布的重磅消息（即使偏"地图感"类），升级为 S 级，因为这是听众最关注的时刻
- **A 级**（保持地图感，4-6段）：大公司战略动向、行业格局变化、重要融资/合作，简明介绍背景即可
- **B 级**（动手试试，2-3段）：新工具/新功能发布，说清楚能干什么、怎么用
- **C 级**（跳过）：模型跑分排名、AI 末日论、公司内部八卦、输家新闻、纯营销内容、节日问候、影评、纯转发、<10字推文、重复内容

## 选题数量
由你根据当天素材质量决定：1-2 个 S 级 + 1-2 个 A 级 + 1-2 个 B 级，总共不超过 5 个。
S 级是节目核心，占时长 50%+。如果当天有重磅技术突破就集中 1 个 S 级讲透，素材分散则 2 个 S 级并重。

## 排序要求
1. 按重要性和叙事流排序（重磅新闻在前，轻松话题穿插，有思考深度的放中后段）
2. 生成一个吸引人的标题和一句话描述
3. 日期：{TODAY}

## 今日数据
{feed_summary}

## 输出格式
严格输出 JSON，不要输出其他内容：
```json
{{
  "title": "EP{TODAY} 三个关键词概括今日主题",
  "description": "一句话概括今天的核心内容，吸引听众点击",
  "topics": [
    {{
      "grade": "S",
      "title": "话题标题",
      "summary": "100字内概要，包括核心观点和为什么重要",
      "source": "谁说的 / 来源",
      "key_quotes": ["最值得引用的原文1", "原文2"],
      "exchanges": 10
    }}
  ]
}}
```"""

    print("  Call 1: qwen-plus 话题规划...")
    content = call_dashscope("qwen-plus", prompt, max_tokens=4000)
    if not content:
        return None

    try:
        plan = extract_json(content)
        s_count = sum(1 for t in plan.get("topics", []) if t.get("grade") == "S")
        a_count = sum(1 for t in plan.get("topics", []) if t.get("grade") == "A")
        b_count = sum(1 for t in plan.get("topics", []) if t.get("grade") == "B")
        print(f"  规划完成: {len(plan.get('topics', []))} 个话题（{s_count}S + {a_count}A + {b_count}B）")
        print(f"  标题: {plan.get('title', '?')}")
        return plan
    except Exception as e:
        print(f"  规划解析失败: {e}")
        return None


def generate_podcast_script(plan, feed_summary):
    """Call 2: qwen-max 基于规划生成完整对话脚本"""

    # Few-shot 示例：展示 S 级深度展开 + B 级快速带过
    few_shot = """## 好的输出示例

### 示例 1：S 级话题（12 段对话，完整深度展开 + 人物介绍 + 术语解释 + 知识锚点）

```json
[
  {"speaker": "递归", "text": "先说今天最重磅的。Vercel——就是做 Next.js 那家公司，前端开发者几乎都用过——他们的 CEO Guillermo Rauch 昨天发了一条长推，获赞两万多。他说 Vercel 要全面转向 MCP 架构，所有产品都会原生支持。", "new_topic": true},
  {"speaker": "大师", "text": "等一下，先帮大家补一个背景。Guillermo Rauch 这个人为什么说的话值得听呢？因为他一手打造了 Next.js 这个框架，直接定义了现代前端开发的范式。他说要全面转向某个方向，基本上就意味着整个前端生态要跟着动。", "new_topic": false},
  {"speaker": "递归", "text": "等等，MCP 是什么？这个缩写我之前好像听过，但不太确定具体是什么。", "new_topic": false},
  {"speaker": "大师", "text": "MCP 全称是 Model Context Protocol，模型上下文协议。你可以把它想成 AI 世界的 USB-C 接口。不管什么品牌的 AI 工具，只要支持 MCP，就能互相连接、互相调用。", "new_topic": false},
  {"speaker": "递归", "text": "哦，就是一个通用的对接标准。那 Vercel 说要全面支持，具体是什么意思？", "new_topic": false},
  {"speaker": "大师", "text": "这个我得帮大家拆解一下。以前你要让 AI 工具连上数据库、连上 GitHub、连上 Slack，每个都得单独写接口代码。有了 MCP 之后呢，就像你的手机有了 USB-C 口，充电线、耳机、U盘，一个口全搞定。Vercel 全面支持意味着，你在 Vercel 平台上部署的任何应用，都可以直接通过 MCP 被 AI 工具调用。", "new_topic": false},
  {"speaker": "递归", "text": "你看这背后其实有一个更大的趋势。AI 应用过去一年最大的瓶颈不是模型不够强，而是连接太碎片化。每个工具一套 API，开发者光对接就累死了。", "new_topic": false},
  {"speaker": "大师", "text": "没错，这正是 MCP 要解决的问题。你注意到关键词了吗？协议。不是 API，不是 SDK，是协议。就像 HTTP 协议定义了网页怎么传输，MCP 定义了 AI 工具之间怎么交互。这是基础设施级别的东西。记住这个框架：API 是点对点连线，协议是全网互通。这就是 MCP 的本质。", "new_topic": false},
  {"speaker": "递归", "text": "对，而且我看到 Anthropic 官方的数据，目前已经有超过两百个 MCP Server 在社区开源了。GitHub、Notion、Postgres 数据库、Slack，主流工具基本都有了。", "new_topic": false},
  {"speaker": "大师", "text": "速度很快。而且你注意到一个细节没有，是社区在建，不是 Anthropic 自己建。这说明什么？说明这个协议已经形成了网络效应。每多一个 MCP Server，所有 AI 工具的能力就多一分。这跟 USB 接口的发展路径一模一样。", "new_topic": false},
  {"speaker": "递归", "text": "所以对咱们 Builder 来说，现在应该做什么？", "new_topic": false},
  {"speaker": "大师", "text": "三个行动建议。第一，如果你在做 AI 应用，优先接入 MCP 而不是自己造轮子写对接代码。第二，如果你有内部工具，考虑把它包装成 MCP Server 开源出去，这是最好的开发者营销。第三，关注 Anthropic 的 MCP 规范更新，因为目前还在快速迭代，提前跟进就是竞争优势。", "new_topic": false}
]
```

### 示例 2：B 级话题（2 段，快速带过）

```json
[
  {"speaker": "递归", "text": "换个轻松点的话题。Swyx——他是 AI Engineer 大会的创始人，Developer 圈子挺有影响力的——他昨天发了一条建议，说赶紧把你的 Coding Agent 给你的设计师用。一个月之后你就会发现，原来一直是你在拖后腿。", "new_topic": true},
  {"speaker": "大师", "text": "哈，这话说得够直接的。但仔细想想确实有道理。以前设计师画完稿要等开发还原，来回改。现在设计师可以直接用 AI 把设计变成代码，跳过中间环节。值得试试，把你的 Cursor 或者 Claude Code 账号分享给团队里的非工程师。", "new_topic": false}
]
```

关键特点（必须对照检查）：
- **S 级话题 12 段对话**（6 个来回），10 段是最低标准！
- **人物/公司介绍**：首次提到 Vercel 时说"就是做 Next.js 那家公司"，首次提到 Guillermo Rauch 时说为什么他的话值得听
- **术语前置解释**：递归问"MCP 是什么？"→ 大师用类比回答（AI 世界的 USB-C 接口）
- **技术原理展开**：不只是说"MCP 很重要"，而是拆解协议 vs API 的本质区别
- **知识锚点**：留下可回忆的结构——"API 是点对点连线，协议是全网互通"
- **行动建议**：具体可操作的三步建议
- 有短回应穿插："等一下""没错""对"
- B 级话题也有人物介绍（Swyx——AI Engineer 大会创始人）
- 每段 50-100 字，不长不短"""

    prompt = f"""你是播客「递归大师」的脚本编剧。

## ⚠️ 最重要的要求：长度和深度！

这个播客目标时长 8-10 分钟。你**必须**生成：
- **最少 40 段对话**（目标 45-50 段）
- **最少 3500 字**（目标 4000 字）
- **每个 S 级话题至少 10-12 段对话**（5-6 个来回）
- **每个 A 级话题至少 4-6 段对话**（2-3 个来回）
- **开场 3-4 段，收尾 4-5 段**
宁长勿短。S 级话题是节目核心，占总时长 50%+。

## 角色人格

**递归**：好奇心旺盛的年轻 Builder。语气词多（嗯、对、哎、啊、你看啊、不过话说回来）。爱追问、爱联想。善用比喻。偶尔蹦出玩笑。说话节奏快。每段 40-100 字。
递归的特殊职责：负责「提问」——遇到术语时主动问"等等，XX是什么？"，遇到人物时帮听众问"这个人是谁啊？"

**大师**：沉稳有深度的技术老手。先拆解再给结论。科普时用费曼法：先打比方→再白话→最后给定义。偶尔回应玩笑但快速拉回正题。每段 50-120 字。口头禅："这个我得帮大家拆解一下""你注意到关键词了吗"。

## 听众画像
**AI Builder 同行**（有 AI 工具使用经验和一定开发基础）。基础概念（API、开源）不用解释，但前沿术语（MCP、RLHF、MoE）必须解释。

## 话题规划
{json.dumps(plan, ensure_ascii=False, indent=2)}

## 原始数据
{feed_summary}

## 人物与公司介绍规则（强制）
首次提到一家公司或一个人物时，必须加一句定位介绍：
- 公司：一句话说清楚"这家公司是做什么的，代表产品是什么"
  示例：不要说"Vercel的CEO发推说..."，要说"Vercel——就是做Next.js那家公司，前端开发者几乎都用过——他们的CEO Guillermo Rauch发推说..."
- 人物：一句话说清楚"这个人是什么身份，为什么他说的话值得听"
  示例：不要说"Aaron Levie指出..."，要说"Box的CEO Aaron Levie——Box是美国最大的企业云存储公司——他指出..."
- 如果同一集里同一个人/公司第二次出现，不需要重复介绍

## 专有名词前置解释（强制）
涉及专业术语、缩写、生僻概念时，必须在使用前先解释：
- 由递归提问："等等，XX是什么？" 或 "这个XX我不太懂，能解释一下吗？"
- 由大师回答：用一个生活化类比 + 一句白话定义
- 解释完再继续正题
- 每个术语只需解释一次
- 基础概念（API、开源、GitHub）不需要解释，但前沿术语（MCP、RLHF、MoE、CoT、Scaling Laws）必须解释

## S 级话题深度展开（核心，占节目 50%+ 时长）
S 级话题必须按以下结构展开（10-12段）：
1. **引出**：递归引用原文/数据，说清楚发生了什么
2. **背景**：大师给行业背景/历史脉络，解释为什么这个重要
3. **概念拆解**：核心概念用费曼法讲透（类比→白话→定义）
4. **技术原理**：如果涉及论文/模型设计，必须解释底层机制
   - 不要说"这个模型很强"，要说"它用了什么方法、解决了什么问题、跟之前的方法比有什么不同"
5. **知识锚点**：每个 S 级话题必须留一个「可回忆的结构」——一个类比、一个模型、一个心智框架
   - 好的锚点："Scaling Laws 有三根杠杆：数据量、参数量、计算量，按固定比例缩放效果最好"
   - 好的锚点："MCP 就是 AI 世界的 USB-C 接口"
   - 差的锚点："这个技术很重要"（太空洞，记不住）
6. **实际影响**：对 Builder 意味着什么
7. **动手指南**：具体可以怎么用，给出行动建议

## 对话结构

1. **S 级话题**（每个 10-12 段）：按上面的深度展开模板
2. **A 级话题**（每个 4-6 段）：递归引出 → 大师给背景 → 递归追问 → 大师简要点评影响
3. **B 级话题**（每个 2-3 段）：快速引出 → 简明点评 + 行动建议
4. **开场**（3-4 段）：递归打招呼 + 预告重点 + 大师回应
5. **收尾**（4-5 段）：总结 + 行动清单 3-5 条 + "我是递归" + "我是大师，明天见"
6. **话题过渡**：自然衔接，"好，下一个""换个话题""这跟刚才有关"
7. **穿插短回应**：嗯、对、没错、哈哈、有意思、这个观察很到位
8. **日期**：{TODAY}

## 语言要求
这是中文播客，会用 TTS 合成音频。英文发音不自然，所以：
- 产品名可以保留英文（Claude、Cursor、Next.js）
- 但英文短语/句子必须翻译成中文（"agent-native framework"→"代理原生框架"）
- 引用原文时，如果是英文，先翻译再说"原文是..."
- 缩写可以保留（API、MCP、MVP）

## 禁止出现
套话：让我们一起、值得注意的是、毋庸置疑、综上所述、不难发现、赋能、抓手、闭环、由此可见、让我们深入了解、不可忽视的是、干货十足、激动人心、令人兴奋。
重复句式：不要多次使用"这意味着什么""这对Builder们来说意味着什么"——每个话题的追问方式要不同，比如用"等等那""你看这背后""所以实际上""我好奇的是"等变体。
重复结构：不要每个话题都是"递归引用→大师拆解→递归追问→大师确认"的固定循环。要有变化：有时大师先说，有时递归自己分析，有时两人争论。

{few_shot}

## 输出
严格 JSON 数组。确保至少 40 段，至少 3500 字。不要截断。
```json
[{{"speaker":"递归","text":"...","new_topic":false}},...]
```"""

    print("  Call 2: qwen-max 生成脚本...")
    content = call_dashscope("qwen-max", prompt, max_tokens=8192)
    if not content:
        return None

    try:
        script = extract_json(content)
        total_chars = sum(len(s.get("text", "")) for s in script)
        print(f"  生成 {len(script)} 段对话，{total_chars} 字")
        return script
    except Exception as e:
        print(f"  脚本解析失败: {e}")
        if content:
            print(f"  原始内容前 300 字: {content[:300]}")
        return None


# ============================================================
# Step 5: 质量检查
# ============================================================
def validate_script(script):
    """质量检查，返回 (passed: bool, warnings: list)"""
    warnings = []

    seg_count = len(script)
    total_chars = sum(len(s.get("text", "")) for s in script)

    # 段数检查
    if seg_count < 25:
        return False, [f"段数过少: {seg_count} < 25"]

    # 字数检查
    if total_chars < 2500:
        return False, [f"字数过少: {total_chars} < 2500"]

    # 说话比例
    speaker_chars = {}
    for s in script:
        sp = s.get("speaker", "?")
        speaker_chars[sp] = speaker_chars.get(sp, 0) + len(s.get("text", ""))
    if speaker_chars:
        total = sum(speaker_chars.values())
        for speaker, chars in speaker_chars.items():
            ratio = chars / total
            if ratio < 0.25 or ratio > 0.75:
                warnings.append(f"说话比例失衡: {speaker} 占 {ratio:.0%}")

    # AI 套话检测
    cliche_hits = []
    for i, s in enumerate(script):
        text = s.get("text", "")
        for cliche in AI_CLICHES:
            if cliche in text:
                cliche_hits.append(f"第{i+1}段「{cliche}」")
    if cliche_hits:
        warnings.append(f"AI 套话 ({len(cliche_hits)} 处): {', '.join(cliche_hits[:5])}")

    # 段落过长检查
    long_segs = [i+1 for i, s in enumerate(script) if len(s.get("text", "")) > 200]
    if long_segs:
        warnings.append(f"过长段落 (>200字): 第 {', '.join(map(str, long_segs[:5]))} 段")

    # 人物/公司背景介绍检查：检测 new_topic 段是否含有介绍标记（——、就是）
    intro_markers = ["——", "就是", "也就是", "他是", "她是", "他们是", "这家公司"]
    topic_segs = [s for s in script if s.get("new_topic")]
    missing_intro = 0
    for ts in topic_segs:
        # 检查话题引出段及其后续 2 段是否有人物/公司介绍
        idx = script.index(ts)
        window = script[idx:idx+3]
        has_intro = any(
            any(marker in seg.get("text", "") for marker in intro_markers)
            for seg in window
        )
        if not has_intro:
            missing_intro += 1
    if missing_intro > 0:
        warnings.append(f"有 {missing_intro}/{len(topic_segs)} 个话题缺少人物/公司背景介绍（——或就是）")

    # S 级话题段数检查：new_topic 之间的段数
    topic_indices = [i for i, s in enumerate(script) if s.get("new_topic")]
    for k, start_idx in enumerate(topic_indices):
        end_idx = topic_indices[k+1] if k+1 < len(topic_indices) else len(script)
        seg_count_topic = end_idx - start_idx
        # 尝试从话题引出段文本判断是否为 S 级（检查是否有深度展开标志）
        # 简单启发式：如果某个话题段数 >= 8 段可能是 S 级，但低于 10 段就警告
        if seg_count_topic >= 8 and seg_count_topic < 10:
            topic_text = script[start_idx].get("text", "")[:30]
            warnings.append(f"话题「{topic_text}...」有 {seg_count_topic} 段，S 级话题建议 ≥10 段")

    return True, warnings


# ============================================================
# Step 6: TTS 合成音频
# ============================================================
def generate_silence(output_path, duration_ms):
    """生成指定时长的静音 mp3"""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        "anullsrc=r=24000:cl=mono", "-t", str(duration_ms / 1000),
        "-c:a", "libmp3lame", "-b:a", "192k", str(output_path)
    ], capture_output=True)


def synthesize_cosyvoice(text, speaker, output_path):
    """CosyVoice 单段合成 via DashScope SDK"""
    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer

    # 预处理英文发音
    text = preprocess_for_tts(text)

    dashscope.api_key = DASHSCOPE_API_KEY
    voice = COSYVOICE_VOICES.get(speaker, COSYVOICE_VOICES["递归"])
    synthesizer = SpeechSynthesizer(model="cosyvoice-v1", voice=voice)
    audio = synthesizer.call(text)
    if audio and len(audio) > 100:
        with open(output_path, "wb") as f:
            f.write(audio)
        return True
    return False


async def synthesize_edge_tts(text, speaker, output_path):
    """Edge TTS 单段合成"""
    import edge_tts

    voice, rate = EDGE_TTS_VOICES.get(speaker, EDGE_TTS_VOICES["递归"])
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_path))


async def generate_audio(script):
    """TTS 合成 + 可变停顿合并"""
    print("[5/7] TTS 合成音频...")

    output_dir = BASE_DIR / f"podcast-output-{TODAY}"
    output_dir.mkdir(exist_ok=True)

    tts_used = TTS_ENGINE

    # —— CosyVoice 合成（逐段 + 每段最多重试 3 次）——
    if TTS_ENGINE == "cosyvoice":
        import time
        COSY_MAX_RETRIES = 3
        cosy_failed = False
        for i in range(len(script)):
            seg_file = output_dir / f"seg_{i:03d}.mp3"
            for retry in range(COSY_MAX_RETRIES):
                try:
                    ok = synthesize_cosyvoice(
                        script[i]["text"], script[i]["speaker"], seg_file
                    )
                    if ok:
                        break
                    else:
                        raise Exception("返回空音频")
                except Exception as e:
                    if retry < COSY_MAX_RETRIES - 1:
                        wait = 3 * (retry + 1)
                        print(f"  CosyVoice 第{i}段失败({e})，{wait}s后重试({retry+1}/{COSY_MAX_RETRIES})...")
                        time.sleep(wait)
                    else:
                        print(f"  CosyVoice 第{i}段 {COSY_MAX_RETRIES} 次均失败，回退 Edge TTS")
                        cosy_failed = True
            if cosy_failed:
                tts_used = "edge_tts"
                break
            if (i + 1) % 10 == 0:
                print(f"  CosyVoice: {i+1}/{len(script)}")
        if not cosy_failed:
            print(f"  CosyVoice 合成完成 ({len(script)} 段)")

    # —— Edge TTS 合成 (回退) ——
    if tts_used == "edge_tts":
        import edge_tts
        BATCH = 3  # 降低并发，避免被 Edge TTS 限流 503
        MAX_RETRIES = 3
        for i in range(0, len(script), BATCH):
            batch = script[i:i+BATCH]
            for retry in range(MAX_RETRIES):
                try:
                    tasks = []
                    for j, item in enumerate(batch):
                        seg_file = output_dir / f"seg_{i+j:03d}.mp3"
                        text = preprocess_for_tts(item["text"])
                        voice, rate = EDGE_TTS_VOICES.get(item["speaker"], EDGE_TTS_VOICES["递归"])
                        communicate = edge_tts.Communicate(text, voice, rate=rate)
                        tasks.append(communicate.save(str(seg_file)))
                    await asyncio.gather(*tasks)
                    break  # 成功，跳出重试
                except Exception as e:
                    if retry < MAX_RETRIES - 1:
                        print(f"  Edge TTS 第 {i+1}-{i+len(batch)} 段失败({e.__class__.__name__})，{retry+1}/{MAX_RETRIES} 重试...")
                        await asyncio.sleep(2)
                    else:
                        raise
            print(f"  Edge TTS: {min(i+BATCH, len(script))}/{len(script)}")
            await asyncio.sleep(0.5)  # 批次间间隔，避免限流

    # —— 生成各时长静音文件 ——
    for name, ms in PAUSE_MS.items():
        generate_silence(output_dir / f"silence_{name}.mp3", ms)

    # —— 合并（可变停顿）——
    list_file = output_dir / "filelist.txt"
    with open(list_file, "w") as f:
        for i in range(len(script)):
            f.write(f"file '{output_dir}/seg_{i:03d}.mp3'\n")
            if i < len(script) - 1:
                next_item = script[i + 1]
                if next_item.get("new_topic", False):
                    pause = "topic_change"
                elif script[i]["speaker"] != next_item["speaker"]:
                    pause = "speaker_change"
                else:
                    pause = "same_speaker"
                f.write(f"file '{output_dir}/silence_{pause}.mp3'\n")

    final = BASE_DIR / f"ai-builders-daily-{TODAY}.mp3"
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
    ]
    # 全局加速（TTS_SPEED_RATIO > 1.0 时启用）
    if TTS_SPEED_RATIO != 1.0:
        ffmpeg_cmd += ["-filter:a", f"atempo={TTS_SPEED_RATIO}"]
    ffmpeg_cmd += ["-c:a", "libmp3lame", "-b:a", "192k", str(final)]
    subprocess.run(ffmpeg_cmd, capture_output=True)

    # 获取时长
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(final)],
        capture_output=True, text=True
    )
    duration = int(float(probe.stdout.strip())) if probe.stdout.strip() else 0
    size = os.path.getsize(final) if final.exists() else 0
    print(f"  音频: {final.name}, {duration//60}分{duration%60}秒, {size/1024/1024:.1f}MB")
    print(f"  TTS 引擎: {tts_used}")

    return str(final), duration


# ============================================================
# Step 7: 上传到服务器
# ============================================================
def upload_to_server(mp3_path, duration, script, plan=None):
    print("[6/7] 上传到服务器...")

    # 标题和描述来自规划（如果有）
    if plan:
        title = plan.get("title", f"EP{TODAY}")
        description = plan.get("description", "")
        # 结构化描述：加上话题列表
        topics = plan.get("topics", [])
        rss_desc = description
        if topics:
            rss_desc += "\n\n话题：\n" + "\n".join(
                f"{'★' if t.get('grade')=='S' else '●' if t.get('grade')=='A' else '·'} {t.get('title', '')}"
                for t in topics
            )
    else:
        first_lines = " ".join([s["text"] for s in script[:4]])
        title = f"EP{TODAY} {extract_title_keywords(first_lines)}"
        rss_desc = first_lines[:200]

    # 上传 MP3
    subprocess.run([
        "sshpass", "-p", SERVER_PASS, "scp", "-o", "StrictHostKeyChecking=no",
        mp3_path, f"root@{SERVER}:{SERVER_PODCAST_DIR}/episodes/{TODAY}.mp3"
    ], capture_output=True)

    # 上传 meta JSON
    meta = {
        "title": title,
        "description": rss_desc,
        "duration": duration
    }
    meta_path = BASE_DIR / f"meta-{TODAY}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    subprocess.run([
        "sshpass", "-p", SERVER_PASS, "scp", "-o", "StrictHostKeyChecking=no",
        str(meta_path), f"root@{SERVER}:{SERVER_PODCAST_DIR}/episodes/{TODAY}.json"
    ], capture_output=True)

    # 远程更新 RSS
    subprocess.run([
        "sshpass", "-p", SERVER_PASS, "ssh", "-o", "StrictHostKeyChecking=no",
        f"root@{SERVER}", f"python3 {SERVER_PODCAST_DIR}/rss-generator.py"
    ], capture_output=True)

    print(f"  已上传: {title}")
    print(f"  RSS 已更新")
    return title


def extract_title_keywords(text):
    """从前几段对话提取标题关键词（回退用）"""
    keywords = []
    for word in ["Claude", "Cursor", "OpenAI", "Gemini", "GPT", "Token",
                 "Agent", "Anthropic", "Skill", "Composer", "Channel",
                 "Replit", "Vercel", "模型", "发布", "更新", "开源"]:
        if word.lower() in text.lower():
            keywords.append(word)
    return "、".join(keywords[:4]) if keywords else "AI 圈今日动态"


# ============================================================
# Step 8: 飞书推送
# ============================================================
def push_to_feishu(title, mp3_url, duration=0, warnings=None):
    print("[7/7] 飞书推送...")

    # 获取 tenant_access_token
    conn = http.client.HTTPSConnection("open.feishu.cn")
    payload = json.dumps({
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    })
    conn.request("POST", "/open-apis/auth/v3/tenant_access_token/internal",
                 payload, {"Content-Type": "application/json"})
    resp = conn.getresponse()
    token_data = json.loads(resp.read().decode())
    token = token_data.get("tenant_access_token", "")

    if not token:
        print(f"  获取 token 失败: {token_data}")
        return

    # 构建消息
    lines = [f"AI Builders Daily {TODAY}", "", title, ""]
    lines.append(f"播客已更新：{mp3_url}")
    lines.append(f"RSS：http://{SERVER}:8081/podcast/feed.xml")

    if duration > 0:
        lines.append(f"时长：{duration//60}分{duration%60}秒")

    # 质量警告
    if duration > 0 and duration < 300:
        lines.append("\n⚠ 时长不足 5 分钟，建议检查")
    if warnings:
        lines.append("\n质量提示：")
        for w in warnings[:3]:
            lines.append(f"  - {w}")

    msg_content = {"text": "\n".join(lines)}

    conn2 = http.client.HTTPSConnection("open.feishu.cn")
    send_payload = json.dumps({
        "receive_id": FEISHU_USER_OPEN_ID,
        "msg_type": "text",
        "content": json.dumps(msg_content)
    })
    conn2.request("POST",
                  "/open-apis/im/v1/messages?receive_id_type=open_id",
                  send_payload,
                  {
                      "Content-Type": "application/json",
                      "Authorization": f"Bearer {token}"
                  })
    send_resp = conn2.getresponse()
    send_data = json.loads(send_resp.read().decode())

    if send_data.get("code") == 0:
        print(f"  飞书推送成功！")
    else:
        print(f"  飞书推送失败: {send_data.get('msg', send_data)}")


# ============================================================
# 保存脚本文本
# ============================================================
def save_script_text(script, plan=None):
    print("  保存脚本文本...")
    txt_path = BASE_DIR / f"podcast-script-{TODAY}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        title = plan.get("title", f"AI Builders Daily — {TODAY}") if plan else f"AI Builders Daily — {TODAY}"
        f.write(f"{title} 播客脚本\n\n")
        f.write(f"主持人：递归、大师\n")
        f.write(f"段数：{len(script)}，字数：{sum(len(s.get('text','')) for s in script)}\n\n")
        f.write(f"{'—'*40}\n\n")
        for item in script:
            f.write(f"{item['speaker']}：{item['text']}\n\n")
    print(f"  已保存: {txt_path.name}")


# ============================================================
# Main
# ============================================================
def main():
    print(f"{'='*50}")
    print(f"AI Builders Daily 流水线 v2")
    print(f"日期: {TODAY}")
    print(f"TTS: {TTS_ENGINE}")
    print(f"{'='*50}\n")

    # 1. 拉取数据
    feeds = fetch_feeds()
    x_count = len(feeds.get("x", {}).get("x", []))
    tweet_count = sum(len(b.get("tweets", [])) for b in feeds.get("x", {}).get("x", []))
    podcast_count = len(feeds.get("podcasts", {}).get("podcasts", []))

    if x_count == 0 and podcast_count == 0:
        print("今日无新数据，跳过。")
        return

    print(f"  数据: {x_count} 位 Builder, {tweet_count} 条推文, {podcast_count} 集播客\n")

    # 2. 预过滤
    feeds = filter_feed_content(feeds)

    # 3. 格式化
    feed_summary = format_feed_for_prompt(feeds)

    # 4. 两步 LLM 生成（含重试）
    print("[3/7] 两步 LLM 生成...")
    plan = None
    script = None
    warnings = []

    for attempt in range(2):
        # Call 1: 规划
        plan = plan_content(feed_summary)
        if not plan:
            print("  话题规划失败，终止。")
            return

        # Call 2: 脚本
        script = generate_podcast_script(plan, feed_summary)
        if not script:
            print("  脚本生成失败，终止。")
            return

        # 质量检查
        print("[4/7] 质量检查...")
        passed, warnings = validate_script(script)
        if passed:
            print(f"  通过！{len(script)} 段, {sum(len(s.get('text','')) for s in script)} 字")
            if warnings:
                for w in warnings:
                    print(f"  ⚠ {w}")
            break
        else:
            print(f"  未通过（第 {attempt+1} 次）: {warnings}")
            if attempt == 0:
                print("  重试生成...")

    if not script:
        print("脚本生成失败，终止。")
        return

    # 5. TTS 合成
    mp3_path, duration = asyncio.run(generate_audio(script))

    # 6. 上传服务器
    title = upload_to_server(mp3_path, duration, script, plan)

    # 7. 飞书推送
    mp3_url = f"http://{SERVER}:8081/podcast/episodes/{TODAY}.mp3"
    push_to_feishu(title, mp3_url, duration, warnings)

    # 保存脚本
    save_script_text(script, plan)

    print(f"\n{'='*50}")
    print(f"流水线完成！")
    print(f"音频: {mp3_path}")
    print(f"时长: {duration//60}分{duration%60}秒")
    print(f"RSS: http://{SERVER}:8081/podcast/feed.xml")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
