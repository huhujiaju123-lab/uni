"""
0212涨价实验 — 按生命周期(0-15/16-30/31+)拆分核心指标
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
            if i % 5 == 0: print(f"  ... {(i+1)*3}s")
            continue
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
# 公共 CTE — 含生命周期分层
# ============================================================
FULL_CTE = """
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
),
user_lc AS (
    SELECT gu.user_no, gu.grp,
        CASE
            WHEN ufo.first_order_date IS NULL THEN '未购'
            WHEN DATEDIFF('2026-02-12', ufo.first_order_date) <= 15 THEN '0-15天'
            WHEN DATEDIFF('2026-02-12', ufo.first_order_date) <= 30 THEN '16-30天'
            ELSE '31天+'
        END AS lifecycle
    FROM grp_users gu
    LEFT JOIN user_first_order ufo ON gu.user_no = ufo.user_no
)
"""

# ============================================================
# LC1: 基础指标 — 用户数、下单用户、订单数、杯量、实收、单杯实收、客单价
# ============================================================
SQL_LC1 = FULL_CTE + """,
exp_orders AS (
    SELECT ul.grp, ul.lifecycle, ul.user_no,
        o.id AS order_id, o.pay_money
    FROM user_lc ul
    INNER JOIN ods_luckyus_sales_order.v_order o ON ul.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-05'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
),
exp_items AS (
    SELECT eo.grp, eo.lifecycle, eo.order_id,
        SUM(i.sku_num) AS cups, SUM(i.pay_money) AS item_rev
    FROM exp_orders eo
    INNER JOIN ods_luckyus_sales_order.t_order_item i ON eo.order_id = i.order_id
    GROUP BY eo.grp, eo.lifecycle, eo.order_id
),
base AS (
    SELECT grp, lifecycle, COUNT(*) AS total_users
    FROM user_lc GROUP BY grp, lifecycle
)
SELECT
    b.grp, b.lifecycle, b.total_users,
    COUNT(DISTINCT eo.user_no) AS order_users,
    COUNT(DISTINCT eo.order_id) AS order_cnt,
    COALESCE(SUM(ei.cups), 0) AS total_cups,
    ROUND(COALESCE(SUM(ei.item_rev), 0), 2) AS total_item_rev,
    ROUND(COALESCE(SUM(eo.pay_money), 0), 2) AS total_order_rev,
    ROUND(SUM(ei.item_rev) / NULLIF(SUM(ei.cups), 0), 2) AS unit_price,
    ROUND(SUM(eo.pay_money) / NULLIF(COUNT(DISTINCT eo.order_id), 0), 2) AS avg_order_value
FROM base b
LEFT JOIN exp_orders eo ON b.grp = eo.grp AND b.lifecycle = eo.lifecycle
LEFT JOIN exp_items ei ON eo.order_id = ei.order_id AND eo.grp = ei.grp AND eo.lifecycle = ei.lifecycle
GROUP BY b.grp, b.lifecycle, b.total_users
ORDER BY b.grp,
    CASE b.lifecycle WHEN '0-15天' THEN 1 WHEN '16-30天' THEN 2 WHEN '31天+' THEN 3 ELSE 4 END
"""

# ============================================================
# LC2: 复购率 D7/D14/D30 — 按组×生命周期
# ============================================================
SQL_LC2 = FULL_CTE + """,
first_exp_order AS (
    SELECT ul.grp, ul.lifecycle, ul.user_no,
        MIN(DATE(o.create_time)) AS first_exp_dt
    FROM user_lc ul
    INNER JOIN ods_luckyus_sales_order.v_order o ON ul.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-05'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY ul.grp, ul.lifecycle, ul.user_no
),
repeat_orders AS (
    SELECT feo.grp, feo.lifecycle, feo.user_no, feo.first_exp_dt,
        DATE(o.create_time) AS rep_dt
    FROM first_exp_order feo
    INNER JOIN ods_luckyus_sales_order.v_order o ON feo.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND DATE(o.create_time) > feo.first_exp_dt
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-05'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
    feo.grp, feo.lifecycle,
    COUNT(DISTINCT feo.user_no) AS total_buyers,
    COUNT(DISTINCT CASE WHEN feo.first_exp_dt <= '2026-02-25' THEN feo.user_no END) AS d7_elig,
    COUNT(DISTINCT CASE WHEN feo.first_exp_dt <= '2026-02-25'
        AND ro.rep_dt <= DATE_ADD(feo.first_exp_dt, INTERVAL 7 DAY) THEN feo.user_no END) AS d7_rep,
    COUNT(DISTINCT CASE WHEN feo.first_exp_dt <= '2026-02-18' THEN feo.user_no END) AS d14_elig,
    COUNT(DISTINCT CASE WHEN feo.first_exp_dt <= '2026-02-18'
        AND ro.rep_dt <= DATE_ADD(feo.first_exp_dt, INTERVAL 14 DAY) THEN feo.user_no END) AS d14_rep,
    COUNT(DISTINCT CASE WHEN feo.first_exp_dt <= '2026-02-02' THEN feo.user_no END) AS d30_elig,
    COUNT(DISTINCT CASE WHEN feo.first_exp_dt <= '2026-02-02'
        AND ro.rep_dt <= DATE_ADD(feo.first_exp_dt, INTERVAL 30 DAY) THEN feo.user_no END) AS d30_rep
FROM first_exp_order feo
LEFT JOIN repeat_orders ro ON feo.user_no = ro.user_no AND feo.grp = ro.grp AND feo.lifecycle = ro.lifecycle
GROUP BY feo.grp, feo.lifecycle
ORDER BY feo.grp,
    CASE feo.lifecycle WHEN '0-15天' THEN 1 WHEN '16-30天' THEN 2 WHEN '31天+' THEN 3 ELSE 4 END
"""

def main():
    queries = [
        ("LC1: 基础指标(组×生命周期)", SQL_LC1),
        ("LC2: 复购率(组×生命周期)", SQL_LC2),
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
            widths = [max(len(str(h)), max((len(str(r[i])) for r in rows[:5]), default=0)) for i, h in enumerate(headers)]
            print("  " + " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)))
            print("  " + "-+-".join("-" * w for w in widths))
            for row in rows[:30]:
                print("  " + " | ".join(str(row[i] if i < len(row) else "").ljust(widths[i]) for i in range(len(headers))))
            all_data[label] = [dict(zip(headers, row)) for row in rows]
        print()

    out_path = "/Users/xiaoxiao/Vibe coding/0212_lifecycle_split_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n📄 数据已保存: {out_path}")


if __name__ == "__main__":
    main()
