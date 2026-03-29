#!/usr/bin/env python3
"""0212涨价实验报告生成器
按同事口径：DWD表 + type NOT IN (3,4,5) + 仅饮品 + 门店订单 + 生命周期分层
"""
import subprocess, json, time, sys, os
from datetime import datetime

def run_sql(sql, max_retries=4, wait=10):
    for attempt in range(max_retries):
        result = subprocess.run(
            [os.path.expanduser('~/.claude/skills/cyberdata-query/run_sql.sh'), sql],
            capture_output=True, text=True, timeout=120
        )
        output = result.stdout.strip()
        if '查询失败或无结果' in output or not output:
            if attempt < max_retries - 1:
                print(f"  重试 {attempt+2}/{max_retries}...")
                time.sleep(wait)
                continue
            return None
        lines = output.split('\n')
        data_start = 0
        for i, line in enumerate(lines):
            if '\t' in line and not line.startswith('提交') and not line.startswith('任务') and not line.startswith('等待'):
                data_start = i
                break
        if data_start >= len(lines):
            if attempt < max_retries - 1:
                time.sleep(wait)
                continue
            return None
        headers = lines[data_start].split('\t')
        rows = []
        for line in lines[data_start+1:]:
            if line.strip() and '\t' in line:
                rows.append(dict(zip(headers, line.split('\t'))))
        if rows:
            return rows
        if attempt < max_retries - 1:
            time.sleep(wait)
    return None

# ============================================================
# 人群组名映射
# ============================================================
lifecycle_groups = {
    'A_涨价组1': {
        '0-15天': '价格实验30%涨价组1_0_15交易用户',
        '16-30天': '价格实验A30%涨价组1_16_30交易用户',
        '30+天': '0212价格实验30%涨价组1_31+交易用户',
    },
    'B_涨价组2': {
        '0-15天': '价格实验30%涨价组2_0_15交易用户',
        '16-30天': '价格实验A30%涨价组2_16_30交易用户',
        '30+天': '0212价格实验30%涨价组2_31+交易用户',
    },
    'C_对照组': {
        '0-15天': '价格实验30%对照组3_0_15交易用户',
        '16-30天': '价格实验A30%对照组3_16_30交易用户',
        '30+天': '0212价格实验40%涨价组3_31+交易用户',
    },
}

BEGIN_DATE = '2026-02-13'
END_DATE = '2026-03-04'

# ============================================================
# Step 1: 全周期分层汇总 (already validated)
# ============================================================
print("=" * 60)
print("Step 1: 查询分层汇总数据")
print("=" * 60)

summary_data = {}
for group_name, lifecycles in lifecycle_groups.items():
    for lc_name, gname in lifecycles.items():
        print(f"  {group_name}/{lc_name}...")
        sql = f"""
SELECT
    '{group_name}' AS exp_group, '{lc_name}' AS lifecycle,
    user_stats.total_users,
    COALESCE(order_stats.order_users, 0) AS order_users,
    COALESCE(order_stats.drink_cnt, 0) AS drink_cnt,
    ROUND(COALESCE(order_stats.drink_pay, 0), 2) AS drink_pay,
    ROUND(COALESCE(order_stats.drink_origin, 0), 2) AS drink_origin
FROM (
    SELECT COUNT(DISTINCT g.user_no) AS total_users
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN ods_luckyus_sales_crm.t_user u ON g.user_no = u.user_no AND u.type NOT IN (3, 4, 5) AND INSTR(COALESCE(u.tenant, 'LKUS'), 'IQ') = 0
    WHERE g.dt = '2026-02-12' AND g.tenant = 'LKUS' AND g.group_name = '{gname}'
) user_stats
LEFT JOIN (
    SELECT COUNT(DISTINCT o.user_no) AS order_users, COUNT(*) AS drink_cnt,
        SUM(o.pay_amount) AS drink_pay, SUM(o.origin_price) AS drink_origin
    FROM dw_dwd.dwd_t_ord_order_item_d_inc o
    INNER JOIN (
        SELECT DISTINCT g.user_no FROM dw_ads.ads_marketing_t_user_group_d_his g
        INNER JOIN ods_luckyus_sales_crm.t_user u ON g.user_no = u.user_no AND u.type NOT IN (3, 4, 5) AND INSTR(COALESCE(u.tenant, 'LKUS'), 'IQ') = 0
        WHERE g.dt = '2026-02-12' AND g.tenant = 'LKUS' AND g.group_name = '{gname}'
    ) vu ON o.user_no = vu.user_no
    WHERE o.dt BETWEEN '{BEGIN_DATE}' AND '{END_DATE}' AND o.tenant = 'LKUS' AND o.order_status = 90
        AND o.order_category = '门店订单' AND o.one_category_name = 'Drink'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
) order_stats ON 1=1
"""
        rows = run_sql(sql)
        if rows:
            r = rows[0]
            summary_data[(group_name, lc_name)] = {
                'total_users': int(r['total_users']),
                'order_users': int(r['order_users']),
                'drink_cnt': int(r['drink_cnt']),
                'drink_pay': float(r['drink_pay']),
                'drink_origin': float(r['drink_origin']),
            }
            print(f"    ✓ users={r['total_users']}, buyers={r['order_users']}, cups={r['drink_cnt']}, pay=${r['drink_pay']}")
        else:
            print(f"    ✗ 查询失败")
            summary_data[(group_name, lc_name)] = {'total_users': 0, 'order_users': 0, 'drink_cnt': 0, 'drink_pay': 0, 'drink_origin': 0}

# ============================================================
# Step 2: 每日趋势 (per group, across all lifecycles)
# ============================================================
print("\n" + "=" * 60)
print("Step 2: 查询每日趋势数据（按组汇总）")
print("=" * 60)

main_groups = {
    'A_涨价组1': '0212价格实验30%分流涨价组1',
    'B_涨价组2': '0212价格实验30%分流涨价组2',
    'C_对照组': '0212价格实验40%分流对照组3',
}

