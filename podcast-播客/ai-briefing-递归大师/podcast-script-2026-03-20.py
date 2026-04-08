#!/usr/bin/env python3
"""AI Builders Daily — 播客生成脚本 2026-03-20"""

import asyncio
import edge_tts
import os
import subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "podcast-output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 声音配置
VOICE_A = "zh-CN-YunxiNeural"    # 小宇 — 男声，年轻有活力
VOICE_B = "zh-CN-XiaoxiaoNeural"  # 小夏 — 女声，明亮温暖

# 语速和语调微调
RATE_A = "+5%"
RATE_B = "+0%"

# ============================================================
# 播客脚本
# ============================================================
SCRIPT = [
    # (speaker, text)
    # 开场
    ("B", "嗨，早上好！欢迎来到 AI Builders Daily，我是小夏。"),
    ("A", "我是小宇。今天是 2026 年 3 月 20 号，AI 圈昨天发生了不少事，我们挑重点聊。"),
    ("B", "先给大家剧透一下：今天有一个大新闻，Anthropic 让你用手机直接操控 Claude Code 了。另外，Cursor 放了个大招，还有一个特别有意思的概念——你的工作产出以后可能不是按小时算，而是按 Token 算。"),
    ("A", "听起来很科幻，但其实已经在发生了。我们一个一个来。"),

    # 第一段：Claude Code Channels
    ("B", "好，第一条，也是昨天最炸裂的。Anthropic 的 Thariq 发了一条推，一天之内拿了一万七千多个赞。他说：Claude Code 现在支持 Channels 了，你可以通过 Telegram 和 Discord 直接在手机上给你的 Claude Code 发消息。"),
    ("A", "这个怎么理解呢？以前用 Claude Code，你必须坐在电脑前面，打开终端。现在呢，你躺在沙发上，掏出手机，在 Telegram 里发一句话，你电脑上的 Claude Code 就会帮你执行。写代码、查数据、跑脚本，全都行。"),
    ("B", "对，而且它不是一个简化版。它是完整的 Claude Code 能力，只是换了个入口。Roblox 的产品经理 Peter Yang 说了一句很有意思的话，他说：我都是躺在床上用它了，这东西还叫 Claude Code 是不是有点奇怪？不如叫 Clawd，加个 w。"),
    ("A", "哈哈哈，这个命名不错。"),
    ("B", "说真的，这背后有一个很重要的趋势。AI 工具正在从坐在工位上用，变成随时随地用。就像手机银行取代了柜台一样，AI 的交互界面正在从终端走向即时通讯。"),
    ("A", "对于我们 Builder 来说，这意味着什么呢？你可以通勤的时候让 Claude 帮你跑个数据，吃饭的时候让它生成个报告。你的 AI 助手变成了 24 小时在线的同事。"),
    ("B", "目前支持 Telegram 和 Discord，飞书和微信还没有官方支持，但是社区已经有人在做桥接了。如果你正好在搞飞书机器人——嗯，你懂的。"),

    # 第二段：Cursor Composer 2
    ("A", "好，第二条。Cursor 发布了 Composer 2。Cursor 的设计负责人 Ryo Lu 发了四个词：前沿智能、低成本、快速、Composer 2。"),
    ("B", "Cursor 是什么？简单说，它是一个内置了 AI 的代码编辑器。而 Composer 是它里面最核心的功能，你可以理解为：你告诉它你想做什么，它帮你把代码写出来。"),
    ("A", "Composer 2 厉害在哪呢？Dan Shipper 做了一个测试，他让 Composer 2 和 GPT 5.4 同时做一个任务，然后让 GPT 5.4 和 Claude Opus 来当裁判。结果 Composer 2 赢了。"),
    ("B", "等一下，GPT 5.4 自己当裁判，判自己输了？"),
    ("A", "对，就是这么诚实。这说明 Cursor 在 AI 编程这个赛道上确实做到了很高的水准。对于我们 Builder 来说，了解不同工具的优劣很重要。Claude Code 擅长复杂推理和长上下文，Cursor 擅长快速编辑和设计集成。两个工具各有所长，不冲突。"),

    # 第三段：Token 预算
    ("B", "接下来聊一个概念，我觉得特别值得深入。Box 的 CEO Aaron Levie 说了一段很长的话，核心意思是：未来每个人的工作产出，本质上取决于他能调用多少 Token。"),
    ("A", "这个需要解释一下。Token 是什么？你可以把它想象成 AI 的字数。你每问 AI 一个问题，AI 每给你一个回答，都在消耗 Token。一个 Token 大约等于一个中文字或者半个英文单词。"),
    ("B", "Aaron Levie 的意思是，以前衡量一个人的产出是看他工作了多少小时。以后可能是看他消耗了多少 Token。因为 AI Agent 可以并行跑，一个人可以同时让好几个 Agent 帮他做事——一个在分析数据，一个在写报告，一个在跑实验。"),
    ("A", "这就像工业革命的时候，产出从雇了多少人变成有多少台机器。现在是从工作多少小时变成能调度多少 AI 算力。"),
    ("B", "他还说了一句特别有意思的话：也许以后 CFO 才是真正的 AI 负责人。因为 AI 最终是一个预算问题——你愿意为一个员工投入多少 Token 预算？"),
    ("A", "所以对我们来说，有一个很实际的启示：开始关注你的 Token 使用效率。同样的任务，能不能用更少的 Token 完成？或者同样的 Token 预算，能不能产出更多？这会成为一个核心竞争力。"),

    # 第四段：设计师 + Agent
    ("B", "好，再说一条轻松点的。Swyx 昨天发了一条建议，他说：赶紧把你的 Coding Agent 给你的设计师用。一个月之后你会发现，之前一直是你在拖后腿。"),
    ("A", "哈哈，这话说得够扎心的。"),
    ("B", "但他说的有道理。以前设计师设计完了，要等开发来实现。现在设计师可以直接用 AI 把设计变成代码。中间那个等待环节消失了。"),
    ("A", "我们之前装的那个 Frontend Design Skill 其实就是这个方向。它让 AI 写出来的代码有设计感，不再是千篇一律的 AI 味。设计师加上 Agent，等于一个人就是一个产品团队。"),

    # 第五段：播客深度
    ("B", "最后我们快速聊一下 Benedict Evans 的播客。他跟 Matt Turck 聊了一个很尖锐的问题：OpenAI 有没有护城河？"),
    ("A", "Evans 的观点很直接：OpenAI 手里拿的是商品化技术，竞争对手是有巨额现金流的科技巨头，自己没有基础设施，也没什么真正的差异化。有的只是巨大的品牌知名度。"),
    ("B", "他还提了一个概念叫即兴软件。意思是，AI 让写代码变得非常便宜，所以会出现大量以前不值得写的软件。不是所有人都会写自己的软件，但会有更多的软件被创造出来。"),
    ("A", "这对 Builder 来说是好消息。市场在变大，不是在缩小。关键是找到那些以前不值得做、现在可以做的场景。"),

    # 收尾
    ("B", "好，今天的内容就到这里。快速总结一下今天的 Builder 行动清单："),
    ("A", "第一，试试 Claude Code Channels，用手机操控你的 Claude。第二，关注 Cursor Composer 2，了解 AI 编程工具的最新格局。第三，开始思考你的 Token 使用效率，这会是未来的核心指标。"),
    ("B", "第四，如果你身边有设计师，把你的 AI 工具分享给他们。第五，去看看 Prompt to Chip 那个可视化网站，帮你理解 AI 从头到尾是怎么工作的。"),
    ("A", "今天的 AI Builders Daily 就到这里。我是小宇。"),
    ("B", "我是小夏。明天见，祝你有一个高效的一天！"),
]


