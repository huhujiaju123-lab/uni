#!/usr/bin/env python3
"""AI Builders Daily v2 — 自然对话风格播客"""

import asyncio
import edge_tts
import os
import subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "podcast-output-v2"
OUTPUT_DIR.mkdir(exist_ok=True)

# 递归 = 男声 YunxiNeural (chat style, 活泼有表现力)
# 大师 = 男声 YunyangNeural (chat style, 沉稳有深度)
# 两个男声搭配，一个跳脱一个稳重，更像真实播客拍档

VOICES = {
    "递归": {
        "voice": "zh-CN-YunxiNeural",
        "style": "chat",
        "degree": "2",
        "rate": "+22%",
        "pitch": "+6%",
    },
    "大师": {
        "voice": "zh-CN-YunyangNeural",
        "style": "chat",
        "degree": "1.5",
        "rate": "+18%",
        "pitch": "+0%",
    },
}

# ============================================================
# 播客脚本 v2 — 自然对话，有深度
# ============================================================
SCRIPT = [
    # ---------- 开场 ----------
    ("递归", "嗨，各位早上好，这里是 AI Builders Daily。我是递归。"),
    ("大师", "我是大师。今天三月二十号，昨天 AI 圈子有不少动静，我们来聊聊。"),
    ("递归", "嗯，先给大家预告一下，今天有几条挺重磅的。首先呢，Anthropic 搞了个大动作，让你直接在手机上操控 Claude Code。然后 Cursor 放了 Composer 2，还有一个我觉得特别值得聊的概念，就是以后你的工作产出啊，可能不再按小时算了，而是按 Token 算。"),
    ("大师", "最后这个我也很想展开聊一聊。好，我们进正题。"),

    # ---------- 第一段：Claude Code Channels ----------
    ("递归", "先说最大的这条。Anthropic 团队的 Thariq 昨天发了一条推，一天之内啊，一万七千多个赞。他说 Claude Code 现在支持 Channels 了，你可以通过 Telegram 啊，Discord 啊，直接在手机上给你电脑上跑着的 Claude Code 发消息。"),
    ("大师", "这个我得帮大家拆解一下。以前用 Claude Code 是什么体验呢？你必须坐在电脑前面，打开终端，一行一行地跟它交互。现在这个 Channels 功能呢，等于是给 Claude Code 开了一个手机入口。你想象一下，你在地铁上，掏出手机，在 Telegram 里打一句话说，帮我查一下昨天的销售数据，你电脑上的 Claude Code 就开始跑了。"),
    ("递归", "对，而且这不是一个阉割版啊。它背后跑的就是完整的 Claude Code，所有的能力都在。写代码、跑脚本、读文件，全都行。只是入口从终端变成了聊天窗口。"),
    ("大师", "Roblox 的产品经理 Peter Yang 说了句特别有意思的话，他说，我都是躺在床上用 Claude Code 了，这东西还叫 Code 是不是有点奇怪？不如叫 Clawd，C-L-A-W-D。"),
    ("递归", "哈哈哈，这名字不错。不过话说回来，这背后有一个很重要的趋势啊。我们来展开聊一下。"),
    ("大师", "嗯，说吧。"),
    ("递归", "你看啊，AI 工具的交互界面一直在变。最早是 API，你得写代码才能调用。然后是 Web 界面，像 ChatGPT 那样在浏览器里聊。再然后是 IDE 集成，像 Cursor 那样直接嵌在编辑器里。现在呢，是即时通讯。这个演进方向是什么？是越来越贴近人本来就在用的工具。"),
    ("大师", "对，这个观察很到位。技术领域有个概念叫做「零摩擦交互」。什么意思呢？就是说最好的工具不是让你去适应它，而是它来适应你。你本来就天天用 Telegram、用微信、用飞书对吧。那 AI 直接出现在这些地方，你连切换应用都不用。这就是零摩擦。"),
    ("递归", "而且你想啊，这不只是方便了一点点。它从根本上改变了你跟 AI 协作的模式。以前是你坐下来专门用 AI，现在是你随时随地、见缝插针地用 AI。这个使用频率和使用场景一下就打开了。"),
    ("大师", "目前官方支持 Telegram 和 Discord。飞书和微信还没有，但是社区已经有人在做桥接方案了。如果你也在做这方面的开发，这绝对是一个值得投入的方向。"),

    # ---------- 第二段：Cursor Composer 2 ----------
    ("递归", "好，第二条。Cursor 发布了 Composer 2。"),
    ("大师", "先给不太熟悉的朋友科普一下。Cursor 是一款 AI 代码编辑器，你可以理解为它就是 VS Code 加上一个超级聪明的结对编程伙伴。而 Composer 是它里面最核心的功能，你用自然语言描述你想做什么，它帮你把代码写出来，而且是跨文件的，不只是补全一行。"),
    ("递归", "Cursor 的设计负责人 Ryo Lu 昨天发了四个词来介绍 Composer 2：前沿智能、低成本、快速。简洁到不行。"),
    ("大师", "但更有说服力的是 Dan Shipper 的实测。他拿 Composer 2 和 GPT 5.4 做了一个对照实验，同一个任务，然后让 GPT 5.4 和 Claude Opus 4.6 来当裁判。"),
    ("递归", "等等，GPT 5.4 给自己当裁判？"),
    ("大师", "对，而且它判自己输了。这说明 Cursor 的工程优化确实做得不错。你想想看，底层模型可能是同一个或者差不多的，但是 Cursor 在 prompt 工程、上下文管理、工具链集成这些层面做了大量工作，最终效果就超过了直接用裸模型。"),
    ("递归", "这里有一个挺值得科普的概念，就是为什么同样的底层模型，套壳产品的效果可以差这么多。"),
    ("大师", "嗯，这是个好问题。你可以这样理解。大语言模型就像一个超级聪明的大脑，但是这个大脑需要合适的指令才能发挥最好的表现。这个指令怎么写、上下文怎么组织、工具怎么调用，这些统称为「编排层」。Cursor 做的事情就是在编排层上做到了极致。同样一个任务，GPT 5.4 裸用是一个效果，经过 Cursor 精心编排之后可能效果翻倍。这就好比同样一把好刀，厨师和新手切出来的菜完全不一样。"),
    ("递归", "所以对我们 Builder 来说，有两个启发。第一，工具选型很重要，Claude Code 和 Cursor 各有所长，Claude Code 擅长长上下文和复杂推理，Cursor 擅长快速编辑和设计集成，可以搭配使用。第二呢，如果你在做 AI 产品，编排层是你的核心壁垒，不是底层模型。"),

    # ---------- 第三段：Token 预算 ----------
    ("大师", "好，接下来这个话题我觉得可以多聊几分钟。Box 的 CEO Aaron Levie 昨天发了一段很长的分析。他核心的观点是，未来每个人的工作产出，本质上取决于他能调用多少 Token。"),
    ("递归", "这个需要解释一下。Token 是什么？用最简单的话说，Token 就是 AI 处理信息的基本单位。你可以把它想成 AI 的字数。你问 AI 一个问题，消耗一些 Token。AI 回答你，又消耗一些 Token。大概一个中文字就是一到两个 Token。"),
    ("大师", "Aaron Levie 的意思是这样的。以前我们衡量一个员工的产出，看的是什么？工作时长、任务完成量、产出质量。但现在有了 AI Agent 之后，一个人可以同时运行好几个 Agent。一个在帮你分析数据，一个在写报告，一个在审查代码，同时进行。那这个人的产出上限，就不再取决于他自己能工作多少小时，而是取决于他能调度多少 AI 算力。而 AI 算力的计量单位就是 Token。"),
    ("递归", "嗯，这个逻辑我再延伸一下。工业革命之前啊，产出等于人力乘以时间。工业革命之后呢，产出变成了机器数量乘以运转时间。现在 AI 时代，产出可能就变成了 Token 消耗量乘以编排效率。"),
    ("大师", "对，你注意到了关键词：编排效率。不是说谁消耗的 Token 多谁就厉害，而是谁能用同样多的 Token 做出更好的结果。这就是为什么学会用好 AI 工具这么重要。同样花一万个 Token，一个高手可能完成了三件事，一个新手可能一件都没做好。"),
    ("递归", "Aaron Levie 还有一句话我觉得特别有意思。他说，也许以后 CFO 才是真正的 AI 负责人。因为 Token 就是钱嘛，你每调用一次 AI 都在花钱。那给每个员工分配多少 Token 预算，这就变成了一个财务决策。"),
    ("大师", "这个判断挺大胆的，但逻辑上说得通。对我们个人来说呢，有一个很实际的行动建议：从现在开始关注你的 Token 使用效率。你可以做一个简单的记录，同一类任务，你用了多少 Token，产出了什么。然后想办法优化。比如用更精准的 prompt 来减少来回，或者用 skill 来标准化流程。这种意识以后会变成核心竞争力。"),

    # ---------- 第四段：设计师 + Agent ----------
    ("递归", "换个轻松点的话题。Swyx 昨天发了一条建议，他说，赶紧把你的 Coding Agent 给你的设计师用。一个月之后你就会发现，原来一直是你在拖后腿。"),
    ("大师", "哈，这话说得够直接的。"),
    ("递归", "但是仔细想想确实有道理。传统开发流程是什么？设计师画稿，开发来还原，然后设计师看了说，这不是我要的效果。来回改，沟通成本巨大。"),
    ("大师", "现在呢，设计师可以直接用 AI 把设计变成代码。不需要等开发排期，不需要来回沟通。她自己就能验证效果。这等于是跳过了整个协作的中间环节。"),
    ("递归", "而且这跟我们之前聊的 Frontend Design Skill 可以接上。那个 Skill 解决的核心问题就是：AI 生成的前端代码通常都长一个样，Inter 字体加紫色渐变。但有了那个 Skill 之后，AI 可以生成有设计感的代码。设计师加上这种工具，基本上一个人就是一个产品团队了。"),

    # ---------- 第五段：播客深度 ----------
    ("大师", "好，最后我们来聊一个播客推荐。昨天 Data Driven NYC 上线了一期很有深度的对话，Benedict Evans 和 Matt Turck 聊了将近一个小时。"),
    ("递归", "Benedict Evans 是谁呢？他是科技领域最有影响力的分析师之一，以前是 a16z 的合伙人。他写的年度科技趋势报告被全世界的投资人和创业者当做必读材料。"),
    ("大师", "这期播客有几个核心论点。第一个呢，就是 OpenAI 的护城河问题。Evans 的观点很犀利。他说 OpenAI 手里拿的本质上是一个商品化的技术。什么叫商品化？就是说别人也能做。Google 能做，Anthropic 能做，Meta 也能做。而 OpenAI 没有自己的基础设施，不像 Google 有自己的芯片和数据中心。OpenAI 有的是什么呢？品牌知名度。所以 Sam Altman 在做的事情就是试图把品牌影响力转化成硬资产。"),
    ("递归", "嗯，这个分析挺尖锐的。"),
    ("大师", "第二个论点更有意思。他提了一个概念叫即兴软件。什么意思呢？以前写一个软件成本很高，你需要程序员，需要时间，需要预算。所以很多需求就被忍了，没人去做。但现在 AI 让写代码变得非常便宜，那些以前不值得做的软件现在都可以做了。"),
    ("递归", "对，所以他的结论是：世界上会有更多的软件，不是更少。很多人说 AI 会取代程序员，让软件变少。Evans 不同意。他说 AI 会让软件的门槛降低，总量反而会暴增。"),
    ("大师", "还有一个判断我觉得特别值得记住。他说那种人人都会写自己的软件的说法是完全错的。大多数人不会自己做软件，就像大多数人有了 Word 也不会自己排版书一样。但是会有更多的专业开发者去做更多的垂直场景软件。"),
    ("递归", "这对我们 Builder 来说就是好消息了。市场在膨胀，机会在增多。关键是找到那些以前做不了、现在可以做的场景。"),

    # ---------- 收尾 ----------
    ("大师", "好了，今天的内容差不多了。我们来做一个总结。"),
    ("递归", "今天的 Builder 行动清单。第一，去试试 Claude Code Channels，用手机操控你的 Claude。这个是现在就能用的，Telegram 和 Discord 都支持。"),
    ("大师", "第二，关注 Cursor Composer 2。不一定要切换工具，但要了解竞争格局，知道什么工具擅长什么。"),
    ("递归", "第三，开始追踪你的 Token 使用效率。这是一个长期的事情，但越早开始越好。"),
    ("大师", "第四，如果身边有设计师朋友，把 AI 工具介绍给他们。设计加 Agent 是一个很有爆发力的组合。"),
    ("递归", "第五呢，有空去看看那个 Prompt to Chip 的可视化网站，从提示词到芯片，完整展示了 AI 的工作流程，挺涨知识的。"),
    ("大师", "好了，今天的 AI Builders Daily 就到这里。我是大师。"),
    ("递归", "我是递归。明天见，祝你 build something amazing。"),
]


