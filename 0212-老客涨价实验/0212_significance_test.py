"""0212 涨价实验显著性检验 + 样本量评估"""
import numpy as np
from scipy import stats
import pandas as pd

# ============================================================
# 数据输入
# ============================================================
# 各组用户数
N = {'涨价组1': 38093, '涨价组2': 38058, '对照组3': 50295}

# 转化率 (order_users / total_users)
conv = {'涨价组1': 3322, '涨价组2': 3294, '对照组3': 4699}

# 单杯实收 (from 杯量CSV汇总)
cups = {'涨价组1': 7636, '涨价组2': 7566, '对照组3': 11185}
item_rev = {'涨价组1': 27543.30, '涨价组2': 26897.47, '对照组3': 36921.82}

# 实收 (period summary)
revenue = {'涨价组1': 29987.00, '涨价组2': 29280.28, '对照组3': 40207.65}

# 3日复购率 (from B3 lifecycle data, cutoff 02-21)
rep3_buyers = {'涨价组1': 3097, '涨价组2': 3064, '对照组3': 4398}
rep3_repurchase = {'涨价组1': 773, '涨价组2': 716, '对照组3': 1101}

# 7日复购率 (from 7日复购率.csv, sum across 02/12-02/17)
rep7_buyers = {'涨价组1': 2915, '涨价组2': 2970, '对照组3': 4172}
rep7_repurchase = {'涨价组1': 1473, '涨价组2': 1478, '对照组3': 2122}

# ============================================================
# 统计检验函数
# ============================================================

def prop_ztest(x1, n1, x2, n2, name=''):
    """双样本比例 z 检验"""
    p1, p2 = x1/n1, x2/n2
    p_pool = (x1+x2) / (n1+n2)
    se = np.sqrt(p_pool * (1-p_pool) * (1/n1 + 1/n2))
    z = (p1 - p2) / se if se > 0 else 0
    p_val = 2 * (1 - stats.norm.cdf(abs(z)))
    # 95% CI for difference
    se_diff = np.sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2)
    ci_low = (p1-p2) - 1.96*se_diff
    ci_high = (p1-p2) + 1.96*se_diff
    return {
        'name': name,
        'p1': p1, 'p2': p2, 'diff': p1-p2,
        'z': z, 'p_value': p_val,
        'ci_low': ci_low, 'ci_high': ci_high,
        'significant': p_val < 0.05
    }

def mean_ztest_from_agg(total1, n1, total2, n2, name='', cv=0.5):
    """基于聚合数据的均值 z 检验（假设 CV=coefficient of variation）"""
    mean1 = total1 / n1
    mean2 = total2 / n2
    # 估算标准差 = mean * cv
    sd1 = mean1 * cv
    sd2 = mean2 * cv
    se = np.sqrt(sd1**2/n1 + sd2**2/n2)
    z = (mean1 - mean2) / se if se > 0 else 0
    p_val = 2 * (1 - stats.norm.cdf(abs(z)))
    ci_low = (mean1-mean2) - 1.96*se
    ci_high = (mean1-mean2) + 1.96*se
    return {
        'name': name,
        'mean1': mean1, 'mean2': mean2, 'diff': mean1-mean2,
        'z': z, 'p_value': p_val,
        'ci_low': ci_low, 'ci_high': ci_high,
        'significant': p_val < 0.05
    }

def power_analysis_proportion(p1, p2, n1, n2, alpha=0.05):
    """计算统计功效（power）"""
    se = np.sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2)
    z_alpha = stats.norm.ppf(1 - alpha/2)
    z_stat = abs(p1 - p2) / se
    power = 1 - stats.norm.cdf(z_alpha - z_stat) + stats.norm.cdf(-z_alpha - z_stat)
    return power

def mde_proportion(p_base, n1, n2, alpha=0.05, power=0.8):
    """最小可检测效应（MDE）"""
    z_alpha = stats.norm.ppf(1 - alpha/2)
    z_beta = stats.norm.ppf(power)
    se = np.sqrt(p_base*(1-p_base)*(1/n1 + 1/n2))
    mde = (z_alpha + z_beta) * se
    return mde

