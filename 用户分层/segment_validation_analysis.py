"""分群小实验前置检验分析
读取基线数据 CSV，对每个分段做 SRM + 基线特征检验
"""
import pandas as pd
import numpy as np
from scipy import stats

CSV_DIR = '/Users/xiaoxiao/Downloads/feb_monthly'
OUTPUT_DIR = '/Users/xiaoxiao/Vibe coding'

# 预期分组比例
EXPECTED_RATIO = {'涨价组1': 0.3, '涨价组2': 0.3, '对照组3': 0.4}
GROUPS = ['涨价组1', '涨价组2', '对照组3']


def srm_test(counts, expected_ratios):
    """SRM检验：卡方拟合优度"""
    total = sum(counts.values())
    expected = {g: total * r for g, r in expected_ratios.items()}
    obs = [counts.get(g, 0) for g in GROUPS]
    exp = [expected.get(g, 0) for g in GROUPS]
    chi2, p_val = stats.chisquare(obs, exp)
    return {'chi2': chi2, 'p_value': p_val, 'significant': p_val < 0.05}


def prop_test_3groups(counts, totals):
    """3组比例检验（卡方独立性）"""
    contingency = np.array([
        [counts[g] for g in GROUPS],
        [totals[g] - counts[g] for g in GROUPS]
    ])
    if contingency.min() < 0 or contingency.sum(axis=1).min() == 0:
        return {'chi2': 0, 'p_value': 1, 'significant': False}
    try:
        chi2, p_val, dof, _ = stats.chi2_contingency(contingency)
    except ValueError:
        return {'chi2': 0, 'p_value': 1, 'significant': False}
    return {'chi2': chi2, 'p_value': p_val, 'significant': p_val < 0.05}


def mean_test_2groups(mean1, n1, mean2, n2, cv=0.5):
    """两组均值z检验"""
    if n1 == 0 or n2 == 0:
        return {'z': 0, 'p_value': 1}
    sd1, sd2 = mean1 * cv, mean2 * cv
    se = np.sqrt(sd1**2/n1 + sd2**2/n2)
    z = (mean1 - mean2) / se if se > 0 else 0
    p_val = 2 * (1 - stats.norm.cdf(abs(z)))
    return {'z': z, 'p_value': p_val}


def analyze_segment(seg_name, seg_data):
    """对单个分段做完整检验"""
    results = {'segment': seg_name}

    # 1. SRM 检验
    counts = {row['grp']: int(row['total_users']) for _, row in seg_data.iterrows()}
    srm = srm_test(counts, EXPECTED_RATIO)
    results['srm_chi2'] = srm['chi2']
    results['srm_p'] = srm['p_value']
    results['srm_pass'] = not srm['significant']

    # 2. 有购率检验
    active_counts = {row['grp']: int(row['active_users']) for _, row in seg_data.iterrows()}
    prop = prop_test_3groups(active_counts, counts)
    results['active_rate_chi2'] = prop['chi2']
    results['active_rate_p'] = prop['p_value']
    results['active_rate_pass'] = not prop['significant']

    # 3. 人均订单数对比（组1 vs 组2，组1 vs 对照，组2 vs 对照）
    comparisons = [('涨价组1', '对照组3'), ('涨价组2', '对照组3'), ('涨价组1', '涨价组2')]

    for g1, g2 in comparisons:
        r1 = seg_data[seg_data['grp'] == g1].iloc[0] if len(seg_data[seg_data['grp'] == g1]) else None
        r2 = seg_data[seg_data['grp'] == g2].iloc[0] if len(seg_data[seg_data['grp'] == g2]) else None
        if r1 is not None and r2 is not None:
            m1, n1 = float(r1['avg_orders']), int(r1['total_users'])
            m2, n2 = float(r2['avg_orders']), int(r2['total_users'])
            t = mean_test_2groups(m1, n1, m2, n2, cv=1.5)
            label = f'{g1[:3]}v{g2[:3]}'
            results[f'orders_{label}_p'] = t['p_value']

    # 4. 客单价对比
    for g1, g2 in comparisons:
        r1 = seg_data[seg_data['grp'] == g1].iloc[0] if len(seg_data[seg_data['grp'] == g1]) else None
        r2 = seg_data[seg_data['grp'] == g2].iloc[0] if len(seg_data[seg_data['grp'] == g2]) else None
        if r1 is not None and r2 is not None:
            m1_aov = float(r1['avg_aov']) if not pd.isna(r1['avg_aov']) else 0
            m2_aov = float(r2['avg_aov']) if not pd.isna(r2['avg_aov']) else 0
            n1_active = int(r1['active_users'])
            n2_active = int(r2['active_users'])
            t = mean_test_2groups(m1_aov, n1_active, m2_aov, n2_active, cv=0.5)
            label = f'{g1[:3]}v{g2[:3]}'
            results[f'aov_{label}_p'] = t['p_value']

    return results


