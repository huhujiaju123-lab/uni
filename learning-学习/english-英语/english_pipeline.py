#!/usr/bin/env python3
"""
宝宝英语日课 — 亲子英语播客生成 Pipeline
Parent-Child English Podcast Generator

基于递归大师 pipeline 改造，复用 TTS/音频组装/上传模块。
"""

import asyncio
import http.client
import json
import os
import re
import subprocess
import sys
import shutil
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置
# ============================================================
from english_config import *

TODAY = datetime.now().strftime("%Y-%m-%d")
EPISODE_DIR = EPISODES_DIR / TODAY


# ============================================================
# 工具函数
# ============================================================

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def call_dashscope(model, prompt, max_tokens=4000):
    """调用通义千问 API（复用递归大师的方式）"""
    conn = http.client.HTTPSConnection("dashscope.aliyuncs.com")
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }
    body = json.dumps({
        "model": model,
        "input": {"messages": [{"role": "user", "content": prompt}]},
        "parameters": {"max_tokens": max_tokens, "result_format": "message"},
    })
    conn.request("POST", "/api/v1/services/aigc/text-generation/generation", body, headers)
    resp = conn.getresponse()
    data = json.loads(resp.read().decode())
    try:
        return data["output"]["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        log(f"LLM 调用失败: {json.dumps(data, ensure_ascii=False)[:500]}")
        return None


def extract_json(text):
    """从 LLM 输出中提取 JSON"""
    # 尝试 ```json ... ``` 格式
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # 尝试直接解析
    return json.loads(text)


# ============================================================
# Step 1: 选择今日场景
# ============================================================

def select_scene():
    """从 learner_state 中选择下一个场景"""
    state = json.loads(LEARNER_STATE_PATH.read_text())
    queue = state.get("scene_queue", [])
    covered = state.get("recent_scenes_covered", [])

    if queue:
        scene_id = queue[0]
    else:
        # 队列为空，从主题库中选一个未覆盖的
        all_scenes = []
        for cat in SCENE_CATEGORIES.values():
            all_scenes.extend(cat["scenes"])
        remaining = [s for s in all_scenes if s not in covered]
        scene_id = remaining[0] if remaining else all_scenes[0]

    # 找到场景所属类别
    category_name = "日常作息"
    for cat_key, cat in SCENE_CATEGORIES.items():
        if scene_id in cat["scenes"]:
            category_name = cat["name"]
            break

    log(f"今日场景: {scene_id} ({category_name})")
    return scene_id, category_name


# ============================================================
# Step 2: LLM 生成四段式脚本
# ============================================================

def plan_episode(scene_id, category_name):
    """qwen-plus 规划集数结构"""
    prompt = f"""你是一位亲子英语教育专家，帮助中国妈妈（英语 B1+ 水平）学会用地道英语和 2 岁宝宝互动。

今天的场景是：**{scene_id.replace('_', ' ')}**（{category_name}）

请规划一集亲子英语播客的内容大纲，输出 JSON：

```json
{{
  "scene_id": "{scene_id}",
  "scene_title_en": "场景英文标题",
  "scene_title_zh": "场景中文标题",
  "scene_description": "用 1-2 句话描述这个场景，妈妈和宝宝在做什么",
  "key_phrases": [
    {{
      "phrase": "地道英文表达",
      "chinese_equivalent": "中国妈妈可能会说的中式英语",
      "native_version": "美国妈妈怎么说",
      "context": "什么时候用",
      "examples": ["例句1", "例句2"]
    }}
  ],
  "scene_dialogue": [
    {{"speaker": "mom", "text": "妈妈说的英文", "action": "（动作描述）"}},
    {{"speaker": "baby", "text": "宝宝可能的反应", "action": "（动作描述）"}}
  ],
  "shadow_sentences": ["跟读句子1", "跟读句子2"],
  "try_it_suggestions": ["今天就能用的具体建议1", "建议2", "建议3"]
}}
```

要求：
1. key_phrases 给出 5 个地道表达，每个必须对比"中式英语" vs "美国妈妈说法"
2. scene_dialogue 写 10-15 轮自然对话，妈妈的话要真实自然（不是教科书英语）
3. 宝宝的反应要符合 2 岁特征（简单词、动作、情绪）
4. shadow_sentences 精选 8-10 个最实用的句子
5. try_it_suggestions 给 3 个今天就能实践的具体建议
6. 所有英文用美式英语，口语化，温暖有爱"""

    log("正在规划集数内容...")
    result = call_dashscope(LLM_PLANNING["model"], prompt, LLM_PLANNING["max_tokens"])
    if not result:
        return None
    try:
        return extract_json(result)
    except json.JSONDecodeError:
        log(f"JSON 解析失败，原始输出: {result[:500]}")
        return None


def generate_script(plan):
    """qwen-max 生成完整四段式播客脚本"""

    few_shot_example = """示例输出（bath_time 场景）：
[
  {"part": "intro", "lang": "zh", "text": "大家好，欢迎收听宝宝英语日课。今天我们来学习洗澡时间怎么和宝宝用英语互动。"},

  {"part": "scene", "pass": 1, "lang": "en", "text": "Okay sweetie, it's bath time! Let's go to the bathroom."},
  {"part": "scene", "pass": 1, "lang": "en", "text": "Can you help mommy turn on the water? Good job!"},
  {"part": "scene", "pass": 1, "lang": "en", "text": "Let's check the water. Is it warm enough? Nice and warm!"},
  {"part": "scene", "pass": 1, "lang": "en", "text": "Time to take off your clothes. Arms up! One, two, three!"},
  {"part": "scene", "pass": 1, "lang": "en", "text": "Let's get in the tub. Splash splash! Do you like the water?"},
  {"part": "scene", "pass": 1, "lang": "en", "text": "Here's your rubber ducky. Quack quack!"},
  {"part": "scene", "pass": 1, "lang": "en", "text": "Let me wash your hair. Tip your head back, baby. Good girl!"},
  {"part": "scene", "pass": 1, "lang": "en", "text": "Now let's wash your tummy. Round and round! Tickle tickle!"},
  {"part": "scene", "pass": 1, "lang": "en", "text": "All clean! Let's get out. Here's your towel. So cozy!"},

  {"part": "scene", "pass": 2, "lang": "en", "text": "Okay sweetie, it's bath time! Let's go to the bathroom."},
  {"part": "scene", "pass": 2, "lang": "zh", "text": "注意这里说 it's bath time，美国妈妈不会说 let's take a bath now，而是直接用 it's bath time 这种简洁的方式。sweetie 是对宝宝的昵称，非常自然。"},

  {"part": "decode", "lang": "zh", "text": "第一个表达：It's bath time! 美国妈妈在提醒宝宝做某件事时，最常用的句型是 It's + 名词 + time。比如 It's bedtime, It's snack time, It's nap time。"},
  {"part": "decode", "lang": "en", "text": "It's bath time. It's bedtime. It's snack time."},
  {"part": "decode", "lang": "zh", "text": "中国妈妈可能会说 Let's go take a bath 或 We need to take a bath now，但地道的说法更简洁——It's bath time，三个词搞定。"},

  {"part": "shadow", "lang": "en", "speed": "normal", "text": "It's bath time!"},
  {"part": "shadow", "lang": "silence", "duration_ms": 2000},
  {"part": "shadow", "lang": "en", "speed": "slow", "text": "It's bath time!"},

  {"part": "tryit", "lang": "zh", "text": "今晚给宝宝洗澡前，试着说 It's bath time! Let's go to the bathroom. 宝宝可能不会马上理解，但你的语气和动作会帮她理解意思。坚持几天，她就会知道 bath time 是什么意思了。"}
]"""

    prompt = f"""你是一位亲子英语播客脚本作家。请根据以下内容大纲，生成完整的播客脚本。

## 内容大纲
```json
{json.dumps(plan, ensure_ascii=False, indent=2)}
```

## 脚本格式

输出一个 JSON 数组，每个元素是一个语音段落：

```json
[
  {{"part": "intro|scene|decode|shadow|tryit", "lang": "en|zh|silence", "speed": "normal|slow", "text": "内容", "pass": 1|2, "duration_ms": 2000}}
]
```

## 四段结构要求

### 1. intro（开场，中文，2-3 段）
- 简短问候 + 今天的场景介绍

### 2. scene（场景沉浸，英文为主）
- **pass 1**：纯英文对话（10-15 段），妈妈对宝宝说的自然英语
  - 语气温暖、口语化，像真的在跟宝宝说话
  - 穿插拟声词（splash, quack, vroom）
  - 句子短（3-8 词为主）
- **pass 2**：逐句重复 + 中文讲解
  - 每句英文后跟一段中文，解释"为什么这样说"、"美国妈妈的习惯"

### 3. decode（核心讲解，中英混合，5 个表达）
- 每个表达：
  - 中文：这个表达是什么、为什么不说中式英语版本
  - 英文：原句 + 2 个变体例句
  - 中文：使用场景和技巧
- 语言标记要准确：中文讲解用 "zh"，英文例句用 "en"

### 4. shadow（跟读，英文）
- 8-10 个核心句子
- 每句格式：
  - {{"part": "shadow", "lang": "en", "speed": "normal", "text": "句子"}}
  - {{"part": "shadow", "lang": "silence", "duration_ms": 2000}}
  - {{"part": "shadow", "lang": "en", "speed": "slow", "text": "句子"}}

### 5. tryit（实践引导，中文，2-3 段）
- 3 个今天就能用的具体建议
- 要具体到场景和句子，不要空洞的鼓励

## 参考示例

{few_shot_example}

## 质量要求
- 总段数 ≥ 30
- 英文总字数 ≥ 500
- 英文必须是美式口语，不要书面语
- 中文讲解简洁有趣，不要说教
- 禁止以下套话：{', '.join(CLICHE_BLACKLIST)}
- 每个英文句子对宝宝说时不超过 8 个词

请输出完整 JSON 数组："""

    log("正在生成四段式脚本...")
    result = call_dashscope(LLM_SCRIPT["model"], prompt, LLM_SCRIPT["max_tokens"])
    if not result:
        return None
    try:
        return extract_json(result)
    except json.JSONDecodeError:
        log(f"JSON 解析失败，原始输出: {result[:500]}")
        return None


# ============================================================
# Step 3: 质量检查
# ============================================================

def validate_script(script):
    """检查脚本质量"""
    warnings = []
    passed = True

    # 段数检查
    if len(script) < QUALITY_GATES["min_segments"]:
        warnings.append(f"段数不足: {len(script)} < {QUALITY_GATES['min_segments']}")
        passed = False

    # 英文内容检查
    en_texts = [s["text"] for s in script if s.get("lang") == "en"]
    en_chars = sum(len(t) for t in en_texts)
    if en_chars < QUALITY_GATES.get("min_english_chars", 400):
        warnings.append(f"英文内容偏少: {en_chars} 字符")

    # 跟读句子检查
    shadow_count = len([s for s in script if s.get("part") == "shadow" and s.get("lang") == "en" and s.get("speed") == "normal"])
    if shadow_count < QUALITY_GATES["min_shadow_sentences"]:
        warnings.append(f"跟读句子不足: {shadow_count} < {QUALITY_GATES['min_shadow_sentences']}")

    # 讲解表达检查
    decode_zh = [s for s in script if s.get("part") == "decode" and s.get("lang") == "zh"]
    if len(decode_zh) < QUALITY_GATES["min_phrases"]:
        warnings.append(f"核心表达讲解不足: {len(decode_zh)}")

    # 套话检查
    all_text = " ".join(s.get("text", "") for s in script)
    for cliche in CLICHE_BLACKLIST:
        if cliche in all_text:
            warnings.append(f"检测到套话: {cliche}")

    # 四段完整性
    parts_found = set(s.get("part") for s in script)
    required_parts = {"intro", "scene", "decode", "shadow", "tryit"}
    missing = required_parts - parts_found
    if missing:
        warnings.append(f"缺少段落: {missing}")
        passed = False

    if warnings:
        log(f"质量检查: {len(warnings)} 条警告")
        for w in warnings:
            log(f"  ⚠️  {w}")
    else:
        log("质量检查通过 ✅")

    return passed, warnings


# ============================================================
# Step 4: TTS 合成
# ============================================================

async def synthesize_edge_tts(text, voice, rate, output_path):
    """Edge TTS 合成（英文 + 中文备选）"""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)


