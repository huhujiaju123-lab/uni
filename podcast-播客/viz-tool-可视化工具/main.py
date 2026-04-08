#!/usr/bin/env python3
"""
播客可视化工具主入口
用法：python3 main.py "https://www.xiaoyuzhoufm.com/episode/xxx"
输出：./output/{episode_id}/ 下的完整可视化网页
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

# 确保当前目录在 Python 路径中
TOOL_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(TOOL_DIR))

DEEPGRAM_SCRIPT = Path.home() / ".claude/skills/deepgram-transcription/transcribe.py"


def check_dependencies():
    """检查必要的环境变量和依赖"""
    errors = []
    if not os.getenv("ANTHROPIC_API_KEY"):
        errors.append("❌ 未设置 ANTHROPIC_API_KEY（Claude API 分析需要）")
    if not os.getenv("DEEPGRAM_API_KEY"):
        errors.append("❌ 未设置 DEEPGRAM_API_KEY（音频转录需要）")
    if not DEEPGRAM_SCRIPT.exists():
        errors.append(f"❌ 未找到转录脚本：{DEEPGRAM_SCRIPT}")

    if errors:
        print("\n".join(errors))
        sys.exit(1)


def step_fetch(url: str) -> dict:
    """Step 1：获取元数据"""
    print("\n" + "=" * 50)
    print("📡 Step 1/4：获取播客元数据")
    print("=" * 50)

    from fetcher import fetch_metadata
    metadata = fetch_metadata(url)

    if not metadata.get("audio_url"):
        print("❌ 无法获取音频直链，请确认：")
        print("   1. URL 是否为小宇宙单集页面（/episode/xxx）")
        print("   2. 该单集是否为付费内容")
        sys.exit(1)

    return metadata


def step_transcribe(audio_url: str, output_dir: str, episode_id: str, language: str = "zh") -> dict:
    """Step 2：音频转录"""
    print("\n" + "=" * 50)
    print("🎙️  Step 2/4：音频转录（Deepgram）")
    print("=" * 50)

    prefix = "transcript"
    txt_path = os.path.join(output_dir, f"{prefix}.txt")
    json_path = os.path.join(output_dir, f"{prefix}.json")

    # 如果转录文件已存在，跳过
    if os.path.exists(txt_path) and os.path.getsize(txt_path) > 100:
        print(f"⏭️  转录文件已存在，跳过转录：{txt_path}")
        return {"success": True, "txt_file": txt_path, "json_file": json_path}

    cmd = [
        sys.executable,
        str(DEEPGRAM_SCRIPT),
        audio_url,
        "--language", language,
        "--output-prefix", prefix,
        "--output-dir", output_dir,
    ]

    print(f"   音频：{audio_url[:80]}...")
    print(f"   语言：{language}")
    print(f"   输出：{output_dir}/")
    print(f"   请耐心等待（长音频可能需要 5-10 分钟）...\n")

    result = subprocess.run(cmd, capture_output=False, text=True, timeout=700)

    if result.returncode != 0:
        print(f"❌ 转录失败（退出码 {result.returncode}）")
        sys.exit(1)

    if not os.path.exists(txt_path):
        print(f"❌ 转录脚本执行完成，但未找到输出文件：{txt_path}")
        sys.exit(1)

    return {"success": True, "txt_file": txt_path, "json_file": json_path}


def step_analyze(transcript_path: str, output_dir: str, metadata: dict) -> dict:
    """Step 3：Claude AI 内容分析"""
    print("\n" + "=" * 50)
    print("🧠 Step 3/4：AI 内容分析（Claude）")
    print("=" * 50)

    episode_json_path = os.path.join(output_dir, "episode.json")

    # 如果分析结果已存在，跳过
    if os.path.exists(episode_json_path) and os.path.getsize(episode_json_path) > 100:
        print(f"⏭️  分析文件已存在，跳过分析：{episode_json_path}")
        with open(episode_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    from analyzer import analyze_transcript
    episode_data = analyze_transcript(transcript_path, episode_json_path, metadata)
    return episode_data


def step_generate(episode_json_path: str, output_dir: str, metadata: dict) -> str:
    """Step 4：生成可视化 HTML"""
    print("\n" + "=" * 50)
    print("🎨 Step 4/4：生成可视化网页")
    print("=" * 50)

    html_path = os.path.join(output_dir, "visualization.html")

    # 尝试导入 generator（由队友实现）
    generator_path = TOOL_DIR / "generator.py"
    if not generator_path.exists():
        print(f"⚠️  generator.py 尚未实现，跳过 HTML 生成")
        print(f"   等待前端开发者实现 generator.py 后即可完成")
        return None

    try:
        sys.path.insert(0, str(TOOL_DIR))
        from generator import render
        html_path = render(episode_json_path, html_path)
        return html_path
    except ImportError as e:
        print(f"⚠️  generator.py 导入失败：{e}")
        print(f"   episode.json 已就绪，等待 generator.py 实现即可")
        return None


def print_summary(output_dir: str, metadata: dict, html_path: str = None):
    """打印最终结果摘要"""
    print("\n" + "=" * 50)
    print("🎉 处理完成！")
    print("=" * 50)
    print(f"\n📁 输出目录：{output_dir}")
    print(f"   ├── transcript.txt      转录文本（带时间戳）")
    print(f"   ├── transcript.json     Deepgram 原始响应")
    print(f"   ├── episode.json        结构化内容数据")
    if html_path:
        print(f"   └── visualization.html  🌐 可视化网页")
        print(f"\n👉 用浏览器打开：{html_path}")
    else:
        print(f"   └── visualization.html  （等待 generator.py 实现）")


def main():
    parser = argparse.ArgumentParser(
        description="播客可视化工具 — 小宇宙链接 → 交互式网页",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python3 main.py "https://www.xiaoyuzhoufm.com/episode/674a16478d5d7e073a18b4cc"
  python3 main.py "https://www.xiaoyuzhoufm.com/episode/xxx" --language zh --skip-transcribe
        """
    )
    parser.add_argument("url", help="小宇宙单集页面 URL")
    parser.add_argument("--language", "-l", default="zh", help="音频语言（默认：zh）")
    parser.add_argument("--output-dir", "-o", default=None, help="输出根目录（默认：./output）")
    parser.add_argument("--skip-transcribe", action="store_true", help="跳过转录（已有 transcript.txt 时使用）")
    parser.add_argument("--skip-analyze", action="store_true", help="跳过分析（已有 episode.json 时使用）")

    args = parser.parse_args()

    print("🎙️  播客可视化工具 v0.1")
    print(f"   输入：{args.url}")

    # 检查依赖
    check_dependencies()

    # Step 1: 获取元数据
    metadata = step_fetch(args.url)
    episode_id = metadata["episode_id"]

    # 创建输出目录
    base_output = args.output_dir or os.path.join(TOOL_DIR, "output")
    output_dir = os.path.join(base_output, episode_id)
    os.makedirs(output_dir, exist_ok=True)

    # 保存元数据
    meta_path = os.path.join(output_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    transcript_path = os.path.join(output_dir, "transcript.txt")
    episode_json_path = os.path.join(output_dir, "episode.json")

    # Step 2: 转录
    if not args.skip_transcribe:
        step_transcribe(metadata["audio_url"], output_dir, episode_id, args.language)
    else:
        print(f"\n⏭️  跳过转录（--skip-transcribe）")
        if not os.path.exists(transcript_path):
            print(f"❌ 找不到转录文件：{transcript_path}")
            sys.exit(1)

    # Step 3: 内容分析
    if not args.skip_analyze:
        episode_data = step_analyze(transcript_path, output_dir, metadata)
    else:
        print(f"\n⏭️  跳过分析（--skip-analyze）")
        if not os.path.exists(episode_json_path):
            print(f"❌ 找不到分析文件：{episode_json_path}")
            sys.exit(1)
        with open(episode_json_path, "r", encoding="utf-8") as f:
            episode_data = json.load(f)

    # Step 4: 生成 HTML
    html_path = step_generate(episode_json_path, output_dir, metadata)

    # 结果摘要
    print_summary(output_dir, metadata, html_path)


if __name__ == "__main__":
    main()
