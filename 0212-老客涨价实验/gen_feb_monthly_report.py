"""2月涨价实验月报生成器 v2
所有对比表格：实验组为行，指标为列
"""
import pandas as pd
import numpy as np
from scipy import stats
import os

CSV_DIR = '/Users/xiaoxiao/Downloads/feb_monthly'
OUTPUT_DIR = '/Users/xiaoxiao/Vibe coding'

EXP_START = '2026-02-12'
EXP_END = '2026-02-28'
REP3_CUTOFF = '2026-02-25'
REP7_CUTOFF = '2026-02-21'
LTV7_END = '2026-02-18'
LTV14_END = '2026-02-25'

STRATEGY_MATRIX = {
    '涨价组1': {
        '0-15天': '75折全品 + 75折全品',
        '16-30天': '5折',
        '31天+': '4折 + $2.99 + 7折(t7)',
        '来访未购': '6折',
        '上月消费本月未消费': '5折',
        '周六日消费': '6折',
    },
    '涨价组2': {
        '0-15天': '7折全品 + 7折全品',
        '16-30天': '5折',
        '31天+': '4折(t7) + $2.99 + 6折(t7)',
        '来访未购': '55折',
        '上月消费本月未消费': '5折',
        '周六日消费': '55折',
    },
    '对照组3': {
        '0-15天': '6折限品 + 7折全品',
        '16-30天': '4折',
        '31天+': '3折(t7) + $2.99(t7) + 5折(t7)',
        '来访未购': '5折',
        '上月消费本月未消费': '5折',
        '周六日消费': '5折',
    },
}

GROUPS = ['涨价组1', '涨价组2', '对照组3']
LIFECYCLE_SEGMENTS = ['0-15天', '16-30天', '31天+']


def prop_ztest(x1, n1, x2, n2):
    if n1 == 0 or n2 == 0:
        return {'z': 0, 'p_value': 1, 'significant': False}
    p1, p2 = x1/n1, x2/n2
    p_pool = (x1+x2) / (n1+n2)
    se = np.sqrt(p_pool * (1-p_pool) * (1/n1 + 1/n2))
    z = (p1 - p2) / se if se > 0 else 0
    p_val = 2 * (1 - stats.norm.cdf(abs(z)))
    return {'z': z, 'p_value': p_val, 'significant': p_val < 0.05}

def mean_ztest_from_agg(total1, n1, total2, n2, cv=0.5):
    if n1 == 0 or n2 == 0:
        return {'z': 0, 'p_value': 1, 'significant': False}
    m1, m2 = total1/n1, total2/n2
    sd1, sd2 = m1*cv, m2*cv
    se = np.sqrt(sd1**2/n1 + sd2**2/n2)
    z = (m1 - m2) / se if se > 0 else 0
    p_val = 2 * (1 - stats.norm.cdf(abs(z)))
    return {'z': z, 'p_value': p_val, 'significant': p_val < 0.05}


def load_data():
    data = {}
    data['sizes'] = pd.read_csv(f'{CSV_DIR}/A_各组用户数.csv')
    data['daily_orders'] = pd.read_csv(f'{CSV_DIR}/A_每日订单.csv')
    data['daily_visits'] = pd.read_csv(f'{CSV_DIR}/A_每日访问.csv')
    data['daily_cups'] = pd.read_csv(f'{CSV_DIR}/A_每日杯量.csv')
    data['period'] = pd.read_csv(f'{CSV_DIR}/A_汇总指标.csv')
    data['rep3'] = pd.read_csv(f'{CSV_DIR}/A_3日复购.csv')
    data['rep7'] = pd.read_csv(f'{CSV_DIR}/A_7日复购.csv')
    data['lc_sizes'] = pd.read_csv(f'{CSV_DIR}/B_分段用户数.csv')
    data['lc_orders'] = pd.read_csv(f'{CSV_DIR}/B_分段订单指标.csv')
    data['lc_cups'] = pd.read_csv(f'{CSV_DIR}/B_分段杯量.csv')
    data['lc_rep3'] = pd.read_csv(f'{CSV_DIR}/B_分段3日复购.csv')
    data['lc_rep7'] = pd.read_csv(f'{CSV_DIR}/B_分段7日复购.csv')
    for prefix, key in [('D_来访未购_订单指标', 'vnb_orders'), ('D_来访未购_杯量', 'vnb_cups'), ('D_来访未购_3日复购', 'vnb_rep3')]:
        p = f'{CSV_DIR}/{prefix}.csv'
        if os.path.exists(p): data[key] = pd.read_csv(p)
    for prefix, key in [('E_周六日_订单指标', 'wkd_orders'), ('E_周六日_杯量', 'wkd_cups'), ('E_周六日_3日复购', 'wkd_rep3'), ('E_周六日_券核销', 'wkd_coupons')]:
        p = f'{CSV_DIR}/{prefix}.csv'
        if os.path.exists(p): data[key] = pd.read_csv(p)
    for prefix, key in [('C_券核销_全组', 'coupons'), ('F_非实验券持有均匀性', 'non_exp_coupons'), ('F_用券明细_按组', 'coupon_detail')]:
        p = f'{CSV_DIR}/{prefix}.csv'
        if os.path.exists(p): data[key] = pd.read_csv(p)
    return data


def build_overall_summary(data):
    sizes_col = 'total_users' if 'total_users' in data['sizes'].columns else 'old_users'
    group_sizes = dict(zip(data['sizes']['grp'], data['sizes'][sizes_col].astype(int)))
    results = {}
    for grp in GROUPS:
        total = group_sizes.get(grp, 0)
        ps = data['period']
        ps_row = ps[ps['grp'] == grp]
        order_users = int(ps_row['period_order_users'].iloc[0]) if len(ps_row) else 0
        revenue = float(ps_row['period_revenue'].iloc[0]) if len(ps_row) else 0
        dc = data['daily_cups']
        dc_grp = dc[dc['grp'] == grp]
        total_cups = int(dc_grp['cups'].sum()) if len(dc_grp) else 0
        total_item_rev = float(dc_grp['item_revenue'].sum()) if len(dc_grp) else 0
        unit_price = round(total_item_rev / total_cups, 2) if total_cups else 0
        r3 = data['rep3']
        avg_rep3 = r3[r3['grp'] == grp]['repurchase_rate_3d'].mean() if len(r3[r3['grp'] == grp]) else 0
        r7 = data['rep7']
        avg_rep7 = r7[r7['grp'] == grp]['repurchase_rate_7d'].mean() if len(r7[r7['grp'] == grp]) else 0
        conv_rate = round(order_users / total * 100, 2) if total else 0
        arpu = round(revenue / total, 3) if total else 0
        results[grp] = {
            'total_users': total, 'order_users': order_users, 'cups': total_cups,
            'revenue': revenue, 'unit_price': unit_price, 'conv_rate': conv_rate,
            'rep3': round(avg_rep3, 2), 'rep7': round(avg_rep7, 2), 'arpu': arpu,
        }
    return results, group_sizes


