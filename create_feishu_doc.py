#!/usr/bin/env python3
"""将新客次月复购分析报告发布为飞书文档 — 纯文本块版本"""

import requests, json, time

APP_ID = "cli_a937e91d7f38dbd8"
APP_SECRET = "r2Qm0OBs7cA7x9CpD29hwg1BMJpfx4Ze"
BASE = "https://open.feishu.cn/open-apis"

def get_token():
    r = requests.post(f"{BASE}/auth/v3/tenant_access_token/internal",
                      json={"app_id": APP_ID, "app_secret": APP_SECRET})
    return r.json()["tenant_access_token"]

def txt(content, bold=False):
    e = {"text_run": {"content": content}}
    if bold:
        e["text_run"]["text_element_style"] = {"bold": True}
    return e

def heading(level, text):
    key = f"heading{level}"
    return {"block_type": level + 2, key: {"elements": [txt(text)]}}

def para(*elems):
    return {"block_type": 2, "text": {"elements": list(elems)}}

def bullet(*elems):
    return {"block_type": 12, "bullet": {"elements": list(elems)}}

def ordered(*elems):
    return {"block_type": 13, "ordered": {"elements": list(elems)}}

def code_block(code_text):
    return {"block_type": 14, "code": {
        "elements": [txt(code_text)],
        "style": {"language": 1}  # PlainText
    }}

def add_blocks(doc_id, parent_id, children, headers):
    """分批添加，每次最多 50 个"""
    BATCH = 30
    ok = 0
    for i in range(0, len(children), BATCH):
        batch = children[i:i+BATCH]
        r = requests.post(
            f"{BASE}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children",
            headers=headers, json={"children": batch, "index": -1}
        )
        d = r.json()
        if d.get("code") == 0:
            ok += len(batch)
            print(f"  ✅ batch {i//BATCH+1}: {len(batch)} 块")
        else:
            print(f"  ⚠️ batch {i//BATCH+1} 失败: {d.get('msg','')[:120]}")
            # 逐个重试
            for child in batch:
                r2 = requests.post(
                    f"{BASE}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children",
                    headers=headers, json={"children": [child], "index": -1}
                )
                d2 = r2.json() if r2.text else {}
                if d2.get("code") == 0:
                    ok += 1
                else:
                    btype = child.get("block_type")
                    print(f"    ❌ type={btype} 失败: {d2.get('msg','empty response')[:80]}")
                time.sleep(0.2)
        time.sleep(0.3)
    print(f"  共写入 {ok} 块")

def table_text(headers_row, data_rows):
    """将表格数据转换为对齐的文本行（用 code block 展示）"""
    all_rows = [headers_row] + data_rows
    # 计算列宽
    widths = []
    for col in range(len(headers_row)):
        w = max(len(str(row[col])) for row in all_rows)
        widths.append(max(w, 4))

    lines = []
    for i, row in enumerate(all_rows):
        cells = []
        for j, cell in enumerate(row):
            cells.append(str(cell).ljust(widths[j]))
        lines.append("  ".join(cells))
        if i == 0:
            lines.append("  ".join("-" * w for w in widths))
    return "\n".join(lines)

