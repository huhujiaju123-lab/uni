#!/usr/bin/env python3
"""Coffee Pass 卖券活动复盘报告生成器
从 coffee_pass_data.json 读取数据，生成 HTML 报告
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "coffee_pass_data.json")
R2_FILE = os.path.join(SCRIPT_DIR, "coffee_pass_data_r2.json")
FUNNEL_FILE = os.path.join(SCRIPT_DIR, "coffee_pass_funnel.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "Coffee_Pass_复盘报告.html")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)
with open(R2_FILE, "r", encoding="utf-8") as f:
    r2 = json.load(f)
with open(FUNNEL_FILE, "r", encoding="utf-8") as f:
    funnel_data = json.load(f)

# ============================================================
# 数据预处理
# ============================================================

# ===== 使用 R2（活动期 02-06~02-15）数据 =====
# Q1: 销售概况 — 仍取原数据的活动期日趋势
q1 = data["Q1_sales"]
main_period = [r for r in q1 if "2026-02-06" <= r["dt"] <= "2026-02-15"]

total_coupons = sum(int(r["cnt"]) for r in r2["R2_redemption"])  # 550
total_packs = total_coupons / 5  # 110
total_revenue = total_packs * 19.9
total_buyers = 102  # R2 round only

# Q1b: 购买份数分布
q1b = r2["R2_packs_dist"]

# Q2: 核销
q2 = r2["R2_redemption"]
used_cnt = int(next((r["cnt"] for r in q2 if r["use_status"] == "1"), 0))
unused_cnt = int(next((r["cnt"] for r in q2 if r["use_status"] != "1"), 0))
redeem_rate = used_cnt / total_coupons * 100 if total_coupons else 0

# Q2b: 人均核销张数分布
q2b = r2["R2_redeem_dist"]

# Q3: 核销时效
q3 = r2["R2_timing"]
# 分周统计
week1 = sum(int(r["cnt"]) for r in q3 if 0 <= int(r["days_to_use"]) <= 7)
week2 = sum(int(r["cnt"]) for r in q3 if 8 <= int(r["days_to_use"]) <= 14)
week3 = sum(int(r["cnt"]) for r in q3 if 15 <= int(r["days_to_use"]) <= 21)
after3w = sum(int(r["cnt"]) for r in q3 if int(r["days_to_use"]) > 21)
day0_cnt = int(next((r["cnt"] for r in q3 if r["days_to_use"] == "0"), 0))

# Q4b: 核销订单日趋势（筛选活动期 02-06 ~ 03-08）
q4b_activity = [r for r in data["Q4b_order_trend"] if "2026-02-06" <= r["dt"] <= "2026-02-15"]
q4b_post = [r for r in data["Q4b_order_trend"] if "2026-02-16" <= r["dt"] <= "2026-03-08"]
# 活动期汇总
activity_orders = sum(int(r["order_cnt"]) for r in q4b_activity)
activity_pay = sum(float(r["total_pay"]) for r in q4b_activity)

# Q5: 门店分布（排除空 shop_name）— 仍用原数据
q5 = [r for r in data["Q5_shop_top10"] if r["shop_name"]]

# Q6: 用户画像 — 用 R2 数据
q6 = r2["R2_profile"]
q6b = r2["R2_freq_dist"]

# Q7: 前后对比 — 用 R2 数据（14天 + 30天两个窗口）
q7_30 = r2["R2_before_after_30d"]
before30 = next((r for r in q7_30 if "前" in r["period"]), {})
after30 = next((r for r in q7_30 if "后" in r["period"]), {})
q7_14 = r2["R2_before_after_14d"]
before14 = next((r for r in q7_14 if "前" in r["period"]), {})
after14 = next((r for r in q7_14 if "后" in r["period"]), {})

# Q8: 过期/未用 — 用 R2 数据
q8 = r2["R2_expire"]
q8b = r2["R2_unused_dist"]

# Q9: 复购 — 用 R2 数据
q9 = r2["R2_repurchase"]
full_used = next((r for r in q9 if r["buyer_group"] == "全部用完"), {})
not_used = next((r for r in q9 if r["buyer_group"] == "未用完"), {})

# Funnel: 页面级漏斗
page_funnel = funnel_data.get("page_funnel", [])
buyer_pages = funnel_data.get("buyer_pages", [])

# 按日汇总漏斗数据
funnel_dates = sorted(set(r["dt"] for r in page_funnel))
funnel_by_date = {}
for dt in funnel_dates:
    funnel_by_date[dt] = {}
    for r in page_funnel:
        if r["dt"] == dt:
            funnel_by_date[dt][r["screen_name"]] = int(r["uv"])

# 活动期日均
home_total = sum(funnel_by_date.get(d, {}).get("home", 0) for d in funnel_dates)
mine_total = sum(funnel_by_date.get(d, {}).get("mine", 0) for d in funnel_dates)
home_avg = home_total / len(funnel_dates) if funnel_dates else 0
mine_avg = mine_total / len(funnel_dates) if funnel_dates else 0

# 购买日的每日购买人数 (activity period only)
buyers_by_date = {r["dt"]: int(r["buyer_cnt"]) for r in main_period}

# 购买者路径分析
buyer_page_map = {r["screen_name"]: int(r["buyer_uv"]) for r in buyer_pages if r["screen_name"]}


# ============================================================
# HTML 生成
# ============================================================
def fmt(v, decimals=0):
    """格式化数字"""
    if isinstance(v, str):
        try:
            v = float(v)
        except ValueError:
            return v
    if decimals == 0:
        return f"{int(v):,}"
    return f"{v:,.{decimals}f}"


def pct(a, b, d=1):
    if not b or float(b) == 0:
        return "-"
    return f"{float(a)/float(b)*100:.{d}f}%"


# 漏斗图数据
funnel_dates_js = [d[5:] for d in funnel_dates]
funnel_home_js = [funnel_by_date.get(d, {}).get("home", 0) for d in funnel_dates]
funnel_mine_js = [funnel_by_date.get(d, {}).get("mine", 0) for d in funnel_dates]
funnel_buyers_js = [buyers_by_date.get(d, 0) for d in funnel_dates]

# 销售趋势图数据
sales_dates = [r["dt"][5:] for r in main_period]  # MM-DD
sales_packs = [float(r["total_packs"]) for r in main_period]
sales_buyers = [int(r["buyer_cnt"]) for r in main_period]

# 核销时效分布（前14天）
timing_days = [int(r["days_to_use"]) for r in q3 if int(r["days_to_use"]) <= 21]
timing_cnts = [int(r["cnt"]) for r in q3 if int(r["days_to_use"]) <= 21]

# 门店 TOP 数据（排除空名）
shop_names_js = [r["shop_name"] for r in q5[:8]]
shop_orders_js = [int(r["order_cnt"]) for r in q5[:8]]

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Coffee Pass 卖券活动复盘报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root {{
    --bg: #0f172a; --card: #1e293b; --border: #334155;
    --text: #e2e8f0; --text2: #94a3b8; --accent: #38bdf8;
    --green: #4ade80; --red: #f87171; --yellow: #fbbf24;
    --orange: #fb923c; --purple: #a78bfa;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--text); font-family: -apple-system, "SF Pro Text", "Helvetica Neue", sans-serif; line-height: 1.6; padding: 20px; }}
.container {{ max-width: 1100px; margin: 0 auto; }}
h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 4px; }}
.subtitle {{ color: var(--text2); font-size: 14px; margin-bottom: 24px; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
.kpi {{ background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); }}
.kpi-label {{ font-size: 13px; color: var(--text2); margin-bottom: 4px; }}
.kpi-value {{ font-size: 28px; font-weight: 700; color: var(--accent); }}
.kpi-sub {{ font-size: 12px; color: var(--text2); margin-top: 2px; }}
.section {{ background: var(--card); border-radius: 12px; padding: 24px; margin-bottom: 20px; border: 1px solid var(--border); }}
.section-title {{ font-size: 18px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
.section-title .num {{ background: var(--accent); color: var(--bg); width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{ text-align: left; padding: 10px 12px; background: rgba(56,189,248,0.08); color: var(--accent); font-weight: 600; border-bottom: 1px solid var(--border); }}
td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); }}
tr:hover td {{ background: rgba(255,255,255,0.02); }}
.highlight {{ color: var(--accent); font-weight: 600; }}
.good {{ color: var(--green); }}
.warn {{ color: var(--yellow); }}
.bad {{ color: var(--red); }}
.chart-container {{ position: relative; height: 260px; margin: 16px 0; }}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
.insight {{ background: rgba(56,189,248,0.06); border-left: 3px solid var(--accent); padding: 12px 16px; border-radius: 0 8px 8px 0; margin-top: 12px; font-size: 14px; }}
.insight strong {{ color: var(--accent); }}
.tag {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
.tag-green {{ background: rgba(74,222,128,0.15); color: var(--green); }}
.tag-yellow {{ background: rgba(251,191,36,0.15); color: var(--yellow); }}
.tag-red {{ background: rgba(248,113,113,0.15); color: var(--red); }}
.summary-box {{ background: linear-gradient(135deg, rgba(56,189,248,0.1), rgba(167,139,250,0.1)); border: 1px solid rgba(56,189,248,0.3); border-radius: 12px; padding: 24px; margin-top: 24px; }}
.summary-box h2 {{ color: var(--accent); font-size: 20px; margin-bottom: 12px; }}
.summary-box ul {{ list-style: none; padding: 0; }}
.summary-box li {{ padding: 6px 0; padding-left: 20px; position: relative; font-size: 14px; }}
.summary-box li::before {{ content: "\\25B8"; position: absolute; left: 0; color: var(--accent); }}
@media (max-width: 768px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .two-col {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="container">

<h1>Coffee Pass — 5 for $19.9 复盘报告</h1>
<p class="subtitle">活动时间: 2026-02-06 ~ 02-15 (本轮) | 方案: LKUSCP118713952489488385 | 数据截止: 03-08 | 注: 预售期 01-21~01-30 共 27 人已剔除</p>

<!-- KPI 大盘 -->
<div class="kpi-grid">
    <div class="kpi">
        <div class="kpi-label">总售出份数</div>
        <div class="kpi-value">{fmt(total_packs)}</div>
        <div class="kpi-sub">仅本轮 02-06~02-15</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">购买用户数</div>
        <div class="kpi-value">{fmt(total_buyers)}</div>
        <div class="kpi-sub">人均 {total_packs/total_buyers:.1f} 份 | 94% 仅买1份</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">总收入</div>
        <div class="kpi-value">${fmt(total_revenue, 0)}</div>
        <div class="kpi-sub">单杯成本 $3.98</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">券核销率</div>
        <div class="kpi-value">{redeem_rate:.1f}%</div>
        <div class="kpi-sub">{fmt(used_cnt)}/{fmt(total_coupons)} 张</div>
    </div>
</div>

<!-- 模块0: 资源位转化漏斗 -->
<div class="section">
    <div class="section-title"><span class="num">0</span>资源位转化漏斗</div>
    <p style="color:var(--text2); font-size:13px; margin-bottom:16px">资源位: 首页 Banner + 我的页面腰部 | 页面级 UV 作为曝光代理（精确曝光/点击需埋点大表，API 查询超时）</p>
    <div class="two-col">
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">转化漏斗（活动期汇总）</h4>
            <div class="chart-container" style="height:200px"><canvas id="funnelChart"></canvas></div>
            <table>
                <tr><th>漏斗层级</th><th>UV</th><th>转化率</th></tr>
                <tr>
                    <td>首页曝光（home UV）</td>
                    <td>{fmt(home_total)}</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td>我的页面曝光（mine UV）</td>
                    <td>{fmt(mine_total)}</td>
                    <td>{pct(mine_total, home_total)}</td>
                </tr>
                <tr>
                    <td>购买 Coffee Pass</td>
                    <td class="highlight">{fmt(total_buyers)}</td>
                    <td class="highlight">{pct(total_buyers, home_total)} (vs home)<br>{pct(total_buyers, mine_total)} (vs mine)</td>
                </tr>
            </table>
        </div>
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">购买者购买日页面访问路径</h4>
            <table>
                <tr><th>页面</th><th>购买者中访问过</th><th>覆盖率</th></tr>'''

# buyer path rows
buyer_path_pages = [
    ("home", "首页"),
    ("menu", "菜单页"),
    ("productdetail", "商品详情"),
    ("confirmorder", "确认订单"),
    ("orderdetail", "订单详情"),
    ("mine", "我的"),
    ("H5luckydaypage", "H5活动页"),
    ("LKIDialogWebController", "弹窗/Webview"),
]
for key, label in buyer_path_pages:
    uv_val = buyer_page_map.get(key, 0)
    html += f'''
                <tr><td>{label}</td><td>{fmt(uv_val)}</td><td>{pct(uv_val, total_buyers)}</td></tr>'''

html += f'''
            </table>
            <div class="insight">
                购买者页面路径显示大部分通过<strong>标准购买路径</strong>（home → menu → productdetail → confirmorder）完成购买。<br><br>
                <strong>首页 Banner → 购买转化率约 {pct(total_buyers, home_total)}</strong>，
                转化率偏低，建议增加弹窗、Push 等强势曝光手段提升触达效率。<br>
                <em style="color:var(--text2); font-size:12px">注: 精确活动页曝光/点击需从 v_hmonitor_track_event_rt 表查（API 超时），建议在 CyberData 网页端手动跑 SQL 补充。</em>
            </div>
        </div>
    </div>
    <div style="margin-top:16px">
        <h4 style="margin-bottom:12px; color:var(--text2)">每日页面 UV vs 购买人数趋势</h4>
        <div class="chart-container"><canvas id="funnelTrendChart"></canvas></div>
    </div>
</div>

<!-- 模块1: 销售数据 -->
<div class="section">
    <div class="section-title"><span class="num">1</span>销售数据</div>
    <div class="two-col">
        <div>
            <div class="chart-container"><canvas id="salesChart"></canvas></div>
        </div>
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">人均购买份数分布</h4>
            <table>
                <tr><th>购买份数</th><th>用户数</th><th>占比</th></tr>
'''

for r in q1b:
    packs_val = int(float(r["packs"]))
    uc = int(r["user_cnt"])
    html += f'                <tr><td>{packs_val} 份</td><td>{fmt(uc)}</td><td>{pct(uc, total_buyers)}</td></tr>\n'

html += f'''            </table>
            <div class="insight">
                <strong>94%</strong> 用户仅购买 1 份（5张券），复购率较低。有 {int(float(q1b[1]["user_cnt"])) if len(q1b)>1 else 0} 人购买 2 份，显示券包有一定吸引力但尚未形成复购习惯。
            </div>
        </div>
    </div>
</div>

<!-- 模块2: 券核销分析 -->
<div class="section">
    <div class="section-title"><span class="num">2</span>券核销分析</div>
    <div class="two-col">
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">核销概况</h4>
            <table>
                <tr><th>状态</th><th>券数</th><th>涉及用户</th><th>占比</th></tr>
'''
for r in q2:
    status_label = "已核销" if r["use_status"] == "1" else "未使用"
    cls = "good" if r["use_status"] == "1" else "warn"
    html += f'                <tr><td><span class="{cls}">{status_label}</span></td><td>{fmt(r["cnt"])}</td><td>{fmt(r["user_cnt"])}</td><td>{pct(r["cnt"], total_coupons)}</td></tr>\n'

html += f'''            </table>
            <h4 style="margin: 16px 0 12px; color:var(--text2)">人均核销张数分布</h4>
            <table>
                <tr><th>核销张数</th><th>用户数</th><th>占比</th></tr>
'''
for r in q2b:
    uc_val = int(r["used_cnt"])
    label = f'{uc_val} 张'
    html += f'                <tr><td>{label}</td><td>{fmt(r["user_cnt"])}</td><td>{pct(r["user_cnt"], total_buyers)}</td></tr>\n'

html += f'''            </table>
        </div>
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">核销时效分布</h4>
            <div class="chart-container"><canvas id="timingChart"></canvas></div>
            <table>
                <tr><th>时间段</th><th>核销张数</th><th>占比</th></tr>
                <tr><td>当天 (D0)</td><td>{fmt(day0_cnt)}</td><td>{pct(day0_cnt, used_cnt)}</td></tr>
                <tr><td>第 1 周 (D0-D7)</td><td>{fmt(week1)}</td><td>{pct(week1, used_cnt)}</td></tr>
                <tr><td>第 2 周 (D8-D14)</td><td>{fmt(week2)}</td><td>{pct(week2, used_cnt)}</td></tr>
                <tr><td>第 3 周 (D15-D21)</td><td>{fmt(week3)}</td><td>{pct(week3, used_cnt)}</td></tr>
                <tr><td>3 周后</td><td>{fmt(after3w)}</td><td>{pct(after3w, used_cnt)}</td></tr>
            </table>
            <div class="insight">
                <strong>{pct(day0_cnt, used_cnt)}</strong> 用户当天即核销第一张券，<strong>{pct(week1, used_cnt)}</strong> 在首周完成核销。
                券有效期 21 天足够，但仍有 {fmt(after3w)} 张在 3 周后才使用。
            </div>
        </div>
    </div>
</div>

<!-- 模块3: 门店分布 -->
<div class="section">
    <div class="section-title"><span class="num">3</span>核销门店 TOP 8</div>
    <div class="two-col">
        <div class="chart-container" style="height:280px"><canvas id="shopChart"></canvas></div>
        <div>
            <table>
                <tr><th>门店</th><th>核销单数</th><th>用户数</th></tr>
'''
for r in q5[:8]:
    html += f'                <tr><td>{r["shop_name"]}</td><td>{fmt(r["order_cnt"])}</td><td>{fmt(r["user_cnt"])}</td></tr>\n'

html += f'''            </table>
            <div class="insight">
                核销高度集中在纽约核心商圈门店。<strong>8th & Broadway</strong> 以 {fmt(q5[0]["order_cnt"])} 单领先，
                前 5 名门店贡献了大部分核销量。
            </div>
        </div>
    </div>
</div>

<!-- 模块4: 用户画像 -->
<div class="section">
    <div class="section-title"><span class="num">4</span>购买用户画像</div>
    <div class="two-col">
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">用户类型分布</h4>
            <table>
                <tr><th>用户类型</th><th>人数</th><th>占比</th><th>前30天均单数</th></tr>
'''
for r in q6:
    html += f'                <tr><td>{r["user_type"]}</td><td>{fmt(r["user_cnt"])}</td><td>{pct(r["user_cnt"], total_buyers)}</td><td>{r["avg_prior_orders"]}</td></tr>\n'

html += f'''            </table>
            <div class="insight">
                购买者以 <strong>老客为主（72.5%）</strong>，前30天人均消费 8.1 单。
                仅 {int(next((r["user_cnt"] for r in q6 if r["user_type"] == "新客"), 0))} 位新客购买，
                说明 Coffee Pass 更适合激励存量用户提频，而非拉新。
            </div>
        </div>
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">购买前 30 天消费频次分布</h4>
            <div class="chart-container"><canvas id="freqChart"></canvas></div>
        </div>
    </div>
</div>

<!-- 模块5: 前后消费对比 -->
<div class="section">
    <div class="section-title"><span class="num">5</span>增量价值评估 — 购买前后消费对比</div>
    <div class="two-col">
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">14 天窗口</h4>
            <table>
                <tr><th>对比维度</th><th>前 14 天</th><th>后 14 天</th><th>变化</th></tr>
                <tr><td>有消费用户</td><td>{before14.get("active_users","0")}/{before14.get("total_buyers","0")}</td><td>{after14.get("active_users","0")}/{after14.get("total_buyers","0")}</td><td><span class="good">+{int(after14.get("active_users",0))-int(before14.get("active_users",0))}</span></td></tr>
                <tr><td>总订单数</td><td>{fmt(before14.get("total_orders",0))}</td><td>{fmt(after14.get("total_orders",0))}</td><td><span class="good">+{int(after14.get("total_orders",0))-int(before14.get("total_orders",0))} ({(int(after14.get("total_orders",0))-int(before14.get("total_orders",0)))/max(int(before14.get("total_orders",0)),1)*100:.0f}%)</span></td></tr>
                <tr><td>人均订单数</td><td>{before14.get("avg_orders","-")}</td><td>{after14.get("avg_orders","-")}</td><td><span class="good">+{float(after14.get("avg_orders",0))-float(before14.get("avg_orders",0)):.1f}</span></td></tr>
                <tr><td>总消费金额</td><td>${fmt(before14.get("total_pay",0),2)}</td><td>${fmt(after14.get("total_pay",0),2)}</td><td>'''

pay14 = float(after14.get("total_pay",0)) - float(before14.get("total_pay",0))
pay14_cls = "good" if pay14 >= 0 else "bad"
pay14_sign = "+" if pay14 >= 0 else ""

html += f'''<span class="{pay14_cls}">{pay14_sign}${pay14:,.2f}</span></td></tr>
            </table>
        </div>
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">30 天窗口</h4>
            <table>
                <tr><th>对比维度</th><th>前 30 天</th><th>后 30 天</th><th>变化</th></tr>
                <tr><td>有消费用户</td><td>{before30.get("active_users","0")}/{before30.get("total_buyers","0")}</td><td>{after30.get("active_users","0")}/{after30.get("total_buyers","0")}</td><td><span class="good">+{int(after30.get("active_users",0))-int(before30.get("active_users",0))}</span></td></tr>
                <tr><td>总订单数</td><td>{fmt(before30.get("total_orders",0))}</td><td>{fmt(after30.get("total_orders",0))}</td><td><span class="good">+{int(after30.get("total_orders",0))-int(before30.get("total_orders",0))} ({(int(after30.get("total_orders",0))-int(before30.get("total_orders",0)))/max(int(before30.get("total_orders",0)),1)*100:.0f}%)</span></td></tr>
                <tr><td>人均订单数</td><td>{before30.get("avg_orders","-")}</td><td>{after30.get("avg_orders","-")}</td><td><span class="good">+{float(after30.get("avg_orders",0))-float(before30.get("avg_orders",0)):.1f}</span></td></tr>
                <tr><td>总消费金额</td><td>${fmt(before30.get("total_pay",0),2)}</td><td>${fmt(after30.get("total_pay",0),2)}</td><td>'''

pay30 = float(after30.get("total_pay",0)) - float(before30.get("total_pay",0))
pay30_cls = "good" if pay30 >= 0 else "bad"
pay30_sign = "+" if pay30 >= 0 else ""

html += f'''<span class="{pay30_cls}">{pay30_sign}${pay30:,.2f}</span></td></tr>
            </table>
        </div>
    </div>
    <div class="insight">
        <strong>14 天窗口</strong>：订单 +{int(after14.get("total_orders",0))-int(before14.get("total_orders",0))}（+{(int(after14.get("total_orders",0))-int(before14.get("total_orders",0)))/max(int(before14.get("total_orders",0)),1)*100:.0f}%），
        金额 {pay14_sign}${abs(pay14):,.2f}（{pay14_sign}{abs(pay14)/max(float(before14.get("total_pay",0)),0.01)*100:.0f}%），人均 {before14.get("avg_orders","-")} → {after14.get("avg_orders","-")} 单。<br>
        <strong>30 天窗口</strong>：订单 +{int(after30.get("total_orders",0))-int(before30.get("total_orders",0))}（+{(int(after30.get("total_orders",0))-int(before30.get("total_orders",0)))/max(int(before30.get("total_orders",0)),1)*100:.0f}%），
        金额 {pay30_sign}${abs(pay30):,.2f}（{pay30_sign}{abs(pay30)/max(float(before30.get("total_pay",0)),0.01)*100:.0f}%），人均 {before30.get("avg_orders","-")} → {after30.get("avg_orders","-")} 单。<br>
        购买后 <strong>100% 用户有消费</strong>（含 Coffee Pass 核销订单）。<br>
        <strong>结论：两个窗口均显示频次和金额双升，Coffee Pass 提频提活效果确定。</strong>
    </div>
</div>'''

html += '''
<!-- 模块6: 退款/过期 -->
<div class="section">
    <div class="section-title"><span class="num">6</span>未用完 / 过期分析</div>
    <div class="two-col">
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">券状态汇总</h4>
            <table>
                <tr><th>状态</th><th>券数</th><th>涉及用户</th></tr>
'''
for r in q8:
    cls = "good" if "核销" in r["coupon_state"] else "warn"
    html += f'                <tr><td><span class="{cls}">{r["coupon_state"]}</span></td><td>{fmt(r["cnt"])}</td><td>{fmt(r["user_cnt"])}</td></tr>\n'

html += f'''            </table>
        </div>
        <div>
            <h4 style="margin-bottom:12px; color:var(--text2)">按人统计未用完张数</h4>
            <table>
                <tr><th>未用完张数</th><th>用户数</th><th>占比</th></tr>
'''
for r in q8b:
    label = f'{int(r["unused_cnt"])} 张' if int(r["unused_cnt"]) > 0 else "全部用完"
    cls = "good" if int(r["unused_cnt"]) == 0 else ("warn" if int(r["unused_cnt"]) <= 2 else "bad")
    html += f'                <tr><td><span class="{cls}">{label}</span></td><td>{fmt(r["user_cnt"])}</td><td>{pct(r["user_cnt"], total_buyers)}</td></tr>\n'

# 潜在退款
unused_total = int(unused_cnt)
potential_refund = unused_total * 19.9 / 5  # 按比例退

html += f'''            </table>
            <div class="insight">
                <strong>{fmt(q8b[0]["user_cnt"])}</strong> 人（{pct(q8b[0]["user_cnt"], total_buyers)}）用完全部券。
                {unused_total} 张券未使用，若按比例退款预计 <strong>${potential_refund:,.2f}</strong>。
                有 {sum(int(r["user_cnt"]) for r in q8b if int(r["unused_cnt"]) == 5)} 人购买后完全未使用。
            </div>
        </div>
    </div>
</div>

<!-- 模块7: 复购行为 -->
<div class="section">
    <div class="section-title"><span class="num">7</span>活动后复购行为 (02-16 ~ 03-08)</div>
    <table>
        <tr>
            <th>用户分组</th>
            <th>用户数</th>
            <th>活动后有消费</th>
            <th>回店率</th>
            <th>总订单</th>
            <th>人均订单</th>
            <th>总消费</th>
        </tr>
        <tr>
            <td><span class="tag tag-green">全部用完</span></td>
            <td>{fmt(full_used.get("total_users", 0))}</td>
            <td>{fmt(full_used.get("active_users", 0))}</td>
            <td><span class="good">{full_used.get("return_rate", "-")}%</span></td>
            <td>{fmt(full_used.get("total_orders", 0))}</td>
            <td>{full_used.get("avg_orders", "-")}</td>
            <td>${fmt(full_used.get("total_pay", 0), 2)}</td>
        </tr>
        <tr>
            <td><span class="tag tag-yellow">未用完</span></td>
            <td>{fmt(not_used.get("total_users", 0))}</td>
            <td>{fmt(not_used.get("active_users", 0))}</td>
            <td><span class="warn">{not_used.get("return_rate", "-")}%</span></td>
            <td>{fmt(not_used.get("total_orders", 0))}</td>
            <td>{not_used.get("avg_orders", "-")}</td>
            <td>${fmt(not_used.get("total_pay", 0), 2)}</td>
        </tr>
    </table>
    <div class="insight">
        用完 5 张券的用户回店率 <strong>{full_used.get("return_rate", "-")}%</strong>，人均再消费 <strong>{full_used.get("avg_orders", "-")} 单</strong>，
        远高于未用完用户的 {not_used.get("return_rate", "-")}% 和 {not_used.get("avg_orders", "-")} 单。
        <strong>券包消费完整度与后续黏性强相关</strong>，建议通过推送提醒未用完用户核销剩余券。
    </div>
</div>

<!-- 结论与建议 -->
<div class="summary-box">
    <h2>结论与建议</h2>
    <ul>
        <li><strong>规模有限但质量不错</strong>：本轮 {fmt(total_buyers)} 位用户购买了 {fmt(total_packs)} 份券包，总收入 ${fmt(total_revenue, 0)}。核销率 {redeem_rate:.1f}% 表明用户认可券包价值。</li>
        <li><strong>老客驱动</strong>：72.5% 购买者是 30 天+ 老客，人均前30天已消费 8.1 单。Coffee Pass 是存量提频工具而非拉新手段。</li>
        <li><strong>提频效果显著</strong>：30 天窗口人均订单从 {before30.get("avg_orders","-")} 提升至 {after30.get("avg_orders","-")}（+{float(after30.get("avg_orders",0))-float(before30.get("avg_orders",0)):.1f}），14 天窗口人均 {before14.get("avg_orders","-")} → {after14.get("avg_orders","-")}（+{float(after14.get("avg_orders",0))-float(before14.get("avg_orders",0)):.1f}），两个窗口均确认提频。</li>
        <li><strong>用完即复购</strong>：{full_used.get("return_rate","-")}% 用完所有券的用户在活动后继续消费，人均 {full_used.get("avg_orders","-")} 单。未用完用户回店率仅 {not_used.get("return_rate","-")}%，人均 {not_used.get("avg_orders","-")} 单。</li>
        <li><strong>21天有效期适中</strong>：{pct(day0_cnt, used_cnt)} 当天核销，{pct(week1, used_cnt)} 在首周完成。</li>
    </ul>
    <h2 style="margin-top:16px">优化建议</h2>
    <ul>
        <li><strong>提醒未核销用户</strong>：{unused_cnt} 张券未使用（{sum(int(r["user_cnt"]) for r in q8b if int(r["unused_cnt"]) > 0)} 位用户），可通过 Push/SMS 在到期前 3 天提醒。</li>
        <li><strong>扩大触达面</strong>：102 人规模偏小，考虑增加首页弹窗、我的页面入口等更强势资源位。</li>
        <li><strong>分层定价</strong>：高频用户（10单+）占 24.8%，可考虑推出更高性价比的 10 杯装；低频用户（0-2单）推 3 杯尝鲜装。</li>
        <li><strong>设定复购引导</strong>：用户用完 5 张券后，自动推送下一轮 Coffee Pass 购买入口，抓住高黏性窗口。</li>
    </ul>
</div>

</div>

<script>
// 漏斗柱状图 (汇总)
new Chart(document.getElementById('funnelChart'), {{
    type: 'bar',
    data: {{
        labels: ['首页 UV', '我的 UV', '购买者'],
        datasets: [{{
            data: [{home_total}, {mine_total}, {total_buyers}],
            backgroundColor: ['rgba(56,189,248,0.5)', 'rgba(167,139,250,0.5)', 'rgba(74,222,128,0.7)'],
            borderRadius: 6,
            barThickness: 50
        }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(51,65,85,0.3)' }} }},
            y: {{ ticks: {{ color: '#e2e8f0', font: {{ size: 13 }} }}, grid: {{ display: false }} }}
        }}
    }}
}});

// 漏斗趋势图 (按日)
new Chart(document.getElementById('funnelTrendChart'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(funnel_dates_js)},
        datasets: [{{
            label: '首页 UV',
            data: {json.dumps(funnel_home_js)},
            borderColor: '#38bdf8',
            backgroundColor: 'transparent',
            tension: 0.3, pointRadius: 3, yAxisID: 'y'
        }}, {{
            label: '我的 UV',
            data: {json.dumps(funnel_mine_js)},
            borderColor: '#a78bfa',
            backgroundColor: 'transparent',
            tension: 0.3, pointRadius: 3, yAxisID: 'y'
        }}, {{
            label: '购买人数',
            data: {json.dumps(funnel_buyers_js)},
            type: 'bar',
            backgroundColor: 'rgba(74,222,128,0.6)',
            borderRadius: 4, yAxisID: 'y1'
        }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
        scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(51,65,85,0.3)' }} }},
            y: {{ position: 'left', ticks: {{ color: '#38bdf8' }}, grid: {{ color: 'rgba(51,65,85,0.3)' }}, title: {{ display: true, text: '页面 UV', color: '#38bdf8' }} }},
            y1: {{ position: 'right', ticks: {{ color: '#4ade80' }}, grid: {{ display: false }}, title: {{ display: true, text: '购买人数', color: '#4ade80' }} }}
        }}
    }}
}});

// 销售趋势图
new Chart(document.getElementById('salesChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(sales_dates)},
        datasets: [{{
            label: '售出份数',
            data: {json.dumps(sales_packs)},
            backgroundColor: 'rgba(56,189,248,0.6)',
            borderRadius: 4,
            yAxisID: 'y'
        }}, {{
            label: '购买人数',
            data: {json.dumps(sales_buyers)},
            type: 'line',
            borderColor: '#fbbf24',
            backgroundColor: 'transparent',
            pointRadius: 4,
            pointBackgroundColor: '#fbbf24',
            tension: 0.3,
            yAxisID: 'y1'
        }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
        scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(51,65,85,0.5)' }} }},
            y: {{ position: 'left', ticks: {{ color: '#38bdf8' }}, grid: {{ color: 'rgba(51,65,85,0.5)' }}, title: {{ display: true, text: '份数', color: '#38bdf8' }} }},
            y1: {{ position: 'right', ticks: {{ color: '#fbbf24' }}, grid: {{ display: false }}, title: {{ display: true, text: '人数', color: '#fbbf24' }} }}
        }}
    }}
}});

// 核销时效图
new Chart(document.getElementById('timingChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps([f'D{d}' for d in timing_days])},
        datasets: [{{
            label: '核销张数',
            data: {json.dumps(timing_cnts)},
            backgroundColor: 'rgba(74,222,128,0.5)',
            borderRadius: 3
        }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ ticks: {{ color: '#94a3b8', maxRotation: 0 }}, grid: {{ display: false }} }},
            y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(51,65,85,0.5)' }} }}
        }}
    }}
}});

// 门店分布图
new Chart(document.getElementById('shopChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(shop_names_js)},
        datasets: [{{
            label: '核销单数',
            data: {json.dumps(shop_orders_js)},
            backgroundColor: ['rgba(56,189,248,0.6)','rgba(167,139,250,0.6)','rgba(251,191,36,0.6)','rgba(74,222,128,0.6)','rgba(248,113,113,0.6)','rgba(251,146,60,0.6)','rgba(56,189,248,0.4)','rgba(167,139,250,0.4)'],
            borderRadius: 4
        }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(51,65,85,0.5)' }} }},
            y: {{ ticks: {{ color: '#e2e8f0', font: {{ size: 11 }} }}, grid: {{ display: false }} }}
        }}
    }}
}});

// 频次分布图
const freqLabels = {json.dumps([r["freq_bucket"] for r in q6b])};
const freqData = {json.dumps([int(r["user_cnt"]) for r in q6b])};
new Chart(document.getElementById('freqChart'), {{
    type: 'doughnut',
    data: {{
        labels: freqLabels,
        datasets: [{{
            data: freqData,
            backgroundColor: ['rgba(248,113,113,0.7)','rgba(251,191,36,0.7)','rgba(56,189,248,0.7)','rgba(74,222,128,0.7)','rgba(167,139,250,0.7)'],
            borderWidth: 0
        }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{
            legend: {{ position: 'right', labels: {{ color: '#94a3b8', padding: 8, font: {{ size: 12 }} }} }}
        }}
    }}
}});
</script>

</body>
</html>
'''

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"报告已生成: {OUTPUT_FILE}")