async def generate_segment(index: int, speaker: str, text: str):
    """生成单个音频片段"""
    voice = VOICE_A if speaker == "A" else VOICE_B
    rate = RATE_A if speaker == "A" else RATE_B
    output_file = OUTPUT_DIR / f"seg_{index:03d}_{speaker}.mp3"

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_file))
    return str(output_file)


async def main():
    print(f"共 {len(SCRIPT)} 段对话，开始生成...")

    # 并发生成所有音频片段
    tasks = []
    for i, (speaker, text) in enumerate(SCRIPT):
        tasks.append(generate_segment(i, speaker, text))

    files = await asyncio.gather(*tasks)
    print(f"已生成 {len(files)} 个音频片段")

    # 生成 ffmpeg 合并文件列表
    list_file = OUTPUT_DIR / "filelist.txt"
    with open(list_file, "w") as f:
        for i in range(len(SCRIPT)):
            speaker = SCRIPT[i][0]
            seg_file = OUTPUT_DIR / f"seg_{i:03d}_{speaker}.mp3"
            # 加一个短暂停顿
            f.write(f"file '{seg_file}'\n")

    # 合并为最终音频
    final_output = Path(__file__).parent / "ai-builders-daily-2026-03-20.mp3"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(final_output)
    ]

    print("正在合并音频...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        # 获取时长
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(final_output)],
            capture_output=True, text=True
        )
        duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        size_mb = os.path.getsize(final_output) / (1024 * 1024)

        print(f"\n✅ 播客生成完成！")
        print(f"📁 文件: {final_output}")
        print(f"⏱️  时长: {minutes}分{seconds}秒")
        print(f"💾 大小: {size_mb:.1f} MB")
    else:
        print(f"❌ 合并失败: {result.stderr}")


if __name__ == "__main__":
    asyncio.run(main())
