#!/usr/bin/env python3
"""AI Builders Daily v3 — 自然对话，不用 SSML"""

import asyncio
import edge_tts
import os
import subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "podcast-output-v3"
OUTPUT_DIR.mkdir(exist_ok=True)

# 递归 = YunxiNeural chat 风格（活泼跳脱）
# 大师 = YunyangNeural（沉稳有深度）
VOICES = {
    "递归": ("zh-CN-YunxiNeural", "+22%"),
    "大师": ("zh-CN-YunyangNeural", "+18%"),
}

SCRIPT = [
    ("递归", "嗨！各位早上好，这里是 AI Builders Daily。我是递归。"),
    ("大师", "我是大师。今天三月二十号，昨天 AI 圈有不少动静，挑重点聊。"),
    ("递归", "先预告一下，今天最大的新闻是 Anthropic 让你用手机直接操控 Claude Code 了。另外 Cursor 放了 Composer 2，还有一个值得展开的概念，就是以后工作产出可能按 Token 算，不按小时算。"),
    ("大师", "最后这个我也想展开聊。好，进正题。"),

    # Claude Code Channels
    ("递归", "第一条，Anthropic 的 Thariq 发了条推，一万七千多赞，说 Claude Code 支持 Channels 了。你可以通过 Telegram、Discord 直接在手机上操控你电脑上的 Claude Code。"),
    ("大师", "帮大家拆解一下。以前用 Claude Code 必须坐在电脑前开终端。现在呢，你在地铁上掏出手机发一句查一下昨天的数据，电脑上的 Claude Code 就开始跑了。而且不是阉割版，是完整能力。"),
    ("递归", "Peter Yang 说了句特别逗的，他说，我都躺床上用了，还叫 Code 是不是有点奇怪？不如叫 Clawd，加个 W。"),
    ("大师", "哈哈，名字不错。但这背后有个重要趋势，AI 的交互界面一直在演进。从 API 到网页，到 IDE 插件，现在是即时通讯。方向就是越来越贴近你本来就在用的工具。"),
    ("递归", "对，这从根本上改变了使用模式。以前是坐下来专门用 AI，现在是随时随地见缝插针地用。使用频率和场景一下就打开了。目前支持 Telegram 和 Discord，飞书微信社区在做桥接。"),

    # Cursor Composer 2
    ("大师", "第二条，Cursor 发布了 Composer 2。先科普一下，Cursor 是一款内置 AI 的代码编辑器。Composer 是核心功能，你用自然语言说想做什么，它帮你跨文件把代码写出来。"),
    ("递归", "设计负责人 Ryo Lu 四个词概括：前沿智能、低成本、快速。但更有说服力的是实测。Dan Shipper 让 Composer 2 跟 GPT 5.4 对打，然后让 GPT 5.4 自己当裁判，结果 GPT 判自己输了。"),
    ("大师", "这说明 Cursor 在编排层做了很好的优化。什么是编排层呢？底层模型就像一个超级聪明的大脑，但它需要合适的指令才能发挥最好。怎么写 prompt、怎么组织上下文、怎么调用工具，这些就是编排层。同样的模型，经过精心编排效果可以翻倍。就像同一把刀，厨师和新手切出来的菜完全不一样。"),
    ("递归", "所以两个启发。第一，Claude Code 和 Cursor 各有所长，可以搭配用。第二，如果你做 AI 产品，编排层才是壁垒，不是底层模型。"),

    # Token 预算
    ("大师", "第三个话题多聊几分钟。Box 的 CEO Aaron Levie 的核心观点是：未来每个人的工作产出取决于他能调用多少 Token。"),
    ("递归", "Token 就是 AI 的计量单位，你可以理解为 AI 的字数。问 AI 一个问题消耗 Token，AI 回答也消耗 Token。一个中文字大约一到两个 Token。"),
    ("大师", "他的逻辑是这样的。有了 AI Agent 之后，一个人可以同时跑好几个 Agent，一个分析数据、一个写报告、一个审代码。产出上限不再取决于你能工作多少小时，而是你能调度多少 AI 算力。"),
    ("递归", "工业革命之前，产出等于人力乘以时间。工业革命之后变成机器数量乘以运转时间。AI 时代就变成了 Token 消耗量乘以编排效率。注意关键词，编排效率。不是谁消耗 Token 多谁厉害，而是谁能用同样的 Token 做出更好的结果。"),
    ("大师", "他还说了一句，也许以后 CFO 才是 AI 负责人，因为 Token 就是钱，给每个员工分配多少 Token 预算就是财务决策。对我们个人来说，从现在开始关注你的 Token 效率，同一类任务能不能用更少的 Token 完成，这会成为核心竞争力。"),

    # 设计师 + Agent
    ("递归", "轻松点的话题。Swyx 建议说，赶紧把你的 Coding Agent 给设计师用，一个月后你会发现原来一直是你在拖后腿。"),
    ("大师", "有道理。以前设计师画完稿要等开发还原，来回改。现在设计师可以直接用 AI 把设计变成代码，跳过中间环节。一个人就是一个产品团队。"),

    # Benedict Evans
    ("大师", "最后聊一下 Benedict Evans 的播客。他是科技领域最有影响力的分析师之一，前 a16z 合伙人。他跟 Matt Turck 聊了个尖锐问题：OpenAI 有没有护城河？"),
    ("递归", "Evans 的观点是，OpenAI 手里是商品化技术，Google 能做、Anthropic 能做、Meta 也能做。OpenAI 有的只是品牌知名度。"),
    ("大师", "他还提了个概念叫即兴软件。AI 让写代码变得便宜，以前不值得做的软件现在都可以做了。所以世界上会有更多软件，不是更少。那种人人写自己软件的说法他认为是错的，但会有更多开发者做更多垂直场景软件。"),
    ("递归", "这对 Builder 是好消息，市场在膨胀。关键是找到以前做不了、现在可以做的场景。"),

    # 收尾
    ("大师", "好，总结一下今天的 Builder 行动清单。"),
    ("递归", "第一，试试 Claude Code Channels，用手机操控 Claude。第二，关注 Cursor Composer 2，了解工具格局。第三，开始追踪你的 Token 使用效率。"),
    ("大师", "第四，把 AI 工具介绍给设计师朋友。第五，去看看 Prompt to Chip 可视化网站，从头到尾了解 AI 怎么工作的。"),
    ("递归", "今天的 AI Builders Daily 就到这里。我是递归。"),
    ("大师", "我是大师。明天见，祝你 build something amazing。"),
]