def synthesize_cosyvoice(text, voice_id, output_path):
    """CosyVoice 合成（中文讲解）"""
    try:
        from dashscope.audio.tts_v2 import SpeechSynthesizer
        synthesizer = SpeechSynthesizer(model="cosyvoice-v1", voice=voice_id)
        audio = synthesizer.call(text)
        with open(output_path, "wb") as f:
            f.write(audio)
        return True
    except Exception as e:
        log(f"CosyVoice 失败: {e}")
        return False


def generate_silence(output_path, duration_ms):
    """生成静音段（用于跟读空白）"""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(duration_ms / 1000),
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(output_path)
    ], capture_output=True)


async def synthesize_all(script):
    """合成所有语音段"""
    EPISODE_DIR.mkdir(parents=True, exist_ok=True)
    segments_dir = EPISODE_DIR / "segments"
    segments_dir.mkdir(exist_ok=True)

    segment_files = []

    for i, seg in enumerate(script):
        output_path = segments_dir / f"seg_{i:03d}.mp3"
        lang = seg.get("lang", "en")
        text = seg.get("text", "")
        speed = seg.get("speed", "normal")

        if lang == "silence":
            # 跟读空白
            duration = seg.get("duration_ms", PAUSES["shadow_gap"])
            generate_silence(output_path, duration)
            segment_files.append(str(output_path))
            continue

        if not text.strip():
            continue

        if lang == "en":
            # 英文用 Edge TTS
            voice, rate = EDGE_TTS_VOICES["en_slow"] if speed == "slow" else EDGE_TTS_VOICES["en_normal"]
            try:
                await synthesize_edge_tts(text, voice, rate, str(output_path))
                segment_files.append(str(output_path))
            except Exception as e:
                log(f"Edge TTS 失败 seg_{i}: {e}")

        elif lang == "zh":
            # 中文优先 CosyVoice，失败用 Edge TTS
            voice_id = COSYVOICE_VOICES["zh_host"]
            success = False
            for attempt in range(3):
                if synthesize_cosyvoice(text, voice_id, str(output_path)):
                    success = True
                    break
                await asyncio.sleep(3 * (attempt + 1))

            if not success:
                # 回退到 Edge TTS 中文
                voice, rate = EDGE_TTS_VOICES["zh_host"]
                try:
                    await synthesize_edge_tts(text, voice, rate, str(output_path))
                    success = True
                except Exception as e:
                    log(f"中文 TTS 全部失败 seg_{i}: {e}")

            if success:
                segment_files.append(str(output_path))

        log(f"  TTS {i+1}/{len(script)}: {lang} {'✅' if output_path.name in [Path(f).name for f in segment_files] else '❌'}")

    return segment_files