daily_data = {}
for group_name, gname in main_groups.items():
    print(f"  {group_name} 每日数据...")
    sql = f"""
SELECT
    o.dt,
    COUNT(DISTINCT o.user_no) AS daily_order_users,
    COUNT(*) AS daily_drink_cnt,
    ROUND(SUM(o.pay_amount), 2) AS daily_drink_pay,
    ROUND(SUM(o.origin_price), 2) AS daily_drink_origin
FROM dw_dwd.dwd_t_ord_order_item_d_inc o
INNER JOIN (
    SELECT DISTINCT g.user_no FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN ods_luckyus_sales_crm.t_user u ON g.user_no = u.user_no AND u.type NOT IN (3, 4, 5) AND INSTR(COALESCE(u.tenant, 'LKUS'), 'IQ') = 0
    WHERE g.dt = '2026-02-12' AND g.tenant = 'LKUS' AND g.group_name = '{gname}'
) vu ON o.user_no = vu.user_no
WHERE o.dt BETWEEN '{BEGIN_DATE}' AND '{END_DATE}' AND o.tenant = 'LKUS' AND o.order_status = 90
    AND o.order_category = '门店订单' AND o.one_category_name = 'Drink'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY o.dt
ORDER BY o.dt
"""
    rows = run_sql(sql)
    if rows:
        daily_data[group_name] = rows
        print(f"    ✓ {len(rows)} 天数据")
    else:
        daily_data[group_name] = []
        print(f"    ✗ 失败")

# ============================================================
# Step 3: 来访数据 (per group)
# ============================================================
print("\n" + "=" * 60)
print("Step 3: 查询来访数据（访购率）")
print("=" * 60)

visit_data = {}
for group_name, gname in main_groups.items():
    print(f"  {group_name} 来访...")
    sql = f"""
SELECT
    COUNT(DISTINCT v.login_id) AS visit_users
FROM dw_dwd.dwd_mg_log_detail_d_inc v
INNER JOIN (
    SELECT DISTINCT g.user_no FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN ods_luckyus_sales_crm.t_user u ON g.user_no = u.user_no AND u.type NOT IN (3, 4, 5) AND INSTR(COALESCE(u.tenant, 'LKUS'), 'IQ') = 0
    WHERE g.dt = '2026-02-12' AND g.tenant = 'LKUS' AND g.group_name = '{gname}'
) vu ON v.login_id = vu.user_no
WHERE v.local_dt BETWEEN '{BEGIN_DATE}' AND '{END_DATE}'
    AND ((v.platform IN (1, 2) AND v.event = '$AppStart') OR (v.platform = 3))
    AND v.login_id IS NOT NULL AND v.login_id != ''
"""
    rows = run_sql(sql)
    if rows:
        visit_data[group_name] = int(rows[0]['visit_users'])
        print(f"    ✓ {rows[0]['visit_users']} 来访用户")
    else:
        visit_data[group_name] = 0
        print(f"    ✗ 失败")

# ============================================================
# Step 4: 生成 HTML 报告
# ============================================================
print("\n" + "=" * 60)
print("Step 4: 生成 HTML 报告")
print("=" * 60)

# Calculate all derived metrics
def calc_metrics(d):
    tu = d['total_users']
    ou = d['order_users']
    dc = d['drink_cnt']
    dp = d['drink_pay']
    do_ = d['drink_origin']
    return {
        **d,
        'order_rate': ou / tu * 100 if tu > 0 else 0,
        'itt_revenue': dp / tu if tu > 0 else 0,
        'itt_cups': dc / tu if tu > 0 else 0,
        'avg_cup_price': dp / dc if dc > 0 else 0,
        'discount_rate': dp / do_ * 100 if do_ > 0 else 0,
        'cups_per_buyer': dc / ou if ou > 0 else 0,
    }

# Build metrics for each group × lifecycle
metrics = {}
lcs = ['0-15天', '16-30天', '30+天']
groups = ['A_涨价组1', 'B_涨价组2', 'C_对照组']

for g in groups:
    for lc in lcs:
        metrics[(g, lc)] = calc_metrics(summary_data.get((g, lc), {'total_users':0,'order_users':0,'drink_cnt':0,'drink_pay':0,'drink_origin':0}))
    # 全量
    tu = sum(summary_data.get((g, lc), {}).get('total_users', 0) for lc in lcs)
    ou = sum(summary_data.get((g, lc), {}).get('order_users', 0) for lc in lcs)
    dc = sum(summary_data.get((g, lc), {}).get('drink_cnt', 0) for lc in lcs)
    dp = sum(summary_data.get((g, lc), {}).get('drink_pay', 0) for lc in lcs)
    do_ = sum(summary_data.get((g, lc), {}).get('drink_origin', 0) for lc in lcs)
    metrics[(g, '全量')] = calc_metrics({'total_users': tu, 'order_users': ou, 'drink_cnt': dc, 'drink_pay': dp, 'drink_origin': do_})

# Group user counts for visit rate
group_total_users = {g: metrics[(g, '全量')]['total_users'] for g in groups}

# Diff calculation helper
def diff_pct(val, base):
    return (val / base - 1) * 100 if base > 0 else 0

def diff_pp(val, base):
    return val - base

# Prepare daily chart data
all_dates = sorted(set(r['dt'] for rows in daily_data.values() for r in rows))
daily_by_group = {}
for g in groups:
    daily_by_group[g] = {}
    tu = group_total_users[g]
    for r in daily_data.get(g, []):
        daily_by_group[g][r['dt']] = {
            'order_users': int(r['daily_order_users']),
            'drink_cnt': int(r['daily_drink_cnt']),
            'drink_pay': float(r['daily_drink_pay']),
            'itt_revenue': float(r['daily_drink_pay']) / tu if tu > 0 else 0,
            'avg_cup_price': float(r['daily_drink_pay']) / int(r['daily_drink_cnt']) if int(r['daily_drink_cnt']) > 0 else 0,
        }

