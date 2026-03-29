#!/usr/bin/env python3
"""0212涨价实验 - 分层日均杯量贡献分析
维度: 3组 × 3分层 × 20天
"""
import subprocess, json, time, os, sys
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
# 配置
# ============================================================
BEGIN_DATE = '2026-02-13'
END_DATE = '2026-03-04'
DAYS = 20

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

# 用户数 (from previous run)
user_counts = {
    ('A_涨价组1', '0-15天'): 4217, ('A_涨价组1', '16-30天'): 3292, ('A_涨价组1', '30+天'): 30445,
    ('B_涨价组2', '0-15天'): 4368, ('B_涨价组2', '16-30天'): 3307, ('B_涨价组2', '30+天'): 30247,
    ('C_对照组', '0-15天'): 5895, ('C_对照组', '16-30天'): 4169, ('C_对照组', '30+天'): 40020,
}

# 全周期汇总数据 (from previous run)
summary = {
    ('A_涨价组1', '0-15天'): {'cups': 7616, 'pay': 28856.24},
    ('A_涨价组1', '16-30天'): {'cups': 1335, 'pay': 4493.14},
    ('A_涨价组1', '30+天'): {'cups': 2449, 'pay': 7402.15},
    ('B_涨价组2', '0-15天'): {'cups': 7353, 'pay': 27369.20},
    ('B_涨价组2', '16-30天'): {'cups': 1345, 'pay': 4626.81},
    ('B_涨价组2', '30+天'): {'cups': 2407, 'pay': 7158.91},
    ('C_对照组', '0-15天'): {'cups': 11319, 'pay': 39890.81},
    ('C_对照组', '16-30天'): {'cups': 1849, 'pay': 5506.99},
    ('C_对照组', '30+天'): {'cups': 3483, 'pay': 8476.30},
}

# ============================================================
# Step 1: 每日分层杯量查询
# ============================================================
print("=" * 60)
print("Step 1: 查询每日分层杯量 (9组 × ~20天)")
print("=" * 60)

daily_data = {}  # (group, lifecycle) -> [{dt, cups, order_users, pay}, ...]

for group_name, lifecycles in lifecycle_groups.items():
    for lc_name, gname in lifecycles.items():
        key = (group_name, lc_name)
        print(f"\n  {group_name}/{lc_name}...")
        sql = f"""
SELECT
    o.dt,
    COUNT(DISTINCT o.user_no) AS order_users,
    COUNT(*) AS cups,
    ROUND(SUM(o.pay_amount), 2) AS pay
FROM dw_dwd.dwd_t_ord_order_item_d_inc o
INNER JOIN (
    SELECT DISTINCT g.user_no
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN ods_luckyus_sales_crm.t_user u ON g.user_no = u.user_no AND u.type NOT IN (3, 4, 5) AND INSTR(COALESCE(u.tenant, 'LKUS'), 'IQ') = 0
    WHERE g.dt = '2026-02-12' AND g.tenant = 'LKUS' AND g.group_name = '{gname}'
) vu ON o.user_no = vu.user_no
WHERE o.dt BETWEEN '{BEGIN_DATE}' AND '{END_DATE}'
    AND o.tenant = 'LKUS' AND o.order_status = 90
    AND o.order_category = '门店订单' AND o.one_category_name = 'Drink'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY o.dt
ORDER BY o.dt
"""
        rows = run_sql(sql)
        if rows:
            daily_data[key] = rows
            print(f"    ✓ {len(rows)} 天")
        else:
            daily_data[key] = []
            print(f"    ✗ 失败")

# ============================================================
# Step 2: 计算核心指标
# ============================================================
print("\n\n" + "=" * 60)
print("Step 2: 核心指标计算")
print("=" * 60)

groups = ['A_涨价组1', 'B_涨价组2', 'C_对照组']
lcs = ['0-15天', '16-30天', '30+天']

# 2a. ITT 日均杯量 & 杯量弹性
print(f"\n{'─'*100}")
print(f"{'分层日均杯量 & 杯量弹性 (全周期 02-13 ~ 03-04)':^100}")
print(f"{'─'*100}")
print(f"{'分层':<10} │ {'A日均杯/人':>12} │ {'B日均杯/人':>12} │ {'C日均杯/人':>12} │ {'A杯量diff':>10} │ {'B杯量diff':>10} │ {'A单价diff':>10} │ {'B单价diff':>10} │ {'A弹性':>8} │ {'B弹性':>8}")
print("─" * 110)

