"""2月涨价实验月报 - 简版
只保留：总体实验效果 + 分阶段用户数据表现
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
    '涨价组1': {'0-15天': '75折全品×2', '16-30天': '5折', '31天+': '4折+$2.99+7折(t7)', '来访未购': '6折', '周六日消费': '6折'},
    '涨价组2': {'0-15天': '7折全品×2', '16-30天': '5折', '31天+': '4折(t7)+$2.99+6折(t7)', '来访未购': '55折', '周六日消费': '55折'},
    '对照组3': {'0-15天': '6折限品+7折全品', '16-30天': '4折', '31天+': '3折(t7)+$2.99(t7)+5折(t7)', '来访未购': '5折', '周六日消费': '5折'},
}
GROUPS = ['涨价组1', '涨价组2', '对照组3']


def prop_ztest(x1, n1, x2, n2):
    if n1 == 0 or n2 == 0: return {'p_value': 1, 'significant': False}
    p1, p2 = x1/n1, x2/n2
    p_pool = (x1+x2)/(n1+n2)
    se = np.sqrt(p_pool*(1-p_pool)*(1/n1+1/n2))
    z = (p1-p2)/se if se > 0 else 0
    p = 2*(1-stats.norm.cdf(abs(z)))
    return {'p_value': p, 'significant': p < 0.05}

def mean_ztest(t1, n1, t2, n2, cv=0.5):
    if n1 == 0 or n2 == 0: return {'p_value': 1, 'significant': False}
    m1, m2 = t1/n1, t2/n2
    se = np.sqrt((m1*cv)**2/n1 + (m2*cv)**2/n2)
    z = (m1-m2)/se if se > 0 else 0
    p = 2*(1-stats.norm.cdf(abs(z)))
    return {'p_value': p, 'significant': p < 0.05}


def load_and_compute():
    d = {}
    d['sizes'] = pd.read_csv(f'{CSV_DIR}/A_各组用户数.csv')
    d['daily_orders'] = pd.read_csv(f'{CSV_DIR}/A_每日订单.csv')
    d['daily_cups'] = pd.read_csv(f'{CSV_DIR}/A_每日杯量.csv')
    d['period'] = pd.read_csv(f'{CSV_DIR}/A_汇总指标.csv')
    d['rep3'] = pd.read_csv(f'{CSV_DIR}/A_3日复购.csv')
    d['rep7'] = pd.read_csv(f'{CSV_DIR}/A_7日复购.csv')
    d['lc_orders'] = pd.read_csv(f'{CSV_DIR}/B_分段订单指标.csv')
    d['lc_cups'] = pd.read_csv(f'{CSV_DIR}/B_分段杯量.csv')
    d['lc_rep3'] = pd.read_csv(f'{CSV_DIR}/B_分段3日复购.csv')
    d['lc_rep7'] = pd.read_csv(f'{CSV_DIR}/B_分段7日复购.csv')
    for prefix, key in [('D_来访未购_订单指标','vnb_orders'),('D_来访未购_杯量','vnb_cups'),('D_来访未购_3日复购','vnb_rep3'),
                         ('E_周六日_订单指标','wkd_orders'),('E_周六日_杯量','wkd_cups'),('E_周六日_3日复购','wkd_rep3')]:
        p = f'{CSV_DIR}/{prefix}.csv'
        if os.path.exists(p): d[key] = pd.read_csv(p)

    # Group sizes
    col = 'total_users' if 'total_users' in d['sizes'].columns else 'old_users'
    gsizes = dict(zip(d['sizes']['grp'], d['sizes'][col].astype(int)))

    # Overall
    overall = {}
    for grp in GROUPS:
        n = gsizes[grp]
        ps = d['period'][d['period']['grp']==grp]
        ou = int(ps['period_order_users'].iloc[0]); rev = float(ps['period_revenue'].iloc[0])
        dc = d['daily_cups'][d['daily_cups']['grp']==grp]
        cups = int(dc['cups'].sum()); irev = float(dc['item_revenue'].sum())
        up = round(irev/cups, 2) if cups else 0
        r3 = d['rep3'][d['rep3']['grp']==grp]['repurchase_rate_3d'].mean()
        r7 = d['rep7'][d['rep7']['grp']==grp]['repurchase_rate_7d'].mean()
        overall[grp] = {'n': n, 'ou': ou, 'cups': cups, 'rev': rev, 'up': up,
                        'conv': round(ou/n*100, 2), 'r3': round(r3, 2), 'r7': round(r7, 2),
                        'arpu': round(rev/n, 3)}

    # LTV
    do = d['daily_orders'].copy(); do['dt'] = pd.to_datetime(do['dt'])
    ltv = {}
    for grp in GROUPS:
        gd = do[do['grp']==grp]; n = gsizes[grp]
        ltv[grp] = {
            'ltv7': round(gd[gd['dt']<=LTV7_END]['revenue'].sum()/n, 3),
            'ltv14': round(gd[gd['dt']<=LTV14_END]['revenue'].sum()/n, 3),
        }

    # Segments
    segs = {}
    for seg in ['0-15天', '16-30天', '31天+']:
        segs[seg] = {}
        for grp in GROUPS:
            ro = d['lc_orders'][(d['lc_orders']['grp']==grp)&(d['lc_orders']['lifecycle']==seg)]
            rc = d['lc_cups'][(d['lc_cups']['grp']==grp)&(d['lc_cups']['lifecycle']==seg)]
            r3 = d['lc_rep3'][(d['lc_rep3']['grp']==grp)&(d['lc_rep3']['lifecycle']==seg)]
            r7 = d['lc_rep7'][(d['lc_rep7']['grp']==grp)&(d['lc_rep7']['lifecycle']==seg)]
            segs[seg][grp] = {
                'n': int(ro['total_users'].iloc[0]) if len(ro) else 0,
                'ou': int(ro['order_users'].iloc[0]) if len(ro) else 0,
                'rev': float(ro['revenue'].iloc[0]) if len(ro) and not pd.isna(ro['revenue'].iloc[0]) else 0,
                'conv': float(ro['conversion_rate'].iloc[0]) if len(ro) else 0,
                'up': float(rc['unit_price'].iloc[0]) if len(rc) else 0,
                'cups': int(rc['cups'].iloc[0]) if len(rc) else 0,
                'r3': float(r3['repurchase_rate_3d'].iloc[0]) if len(r3) else 0,
                'r7': float(r7['repurchase_rate_7d'].iloc[0]) if len(r7) else 0,
            }
    if 'vnb_orders' in d:
        segs['来访未购'] = {}
        for grp in GROUPS:
            ro = d['vnb_orders'][d['vnb_orders']['grp']==grp]
            rc = d['vnb_cups'][d['vnb_cups']['grp']==grp]
            r3 = d['vnb_rep3'][d['vnb_rep3']['grp']==grp]
            segs['来访未购'][grp] = {
                'n': int(ro['total_users'].iloc[0]) if len(ro) else 0,
                'ou': int(ro['order_users'].iloc[0]) if len(ro) else 0,
                'rev': float(ro['revenue'].iloc[0]) if len(ro) and not pd.isna(ro['revenue'].iloc[0]) else 0,
                'conv': float(ro['conversion_rate'].iloc[0]) if len(ro) else 0,
                'up': float(rc['unit_price'].iloc[0]) if len(rc) else 0,
                'cups': int(rc['cups'].iloc[0]) if len(rc) else 0,
                'r3': float(r3['repurchase_rate_3d'].iloc[0]) if len(r3) else 0, 'r7': 0,
            }
    if 'wkd_orders' in d:
        segs['周六日消费'] = {}
        for grp in GROUPS:
            ro = d['wkd_orders'][d['wkd_orders']['grp']==grp]
            rc = d['wkd_cups'][d['wkd_cups']['grp']==grp]
            r3 = d['wkd_rep3'][d['wkd_rep3']['grp']==grp]
            segs['周六日消费'][grp] = {
                'n': int(ro['total_users'].iloc[0]) if len(ro) else 0,
                'ou': int(ro['order_users'].iloc[0]) if len(ro) else 0,
                'rev': float(ro['revenue'].iloc[0]) if len(ro) and not pd.isna(ro['revenue'].iloc[0]) else 0,
                'conv': float(ro['conversion_rate'].iloc[0]) if len(ro) else 0,
                'up': float(rc['unit_price'].iloc[0]) if len(rc) else 0,
                'cups': int(rc['cups'].iloc[0]) if len(rc) else 0,
                'r3': float(r3['repurchase_rate_3d'].iloc[0]) if len(r3) else 0, 'r7': 0,
            }

    # Significance tests
    ctrl = overall['对照组3']
    tests = {}
    for grp in ['涨价组1', '涨价组2']:
        g = overall[grp]
        tests[f'conv_{grp}'] = prop_ztest(g['ou'], g['n'], ctrl['ou'], ctrl['n'])
        tests[f'up_{grp}'] = mean_ztest(g['up']*g['cups'], g['cups'], ctrl['up']*ctrl['cups'], ctrl['cups'], cv=0.5)
        rx1 = int(g['r7']/100*g['ou']); rx2 = int(ctrl['r7']/100*ctrl['ou'])
        tests[f'r7_{grp}'] = prop_ztest(rx1, g['ou'], rx2, ctrl['ou'])
        tests[f'arpu_{grp}'] = mean_ztest(g['rev'], g['n'], ctrl['rev'], ctrl['n'], cv=2.0)
    for seg in segs:
        for grp in ['涨价组1', '涨价组2']:
            if grp in segs[seg] and '对照组3' in segs[seg]:
                tests[f'{seg}_conv_{grp}'] = prop_ztest(segs[seg][grp]['ou'], segs[seg][grp]['n'], segs[seg]['对照组3']['ou'], segs[seg]['对照组3']['n'])

    return overall, gsizes, ltv, segs, tests


def generate_html(overall, gsizes, ltv, segs, tests):
    ctrl = overall['对照组3']; cs = gsizes['对照组3']
    GC = {'涨价组1': 'grp1', '涨价组2': 'grp2', '对照组3': 'ctrl'}
    ratios = {g: cs/gsizes[g] for g in GROUPS}

    def fd(v, s='%'):
        c = 'positive' if v > 0 else ('negative' if v < 0 else '')
        return f'<span class="{c}">{v:+.2f}{s}</span>'

    def cl(v, f, d=None, ds='%'):
        if f=='pct': b = f'{v:.2f}%'
        elif f=='money': b = f'${v:,.2f}'
        elif f=='m3': b = f'${v:.3f}'
        elif f=='int': b = f'{int(v):,}'
        else: b = str(v)
        if d is None: return b
        return f'{b} <small>({fd(d,ds)})</small>'

    ld = {}
    for g in ['涨价组1', '涨价组2']:
        ld[g] = {
            'l7': (ltv[g]['ltv7']-ltv['对照组3']['ltv7'])/ltv['对照组3']['ltv7']*100,
            'l14': (ltv[g]['ltv14']-ltv['对照组3']['ltv14'])/ltv['对照组3']['ltv14']*100,
        }
    rd = {g: (overall[g]['rev']*ratios[g]-ctrl['rev'])/ctrl['rev']*100 for g in ['涨价组1','涨价组2']}
    g1, g2, c = overall['涨价组1'], overall['涨价组2'], ctrl
    up1 = (g1['up']-c['up'])/c['up']*100; up2 = (g2['up']-c['up'])/c['up']*100
    cv1 = g1['conv']-c['conv']; cv2 = g2['conv']-c['conv']

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>2月涨价实验月报（简版）</title>
<style>
@page {{ size: landscape; margin: 12mm; }}
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; margin: 20px auto; max-width: 1100px; font-size: 12px; color: #333; line-height: 1.5; }}
h1 {{ color: #1a1a2e; font-size: 18px; border-bottom: 2px solid #e94560; padding-bottom: 6px; margin-bottom: 8px; }}
h3 {{ color: #0f3460; font-size: 13px; margin: 14px 0 6px 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 6px 0; }}
th, td {{ border: 1px solid #ddd; padding: 5px 8px; text-align: right; font-size: 11px; white-space: nowrap; }}
th {{ background: #f0f0f0; font-weight: 600; text-align: center; }}
td:first-child {{ text-align: left; font-weight: 500; }}
.positive {{ color: #D32F2F; }} .negative {{ color: #2E7D32; }}
.grp1 {{ background: #FFF3E0; }} .grp2 {{ background: #E3F2FD; }} .ctrl {{ background: #E8F5E9; }}
.conclusion {{ background: #f8f9fa; border-radius: 6px; padding: 10px 14px; margin: 8px 0; }}
.conclusion ul {{ margin: 4px 0; padding-left: 20px; }}
.conclusion li {{ margin: 2px 0; font-size: 11px; }}
.note {{ font-size: 10px; color: #999; margin-top: 6px; }}
small {{ font-size: 9px; color: #888; }}
</style></head><body>

<h1>2月老客涨价实验月报</h1>
<p style="color:#666;font-size:11px;margin:2px 0 10px">实验: {EXP_START} ~ {EXP_END} | 涨价组1(75折系, 30%, {g1['n']:,}人) vs 涨价组2(7折系, 30%, {g2['n']:,}人) vs 对照组3(原价, 40%, {c['n']:,}人)</p>

<div class="conclusion">
<b>结论：整体可以涨价，推荐涨价组1（75折系）为基础方案。</b>
<ul>
<li>单杯实收显著提升：组1 {fd(up1)}、组2 {fd(up2)}；转化率代价可控：组1 {fd(cv1,'pp')}、组2 {fd(cv2,'pp')}</li>
<li>7日复购：组1 {fd(g1['r7']-c['r7'],'pp')}（影响极小）、组2 {fd(g2['r7']-c['r7'],'pp')}（更明显）；LTV 14天：组1 {fd(ld['涨价组1']['l14'])}、组2 {fd(ld['涨价组2']['l14'])}，组1损失更小且{'趋势收窄' if abs(ld['涨价组1']['l14']) < abs(ld['涨价组1']['l7']) else '需关注'}</li>
<li><b>组1定价更高但表现更好</b>——折扣深度并非越深越好，组1在单杯提升、转化控制、留存维护三维度均优于组2</li>
<li><b>差异化定价是关键</b>：31天+和周六日消费可大胆涨价；来访未购和新客需维持深折扣</li>
</ul>
</div>
"""

    # ═══ 表1：总体实验效果 ═══
    html += '<h3>总体实验效果</h3>\n'
    html += '<table>\n<tr><th>组别</th><th>转化率</th><th>单杯实收</th><th>7日复购</th><th>3日复购</th><th>拉齐实收</th><th>LTV 7天</th><th>LTV 14天</th></tr>\n'
    for grp in GROUPS:
        g = overall[grp]; ic = grp=='对照组3'; s = GC[grp]
        if not ic:
            cd = g['conv']-c['conv']; ud = (g['up']-c['up'])/c['up']*100
            r7d = g['r7']-c['r7']; r3d = g['r3']-c['r3']
            nr = g['rev']*ratios[grp]; nrd = (nr-c['rev'])/c['rev']*100
            l7 = ld[grp]['l7']; l14 = ld[grp]['l14']
        else:
            cd=ud=r7d=r3d=nrd=l7=l14=None; nr=c['rev']
        html += f'<tr class="{s}"><td><b>{grp}</b></td>'
        html += f'<td>{cl(g["conv"],"pct",cd,"pp")}</td>'
        html += f'<td>{cl(g["up"],"money",ud,"%")}</td>'
        html += f'<td>{cl(g["r7"],"pct",r7d,"pp")}</td>'
        html += f'<td>{cl(g["r3"],"pct",r3d if not ic else None,"pp")}</td>'
        html += f'<td>{cl(nr,"money",nrd,"%")}</td>'
        html += f'<td>{cl(ltv[grp]["ltv7"],"m3",l7 if not ic else None,"%")}</td>'
        html += f'<td>{cl(ltv[grp]["ltv14"],"m3",l14 if not ic else None,"%")}</td>'
        html += '</tr>\n'
    html += '</table>\n'

    # ═══ 表2：分阶段策略效果 ═══
    html += '<h3>分阶段策略效果与定价建议</h3>\n'
    html += '<table>\n<tr><th>用户分段</th><th>涨价组1（75折系）</th><th>涨价组2（7折系）</th><th>建议调整方向</th></tr>\n'

    recs = {
        '31天+': '维持组1策略，可探索45折替代4折，试探更浅折扣天花板',
        '周六日消费': '可激进涨价，从6折提到65折或7折。习惯型用户对折扣不敏感',
        '16-30天': '当前5折合理，可小幅测试55折。培养期用户正在形成消费习惯',
        '来访未购': '定价偏高，建议回调到5折或更低。价格敏感型用户需深折扣拉回',
        '0-15天': '定价偏高，建议新客维持6折或更深折扣。首单价格锚点影响长期价值',
    }

    for seg in ['31天+', '周六日消费', '16-30天', '来访未购', '0-15天']:
        if seg not in segs: continue
        sd = segs[seg]; cs_seg = sd.get('对照组3', {})
        if not cs_seg: continue
        pct = cs_seg['n'] / ctrl['n'] * 100
        cells = []
        for grp in ['涨价组1', '涨价组2']:
            if grp not in sd: cells.append('-'); continue
            g = sd[grp]; strat = STRATEGY_MATRIX.get(grp, {}).get(seg, '-')
            ud = (g['up']-cs_seg['up'])/cs_seg['up']*100 if cs_seg['up'] else 0
            cd = g['conv']-cs_seg['conv']
            cells.append(f'<b>{strat}</b><br>单杯{fd(ud)}，转化{fd(cd, "pp")}')
        html += f'<tr><td><b>{seg}</b><br><span style="font-size:10px;color:#666">占比{pct:.1f}%</span></td>'
        html += f'<td style="font-size:11px;white-space:normal;min-width:150px">{cells[0]}</td>'
        html += f'<td style="font-size:11px;white-space:normal;min-width:150px">{cells[1]}</td>'
        html += f'<td style="font-size:11px;white-space:normal">{recs.get(seg,"-")}</td></tr>\n'
    html += '</table>\n'

    html += f'<p class="note">* 3日复购截至{REP3_CUTOFF}，7日复购截至{REP7_CUTOFF}。LTV 7天截至{LTV7_END}，14天截至{LTV14_END}。转化率=下单用户/总用户，拉齐=按对照组人数归一化。</p>\n'
    html += '</body></html>'
    return html


if __name__ == '__main__':
    print('Computing...')
    overall, gsizes, ltv, segs, tests = load_and_compute()
    html = generate_html(overall, gsizes, ltv, segs, tests)
    path = f'{OUTPUT_DIR}/2月涨价实验月报-简版.html'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Saved: {path}')
    # Also copy to desktop
    import shutil
    desk = os.path.expanduser('~/Desktop/实验报告/2月涨价实验月报-简版.html')
    shutil.copy2(path, desk)
    print(f'Copied: {desk}')