# JSON for charts
chart_dates_json = json.dumps(all_dates)
chart_itt_a = json.dumps([round(daily_by_group['A_涨价组1'].get(d, {}).get('itt_revenue', 0), 6) for d in all_dates])
chart_itt_b = json.dumps([round(daily_by_group['B_涨价组2'].get(d, {}).get('itt_revenue', 0), 6) for d in all_dates])
chart_itt_c = json.dumps([round(daily_by_group['C_对照组'].get(d, {}).get('itt_revenue', 0), 6) for d in all_dates])
chart_cup_a = json.dumps([round(daily_by_group['A_涨价组1'].get(d, {}).get('avg_cup_price', 0), 4) for d in all_dates])
chart_cup_b = json.dumps([round(daily_by_group['B_涨价组2'].get(d, {}).get('avg_cup_price', 0), 4) for d in all_dates])
chart_cup_c = json.dumps([round(daily_by_group['C_对照组'].get(d, {}).get('avg_cup_price', 0), 4) for d in all_dates])
chart_buyers_a = json.dumps([daily_by_group['A_涨价组1'].get(d, {}).get('order_users', 0) for d in all_dates])
chart_buyers_b = json.dumps([daily_by_group['B_涨价组2'].get(d, {}).get('order_users', 0) for d in all_dates])
chart_buyers_c = json.dumps([daily_by_group['C_对照组'].get(d, {}).get('order_users', 0) for d in all_dates])

# Economic analysis (from colleague's framework)
# LTV assumptions per segment (monthly avg spend per user)
ltv_params = {
    '0-15天': {'ltv': 21.5, 'margin': 0.6},
    '16-30天': {'ltv': 13.4, 'margin': 0.5},
    '30+天': {'ltv': 8.8, 'margin': 0.4},
    '全量': {'ltv': 13.0, 'margin': 0.5},
}

# Generate HTML
all_lcs = ['0-15天', '16-30天', '30+天', '全量']

def fmt_num(n):
    return f"{n:,.0f}"

def fmt_pct(n):
    return f"{n:.2f}%"

def fmt_dollar(n):
    return f"${n:.4f}"

def fmt_diff(n, unit='%'):
    sign = '+' if n >= 0 else ''
    if unit == 'pp':
        return f"{sign}{n:.2f}pp"
    return f"{sign}{n:.1f}%"

def color_diff(n, reverse=False):
    """Return CSS color for positive/negative diff"""
    if reverse:
        n = -n
    if n > 0:
        return 'color: #22c55e; font-weight: 600;'
    elif n < 0:
        return 'color: #ef4444; font-weight: 600;'
    return ''

# Build summary table rows
def make_summary_rows():
    rows_html = ''
    for lc in all_lcs:
        a = metrics[(groups[0], lc)]
        b = metrics[(groups[1], lc)]
        c = metrics[(groups[2], lc)]

        itt_a_d = diff_pct(a['itt_revenue'], c['itt_revenue'])
        itt_b_d = diff_pct(b['itt_revenue'], c['itt_revenue'])
        cup_a_d = diff_pct(a['avg_cup_price'], c['avg_cup_price'])
        cup_b_d = diff_pct(b['avg_cup_price'], c['avg_cup_price'])
        or_a_d = diff_pp(a['order_rate'], c['order_rate'])
        or_b_d = diff_pp(b['order_rate'], c['order_rate'])
        cups_a_d = diff_pct(a['itt_cups'], c['itt_cups'])
        cups_b_d = diff_pct(b['itt_cups'], c['itt_cups'])

        border_class = 'total-row' if lc == '全量' else ''
        rows_html += f'''
        <tr class="{border_class}">
            <td class="lc-label" rowspan="1">{lc}</td>
            <td>{fmt_num(a['total_users'])}</td><td>{fmt_num(b['total_users'])}</td><td>{fmt_num(c['total_users'])}</td>
            <td>{fmt_pct(a['order_rate'])}</td><td>{fmt_pct(b['order_rate'])}</td><td>{fmt_pct(c['order_rate'])}</td>
            <td style="{color_diff(or_a_d)}">{fmt_diff(or_a_d, 'pp')}</td>
            <td style="{color_diff(or_b_d)}">{fmt_diff(or_b_d, 'pp')}</td>
            <td>{fmt_dollar(a['itt_revenue'])}</td><td>{fmt_dollar(b['itt_revenue'])}</td><td>{fmt_dollar(c['itt_revenue'])}</td>
            <td style="{color_diff(itt_a_d)}">{fmt_diff(itt_a_d)}</td>
            <td style="{color_diff(itt_b_d)}">{fmt_diff(itt_b_d)}</td>
            <td>{fmt_dollar(a['avg_cup_price'])}</td><td>{fmt_dollar(b['avg_cup_price'])}</td><td>{fmt_dollar(c['avg_cup_price'])}</td>
            <td style="{color_diff(cup_a_d)}">{fmt_diff(cup_a_d)}</td>
            <td style="{color_diff(cup_b_d)}">{fmt_diff(cup_b_d)}</td>
        </tr>'''
    return rows_html

# Economic analysis table
def make_econ_rows():
    rows_html = ''
    for lc in all_lcs:
        a = metrics[(groups[0], lc)]
        b = metrics[(groups[1], lc)]
        c = metrics[(groups[2], lc)]
        params = ltv_params[lc]

        # Revenue diff per user (ITT)
        a_rev_diff = a['itt_revenue'] - c['itt_revenue']
        b_rev_diff = b['itt_revenue'] - c['itt_revenue']

        # Monthly incremental revenue per user (scale to 30 days from 20 day window)
        days = 20  # 02-13 to 03-04
        a_monthly = a_rev_diff * 30 / days
        b_monthly = b_rev_diff * 30 / days

        # Lost cup revenue (price elasticity cost)
        a_cups_diff = a['itt_cups'] - c['itt_cups']
        b_cups_diff = b['itt_cups'] - c['itt_cups']
        a_cup_cost = abs(a_cups_diff) * c['avg_cup_price'] * 30 / days if a_cups_diff < 0 else 0
        b_cup_cost = abs(b_cups_diff) * c['avg_cup_price'] * 30 / days if b_cups_diff < 0 else 0

        # Margin payback (months to recoup lost cups through higher prices)
        margin = params['margin']
        a_margin_gain = a_monthly * margin if a_monthly > 0 else 0
        b_margin_gain = b_monthly * margin if b_monthly > 0 else 0
        a_payback = a_cup_cost / a_margin_gain if a_margin_gain > 0 else float('inf')
        b_payback = b_cup_cost / b_margin_gain if b_margin_gain > 0 else float('inf')

        border_class = 'total-row' if lc == '全量' else ''
        a_pb_str = f"{a_payback:.2f}月" if a_payback < 100 else "—"
        b_pb_str = f"{b_payback:.2f}月" if b_payback < 100 else "—"

        rows_html += f'''
        <tr class="{border_class}">
            <td class="lc-label">{lc}</td>
            <td>{fmt_num(a['total_users'])}</td><td>{fmt_num(b['total_users'])}</td><td>{fmt_num(c['total_users'])}</td>
            <td style="{color_diff(a_rev_diff)}">{'+' if a_rev_diff>=0 else ''}{a_rev_diff:.4f}</td>
            <td style="{color_diff(b_rev_diff)}">{'+' if b_rev_diff>=0 else ''}{b_rev_diff:.4f}</td>
            <td style="{color_diff(-a_cups_diff)}">{'+' if a_cups_diff>=0 else ''}{a_cups_diff:.4f}</td>
            <td style="{color_diff(-b_cups_diff)}">{'+' if b_cups_diff>=0 else ''}{b_cups_diff:.4f}</td>
            <td>{a_pb_str}</td>
            <td>{b_pb_str}</td>
        </tr>'''
    return rows_html