elasticity = {}
for lc in lcs + ['全量']:
    if lc == '全量':
        a_cups = sum(summary[('A_涨价组1', l)]['cups'] for l in lcs)
        b_cups = sum(summary[('B_涨价组2', l)]['cups'] for l in lcs)
        c_cups = sum(summary[('C_对照组', l)]['cups'] for l in lcs)
        a_pay = sum(summary[('A_涨价组1', l)]['pay'] for l in lcs)
        b_pay = sum(summary[('B_涨价组2', l)]['pay'] for l in lcs)
        c_pay = sum(summary[('C_对照组', l)]['pay'] for l in lcs)
        a_users = sum(user_counts[('A_涨价组1', l)] for l in lcs)
        b_users = sum(user_counts[('B_涨价组2', l)] for l in lcs)
        c_users = sum(user_counts[('C_对照组', l)] for l in lcs)
    else:
        a_cups = summary[('A_涨价组1', lc)]['cups']
        b_cups = summary[('B_涨价组2', lc)]['cups']
        c_cups = summary[('C_对照组', lc)]['cups']
        a_pay = summary[('A_涨价组1', lc)]['pay']
        b_pay = summary[('B_涨价组2', lc)]['pay']
        c_pay = summary[('C_对照组', lc)]['pay']
        a_users = user_counts[('A_涨价组1', lc)]
        b_users = user_counts[('B_涨价组2', lc)]
        c_users = user_counts[('C_对照组', lc)]

    # ITT 日均杯量
    a_daily = a_cups / a_users / DAYS
    b_daily = b_cups / b_users / DAYS
    c_daily = c_cups / c_users / DAYS

    # 杯量 diff%
    a_cup_diff = (a_daily / c_daily - 1) * 100 if c_daily > 0 else 0
    b_cup_diff = (b_daily / c_daily - 1) * 100 if c_daily > 0 else 0

    # 单杯实收 diff%
    a_cup_price = a_pay / a_cups if a_cups > 0 else 0
    b_cup_price = b_pay / b_cups if b_cups > 0 else 0
    c_cup_price = c_pay / c_cups if c_cups > 0 else 0
    a_price_diff = (a_cup_price / c_cup_price - 1) * 100 if c_cup_price > 0 else 0
    b_price_diff = (b_cup_price / c_cup_price - 1) * 100 if c_cup_price > 0 else 0

    # 弹性 = 杯量变化% / 价格变化%
    a_elast = a_cup_diff / a_price_diff if a_price_diff != 0 else 0
    b_elast = b_cup_diff / b_price_diff if b_price_diff != 0 else 0

    elasticity[lc] = {'a': a_elast, 'b': b_elast}

    prefix = "★ " if lc == '全量' else "  "
    print(f"{prefix}{lc:<8} │ {a_daily:>12.6f} │ {b_daily:>12.6f} │ {c_daily:>12.6f} │ {a_cup_diff:>+9.1f}% │ {b_cup_diff:>+9.1f}% │ {a_price_diff:>+9.1f}% │ {b_price_diff:>+9.1f}% │ {a_elast:>8.2f} │ {b_elast:>8.2f}")

# 2b. 绝对杯量损失拆解
print(f"\n{'─'*100}")
print(f"{'每日绝对杯量损失拆解':^100}")
print(f"{'─'*100}")
print(f"{'分层':<10} │ {'用户数A':>8} │ {'用户数C':>8} │ {'A日均杯/人':>12} │ {'C日均杯/人':>12} │ {'差异杯/人':>10} │ {'A日损失杯':>10} │ {'A日损失$':>10} │ {'占比':>8}")

total_a_loss_cups = 0
total_b_loss_cups = 0
loss_detail = {}

for lc in lcs:
    a_users = user_counts[('A_涨价组1', lc)]
    c_users = user_counts[('C_对照组', lc)]
    a_cups = summary[('A_涨价组1', lc)]['cups']
    c_cups = summary[('C_对照组', lc)]['cups']
    c_pay = summary[('C_对照组', lc)]['pay']
    c_cup_price = c_pay / c_cups if c_cups > 0 else 0

    a_daily_per_user = a_cups / a_users / DAYS
    c_daily_per_user = c_cups / c_users / DAYS
    diff_per_user = a_daily_per_user - c_daily_per_user
    daily_loss_cups = diff_per_user * a_users
    daily_loss_dollars = daily_loss_cups * c_cup_price

    loss_detail[lc] = {'cups': daily_loss_cups, 'dollars': daily_loss_dollars}
    total_a_loss_cups += daily_loss_cups