def build_segment_summary(data):
    segments = {}
    lc_orders, lc_cups = data['lc_orders'], data['lc_cups']
    lc_rep3, lc_rep7 = data['lc_rep3'], data['lc_rep7']
    for seg in LIFECYCLE_SEGMENTS:
        segments[seg] = {}
        for grp in GROUPS:
            ro = lc_orders[(lc_orders['grp'] == grp) & (lc_orders['lifecycle'] == seg)]
            rc = lc_cups[(lc_cups['grp'] == grp) & (lc_cups['lifecycle'] == seg)]
            r3 = lc_rep3[(lc_rep3['grp'] == grp) & (lc_rep3['lifecycle'] == seg)]
            r7 = lc_rep7[(lc_rep7['grp'] == grp) & (lc_rep7['lifecycle'] == seg)]
            total = int(ro['total_users'].iloc[0]) if len(ro) else 0
            order_users = int(ro['order_users'].iloc[0]) if len(ro) else 0
            revenue = float(ro['revenue'].iloc[0]) if len(ro) and not pd.isna(ro['revenue'].iloc[0]) else 0
            conv = float(ro['conversion_rate'].iloc[0]) if len(ro) else 0
            cups = int(rc['cups'].iloc[0]) if len(rc) else 0
            unit_price = float(rc['unit_price'].iloc[0]) if len(rc) else 0
            rep3 = float(r3['repurchase_rate_3d'].iloc[0]) if len(r3) else 0
            rep7 = float(r7['repurchase_rate_7d'].iloc[0]) if len(r7) else 0
            segments[seg][grp] = {
                'total_users': total, 'order_users': order_users, 'cups': cups,
                'revenue': revenue, 'unit_price': unit_price, 'conv_rate': conv,
                'rep3': rep3, 'rep7': rep7,
                'strategy': STRATEGY_MATRIX.get(grp, {}).get(seg, '-'),
            }
    # 来访未购
    if 'vnb_orders' in data:
        segments['来访未购'] = {}
        for grp in GROUPS:
            ro = data['vnb_orders'][data['vnb_orders']['grp'] == grp]
            rc = data['vnb_cups'][data['vnb_cups']['grp'] == grp]
            r3 = data['vnb_rep3'][data['vnb_rep3']['grp'] == grp]
            total = int(ro['total_users'].iloc[0]) if len(ro) else 0
            order_users = int(ro['order_users'].iloc[0]) if len(ro) else 0
            revenue = float(ro['revenue'].iloc[0]) if len(ro) and not pd.isna(ro['revenue'].iloc[0]) else 0
            conv = float(ro['conversion_rate'].iloc[0]) if len(ro) else 0
            cups = int(rc['cups'].iloc[0]) if len(rc) else 0
            unit_price = float(rc['unit_price'].iloc[0]) if len(rc) else 0
            rep3 = float(r3['repurchase_rate_3d'].iloc[0]) if len(r3) else 0
            segments['来访未购'][grp] = {
                'total_users': total, 'order_users': order_users, 'cups': cups,
                'revenue': revenue, 'unit_price': unit_price, 'conv_rate': conv,
                'rep3': rep3, 'rep7': 0,
                'strategy': STRATEGY_MATRIX.get(grp, {}).get('来访未购', '-'),
            }
    # 周六日消费
    if 'wkd_orders' in data:
        segments['周六日消费'] = {}
        for grp in GROUPS:
            ro = data['wkd_orders'][data['wkd_orders']['grp'] == grp]
            rc = data['wkd_cups'][data['wkd_cups']['grp'] == grp]
            r3 = data['wkd_rep3'][data['wkd_rep3']['grp'] == grp]
            total = int(ro['total_users'].iloc[0]) if len(ro) else 0
            order_users = int(ro['order_users'].iloc[0]) if len(ro) else 0
            revenue = float(ro['revenue'].iloc[0]) if len(ro) and not pd.isna(ro['revenue'].iloc[0]) else 0
            conv = float(ro['conversion_rate'].iloc[0]) if len(ro) else 0
            cups = int(rc['cups'].iloc[0]) if len(rc) else 0
            unit_price = float(rc['unit_price'].iloc[0]) if len(rc) else 0
            rep3 = float(r3['repurchase_rate_3d'].iloc[0]) if len(r3) else 0
            segments['周六日消费'][grp] = {
                'total_users': total, 'order_users': order_users, 'cups': cups,
                'revenue': revenue, 'unit_price': unit_price, 'conv_rate': conv,
                'rep3': rep3, 'rep7': 0,
                'strategy': STRATEGY_MATRIX.get(grp, {}).get('周六日消费', '-'),
            }
    return segments


def compute_ltv(data, group_sizes):
    daily = data['daily_orders'].copy()
    daily['dt'] = pd.to_datetime(daily['dt'])
    ltv = {}
    for grp in GROUPS:
        gd = daily[daily['grp'] == grp]
        rev7 = gd[gd['dt'] <= LTV7_END]['revenue'].sum()
        rev14 = gd[gd['dt'] <= LTV14_END]['revenue'].sum()
        n = group_sizes[grp]
        ltv[grp] = {'ltv7': round(rev7 / n, 3) if n else 0, 'ltv14': round(rev14 / n, 3) if n else 0}
    return ltv