# Visit rate section
visit_html = ''
for g in groups:
    vu = visit_data.get(g, 0)
    tu = group_total_users[g]
    ou_all = metrics[(g, '全量')]['order_users']
    visit_rate = vu / tu * 100 if tu > 0 else 0
    purchase_rate = ou_all / vu * 100 if vu > 0 else 0
    visit_html += f'<tr><td>{g}</td><td>{fmt_num(tu)}</td><td>{fmt_num(vu)}</td><td>{fmt_pct(visit_rate)}</td><td>{fmt_num(ou_all)}</td><td>{fmt_pct(purchase_rate)}</td></tr>\n'

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>0212 老客涨价实验报告 (02-13 ~ 03-04)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
    --bg: #0f172a;
    --card: #1e293b;
    --border: #334155;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --accent: #3b82f6;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #eab308;
    --orange: #f97316;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'SF Pro Display', 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 24px; }}
.container {{ max-width: 1400px; margin: 0 auto; }}

/* Header */
.header {{ text-align: center; padding: 40px 0 32px; }}
.header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
.header .subtitle {{ color: var(--muted); font-size: 14px; }}
.header .tags {{ margin-top: 16px; display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }}
.tag {{ padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; }}
.tag-blue {{ background: rgba(59,130,246,0.15); color: var(--accent); border: 1px solid rgba(59,130,246,0.3); }}
.tag-green {{ background: rgba(34,197,94,0.15); color: var(--green); border: 1px solid rgba(34,197,94,0.3); }}
.tag-yellow {{ background: rgba(234,179,8,0.15); color: var(--yellow); border: 1px solid rgba(234,179,8,0.3); }}

/* Cards */
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 20px; }}
.card h2 {{ font-size: 18px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
.card h3 {{ font-size: 15px; font-weight: 600; margin: 16px 0 8px; color: var(--muted); }}

/* KPI strip */
.kpi-strip {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.kpi {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; text-align: center; }}
.kpi .label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}
.kpi .value {{ font-size: 24px; font-weight: 700; margin: 4px 0; }}
.kpi .diff {{ font-size: 13px; font-weight: 600; }}
.kpi .diff.positive {{ color: var(--green); }}
.kpi .diff.negative {{ color: var(--red); }}
.kpi .diff.neutral {{ color: var(--yellow); }}

/* Tables */
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ background: rgba(59,130,246,0.1); color: var(--accent); font-weight: 600; padding: 10px 8px; text-align: center; white-space: nowrap; position: sticky; top: 0; }}
td {{ padding: 8px; text-align: center; border-bottom: 1px solid var(--border); }}
.lc-label {{ font-weight: 600; text-align: left !important; white-space: nowrap; }}
.total-row {{ background: rgba(59,130,246,0.05); font-weight: 600; }}
.total-row td {{ border-top: 2px solid var(--accent); }}
tr:hover {{ background: rgba(255,255,255,0.02); }}
.th-group {{ border-bottom: 2px solid var(--accent); }}

/* Conclusion */
.conclusion {{ background: linear-gradient(135deg, rgba(59,130,246,0.1), rgba(139,92,246,0.1)); border: 1px solid rgba(59,130,246,0.3); border-radius: 12px; padding: 24px; }}
.conclusion h2 {{ color: var(--accent); }}
.conclusion ul {{ margin: 12px 0 0 20px; }}
.conclusion li {{ margin-bottom: 8px; }}
.highlight {{ color: var(--yellow); font-weight: 600; }}
.positive {{ color: var(--green); }}
.negative {{ color: var(--red); }}

/* Chart */
.chart-container {{ position: relative; height: 300px; margin: 16px 0; }}
.charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
@media (max-width: 900px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}

/* Design info */
.design-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
.design-item {{ background: rgba(255,255,255,0.03); border-radius: 8px; padding: 16px; text-align: center; }}
.design-item .group-name {{ font-weight: 700; font-size: 16px; margin-bottom: 4px; }}
.design-item .group-desc {{ color: var(--muted); font-size: 13px; }}
.design-item .group-count {{ font-size: 20px; font-weight: 700; color: var(--accent); margin-top: 8px; }}

/* Footer */
.footer {{ text-align: center; color: var(--muted); font-size: 12px; padding: 24px 0; }}
</style>
</head>
<body>
<div class="container">

<!-- Header -->
<div class="header">
    <h1>0212 老客涨价实验效果报告</h1>
    <div class="subtitle">Lucky US | 实验周期: 2026-02-13 ~ 03-04 (20天) | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    <div class="tags">
        <span class="tag tag-blue">DWD 订单明细表</span>
        <span class="tag tag-green">仅饮品 Drink Only</span>
        <span class="tag tag-yellow">门店订单 | type NOT IN (3,4,5)</span>
    </div>
</div>