def build_ssml(speaker: str, text: str) -> str:
    """构建 SSML，让语音更自然"""
    cfg = VOICES[speaker]

    # 在逗号和句号处加微停顿，模拟自然语流
    # 句末加轻微语调变化
    processed = text
    processed = processed.replace("。", '。<break time="280ms"/>')
    processed = processed.replace("？", '？<break time="300ms"/>')
    processed = processed.replace("！", '！<break time="250ms"/>')
    processed = processed.replace("，", '，<break time="120ms"/>')
    processed = processed.replace("、", '、<break time="80ms"/>')
    processed = processed.replace("……", '……<break time="350ms"/>')
    processed = processed.replace("——", '——<break time="200ms"/>')
    # 笑声加停顿
    processed = processed.replace("哈哈哈", '<break time="100ms"/>哈哈哈<break time="200ms"/>')
    processed = processed.replace("嗯", '<break time="80ms"/>嗯<break time="100ms"/>')

    ssml = f"""<speak xmlns='http://www.w3.org/2001/10/synthesis'
 xmlns:mstts='http://www.w3.org/2001/mstts'
 version='1.0' xml:lang='zh-CN'>
<voice name='{cfg["voice"]}'>
<mstts:express-as style='{cfg["style"]}' styledegree='{cfg["degree"]}'>
<prosody rate='{cfg["rate"]}' pitch='{cfg["pitch"]}'>
{processed}
</prosody>
</mstts:express-as>
</voice>
</speak>"""
    return ssml