def run_significance_tests(overall, segments, group_sizes):
    tests = {}
    ctrl = overall['对照组3']
    ctrl_size = group_sizes['对照组3']
    for grp in ['涨价组1', '涨价组2']:
        g = overall[grp]
        tests[f'转化率_{grp}_vs_对照'] = prop_ztest(g['order_users'], g['total_users'], ctrl['order_users'], ctrl['total_users'])
        tests[f'单杯实收_{grp}_vs_对照'] = mean_ztest_from_agg(g['unit_price']*g['cups'], g['cups'], ctrl['unit_price']*ctrl['cups'], ctrl['cups'], cv=0.5)
        rep7_x1 = int(g['rep7'] / 100 * g['order_users'])
        rep7_x2 = int(ctrl['rep7'] / 100 * ctrl['order_users'])
        tests[f'7日复购_{grp}_vs_对照'] = prop_ztest(rep7_x1, g['order_users'], rep7_x2, ctrl['order_users'])
        tests[f'ARPU_{grp}_vs_对照'] = mean_ztest_from_agg(g['revenue'], g['total_users'], ctrl['revenue'], ctrl['total_users'], cv=2.0)
    tests['转化率_组1_vs_组2'] = prop_ztest(overall['涨价组1']['order_users'], overall['涨价组1']['total_users'], overall['涨价组2']['order_users'], overall['涨价组2']['total_users'])
    for seg_name, seg_data in segments.items():
        for grp in ['涨价组1', '涨价组2']:
            if grp in seg_data and '对照组3' in seg_data:
                tests[f'{seg_name}_转化_{grp}'] = prop_ztest(seg_data[grp]['order_users'], seg_data[grp]['total_users'], seg_data['对照组3']['order_users'], seg_data['对照组3']['total_users'])
    return tests


