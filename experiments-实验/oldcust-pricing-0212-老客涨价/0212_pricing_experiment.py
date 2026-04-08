"""
0212 涨价实验效果分析
======================
3组对比: 涨价组1(30%), 涨价组2(30%), 对照组3(40%)
时间范围: 2026-02-12 ~ 2026-02-20
口径: 剔除新客（实验前无订单）

使用方式:
1. 把下面 6 个 SQL 在 CyberData 上分别跑出结果
2. 把结果填入对应的 data dict
3. 运行脚本生成分析报告
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ============================================================
# 配置
# ============================================================
EXP_START = '2026-02-12'
EXP_END = '2026-02-24'       # 含当天
EXP_END_NEXT = '2026-02-25'  # 查询用 < 此日期
DT_LATEST = '2026-02-24'     # user_label / group_his 取最新分区
REPURCHASE_3D_CUTOFF = '2026-02-21'  # 3日复购需要 +3 天窗口
REPURCHASE_7D_CUTOFF = '2026-02-17'  # 7日复购需要 +7 天窗口

GROUP_NAMES = [
    '0212价格实验30%分流涨价组1',
    '0212价格实验30%分流涨价组2',
    '0212价格实验40%分流对照组3',
]

# ============================================================
# 公共 CTE（剔除新客 = 实验前有订单的老客）
# 所有 SQL 共用此段，复制时带上
# ============================================================
COMMON_CTE = f"""
WITH grp_users AS (
    SELECT DISTINCT g.user_no,
        CASE
            WHEN g.group_name LIKE '%涨价组1%' THEN '涨价组1'
            WHEN g.group_name LIKE '%涨价组2%' THEN '涨价组2'
            WHEN g.group_name LIKE '%对照组3%' THEN '对照组3'
        END AS grp
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN (
        SELECT DISTINCT user_no
        FROM ods_luckyus_sales_order.v_order
        WHERE status = 90 AND INSTR(tenant, 'IQ') = 0
            AND create_time < '{EXP_START}'
            AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    ) hist ON g.user_no = hist.user_no
    WHERE g.tenant = 'LKUS' AND g.dt = '{DT_LATEST}'
        AND (g.group_name LIKE '%0212价格实验%涨价组1%'
          OR g.group_name LIKE '%0212价格实验%涨价组2%'
          OR g.group_name LIKE '%0212价格实验%对照组3%')
)"""

# ============================================================
# SQL 1: 各组老客用户数
# ============================================================
SQL_1_GROUP_SIZES = COMMON_CTE + """
SELECT grp, COUNT(*) AS total_users
FROM grp_users
GROUP BY grp
ORDER BY grp
"""

# ============================================================
# SQL 2: 每日订单指标（下单用户、订单数、实收）
# ============================================================
SQL_2_DAILY_ORDERS = COMMON_CTE + f"""
SELECT
    gu.grp,
    DATE(o.create_time) AS dt,
    COUNT(DISTINCT o.user_no) AS order_users,
    COUNT(DISTINCT o.id) AS order_cnt,
    ROUND(SUM(o.pay_money), 2) AS revenue
FROM grp_users gu
INNER JOIN ods_luckyus_sales_order.v_order o
    ON gu.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY gu.grp, DATE(o.create_time)
ORDER BY dt, grp
"""

# ============================================================
# SQL 3: 每日访问人数
# ============================================================
SQL_3_DAILY_VISITS = COMMON_CTE + f"""
SELECT
    gu.grp,
    dau.dt,
    COUNT(DISTINCT dau.user_no) AS visit_users
FROM grp_users gu
INNER JOIN dw_dws.dws_mg_log_user_screen_name_d_1d dau
    ON gu.user_no = dau.user_no
    AND dau.dt >= '{EXP_START}' AND dau.dt <= '{EXP_END}'