async def generate_segment(index: int, speaker: str, text: str):
    """生成单个音频片段"""
    output_file = OUTPUT_DIR / f"seg_{index:03d}.mp3"
    ssml = build_ssml(speaker, text)
    communicate = edge_tts.Communicate(ssml, voice=VOICES[speaker]["voice"])
    await communicate.save(str(output_file))
    return str(output_file)


async def main():
    print(f"共 {len(SCRIPT)} 段对话，开始生成...")

    # 分批生成（避免并发太多被限流）
    BATCH = 8
    all_files = []
    for i in range(0, len(SCRIPT), BATCH):
        batch = SCRIPT[i:i+BATCH]
        tasks = [generate_segment(i+j, s, t) for j, (s, t) in enumerate(batch)]
        files = await asyncio.gather(*tasks)
        all_files.extend(files)
        print(f"  已完成 {min(i+BATCH, len(SCRIPT))}/{len(SCRIPT)}")

    print(f"已生成 {len(all_files)} 个音频片段")

    # 生成 ffmpeg 合并列表，段落间加静音间隔
    list_file = OUTPUT_DIR / "filelist.txt"
    silence_file = OUTPUT_DIR / "silence_300ms.mp3"

    # 生成 300ms 静音文件（段落间停顿）
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        "anullsrc=r=24000:cl=mono", "-t", "0.3",
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(silence_file)
    ], capture_output=True)

    with open(list_file, "w") as f:
        for i in range(len(SCRIPT)):
            seg_file = OUTPUT_DIR / f"seg_{i:03d}.mp3"
            f.write(f"file '{seg_file}'\n")
            # 每段之间加静音（模拟对话节奏）
            if i < len(SCRIPT) - 1:
                f.write(f"file '{silence_file}'\n")

    # 合并
    final_output = Path(__file__).parent / "ai-builders-daily-2026-03-20-v2.mp3"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(final_output)
    ]

    print("正在合并音频...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(final_output)],
            capture_output=True, text=True
        )
        duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        size_mb = os.path.getsize(final_output) / (1024 * 1024)

        print(f"\n{'='*50}")
        print(f"播客生成完成！")
        print(f"文件: {final_output}")
        print(f"时长: {minutes}分{seconds}秒")
        print(f"大小: {size_mb:.1f} MB")
        print(f"主持人: 递归 (YunxiNeural) + 大师 (YunyangNeural)")
        print(f"风格: chat 对话模式 + SSML 自然停顿")
        print(f"{'='*50}")
    else:
        print(f"合并失败: {result.stderr}")


if __name__ == "__main__":
    asyncio.run(main())