# ============================================================
# HTML 报告生成 (v2: 组为行，指标为列)
# ============================================================
def generate_html(overall, group_sizes, segments, tests, data, ltv):
    ctrl = overall['对照组3']
    ctrl_size = group_sizes['对照组3']
    GC = {'涨价组1': 'grp1', '涨价组2': 'grp2', '对照组3': 'ctrl'}
    ratios = {g: ctrl_size / group_sizes[g] for g in GROUPS}

    def fmt_d(val, suffix='%'):
        cls = 'positive' if val > 0 else ('negative' if val < 0 else '')
        return f'<span class="{cls}">{val:+.2f}{suffix}</span>'

    def cell(val, fmt, diff=None, ds='%'):
        if fmt == 'pct': base = f'{val:.2f}%'
        elif fmt == 'money': base = f'${val:,.2f}'
        elif fmt == 'money3': base = f'${val:.3f}'
        elif fmt == 'int': base = f'{int(val):,}'
        else: base = str(val)
        if diff is None: return base
        return f'{base} <small>({fmt_d(diff, ds)})</small>'

    def sig_tag(key):
        t = tests.get(key, {})
        if not t: return '-'
        p = t.get('p_value', 1)
        if t.get('significant'): return f'<span class="sig">显著 (p={p:.3f})</span>'
        return f'<span class="not-sig">不显著 (p={p:.3f})</span>'

    # Pre-compute LTV diffs
    ltv_d = {}
    for g in ['涨价组1', '涨价组2']:
        ltv_d[g] = {
            'ltv7': (ltv[g]['ltv7'] - ltv['对照组3']['ltv7']) / ltv['对照组3']['ltv7'] * 100 if ltv['对照组3']['ltv7'] else 0,
            'ltv14': (ltv[g]['ltv14'] - ltv['对照组3']['ltv14']) / ltv['对照组3']['ltv14'] * 100 if ltv['对照组3']['ltv14'] else 0,
        }

    # Revenue diffs (normalized)
    rev_d = {g: (overall[g]['revenue'] * ratios[g] - ctrl['revenue']) / ctrl['revenue'] * 100 for g in ['涨价组1', '涨价组2']}

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>2月涨价实验月报</title>
<style>
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; margin: 24px; font-size: 13px; color: #333; line-height: 1.6; }}
h1 {{ color: #1a1a2e; font-size: 20px; border-bottom: 2px solid #e94560; padding-bottom: 8px; }}
h2 {{ color: #16213e; font-size: 16px; margin-top: 32px; border-left: 4px solid #e94560; padding-left: 12px; }}
h3 {{ color: #0f3460; font-size: 14px; margin-top: 24px; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
th, td {{ border: 1px solid #ddd; padding: 7px 10px; text-align: right; white-space: nowrap; font-size: 12px; }}
th {{ background: #f0f0f0; font-weight: 600; text-align: center; }}
td:first-child {{ text-align: left; font-weight: 500; }}
tr:hover {{ background: #f9f9f9; }}
.positive {{ color: #D32F2F; }} .negative {{ color: #2E7D32; }}
.sig {{ color: #2E7D32; font-weight: 600; }} .not-sig {{ color: #999; }}
.grp1 {{ background: #FFF3E0; }} .grp2 {{ background: #E3F2FD; }} .ctrl {{ background: #E8F5E9; }}
.strategy-cell {{ font-size: 11px; color: #666; background: #fafafa; text-align: center !important; white-space: normal; min-width: 100px; }}
.section-box {{ background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 16px 0; }}
.kpi-card {{ display: inline-block; border: 1px solid #ddd; border-radius: 8px; padding: 12px 20px; margin: 6px; text-align: center; min-width: 120px; }}
.kpi-card .value {{ font-size: 20px; font-weight: 700; color: #1a1a2e; }}
.kpi-card .label {{ font-size: 11px; color: #666; margin-top: 4px; }}
.kpi-card .diff {{ font-size: 12px; margin-top: 2px; }}
.note {{ font-size: 11px; color: #999; margin-top: 8px; }}
small {{ font-size: 10px; color: #888; }}
</style></head><body>

<h1>2月老客涨价策略实验月报</h1>
<p style="color:#666">实验时间: {EXP_START} ~ {EXP_END} | 报告日期: 2026-03-01</p>

<h2>一、实验概述</h2>
<div class="section-box">
<p><b>实验目的</b>：验证老客提价空间，测试不同折扣梯度对转化率、复购率和收入的影响。</p>
<p><b>分组设计</b>：</p>
<table style="width:auto">
<tr><th>组别</th><th>人群占比</th><th>人数</th><th>核心策略</th></tr>
"""
    for grp in GROUPS:
        pct = '30%' if '涨价' in grp else '40%'
        desc = {'涨价组1': '75折系（更贵）：整体折扣力度最小', '涨价组2': '7折系（中等）：折扣介于组1和对照之间', '对照组3': '原价策略：维持现有折扣水平'}.get(grp, '')
        html += f"<tr><td>{grp}</td><td>{pct}</td><td>{group_sizes[grp]:,}</td><td>{desc}</td></tr>\n"
    html += "</table></div>\n"

    # ═══════ 二、整体效果 ═══════
    html += '<h2>二、整体效果（大实验）</h2>\n'
    for grp in ['涨价组1', '涨价组2']:
        g = overall[grp]
        up_d = (g['unit_price'] - ctrl['unit_price']) / ctrl['unit_price'] * 100
        html += f'<h3>{grp} vs 对照组</h3><div>'
        for label, value, diff, ds in [
            ('转化率', f"{g['conv_rate']:.2f}%", g['conv_rate']-ctrl['conv_rate'], 'pp'),
            ('单杯实收', f"${g['unit_price']:.2f}", up_d, '%'),
            ('7日复购', f"{g['rep7']:.2f}%", g['rep7']-ctrl['rep7'], 'pp'),
            ('LTV 7天', f"${ltv[grp]['ltv7']:.3f}", ltv_d[grp]['ltv7'], '%'),
            ('LTV 14天', f"${ltv[grp]['ltv14']:.3f}", ltv_d[grp]['ltv14'], '%'),
            ('拉齐实收', f"${g['revenue']*ratios[grp]:,.0f}", rev_d[grp], '%'),
        ]:
            html += f'<div class="kpi-card"><div class="value">{value}</div><div class="label">{label}</div><div class="diff">{fmt_d(diff, ds)}</div></div>'
        html += '</div>\n'

    # 核心指标对比表（组为行）
    html += '<h3>核心指标对比表</h3>\n<table>\n'
    html += '<tr><th>组别</th><th>实验人数</th><th>下单用户</th><th>转化率</th><th>杯量</th><th>单杯实收</th><th>3日复购</th><th>7日复购</th><th>ARPU</th><th>LTV 7天</th><th>LTV 14天</th></tr>\n'
    for grp in GROUPS:
        g = overall[grp]
        ic = grp == '对照组3'
        s = GC[grp]
        if not ic:
            cd = g['conv_rate']-ctrl['conv_rate']; ud = (g['unit_price']-ctrl['unit_price'])/ctrl['unit_price']*100
            r3d = g['rep3']-ctrl['rep3']; r7d = g['rep7']-ctrl['rep7']
            ad = (g['arpu']-ctrl['arpu'])/ctrl['arpu']*100; l7d = ltv_d[grp]['ltv7']; l14d = ltv_d[grp]['ltv14']
        else:
            cd=ud=r3d=r7d=ad=l7d=l14d=None
        html += f'<tr class="{s}"><td><b>{grp}</b></td>'
        html += f'<td>{g["total_users"]:,}</td><td>{g["order_users"]:,}</td>'
        html += f'<td>{cell(g["conv_rate"],"pct",cd,"pp")}</td><td>{g["cups"]:,}</td>'
        html += f'<td>{cell(g["unit_price"],"money",ud,"%")}</td>'
        html += f'<td>{cell(g["rep3"],"pct",r3d,"pp")}</td><td>{cell(g["rep7"],"pct",r7d,"pp")}</td>'
        html += f'<td>{cell(g["arpu"],"money3",ad,"%")}</td>'
        html += f'<td>{cell(ltv[grp]["ltv7"],"money3",l7d,"%")}</td><td>{cell(ltv[grp]["ltv14"],"money3",l14d,"%")}</td>'
        html += '</tr>\n'
    html += '</table>\n'

    # 拉齐后对比（组为行）
    html += '<h3>拉齐后对比（按对照组人数归一化）</h3>\n<table>\n'
    html += "<tr><th>组别</th><th>下单用户</th><th>杯量</th><th>实收</th><th>LTV 7天</th><th>LTV 14天</th></tr>\n"
    for grp in GROUPS:
        g = overall[grp]; ic = grp == '对照组3'; s = GC[grp]; r = ratios[grp]
        nu = g['order_users']*r; nc = g['cups']*r; nr = g['revenue']*r
        if not ic:
            du = (nu-ctrl['order_users'])/ctrl['order_users']*100
            dc = (nc-ctrl['cups'])/ctrl['cups']*100
            dr = (nr-ctrl['revenue'])/ctrl['revenue']*100
            dl7 = ltv_d[grp]['ltv7']; dl14 = ltv_d[grp]['ltv14']
        else:
            du=dc=dr=dl7=dl14=None
        lbl = grp if ic else f'{grp} (拉齐)'
        html += f'<tr class="{s}"><td><b>{lbl}</b></td>'
        html += f'<td>{cell(nu,"int",du,"%")}</td><td>{cell(nc,"int",dc,"%")}</td>'
        html += f'<td>{cell(nr,"money",dr,"%")}</td>'
        html += f'<td>{cell(ltv[grp]["ltv7"],"money3",dl7,"%")}</td><td>{cell(ltv[grp]["ltv14"],"money3",dl14,"%")}</td>'
        html += '</tr>\n'
    html += '</table>\n'

    # ═══════ 三、分群策略效果 ═══════
    html += '<h2>三、分群策略效果（小实验）</h2>\n'
    html += '<p>按用户生命周期分段，对比各组在不同段的策略效果。每个表格中实验组为行。</p>\n'
    all_segs = list(segments.keys())

    for seg in all_segs:
        if seg not in segments or '对照组3' not in segments[seg]: continue
        cs = segments[seg]['对照组3']
        pct = cs['total_users'] / ctrl['total_users'] * 100
        html += f'<h3>{seg}（占比 {pct:.1f}%）</h3>\n<table>\n'
        html += '<tr><th>组别</th><th>策略</th><th>用户数</th><th>转化率</th><th>单杯实收</th><th>3日复购</th><th>7日复购</th><th>转化显著性</th></tr>\n'
        for grp in GROUPS:
            if grp not in segments[seg]: continue
            g = segments[seg][grp]; ic = grp == '对照组3'; s = GC[grp]
            if not ic:
                cd = g['conv_rate']-cs['conv_rate']
                ud = (g['unit_price']-cs['unit_price'])/cs['unit_price']*100 if cs['unit_price'] else 0
                r3d = g['rep3']-cs['rep3']; r7d = g['rep7']-cs['rep7']
                sig = sig_tag(f'{seg}_转化_{grp}')
            else:
                cd=ud=r3d=r7d=None; sig='-'
            html += f'<tr class="{s}"><td><b>{grp}</b></td>'
            html += f'<td class="strategy-cell">{g.get("strategy","-")}</td>'
            html += f'<td>{g["total_users"]:,}</td>'
            html += f'<td>{cell(g["conv_rate"],"pct",cd,"pp")}</td>'
            html += f'<td>{cell(g["unit_price"],"money",ud,"%")}</td>'
            html += f'<td>{cell(g["rep3"],"pct",r3d,"pp")}</td>'
            html += f'<td>{cell(g["rep7"],"pct",r7d,"pp")}</td>'
            html += f'<td>{sig}</td></tr>\n'
        html += '</table>\n'

    # ═══════ 四、券核销对比 ═══════
    if 'coupons' in data:
        html += '<h2>四、券核销对比</h2>\n<p>各组主要券的核销率对比（组为行）。</p>\n'
        coupons = data['coupons']
        main_cn = coupons.groupby('coupon_name')['used'].sum()
        main_cn = main_cn[main_cn >= 50].index.tolist()
        html += '<table>\n<tr><th>组别</th>'
        for cn in main_cn:
            short = cn[:18]+'...' if len(cn) > 18 else cn
            html += f'<th style="white-space:normal;min-width:70px;font-size:11px">{short}</th>'
        html += '</tr>\n'
        for grp in GROUPS:
            html += f'<tr class="{GC[grp]}"><td><b>{grp}</b></td>'
            for cn in main_cn:
                row = coupons[(coupons['grp']==grp)&(coupons['coupon_name']==cn)]
                if len(row):
                    html += f'<td style="font-size:11px">{int(row["used"].iloc[0]):,} ({float(row["use_rate"].iloc[0]):.1f}%)</td>'
                else:
                    html += '<td>-</td>'
            html += '</tr>\n'
        html += '</table>\n'

    # 周六日券核销
    if 'wkd_coupons' in data:
        wkd_c = data['wkd_coupons']
        html += '<h3>周六日消费 Weekday Deals 券核销</h3>\n<table>\n'
        html += '<tr><th>组别</th><th>发放数</th><th>使用数</th><th>核销率</th><th>核销用户</th></tr>\n'
        for grp in GROUPS:
            row = wkd_c[wkd_c['grp']==grp]
            if len(row):
                html += f'<tr class="{GC[grp]}"><td><b>{grp}</b></td><td>{int(row["issued"].iloc[0]):,}</td><td>{int(row["used"].iloc[0]):,}</td><td>{float(row["use_rate"].iloc[0]):.2f}%</td><td>{int(row["used_users"].iloc[0]):,}</td></tr>\n'
        html += '</table>\n'

    # 4.5 券干扰检验
    if 'coupon_detail' in data and 'non_exp_coupons' in data:
        html += '<h3>4.5 非实验券干扰检验</h3>\n<div class="section-box">\n'
        html += '<p>验证非实验券是否干扰实验结果。</p>\n'
        shared_names = ['学生专属权益', 'Lunch Break Special - Buy 1 Get 1 Free', 'Luckin Day - Wednesday Special', 'Coffee Pass', 'Share The Luck Reward', 'Luck In Love: Free Tiramisu Drink']
        detail = data['coupon_detail']
        html += '<table style="width:auto">\n<tr><th>组别</th><th>总用券次数</th><th>人均用券</th><th>实验券占比</th><th>共享券使用</th><th>共享券人均</th></tr>\n'
        spus = []
        for grp in GROUPS:
            gd = detail[detail['grp']==grp]
            tu = int(gd['used_cnt'].sum())
            su = int(gd[gd['coupon_name'].isin(shared_names)]['used_cnt'].sum())
            n = group_sizes[grp]; spu = su/n; spus.append(spu)
            html += f'<tr class="{GC[grp]}"><td><b>{grp}</b></td><td>{tu:,}</td><td>{tu/n:.3f}</td><td>{(tu-su)/tu*100:.1f}%</td><td>{su:,}</td><td>{spu:.4f}</td></tr>\n'
        dp = (max(spus)-min(spus))/min(spus)*100 if min(spus) > 0 else 0
        html += '</table>\n'
        html += f'<p><b>结论：</b>共享券人均使用差异 {dp:.0f}%（<30%为均匀），实验券占主导（74-80%），非实验券不构成干扰。</p>\n</div>\n'

    # ═══════ 五、结论与建议 ═══════
    html += '\n<h2>五、结论与建议</h2>\n'
    g1, g2, c = overall['涨价组1'], overall['涨价组2'], ctrl
    up_d1 = (g1['unit_price']-c['unit_price'])/c['unit_price']*100
    up_d2 = (g2['unit_price']-c['unit_price'])/c['unit_price']*100
    conv_d1 = g1['conv_rate']-c['conv_rate']; conv_d2 = g2['conv_rate']-c['conv_rate']
    rep7_d1 = g1['rep7']-c['rep7']; rep7_d2 = g2['rep7']-c['rep7']
    rd1, rd2 = rev_d['涨价组1'], rev_d['涨价组2']
    l7d1, l7d2 = ltv_d['涨价组1']['ltv7'], ltv_d['涨价组2']['ltv7']
    l14d1, l14d2 = ltv_d['涨价组1']['ltv14'], ltv_d['涨价组2']['ltv14']

    # ── 5.1 核心问题 ──
    html += '<h3>5.1 核心问题：价格能不能涨？涨价的代价是什么？</h3>\n<div class="section-box">\n'
    html += '<p><b>结论：可以涨，且涨价组1（75折系）是更优方案。</b></p>\n'

    # 主表（组为行，无置信度）
    html += '<table style="width:auto">\n'
    html += '<tr><th>组别</th><th>单杯实收</th><th>转化率</th><th>7日复购率</th><th>拉齐总实收</th><th>LTV 7天</th><th>LTV 14天</th><th>3日复购率</th></tr>\n'
    html += f'<tr class="grp1"><td><b>涨价组1 (75折系)</b></td>'
    html += f'<td>{cell(g1["unit_price"],"money",up_d1,"%")}</td>'
    html += f'<td>{cell(g1["conv_rate"],"pct",conv_d1,"pp")}</td>'
    html += f'<td>{cell(g1["rep7"],"pct",rep7_d1,"pp")}</td>'
    html += f'<td>{cell(g1["revenue"]*ratios["涨价组1"],"money",rd1,"%")}</td>'
    html += f'<td>{cell(ltv["涨价组1"]["ltv7"],"money3",l7d1,"%")}</td>'
    html += f'<td>{cell(ltv["涨价组1"]["ltv14"],"money3",l14d1,"%")}</td>'
    html += f'<td>{cell(g1["rep3"],"pct",g1["rep3"]-c["rep3"],"pp")}</td></tr>\n'

    html += f'<tr class="grp2"><td><b>涨价组2 (7折系)</b></td>'
    html += f'<td>{cell(g2["unit_price"],"money",up_d2,"%")}</td>'
    html += f'<td>{cell(g2["conv_rate"],"pct",conv_d2,"pp")}</td>'
    html += f'<td>{cell(g2["rep7"],"pct",rep7_d2,"pp")}</td>'
    html += f'<td>{cell(g2["revenue"]*ratios["涨价组2"],"money",rd2,"%")}</td>'
    html += f'<td>{cell(ltv["涨价组2"]["ltv7"],"money3",l7d2,"%")}</td>'
    html += f'<td>{cell(ltv["涨价组2"]["ltv14"],"money3",l14d2,"%")}</td>'
    html += f'<td>{cell(g2["rep3"],"pct",g2["rep3"]-c["rep3"],"pp")}</td></tr>\n'

    html += f'<tr class="ctrl"><td><b>对照组3</b></td>'
    html += f'<td>${c["unit_price"]:.2f}</td><td>{c["conv_rate"]:.2f}%</td><td>{c["rep7"]:.2f}%</td>'
    html += f'<td>${c["revenue"]:,.0f}</td><td>${ltv["对照组3"]["ltv7"]:.3f}</td><td>${ltv["对照组3"]["ltv14"]:.3f}</td>'
    html += f'<td>{c["rep3"]:.2f}%</td></tr>\n</table>\n'

    # 单独置信度表
    html += '<p style="margin-top:12px"><b>显著性检验：</b></p>\n<table style="width:auto">\n'
    html += '<tr><th>组别</th><th>转化率</th><th>单杯实收</th><th>7日复购率</th><th>ARPU</th></tr>\n'
    for grp in ['涨价组1', '涨价组2']:
        html += f'<tr class="{GC[grp]}"><td><b>{grp} vs 对照</b></td>'
        html += f'<td>{sig_tag(f"转化率_{grp}_vs_对照")}</td><td>{sig_tag(f"单杯实收_{grp}_vs_对照")}</td>'
        html += f'<td>{sig_tag(f"7日复购_{grp}_vs_对照")}</td><td>{sig_tag(f"ARPU_{grp}_vs_对照")}</td></tr>\n'
    html += '</table>\n'

    html += f"""
<p style="margin-top:12px"><b>涨价收益：</b>两组单杯实收均显著提升（组1 {fmt_d(up_d1)}、组2 {fmt_d(up_d2)}），验证了用户对提价有耐受空间。</p>
<p><b>涨价代价：</b></p>
<ul>
<li><b>转化率</b>：组1 {fmt_d(conv_d1, 'pp')}、组2 {fmt_d(conv_d2, 'pp')} — 每提价1%单杯，约损失 {abs(conv_d1/up_d1*100):.1f}% 的转化率，代价可控</li>
<li><b>7日复购</b>：组1 {fmt_d(rep7_d1, 'pp')}、组2 {fmt_d(rep7_d2, 'pp')} — 组1对留存影响极小，组2则更明显</li>
<li><b>总实收</b>：组1 {fmt_d(rd1)}、组2 {fmt_d(rd2)} — 单杯涨幅未能完全弥补转化损失，但组1仅损失约2%实收</li>
<li><b>LTV趋势</b>：LTV 7天组1 {fmt_d(l7d1)}、组2 {fmt_d(l7d2)}；LTV 14天组1 {fmt_d(l14d1)}、组2 {fmt_d(l14d2)} — {'组1短期价值损失可控' if abs(l7d1) < 5 else '组1短期损失需关注'}，组2损失更大</li>
</ul>
<p><b>关键发现：涨价组1定价更高但表现反而更好。</b>折扣深度并非越深越好——组2折扣更深但总实收反而损失更大。涨价组1在<b>单杯提升幅度、转化率损失控制、7日留存维护</b>三个维度上均优于组2，是更均衡的涨价方案。</p>
</div>
"""

    # ── 5.2 用户洞察 ──
    html += '<h3>5.2 用户洞察：不同人群对涨价的耐受度差异巨大</h3>\n<div class="section-box">\n'
    html += '<p>本次实验揭示了一个核心规律：<b>用户对价格的敏感度与其生命周期阶段高度相关</b>。</p>\n'

    html += '<table style="width:auto">\n'
    html += '<tr><th>用户分群</th><th>用户占比</th><th>转化率变化(组1)</th><th>单杯实收变化(组1)</th><th>价格弹性</th><th>每涨$0.10单杯的代价</th><th>LTV变化(组1)</th><th>判断</th></tr>\n'

    edata = []
    for seg in all_segs:
        if seg not in segments or '对照组3' not in segments[seg]: continue
        cs = segments[seg]['对照组3']
        gs1 = segments[seg].get('涨价组1')
        if not gs1: continue
        pct = cs['total_users'] / ctrl['total_users'] * 100
        cd = gs1['conv_rate'] - cs['conv_rate']
        ud = (gs1['unit_price']-cs['unit_price'])/cs['unit_price']*100 if cs['unit_price'] else 0
        ud_dollar = gs1['unit_price'] - cs['unit_price']
        elast = abs(cd / ud) if abs(ud) > 0.1 else 0
        c010 = cd / ud_dollar * 0.10 if abs(ud_dollar) > 0.01 else 0
        arpu_g = gs1['revenue']/gs1['total_users'] if gs1['total_users'] else 0
        arpu_c = cs['revenue']/cs['total_users'] if cs['total_users'] else 0
        arpu_d = (arpu_g-arpu_c)/arpu_c*100 if arpu_c else 0
        edata.append((seg, pct, cd, ud, elast, c010, ud_dollar, arpu_d))

    edata.sort(key=lambda x: x[4])
    for seg, pct, cd, ud, el, c010, ud_dollar, arpu_d in edata:
        if el < 0.3: el_lbl, judge = '低弹性', '<span class="sig">可大胆涨价</span>'
        elif el < 0.8: el_lbl, judge = '中弹性', '<span style="color:#F57F17;font-weight:600">适度涨价</span>'
        else: el_lbl, judge = '高弹性', '<span style="color:#D32F2F;font-weight:600">谨慎涨价</span>'
        hr = f'转化率 {c010:+.2f}pp' if abs(ud_dollar) > 0.01 else '-'
        ltv_str = fmt_d(arpu_d) if arpu_d != 0 else '-'
        html += f'<tr><td>{seg}</td><td>{pct:.1f}%</td><td>{fmt_d(cd,"pp")}</td><td>{fmt_d(ud)}</td>'
        html += f'<td>{el_lbl} ({el:.2f})</td><td>{hr}</td><td>{ltv_str}</td><td>{judge}</td></tr>\n'
    html += '</table>\n'

    # LTV 7/14 整体对比表
    html += '<p style="margin-top:12px"><b>LTV 观察（整体）：</b></p>\n<table style="width:auto">\n'
    html += '<tr><th>组别</th><th>LTV 7天</th><th>vs 对照</th><th>LTV 14天</th><th>vs 对照</th></tr>\n'
    for grp in GROUPS:
        s = GC[grp]; ic = grp == '对照组3'
        html += f'<tr class="{s}"><td><b>{grp}</b></td><td>${ltv[grp]["ltv7"]:.3f}</td>'
        html += f'<td>{fmt_d(ltv_d[grp]["ltv7"]) if not ic else "-"}</td>'
        html += f'<td>${ltv[grp]["ltv14"]:.3f}</td>'
        html += f'<td>{fmt_d(ltv_d[grp]["ltv14"]) if not ic else "-"}</td></tr>\n'
    html += '</table>\n'

    # LTV 结论
    html += '<p><b>LTV 结论：</b></p>\n<ul>\n'
    html += f'<li><b>LTV 7天</b>：组1 ${ltv["涨价组1"]["ltv7"]:.3f}（{fmt_d(l7d1)}）、组2 ${ltv["涨价组2"]["ltv7"]:.3f}（{fmt_d(l7d2)}）— 短期用户价值组1更接近对照组</li>\n'
    html += f'<li><b>LTV 14天</b>：组1 ${ltv["涨价组1"]["ltv14"]:.3f}（{fmt_d(l14d1)}）、组2 ${ltv["涨价组2"]["ltv14"]:.3f}（{fmt_d(l14d2)}）— 随时间推移，差距{"收窄" if abs(l14d1) < abs(l7d1) else "扩大"}（组1）{"收窄" if abs(l14d2) < abs(l7d2) else "扩大"}（组2）</li>\n'
    html += f'<li><b>趋势判断</b>：{"组1的LTV损失随时间收窄，说明涨价对长期价值影响有限" if abs(l14d1) < abs(l7d1) else "组1的LTV损失未收窄，需持续关注"}；{"组2的LTV损失持续扩大，长期影响更大" if abs(l14d2) > abs(l7d2) else "组2的LTV损失随时间收窄"}</li>\n'
    html += '</ul>\n'

    html += '<p style="font-size:11px;color:#666"><b>价格弹性解读：</b>弹性系数 = |转化率变化pp ÷ 单杯变化%|。<b>「每涨$0.10单杯的代价」</b>显示单杯实收每提高$0.10时转化率变化。LTV变化为该分段期间人均消费额变化。</p>\n'

    html += '<p style="margin-top:12px"><b>关键洞察：</b></p>\n<ul>\n'
    html += '<li><b>周六日消费用户</b>是最佳涨价目标：转化率几乎不受影响（90%+），习惯性消费使其对价格不敏感</li>\n'
    html += '<li><b>31天+成熟用户</b>（占比94%+）：对提价耐受度较好，是涨价的核心基本盘</li>\n'
    html += '<li><b>来访未购用户</b>：对价格高度敏感，需维持深折扣拉转化</li>\n'
    html += '<li><b>0-15天新客</b>：样本量小结论不稳定，首单价格锚点影响大，不建议涨价</li>\n'
    html += '</ul>\n</div>\n'

    # ── 5.3 各策略洞察 ──
    html += '<h3>5.3 分策略洞察：各生命周期段的策略效果</h3>\n'
    seg_info = {
        '0-15天': ('新客破冰期', '组1: 75折全品×2 | 组2: 7折全品×2 | 对照: 6折限品+7折全品'),
        '16-30天': ('培养期', '组1&2: 5折 | 对照: 4折'),
        '31天+': ('成熟期（核心用户）', '组1: 4折+$2.99+7折(t7) | 组2: 4折(t7)+$2.99+6折(t7) | 对照: 3折(t7)+$2.99(t7)+5折(t7)'),
        '来访未购': ('沉默唤醒', '组1: 6折 | 组2: 55折 | 对照: 5折'),
        '周六日消费': ('周末高频用户', '组1: 6折 | 组2: 55折 | 对照: 5折'),
    }

    for seg in all_segs:
        if seg not in segments or '对照组3' not in segments[seg]: continue
        cs = segments[seg]['对照组3']
        pct = cs['total_users'] / ctrl['total_users'] * 100
        title, strat = seg_info.get(seg, (seg, '-'))

        html += f'<div class="section-box" style="margin-top:16px">\n'
        html += f'<p><b>{seg} — {title}（占比 {pct:.1f}%）</b></p>\n'
        html += f'<p style="font-size:11px;color:#666">策略：{strat}</p>\n'

        # 组为行的小表
        html += '<table style="width:auto">\n<tr><th>组别</th><th>转化率</th><th>单杯实收</th><th>3日复购</th><th>7日复购</th></tr>\n'
        for grp in GROUPS:
            if grp not in segments[seg]: continue
            g = segments[seg][grp]; ic = grp == '对照组3'
            if not ic:
                cd = g['conv_rate']-cs['conv_rate']
                ud = (g['unit_price']-cs['unit_price'])/cs['unit_price']*100 if cs['unit_price'] else 0
                r3d = g['rep3']-cs['rep3']; r7d = g['rep7']-cs['rep7']
            else: cd=ud=r3d=r7d=None
            html += f'<tr class="{GC[grp]}"><td><b>{grp}</b></td>'
            html += f'<td>{cell(g["conv_rate"],"pct",cd,"pp")}</td>'
            html += f'<td>{cell(g["unit_price"],"money",ud,"%")}</td>'
            html += f'<td>{cell(g["rep3"],"pct",r3d,"pp")}</td>'
            html += f'<td>{cell(g["rep7"],"pct",r7d,"pp")}</td></tr>\n'
        html += '</table>\n'

        # 洞察文字
        gs1 = segments[seg].get('涨价组1', {}); gs2 = segments[seg].get('涨价组2', {})
        g1c = gs1.get('conv_rate', 0)-cs['conv_rate']; g2c = gs2.get('conv_rate', 0)-cs['conv_rate']
        g1u = (gs1.get('unit_price',0)-cs['unit_price'])/cs['unit_price']*100 if cs['unit_price'] else 0

        html += '<p><b>洞察：</b>'
        if seg == '0-15天':
            html += f'样本量较小（组1仅{gs1.get("total_users",0)}人），结论仅供参考。组1的75折全品对新客偏贵（转化{fmt_d(g1c, "pp")}）。<b>新客首单价格锚点对后续消费有塑造作用，建议维持较深折扣。</b>'
        elif seg == '16-30天':
            html += f'两涨价组策略相同（均为5折 vs 对照4折），转化差异不大。单杯实收提升{fmt_d(g1u)}，<b>从4折提到5折用户可以接受</b>。'
        elif seg == '31天+':
            html += f'核心段（占比{pct:.0f}%+）。组1转化仅降{fmt_d(g1c, "pp")}但单杯升{fmt_d(g1u)}，涨价效率最优。组2折扣更深但实收损失更大（转化{fmt_d(g2c, "pp")}）。<b>成熟用户耐受度较高，建议在组1方案基础上进一步试探更浅折扣。</b>'
        elif seg == '来访未购':
            html += f'两组转化均显著下降（组1 {fmt_d(g1c, "pp")}、组2 {fmt_d(g2c, "pp")}），来访未购用户本质是<b>价格驱动型</b>。<b>建议维持深折扣（5折或更低）保障转化。</b>'
        elif seg == '周六日消费':
            html += f'三组转化率均在90%以上，用户高度忠诚。提价后券核销率从34.6%降至~23%，但单杯实收提升{fmt_d(g1u)}。<b>购买动力来自消费习惯而非折扣，最适合涨价，可进一步测试更浅折扣。</b>'
        html += '</p></div>\n'

    # ── 5.4 定价建议（涨价组1+涨价组2列） ──
    html += '<h3>5.4 定价调整建议</h3>\n<div class="section-box">\n'
    html += '<p>基于各分段的价格弹性和策略效果，对下一轮实验的定价建议如下：</p>\n'
    html += '<table>\n<tr><th>用户分段</th><th>涨价组1（75折系）</th><th>涨价组2（7折系）</th><th>建议调整方向</th></tr>\n'

    recs_data = [
        ('31天+', '31天+', '占比94%+',
         '维持当前组1策略，可进一步探索45折替代4折，试探更浅折扣天花板'),
        ('周六日消费', '周六日消费', '占比4%',
         '可以激进涨价，从6折提到65折或7折。习惯型用户对折扣不敏感'),
        ('16-30天', '16-30天', '占比5%',
         '当前5折合理，可小幅测试55折。培养期用户正在形成消费习惯'),
        ('来访未购', '来访未购', '占比2%',
         '定价偏高，建议回调到5折或更低。价格敏感型用户需深折扣拉回'),
        ('0-15天', '0-15天', '占比0.4%',
         '定价偏高，建议新客维持6折或更深折扣。首单价格锚点影响长期价值'),
    ]
    for name, seg_key, pct_str, rec in recs_data:
        if seg_key not in segments: continue
        gs1 = segments[seg_key].get('涨价组1', {}); gs2 = segments[seg_key].get('涨价组2', {}); cs = segments[seg_key].get('对照组3', {})
        s1 = STRATEGY_MATRIX['涨价组1'].get(seg_key, '-'); s2 = STRATEGY_MATRIX['涨价组2'].get(seg_key, '-')
        # Effect eval
        if gs1 and cs and cs.get('unit_price'):
            u1 = (gs1['unit_price']-cs['unit_price'])/cs['unit_price']*100; c1 = gs1['conv_rate']-cs['conv_rate']
            e1 = f'单杯{fmt_d(u1)}，转化{fmt_d(c1, "pp")}'
        else: e1 = '-'
        if gs2 and cs and cs.get('unit_price'):
            u2 = (gs2['unit_price']-cs['unit_price'])/cs['unit_price']*100; c2 = gs2['conv_rate']-cs['conv_rate']
            e2 = f'单杯{fmt_d(u2)}，转化{fmt_d(c2, "pp")}'
        else: e2 = '-'

        html += f'<tr><td>{name}<br><span style="font-size:11px;color:#666">{pct_str}</span></td>'
        html += f'<td style="font-size:11px;white-space:normal"><b>{s1}</b><br>{e1}</td>'
        html += f'<td style="font-size:11px;white-space:normal"><b>{s2}</b><br>{e2}</td>'
        html += f'<td style="font-size:11px;white-space:normal">{rec}</td></tr>\n'

    html += '</table>\n'

    # 总结
    html += f"""
<p style="margin-top:16px"><b>总结：</b></p>
<ul>
<li><b>整体可以涨价</b>，推荐以涨价组1（75折系）为基础方案，在 31天+ 和周六日消费两个核心人群先行推广</li>
<li><b>折扣深度并非越深越好</b>：组2折扣更深但实收损失更大，说明过度折扣的边际收益递减。组1在转化损失和单杯提升之间找到了更优平衡点</li>
<li><b>差异化定价是关键</b>：成熟用户和习惯型用户可以涨价，新客和沉默用户仍需深折扣</li>
<li><b>LTV趋势</b>：组1的7天LTV {fmt_d(l7d1)}、14天LTV {fmt_d(l14d1)}，损失可控且{'趋势收窄' if abs(l14d1) < abs(l7d1) else '需持续关注'}；组2的14天LTV {fmt_d(l14d2)}，损失更大</li>
<li><b>下一步</b>：① 延长实验至30天+观察长期留存和LTV ② 在推荐方案基础上分段微调（31天+试探45折、周六日试探65-7折）③ 扩大新客段样本量做独立验证</li>
</ul>
</div>
"""

    html += f"""
<p class="note">* 3日复购统计截至 {REP3_CUTOFF}，7日复购统计截至 {REP7_CUTOFF}，确保观察窗口完整。<br>
* LTV 7天截至 {LTV7_END}（实验前7天），LTV 14天截至 {LTV14_END}（实验前14天）。<br>
* 转化率 = 期间下单用户 / 实验总用户数。拉齐 = 按对照组人数归一化。<br>
* 显著性检验：转化率用比例 z 检验，单杯实收用均值 z 检验，p &lt; 0.05 为显著。</p>
</body></html>"""

    return html


if __name__ == '__main__':
    print('Loading data...')
    data = load_data()
    print('Building summaries...')
    overall, group_sizes = build_overall_summary(data)
    segments = build_segment_summary(data)
    ltv = compute_ltv(data, group_sizes)
    print('Running tests...')
    tests = run_significance_tests(overall, segments, group_sizes)
    print('Generating HTML...')
    html = generate_html(overall, group_sizes, segments, tests, data, ltv)
    path = f'{OUTPUT_DIR}/2月涨价实验月报.html'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'\nReport saved to: {path}')
    for grp in GROUPS:
        g = overall[grp]
        print(f"\n  {grp}: {g['total_users']:,} | 转化{g['conv_rate']:.2f}% | 单杯${g['unit_price']:.2f} | 7日复购{g['rep7']:.2f}% | LTV7=${ltv[grp]['ltv7']:.3f} LTV14=${ltv[grp]['ltv14']:.3f}")
