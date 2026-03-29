#!/usr/bin/env python3
"""
学习引擎播客生成器
复用递归大师的 TTS 引擎，从脚本 JSON 生成个性化播客音频

用法:
  python generate_podcast-生成播客.py <script.json> [output.mp3]
"""
import json
import sys
import subprocess
import time
from pathlib import Path

# ── 配置 ──
DASHSCOPE_API_KEY = "sk-e1151b380b82414d9b29470dd5ec448f"

COSYVOICE_VOICES = {"递归": "longcheng", "大师": "longshu"}
EDGE_TTS_VOICES = {
    "递归": ("zh-CN-YunxiNeural", "+26%"),
    "大师": ("zh-CN-YunyangNeural", "+22%"),
}

TTS_SPEED_RATIO = 1.2  # 全局加速

PAUSE_MS = {
    "topic_change": 600,
    "speaker_change": 300,
    "same_speaker": 150,
}

# ── 发音预处理 ──
PRONUNCIATION_DICT = {
    "Skills": "斯基尔斯",
    "Skill": "斯基尔",
    "Claude": "克劳德",
    "Code": "扣的",
    "Claude Code": "克劳德 扣的",
    "extension points": "扩展点",
    "gotchas": "踩坑点",
    "i+1": "i 加 1",
    "i+3": "i 加 3",
    "Bloom": "布鲁姆",
    "Anthropic": "安索匹克",
    "SQL": "S Q L",
    "API": "A P I",
    "SDK": "S D K",
    "hooks": "钩子",
    "TTS": "T T S",
    "LLM": "大语言模型",
    "MCP": "M C P",
    "Feynman": "费曼",
    "Krashen": "克拉申",
    "ODS": "O D S",
    "ads": "A D S",
    "order item": "订单明细",
    "tenant": "租户",
    "LKUS": "L K U S",
    "count star": "count 星号",
    "count distinct": "count distinct",
    "progressive disclosure": "渐进式披露",
}

def preprocess_for_tts(text):
    """发音预处理"""
    import re
    for en, zh in sorted(PRONUNCIATION_DICT.items(), key=lambda x: -len(x[0])):
        text = text.replace(en, zh)
    # 中英文边界加空格
    text = re.sub(r'([a-zA-Z0-9])([^\x00-\x7F])', r'\1 \2', text)
    text = re.sub(r'([^\x00-\x7F])([a-zA-Z0-9])', r'\1 \2', text)
    return text


def synthesize_cosyvoice(text, speaker, output_path):
    """CosyVoice 单段合成"""
    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer

    text = preprocess_for_tts(text)
    dashscope.api_key = DASHSCOPE_API_KEY
    voice = COSYVOICE_VOICES.get(speaker, "longcheng")
    synthesizer = SpeechSynthesizer(model="cosyvoice-v1", voice=voice)
    audio = synthesizer.call(text)
    if audio and len(audio) > 100:
        with open(output_path, "wb") as f:
            f.write(audio)
        return True
    return False


def generate_silence(output_path, duration_ms):
    """生成静音片段"""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        "anullsrc=r=24000:cl=mono", "-t", str(duration_ms / 1000),
        "-c:a", "libmp3lame", "-b:a", "192k", str(output_path)
    ], capture_output=True)


def main():
    if len(sys.argv) < 2:
        print("用法: python generate_podcast-生成播客.py <script.json> [output.mp3]")
        sys.exit(1)

    script_path = Path(sys.argv[1])
    script = json.loads(script_path.read_text())

    output_mp3 = Path(sys.argv[2]) if len(sys.argv) > 2 else script_path.with_suffix(".mp3")

    # 工作目录
    work_dir = script_path.parent / "tts_segments"
    work_dir.mkdir(exist_ok=True)

    print(f"📻 开始生成播客: {len(script)} 段对话")
    print(f"   输出: {output_mp3.name}")

    # 1. 生成静音文件
    print("🔇 生成停顿...")
    for name, ms in PAUSE_MS.items():
        generate_silence(work_dir / f"silence_{name}.mp3", ms)

    # 2. 逐段 TTS 合成
    print("🎙️  TTS 合成中...")
    for i, seg in enumerate(script):
        seg_file = work_dir / f"seg_{i:03d}.mp3"
        for retry in range(3):
            try:
                ok = synthesize_cosyvoice(seg["text"], seg["speaker"], seg_file)
                if ok:
                    break
                else:
                    raise Exception("返回空音频")
            except Exception as e:
                if retry < 2:
                    wait = 3 * (retry + 1)
                    print(f"  ⚠️  第{i}段失败({e})，{wait}s后重试...")
                    time.sleep(wait)
                else:
                    print(f"  ❌ 第{i}段失败，跳过")

        if (i + 1) % 5 == 0 or i == len(script) - 1:
            print(f"  进度: {i+1}/{len(script)}")

    # 3. 生成拼接列表
    print("🔗 拼接音频...")
    list_file = work_dir / "filelist.txt"
    with open(list_file, "w") as f:
        for i in range(len(script)):
            seg_file = work_dir / f"seg_{i:03d}.mp3"
            if not seg_file.exists():
                continue
            # 用相对于 filelist.txt 所在目录的文件名
            f.write(f"file 'seg_{i:03d}.mp3'\n")
            if i < len(script) - 1:
                next_seg = script[i + 1]
                if next_seg.get("new_topic", False):
                    pause = "topic_change"
                elif script[i]["speaker"] != next_seg["speaker"]:
                    pause = "speaker_change"
                else:
                    pause = "same_speaker"
                f.write(f"file 'silence_{pause}.mp3'\n")

    # 4. FFmpeg 合并 + 加速
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
    ]
    if TTS_SPEED_RATIO != 1.0:
        ffmpeg_cmd += ["-filter:a", f"atempo={TTS_SPEED_RATIO}"]
    ffmpeg_cmd += ["-c:a", "libmp3lame", "-b:a", "192k", str(output_mp3)]
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FFmpeg 错误: {result.stderr[-500:]}")

    # 5. 输出信息
    if output_mp3.exists():
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(output_mp3)],
            capture_output=True, text=True
        )
        duration = int(float(probe.stdout.strip())) if probe.stdout.strip() else 0
        size = output_mp3.stat().st_size
        print(f"\n✅ 播客生成完成!")
        print(f"   文件: {output_mp3}")
        print(f"   时长: {duration//60}分{duration%60}秒")
        print(f"   大小: {size/1024/1024:.1f}MB")
    else:
        print("❌ 生成失败")

    # 6. 清理临时文件（成功后才清理）
    if output_mp3.exists():
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
