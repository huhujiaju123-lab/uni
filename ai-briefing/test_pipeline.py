#!/usr/bin/env python3
"""
递归大师 Pipeline 端到端测试
在服务器上跑，验证从生成到发布的完整链路。
用 test 日期避免污染生产数据，测试完自动清理。
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# 加载 pipeline 模块
sys.path.insert(0, str(Path(__file__).parent))
import daily_pipeline as dp

TEST_DATE = "9999-12-31"  # 不会和真实日期冲突
PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


def test_environment():
    """测试 1: 运行环境"""
    print("\n[测试 1/6] 运行环境")

    check("Python 版本 ≥ 3.9", sys.version_info >= (3, 9), f"当前 {sys.version}")

    # dashscope
    try:
        from dashscope.audio.tts_v2 import SpeechSynthesizer
        check("dashscope SDK", True)
    except ImportError as e:
        check("dashscope SDK", False, str(e))

    # edge_tts
    try:
        import edge_tts
        check("edge_tts", True)
    except ImportError as e:
        check("edge_tts", False, str(e))

    # ffmpeg
    r = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    check("ffmpeg", r.returncode == 0)

    # on_server 检测
    on_server = Path(dp.SERVER_PODCAST_DIR).exists()
    check("on_server 检测", on_server, f"SERVER_PODCAST_DIR={dp.SERVER_PODCAST_DIR}")


def test_feed_fetch():
    """测试 2: Feed 拉取"""
    print("\n[测试 2/6] Feed 拉取")

    feeds = dp.fetch_feeds()
    x_data = feeds.get("x", {}).get("x", [])
    podcast_data = feeds.get("podcasts", {}).get("podcasts", [])

    check("X feed 有数据", len(x_data) > 0, f"拿到 {len(x_data)} 个 Builder")
    tweet_count = sum(len(b.get("tweets", [])) for b in x_data)
    check("推文数量 > 0", tweet_count > 0, f"{tweet_count} 条推文")

    # 预过滤
    feeds = dp.filter_feed_content(feeds)
    filtered_count = sum(len(b.get("tweets", [])) for b in feeds.get("x", {}).get("x", []))
    check("预过滤正常", filtered_count > 0 and filtered_count <= tweet_count,
          f"过滤后 {filtered_count} 条")

    return feeds


def test_tts_preprocessing():
    """测试 3: TTS 发音预处理"""
    print("\n[测试 3/6] TTS 发音预处理")

    cases = [
        ("Sam Altman说", "山姆·奥特曼说", "人名音译"),
        ("MCP协议", "M C P 协议", "缩写展开"),
        ("Claude Code很好用", "克劳德 Code 很好用", "产品名"),
        ("OpenAI发布了", "Open A I 发布了", "公司名"),
        ("fine-tuning效果好", "微调效果好", "术语翻译"),
        ("用Cursor写代码", "用 Cursor 写代码", "中英边界空格"),
    ]

    for input_text, expected_fragment, desc in cases:
        result = dp.preprocess_for_tts(input_text)
        check(f"预处理: {desc}", expected_fragment in result,
              f"输入='{input_text}' 期望含='{expected_fragment}' 实际='{result}'")


def test_tts_synthesis():
    """测试 4: TTS 合成（CosyVoice + Edge TTS）"""
    print("\n[测试 4/6] TTS 合成")

    test_dir = Path(dp.BASE_DIR) / "test-tts-output"
    test_dir.mkdir(exist_ok=True)

    test_text = "大家好，这是一段测试语音，用来验证语音合成是否正常工作。"

    # CosyVoice
    cosy_file = test_dir / "test_cosyvoice.mp3"
    try:
        ok = dp.synthesize_cosyvoice(test_text, "递归", cosy_file)
        check("CosyVoice 合成", ok and cosy_file.exists() and cosy_file.stat().st_size > 1000,
              f"文件大小: {cosy_file.stat().st_size if cosy_file.exists() else 0}")
    except Exception as e:
        check("CosyVoice 合成", False, str(e))

    # Edge TTS
    import asyncio
    edge_file = test_dir / "test_edge.mp3"
    try:
        import edge_tts
        voice, rate = dp.EDGE_TTS_VOICES.get("大师", dp.EDGE_TTS_VOICES["递归"])
        communicate = edge_tts.Communicate(test_text, voice, rate=rate)
        asyncio.run(communicate.save(str(edge_file)))
        check("Edge TTS 合成", edge_file.exists() and edge_file.stat().st_size > 1000,
              f"文件大小: {edge_file.stat().st_size if edge_file.exists() else 0}")
    except Exception as e:
        check("Edge TTS 合成", False, str(e))

    # 1.2x 加速
    if cosy_file.exists():
        sped_file = test_dir / "test_1.2x.mp3"
        r = subprocess.run([
            "ffmpeg", "-y", "-i", str(cosy_file),
            "-filter:a", f"atempo={dp.TTS_SPEED_RATIO}",
            "-c:a", "libmp3lame", "-b:a", "192k", str(sped_file)
        ], capture_output=True)
        check("ffmpeg 1.2x 加速", r.returncode == 0 and sped_file.exists())

    # 清理
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)


def test_upload_and_rss():
    """测试 5: 上传 + RSS 生成（用测试日期）"""
    print("\n[测试 5/6] 上传 + RSS 生成")

    ep_dir = Path(dp.SERVER_PODCAST_DIR) / "episodes"
    test_mp3 = ep_dir / f"{TEST_DATE}.mp3"
    test_json = ep_dir / f"{TEST_DATE}.json"
    rss_path = Path(dp.SERVER_PODCAST_DIR) / "static" / "feed.xml"

    try:
        # 生成一个假 MP3（静音 1 秒）
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", "1", "-c:a", "libmp3lame", "-b:a", "192k", str(test_mp3)
        ], capture_output=True)
        check("测试 MP3 生成", test_mp3.exists())

        # 模拟 upload_to_server 的服务器本地逻辑
        on_server = Path(dp.SERVER_PODCAST_DIR).exists()
        check("on_server=True", on_server)

        # 写 meta JSON
        meta = {
            "title": f"TEST-{TEST_DATE} 测试集",
            "description": "自动化测试，稍后删除",
            "duration": 1
        }
        with open(test_json, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        check("meta JSON 写入", test_json.exists())

        # RSS 生成
        r = subprocess.run(
            ["python3", f"{dp.SERVER_PODCAST_DIR}/rss-generator.py"],
            capture_output=True, text=True
        )
        check("RSS 生成成功", r.returncode == 0, r.stderr[:200] if r.stderr else "")

        # 验证 RSS 包含测试集
        if rss_path.exists():
            rss_content = rss_path.read_text()
            check("RSS 包含测试集", f"TEST-{TEST_DATE}" in rss_content)
            check("RSS 包含 iTunes 标签", "itunes:duration" in rss_content)
            check("RSS 包含域名", "podcast.uniwang.com.cn" in rss_content)

            # 统计集数
            episode_count = rss_content.count("<item>")
            check(f"RSS 集数正确 (期望≥4)", episode_count >= 4,
                  f"实际 {episode_count} 集")
        else:
            check("RSS 文件存在", False, "feed.xml 不存在")

    finally:
        # 清理测试数据
        test_mp3.unlink(missing_ok=True)
        test_json.unlink(missing_ok=True)

        # 重新生成 RSS（去掉测试集）
        subprocess.run(
            ["python3", f"{dp.SERVER_PODCAST_DIR}/rss-generator.py"],
            capture_output=True
        )
        print("  🧹 测试数据已清理")


def test_full_pipeline_dryrun():
    """测试 6: Pipeline 干跑（LLM 规划 → 脚本前 3 段 → 验证质量检查）"""
    print("\n[测试 6/6] Pipeline 干跑（LLM + 质量检查）")

    # Feed
    feeds = dp.fetch_feeds()
    feeds = dp.filter_feed_content(feeds)
    feed_summary = dp.format_feed_for_prompt(feeds)
    check("Feed 格式化", len(feed_summary) > 100, f"{len(feed_summary)} 字符")

    # LLM Call 1: 规划
    plan = dp.plan_content(feed_summary)
    check("话题规划成功", plan is not None and "topics" in plan)

    if plan:
        topics = plan.get("topics", [])
        s_count = sum(1 for t in topics if t.get("grade") == "S")
        check(f"有 S 级话题", s_count > 0, f"S={s_count}, 总={len(topics)}")
        check("有标题", bool(plan.get("title")))

        # LLM Call 2: 脚本
        script = dp.generate_podcast_script(plan, feed_summary)
        check("脚本生成成功", script is not None and len(script) > 0)

        if script:
            # 质量检查
            passed, warnings = dp.validate_script(script)
            total_chars = sum(len(s.get("text", "")) for s in script)
            check(f"质量检查通过 ({len(script)}段/{total_chars}字)", passed,
                  "; ".join(warnings) if warnings else "")

            if warnings:
                for w in warnings:
                    print(f"    ⚠ {w}")


def main():
    global PASS, FAIL

    print("=" * 50)
    print("递归大师 Pipeline 端到端测试")
    print(f"运行位置: {Path.cwd()}")
    print(f"on_server: {Path(dp.SERVER_PODCAST_DIR).exists()}")
    print("=" * 50)

    test_environment()
    feeds = test_feed_fetch()
    test_tts_preprocessing()
    test_tts_synthesis()
    test_upload_and_rss()
    test_full_pipeline_dryrun()

    print(f"\n{'=' * 50}")
    print(f"测试结果: {PASS} 通过 / {FAIL} 失败")
    if FAIL == 0:
        print("🎉 全部通过！Pipeline 可以稳定运行。")
    else:
        print("⚠️ 有失败项，请检查上面的 ❌ 详情。")
    print("=" * 50)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