for lc in lcs:
    a_users = user_counts[('A_涨价组1', lc)]
    c_users = user_counts[('C_对照组', lc)]
    a_cups = summary[('A_涨价组1', lc)]['cups']
    c_cups = summary[('C_对照组', lc)]['cups']
    c_pay = summary[('C_对照组', lc)]['pay']
    c_cup_price = c_pay / c_cups if c_cups > 0 else 0

    a_daily = a_cups / a_users / DAYS
    c_daily = c_cups / c_users / DAYS
    diff = a_daily - c_daily
    ld = loss_detail[lc]
    pct = ld['cups'] / total_a_loss_cups * 100 if total_a_loss_cups != 0 else 0

    print(f"  {lc:<8} │ {a_users:>8,} │ {c_users:>8,} │ {a_daily:>12.6f} │ {c_daily:>12.6f} │ {diff:>+10.6f} │ {ld['cups']:>+10.1f} │ ${ld['dollars']:>+9.2f} │ {pct:>7.1f}%")

print(f"  {'全量':<8} │ {'':>8} │ {'':>8} │ {'':>12} │ {'':>12} │ {'':>10} │ {total_a_loss_cups:>+10.1f} │ {'':>10} │ {'100.0%':>8}")

# Same for B group
print(f"\n  --- B组损失拆解 ---")
total_b_loss = 0
loss_b = {}
for lc in lcs:
    b_users = user_counts[('B_涨价组2', lc)]
    c_users = user_counts[('C_对照组', lc)]
    b_cups = summary[('B_涨价组2', lc)]['cups']
    c_cups = summary[('C_对照组', lc)]['cups']
    c_pay = summary[('C_对照组', lc)]['pay']
    c_cup_price = c_pay / c_cups if c_cups > 0 else 0

    b_daily = b_cups / b_users / DAYS
    c_daily = c_cups / c_users / DAYS
    diff = b_daily - c_daily
    daily_loss = diff * b_users
    loss_b[lc] = daily_loss
    total_b_loss += daily_loss

for lc in lcs:
    b_users = user_counts[('B_涨价组2', lc)]
    c_cups = summary[('C_对照组', lc)]['cups']
    c_pay = summary[('C_对照组', lc)]['pay']
    c_cup_price = c_pay / c_cups if c_cups > 0 else 0
    pct = loss_b[lc] / total_b_loss * 100 if total_b_loss != 0 else 0
    print(f"  {lc:<8} │ B日损失杯: {loss_b[lc]:>+8.1f} │ B日损失$: ${loss_b[lc]*c_cup_price:>+8.2f} │ 占比: {pct:>6.1f}%")

# ============================================================
# Step 3: 前10天 vs 后10天趋势分析
# ============================================================
print(f"\n\n{'─'*100}")
print(f"{'前10天 vs 后10天 杯量趋势':^100}")
print(f"{'─'*100}")

all_dates = sorted(set(r['dt'] for rows in daily_data.values() for r in rows if rows))
mid = len(all_dates) // 2
first_half_dates = set(all_dates[:mid])
second_half_dates = set(all_dates[mid:])

print(f"  前半段: {all_dates[0]} ~ {all_dates[mid-1]} ({mid}天)")
print(f"  后半段: {all_dates[mid]} ~ {all_dates[-1]} ({len(all_dates)-mid}天)")
print(f"\n{'分层':<10} │ {'组别':<12} │ {'前半日均杯/人':>14} │ {'后半日均杯/人':>14} │ {'变化':>10} │ {'趋势':>6}")
print("─" * 80)