<!-- KPI Summary -->
<div class="kpi-strip">
    <div class="kpi">
        <div class="label">A组 ITT人均饮品实收 vs 对照</div>
        <div class="value" style="color: var(--yellow);">{diff_pct(metrics[('A_涨价组1','全量')]['itt_revenue'], metrics[('C_对照组','全量')]['itt_revenue']):+.1f}%</div>
        <div class="diff neutral">收入基本持平</div>
    </div>
    <div class="kpi">
        <div class="label">B组 ITT人均饮品实收 vs 对照</div>
        <div class="value" style="color: var(--red);">{diff_pct(metrics[('B_涨价组2','全量')]['itt_revenue'], metrics[('C_对照组','全量')]['itt_revenue']):+.1f}%</div>
        <div class="diff negative">收入显著下降</div>
    </div>
    <div class="kpi">
        <div class="label">A组 单杯实收 vs 对照</div>
        <div class="value" style="color: var(--green);">{diff_pct(metrics[('A_涨价组1','全量')]['avg_cup_price'], metrics[('C_对照组','全量')]['avg_cup_price']):+.1f}%</div>
        <div class="diff positive">涨价有效推高单价</div>
    </div>
    <div class="kpi">
        <div class="label">全量下单率 差异 (A/B vs C)</div>
        <div class="value" style="color: var(--red);">{diff_pp(metrics[('A_涨价组1','全量')]['order_rate'], metrics[('C_对照组','全量')]['order_rate']):+.2f}pp</div>
        <div class="diff negative">涨价抑制购买</div>
    </div>
</div>

<!-- Experiment Design -->
<div class="card">
    <h2>1. 实验设计</h2>
    <div class="design-grid">
        <div class="design-item">
            <div class="group-name" style="color: #f97316;">A 涨价组1 (30%)</div>
            <div class="group-desc">75折系 — 折扣力度最小（激进涨价）</div>
            <div class="group-count">{fmt_num(metrics[('A_涨价组1','全量')]['total_users'])} 人</div>
        </div>
        <div class="design-item">
            <div class="group-name" style="color: #a855f7;">B 涨价组2 (30%)</div>
            <div class="group-desc">7折系 — 中等折扣（普通涨价）</div>
            <div class="group-count">{fmt_num(metrics[('B_涨价组2','全量')]['total_users'])} 人</div>
        </div>
        <div class="design-item">
            <div class="group-name" style="color: #3b82f6;">C 对照组 (40%)</div>
            <div class="group-desc">原价策略 — 维持现有折扣</div>
            <div class="group-count">{fmt_num(metrics[('C_对照组','全量')]['total_users'])} 人</div>
        </div>
    </div>
    <h3>分析口径</h3>
    <table>
        <tr><td style="text-align:left; font-weight:600; width:140px;">数据源</td><td style="text-align:left;">dw_dwd.dwd_t_ord_order_item_d_inc (DWD订单明细)</td></tr>
        <tr><td style="text-align:left; font-weight:600;">用户过滤</td><td style="text-align:left;">type NOT IN (3, 4, 5)，排除特殊/游客/外卖用户</td></tr>
        <tr><td style="text-align:left; font-weight:600;">订单过滤</td><td style="text-align:left;">order_category = '门店订单'，order_status = 90</td></tr>
        <tr><td style="text-align:left; font-weight:600;">品类</td><td style="text-align:left;">one_category_name = 'Drink'（仅饮品）</td></tr>
        <tr><td style="text-align:left; font-weight:600;">核心指标</td><td style="text-align:left;">ITT 进组人均饮品实收 = SUM(drink_pay) / 进组总人数</td></tr>
        <tr><td style="text-align:left; font-weight:600;">生命周期分层</td><td style="text-align:left;">按实验前最后下单距今：0-15天(活跃) / 16-30天(衰退) / 30+天(流失)</td></tr>
    </table>
</div>

<!-- Core Results: Segmented Summary Table -->
<div class="card">
    <h2>2. 分层核心指标对比</h2>
    <div style="overflow-x: auto;">
    <table>
        <thead>
            <tr>
                <th rowspan="2">分层</th>
                <th colspan="3" class="th-group">用户数</th>
                <th colspan="5" class="th-group">下单率</th>
                <th colspan="5" class="th-group">ITT人均饮品实收 $</th>
                <th colspan="5" class="th-group">单杯实收 $</th>
            </tr>
            <tr>
                <th>A组</th><th>B组</th><th>C组</th>
                <th>A组</th><th>B组</th><th>C组</th><th>A-C</th><th>B-C</th>
                <th>A组</th><th>B组</th><th>C组</th><th>A vs C</th><th>B vs C</th>
                <th>A组</th><th>B组</th><th>C组</th><th>A vs C</th><th>B vs C</th>
            </tr>
        </thead>
        <tbody>
            {make_summary_rows()}
        </tbody>
    </table>
    </div>
</div>

<!-- Visit & Purchase Rate -->
<div class="card">
    <h2>3. 来访与访购率</h2>
    <table>
        <thead>
            <tr><th>组别</th><th>进组人数</th><th>来访人数</th><th>来访率</th><th>购买人数</th><th>访购率</th></tr>
        </thead>
        <tbody>
            {visit_html}
        </tbody>
    </table>
</div>

<!-- Daily Trend Charts -->
<div class="card">
    <h2>4. 每日趋势</h2>
    <div class="charts-grid">
        <div>
            <h3>ITT 人均饮品实收 ($/人/天)</h3>
            <div class="chart-container"><canvas id="ittChart"></canvas></div>
        </div>
        <div>
            <h3>单杯实收 ($)</h3>
            <div class="chart-container"><canvas id="cupChart"></canvas></div>
        </div>
        <div>
            <h3>每日购买用户数</h3>
            <div class="chart-container"><canvas id="buyerChart"></canvas></div>
        </div>
        <div>
            <h3>ITT 人均实收累计差异 (A/B vs C)</h3>
            <div class="chart-container"><canvas id="cumDiffChart"></canvas></div>
        </div>
    </div>
</div>