# ============================================================
# Step 5: 音频组装
# ============================================================

def assemble_audio(script, segment_files):
    """将所有语音段 + 停顿组装为最终 MP3"""
    segments_dir = EPISODE_DIR / "segments"

    # 预生成停顿文件
    pause_files = {}
    for name, ms in PAUSES.items():
        pause_path = segments_dir / f"pause_{name}.mp3"
        generate_silence(pause_path, ms)
        pause_files[name] = str(pause_path)

    # 创建 filelist
    filelist_path = segments_dir / "filelist.txt"
    entries = []
    prev_part = None

    seg_idx = 0
    for i, seg in enumerate(script):
        if seg.get("lang") == "silence" or not seg.get("text", "").strip():
            if seg.get("lang") == "silence" and seg_idx < len(segment_files):
                entries.append(f"file '{segment_files[seg_idx]}'")
                seg_idx += 1
            continue

        if seg_idx >= len(segment_files):
            break

        # 插入停顿
        curr_part = seg.get("part")
        if prev_part and curr_part != prev_part:
            entries.append(f"file '{pause_files['part_change']}'")
        elif prev_part:
            curr_lang = seg.get("lang")
            prev_lang = script[i-1].get("lang") if i > 0 else None
            if curr_lang != prev_lang:
                entries.append(f"file '{pause_files['speaker_change']}'")
            elif curr_part == "scene":
                entries.append(f"file '{pause_files['scene_sentence']}'")
            else:
                entries.append(f"file '{pause_files['decode_example']}'")

        entries.append(f"file '{segment_files[seg_idx]}'")
        seg_idx += 1
        prev_part = curr_part

    filelist_path.write_text("\n".join(entries))

    # ffmpeg 合并
    output_path = EPISODE_DIR / f"english-daily-{TODAY}.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(filelist_path),
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(output_path)
    ], capture_output=True)

    # 获取时长
    result = subprocess.run(
        ["ffprobe", "-i", str(output_path), "-show_entries", "format=duration",
         "-v", "quiet", "-of", "csv=p=0"],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip()) if result.stdout.strip() else 0

    log(f"音频组装完成: {output_path.name} ({duration:.0f}s = {duration/60:.1f}min)")
    return str(output_path), duration


