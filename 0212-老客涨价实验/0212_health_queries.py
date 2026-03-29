"""
0212涨价实验 — 业务健康度：每日来访/消费用户的生命周期结构
"""
import requests, json, time, sys

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
    print(f"\n{'='*60}\n  提交: {label}\n{'='*60}")
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

# ============================================================
# 公共 CTE
# ============================================================
GRP_CTE = """
WITH grp_users AS (
    SELECT DISTINCT g.user_no,
        CASE
            WHEN g.group_name LIKE '%涨价组1%' THEN '涨价组1'
            WHEN g.group_name LIKE '%涨价组2%' THEN '涨价组2'
            WHEN g.group_name LIKE '%对照组3%' THEN '对照组3'
        END AS grp
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    WHERE g.tenant = 'LKUS' AND g.dt = '2026-02-28'
        AND (g.group_name LIKE '%0212价格实验%涨价组1%'
          OR g.group_name LIKE '%0212价格实验%涨价组2%'
          OR g.group_name LIKE '%0212价格实验%对照组3%')
),
user_first_order AS (
    SELECT user_no, MIN(DATE(create_time)) AS first_order_date
    FROM ods_luckyus_sales_order.v_order
    WHERE status = 90 AND INSTR(tenant, 'IQ') = 0
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY user_no
)
"""

# ============================================================
# H1: 每日来访用户 × 组 × 生命周期
# ============================================================
SQL_H1_DAILY_VISITORS = GRP_CTE + """,
daily_visit AS (
    SELECT dt, user_no
    FROM dw_dws.dws_mg_log_user_screen_name_d_1d
    WHERE dt >= '2026-02-12' AND dt <= '2026-02-28'
    GROUP BY dt, user_no
)
SELECT
    dv.dt,
    gu.grp,
    CASE
        WHEN ufo.first_order_date IS NULL THEN '未购'
        WHEN DATEDIFF(dv.dt, ufo.first_order_date) <= 15 THEN '0-15天'
        WHEN DATEDIFF(dv.dt, ufo.first_order_date) <= 30 THEN '16-30天'
        ELSE '31天+'
    END AS lifecycle,
    COUNT(DISTINCT dv.user_no) AS visitor_cnt
FROM daily_visit dv
INNER JOIN grp_users gu ON dv.user_no = gu.user_no
LEFT JOIN user_first_order ufo ON dv.user_no = ufo.user_no
GROUP BY dv.dt, gu.grp, lifecycle
ORDER BY dv.dt, gu.grp,
    CASE lifecycle WHEN '0-15天' THEN 1 WHEN '16-30天' THEN 2 WHEN '31天+' THEN 3 ELSE 4 END
"""

# ============================================================
# H2: 每日消费用户 × 组 × 生命周期（含杯量、实收）
# ============================================================
SQL_H2_DAILY_CONSUMERS = GRP_CTE + """,
daily_orders AS (
    SELECT
        DATE(o.create_time) AS dt,
        o.user_no,
        SUM(item.sku_num) AS cups,
        SUM(item.pay_money) AS revenue
    FROM ods_luckyus_sales_order.v_order o
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY DATE(o.create_time), o.user_no
)
SELECT
    do2.dt,
    gu.grp,
    CASE
        WHEN ufo.first_order_date IS NULL THEN '未购'
        WHEN DATEDIFF(do2.dt, ufo.first_order_date) <= 15 THEN '0-15天'
        WHEN DATEDIFF(do2.dt, ufo.first_order_date) <= 30 THEN '16-30天'
        ELSE '31天+'
    END AS lifecycle,
    COUNT(DISTINCT do2.user_no) AS buyer_cnt,
    SUM(do2.cups) AS total_cups,
    ROUND(SUM(do2.revenue), 2) AS total_revenue,
    ROUND(SUM(do2.revenue) / NULLIF(SUM(do2.cups), 0), 2) AS unit_price
FROM daily_orders do2
INNER JOIN grp_users gu ON do2.user_no = gu.user_no
LEFT JOIN user_first_order ufo ON do2.user_no = ufo.user_no
GROUP BY do2.dt, gu.grp, lifecycle
ORDER BY do2.dt, gu.grp,
    CASE lifecycle WHEN '0-15天' THEN 1 WHEN '16-30天' THEN 2 WHEN '31天+' THEN 3 ELSE 4 END
"""