GROUP BY gu.grp, dau.dt
ORDER BY dau.dt, gu.grp
"""

# ============================================================
# SQL 4: 每日杯量与单杯实收（t_order_item 较慢，单独跑）
# 优化：先取订单 ID 再 JOIN item 表
# ============================================================
SQL_4_DAILY_CUPS = COMMON_CTE + f""",
exp_orders AS (
    SELECT o.id AS order_id, gu.grp, DATE(o.create_time) AS dt
    FROM grp_users gu
    INNER JOIN ods_luckyus_sales_order.v_order o
        ON gu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
    eo.grp,
    eo.dt,
    SUM(item.sku_num) AS cups,
    ROUND(SUM(item.pay_money), 2) AS item_revenue,
    ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS unit_price
FROM exp_orders eo
INNER JOIN ods_luckyus_sales_order.t_order_item item
    ON eo.order_id = item.order_id
GROUP BY eo.grp, eo.dt
ORDER BY eo.dt, eo.grp
"""

# ============================================================
# SQL 5: 汇总期间独立指标（unique 下单用户、访问用户）
# 注意：汇总的下单用户 ≠ 每日下单用户之和（同一用户多天下单只算一次）
# ============================================================
SQL_5_PERIOD_SUMMARY = COMMON_CTE + f"""
SELECT
    gu.grp,
    COUNT(DISTINCT o.user_no) AS period_order_users,
    COUNT(DISTINCT o.id) AS period_order_cnt,
    ROUND(SUM(o.pay_money), 2) AS period_revenue
FROM grp_users gu
LEFT JOIN ods_luckyus_sales_order.v_order o
    ON gu.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY gu.grp
ORDER BY gu.grp
"""

# ============================================================
# SQL 6: 3日复购率（每日 + 汇总）
# ============================================================
SQL_6_REPURCHASE_3D = COMMON_CTE + f""",
user_daily AS (
    SELECT DISTINCT gu.grp, gu.user_no, DATE(o.create_time) AS order_date
    FROM grp_users gu
    INNER JOIN ods_luckyus_sales_order.v_order o
        ON gu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
    a.grp,
    a.order_date,
    COUNT(DISTINCT a.user_no) AS day_buyers,
    COUNT(DISTINCT b.user_no) AS repurchase_users,
    ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_3d
FROM user_daily a
LEFT JOIN user_daily b
    ON a.user_no = b.user_no
    AND a.grp = b.grp
    AND b.order_date > a.order_date
    AND DATEDIFF(b.order_date, a.order_date) <= 3
WHERE a.order_date <= '{REPURCHASE_3D_CUTOFF}'
GROUP BY a.grp, a.order_date
ORDER BY a.order_date, a.grp
"""

# ============================================================
# SQL 7: 7日复购率（每日 + 汇总）
# ============================================================
SQL_7_REPURCHASE_7D = COMMON_CTE + f""",
user_daily AS (
    SELECT DISTINCT gu.grp, gu.user_no, DATE(o.create_time) AS order_date
    FROM grp_users gu
    INNER JOIN ods_luckyus_sales_order.v_order o
        ON gu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
    a.grp,
    a.order_date,
    COUNT(DISTINCT a.user_no) AS day_buyers,
    COUNT(DISTINCT b.user_no) AS repurchase_users,
    ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_7d
FROM user_daily a
LEFT JOIN user_daily b
    ON a.user_no = b.user_no
    AND a.grp = b.grp
    AND b.order_date > a.order_date
    AND DATEDIFF(b.order_date, a.order_date) <= 7
WHERE a.order_date <= '{REPURCHASE_7D_CUTOFF}'
GROUP BY a.grp, a.order_date
ORDER BY a.order_date, a.grp
"""


# ============================================================
# 打印所有 SQL（方便复制到 CyberData）
# ============================================================
def print_all_sql():
    queries = [
        ("SQL 1: 各组老客用户数", SQL_1_GROUP_SIZES),
        ("SQL 2: 每日订单指标", SQL_2_DAILY_ORDERS),
        ("SQL 3: 每日访问人数", SQL_3_DAILY_VISITS),
        ("SQL 4: 每日杯量与单杯实收", SQL_4_DAILY_CUPS),
        ("SQL 5: 汇总期间独立指标", SQL_5_PERIOD_SUMMARY),
        ("SQL 6: 3日复购率", SQL_6_REPURCHASE_3D),
        ("SQL 7: 7日复购率", SQL_7_REPURCHASE_7D),
    ]
    for title, sql in queries:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
        print(sql)
        print()


# ============================================================
# 数据输入区（跑完 SQL 后填入结果）
# ============================================================

# SQL 1 结果: 各组用户数
group_sizes = {
    # '涨价组1': 0,
    # '涨价组2': 0,
    # '对照组3': 0,
}

# SQL 2 结果: 每日订单
# daily_orders = pd.DataFrame(columns=['grp', 'dt', 'order_users', 'order_cnt', 'revenue'])

# SQL 3 结果: 每日访问
# daily_visits = pd.DataFrame(columns=['grp', 'dt', 'visit_users'])

# SQL 4 结果: 每日杯量
# daily_cups = pd.DataFrame(columns=['grp', 'dt', 'cups', 'item_revenue', 'unit_price'])

# SQL 5 结果: 汇总
# period_summary = pd.DataFrame(columns=['grp', 'period_order_users', 'period_order_cnt', 'period_revenue'])

# SQL 6 结果: 3日复购
# daily_repurchase = pd.DataFrame(columns=['grp', 'order_date', 'day_buyers', 'repurchase_users', 'repurchase_rate_3d'])


# ============================================================
# 分析与报告生成
# ============================================================
def build_daily_table(group_sizes, daily_orders, daily_visits, daily_cups, daily_repurchase_3d, daily_repurchase_7d):
    """合并每日数据为宽表"""
    # 收集所有出现过的日期
    all_dates = set()
    for df, col in [(daily_orders, 'dt'), (daily_visits, 'dt'), (daily_cups, 'dt')]:
        all_dates.update(df[col].unique())
    all_dates = sorted(all_dates)
    groups = ['涨价组1', '涨价组2', '对照组3']

    rows = []
    for dt_str in all_dates:
        dt_display = dt_str[5:].replace('-', '/')
        row = {'日期': dt_display}
        for grp in groups:
            total = group_sizes.get(grp, 0)

            # 订单
            mask_o = (daily_orders['grp'] == grp) & (daily_orders['dt'] == dt_str)
            o = daily_orders[mask_o].iloc[0] if mask_o.any() else None
            order_users = int(o['order_users']) if o is not None else 0
            revenue = float(o['revenue']) if o is not None else 0

            # 访问
            mask_v = (daily_visits['grp'] == grp) & (daily_visits['dt'] == dt_str)
            v = daily_visits[mask_v].iloc[0] if mask_v.any() else None
            visit_users = int(v['visit_users']) if v is not None else 0

            # 杯量
            mask_c = (daily_cups['grp'] == grp) & (daily_cups['dt'] == dt_str)
            c = daily_cups[mask_c].iloc[0] if mask_c.any() else None
            cups = int(c['cups']) if c is not None else 0
            unit_price = float(c['unit_price']) if c is not None else 0

            # 3日复购
            mask_r3 = (daily_repurchase_3d['grp'] == grp) & (daily_repurchase_3d['order_date'] == dt_str)
            r3 = daily_repurchase_3d[mask_r3].iloc[0] if mask_r3.any() else None
            repurchase_rate_3d = float(r3['repurchase_rate_3d']) if r3 is not None else None

            # 7日复购
            mask_r7 = (daily_repurchase_7d['grp'] == grp) & (daily_repurchase_7d['order_date'] == dt_str)
            r7 = daily_repurchase_7d[mask_r7].iloc[0] if mask_r7.any() else None
            repurchase_rate_7d = float(r7['repurchase_rate_7d']) if r7 is not None else None

            prefix = grp
            row[f'{prefix}_实验人数'] = total
            row[f'{prefix}_访问人数'] = visit_users
            row[f'{prefix}_访问率'] = f"{visit_users/total*100:.2f}%" if total else '-'
            row[f'{prefix}_下单用户'] = order_users
            row[f'{prefix}_杯量'] = cups
            row[f'{prefix}_实收'] = revenue
            row[f'{prefix}_单杯实收'] = unit_price
            row[f'{prefix}_3日复购率'] = f"{repurchase_rate_3d:.2f}%" if repurchase_rate_3d is not None else '-'
            row[f'{prefix}_7日复购率'] = f"{repurchase_rate_7d:.2f}%" if repurchase_rate_7d is not None else '-'
            row[f'{prefix}_转化率'] = f"{order_users/total*100:.2f}%" if total else '-'

        rows.append(row)

    return pd.DataFrame(rows)


def build_summary_row(group_sizes, period_summary, daily_visits, daily_cups, daily_repurchase_3d, daily_repurchase_7d):
    """构建汇总行"""
    groups = ['涨价组1', '涨价组2', '对照组3']
    row = {'日期': '汇总'}

    for grp in groups:
        total = group_sizes.get(grp, 0)

        # 汇总订单（用 SQL 5 的 unique 数据）
        mask_s = period_summary['grp'] == grp
        s = period_summary[mask_s].iloc[0] if mask_s.any() else None
        period_order_users = int(s['period_order_users']) if s is not None else 0
        period_revenue = float(s['period_revenue']) if s is not None else 0

        # 汇总访问
        mask_v = daily_visits['grp'] == grp
        total_visit = daily_visits[mask_v]['visit_users'].sum() if mask_v.any() else 0

        # 汇总杯量
        mask_c = daily_cups['grp'] == grp
        total_cups = int(daily_cups[mask_c]['cups'].sum()) if mask_c.any() else 0
        total_item_rev = float(daily_cups[mask_c]['item_revenue'].sum()) if mask_c.any() else 0

        # 汇总3日复购：取均值
        mask_r3 = daily_repurchase_3d['grp'] == grp
        avg_repurchase_3d = daily_repurchase_3d[mask_r3]['repurchase_rate_3d'].mean() if mask_r3.any() else 0

        # 汇总7日复购：取均值
        mask_r7 = daily_repurchase_7d['grp'] == grp
        avg_repurchase_7d = daily_repurchase_7d[mask_r7]['repurchase_rate_7d'].mean() if mask_r7.any() else 0

        prefix = grp
        row[f'{prefix}_实验人数'] = total
        row[f'{prefix}_访问人数'] = f"{total_visit}*"
        row[f'{prefix}_访问率'] = '-'
        row[f'{prefix}_下单用户'] = period_order_users
        row[f'{prefix}_杯量'] = total_cups
        row[f'{prefix}_实收'] = period_revenue
        row[f'{prefix}_单杯实收'] = round(total_item_rev / total_cups, 2) if total_cups else 0
        row[f'{prefix}_3日复购率'] = f"{avg_repurchase_3d:.2f}%"
        row[f'{prefix}_7日复购率'] = f"{avg_repurchase_7d:.2f}%"
        row[f'{prefix}_转化率'] = f"{period_order_users/total*100:.2f}%" if total else '-'

    return row


def build_normalized_comparison(summary_row, group_sizes):
    """拉齐后对比分析 - 以对照组3为基准"""
    control_size = group_sizes.get('对照组3', 1)
    groups_to_normalize = ['涨价组1', '涨价组2']

    results = []

    for grp in groups_to_normalize:
        grp_size = group_sizes.get(grp, 1)
        ratio = control_size / grp_size

        row = {'日期': f'{grp}拉齐'}
        control_prefix = '对照组3'

        # 拉齐后的绝对值
        for metric in ['下单用户', '杯量', '实收']:
            grp_val = summary_row.get(f'{grp}_{metric}', 0)
            ctrl_val = summary_row.get(f'{control_prefix}_{metric}', 0)
            if isinstance(grp_val, str):
                grp_val = float(grp_val.replace('*', '').replace('%', ''))
            if isinstance(ctrl_val, str):
                ctrl_val = float(ctrl_val.replace('*', '').replace('%', ''))

            normalized = grp_val * ratio
            diff_pct = (normalized - ctrl_val) / ctrl_val * 100 if ctrl_val else 0
            row[f'{metric}_拉齐值'] = round(normalized, 1)
            row[f'{metric}_对照组值'] = ctrl_val
            row[f'{metric}_差异'] = f"{diff_pct:+.2f}%"

        # 比率指标直接对比（无需拉齐）
        for metric in ['单杯实收']:
            grp_val = summary_row.get(f'{grp}_{metric}', 0)
            ctrl_val = summary_row.get(f'{control_prefix}_{metric}', 0)
            if isinstance(grp_val, str):
                grp_val = float(grp_val)
            if isinstance(ctrl_val, str):
                ctrl_val = float(ctrl_val)
            diff_pct = (grp_val - ctrl_val) / ctrl_val * 100 if ctrl_val else 0
            row[f'{metric}_实验组'] = grp_val
            row[f'{metric}_对照组'] = ctrl_val
            row[f'{metric}_差异'] = f"{diff_pct:+.2f}%"

        for metric in ['转化率', '3日复购率', '7日复购率']:
            grp_val = summary_row.get(f'{grp}_{metric}', '0%')
            ctrl_val = summary_row.get(f'{control_prefix}_{metric}', '0%')
            grp_num = float(str(grp_val).replace('%', ''))
            ctrl_num = float(str(ctrl_val).replace('%', ''))
            diff = grp_num - ctrl_num
            row[f'{metric}_实验组'] = grp_val
            row[f'{metric}_对照组'] = ctrl_val
            row[f'{metric}_差异'] = f"{diff:+.2f}pp"

        results.append(row)

    return results


def generate_markdown_report(daily_df, summary_row, normalized, group_sizes):
    """生成 Markdown 报告"""
    groups = ['涨价组1', '涨价组2', '对照组3']
    metrics = ['实验人数', '访问人数', '访问率', '下单用户', '杯量', '实收', '单杯实收', '3日复购率', '7日复购率', '转化率']

    lines = []
    lines.append("# 0212 涨价实验分析结果（剔除新客）\n")
    lines.append(f"实验时间: {EXP_START} ~ {EXP_END}\n")
    lines.append("## 各组用户数\n")
    lines.append("| 组别 | 老客用户数 |")
    lines.append("|------|-----------|")
    for grp in groups:
        lines.append(f"| {grp} | {group_sizes.get(grp, 0):,} |")
    lines.append("")

    # 每日明细表 - 每组一个表
    for grp in groups:
        lines.append(f"\n## {grp} 每日数据\n")
        cols = [f'{grp}_{m}' for m in metrics]
        header = "| 日期 | " + " | ".join(metrics) + " |"
        sep = "|------|" + "|".join(["------"] * len(metrics)) + "|"
        lines.append(header)
        lines.append(sep)

        for _, row in daily_df.iterrows():
            vals = [str(row.get(c, '-')) for c in cols]
            lines.append(f"| {row['日期']} | " + " | ".join(vals) + " |")

        # 汇总行
        vals = [str(summary_row.get(c, '-')) for c in cols]
        lines.append(f"| **汇总** | " + " | ".join(vals) + " |")

    # 拉齐对比
    lines.append("\n## 拉齐后对比分析（以对照组3为基准）\n")
    for norm in normalized:
        lines.append(f"\n### {norm['日期']}\n")
        lines.append("| 指标 | 拉齐值/实验组 | 对照组值 | 差异 |")
        lines.append("|------|-------------|---------|------|")

        for metric in ['下单用户', '杯量', '实收']:
            lines.append(f"| {metric} | {norm.get(f'{metric}_拉齐值', '-')} | {norm.get(f'{metric}_对照组值', '-')} | {norm.get(f'{metric}_差异', '-')} |")
        for metric in ['单杯实收', '转化率', '3日复购率', '7日复购率']:
            lines.append(f"| {metric} | {norm.get(f'{metric}_实验组', '-')} | {norm.get(f'{metric}_对照组', '-')} | {norm.get(f'{metric}_差异', '-')} |")

    return "\n".join(lines)


def generate_html_report(daily_df, summary_row, normalized, group_sizes):
    """生成 HTML 报告（可 Cmd+P 导出 PDF）"""
    groups = ['涨价组1', '涨价组2', '对照组3']
    metrics = ['实验人数', '访问人数', '访问率', '下单用户', '杯量', '实收', '单杯实收', '3日复购率', '7日复购率', '转化率']
    group_colors = {'涨价组1': '#FFF3E0', '涨价组2': '#E3F2FD', '对照组3': '#E8F5E9'}

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>0212 涨价实验分析</title>
<style>
body {{ font-family: -apple-system, sans-serif; margin: 20px; font-size: 13px; }}
h1 {{ color: #333; font-size: 18px; }}
h2 {{ color: #555; font-size: 15px; margin-top: 24px; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: right; white-space: nowrap; }}
th {{ background: #f5f5f5; font-weight: 600; text-align: center; }}
td:first-child {{ text-align: center; font-weight: 500; }}
tr.summary {{ background: #FFF9C4; font-weight: 600; }}
.positive {{ color: #D32F2F; }}
.negative {{ color: #388E3C; }}
.section-header {{ background: #333; color: white; text-align: center !important; }}
</style></head><body>
<h1>0212 涨价实验分析结果（剔除新客）</h1>
<p>实验时间: {EXP_START} ~ {EXP_END}</p>

<h2>各组老客用户数</h2>
<table style="width:auto">
<tr><th>组别</th><th>老客用户数</th></tr>
"""
    for grp in groups:
        html += f"<tr><td>{grp}</td><td>{group_sizes.get(grp, 0):,}</td></tr>\n"
    html += "</table>\n"

    # 合并大表（类似图2的格式）
    html += "<h2>每日数据对比</h2>\n<table>\n"

    # 表头 - 两行
    html += "<tr><th rowspan='2'>日期</th>"
    for grp in groups:
        color = group_colors.get(grp, '#f5f5f5')
        html += f"<th colspan='{len(metrics)}' style='background:{color}'>{grp}</th>"
    html += "</tr>\n<tr>"
    for grp in groups:
        for m in metrics:
            html += f"<th>{m}</th>"
    html += "</tr>\n"

    # 数据行
    for _, row in daily_df.iterrows():
        html += f"<tr><td>{row['日期']}</td>"
        for grp in groups:
            for m in metrics:
                val = row.get(f'{grp}_{m}', '-')
                html += f"<td>{val}</td>"
        html += "</tr>\n"

    # 汇总行
    html += "<tr class='summary'><td>汇总</td>"
    for grp in groups:
        for m in metrics:
            val = summary_row.get(f'{grp}_{m}', '-')
            html += f"<td>{val}</td>"
    html += "</tr>\n</table>\n"

    # 拉齐对比
    html += "<h2>拉齐后对比分析（以对照组3为基准）</h2>\n"
    for norm in normalized:
        html += f"<h3>{norm['日期']}</h3>\n<table style='width:auto'>\n"
        html += "<tr><th>指标</th><th>拉齐值/实验组</th><th>对照组值</th><th>差异</th></tr>\n"

        for metric in ['下单用户', '杯量', '实收']:
            diff = norm.get(f'{metric}_差异', '-')
            css = 'positive' if '+' in str(diff) else 'negative' if '-' in str(diff) else ''
            html += f"<tr><td style='text-align:left'>{metric}</td>"
            html += f"<td>{norm.get(f'{metric}_拉齐值', '-')}</td>"
            html += f"<td>{norm.get(f'{metric}_对照组值', '-')}</td>"
            html += f"<td class='{css}'>{diff}</td></tr>\n"

        for metric in ['单杯实收', '转化率', '3日复购率', '7日复购率']:
            diff = norm.get(f'{metric}_差异', '-')
            css = 'positive' if '+' in str(diff) else 'negative' if '-' in str(diff) else ''
            html += f"<tr><td style='text-align:left'>{metric}</td>"
            html += f"<td>{norm.get(f'{metric}_实验组', '-')}</td>"
            html += f"<td>{norm.get(f'{metric}_对照组', '-')}</td>"
            html += f"<td class='{css}'>{diff}</td></tr>\n"

        html += "</table>\n"

    html += "</body></html>"
    return html


# ============================================================
# 主流程：读取 CSV 并生成报告
# ============================================================
CSV_DIR = '/Users/xiaoxiao/Downloads'

def run_report():
    # 读取 7 个 CSV
    df_sizes = pd.read_csv(f'{CSV_DIR}/各组老客用户数（剔除新客）.csv')
    daily_orders = pd.read_csv(f'{CSV_DIR}/每日订单指标.csv')
    daily_visits = pd.read_csv(f'{CSV_DIR}/每日访问人数.csv')
    daily_cups = pd.read_csv(f'{CSV_DIR}/每日杯量与单杯实收.csv')
    period_summary = pd.read_csv(f'{CSV_DIR}/汇总期间独立指标.csv')
    daily_repurchase_3d = pd.read_csv(f'{CSV_DIR}/3日复购率.csv')
    daily_repurchase_7d = pd.read_csv(f'{CSV_DIR}/7日复购率.csv')

    # 类型转换
    daily_orders['dt'] = daily_orders['dt'].astype(str)
    daily_visits['dt'] = daily_visits['dt'].astype(str)
    daily_cups['dt'] = daily_cups['dt'].astype(str)
    daily_repurchase_3d['order_date'] = daily_repurchase_3d['order_date'].astype(str)
    daily_repurchase_7d['order_date'] = daily_repurchase_7d['order_date'].astype(str)
    daily_visits['visit_users'] = daily_visits['visit_users'].astype(int)
    daily_cups['cups'] = daily_cups['cups'].astype(int)
    daily_repurchase_3d['repurchase_rate_3d'] = daily_repurchase_3d['repurchase_rate_3d'].astype(float)
    daily_repurchase_7d['repurchase_rate_7d'] = daily_repurchase_7d['repurchase_rate_7d'].astype(float)

    # 构建 group_sizes dict
    size_col = 'old_users' if 'old_users' in df_sizes.columns else 'total_users'
    group_sizes = dict(zip(df_sizes['grp'], df_sizes[size_col].astype(int)))
    print("各组老客用户数:")
    for grp, cnt in group_sizes.items():
        print(f"  {grp}: {cnt:,}")

    # 构建每日宽表
    daily_df = build_daily_table(group_sizes, daily_orders, daily_visits, daily_cups, daily_repurchase_3d, daily_repurchase_7d)

    # 构建汇总行
    summary_row = build_summary_row(group_sizes, period_summary, daily_visits, daily_cups, daily_repurchase_3d, daily_repurchase_7d)

    # 拉齐对比
    normalized = build_normalized_comparison(summary_row, group_sizes)

    # 生成报告
    md = generate_markdown_report(daily_df, summary_row, normalized, group_sizes)
    html = generate_html_report(daily_df, summary_row, normalized, group_sizes)

    output_dir = '/Users/xiaoxiao/Vibe coding'
    md_path = f'{output_dir}/0212涨价实验分析报告.md'
    html_path = f'{output_dir}/0212涨价实验分析报告.html'

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n报告已生成:")
    print(f"  Markdown: {md_path}")
    print(f"  HTML: {html_path}")
    return daily_df, summary_row, normalized


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'sql':
        print_all_sql()
    else:
        run_report()