async def generate_segment(index: int, speaker: str, text: str):
    """生成单个音频片段"""
    voice, rate = VOICES[speaker]
    output_file = OUTPUT_DIR / f"seg_{index:03d}.mp3"
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_file))
    return str(output_file)


async def main():
    print(f"共 {len(SCRIPT)} 段对话，开始生成...")

    BATCH = 10
    for i in range(0, len(SCRIPT), BATCH):
        batch = SCRIPT[i:i+BATCH]
        tasks = [generate_segment(i+j, s, t) for j, (s, t) in enumerate(batch)]
        await asyncio.gather(*tasks)
        print(f"  已完成 {min(i+BATCH, len(SCRIPT))}/{len(SCRIPT)}")

    # 生成 200ms 静音
    silence = OUTPUT_DIR / "silence.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        "anullsrc=r=24000:cl=mono", "-t", "0.2",
        "-c:a", "libmp3lame", "-b:a", "192k", str(silence)
    ], capture_output=True)

    # 合并列表
    list_file = OUTPUT_DIR / "filelist.txt"
    with open(list_file, "w") as f:
        for i in range(len(SCRIPT)):
            f.write(f"file '{OUTPUT_DIR}/seg_{i:03d}.mp3'\n")
            if i < len(SCRIPT) - 1:
                f.write(f"file '{silence}'\n")

    final = Path(__file__).parent / "ai-builders-daily-2026-03-20-v3.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:a", "libmp3lame", "-b:a", "192k", str(final)
    ], capture_output=True)

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(final)],
        capture_output=True, text=True
    )
    dur = float(probe.stdout.strip())
    size = os.path.getsize(final) / (1024*1024)
    print(f"\n{'='*50}")
    print(f"播客生成完成！")
    print(f"文件: {final}")
    print(f"时长: {int(dur//60)}分{int(dur%60)}秒")
    print(f"大小: {size:.1f} MB")
    print(f"主持: 递归 (Yunxi) + 大师 (Yunyang)")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