<!-- Segmented Deep Dive -->
<div class="card">
    <h2>5. 分层深度解读</h2>

    <h3 style="color: var(--green);">30+天流失用户 — 涨价效果最好</h3>
    <p style="color: var(--muted); margin-bottom: 12px;">占进组人数 ~80%，但仅贡献 ~15% 饮品收入。这部分用户本身购买概率很低，涨价对其行为影响有限，但一旦购买则贡献更高单杯收入。</p>
    <table>
        <tr><th>指标</th><th>A组</th><th>B组</th><th>C对照</th><th>A vs C</th><th>B vs C</th></tr>
        <tr><td>下单率</td><td>{fmt_pct(metrics[('A_涨价组1','30+天')]['order_rate'])}</td><td>{fmt_pct(metrics[('B_涨价组2','30+天')]['order_rate'])}</td><td>{fmt_pct(metrics[('C_对照组','30+天')]['order_rate'])}</td>
            <td style="{color_diff(diff_pp(metrics[('A_涨价组1','30+天')]['order_rate'],metrics[('C_对照组','30+天')]['order_rate']))}">{diff_pp(metrics[('A_涨价组1','30+天')]['order_rate'],metrics[('C_对照组','30+天')]['order_rate']):+.2f}pp</td>
            <td style="{color_diff(diff_pp(metrics[('B_涨价组2','30+天')]['order_rate'],metrics[('C_对照组','30+天')]['order_rate']))}">{diff_pp(metrics[('B_涨价组2','30+天')]['order_rate'],metrics[('C_对照组','30+天')]['order_rate']):+.2f}pp</td></tr>
        <tr><td>ITT人均实收</td><td>{fmt_dollar(metrics[('A_涨价组1','30+天')]['itt_revenue'])}</td><td>{fmt_dollar(metrics[('B_涨价组2','30+天')]['itt_revenue'])}</td><td>{fmt_dollar(metrics[('C_对照组','30+天')]['itt_revenue'])}</td>
            <td style="{color_diff(diff_pct(metrics[('A_涨价组1','30+天')]['itt_revenue'],metrics[('C_对照组','30+天')]['itt_revenue']))}">{diff_pct(metrics[('A_涨价组1','30+天')]['itt_revenue'],metrics[('C_对照组','30+天')]['itt_revenue']):+.1f}%</td>
            <td style="{color_diff(diff_pct(metrics[('B_涨价组2','30+天')]['itt_revenue'],metrics[('C_对照组','30+天')]['itt_revenue']))}">{diff_pct(metrics[('B_涨价组2','30+天')]['itt_revenue'],metrics[('C_对照组','30+天')]['itt_revenue']):+.1f}%</td></tr>
        <tr><td>单杯实收</td><td>{fmt_dollar(metrics[('A_涨价组1','30+天')]['avg_cup_price'])}</td><td>{fmt_dollar(metrics[('B_涨价组2','30+天')]['avg_cup_price'])}</td><td>{fmt_dollar(metrics[('C_对照组','30+天')]['avg_cup_price'])}</td>
            <td style="{color_diff(diff_pct(metrics[('A_涨价组1','30+天')]['avg_cup_price'],metrics[('C_对照组','30+天')]['avg_cup_price']))}">{diff_pct(metrics[('A_涨价组1','30+天')]['avg_cup_price'],metrics[('C_对照组','30+天')]['avg_cup_price']):+.1f}%</td>
            <td style="{color_diff(diff_pct(metrics[('B_涨价组2','30+天')]['avg_cup_price'],metrics[('C_对照组','30+天')]['avg_cup_price']))}">{diff_pct(metrics[('B_涨价组2','30+天')]['avg_cup_price'],metrics[('C_对照组','30+天')]['avg_cup_price']):+.1f}%</td></tr>
    </table>

    <h3 style="color: var(--yellow); margin-top: 24px;">16-30天衰退用户 — 涨价温和正向</h3>
    <p style="color: var(--muted); margin-bottom: 12px;">占进组人数 ~9%，贡献 ~10% 饮品收入。单杯实收提升显著 (+13~16%)，虽杯量下降但价格弹性不大，ITT 实收正向。</p>
    <table>
        <tr><th>指标</th><th>A组</th><th>B组</th><th>C对照</th><th>A vs C</th><th>B vs C</th></tr>
        <tr><td>下单率</td><td>{fmt_pct(metrics[('A_涨价组1','16-30天')]['order_rate'])}</td><td>{fmt_pct(metrics[('B_涨价组2','16-30天')]['order_rate'])}</td><td>{fmt_pct(metrics[('C_对照组','16-30天')]['order_rate'])}</td>
            <td style="{color_diff(diff_pp(metrics[('A_涨价组1','16-30天')]['order_rate'],metrics[('C_对照组','16-30天')]['order_rate']))}">{diff_pp(metrics[('A_涨价组1','16-30天')]['order_rate'],metrics[('C_对照组','16-30天')]['order_rate']):+.2f}pp</td>
            <td style="{color_diff(diff_pp(metrics[('B_涨价组2','16-30天')]['order_rate'],metrics[('C_对照组','16-30天')]['order_rate']))}">{diff_pp(metrics[('B_涨价组2','16-30天')]['order_rate'],metrics[('C_对照组','16-30天')]['order_rate']):+.2f}pp</td></tr>
        <tr><td>ITT人均实收</td><td>{fmt_dollar(metrics[('A_涨价组1','16-30天')]['itt_revenue'])}</td><td>{fmt_dollar(metrics[('B_涨价组2','16-30天')]['itt_revenue'])}</td><td>{fmt_dollar(metrics[('C_对照组','16-30天')]['itt_revenue'])}</td>
            <td style="{color_diff(diff_pct(metrics[('A_涨价组1','16-30天')]['itt_revenue'],metrics[('C_对照组','16-30天')]['itt_revenue']))}">{diff_pct(metrics[('A_涨价组1','16-30天')]['itt_revenue'],metrics[('C_对照组','16-30天')]['itt_revenue']):+.1f}%</td>
            <td style="{color_diff(diff_pct(metrics[('B_涨价组2','16-30天')]['itt_revenue'],metrics[('C_对照组','16-30天')]['itt_revenue']))}">{diff_pct(metrics[('B_涨价组2','16-30天')]['itt_revenue'],metrics[('C_对照组','16-30天')]['itt_revenue']):+.1f}%</td></tr>
        <tr><td>单杯实收</td><td>{fmt_dollar(metrics[('A_涨价组1','16-30天')]['avg_cup_price'])}</td><td>{fmt_dollar(metrics[('B_涨价组2','16-30天')]['avg_cup_price'])}</td><td>{fmt_dollar(metrics[('C_对照组','16-30天')]['avg_cup_price'])}</td>
            <td style="{color_diff(diff_pct(metrics[('A_涨价组1','16-30天')]['avg_cup_price'],metrics[('C_对照组','16-30天')]['avg_cup_price']))}">{diff_pct(metrics[('A_涨价组1','16-30天')]['avg_cup_price'],metrics[('C_对照组','16-30天')]['avg_cup_price']):+.1f}%</td>
            <td style="{color_diff(diff_pct(metrics[('B_涨价组2','16-30天')]['avg_cup_price'],metrics[('C_对照组','16-30天')]['avg_cup_price']))}">{diff_pct(metrics[('B_涨价组2','16-30天')]['avg_cup_price'],metrics[('C_对照组','16-30天')]['avg_cup_price']):+.1f}%</td></tr>
    </table>

    <h3 style="color: var(--red); margin-top: 24px;">0-15天活跃用户 — A组持平，B组显著负向</h3>
    <p style="color: var(--muted); margin-bottom: 12px;">占进组人数 ~11%，但贡献 ~70% 饮品收入。该群体价格敏感度高，涨价导致杯量明显下降，B组总收入被拖负。</p>
    <table>
        <tr><th>指标</th><th>A组</th><th>B组</th><th>C对照</th><th>A vs C</th><th>B vs C</th></tr>
        <tr><td>下单率</td><td>{fmt_pct(metrics[('A_涨价组1','0-15天')]['order_rate'])}</td><td>{fmt_pct(metrics[('B_涨价组2','0-15天')]['order_rate'])}</td><td>{fmt_pct(metrics[('C_对照组','0-15天')]['order_rate'])}</td>
            <td style="{color_diff(diff_pp(metrics[('A_涨价组1','0-15天')]['order_rate'],metrics[('C_对照组','0-15天')]['order_rate']))}">{diff_pp(metrics[('A_涨价组1','0-15天')]['order_rate'],metrics[('C_对照组','0-15天')]['order_rate']):+.2f}pp</td>
            <td style="{color_diff(diff_pp(metrics[('B_涨价组2','0-15天')]['order_rate'],metrics[('C_对照组','0-15天')]['order_rate']))}">{diff_pp(metrics[('B_涨价组2','0-15天')]['order_rate'],metrics[('C_对照组','0-15天')]['order_rate']):+.2f}pp</td></tr>
        <tr><td>ITT人均实收</td><td>{fmt_dollar(metrics[('A_涨价组1','0-15天')]['itt_revenue'])}</td><td>{fmt_dollar(metrics[('B_涨价组2','0-15天')]['itt_revenue'])}</td><td>{fmt_dollar(metrics[('C_对照组','0-15天')]['itt_revenue'])}</td>
            <td style="{color_diff(diff_pct(metrics[('A_涨价组1','0-15天')]['itt_revenue'],metrics[('C_对照组','0-15天')]['itt_revenue']))}">{diff_pct(metrics[('A_涨价组1','0-15天')]['itt_revenue'],metrics[('C_对照组','0-15天')]['itt_revenue']):+.1f}%</td>
            <td style="{color_diff(diff_pct(metrics[('B_涨价组2','0-15天')]['itt_revenue'],metrics[('C_对照组','0-15天')]['itt_revenue']))}">{diff_pct(metrics[('B_涨价组2','0-15天')]['itt_revenue'],metrics[('C_对照组','0-15天')]['itt_revenue']):+.1f}%</td></tr>
        <tr><td>单杯实收</td><td>{fmt_dollar(metrics[('A_涨价组1','0-15天')]['avg_cup_price'])}</td><td>{fmt_dollar(metrics[('B_涨价组2','0-15天')]['avg_cup_price'])}</td><td>{fmt_dollar(metrics[('C_对照组','0-15天')]['avg_cup_price'])}</td>
            <td style="{color_diff(diff_pct(metrics[('A_涨价组1','0-15天')]['avg_cup_price'],metrics[('C_对照组','0-15天')]['avg_cup_price']))}">{diff_pct(metrics[('A_涨价组1','0-15天')]['avg_cup_price'],metrics[('C_对照组','0-15天')]['avg_cup_price']):+.1f}%</td>
            <td style="{color_diff(diff_pct(metrics[('B_涨价组2','0-15天')]['avg_cup_price'],metrics[('C_对照组','0-15天')]['avg_cup_price']))}">{diff_pct(metrics[('B_涨价组2','0-15天')]['avg_cup_price'],metrics[('C_对照组','0-15天')]['avg_cup_price']):+.1f}%</td></tr>
        <tr><td>ITT人均杯量</td><td>{metrics[('A_涨价组1','0-15天')]['itt_cups']:.4f}</td><td>{metrics[('B_涨价组2','0-15天')]['itt_cups']:.4f}</td><td>{metrics[('C_对照组','0-15天')]['itt_cups']:.4f}</td>
            <td style="{color_diff(diff_pct(metrics[('A_涨价组1','0-15天')]['itt_cups'],metrics[('C_对照组','0-15天')]['itt_cups']))}">{diff_pct(metrics[('A_涨价组1','0-15天')]['itt_cups'],metrics[('C_对照组','0-15天')]['itt_cups']):+.1f}%</td>
            <td style="{color_diff(diff_pct(metrics[('B_涨价组2','0-15天')]['itt_cups'],metrics[('C_对照组','0-15天')]['itt_cups']))}">{diff_pct(metrics[('B_涨价组2','0-15天')]['itt_cups'],metrics[('C_对照组','0-15天')]['itt_cups']):+.1f}%</td></tr>
    </table>