# ============================================================
# 执行检验
# ============================================================
print("=" * 70)
print("  0212 涨价实验 显著性检验报告")
print("=" * 70)

comparisons = [
    ('涨价组1', '对照组3'),
    ('涨价组2', '对照组3'),
    ('涨价组1', '涨价组2'),
]

# 1. 转化率检验
print("\n" + "=" * 70)
print("  1. 转化率显著性检验")
print("=" * 70)
for g1, g2 in comparisons:
    r = prop_ztest(conv[g1], N[g1], conv[g2], N[g2], f'{g1} vs {g2}')
    sig = '✅ 显著' if r['significant'] else '❌ 不显著'
    print(f"\n  {r['name']}:")
    print(f"    {g1}: {r['p1']*100:.2f}%  {g2}: {r['p2']*100:.2f}%  差异: {r['diff']*100:+.2f}pp")
    print(f"    z={r['z']:.3f}  p={r['p_value']:.4f}  95%CI: [{r['ci_low']*100:+.2f}pp, {r['ci_high']*100:+.2f}pp]")
    print(f"    结论: {sig}")

# 2. 单杯实收检验
print("\n" + "=" * 70)
print("  2. 单杯实收显著性检验")
print("=" * 70)
for g1, g2 in comparisons:
    r = mean_ztest_from_agg(item_rev[g1], cups[g1], item_rev[g2], cups[g2],
                            f'{g1} vs {g2}', cv=0.4)
    sig = '✅ 显著' if r['significant'] else '❌ 不显著'
    print(f"\n  {r['name']}:")
    print(f"    {g1}: ${r['mean1']:.2f}  {g2}: ${r['mean2']:.2f}  差异: ${r['diff']:+.3f}")
    print(f"    z={r['z']:.3f}  p={r['p_value']:.4f}")
    print(f"    结论: {sig}")

# 3. 3日复购率检验
print("\n" + "=" * 70)
print("  3. 3日复购率显著性检验")
print("=" * 70)
for g1, g2 in comparisons:
    r = prop_ztest(rep3_repurchase[g1], rep3_buyers[g1],
                   rep3_repurchase[g2], rep3_buyers[g2], f'{g1} vs {g2}')
    sig = '✅ 显著' if r['significant'] else '❌ 不显著'
    print(f"\n  {r['name']}:")
    print(f"    {g1}: {r['p1']*100:.2f}%  {g2}: {r['p2']*100:.2f}%  差异: {r['diff']*100:+.2f}pp")
    print(f"    z={r['z']:.3f}  p={r['p_value']:.4f}  95%CI: [{r['ci_low']*100:+.2f}pp, {r['ci_high']*100:+.2f}pp]")
    print(f"    结论: {sig}")

# 4. 7日复购率检验
print("\n" + "=" * 70)
print("  4. 7日复购率显著性检验")
print("=" * 70)
for g1, g2 in comparisons:
    r = prop_ztest(rep7_repurchase[g1], rep7_buyers[g1],
                   rep7_repurchase[g2], rep7_buyers[g2], f'{g1} vs {g2}')
    sig = '✅ 显著' if r['significant'] else '❌ 不显著'
    print(f"\n  {r['name']}:")
    print(f"    {g1}: {r['p1']*100:.2f}%  {g2}: {r['p2']*100:.2f}%  差异: {r['diff']*100:+.2f}pp")
    print(f"    z={r['z']:.3f}  p={r['p_value']:.4f}  95%CI: [{r['ci_low']*100:+.2f}pp, {r['ci_high']*100:+.2f}pp]")
    print(f"    结论: {sig}")

