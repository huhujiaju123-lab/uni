#!/usr/bin/env python3
"""
PPT 老板审核模块 — 瑞幸美国国际业务高管视角
基于公司三份参考 PPT（香港周会/美国私域方案/CDP年报）的设计标准，
结合业务领域知识进行严格审核。

审核通过标准：总分 ≥ 85
"""

import json
from dataclasses import dataclass, field


# ============ 业务领域知识 ============

DOMAIN_KNOWLEDGE = {
    "metrics": {
        "杯量": "COUNT(*) from order_item WHERE Drink，非 COUNT(DISTINCT order_id)。多杯率是被低估的增长杠杆",
        "实收": "仅饮品实收（drink_pay_money），排除食品等非饮品",
        "单杯实收": "pay_amount / sku_num（item级），衡量价格管理效果",
        "转化率": "下单用户/进组用户（ITT口径），非仅活跃用户",
        "访购率": "order_users / visit_users，比转化率更能反映价格对购买决策的影响",
        "复购率": "周复购/月复购，需明确时间窗口（D3/D7/D14/D30）",
        "进组人均饮品实收(ITT)": "总饮品实收 ÷ 进组总用户，核心指标，避免下单用户拉齐",
        "LTV回收周期": "CAC ÷ LTV，<1月=强正向，1-3月=观望，>3月=谨慎",
        "毛利回收周期": "CAC ÷ (LTV × 毛利率)，经济可行性判断",
    },
    "analysis_standards": [
        "必须分层分析：按用户生命周期(0-15天活跃/16-30天衰退/30+天流失)分层，避免辛普森悖论",
        "核心指标用 ITT（Intent-to-Treat）：进组人均，非仅下单用户均值",
        "收入口径仅饮品：one_category_name = 'Drink'",
        "显著性检验：p<0.05 才能下结论",
        "报告用百分比/比例，避免暴露绝对用户数",
        "外卖(ch 8/9/10)是独立世界，不经APP漏斗，必须与 Pickup 分离分析",
        "经济分析必做：LTV回收周期 + 毛利回收周期",
        "多看访购率：比下单率更反映价格对决策的影响",
        "不建议把涨价券改回对照组价格",
        "新客券实验先检查 activity_no 是否被历史复用",
    ],
    "current_context": {
        "company": "Lucky US（瑞幸美国），咖啡连锁品牌",
        "stores": "~30家门店，主要在纽约/新泽西地区",
        "channels": "APP自取(Pickup) + 外卖(DoorDash/Grubhub/UberEats)",
        "user_segments": "新客/活跃(0-15天)/衰退(16-30天)/流失(30+天)",
        "key_experiments": {
            "0119新客弹层券": "已完成，全量推A组涨价券包。转化率无损(+0.26pp)，收入+4.5%，LTV+4.2%",
            "0212老客涨价": "持续追踪中。整体：单杯实收+8-10%，转化率-1pp，总收入略降。分层看：30+天流失用户实收+12-15%(正向)",
        },
        "key_activities": "分享有礼(Share The Luck, 拉新占比~5-7%)、Coffee Pass、提频任务",
        "辛普森悖论案例": "0212实验整体看负，分层后衰退/流失用户实收正向。活跃用户仅占11%人数但70%收入，杯量下降拖累整体",
    },
}


# ============ 审核维度定义 ============