def generate_html_report(all_results, baseline_df, vnb_baseline=None):
    """生成检验结果HTML报告"""

    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>分群前置检验报告</title>
<style>
body { font-family: -apple-system, sans-serif; margin: 24px; font-size: 13px; color: #333; }
h1 { font-size: 18px; border-bottom: 2px solid #1976D2; padding-bottom: 8px; }
h2 { font-size: 15px; margin-top: 28px; border-left: 4px solid #1976D2; padding-left: 12px; }
h3 { font-size: 13px; margin-top: 20px; }
table { border-collapse: collapse; margin: 10px 0; }
th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: right; font-size: 12px; }
th { background: #e3f2fd; text-align: center; }
td:first-child { text-align: left; font-weight: 500; }
.pass { color: #2E7D32; font-weight: 600; }
.fail { color: #D32F2F; font-weight: 600; }
.section { background: #f8f9fa; border-radius: 8px; padding: 14px; margin: 12px 0; }
.grp1 { background: #FFF3E0; }
.grp2 { background: #E3F2FD; }
.ctrl { background: #E8F5E9; }
</style></head><body>

<h1>0212涨价实验 - 分群前置检验报告</h1>
<p style="color:#666">检验内容：SRM + 基线消费特征（实验前90天）| 分群：按生命周期 + 来访未购</p>

<h2>一、检验逻辑</h2>
<div class="section">
<p>本实验将用户分为3个价格组（涨价组1/2 + 对照组3），然后根据生命周期交叉不同券策略。</p>
<p>由于分组是在用户层面完成（AB 分流），而非在生命周期层面分别分组，因此需要验证：</p>
<ul>
<li><b>SRM 检验</b>：每个生命周期段内，3组的用户数比例是否接近 30%:30%:40%</li>
<li><b>有购率检验</b>：3组在实验前90天的有购率是否无显著差异</li>
<li><b>人均订单 & 客单价</b>：3组的基线消费水平是否可比</li>
</ul>
<p>所有检验 p > 0.05 为通过（组间无显著差异）。</p>
</div>
"""

    # 二、基线数据展示
    html += "<h2>二、各分段基线数据</h2>\n"

    segments = baseline_df['lifecycle'].unique()
    for seg in sorted(segments):
        seg_data = baseline_df[baseline_df['lifecycle'] == seg]
        html += f"<h3>{seg}</h3>\n<table>\n"
        html += "<tr><th>组别</th><th>用户数</th><th>有购用户</th><th>有购率</th><th>人均订单</th><th>人均消费(有购)</th><th>平均客单价</th></tr>\n"
        for _, row in seg_data.iterrows():
            style = {'涨价组1': 'grp1', '涨价组2': 'grp2', '对照组3': 'ctrl'}.get(row['grp'], '')
            html += f"<tr class='{style}'>"
            html += f"<td>{row['grp']}</td>"
            html += f"<td>{int(row['total_users']):,}</td>"
            html += f"<td>{int(row['active_users']):,}</td>"
            html += f"<td>{row['active_rate']:.2f}%</td>"
            html += f"<td>{row['avg_orders']:.4f}</td>"
            avg_spend = row['avg_spend'] if not pd.isna(row['avg_spend']) else 0
            avg_aov = row['avg_aov'] if not pd.isna(row['avg_aov']) else 0
            html += f"<td>${avg_spend:.2f}</td>"
            html += f"<td>${avg_aov:.2f}</td>"
            html += "</tr>\n"
        html += "</table>\n"

    # 来访未购基线
    if vnb_baseline is not None:
        html += "<h3>来访未购</h3>\n<table>\n"
        html += "<tr><th>组别</th><th>用户数</th><th>有购用户</th><th>有购率</th><th>人均订单</th><th>人均消费(有购)</th><th>平均客单价</th></tr>\n"
        for _, row in vnb_baseline.iterrows():
            style = {'涨价组1': 'grp1', '涨价组2': 'grp2', '对照组3': 'ctrl'}.get(row['grp'], '')
            html += f"<tr class='{style}'>"
            html += f"<td>{row['grp']}</td>"
            html += f"<td>{int(row['total_users']):,}</td>"
            html += f"<td>{int(row['active_users']):,}</td>"
            html += f"<td>{row['active_rate']:.2f}%</td>"
            html += f"<td>{row['avg_orders']:.4f}</td>"
            avg_spend = row['avg_spend'] if not pd.isna(row['avg_spend']) else 0
            avg_aov = row['avg_aov'] if not pd.isna(row['avg_aov']) else 0
            html += f"<td>${avg_spend:.2f}</td>"
            html += f"<td>${avg_aov:.2f}</td>"
            html += "</tr>\n"
        html += "</table>\n"

    # 三、检验结果汇总
    html += "<h2>三、检验结果汇总</h2>\n<table>\n"
    html += "<tr><th>分段</th><th>SRM p值</th><th>SRM</th><th>有购率 p值</th><th>有购率</th><th>人均订单(最小p)</th><th>订单</th><th>客单价(最小p)</th><th>客单价</th></tr>\n"

    for r in all_results:
        seg = r['segment']
        srm_cls = 'pass' if r['srm_pass'] else 'fail'
        srm_label = 'PASS' if r['srm_pass'] else 'FAIL'
        ar_cls = 'pass' if r['active_rate_pass'] else 'fail'
        ar_label = 'PASS' if r['active_rate_pass'] else 'FAIL'

        # 找最小的 p 值 for orders and aov
        order_ps = [v for k, v in r.items() if k.startswith('orders_') and k.endswith('_p')]
        aov_ps = [v for k, v in r.items() if k.startswith('aov_') and k.endswith('_p')]
        min_order_p = min(order_ps) if order_ps else 1
        min_aov_p = min(aov_ps) if aov_ps else 1
        order_pass = min_order_p > 0.05
        aov_pass = min_aov_p > 0.05

        o_cls = 'pass' if order_pass else 'fail'
        a_cls = 'pass' if aov_pass else 'fail'

        html += f"<tr><td>{seg}</td>"
        html += f"<td>{r['srm_p']:.4f}</td><td class='{srm_cls}'>{srm_label}</td>"
        html += f"<td>{r['active_rate_p']:.4f}</td><td class='{ar_cls}'>{ar_label}</td>"
        html += f"<td>{min_order_p:.4f}</td><td class='{o_cls}'>{'PASS' if order_pass else 'FAIL'}</td>"
        html += f"<td>{min_aov_p:.4f}</td><td class='{a_cls}'>{'PASS' if aov_pass else 'FAIL'}</td>"
        html += "</tr>\n"

    html += "</table>\n"

    # 结论
    all_pass = all(
        r['srm_pass'] and r['active_rate_pass']
        for r in all_results
    )
    if all_pass:
        html += '<div class="section"><p class="pass">所有分段的 SRM 和有购率检验均通过，各组在各段内具有可比性，小实验结果可信。</p></div>'
    else:
        failed_segs = [r['segment'] for r in all_results if not (r['srm_pass'] and r['active_rate_pass'])]
        html += f'<div class="section"><p class="fail">以下分段存在检验不通过：{", ".join(failed_segs)}。需关注这些段的实验结论。</p></div>'

    html += "</body></html>"
    return html


if __name__ == '__main__':
    print('Loading baseline data...')
    baseline = pd.read_csv(f'{CSV_DIR}/V_分段基线特征.csv')

    vnb_baseline = None
    vnb_path = f'{CSV_DIR}/V_来访未购基线.csv'
    import os
    if os.path.exists(vnb_path):
        vnb_baseline = pd.read_csv(vnb_path)

    print('Running validation tests...')
    all_results = []

    # 生命周期段
    for seg in ['0-15天', '16-30天', '31天+']:
        seg_data = baseline[baseline['lifecycle'] == seg]
        if len(seg_data) > 0:
            r = analyze_segment(seg, seg_data)
            all_results.append(r)
            print(f"\n  [{seg}] SRM p={r['srm_p']:.4f} {'PASS' if r['srm_pass'] else 'FAIL'}")

    # 来访未购
    if vnb_baseline is not None:
        vnb_baseline['lifecycle'] = '来访未购'
        r = analyze_segment('来访未购', vnb_baseline)
        all_results.append(r)
        print(f"\n  [来访未购] SRM p={r['srm_p']:.4f} {'PASS' if r['srm_pass'] else 'FAIL'}")

    print('\nGenerating report...')
    html = generate_html_report(all_results, baseline, vnb_baseline)

    output_path = f'{OUTPUT_DIR}/分群前置检验报告.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Report saved to: {output_path}')