# 5. ARPU 检验 (revenue / total_users)
print("\n" + "=" * 70)
print("  5. ARPU（全用户）显著性检验")
print("=" * 70)
for g1, g2 in comparisons:
    r = mean_ztest_from_agg(revenue[g1], N[g1], revenue[g2], N[g2],
                            f'{g1} vs {g2}', cv=3.0)  # ARPU 高方差
    sig = '✅ 显著' if r['significant'] else '❌ 不显著'
    print(f"\n  {r['name']}:")
    print(f"    {g1}: ${r['mean1']:.3f}  {g2}: ${r['mean2']:.3f}  差异: ${r['diff']:+.4f}")
    print(f"    z={r['z']:.3f}  p={r['p_value']:.4f}")
    print(f"    结论: {sig}")

# ============================================================
# 6. 样本量与统计功效分析
# ============================================================
print("\n" + "=" * 70)
print("  6. 样本量与统计功效分析")
print("=" * 70)

base_conv = conv['对照组3'] / N['对照组3']

# MDE
for g1, g2 in comparisons:
    p_base = conv[g2] / N[g2]
    mde = mde_proportion(p_base, N[g1], N[g2])
    print(f"\n  {g1} vs {g2}:")
    print(f"    样本量: {N[g1]:,} vs {N[g2]:,}")
    print(f"    最小可检测效应(MDE, 80%功效): {mde*100:.2f}pp")

    # 实际功效
    p1 = conv[g1] / N[g1]
    p2 = conv[g2] / N[g2]
    pwr = power_analysis_proportion(p1, p2, N[g1], N[g2])
    print(f"    实际转化率差异: {abs(p1-p2)*100:.2f}pp")
    print(f"    当前统计功效(power): {pwr*100:.1f}%")
    if pwr >= 0.8:
        print(f"    → ✅ 功效充足，样本量足够检测该差异")
    else:
        print(f"    → ⚠️ 功效不足，需更大样本或更长实验周期")

# 复购率功效
print("\n  --- 3日复购率功效 ---")
for g1, g2 in [('涨价组1', '涨价组2'), ('涨价组2', '对照组3')]:
    p1 = rep3_repurchase[g1] / rep3_buyers[g1]
    p2 = rep3_repurchase[g2] / rep3_buyers[g2]
    pwr = power_analysis_proportion(p1, p2, rep3_buyers[g1], rep3_buyers[g2])
    mde = mde_proportion((p1+p2)/2, rep3_buyers[g1], rep3_buyers[g2])
    print(f"\n  {g1} vs {g2}:")
    print(f"    样本量(有购用户): {rep3_buyers[g1]:,} vs {rep3_buyers[g2]:,}")
    print(f"    差异: {abs(p1-p2)*100:.2f}pp  MDE: {mde*100:.2f}pp")
    print(f"    功效: {pwr*100:.1f}%  {'✅' if pwr >= 0.8 else '⚠️'}")

print("\n" + "=" * 70)
print("  7. 综合结论")
print("=" * 70)
print("""
  各对比维度显著性汇总:

  指标                 组1 vs 对照   组2 vs 对照   组1 vs 组2
  ─────────────────────────────────────────────────────────
""")

# Run all tests and summarize
metrics_tests = []
for metric_name, test_func, args_list in [
    ('转化率', lambda g1,g2: prop_ztest(conv[g1], N[g1], conv[g2], N[g2]),
     comparisons),
    ('3日复购率', lambda g1,g2: prop_ztest(rep3_repurchase[g1], rep3_buyers[g1],
                                          rep3_repurchase[g2], rep3_buyers[g2]),
     comparisons),
    ('7日复购率', lambda g1,g2: prop_ztest(rep7_repurchase[g1], rep7_buyers[g1],
                                          rep7_repurchase[g2], rep7_buyers[g2]),
     comparisons),
]:
    results = []
    for g1, g2 in args_list:
        r = test_func(g1, g2)
        results.append(r)
    sig_labels = ['✅' if r['significant'] else '❌' for r in results]
    p_labels = [f"p={r['p_value']:.3f}" for r in results]
    print(f"  {metric_name:12s}    {sig_labels[0]} {p_labels[0]:12s}  {sig_labels[1]} {p_labels[1]:12s}  {sig_labels[2]} {p_labels[2]:12s}")