# ── 构建内容 ──
def build():
    b = []

    b.append(para(txt("Lucky US · 2025.08 – 2026.02 · 7个月 × 5维度 × 13家门店")))
    b.append(para(
        txt("核心发现：", bold=True),
        txt("新店蜜月效应是复购率波动的最大解释变量——开业当月复购率29.2%，衰减至成熟期16.5%，差距12.7pp。37%新客不可触达，复购率仅为可触达用户的一半。")
    ))

    # ── 关键指标 ──
    b.append(heading(1, "一、关键指标"))
    b.append(code_block(table_text(
        ["指标", "数值", "说明"],
        [
            ["成熟门店复购率基线", "16.5%", "开业3-5月门店"],
            ["新店蜜月复购率", "29.2%", "开业当月，+12.7pp"],
            ["不可触达用户占比", "37.1%", "49,184名新客"],
            ["触达vs不可触达差距", "+12.5pp", "26.4% vs 13.9%"],
            ["午间首单复购率", "30.8%", "12pm，是23pm的2倍"],
            ["仅1单占未复购比例", "~65%", "最大流失池"],
        ]
    )))

    # ── 开店节奏 ──
    b.append(heading(1, "二、开店节奏"))
    b.append(code_block(table_text(
        ["开店月", "门店", "备注"],
        [
            ["2025-06", "8th & Broadway, 28th & 6th", "首批2店"],
            ["2025-08", "54th & 8th, 102 Fulton", "+2，月底密集"],
            ["2025-09", "100 Maiden Ln", "+1"],
            ["2025-11", "37th & Broadway", "+1"],
            ["2025-12", "JFK 24, 33rd&10th, 15th&3rd, 221 Grand", "爆发+4"],
            ["2026-02", "21st & 3rd, 52nd & Madison", "+2"],
            ["2026-03", "16th & 6th", "+1，刚开业"],
        ]
    )))

    # ── 月度总览 ──
    b.append(heading(1, "三、月度总览"))
    b.append(code_block(table_text(
        ["新客月", "次月", "新客总数", "已复购", "复购率", "新店占比", "新店复购", "老店复购"],
        [
            ["2025-08", "Sep", "21,525", "4,281", "19.9%", "14.1%", "39.9%", "16.6%"],
            ["2025-09", "Oct", "24,371", "6,750", "27.7%★", "47.6%", "31.0%", "24.7%"],
            ["2025-10", "Nov", "19,031", "4,064", "21.4%", "12.3%", "22.1%", "~21%"],
            ["2025-11", "Dec", "14,898", "2,775", "18.6%", "12.0%", "31.7%", "~16.6%"],
            ["2025-12", "Jan", "19,963", "4,233", "21.2%", "53.5%", "28.3%", "~13.1%"],
            ["2026-01", "Feb", "16,749", "3,353", "20.0%", "40.6%", "22.5%", "~18.4%"],
            ["2026-02", "Mar*", "15,936", "3,237", "20.3%", "15.5%", "35.2%", "~17.6%"],
        ]
    )))
    b.append(para(txt("* 2月次月观察期截至3/23，尚未跑满")))
    b.append(para(
        txt("解读：", bold=True),
        txt("整体复购率18.6%-27.7%看似波动大，但拆开新店/老店后发现：老店复购率稳定在16-18%，波动主要来自新店蜜月效应。9月高峰(27.7%)中近半新客来自蜜月期新店。")
    ))

    # ── 新店蜜月效应 ──
    b.append(heading(1, "四、新店蜜月效应（核心发现）"))
    b.append(para(txt("这是本次分析最重要的发现：每家新店都遵循同一条复购率衰减曲线。", bold=True)))

    b.append(heading(2, "4.1 门店年龄 → 复购率"))
    b.append(code_block(table_text(
        ["门店年龄", "新客人数", "已复购", "复购率", "vs成熟期"],
        [
            ["开业当月", "38,719", "11,302", "29.2%", "+12.7pp"],
            ["开业1月", "34,148", "6,335", "18.6%", "+2.1pp"],
            ["开业2月", "20,835", "4,637", "22.3%", "+5.8pp"],
            ["开业3-5月", "31,489", "5,205", "16.5%", "基线"],
            ["开业6月+", "7,282", "1,272", "17.5%", "+1.0pp"],
        ]
    )))
    b.append(para(txt("规律：开业当月29.2% → 开业1月18.6% → 3个月后稳定在16-17%。蜜月红利集中在前2个月。")))

    b.append(heading(2, "4.2 单店衰减曲线（以 102 Fulton 为例）"))
    b.append(code_block(table_text(
        ["月龄", "月份", "新客数", "复购率"],
        [
            ["Month 0", "2025-08", "1,328", "41.3%"],
            ["Month 0", "2025-09", "5,008", "31.6%"],
            ["Month 1", "2025-10", "4,038", "23.5%"],
            ["Month 2", "2025-11", "2,559", "18.2%"],
            ["Month 3", "2025-12", "1,951", "15.0%"],
            ["Month 4", "2026-01", "1,640", "14.9%"],
            ["Month 5", "2026-02", "1,323", "17.9%"],
        ]
    )))
    b.append(para(txt("54th & 8th、100 Maiden Ln、221 Grand 等门店均呈现相同衰减模式：~40% → ~28% → ~22% → ~17% → 稳定。")))

    b.append(heading(2, "4.3 异常门店：28th & 6th"))
    b.append(para(txt("28th & 6th 是唯一没有蜜月效应的门店：", bold=True)))
    b.append(code_block(table_text(
        ["月龄", "月份", "新客数", "复购率"],
        [
            ["Month 1", "2025-08", "8,884", "14.9%"],
            ["Month 2", "2025-09", "4,917", "17.2%"],
            ["Month 3", "2025-10", "4,010", "16.3%"],
            ["Month 4", "2025-11", "3,029", "14.0%"],
            ["Month 5", "2025-12", "2,072", "10.4%"],
            ["Month 6", "2026-01", "1,633", "13.6%"],
            ["Month 7", "2026-02", "1,374", "15.5%"],
        ]
    )))
    b.append(para(txt("对比：同批开业的 8th & Broadway 有正常蜜月（最高29.5%）。28th & 6th 从第1个月起就在14.9%，累计25,919名新客但复购仅15.0%——第二大门店，复购垫底。需专项排查。")))

    b.append(heading(2, "4.4 Sep 2025 高峰归因"))
    b.append(bullet(txt("47.6%", bold=True), txt(" 新客来自蜜月期新店（54th、102 Fulton、100 Maiden Ln），复购率31.0%")))
    b.append(bullet(txt("52.4%", bold=True), txt(" 新客来自2月龄老店（8th & Broadway、28th & 6th），复购率24.7%")))
    b.append(para(
        txt("注意：", bold=True),
        txt("8th & Broadway 在9月达29.5%（常态18%），说明除蜜月外，9月可能还有促销或开学季效应。")
    ))

    # ── 门店维度 ──
    b.append(heading(1, "五、门店维度（7个月汇总）"))
    b.append(code_block(table_text(
        ["门店", "新客数", "复购", "复购率", "备注"],
        [
            ["JFK 24", "214", "106", "49.5%", "样本小，12月新店"],
            ["52nd & Madison", "489", "236", "48.3%", "样本小，2月新店"],
            ["21st & 3rd", "1,977", "616", "31.2%", "2月新店"],
            ["15th & 3rd", "3,760", "1,083", "28.8%", "12月新店"],
            ["102 Fulton", "17,847", "4,317", "24.2%", "8月新店"],
            ["37th & Broadway", "9,515", "2,254", "23.7%", "11月新店"],
            ["33rd & 10th", "5,505", "1,304", "23.7%", "12月新店"],
            ["221 Grand", "9,305", "2,172", "23.3%", "12月新店"],
            ["100 Maiden Ln", "9,117", "2,091", "22.9%", "9月新店"],
            ["54th & 8th", "15,503", "3,493", "22.5%", "8月新店"],
            ["8th & Broadway", "33,322", "7,122", "21.4%", "6月创始店"],
            ["28th & 6th", "25,919", "3,899", "15.0%⚠️", "异常低"],
        ]
    )))

    # ── 品类维度 ──
    b.append(heading(1, "六、品类维度"))
    b.append(para(txt("按新客首单饮品的二级品类分组：")))
    b.append(code_block(table_text(
        ["品类", "新客数", "占比", "复购率"],
        [
            ["Super Drink", "2,544", "1.9%", "24.6% ★"],
            ["Exfreezo", "5,669", "4.3%", "24.4% ★"],
            ["Matcha", "16,108", "12.2%", "24.0% ★"],
            ["Fresh ground coffee", "69,410", "52.4%", "22.6%"],
            ["Cold Brew", "9,495", "7.2%", "21.4%"],
            ["Classic drinks", "24,939", "18.8%", "17.8%"],
            ["Refreshers", "4,308", "3.3%", "15.9%"],
        ]
    )))
    b.append(para(
        txt("洞察：", bold=True),
        txt("Matcha/Exfreezo/Super Drink 是粘性品类（24%+）。Refreshers(15.9%)和Classic(17.8%)首单用户流失风险高。首单品类是用户质量的早期预测信号。")
    ))

    # ── 时段维度 ──
    b.append(heading(1, "七、时段维度"))
    b.append(code_block(table_text(
        ["时段", "小时", "新客数", "复购率"],
        [
            ["上午", "11:00", "1,469", "29.3%"],
            ["午间", "12:00", "4,835", "30.8% ★"],
            ["午间", "13:00", "8,226", "29.4%"],
            ["午间", "14:00", "10,560", "26.5%"],
            ["下午", "15:00", "11,294", "21.9%"],
            ["下午", "16-17", "27,737", "23.0%"],
            ["傍晚", "18-19", "29,904", "20.5%"],
            ["晚间", "20-21", "22,745", "17.6%"],
            ["晚间", "22-23", "11,863", "16.8%"],
            ["凌晨", "0-1", "3,838", "14.4%"],
        ]
    )))
    b.append(para(
        txt("洞察：", bold=True),
        txt("午间12pm首单复购率30.8%，是深夜23pm(16.1%)的近2倍。白领午餐场景天然高频高粘性。")
    ))

    # ── 触达维度 ──
    b.append(heading(1, "八、触达维度（最重要的运营杠杆）"))
    b.append(para(txt("37%的新客不可触达，复购率仅为可触达用户的一半", bold=True)))

    b.append(heading(2, "8.1 整体"))
    b.append(code_block(table_text(
        ["触达状态", "新客数", "占比", "复购率"],
        [
            ["Push可触达", "59,958", "45.3%", "26.4%"],
            ["仅SMS可触达", "23,331", "17.6%", "25.9%"],
            ["不可触达", "49,184", "37.1%", "13.9% ⚠️"],
        ]
    )))

    b.append(heading(2, "8.2 月度趋势"))
    b.append(code_block(table_text(
        ["月份", "Push", "SMS", "不可触达", "差距"],
        [
            ["2025-08", "22.7%", "21.8%", "14.9%", "+7.8pp"],
            ["2025-09", "33.1%", "31.3%", "18.6%", "+14.5pp"],
            ["2025-10", "26.9%", "24.7%", "13.0%", "+13.9pp"],
            ["2025-11", "23.1%", "22.8%", "11.5%", "+11.6pp"],
            ["2025-12", "25.4%", "28.6%", "13.0%", "+12.4pp"],
            ["2026-01", "25.0%", "27.3%", "11.8%", "+13.2pp"],
            ["2026-02", "25.6%", "23.3%", "12.8%", "+12.8pp"],
        ]
    )))
    b.append(para(txt("差距每月稳定在+8~15pp，不随季节波动。触达能力是独立于其他因素的结构性杠杆。")))

    # ── 杯量分层 ──
    b.append(heading(1, "九、杯量分层"))
    b.append(code_block(table_text(
        ["月份", "仅1单复购", "2单复购", "3+单复购", "仅1单占未复购"],
        [
            ["2025-08", "14.4%", "20.5%", "39.5%", "62.8%"],
            ["2025-09", "16.1%", "25.6%", "59.5%", "63.2%"],
            ["2025-10", "13.0%", "21.0%", "50.6%", "64.7%"],
            ["2025-11", "12.9%", "18.1%", "43.3%", "65.9%"],
            ["2025-12", "12.2%", "20.8%", "49.4%", "64.3%"],
            ["2026-01", "12.1%", "20.3%", "47.2%", "67.0%"],
            ["2026-02", "13.5%", "21.1%", "48.4%", "69.5%"],
        ]
    )))
    b.append(para(txt("仅1单用户占未复购的63-70%，是最大流失池。用到第3张券以上的用户留存显著提升（43-59% vs 12-14%）。")))

    b.append(heading(2, "到手价对比"))
    b.append(para(txt("未复购用户到手均价系统性高于已复购用户：")))
    b.append(bullet(txt("仅1单：未复购 $2.82 vs 已复购 $2.25-2.31，差 $0.53")))
    b.append(bullet(txt("2单：未复购 $3.20-3.46 vs 已复购 $2.44-2.78，差 $0.60")))
    b.append(bullet(txt("3+单：未复购 $3.16-3.42 vs 已复购 $2.90-3.12，差 $0.30")))

    # ── 综合洞察 ──
    b.append(heading(1, "十、综合洞察"))

    b.append(heading(3, "1. 新店蜜月效应是复购率波动的主因"))
    b.append(para(txt('开业当月29.2% → 3个月后衰减至16.5%（-12.7pp）。排除蜜月效应后，成熟门店的真实复购率基线约16-17%。每次开新店都会拉高当月整体数据，但这是一次性红利。')))

    b.append(heading(3, "2. 28th & 6th 是结构性异常"))
    b.append(para(txt('唯一一家没有蜜月效应的门店——从第1个月(14.9%)就低，7个月一直在10-17%。同批开业的 8th & Broadway 有正常蜜月（最高29.5%）。需排查获客渠道、竞品、体验。')))

    b.append(heading(3, "3. 触达能力是成熟门店最大杠杆"))
    b.append(para(txt('37%新客不可触达（13.9%复购）vs 可触达（26.4%复购），差距12.5pp且每月稳定。在蜜月消退后，能否触达用户决定了能否守住复购率。')))

    b.append(heading(3, "4. 午间首单 = 高粘性用户信号"))
    b.append(para(txt('12pm首单30.8%复购率，是23pm(16.1%)的近2倍。午间场景天然高频高粘性，可作为用户质量早期标签。')))

    b.append(heading(3, "5. 券包深度使用仍是关键杠杆"))
    b.append(para(txt('仅1单用户（占未复购65%）复购率12-14%，3+单用户达43-59%（4倍差距）。到手价越高流失风险越大，价格敏感度信号明确。')))

    # ── 行动建议 ──
    b.append(heading(1, "十一、行动建议"))

    b.append(heading(2, "短期（1-2周）"))
    b.append(ordered(txt("Push授权弹窗：", bold=True), txt("首单支付成功页引导开启Push，目标不可触达从37%降至25%")))
    b.append(ordered(txt("28th & 6th 排查：", bold=True), txt("对比其他门店拆解触达率、渠道构成、品类结构")))
    b.append(ordered(txt("D3券提醒：", bold=True), txt("仅1单+可触达用户，首单后第3天Push券到期提醒")))

    b.append(heading(2, "中期（1-2月）"))
    b.append(ordered(txt("新店蜜月留存专项：", bold=True), txt("蜜月期(0-2月)重点投入Push授权+二次券激励，锁定触达渠道")))
    b.append(ordered(txt("午间高潜力标签：", bold=True), txt("午间首单用户配差异化复购链路（次日Push+3日SMS双触达）")))
    b.append(ordered(txt("晚间即时激励：", bold=True), txt("下单后弹窗展示券2，或调整券2为即时生效减少断点")))

    b.append(heading(2, "长期（1-3月）"))
    b.append(ordered(txt("门店生命周期看板：", bold=True), txt("分开追踪蜜月期/成熟期复购率，设目标（16.5%→20%）")))
    b.append(ordered(txt("选址预警：", bold=True), txt("28th & 6th 类型门店（无蜜月、持续低复购）预警机制")))
    b.append(ordered(txt("品类引导：", bold=True), txt("首单Refreshers/Classic新客，推送Matcha/Exfreezo试饮券")))

    # 脚注
    b.append(para(txt("—— 数据来源：CyberData DWD层 | 统计日期：2026-03-24 | 口径：首笔成功饮品门店订单")))

    return b

def main():
    print("1/3 获取飞书 Token...")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("  ✅ Token OK")

    print("2/3 创建飞书文档...")
    r = requests.post(f"{BASE}/docx/v1/documents", headers=headers,
                      json={"title": "新客次月复购分析 — Lucky US"})
    d = r.json()
    if d.get("code") != 0:
        print(f"  ❌ 失败: {d.get('msg','')[:200]}")
        return
    doc_id = d["data"]["document"]["document_id"]
    print(f"  ✅ doc_id: {doc_id}")

    print("3/3 写入内容...")
    blocks = build()
    print(f"  共 {len(blocks)} 个块")
    add_blocks(doc_id, doc_id, blocks, headers)

    url = f"https://lkusco.feishu.cn/docx/{doc_id}"
    print(f"\n🎉 完成！")
    print(f"📄 {url}")

if __name__ == "__main__":
    main()
