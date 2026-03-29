#!/usr/bin/env python3
"""0212涨价实验 - 按同事口径重新分析
时间: 02-13 ~ 03-04
口径: DWD表 + type NOT IN (3,4,5) + 仅饮品 + order_category='门店订单'
分层: 0-15天 / 16-30天 / 30+天
"""
import subprocess, json, time, sys

def run_sql(sql, max_retries=4, wait=10):
    """Execute SQL via CyberData API"""
    for attempt in range(max_retries):
        result = subprocess.run(
            ['/Users/xiaoxiao/.claude/skills/cyberdata-query/run_sql.sh', sql],
            capture_output=True, text=True, timeout=120
        )
        output = result.stdout.strip()
        if '查询失败或无结果' in output or not output:
            if attempt < max_retries - 1:
                print(f"  重试 {attempt+2}/{max_retries}...")
                time.sleep(wait)
                continue
            return None
        # Parse TSV output
        lines = output.split('\n')
        data_start = 0
        for i, line in enumerate(lines):
            if '\t' in line and not line.startswith('提交') and not line.startswith('任务') and not line.startswith('等待'):
                data_start = i
                break
        if data_start >= len(lines):
            if attempt < max_retries - 1:
                print(f"  未找到数据，重试 {attempt+2}/{max_retries}...")
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
            print(f"  空结果，重试 {attempt+2}/{max_retries}...")
            time.sleep(wait)
    return None

# ============================================================
# 分组 × 分层人群名
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

# ============================================================
# 逐组逐分层查询（避免超时）
# ============================================================
all_results = []

for group_name, lifecycles in lifecycle_groups.items():
    for lc_name, gname in lifecycles.items():
        print(f"\n查询 {group_name} / {lc_name} ...")

        sql = f"""
SELECT
    '{group_name}' AS exp_group,
    '{lc_name}' AS lifecycle,
    user_stats.total_users,
    COALESCE(order_stats.order_users, 0) AS order_users,
    COALESCE(order_stats.drink_cnt, 0) AS drink_cnt,
    ROUND(COALESCE(order_stats.drink_pay_money, 0), 2) AS drink_pay_money,
    ROUND(COALESCE(order_stats.drink_origin_price, 0), 2) AS drink_origin_price
FROM (
    SELECT COUNT(DISTINCT g.user_no) AS total_users
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN ods_luckyus_sales_crm.t_user u
        ON g.user_no = u.user_no
        AND u.type NOT IN (3, 4, 5)
        AND INSTR(COALESCE(u.tenant, 'LKUS'), 'IQ') = 0
    WHERE g.dt = '2026-02-12' AND g.tenant = 'LKUS'
        AND g.group_name = '{gname}'
) user_stats
LEFT JOIN (
    SELECT
        COUNT(DISTINCT o.user_no) AS order_users,
        COUNT(*) AS drink_cnt,
        SUM(o.pay_amount) AS drink_pay_money,
        SUM(o.origin_price) AS drink_origin_price
    FROM dw_dwd.dwd_t_ord_order_item_d_inc o
    INNER JOIN (
        SELECT DISTINCT g.user_no
        FROM dw_ads.ads_marketing_t_user_group_d_his g
        INNER JOIN ods_luckyus_sales_crm.t_user u
            ON g.user_no = u.user_no
            AND u.type NOT IN (3, 4, 5)
            AND INSTR(COALESCE(u.tenant, 'LKUS'), 'IQ') = 0
        WHERE g.dt = '2026-02-12' AND g.tenant = 'LKUS'
            AND g.group_name = '{gname}'
    ) vu ON o.user_no = vu.user_no
    WHERE o.dt BETWEEN '2026-02-13' AND '2026-03-04'
        AND o.tenant = 'LKUS'
        AND o.order_status = 90
        AND o.order_category = '门店订单'
        AND o.one_category_name = 'Drink'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
) order_stats ON 1=1
"""
        rows = run_sql(sql)
        if rows:
            row = rows[0]
            print(f"  用户={row['total_users']}, 购买={row['order_users']}, "
                  f"杯数={row['drink_cnt']}, 饮品实收=${row['drink_pay_money']}")
            all_results.append(row)
        else:
            print(f"  ❌ 查询失败!")
            all_results.append({
                'exp_group': group_name, 'lifecycle': lc_name,
                'total_users': '0', 'order_users': '0',
                'drink_cnt': '0', 'drink_pay_money': '0', 'drink_origin_price': '0'
            })