DIMENSIONS = [
    {
        "name": "数据准确性",
        "weight": 0.20,
        "description": "数据是否完整、准确、口径一致",
        "checkpoints": [
            "核心数据是否完整呈现？关键数字是否齐全？",
            "数据口径是否一致？（如杯量≠订单数，实收仅饮品）",
            "百分比/比例计算是否正确？",
            "表格数据行数是否充足？（不少于5行）",
            "是否避免了绝对用户数暴露？",
        ],
    },
    {
        "name": "分析深度",
        "weight": 0.25,
        "description": "分析逻辑链是否完整，是否有洞察而非简单描述",
        "checkpoints": [
            "是否有分层分析？（避免辛普森悖论）",
            "结论是否有数据支撑？不是空话套话？",
            "每个发现是否有明确的 so what？",
            "是否有对比基准？（同比/环比/对照组）",
            "是否区分了相关性和因果性？",
            "建议是否可执行？有预期效果量化？",
        ],
    },
    {
        "name": "逻辑完整性",
        "weight": 0.20,
        "description": "页面间递进关系，从问题到方案的因果链",
        "checkpoints": [
            "页面顺序是否有递进？（背景→数据→发现→方案→预期）",
            "问题定义是否清晰？核心问题是什么？",
            "数据发现与建议之间是否有因果链？",
            "结论框是否直接回答核心问题？",
            "是否有遗漏的关键环节？（如成本分析、风险评估）",
        ],
    },
    {
        "name": "策略对齐",
        "weight": 0.15,
        "description": "方案是否符合公司战略方向和业务实际",
        "checkpoints": [
            "方案是否符合公司当前阶段重点？（增长/留存/变现）",
            "是否考虑了实施可行性？（产品/研发资源）",
            "是否考虑了与现有活动的协同/冲突？",
            "ROI 估算是否合理？假设是否明确？",
            "时间节奏是否切实可行？",
        ],
    },
    {
        "name": "视觉标准",
        "weight": 0.20,
        "description": "对标参考PPT，是否达到公司出品水准",
        "checkpoints": [
            "字体层次是否清晰？（标题/副标题/正文/脚注 至少4级）",
            "颜色使用是否克制统一？（不超过3种主色）",
            "Logo 是否正确？（左上鹿头 + 右下 luckin coffee）",
            "表格设计是否规范？（深蓝表头/斑马纹/对齐）",
            "结论框是否有质感？（不是简单白底灰边）",
            "元素间距是否均匀？有无重叠或大面积空白？",
            "页面利用率是否接近参考PPT水平？",
            "信息密度是否合理？一页说完一个完整模块？",
        ],
    },
]


# ============ 审核结果 ============

@dataclass
class DimensionScore:
    name: str
    score: int  # 1-10
    weight: float
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)

    @property
    def weighted(self):
        return self.score * self.weight * 10


@dataclass
class ReviewResult:
    dimensions: list  # List[DimensionScore]
    fatal_issues: list = field(default_factory=list)
    improvements: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def total_score(self):
        return sum(d.weighted for d in self.dimensions)

    @property
    def passed(self):
        return self.total_score >= 85

    def to_markdown(self):
        lines = ["## PPT 审核报告\n"]
        lines.append(f"### 总分：{self.total_score:.0f} / 100 {'✅ 通过' if self.passed else '❌ 未通过'}\n")
        lines.append("| 维度 | 得分 | 权重 | 加权分 |")
        lines.append("|------|------|------|--------|")
        for d in self.dimensions:
            lines.append(f"| {d.name} | {d.score}/10 | {d.weight:.0%} | {d.weighted:.1f} |")
        lines.append("")

        if self.fatal_issues:
            lines.append("### 致命问题（必须修）")
            for i, issue in enumerate(self.fatal_issues, 1):
                lines.append(f"{i}. {issue}")
            lines.append("")

        if self.improvements:
            lines.append("### 改进建议（建议修）")
            for i, imp in enumerate(self.improvements, 1):
                lines.append(f"{i}. {imp}")
            lines.append("")

        if self.notes:
            lines.append("### 审核备注")
            for note in self.notes:
                lines.append(f"- {note}")
            lines.append("")

        lines.append("### 合格标准")
        lines.append("- 总分 ≥ 85 分：可以提交")
        lines.append("- 总分 70-84：需修改后再审")
        lines.append("- 总分 < 70：推翻重做")

        return "\n".join(lines)


# ============ 审核执行 ============

def _gather_all_text(pages):
    """收集所有页面的文本内容"""
    texts = []
    for p in pages:
        texts.append(p.get("title", ""))
        texts.append(p.get("conclusion", ""))
        texts.extend(p.get("points", []))
        texts.extend(p.get("texts", []))
        for t in p.get("tables", []):
            for row in t.get("rows", []):
                texts.extend(row)
    return " ".join(texts)


