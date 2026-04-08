#!/usr/bin/env python3
"""Generate March ops monthly report PPTX decks."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


BASE_DIR = Path(__file__).resolve().parent
PRACTICAL_OUTPUT = BASE_DIR / "3月运营动作与实验月报_实用版.pptx"
DEEP_OUTPUT = BASE_DIR / "3月运营动作与实验月报_深度版.pptx"

SLIDE_W = Inches(26.67)
SLIDE_H = Inches(15)

COVER_BG = RGBColor(0x22, 0x27, 0x73)
TITLE = RGBColor(0x0F, 0x34, 0x60)
BODY = RGBColor(0x33, 0x33, 0x33)
SUB = RGBColor(0x66, 0x66, 0x66)
NOTE = RGBColor(0x99, 0x99, 0x99)
RED = RGBColor(0xD3, 0x2F, 0x2F)
GREEN = RGBColor(0x2E, 0x7D, 0x32)
BLUE = RGBColor(0x44, 0x72, 0xC4)
LIGHT_BG = RGBColor(0xED, 0xF2, 0xF9)
TABLE_STRIPE = RGBColor(0xF5, 0xF7, 0xFA)
BORDER = RGBColor(0xE0, 0xE0, 0xE0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "STKaiti"


def new_presentation():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def set_text_style(run, size, bold=False, color=BODY):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def add_textbox(slide, left, top, width, height, paragraphs, fill=None, line=None, radius=False):
    shape_type = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, left, top, width, height)
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)

    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, para in enumerate(paragraphs):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.alignment = para.get("align", PP_ALIGN.LEFT)
        p.space_after = Pt(0)
        p.space_before = Pt(0)
        run = p.add_run()
        run.text = para["text"]
        set_text_style(run, para.get("size", 20), para.get("bold", False), para.get("color", BODY))
    return shape


def add_cover(slide, title, subtitle, tag):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = COVER_BG
    add_textbox(
        slide,
        Inches(1.3),
        Inches(1.4),
        Inches(16.8),
        Inches(2.4),
        [{"text": title, "size": 32, "bold": True, "color": WHITE}],
    )
    add_textbox(
        slide,
        Inches(1.3),
        Inches(4.0),
        Inches(14.5),
        Inches(1.2),
        [{"text": subtitle, "size": 20, "color": WHITE}],
    )
    add_textbox(
        slide,
        Inches(1.3),
        Inches(12.7),
        Inches(8.0),
        Inches(0.7),
        [{"text": "Lucky US Growth · March Ops Monthly Review", "size": 16, "color": WHITE}],
    )
    add_textbox(
        slide,
        Inches(20.4),
        Inches(1.4),
        Inches(4.5),
        Inches(0.8),
        [{"text": tag, "size": 16, "bold": True, "color": COVER_BG, "align": PP_ALIGN.CENTER}],
        fill=WHITE,
        radius=True,
    )


def add_header(slide, title, subtitle=None):
    add_textbox(
        slide,
        Inches(0.9),
        Inches(0.45),
        Inches(18.0),
        Inches(0.8),
        [{"text": title, "size": 28, "bold": True, "color": TITLE}],
    )
    if subtitle:
        add_textbox(
            slide,
            Inches(0.9),
            Inches(1.15),
            Inches(18.0),
            Inches(0.5),
            [{"text": subtitle, "size": 14, "color": SUB}],
        )
    line = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0.9), Inches(1.7), Inches(24.7), Inches(0.03))
    line.fill.solid()
    line.fill.fore_color.rgb = TITLE
    line.line.fill.background()


def add_footer(slide, page_note="March 2026"):
    add_textbox(
        slide,
        Inches(0.9),
        Inches(14.15),
        Inches(10.0),
        Inches(0.35),
        [{"text": f"Lucky US Growth · {page_note}", "size": 12, "color": NOTE}],
    )


def add_metric_card(slide, left, top, width, height, label, value, note, value_color=TITLE):
    add_textbox(
        slide,
        left,
        top,
        width,
        height,
        [
            {"text": label, "size": 14, "bold": True, "color": SUB},
            {"text": value, "size": 28, "bold": True, "color": value_color},
            {"text": note, "size": 14, "color": BODY},
        ],
        fill=WHITE,
        line=BORDER,
        radius=True,
    )


def add_bullet_panel(slide, left, top, width, height, title, bullets, accent=TITLE):
    panel = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, width, height)
    panel.fill.solid()
    panel.fill.fore_color.rgb = WHITE
    panel.line.color.rgb = BORDER
    panel.line.width = Pt(1)
    tf = panel.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP

    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    set_text_style(r, 22, True, accent)
    p.space_after = Pt(6)

    for bullet in bullets:
        p = tf.add_paragraph()
        p.space_before = Pt(0)
        p.space_after = Pt(4)
        r = p.add_run()
        r.text = f"• {bullet}"
        set_text_style(r, 20, False, BODY)
    return panel


def add_table(slide, left, top, width, height, headers, rows, title=None, font_size=18):
    if title:
        add_textbox(
            slide,
            left,
            top - Inches(0.45),
            width,
            Inches(0.35),
            [{"text": title, "size": 20, "bold": True, "color": TITLE}],
        )
    table = slide.shapes.add_table(len(rows) + 1, len(headers), left, top, width, height).table
    table.first_row = True
    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.fill.solid()
        cell.fill.fore_color.rgb = COVER_BG
        cell.text = header
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.runs[0]
        set_text_style(run, 20, True, WHITE)
    for r_idx, row in enumerate(rows, start=1):
        for c_idx, value in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = TABLE_STRIPE if r_idx % 2 == 0 else WHITE
            cell.text = str(value)
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.CENTER
            run = p.runs[0]
            set_text_style(run, font_size, False, BODY)
            cell.margin_left = Inches(0.06)
            cell.margin_right = Inches(0.04)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
def practical_deck():
    prs = new_presentation()

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_cover(slide, "3月运营动作与实验月报", "老板汇报版 · 按当前已落数窗口 · 仅覆盖运营动作与实验", "实用版")

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "一、核心结论", "3月的价值，在于把有效方向和无效动作初步分清")
    add_textbox(
        slide,
        Inches(0.95),
        Inches(2.0),
        Inches(24.6),
        Inches(1.35),
        [{
            "text": "3月从“多做动作”切到“跑实验、收结论”。时间优化和资源位优化更有效；周末提频弹窗和低频任务当前版本未成立；上月新客召回在 MTD 留存口径上跑出持续正向改善。",
            "size": 22,
            "bold": True,
            "color": TITLE,
        }],
        fill=LIGHT_BG,
        radius=True,
    )
    add_metric_card(slide, Inches(1.0), Inches(4.0), Inches(5.7), Inches(2.0), "分享有礼", "5.20%", "拉新占比与2月持平，注册日均 +26%")
    add_metric_card(slide, Inches(7.1), Inches(4.0), Inches(5.7), Inches(2.0), "时段实验", "9点胜出", "周末 9 点优于 10 点；工作日 8 点略优于 9 点")
    add_metric_card(slide, Inches(13.2), Inches(4.0), Inches(5.7), Inches(2.0), "新客召回", "+2.92pp", "3/26-3/28 MTD 次月留存平均提升", value_color=RED)
    add_metric_card(slide, Inches(19.3), Inches(4.0), Inches(5.7), Inches(2.0), "弱策略", "2条", "周末提频支付返弹窗、一周3杯任务不建议放量", value_color=GREEN)
    add_bullet_panel(
        slide,
        Inches(1.0),
        Inches(6.6),
        Inches(11.8),
        Inches(6.6),
        "本月判断",
        [
            "低摩擦优化更容易跑出结果。时间、资源位优化均优于高门槛玩法。",
            "分享有礼仍是稳定拉新工具，不是裂变效率突破点。",
            "4月重心应是收敛有效策略，而不是继续铺新动作。",
        ],
    )
    add_bullet_panel(
        slide,
        Inches(13.2),
        Inches(6.6),
        Inches(11.8),
        Inches(6.6),
        "项目分层",
        [
            "继续：0326/0401时段实验、上月新客召回、分享有礼素材优化。",
            "观察：上月消费本月未消费新客 AB，优先保留实验组2。",
            "收口：周末提频支付返弹窗、低频任务一周3杯当前版本。",
        ],
    )
    add_footer(slide)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "二、本月动作总览", "按动作-观察窗口-结果-判断整理")
    add_table(
        slide,
        Inches(0.9),
        Inches(2.2),
        Inches(24.7),
        Inches(10.8),
        ["项目", "动作", "观察窗口", "关键结果", "判断"],
        [
            ["分享有礼", "4个资源位更新 + 弹层验证", "3/1-3/23；3/12-3/17", "注册日均 +26%，拉新占比 5.20%，弹层方向正向未显著", "继续优化素材和资源位"],
            ["0326时段实验", "工作日 8/9 点；周末 9/10 点", "3/26-3/29；周末 3/28-3/29", "工作日 8 点略优于 9 点，周末 9 点优于 10 点", "继续前探时段"],
            ["周末提频支付返弹窗", "支付后返周末券", "3/28-3/29", "相对分享有礼支付后弹窗更弱", "当前版本收口"],
            ["低频任务一周3杯", "任务链路提频", "3/25-3/29", "下单率、人均杯量均弱于对照组", "当前版本收口"],
            ["上月新客召回", "1.99/2.99+触达", "3/25-3/29", "MTD 次月留存平均 +2.92pp", "继续跑并补验证"],
            ["上月消费本月未消费新客 AB", "双实验组触达", "3/25-3/29", "方向略正但均未显著，实验组2更优", "保留实验组2观察"],
        ],
    )
    add_footer(slide)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "三、分享有礼", "3月做了两件事：资源位更新 + 弹层实验验证")
    add_bullet_panel(
        slide,
        Inches(1.0),
        Inches(2.1),
        Inches(11.9),
        Inches(10.9),
        "月内整体结果",
        [
            "3/1-3/23 注册被邀请人 1,406，日均 61.1，较 2 月日均 +26%。",
            "拉新占比 5.20%，与 2 月 5.23% 基本持平。",
            "D0 转化率 57.3%，较 2 月提升 +2.2pp。",
            "人均邀请 1.09，与 2 月 1.10 基本持平。",
            "弹窗 CTR 61.5%，成为 3 月最核心的曝光入口。",
        ],
    )
    add_bullet_panel(
        slide,
        Inches(13.1),
        Inches(2.1),
        Inches(11.9),
        Inches(10.9),
        "0312弹层实验",
        [
            "观察窗 3/12-3/17，实验组展示分享弹层，对照组不展示。",
            "分享率 1.62% vs 1.45%，提升 +11.9%。",
            "成功转化率 1.13% vs 0.96%，提升 +17.5%。",
            "但主指标 p=0.455，统计上不显著。",
            "结论：前链路方向正向，但不宜表述为已验证收益。",
        ],
        accent=BLUE,
    )
    add_footer(slide)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "四、提频实验", "时间优化有效，高门槛玩法暂未成立")
    add_bullet_panel(
        slide,
        Inches(1.0),
        Inches(2.0),
        Inches(7.8),
        Inches(11.1),
        "0326时段实验",
        [
            "工作日：8点组到访率 4.96%、下单率 2.19%，略优于 9 点组 4.81%/2.14%。",
            "周末：9点组下单率 0.96%，优于 10 点组 0.90%。",
            "说明触达时间优化值得继续，已在 4/1 前探到 7:00 / 7:30 / 8:00。",
        ],
    )
    add_bullet_panel(
        slide,
        Inches(9.3),
        Inches(2.0),
        Inches(7.8),
        Inches(11.1),
        "周末提频支付返弹窗",
        [
            "业务口径以分享有礼支付后弹窗为对照组。",
            "到访率 21.49% vs 25.30%，差值 -3.81pp（p=0.020）。",
            "下单率 13.52% vs 16.19%，差值 -2.67pp（p=0.052）。",
            "ITT 人均实收 -24.3%，当前版本不建议继续放量。",
        ],
        accent=RED,
    )
    add_bullet_panel(
        slide,
        Inches(17.6),
        Inches(2.0),
        Inches(7.4),
        Inches(11.1),
        "低频任务一周3杯",
        [
            "实验组下单率 17.09%，低于对照组 17.71%。",
            "人均杯量 0.2455，低于对照组 0.2721。",
            "领券率 1.42%，使用率 0.07%。",
            "问题在门槛过高、人群过冷、链路吸引力不够。",
        ],
        accent=GREEN,
    )
    add_footer(slide)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "五、新客召回与留存", "3月最值得继续打磨的正向方向")
    add_bullet_panel(
        slide,
        Inches(1.0),
        Inches(2.1),
        Inches(11.9),
        Inches(10.9),
        "上月新客召回",
        [
            "3/25 上线，目标人群为上月新客本月未复购人群。",
            "MTD 次月留存：3/26、3/27、3/28 分别较上月同期 +2.95pp、+2.92pp、+2.88pp。",
            "三天平均提升 +2.92pp，3/29 MTD 达 23.19%。",
            "当前是前后对比口径，适合表述为表现改善，不直接讲绝对因果增量。",
        ],
    )
    add_bullet_panel(
        slide,
        Inches(13.1),
        Inches(2.1),
        Inches(11.9),
        Inches(10.9),
        "上月消费本月未消费新客 AB",
        [
            "对照组：到访率 6.48%，下单率 3.00%，ITT 人均实收 $0.1326。",
            "实验组1：到访率 6.93%，下单率 3.15%，ITT 人均实收 $0.1133。",
            "实验组2：到访率 7.04%，下单率 3.16%，ITT 人均实收 $0.1361。",
            "两组均仅是方向略正，未形成显著证据；实验组2购买质量最好。",
        ],
        accent=BLUE,
    )
    add_footer(slide)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "六、4月动作建议", "4月重心：收敛有效策略，快速关停弱策略")
    add_bullet_panel(
        slide,
        Inches(1.0),
        Inches(2.1),
        Inches(7.8),
        Inches(10.9),
        "继续推进",
        [
            "继续跑 0326/0401时段实验，尽快收敛工作日和周末推荐时段。",
            "继续跑上月新客召回，并补更硬的验证层。",
            "分享有礼继续做素材与资源位优化，但不承担留存目标。",
        ],
    )
    add_bullet_panel(
        slide,
        Inches(9.3),
        Inches(2.1),
        Inches(7.8),
        Inches(10.9),
        "优先收口",
        [
            "周末提频支付返弹窗当前版本停止放量，先回退到更强的既有方案。",
            "低频任务一周3杯当前版本不继续放大，下一轮先降门槛或换人群。",
            "对方向弱且证据不足的动作，避免继续占用资源位和分析时间。",
        ],
        accent=RED,
    )
    add_bullet_panel(
        slide,
        Inches(17.6),
        Inches(2.1),
        Inches(7.4),
        Inches(10.9),
        "执行原则",
        [
            "少铺新动作，多做收敛。",
            "所有项目统一保留动作、配置、结果三层归档。",
            "对老板汇报只保留：动作、结果、判断、下月动作。",
        ],
        accent=GREEN,
    )
    add_footer(slide)

    return prs


def deep_deck():
    prs = practical_deck()

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "附录A、重点实验明细", "0326时段实验与周末提频支付返弹窗")
    add_table(
        slide,
        Inches(0.9),
        Inches(2.3),
        Inches(12.0),
        Inches(4.6),
        ["组别", "到访率", "下单率", "杯量", "实收"],
        [
            ["工作日空白组", "4.43%", "2.02%", "773", "$2,325.42"],
            ["工作日 8 点组", "4.96%", "2.19%", "1,691", "$5,072.79"],
            ["工作日 9 点组", "4.81%", "2.14%", "1,656", "$4,965.47"],
            ["周末空白组", "1.91%", "0.81%", "316", "$948.40"],
            ["周末 9 点组", "2.18%", "0.96%", "700", "$2,032.25"],
            ["周末 10 点组", "2.21%", "0.90%", "664", "$1,970.59"],
        ],
        title="0326时段实验",
    )
    add_table(
        slide,
        Inches(13.2),
        Inches(2.3),
        Inches(12.4),
        Inches(4.6),
        ["组别", "到访率", "下单率", "杯量", "实收", "ITT人均实收"],
        [
            ["分享有礼支付后弹窗", "25.30%", "16.19%", "339", "$1,261.06", "$0.9411"],
            ["周末提频支付返弹窗", "21.49%", "13.52%", "267", "$948.13", "$0.7123"],
        ],
        title="周末提频支付返弹窗（3/28-3/29）",
    )
    add_bullet_panel(
        slide,
        Inches(0.9),
        Inches(7.4),
        Inches(24.7),
        Inches(5.2),
        "附录判断",
        [
            "工作日 8 点与 9 点差距还不够大，但两者都优于空白组，方向上 8 点略优。",
            "周末 9 点已优于 10 点，适合在 4 月优先收敛到 9 点版本。",
            "周末提频支付返弹窗相对分享有礼支付后弹窗明显偏弱，现版本不宜继续放量。",
        ],
    )
    add_footer(slide, "March 2026 · Appendix A")

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "附录B、召回与任务明细", "低频任务、上月新客召回、上月消费本月未消费新客 AB")
    add_table(
        slide,
        Inches(0.9),
        Inches(2.3),
        Inches(11.7),
        Inches(4.0),
        ["项目", "实验组", "对照组", "差值"],
        [
            ["下单率", "17.09%", "17.71%", "-0.62pp"],
            ["人均订单数", "0.209", "0.224", "-0.015"],
            ["人均杯量", "0.2455", "0.2721", "-0.0266"],
            ["领券率", "1.42%", "-", "-"],
            ["使用率", "0.07%", "-", "-"],
        ],
        title="低频任务一周3杯（3/25-3/29）",
    )
    add_table(
        slide,
        Inches(13.1),
        Inches(2.3),
        Inches(12.4),
        Inches(4.0),
        ["日期", "上月同期", "本月 MTD", "提升"],
        [
            ["3/26", "19.26%", "22.21%", "+2.95pp"],
            ["3/27", "19.65%", "22.58%", "+2.92pp"],
            ["3/28", "20.02%", "22.89%", "+2.88pp"],
            ["3/29", "-", "23.19%", "-"],
        ],
        title="上月新客召回 · MTD 次月留存",
    )
    add_table(
        slide,
        Inches(0.9),
        Inches(7.0),
        Inches(24.6),
        Inches(4.2),
        ["组别", "人群数", "到访率", "下单率", "杯量", "实收", "ITT人均实收"],
        [
            ["对照组", "2,131", "6.48%", "3.00%", "92", "$282.54", "$0.1326"],
            ["实验组1", "4,316", "6.93%", "3.15%", "196", "$489.12", "$0.1133"],
            ["实验组2", "4,301", "7.04%", "3.16%", "200", "$585.52", "$0.1361"],
        ],
        title="上月消费本月未消费新客 AB（3/25-3/29）",
    )
    add_footer(slide, "March 2026 · Appendix B")

    return prs


def main():
    practical = practical_deck()
    practical.save(PRACTICAL_OUTPUT)
    deep = deep_deck()
    deep.save(DEEP_OUTPUT)
    print(f"saved practical: {PRACTICAL_OUTPUT}")
    print(f"saved deep: {DEEP_OUTPUT}")


if __name__ == "__main__":
    main()