# ============================================================
# 汇总分析
# ============================================================
print("\n" + "=" * 120)
print(f"{'0212 涨价实验分层对比 (02-13 ~ 03-04) — 与同事口径对齐':^120}")
print("=" * 120)

# Parse into metrics dict
metrics = {}
for row in all_results:
    key = (row['exp_group'], row['lifecycle'])
    total = int(row['total_users'])
    orders = int(row['order_users'])
    cups = int(row['drink_cnt'])
    pay = float(row['drink_pay_money'])
    origin = float(row['drink_origin_price'])
    metrics[key] = {
        'total_users': total,
        'order_users': orders,
        'drink_cnt': cups,
        'drink_pay': pay,
        'drink_origin': origin,
        'order_rate': orders / total * 100 if total > 0 else 0,
        'itt_revenue': pay / total if total > 0 else 0,
        'itt_cups': cups / total if total > 0 else 0,
        'avg_cup_price': pay / cups if cups > 0 else 0,
        'discount_rate': pay / origin if origin > 0 else 0,
    }

# Calculate 全量 totals
lifecycles = ['0-15天', '16-30天', '30+天']
for grp in ['A_涨价组1', 'B_涨价组2', 'C_对照组']:
    tu = sum(metrics.get((grp, lc), {}).get('total_users', 0) for lc in lifecycles)
    ou = sum(metrics.get((grp, lc), {}).get('order_users', 0) for lc in lifecycles)
    dc = sum(metrics.get((grp, lc), {}).get('drink_cnt', 0) for lc in lifecycles)
    dp = sum(metrics.get((grp, lc), {}).get('drink_pay', 0) for lc in lifecycles)
    do = sum(metrics.get((grp, lc), {}).get('drink_origin', 0) for lc in lifecycles)
    metrics[(grp, '全量')] = {
        'total_users': tu, 'order_users': ou, 'drink_cnt': dc,
        'drink_pay': dp, 'drink_origin': do,
        'order_rate': ou / tu * 100 if tu > 0 else 0,
        'itt_revenue': dp / tu if tu > 0 else 0,
        'itt_cups': dc / tu if tu > 0 else 0,
        'avg_cup_price': dp / dc if dc > 0 else 0,
        'discount_rate': dp / do if do > 0 else 0,
    }

# 同事结论
colleague = {
    ('A_涨价组1', '0-15天'): {'rev': 1.1, 'cup': 7.7},
    ('A_涨价组1', '16-30天'): {'rev': 3.3, 'cup': 13.1},
    ('A_涨价组1', '30+天'): {'rev': 14.8, 'cup': 24.3},
    ('A_涨价组1', '全量'): {'rev': -0.2, 'cup': 10.2},
    ('B_涨价组2', '0-15天'): {'rev': -7.4},
    ('B_涨价组2', '16-30天'): {'rev': 5.9},
    ('B_涨价组2', '30+天'): {'rev': 11.7},
    ('B_涨价组2', '全量'): {'rev': -4.0},
}

