"""
0212 涨价实验报告 — 更新至 2026-03-04
自动通过 CyberData API 跑数 + 生成报告
"""
import requests, json, time, sys, os
import pandas as pd
import numpy as np

# ============================================================
# 日期配置 — 更新到 3/4
# ============================================================
EXP_START = '2026-02-12'
EXP_END = '2026-03-04'
EXP_END_NEXT = '2026-03-05'
DT_LATEST = '2026-02-28'  # 人群标签表快照日期
REPURCHASE_3D_CUTOFF = '2026-03-01'  # 需 +3天窗口
REPURCHASE_7D_CUTOFF = '2026-02-25'  # 需 +7天窗口

# ============================================================
# CyberData API
# ============================================================
BASE_URL = "https://idpcd.luckincoffee.us"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json; charset=UTF-8",
    "jwttoken": "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFMyNTYifQ.eyJyb2wiOnsiQUxMIjpbNF0sIkN5YmVyRGF0YSI6WzRdfSwianRpIjoiMTAwMSw0NyIsImlzcyI6IlNuYWlsQ2xpbWIiLCJpYXQiOjE3NzI2ODEwODgsInN1YiI6IuadjuWutemchCxudWxsLGxpeGlhb3hpYW8iLCJhdWQiOiJbe1wicm9sZUlkXCI6NCxcInZlcnNpb25OYW1lXCI6XCJDeWJlckRhdGFcIixcInZlcnNpb25JZFwiOjMsXCJyb2xlTmFtZVwiOlwiRGF0YUJhc2ljUm9sZVwifV0ifQ.5g6rohLs83835-qHAfE-CLMzPtONC1IggxxDNa04g_E",
    "productkey": "CyberData",
    "origin": "https://idpcd.luckincoffee.us",
    "lang": "zh-CN",
}
COOKIES = {
    "iluckyauth_session_prod": "MTc3MjU4OTkzNXxOd3dBTkRaRVNFMHlORVpEU2toSE0wRkZOMWRITkV0Vk0wWldRMWhRU0ZZM1NsVXpSVFJKTkVJMlJ6Vk5RVkJLU0RSWVZGUTJWMEU9fD_bdtlbeZ1kz04XJIVa89Nv0Oc1Iph6QGXfT8rrwucC"
}
TASK_PAYLOAD_BASE = {
    "tenantId": "1001", "userId": "47",
    "projectId": "1906904360294313985", "resourceGroupId": 1,
    "taskId": "2025093402876882945", "variables": {}, "env": 5,
}

def submit_sql(sql, label=""):
    payload = {**TASK_PAYLOAD_BASE, "_t": int(time.time() * 1000), "sqlStatement": sql}
    print(f"\n{'='*60}\n  {label}\n{'='*60}")
    resp = requests.post(f"{BASE_URL}/api/dev/task/run", headers=HEADERS, cookies=COOKIES, json=payload)
    data = resp.json()
    if str(data.get("code")) != "200":
        print(f"  ❌ {data}"); return None
    raw = data.get("data")
    tid = raw if isinstance(raw, str) else str(raw)
    print(f"  ✅ tid: {tid}"); return tid

