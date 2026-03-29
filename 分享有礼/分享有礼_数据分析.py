"""
分享有礼活动数据分析 - 2026年2月1日至2月22日
"""
import csv
import os

DOWNLOADS = os.path.expanduser("~/Downloads")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def read_csv(filename):
    filepath = os.path.join(DOWNLOADS, filename)
    if not os.path.exists(filepath):
        print(f"  [跳过] 文件不存在: {filename}")
        return []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def sf(val, default=0):
    try:
        return float(val) if val and val.strip() else default
    except (ValueError, AttributeError):
        return default

def si(val, default=0):
    try:
        return int(float(val)) if val and val.strip() else default
    except (ValueError, AttributeError):
        return default

def pct(a, b, digits=2):
    if b == 0: return '-'
    return f"{round(a * 100 / b, digits)}%"

def fmt_int(v):
    return f"{v:,}" if v else '0'

def build_row(label, vals, cls=''):
    cells = ''.join(f'<td>{v}</td>' for v in vals)
    attr = f' class="{cls}"' if cls else ''
    return f'<tr{attr}><td>{label}</td>{cells}</tr>'


def generate_report():
    print("读取CSV文件...")
    traffic_data = read_csv("分享有礼_流量资源位.csv")
    invitation_data = read_csv("分享有礼_邀请数据.csv")
    new_customer_data = read_csv("分享有礼_获客结果.csv")
    share_will_data = read_csv("分享有礼_分享意愿.csv")

    if not invitation_data:
        print("缺少核心数据文件，无法生成报告")
        return

    # 日期范围: 02-01 ~ 02-22
    all_dates = sorted(set(
        [r.get('dt', '') for r in traffic_data] +
        [r.get('register_dt', '') for r in invitation_data] +
        [r.get('dt', '') for r in new_customer_data]
    ))
    all_dates = [d for d in all_dates if d >= '2026-02-01' and d <= '2026-02-22']

    traffic_by_dt = {r['dt']: r for r in traffic_data if r.get('dt', '') >= '2026-02-01'}
    invite_by_dt = {r['register_dt']: r for r in invitation_data}
    newcust_by_dt = {r['dt']: r for r in new_customer_data}
    share_will_by_dt = {r['dt']: r for r in share_will_data} if share_will_data else {}

    # 汇总计算
    total_register = sum(si(invite_by_dt.get(d, {}).get('register_invitee_cnt', 0)) for d in all_dates)
    total_order_d0 = sum(si(invite_by_dt.get(d, {}).get('order_d0_invitee_cnt', 0)) for d in all_dates)
    total_inviters = sum(si(invite_by_dt.get(d, {}).get('inviter_cnt', 0)) for d in all_dates)
    total_share_register = sum(si(newcust_by_dt.get(d, {}).get('share_register_cnt', 0)) for d in all_dates)
    total_share_order = sum(si(newcust_by_dt.get(d, {}).get('share_order_cnt', 0)) for d in all_dates)
    total_new_order = sum(si(newcust_by_dt.get(d, {}).get('total_new_order_cnt', 0)) for d in all_dates)

    date_headers = '<th>指标</th>' + ''.join(f'<th>{d[5:]}</th>' for d in all_dates) + '<th>汇总</th>'

    # ===== HTML =====
    h = []
    h.append('''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>分享有礼活动数据报告 2026年2月</title>
<style>
body { font-family: -apple-system, sans-serif; margin: 20px; font-size: 12px; color: #333; }
h1 { font-size: 18px; margin-bottom: 4px; }
h2 { font-size: 14px; margin-top: 28px; color: #1565C0; border-bottom: 2px solid #1565C0; padding-bottom: 4px; }
p.subtitle { color: #666; margin-top: 0; }
table { border-collapse: collapse; margin: 8px 0; font-size: 11px; }
th, td { border: 1px solid #ddd; padding: 3px 6px; text-align: right; white-space: nowrap; }
th { background: #f5f5f5; font-weight: 600; text-align: center; }
td:first-child { text-align: left; font-weight: 500; min-width: 180px; background: #fafafa; }
.rate { background: #E3F2FD; }
.summary-col { background: #FFF9C4; font-weight: 600; }
.section-sep td { background: #ECEFF1; font-weight: 600; text-align: left !important; font-size: 11px; }
</style></head><body>''')

    h.append('<h1>分享有礼（Share The Luck）活动数据报告</h1>')
    h.append('<p class="subtitle">统计时间: 2026-02-01 ~ 2026-02-22</p>')

    # ---- 一、获客结果 ----
    h.append('<h2>一、获客结果</h2>')
    h.append(f'<table><tr>{date_headers}</tr>')

    # 分享有礼注册人数
    vals = [fmt_int(si(newcust_by_dt.get(d, {}).get('share_register_cnt', 0))) for d in all_dates]
    vals.append(f'<b>{fmt_int(total_share_register)}</b>')
    h.append(build_row('分享有礼注册人数', vals))

    # 分享有礼当日下单新客数（order_d0）
    vals = [fmt_int(si(invite_by_dt.get(d, {}).get('order_d0_invitee_cnt', 0))) for d in all_dates]
    vals.append(f'<b>{fmt_int(total_order_d0)}</b>')
    h.append(build_row('分享有礼当日下单新客数', vals))

    # 大盘拉新下单人数
    vals = [fmt_int(si(newcust_by_dt.get(d, {}).get('total_new_order_cnt', 0))) for d in all_dates]
    vals.append(f'<b>{fmt_int(total_new_order)}</b>')
    h.append(build_row('大盘拉新下单人数', vals))

    # 分享有礼占大盘拉新占比（当日下单口径）
    vals = []
    for d in all_dates:
        d0 = si(invite_by_dt.get(d, {}).get('order_d0_invitee_cnt', 0))
        total = si(newcust_by_dt.get(d, {}).get('total_new_order_cnt', 0))
        vals.append(pct(d0, total))
    vals.append(f'<b>{pct(total_order_d0, total_new_order)}</b>')
    h.append(build_row('分享有礼占大盘拉新占比', vals, 'rate'))

    h.append('</table>')
    h.append('<p style="color:#999;font-size:10px;">注: 占比口径 = 分享有礼当日下单新客数 / 大盘当日首单新客数</p>')

    # ---- 二、流量获取 ----
    h.append('<h2>二、流量获取（资源位）</h2>')
    h.append(f'<table><tr>{date_headers}</tr>')

    # Icon
    def traffic_row(label, key, cls=''):
        vals = [fmt_int(si(traffic_by_dt.get(d, {}).get(key, 0))) for d in all_dates]
        total = sum(si(traffic_by_dt.get(d, {}).get(key, 0)) for d in all_dates)
        vals.append(f'<b>{fmt_int(total)}</b>')
        h.append(build_row(label, vals, cls))

    def traffic_ctr_row(label, num_key, den_key):
        vals = []
        total_num = total_den = 0
        for d in all_dates:
            r = traffic_by_dt.get(d, {})
            n, de = si(r.get(num_key, 0)), si(r.get(den_key, 0))
            total_num += n; total_den += de
            vals.append(pct(n, de))
        vals.append(f'<b>{pct(total_num, total_den)}</b>')
        h.append(build_row(label, vals, 'rate'))

    traffic_row('Icon 曝光UV', 'icon_expose_uv')
    traffic_row('Icon 点击UV', 'icon_click_uv')
    traffic_ctr_row('Icon CTR', 'icon_click_uv', 'icon_expose_uv')

    # 腰部Banner
    traffic_row('腰部Banner 曝光UV', 'slot_expose_uv')
    traffic_row('腰部Banner 点击UV', 'slot_click_uv')
    traffic_ctr_row('腰部Banner CTR', 'slot_click_uv', 'slot_expose_uv')

    # 弹窗
    traffic_row('弹窗 曝光UV', 'popup_expose_uv')
    traffic_row('弹窗 点击UV', 'popup_click_uv')
    traffic_ctr_row('弹窗 CTR', 'popup_click_uv', 'popup_expose_uv')

    # 总计
    traffic_row('总曝光UV', 'total_expose_uv')
    traffic_row('总点击UV', 'total_click_uv')
    traffic_ctr_row('总CTR', 'total_click_uv', 'total_expose_uv')

    h.append('</table>')

    # ---- 三、分享意愿 ----
    if share_will_by_dt:
        h.append('<h2>三、分享意愿</h2>')
        h.append(f'<table><tr>{date_headers}</tr>')

        def share_will_row(label, key, cls=''):
            vals = [fmt_int(si(share_will_by_dt.get(d, {}).get(key, 0))) for d in all_dates]
            total = sum(si(share_will_by_dt.get(d, {}).get(key, 0)) for d in all_dates)
            vals.append(f'<b>{fmt_int(total)}</b>')
            h.append(build_row(label, vals, cls))

        share_will_row('进入分享页UV', 'share_page_uv')
        share_will_row('点击分享按钮UV', 'share_button_click_uv')

        # 分享率 = 点击分享按钮 / 进入分享页
        vals = []
        total_page = total_btn = 0
        for d in all_dates:
            r = share_will_by_dt.get(d, {})
            page = si(r.get('share_page_uv', 0))
            btn = si(r.get('share_button_click_uv', 0))
            total_page += page; total_btn += btn
            vals.append(pct(btn, page))
        vals.append(f'<b>{pct(total_btn, total_page)}</b>')
        h.append(build_row('分享率（点击/进入）', vals, 'rate'))

        h.append('</table>')
        section_offset = 1
    else:
        h.append('<h2>三、分享意愿（待补充SQL 5数据）</h2>')
        h.append('<p>请运行 SQL 5 并保存为 <code>分享有礼_分享意愿.csv</code>，重新运行脚本即可生成此板块。</p>')
        section_offset = 1

    # ---- 四、分享效率 ----
    sec_num = 3 + section_offset
    h.append(f'<h2>四、分享效率（邀请人维度）</h2>')
    h.append(f'<table><tr>{date_headers}</tr>')

    def invite_row(label, key, cls=''):
        vals = [fmt_int(si(invite_by_dt.get(d, {}).get(key, 0))) for d in all_dates]
        total = sum(si(invite_by_dt.get(d, {}).get(key, 0)) for d in all_dates)
        vals.append(f'<b>{fmt_int(total)}</b>')
        h.append(build_row(label, vals, cls))

    def invite_rate_row(label, num_key, den_key):
        vals = []
        tn = td = 0
        for d in all_dates:
            r = invite_by_dt.get(d, {})
            n, de = si(r.get(num_key, 0)), si(r.get(den_key, 0))
            tn += n; td += de
            vals.append(pct(n, de))
        vals.append(f'<b>{pct(tn, td)}</b>')
        h.append(build_row(label, vals, 'rate'))

    invite_row('邀请人数（带来注册）', 'inviter_cnt')
    invite_row('成功邀请人数（当天）', 'success_inviter_d0_cnt')
    invite_row('成功邀请人数（3天内）', 'success_inviter_d3_cnt')
    invite_row('成功邀请人数（7天内）', 'success_inviter_d7_cnt')
    invite_row('成功邀请人数（14天内）', 'success_inviter_d14_cnt')
    invite_rate_row('邀请成功率（当天）', 'success_inviter_d0_cnt', 'inviter_cnt')
    invite_rate_row('邀请成功率（3天内）', 'success_inviter_d3_cnt', 'inviter_cnt')
    invite_rate_row('邀请成功率（7天内）', 'success_inviter_d7_cnt', 'inviter_cnt')
    invite_rate_row('邀请成功率（14天内）', 'success_inviter_d14_cnt', 'inviter_cnt')

    h.append('</table>')

    # ---- 五、被邀请人 ----
    h.append(f'<h2>五、被邀请人（被分享人维度）</h2>')
    h.append(f'<table><tr>{date_headers}</tr>')

    invite_row('注册人数', 'register_invitee_cnt')
    invite_row('下单人数（当天）', 'order_d0_invitee_cnt')
    invite_row('下单人数（3天内）', 'order_d3_invitee_cnt')
    invite_row('下单人数（7天内）', 'order_d7_invitee_cnt')
    invite_row('下单人数（14天内）', 'order_d14_invitee_cnt')
    invite_rate_row('下单转化率（当天）', 'order_d0_invitee_cnt', 'register_invitee_cnt')
    invite_rate_row('下单转化率（3天内）', 'order_d3_invitee_cnt', 'register_invitee_cnt')
    invite_rate_row('下单转化率（7天内）', 'order_d7_invitee_cnt', 'register_invitee_cnt')
    invite_rate_row('下单转化率（14天内）', 'order_d14_invitee_cnt', 'register_invitee_cnt')

    h.append('</table>')

    # ---- 六、人均邀请 ----
    h.append(f'<h2>六、人均邀请指标</h2>')
    h.append(f'<table><tr>{date_headers}</tr>')

    vals = []
    for d in all_dates:
        v = sf(invite_by_dt.get(d, {}).get('avg_register_per_inviter', 0))
        vals.append(f'{v:.2f}' if v > 0 else '-')
    avg_total = round(total_register / total_inviters, 2) if total_inviters else 0
    vals.append(f'<b>{avg_total:.2f}</b>')
    h.append(build_row('人均邀请注册人数', vals))

    vals = []
    for d in all_dates:
        v = sf(invite_by_dt.get(d, {}).get('avg_success_d0_per_inviter', 0))
        vals.append(f'{v:.2f}' if v > 0 else '-')
    avg_success = round(total_order_d0 / total_inviters, 2) if total_inviters else 0
    vals.append(f'<b>{avg_success:.2f}</b>')
    h.append(build_row('人均成功邀请（当天）', vals))

    h.append('</table>')

    # 数据说明
    h.append('<h2>数据说明</h2>')
    h.append('''<ul style="font-size:11px;color:#666;">
<li><b>注册</b>：被邀请人通过分享链接注册，时间取 t_user_invitation_info.create_time</li>
<li><b>下单/成功</b>：invitation_success = 1，下单时间取 modify_time</li>
<li><b>时间窗口</b>：当天=注册当日(D0)，3天内=D0~D2，7天内=D0~D6，14天内=D0~D13</li>
<li><b>窗口完整性</b>：3天内在02-20前完整，7天内在02-16前完整，14天内在02-09前完整</li>
<li><b>资源位</b>：Icon=首页金刚位#2，弹窗=开屏弹窗(LKUSCP117864583917731840)，Slot Banner 2月无数据</li>
<li><b>分享页</b>：H5sharepage 曝光=进入分享页，点击=点击分享按钮</li>
</ul>''')

    h.append('</body></html>')

    report_path = os.path.join(SCRIPT_DIR, '分享有礼活动数据报告_2月.html')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(h))
    print(f"\n报告已生成: {report_path}")
    return report_path


if __name__ == '__main__':
    generate_report()