# ---- 详细表 ----
all_lc = ['0-15天', '16-30天', '30+天', '全量']
for lc in all_lc:
    a = metrics.get(('A_涨价组1', lc))
    b = metrics.get(('B_涨价组2', lc))
    c = metrics.get(('C_对照组', lc))
    if not a or not b or not c:
        continue
    col_a = colleague.get(('A_涨价组1', lc), {})
    col_b = colleague.get(('B_涨价组2', lc), {})

    print(f"\n── {lc} {'─'*(100-len(lc)*2)}")
    print(f"  {'指标':<22} {'A_涨价组1':>14} {'B_涨价组2':>14} {'C_对照组':>14} │ {'A vs C':>10} {'B vs C':>10} │ {'同事A':>8} {'同事B':>8}")
    print(f"  {'─'*110}")

    # 用户数
    print(f"  {'用户数':<22} {a['total_users']:>14,} {b['total_users']:>14,} {c['total_users']:>14,} │ {'':>10} {'':>10} │ {'':>8} {'':>8}")

    # 下单率
    a_or_d = a['order_rate'] - c['order_rate']
    b_or_d = b['order_rate'] - c['order_rate']
    print(f"  {'下单率':<22} {a['order_rate']:>13.2f}% {b['order_rate']:>13.2f}% {c['order_rate']:>13.2f}% │ {a_or_d:>+9.2f}pp {b_or_d:>+9.2f}pp │ {'':>8} {'':>8}")

    # ITT 人均饮品实收 (核心指标)
    a_rd = (a['itt_revenue'] / c['itt_revenue'] - 1) * 100 if c['itt_revenue'] > 0 else 0
    b_rd = (b['itt_revenue'] / c['itt_revenue'] - 1) * 100 if c['itt_revenue'] > 0 else 0
    ca_str = f"{col_a.get('rev',''):>+7.1f}%" if 'rev' in col_a else f"{'':>8}"
    cb_str = f"{col_b.get('rev',''):>+7.1f}%" if 'rev' in col_b else f"{'':>8}"
    print(f"  {'★ITT人均饮品实收$':<22} {a['itt_revenue']:>14.4f} {b['itt_revenue']:>14.4f} {c['itt_revenue']:>14.4f} │ {a_rd:>+9.1f}% {b_rd:>+9.1f}% │ {ca_str} {cb_str}")

    # ITT 人均杯量
    a_cd = (a['itt_cups'] / c['itt_cups'] - 1) * 100 if c['itt_cups'] > 0 else 0
    b_cd = (b['itt_cups'] / c['itt_cups'] - 1) * 100 if c['itt_cups'] > 0 else 0
    print(f"  {'ITT人均杯量':<22} {a['itt_cups']:>14.4f} {b['itt_cups']:>14.4f} {c['itt_cups']:>14.4f} │ {a_cd:>+9.1f}% {b_cd:>+9.1f}% │ {'':>8} {'':>8}")

    # 单杯实收
    a_cpd = (a['avg_cup_price'] / c['avg_cup_price'] - 1) * 100 if c['avg_cup_price'] > 0 else 0
    b_cpd = (b['avg_cup_price'] / c['avg_cup_price'] - 1) * 100 if c['avg_cup_price'] > 0 else 0
    cc_str = f"{col_a.get('cup',''):>+7.1f}%" if 'cup' in col_a else f"{'':>8}"
    print(f"  {'单杯实收$':<22} {a['avg_cup_price']:>14.4f} {b['avg_cup_price']:>14.4f} {c['avg_cup_price']:>14.4f} │ {a_cpd:>+9.1f}% {b_cpd:>+9.1f}% │ {cc_str} {'':>8}")

    # 折扣率
    print(f"  {'折扣率':<22} {a['discount_rate']:>13.1%} {b['discount_rate']:>13.1%} {c['discount_rate']:>13.1%} │ {'':>10} {'':>10} │ {'':>8} {'':>8}")

# ---- 摘要对比表 ----
print(f"\n\n{'='*90}")
print(f"{'核心指标摘要对比: ITT人均饮品实收 diff%':^90}")
print(f"{'='*90}")
print(f"{'分层':<12} │ {'我方 A vs C':>12} │ {'同事 A vs C':>12} │ {'差距':>8} │ {'我方 B vs C':>12} │ {'同事 B vs C':>12} │ {'差距':>8}")
print("─" * 90)
for lc in all_lc:
    a = metrics.get(('A_涨价组1', lc))
    b = metrics.get(('B_涨价组2', lc))
    c = metrics.get(('C_对照组', lc))
    if not a or not b or not c:
        continue
    col_a = colleague.get(('A_涨价组1', lc), {})
    col_b = colleague.get(('B_涨价组2', lc), {})

    a_d = (a['itt_revenue'] / c['itt_revenue'] - 1) * 100 if c['itt_revenue'] > 0 else 0
    b_d = (b['itt_revenue'] / c['itt_revenue'] - 1) * 100 if c['itt_revenue'] > 0 else 0

    ca_r = col_a.get('rev')
    cb_r = col_b.get('rev')
    ga = f"{a_d - ca_r:>+7.1f}pp" if ca_r is not None else "  N/A"
    gb = f"{b_d - cb_r:>+7.1f}pp" if cb_r is not None else "  N/A"
    ca_s = f"{ca_r:>+11.1f}%" if ca_r is not None else f"{'N/A':>12}"
    cb_s = f"{cb_r:>+11.1f}%" if cb_r is not None else f"{'N/A':>12}"

    print(f"{lc:<12} │ {a_d:>+11.1f}% │ {ca_s} │ {ga} │ {b_d:>+11.1f}% │ {cb_s} │ {gb}")

print("\n✅ 分析完成!")