def get_result(tid, max_wait=300):
    print(f"  ⏳ 等待...")
    for i in range(max_wait // 3):
        time.sleep(3)
        payload = {"_t": int(time.time()*1000), "tenantId":"1001", "userId":"47",
                   "projectId":"1906904360294313985", "env":5, "taskInstanceId":str(tid)}
        resp = requests.post(f"{BASE_URL}/api/logger/getQueryLog", headers=HEADERS, cookies=COOKIES, json=payload)
        rj = resp.json()
        if str(rj.get("code","")) == "401": print("  ❌ Token过期"); return None
        results = rj.get("data", [])
        if not results or not isinstance(results, list):
            if i % 5 == 0: print(f"  ... {(i+1)*3}s"); continue
        record = results[0]
        columns = record.get("columns", [])
        if columns and len(columns) > 0:
            headers = columns[0]; rows = columns[1:] if len(columns) > 1 else []
            print(f"  ✅ {len(rows)} 行"); return {"headers": headers, "rows": rows}
        err = record.get("errorMsg") or record.get("error_msg")
        if err: print(f"  ❌ {str(err)[:200]}"); return None
        if i % 5 == 0: print(f"  ... {(i+1)*3}s")
    print("  ⏰ 超时"); return None

def run_query(sql, label=""):
    tid = submit_sql(sql, label)
    if not tid: return None
    return get_result(tid)

def result_to_df(result):
    if not result: return pd.DataFrame()
    return pd.DataFrame(result["rows"], columns=result["headers"])

# ============================================================
# 公共 CTE（剔除新客）
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

# 7 个 SQL
SQL_1 = COMMON_CTE + "\nSELECT grp, COUNT(*) AS total_users FROM grp_users GROUP BY grp ORDER BY grp"

SQL_2 = COMMON_CTE + f"""
SELECT gu.grp, DATE(o.create_time) AS dt,
    COUNT(DISTINCT o.user_no) AS order_users,
    COUNT(DISTINCT o.id) AS order_cnt,
    ROUND(SUM(o.pay_money), 2) AS revenue
FROM grp_users gu
INNER JOIN ods_luckyus_sales_order.v_order o ON gu.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY gu.grp, DATE(o.create_time) ORDER BY dt, grp"""

SQL_3 = COMMON_CTE + f"""
SELECT gu.grp, dau.dt, COUNT(DISTINCT dau.user_no) AS visit_users
FROM grp_users gu
INNER JOIN dw_dws.dws_mg_log_user_screen_name_d_1d dau ON gu.user_no = dau.user_no
    AND dau.dt >= '{EXP_START}' AND dau.dt <= '{EXP_END}'
GROUP BY gu.grp, dau.dt ORDER BY dau.dt, gu.grp"""

SQL_4 = COMMON_CTE + f""",
exp_orders AS (
    SELECT o.id AS order_id, gu.grp, DATE(o.create_time) AS dt
    FROM grp_users gu
    INNER JOIN ods_luckyus_sales_order.v_order o ON gu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT eo.grp, eo.dt, SUM(item.sku_num) AS cups,
    ROUND(SUM(item.pay_money), 2) AS item_revenue,
    ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS unit_price
FROM exp_orders eo
INNER JOIN ods_luckyus_sales_order.t_order_item item ON eo.order_id = item.order_id
GROUP BY eo.grp, eo.dt ORDER BY eo.dt, eo.grp"""

SQL_5 = COMMON_CTE + f"""
SELECT gu.grp,
    COUNT(DISTINCT o.user_no) AS period_order_users,
    COUNT(DISTINCT o.id) AS period_order_cnt,
    ROUND(SUM(o.pay_money), 2) AS period_revenue
FROM grp_users gu
LEFT JOIN ods_luckyus_sales_order.v_order o ON gu.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY gu.grp ORDER BY gu.grp"""

SQL_6 = COMMON_CTE + f""",
user_daily AS (
    SELECT DISTINCT gu.grp, gu.user_no, DATE(o.create_time) AS order_date
    FROM grp_users gu
    INNER JOIN ods_luckyus_sales_order.v_order o ON gu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT a.grp, a.order_date,
    COUNT(DISTINCT a.user_no) AS day_buyers,
    COUNT(DISTINCT b.user_no) AS repurchase_users,
    ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_3d
FROM user_daily a
LEFT JOIN user_daily b ON a.user_no = b.user_no AND a.grp = b.grp
    AND b.order_date > a.order_date AND DATEDIFF(b.order_date, a.order_date) <= 3
WHERE a.order_date <= '{REPURCHASE_3D_CUTOFF}'
GROUP BY a.grp, a.order_date ORDER BY a.order_date, a.grp"""

SQL_7 = COMMON_CTE + f""",
user_daily AS (
    SELECT DISTINCT gu.grp, gu.user_no, DATE(o.create_time) AS order_date
    FROM grp_users gu
    INNER JOIN ods_luckyus_sales_order.v_order o ON gu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT a.grp, a.order_date,
    COUNT(DISTINCT a.user_no) AS day_buyers,
    COUNT(DISTINCT b.user_no) AS repurchase_users,
    ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_7d
FROM user_daily a
LEFT JOIN user_daily b ON a.user_no = b.user_no AND a.grp = b.grp
    AND b.order_date > a.order_date AND DATEDIFF(b.order_date, a.order_date) <= 7
WHERE a.order_date <= '{REPURCHASE_7D_CUTOFF}'
GROUP BY a.grp, a.order_date ORDER BY a.order_date, a.grp"""


def main():
    print(f"📊 0212涨价实验报告更新 ({EXP_START} ~ {EXP_END})")
    print(f"   剔除新客，仅老客\n")

    queries = [
        ("Q1: 各组老客用户数", SQL_1),
        ("Q2: 每日订单指标", SQL_2),
        ("Q3: 每日访问人数", SQL_3),
        ("Q4: 每日杯量与单杯实收", SQL_4),
        ("Q5: 汇总期间独立指标", SQL_5),
        ("Q6: 3日复购率", SQL_6),
        ("Q7: 7日复购率", SQL_7),
    ]

    # 如果指定参数，只跑对应的查询
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        idx = int(sys.argv[1])
        queries = [queries[idx]]

    dfs = {}
    for label, sql in queries:
        result = run_query(sql, label)
        df = result_to_df(result)
        key = label.split(":")[0].strip()
        dfs[key] = df

        # 打印前几行
        if not df.empty:
            print(df.head(6).to_string(index=False))
        print()

    # 保存原始数据为 JSON（供后续使用）
    raw_data = {}
    for k, df in dfs.items():
        raw_data[k] = df.to_dict(orient='records')

    json_path = "/Users/xiaoxiao/Vibe coding/0212_report_data_0304.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
    print(f"📄 原始数据: {json_path}")

    # 如果只跑了部分查询，跳过报告生成
    if len(dfs) < 7:
        print("⚠️ 未跑全部查询，跳过报告生成")
        return

    # ============================================================
    # 生成报告
    # ============================================================
    df_sizes = dfs["Q1"]
    daily_orders = dfs["Q2"]
    daily_visits = dfs["Q3"]
    daily_cups = dfs["Q4"]
    period_summary = dfs["Q5"]
    daily_rep_3d = dfs["Q6"]
    daily_rep_7d = dfs["Q7"]

    # 类型转换
    for df, col in [(daily_orders, 'dt'), (daily_visits, 'dt'), (daily_cups, 'dt')]:
        df[col] = df[col].astype(str)
    daily_rep_3d['order_date'] = daily_rep_3d['order_date'].astype(str)
    daily_rep_7d['order_date'] = daily_rep_7d['order_date'].astype(str)

    for col in ['order_users', 'order_cnt']:
        daily_orders[col] = pd.to_numeric(daily_orders[col])
    daily_orders['revenue'] = pd.to_numeric(daily_orders['revenue'])
    daily_visits['visit_users'] = pd.to_numeric(daily_visits['visit_users'])
    daily_cups['cups'] = pd.to_numeric(daily_cups['cups'])
    daily_cups['item_revenue'] = pd.to_numeric(daily_cups['item_revenue'])
    daily_cups['unit_price'] = pd.to_numeric(daily_cups['unit_price'])
    daily_rep_3d['repurchase_rate_3d'] = pd.to_numeric(daily_rep_3d['repurchase_rate_3d'])
    daily_rep_7d['repurchase_rate_7d'] = pd.to_numeric(daily_rep_7d['repurchase_rate_7d'])
    period_summary['period_order_users'] = pd.to_numeric(period_summary['period_order_users'])
    period_summary['period_revenue'] = pd.to_numeric(period_summary['period_revenue'])

    size_col = 'total_users'
    group_sizes = dict(zip(df_sizes['grp'], df_sizes[size_col].astype(int)))

    # === 导入原始脚本的报告生成函数 ===
    sys.path.insert(0, '/Users/xiaoxiao/Vibe coding')
    from importlib import import_module
    orig = import_module('0212_pricing_experiment')

    # 覆盖日期配置
    orig.EXP_START = EXP_START
    orig.EXP_END = EXP_END

    daily_df = orig.build_daily_table(group_sizes, daily_orders, daily_visits, daily_cups, daily_rep_3d, daily_rep_7d)
    summary_row = orig.build_summary_row(group_sizes, period_summary, daily_visits, daily_cups, daily_rep_3d, daily_rep_7d)
    normalized = orig.build_normalized_comparison(summary_row, group_sizes)

    md = orig.generate_markdown_report(daily_df, summary_row, normalized, group_sizes)
    html = orig.generate_html_report(daily_df, summary_row, normalized, group_sizes)

    output_dir = '/Users/xiaoxiao/Vibe coding'
    md_path = f'{output_dir}/0212涨价实验报告_0212-0304.md'
    html_path = f'{output_dir}/0212涨价实验报告_0212-0304.html'

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ 报告已生成:")
    print(f"   MD:   {md_path}")
    print(f"   HTML: {html_path}")

    # 打印核心指标
    print(f"\n{'='*60}")
    print(f"  核心指标汇总 ({EXP_START} ~ {EXP_END})")
    print(f"{'='*60}")
    for grp in ['涨价组1', '涨价组2', '对照组3']:
        total = group_sizes[grp]
        users = summary_row.get(f'{grp}_下单用户', 0)
        cups = summary_row.get(f'{grp}_杯量', 0)
        rev = summary_row.get(f'{grp}_实收', 0)
        unit = summary_row.get(f'{grp}_单杯实收', 0)
        conv = summary_row.get(f'{grp}_转化率', '-')
        rep3 = summary_row.get(f'{grp}_3日复购率', '-')
        rep7 = summary_row.get(f'{grp}_7日复购率', '-')
        print(f"\n  {grp} ({total:,}人):")
        print(f"    转化率: {conv}  下单用户: {users:,}")
        print(f"    杯量: {cups:,}  单杯实收: ${unit}")
        print(f"    总实收: ${rev:,.2f}")
        print(f"    3日复购: {rep3}  7日复购: {rep7}")

    # 拉齐对比
    print(f"\n{'='*60}")
    print(f"  拉齐后对比（vs 对照组3）")
    print(f"{'='*60}")
    for norm in normalized:
        print(f"\n  {norm['日期']}:")
        for m in ['杯量', '实收', '单杯实收', '转化率', '3日复购率', '7日复购率']:
            diff = norm.get(f'{m}_差异', '-')
            print(f"    {m}: {diff}")


if __name__ == "__main__":
    main()