trend_data = {}
for lc in lcs:
    for g in groups:
        key = (g, lc)
        users = user_counts[key]
        rows = daily_data.get(key, [])

        first_cups = sum(int(r['cups']) for r in rows if r['dt'] in first_half_dates)
        second_cups = sum(int(r['cups']) for r in rows if r['dt'] in second_half_dates)

        first_daily = first_cups / users / mid if users > 0 and mid > 0 else 0
        second_daily = second_cups / users / (len(all_dates) - mid) if users > 0 else 0
        change = (second_daily / first_daily - 1) * 100 if first_daily > 0 else 0

        trend = "↑恢复" if change > 2 else ("↓恶化" if change < -2 else "→稳定")
        trend_data[(g, lc)] = {'first': first_daily, 'second': second_daily, 'change': change, 'trend': trend}

        print(f"  {lc:<8} │ {g:<12} │ {first_daily:>14.6f} │ {second_daily:>14.6f} │ {change:>+9.1f}% │ {trend}")
    print()

# 关键：看实验组相对对照组的差异变化
print(f"\n{'─'*100}")
print(f"{'趋势核心: 实验组 vs 对照组的 diff 变化':^100}")
print(f"{'─'*100}")
print(f"{'分层':<10} │ {'A前半diff%':>12} │ {'A后半diff%':>12} │ {'diff变化':>10} │ {'B前半diff%':>12} │ {'B后半diff%':>12} │ {'diff变化':>10}")
print("─" * 90)

for lc in lcs + ['全量']:
    if lc == '全量':
        # aggregate
        for g in groups:
            first_total = sum(
                sum(int(r['cups']) for r in daily_data.get((g, l), []) if r['dt'] in first_half_dates)
                for l in lcs
            )
            second_total = sum(
                sum(int(r['cups']) for r in daily_data.get((g, l), []) if r['dt'] in second_half_dates)
                for l in lcs
            )
            total_users = sum(user_counts[(g, l)] for l in lcs)
            trend_data[(g, '全量')] = {
                'first': first_total / total_users / mid if total_users > 0 else 0,
                'second': second_total / total_users / (len(all_dates) - mid) if total_users > 0 else 0,
            }

    a_first = trend_data[('A_涨价组1', lc)]['first']
    b_first = trend_data[('B_涨价组2', lc)]['first']
    c_first = trend_data[('C_对照组', lc)]['first']
    a_second = trend_data[('A_涨价组1', lc)]['second']
    b_second = trend_data[('B_涨价组2', lc)]['second']
    c_second = trend_data[('C_对照组', lc)]['second']

    a_diff_first = (a_first / c_first - 1) * 100 if c_first > 0 else 0
    a_diff_second = (a_second / c_second - 1) * 100 if c_second > 0 else 0
    b_diff_first = (b_first / c_first - 1) * 100 if c_first > 0 else 0
    b_diff_second = (b_second / c_second - 1) * 100 if c_second > 0 else 0

    a_delta = a_diff_second - a_diff_first
    b_delta = b_diff_second - b_diff_first

    a_trend = "收敛" if a_delta > 0 and a_diff_first < 0 else ("扩大" if a_delta < 0 and a_diff_first < 0 else "—")
    b_trend = "收敛" if b_delta > 0 and b_diff_first < 0 else ("扩大" if b_delta < 0 and b_diff_first < 0 else "—")

    prefix = "★ " if lc == '全量' else "  "
    print(f"{prefix}{lc:<8} │ {a_diff_first:>+11.1f}% │ {a_diff_second:>+11.1f}% │ {a_delta:>+8.1f}pp {a_trend} │ {b_diff_first:>+11.1f}% │ {b_diff_second:>+11.1f}% │ {b_delta:>+8.1f}pp {b_trend}")

# ============================================================
# Save daily data as JSON for chart generation
# ============================================================
chart_data = {}
for key, rows in daily_data.items():
    g, lc = key
    users = user_counts[key]
    chart_data[f"{g}_{lc}"] = [
        {'dt': r['dt'], 'cups': int(r['cups']), 'users': users, 'itt_daily': int(r['cups']) / users if users > 0 else 0}
        for r in rows
    ]

with open('/Users/xiaoxiao/Vibe coding/0212_cups_daily_data.json', 'w') as f:
    json.dump({
        'daily': chart_data,
        'user_counts': {f"{k[0]}_{k[1]}": v for k, v in user_counts.items()},
        'summary': {f"{k[0]}_{k[1]}": v for k, v in summary.items()},
        'elasticity': elasticity,
        'loss_detail_a': {k: v for k, v in loss_detail.items()},
    }, f, ensure_ascii=False, indent=2)

print(f"\n\n✅ 每日数据已保存: 0212_cups_daily_data.json")
print("准备生成可视化报告...")