# ============================================================
# Step 6: 保存元数据和脚本文本
# ============================================================

def save_metadata(plan, script, duration, warnings):
    """保存集数元数据"""
    meta = {
        "date": TODAY,
        "scene_id": plan.get("scene_id"),
        "scene_title_en": plan.get("scene_title_en"),
        "scene_title_zh": plan.get("scene_title_zh"),
        "duration": round(duration),
        "segments": len(script),
        "phrases_count": len(plan.get("key_phrases", [])),
        "shadow_count": len([s for s in script if s.get("part") == "shadow" and s.get("lang") == "en" and s.get("speed") == "normal"]),
        "warnings": warnings,
    }
    meta_path = EPISODE_DIR / f"{TODAY}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    log(f"元数据已保存: {meta_path}")
    return meta


def save_script_text(script):
    """保存可读文本版脚本"""
    lines = []
    current_part = None
    part_names = {
        "intro": "【开场】",
        "scene": "【场景沉浸】",
        "decode": "【核心讲解】",
        "shadow": "【跟读训练】",
        "tryit": "【实践引导】",
    }

    for seg in script:
        part = seg.get("part", "")
        if part != current_part:
            lines.append(f"\n{'='*40}")
            lines.append(part_names.get(part, part))
            lines.append('='*40)
            current_part = part

        lang = seg.get("lang", "")
        text = seg.get("text", "")
        speed = seg.get("speed", "")

        if lang == "silence":
            lines.append(f"  [跟读空白 {seg.get('duration_ms', 2000)}ms]")
        elif lang == "en":
            prefix = "🔊" if speed == "slow" else "🇺🇸"
            lines.append(f"  {prefix} {text}")
        elif lang == "zh":
            lines.append(f"  🇨🇳 {text}")

    script_path = EPISODE_DIR / f"{TODAY}-script.txt"
    script_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"文字脚本已保存: {script_path}")