# ============================================================
# H3: 每日总来访 × 总消费（不分组，看大盘趋势）
# ============================================================
SQL_H3_DAILY_OVERALL = GRP_CTE + """,
daily_visit AS (
    SELECT dt, user_no
    FROM dw_dws.dws_mg_log_user_screen_name_d_1d
    WHERE dt >= '2026-02-12' AND dt <= '2026-02-28'
    GROUP BY dt, user_no
),
daily_visitors_lc AS (
    SELECT
        dv.dt,
        CASE
            WHEN ufo.first_order_date IS NULL THEN '未购'
            WHEN DATEDIFF(dv.dt, ufo.first_order_date) <= 15 THEN '0-15天'
            WHEN DATEDIFF(dv.dt, ufo.first_order_date) <= 30 THEN '16-30天'
            ELSE '31天+'
        END AS lifecycle,
        COUNT(DISTINCT dv.user_no) AS visitor_cnt
    FROM daily_visit dv
    INNER JOIN grp_users gu ON dv.user_no = gu.user_no
    LEFT JOIN user_first_order ufo ON dv.user_no = ufo.user_no
    GROUP BY dv.dt, lifecycle
),
daily_orders AS (
    SELECT DATE(o.create_time) AS dt, o.user_no,
        SUM(item.sku_num) AS cups, SUM(item.pay_money) AS revenue
    FROM ods_luckyus_sales_order.v_order o
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY DATE(o.create_time), o.user_no
),
daily_consumers_lc AS (
    SELECT
        do2.dt,
        CASE
            WHEN ufo.first_order_date IS NULL THEN '未购'
            WHEN DATEDIFF(do2.dt, ufo.first_order_date) <= 15 THEN '0-15天'
            WHEN DATEDIFF(do2.dt, ufo.first_order_date) <= 30 THEN '16-30天'
            ELSE '31天+'
        END AS lifecycle,
        COUNT(DISTINCT do2.user_no) AS buyer_cnt,
        SUM(do2.cups) AS total_cups,
        ROUND(SUM(do2.revenue), 2) AS total_revenue
    FROM daily_orders do2
    INNER JOIN grp_users gu ON do2.user_no = gu.user_no
    LEFT JOIN user_first_order ufo ON do2.user_no = ufo.user_no
    GROUP BY do2.dt, lifecycle
)
SELECT
    COALESCE(v.dt, c.dt) AS dt,
    COALESCE(v.lifecycle, c.lifecycle) AS lifecycle,
    COALESCE(v.visitor_cnt, 0) AS visitors,
    COALESCE(c.buyer_cnt, 0) AS buyers,
    CASE WHEN COALESCE(v.visitor_cnt, 0) > 0
        THEN ROUND(COALESCE(c.buyer_cnt, 0) * 100.0 / v.visitor_cnt, 1)
        ELSE 0 END AS conversion_rate,
    COALESCE(c.total_cups, 0) AS cups,
    COALESCE(c.total_revenue, 0) AS revenue
FROM daily_visitors_lc v
FULL OUTER JOIN daily_consumers_lc c ON v.dt = c.dt AND v.lifecycle = c.lifecycle
ORDER BY dt,
    CASE COALESCE(v.lifecycle, c.lifecycle)
        WHEN '0-15天' THEN 1 WHEN '16-30天' THEN 2 WHEN '31天+' THEN 3 ELSE 4 END
"""


def main():
    queries = [
        ("H1: 每日来访×组×生命周期", SQL_H1_DAILY_VISITORS),
        ("H2: 每日消费×组×生命周期", SQL_H2_DAILY_CONSUMERS),
        ("H3: 每日大盘趋势(不分组)", SQL_H3_DAILY_OVERALL),
    ]
    if len(sys.argv) > 1:
        idx = int(sys.argv[1])
        queries = [queries[idx]]

    all_data = {}
    for label, sql in queries:
        result = run_query(sql, label)
        if result:
            headers = result["headers"]
            rows = result["rows"]
            # 简单打印前20行
            widths = [max(len(str(h)), max((len(str(r[i])) for r in rows[:5]), default=0)) for i, h in enumerate(headers)]
            print("  " + " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)))
            print("  " + "-+-".join("-" * w for w in widths))
            for row in rows[:20]:
                print("  " + " | ".join(str(row[i] if i < len(row) else "").ljust(widths[i]) for i in range(len(headers))))
            if len(rows) > 20:
                print(f"  ... 共 {len(rows)} 行")
            all_data[label] = [dict(zip(headers, row)) for row in rows]
        print()

    out_path = "/Users/xiaoxiao/Vibe coding/0212_health_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n📄 数据已保存: {out_path}")


if __name__ == "__main__":
    main()