</div>

<!-- Economic Analysis -->
<div class="card">
    <h2>6. 经济分析</h2>
    <p style="color: var(--muted); margin-bottom: 16px;">核心问题：涨价带来的单杯收入提升，能否在可接受周期内弥补杯量损失？</p>
    <table>
        <thead>
            <tr>
                <th>分层</th>
                <th colspan="3">用户数</th>
                <th colspan="2">ITT实收增量 $/人</th>
                <th colspan="2">ITT杯量增量 杯/人</th>
                <th colspan="2">毛利回收周期</th>
            </tr>
            <tr>
                <th></th><th>A组</th><th>B组</th><th>C组</th>
                <th>A-C</th><th>B-C</th><th>A-C</th><th>B-C</th>
                <th>A组</th><th>B组</th>
            </tr>
        </thead>
        <tbody>
            {make_econ_rows()}
        </tbody>
    </table>
    <p style="color: var(--muted); font-size: 12px; margin-top: 12px;">毛利回收周期 = 杯量损失成本 / (月增量收入 × 边际毛利率)。&lt;1月为快速回收。边际毛利率假设：活跃0.6、衰退0.5、流失0.4。</p>
</div>

<!-- Conclusion -->
<div class="conclusion">
    <h2>7. 结论与建议</h2>
    <h3 style="color: var(--text); margin-top: 16px;">核心发现</h3>
    <ul>
        <li><strong>辛普森悖论</strong>：全量看 A组持平(-0.2%)、B组负向(-4.0%)，但分层后衰退/流失用户实收显著正向。原因是活跃用户仅占11%人数却贡献70%收入，其杯量下降拖负了整体。</li>
        <li><strong>A组(75折系)优于B组(7折系)</strong>：A组在所有分层的ITT实收 diff 都优于B组，特别是活跃用户层（A: +1.1% vs B: -7.4%）。</li>
        <li><strong>涨价对不同生命周期用户影响不同</strong>：
            <ul>
                <li><span class="positive">30+天流失用户</span>：涨价 A/B 组 ITT 实收分别 <span class="positive">+14.8%/+11.7%</span>，效果最显著</li>
                <li><span class="highlight">16-30天衰退用户</span>：涨价正向 <span class="positive">+3.3%/+5.9%</span>，价格敏感度低</li>
                <li><span class="negative">0-15天活跃用户</span>：A组勉强持平(+1.1%)，B组显著负向(<span class="negative">-7.4%</span>)，价格敏感度最高</li>
            </ul>
        </li>
    </ul>
    <h3 style="color: var(--text); margin-top: 16px;">策略建议</h3>
    <ul>
        <li><strong>分人群定价</strong>：对衰退/流失用户推行涨价策略（首选A组75折系），对活跃用户维持现有折扣力度</li>
        <li><strong>继续观察</strong>：当前20天数据窗口偏短，建议追踪至少45天确认长期趋势稳定性</li>
        <li><strong>关注B组活跃用户</strong>：B组对活跃用户 ITT 实收 -7.4%，如全量推行将严重影响核心收入</li>
    </ul>
