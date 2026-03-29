"""
0212涨价实验 — 用户距上一单天数分布
参考日期：2026-02-28（实验期末）
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
    print(f"\n{'='*60}\n  提交查询: {label}\n{'='*60}")
    resp = requests.post(f"{BASE_URL}/api/dev/task/run", headers=HEADERS, cookies=COOKIES, json=payload)
    data = resp.json()
    if str(data.get("code")) != "200":
        print(f"  ❌ 提交失败: {data}"); return None
    raw = data.get("data")
    tid = raw if isinstance(raw, str) else str(raw)
    print(f"  ✅ taskInstanceId: {tid}"); return tid

def get_result(tid, max_wait=180):
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
)
"""

# ============================================================
# R1: 距上一单天数分布（截至2/28）
# ============================================================
SQL_R1_RECENCY = GRP_CTE + """,
user_last_order AS (
    SELECT o.user_no, MAX(DATE(o.create_time)) AS last_order_date
    FROM ods_luckyus_sales_order.v_order o
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
user_recency AS (
    SELECT gu.user_no, gu.grp,
        ulo.last_order_date,
        DATEDIFF('2026-02-28', ulo.last_order_date) AS recency_days,
        CASE
            WHEN ulo.last_order_date IS NULL THEN '无订单'
            WHEN DATEDIFF('2026-02-28', ulo.last_order_date) <= 7 THEN '0-7天'
            WHEN DATEDIFF('2026-02-28', ulo.last_order_date) <= 14 THEN '8-14天'
            WHEN DATEDIFF('2026-02-28', ulo.last_order_date) <= 21 THEN '15-21天'
            WHEN DATEDIFF('2026-02-28', ulo.last_order_date) <= 30 THEN '22-30天'
            ELSE '31天+'
        END AS recency_bucket
    FROM grp_users gu
    LEFT JOIN user_last_order ulo ON gu.user_no = ulo.user_no
)
SELECT
    grp,
    recency_bucket,
    COUNT(*) AS user_cnt,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY grp), 1) AS pct
FROM user_recency
GROUP BY grp, recency_bucket
ORDER BY grp,
    CASE recency_bucket
        WHEN '0-7天' THEN 1 WHEN '8-14天' THEN 2 WHEN '15-21天' THEN 3
        WHEN '22-30天' THEN 4 WHEN '31天+' THEN 5 ELSE 6
    END
"""

# ============================================================
# R2: 实验期间有购买的用户 — 距上一单分布 + 消费指标
# ============================================================
SQL_R2_RECENCY_METRICS = GRP_CTE + """,
user_last_order AS (
    SELECT o.user_no, MAX(DATE(o.create_time)) AS last_order_date
    FROM ods_luckyus_sales_order.v_order o
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
user_recency AS (
    SELECT gu.user_no, gu.grp,
        CASE
            WHEN ulo.last_order_date IS NULL THEN '无订单'
            WHEN DATEDIFF('2026-02-28', ulo.last_order_date) <= 7 THEN '0-7天'
            WHEN DATEDIFF('2026-02-28', ulo.last_order_date) <= 14 THEN '8-14天'
            WHEN DATEDIFF('2026-02-28', ulo.last_order_date) <= 21 THEN '15-21天'
            WHEN DATEDIFF('2026-02-28', ulo.last_order_date) <= 30 THEN '22-30天'
            ELSE '31天+'
        END AS recency_bucket
    FROM grp_users gu
    LEFT JOIN user_last_order ulo ON gu.user_no = ulo.user_no
),
exp_items AS (
    SELECT ur.grp, ur.recency_bucket, ur.user_no,
        item.pay_money, item.sku_num
    FROM user_recency ur
    INNER JOIN ods_luckyus_sales_order.v_order o ON ur.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
),
grp_bucket_total AS (
    SELECT grp, recency_bucket, COUNT(*) AS total_users
    FROM user_recency GROUP BY grp, recency_bucket
)
SELECT
    gbt.grp,
    gbt.recency_bucket,
    gbt.total_users,
    COUNT(DISTINCT ei.user_no) AS buyers,
    ROUND(COUNT(DISTINCT ei.user_no) * 100.0 / gbt.total_users, 1) AS conversion_rate,
    COALESCE(SUM(ei.sku_num), 0) AS total_cups,
    ROUND(COALESCE(SUM(ei.pay_money), 0), 2) AS total_revenue,
    ROUND(SUM(ei.pay_money) / NULLIF(SUM(ei.sku_num), 0), 2) AS unit_price,
    ROUND(COALESCE(SUM(ei.sku_num), 0) * 1.0 / NULLIF(COUNT(DISTINCT ei.user_no), 0), 2) AS cups_per_buyer
FROM grp_bucket_total gbt
LEFT JOIN exp_items ei ON gbt.grp = ei.grp AND gbt.recency_bucket = ei.recency_bucket
GROUP BY gbt.grp, gbt.recency_bucket, gbt.total_users
ORDER BY gbt.grp,
    CASE gbt.recency_bucket
        WHEN '0-7天' THEN 1 WHEN '8-14天' THEN 2 WHEN '15-21天' THEN 3
        WHEN '22-30天' THEN 4 WHEN '31天+' THEN 5 ELSE 6
    END
"""


def main():
    queries = [
        ("R1: 距上一单天数分布", SQL_R1_RECENCY),
        ("R2: 距上一单×消费指标", SQL_R2_RECENCY_METRICS),
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
            widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
            print("  " + " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)))
            print("  " + "-+-".join("-" * w for w in widths))
            for row in rows[:30]:
                print("  " + " | ".join(str(row[i] if i < len(row) else "").ljust(widths[i]) for i in range(len(headers))))
            all_data[label] = [dict(zip(headers, row)) for row in rows]
        print()

    out_path = "/Users/xiaoxiao/Vibe coding/0212_recency_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n📄 数据已保存: {out_path}")


if __name__ == "__main__":
    main()