def review_ppt(ppt_content, context=None):
    """
    审核 PPT 内容。基础分 6，好的加分、差的减分，满分 10。

    ppt_content: dict，结构化 PPT 内容描述
    context: dict，可选业务上下文

    Returns: ReviewResult
    """
    dimensions = []
    fatal = []
    improvements = []
    notes = []

    pages = ppt_content.get("pages", [])
    visuals = ppt_content.get("visual_checks", {})
    ctx = context or {}
    all_text = _gather_all_text(pages)

    # === 1. 数据准确性（基础6，上限10）===
    score_data = 6
    issues_data = []
    sugg_data = []

    total_tables = sum(len(p.get("tables", [])) for p in pages)
    total_rows = sum(len(t.get("rows", [])) for p in pages for t in p.get("tables", []))

    # 减分项
    if total_tables == 0:
        score_data -= 3
        fatal.append("缺少数据表格，报告缺乏数据支撑")
    for p in pages:
        for t in p.get("tables", []):
            if len(t.get("rows", [])) < 3:
                score_data -= 0.5
                issues_data.append(f"页面「{p.get('title','')}」表格行数不足（{len(t.get('rows', []))}行）")

    # 检查绝对用户数暴露（业务规范：用百分比，不暴露绝对数）
    import re as _re
    abs_numbers = _re.findall(r'\b\d{4,}\b', all_text)  # 4位以上数字
    if len(abs_numbers) > 10:
        issues_data.append(f"存在大量绝对数字（{len(abs_numbers)}处），建议对外报告用百分比/比例替代")

    # 加分项
    if total_tables >= len(pages):
        score_data += 1  # 每页至少一个表格
        notes.append("✓ 数据表格充足，每页都有数据支撑")
    if total_rows >= 20:
        score_data += 1  # 总行数丰富
        notes.append("✓ 表格数据行丰富，信息密度高")

    # 结论含数字
    conclusions_with_data = sum(1 for p in pages if p.get("conclusion") and any(c.isdigit() for c in p["conclusion"]))
    if conclusions_with_data >= len(pages) * 0.8:
        score_data += 1
        notes.append("✓ 绝大多数结论有具体数据支撑")
    elif conclusions_with_data < len(pages) * 0.5:
        score_data -= 1
        issues_data.append("部分页面结论缺少具体数字")

    # 脚注（数据来源说明）
    footnote_count = sum(1 for p in pages if p.get("has_footnote"))
    if footnote_count >= len(pages) * 0.5:
        score_data += 0.5
        notes.append("✓ 有数据来源脚注说明")

    # 严格模式：好的内容上限 9 分（10 分需要额外卓越表现）
    dimensions.append(DimensionScore("数据准确性", min(9, max(1, round(score_data))), 0.20,
                                     issues_data, sugg_data))

    # === 2. 分析深度（基础6，上限9）===
    score_depth = 6
    issues_depth = []
    sugg_depth = []

    total_points = sum(len(p.get("points", [])) for p in pages)

    # 加分：要点数量丰富
    if total_points >= len(pages) * 3:
        score_depth += 1
        notes.append("✓ 每页要点充分（≥3个）")
    elif total_points < len(pages) * 2:
        score_depth -= 1
        issues_depth.append("要点数量偏少，分析不够深入")

    # 加分：有对比/趋势分析
    comparison_keywords = ["对比", "同比", "环比", "vs", "提升", "下降", "→", "跳升",
                          "增长", "降低", "变化", "趋势"]
    comparison_count = sum(1 for p in pages for pt in p.get("points", [])
                          if any(kw in pt for kw in comparison_keywords))
    if comparison_count >= 3:
        score_depth += 1
        notes.append("✓ 多处使用对比/趋势分析")
    elif comparison_count == 0:
        score_depth -= 1
        issues_depth.append("缺少对比分析（同比/环比/基准）")

    # 加分：有可执行建议
    action_keywords = ["建议", "方案", "策略", "计划", "目标", "任务", "触发", "推送",
                      "发放", "配置", "上线"]
    has_action = any(any(kw in pt for kw in action_keywords)
                     for p in pages for pt in p.get("points", []))
    if has_action:
        score_depth += 1
        notes.append("✓ 包含可执行的行动建议")
    else:
        score_depth -= 1
        sugg_depth.append("建议增加可执行的行动建议，附预期效果量化")

    # 加分：分层/分群分析
    segment_keywords = ["分层", "分群", "阶段", "生命周期", "危险期", "稳定期", "活跃",
                       "流失", "衰退", "新客", "老客"]
    has_segment = any(kw in all_text for kw in segment_keywords)
    if has_segment:
        score_depth += 0.5
        notes.append("✓ 有用户分层/分群分析")

    # 减分：缺少成本分析
    cost_kw = ["成本", "毛利", "费用", "补贴", "投入", "花费", "CAC"]
    has_cost = any(kw in all_text for kw in cost_kw)
    if not has_cost:
        score_depth -= 0.5
        sugg_depth.append("建议补充活动成本/补贴分析，老板关心ROI不只是转化率")

    # 减分：缺少实验验证计划
    exp_kw = ["AB实验", "A/B", "实验验证", "对照组", "实验组", "灰度"]
    has_exp = any(kw in all_text for kw in exp_kw)
    if not has_exp:
        score_depth -= 0.5
        sugg_depth.append("建议增加AB实验验证计划，方案上线前需要数据驱动验证")

    dimensions.append(DimensionScore("分析深度", min(9, max(1, round(score_depth))), 0.25,
                                     issues_depth, sugg_depth))

    # === 3. 逻辑完整性（基础6，上限10）===
    score_logic = 6
    issues_logic = []
    sugg_logic = []

    # 页面数量
    if len(pages) >= 4:
        score_logic += 1
        notes.append("✓ 页面数量充足，信息容量大")
    elif len(pages) < 3:
        score_logic -= 2
        issues_logic.append("页面太少，难以构建完整逻辑链")

    # 逻辑链检查
    title_text = " ".join(p.get("title", "") for p in pages)
    has_bg = any(kw in title_text for kw in ["背景", "问题", "分层", "分布", "现状"])
    has_analysis = any(kw in title_text for kw in ["分析", "数据", "发现", "漏斗", "转化"])
    has_proposal = any(kw in title_text for kw in ["方案", "建议", "策略", "设计", "激励"])
    has_outcome = any(kw in title_text for kw in ["预期", "收益", "节奏", "计划", "总结"])

    chain = [has_bg, has_analysis, has_proposal, has_outcome]
    chain_count = sum(chain)
    if chain_count == 4:
        score_logic += 2
        notes.append("✓ 完整逻辑链：背景→分析→方案→预期")
    elif chain_count == 3:
        score_logic += 1
        missing = []
        if not has_bg: missing.append("背景/问题")
        if not has_analysis: missing.append("数据分析")
        if not has_proposal: missing.append("方案/建议")
        if not has_outcome: missing.append("预期/总结")
        sugg_logic.append(f"逻辑链缺少：{', '.join(missing)}")
    else:
        missing = []
        if not has_bg: missing.append("背景/问题")
        if not has_analysis: missing.append("数据分析")
        if not has_proposal: missing.append("方案/建议")
        if not has_outcome: missing.append("预期/总结")
        score_logic -= 1
        issues_logic.append(f"逻辑链缺失环节：{', '.join(missing)}")

    # 每页都有结论
    pages_with_conclusion = sum(1 for p in pages if p.get("conclusion"))
    if pages_with_conclusion == len(pages):
        score_logic += 1
        notes.append("✓ 每页都有明确结论")
    elif pages_with_conclusion < len(pages) * 0.5:
        score_logic -= 1
        issues_logic.append("多个页面缺少结论，读者难以快速抓住重点")

    dimensions.append(DimensionScore("逻辑完整性", min(9, max(1, round(score_logic))), 0.20,
                                     issues_logic, sugg_logic))

    # === 4. 策略对齐（基础6，上限10）===
    score_strat = 6
    issues_strat = []
    sugg_strat = []

    # 时间规划
    timeline_kw = ["节奏", "时间表", "W5", "W6", "W7", "Q1", "Q2", "阶段", "周", "计划"]
    has_timeline = any(kw.lower() in all_text.lower() for kw in timeline_kw)
    if has_timeline:
        score_strat += 1
        notes.append("✓ 包含实施时间节奏")
    else:
        sugg_strat.append("建议增加实施时间节奏规划")

    # ROI/效果预估
    roi_kw = ["ROI", "预期", "收益", "效果", "成本", "转化率", "提升"]
    has_roi = any(kw in all_text for kw in roi_kw)
    if has_roi:
        score_strat += 1
        notes.append("✓ 包含效果预估/ROI分析")
    else:
        score_strat -= 1
        sugg_strat.append("建议增加 ROI 预估或效果量化预测")

    # 优先级排序
    priority_kw = ["P0", "P1", "P2", "P3", "优先级", "优先", "最高", "关键"]
    has_priority = any(kw in all_text for kw in priority_kw)
    if has_priority:
        score_strat += 1
        notes.append("✓ 方案有优先级排序")

    # 风险/假设说明
    risk_kw = ["假设", "风险", "注意", "前提", "限制", "保守"]
    has_risk = any(kw in all_text for kw in risk_kw)
    if has_risk:
        score_strat += 0.5
    else:
        sugg_strat.append("建议补充关键假设和风险说明")

    # 与现有业务关联
    biz_kw = ["实验", "验证", "AB", "测试", "数据驱动"]
    has_biz = any(kw in all_text for kw in biz_kw)
    if has_biz:
        score_strat += 0.5

    dimensions.append(DimensionScore("策略对齐", min(9, max(1, round(score_strat))), 0.15,
                                     issues_strat, sugg_strat))

    # === 5. 视觉标准（基础6，上限10）===
    score_vis = 6
    issues_vis = []
    sugg_vis = []

    # 致命减分
    if not visuals.get("correct_logo", True):
        score_vis -= 4
        fatal.append("Logo 错误！必须使用正确的 luckin coffee 品牌 Logo")
    if not visuals.get("no_overlap", True):
        score_vis -= 3
        fatal.append("存在元素重叠/堆叠问题，文本框需要自适应高度")

    # 普通减分
    visual_checks = [
        ("consistent_fonts", 0.5, "字体不统一，应全部使用 STKaiti"),
        ("zebra_tables", 0.5, "表格缺少斑马纹设计"),
        ("conclusion_styled", 0.5, "结论框缺少质感"),
        ("section_accents", 0.5, "章节标题缺少装饰"),
    ]
    for key, penalty, msg in visual_checks:
        if not visuals.get(key, True):
            score_vis -= penalty
            issues_vis.append(msg)

    # 加分：所有视觉元素到位
    all_visual_ok = all(visuals.get(k, False) for k in
                        ["correct_logo", "no_overlap", "consistent_fonts",
                         "zebra_tables", "conclusion_styled", "section_accents"])
    if all_visual_ok:
        score_vis += 2
        notes.append("✓ 所有视觉元素符合设计规范")

    # 加分：页面利用率
    low_density = 0
    high_density = 0
    for p in pages:
        elements = (1 if p.get("conclusion") else 0) + len(p.get("tables", [])) + \
                   len(p.get("charts", [])) + len(p.get("texts", []))
        if elements < 2:
            low_density += 1
        elif elements >= 3:
            high_density += 1

    if low_density > 0:
        score_vis -= low_density * 0.5
        issues_vis.append(f"{low_density}个页面内容元素过少，版面利用率低")
    if high_density >= len(pages) * 0.5:
        score_vis += 1
        notes.append("✓ 页面信息密度高，版面利用率好")

    # 加分：有脚注
    if footnote_count >= len(pages) * 0.5:
        score_vis += 0.5

    dimensions.append(DimensionScore("视觉标准", min(9, max(1, round(score_vis))), 0.20,
                                     issues_vis, sugg_vis))

    # === 生成综合改进建议 ===
    # 将各维度的建议汇总
    for d in dimensions:
        improvements.extend(d.suggestions)

    return ReviewResult(dimensions, fatal, improvements, notes)


def review_and_print(ppt_content, context=None):
    """审核并打印报告"""
    result = review_ppt(ppt_content, context)
    report = result.to_markdown()
    print(report)
    return result