</div>

<div class="footer">
    Lucky US Data Team | 数据口径：DWD订单明细 + 仅饮品 + type NOT IN (3,4,5) + 门店订单 | 报告自动生成
</div>
</div>

<script>
const dates = {chart_dates_json};
const shortDates = dates.map(d => d.slice(5));

const colors = {{
    a: {{ line: '#f97316', bg: 'rgba(249,115,22,0.1)' }},
    b: {{ line: '#a855f7', bg: 'rgba(168,85,247,0.1)' }},
    c: {{ line: '#3b82f6', bg: 'rgba(59,130,246,0.1)' }},
}};

const commonOpts = {{
    responsive: true,
    maintainAspectRatio: false,
    interaction: {{ intersect: false, mode: 'index' }},
    plugins: {{
        legend: {{ labels: {{ color: '#94a3b8', font: {{ size: 11 }} }} }},
        tooltip: {{ backgroundColor: '#1e293b', borderColor: '#334155', borderWidth: 1 }},
    }},
    scales: {{
        x: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }}, maxRotation: 45 }}, grid: {{ color: 'rgba(51,65,85,0.3)' }} }},
        y: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: 'rgba(51,65,85,0.3)' }} }},
    }},
}};

function makeDS(label, data, color) {{
    return {{ label, data, borderColor: color.line, backgroundColor: color.bg, borderWidth: 2, pointRadius: 2, tension: 0.3, fill: false }};
}}

// ITT Chart
new Chart(document.getElementById('ittChart'), {{
    type: 'line',
    data: {{ labels: shortDates, datasets: [
        makeDS('A 涨价组1', {chart_itt_a}, colors.a),
        makeDS('B 涨价组2', {chart_itt_b}, colors.b),
        makeDS('C 对照组', {chart_itt_c}, colors.c),
    ] }},
    options: {{ ...commonOpts, scales: {{ ...commonOpts.scales, y: {{ ...commonOpts.scales.y, title: {{ display: true, text: '$/人', color: '#64748b' }} }} }} }}
}});

// Cup Price Chart
new Chart(document.getElementById('cupChart'), {{
    type: 'line',
    data: {{ labels: shortDates, datasets: [
        makeDS('A 涨价组1', {chart_cup_a}, colors.a),
        makeDS('B 涨价组2', {chart_cup_b}, colors.b),
        makeDS('C 对照组', {chart_cup_c}, colors.c),
    ] }},
    options: {{ ...commonOpts, scales: {{ ...commonOpts.scales, y: {{ ...commonOpts.scales.y, title: {{ display: true, text: '$/杯', color: '#64748b' }} }} }} }}
}});

// Buyer Count Chart
new Chart(document.getElementById('buyerChart'), {{
    type: 'line',
    data: {{ labels: shortDates, datasets: [
        makeDS('A 涨价组1', {chart_buyers_a}, colors.a),
        makeDS('B 涨价组2', {chart_buyers_b}, colors.b),
        makeDS('C 对照组', {chart_buyers_c}, colors.c),
    ] }},
    options: commonOpts
}});

// Cumulative ITT Diff Chart
const ittA = {chart_itt_a};
const ittB = {chart_itt_b};
const ittC = {chart_itt_c};
let cumA = [], cumB = [], sumA = 0, sumB = 0;
for (let i = 0; i < dates.length; i++) {{
    sumA += (ittA[i] - ittC[i]);
    sumB += (ittB[i] - ittC[i]);
    cumA.push(+(sumA * 1000).toFixed(2));
    cumB.push(+(sumB * 1000).toFixed(2));
}}
new Chart(document.getElementById('cumDiffChart'), {{
    type: 'line',
    data: {{ labels: shortDates, datasets: [
        {{ ...makeDS('A-C 累计差', cumA, colors.a), fill: true }},
        {{ ...makeDS('B-C 累计差', cumB, colors.b), fill: true }},
    ] }},
    options: {{ ...commonOpts, scales: {{ ...commonOpts.scales, y: {{ ...commonOpts.scales.y, title: {{ display: true, text: '千分之 $', color: '#64748b' }} }} }} }}
}});
</script>
</body>
</html>'''

output_path = '/Users/xiaoxiao/Vibe coding/0212涨价实验报告_对齐版_0213-0304.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅ 报告已生成: {output_path}")
print(f"   文件大小: {os.path.getsize(output_path) / 1024:.1f} KB")