def update_learner_state(scene_id):
    """更新学习者状态"""
    state = json.loads(LEARNER_STATE_PATH.read_text())
    state["episodes_completed"] = state.get("episodes_completed", 0) + 1

    covered = state.get("recent_scenes_covered", [])
    if scene_id not in covered:
        covered.append(scene_id)
    state["recent_scenes_covered"] = covered

    queue = state.get("scene_queue", [])
    if scene_id in queue:
        queue.remove(scene_id)
    state["scene_queue"] = queue

    LEARNER_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    log(f"学习状态已更新: 已完成 {state['episodes_completed']} 集")


# ============================================================
# Main Pipeline
# ============================================================

def main():
    log(f"{'='*50}")
    log(f"宝宝英语日课 — {TODAY}")
    log(f"{'='*50}")

    # Step 1: 选择场景
    scene_id, category_name = select_scene()

    # Step 2: 规划内容
    plan = plan_episode(scene_id, category_name)
    if not plan:
        log("❌ 内容规划失败")
        return

    # Step 3: 生成脚本（最多重试 2 次）
    script = None
    for attempt in range(2):
        script = generate_script(plan)
        if not script:
            log(f"❌ 脚本生成失败 (尝试 {attempt + 1}/2)")
            continue

        passed, warnings = validate_script(script)
        if passed:
            break
        elif attempt == 0:
            log("重新生成脚本...")
            script = None

    if not script:
        log("❌ 脚本生成最终失败")
        return

    # Step 4: 保存文字版脚本
    EPISODE_DIR.mkdir(parents=True, exist_ok=True)
    save_script_text(script)

    # Step 5: TTS 合成
    log("开始 TTS 合成...")
    segment_files = asyncio.run(synthesize_all(script))
    if not segment_files:
        log("❌ TTS 合成失败")
        return

    # Step 6: 音频组装
    mp3_path, duration = assemble_audio(script, segment_files)

    # Step 7: 保存元数据
    meta = save_metadata(plan, script, duration, warnings)

    # Step 8: 更新学习状态
    update_learner_state(scene_id)

    log(f"\n{'='*50}")
    log(f"✅ 完成！")
    log(f"  场景: {plan.get('scene_title_zh', scene_id)}")
    log(f"  时长: {duration/60:.1f} 分钟")
    log(f"  文件: {mp3_path}")
    log(f"  脚本: {EPISODE_DIR}/{TODAY}-script.txt")
    log(f"{'='*50}")


if __name__ == "__main__":
    main()
