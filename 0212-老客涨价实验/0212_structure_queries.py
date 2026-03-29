"""
0212涨价实验 — 用户结构分析 + 实验贡献拆解
三组 × 三个生命周期（0-15天 / 16-30天 / 31+天）
"""
import requests
import json
import time
import sys

# ============================================================
# CyberData API 配置（复用 deep_dive 的认证）
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
    "tenantId": "1001",
    "userId": "47",
    "projectId": "1906904360294313985",
    "resourceGroupId": 1,
    "taskId": "2025093402876882945",
    "variables": {},
    "env": 5,
}


def submit_sql(sql, label=""):
    payload = {**TASK_PAYLOAD_BASE, "_t": int(time.time() * 1000), "sqlStatement": sql}
    print(f"\n{'='*60}")
    print(f"  提交查询: {label}")
    print(f"{'='*60}")
    resp = requests.post(f"{BASE_URL}/api/dev/task/run", headers=HEADERS, cookies=COOKIES, json=payload)
    data = resp.json()
    if str(data.get("code")) != "200":
        print(f"  ❌ 提交失败: {data}")
        return None
    raw_data = data.get("data")
    tid = raw_data if isinstance(raw_data, str) else str(raw_data)
    print(f"  ✅ 提交成功, taskInstanceId: {tid}")
    return tid


def get_result(task_instance_id, max_wait=180):
    print(f"  ⏳ 等待结果...")
    for i in range(max_wait // 3):
        time.sleep(3)
        payload = {
            "_t": int(time.time() * 1000),
            "tenantId": "1001", "userId": "47",
            "projectId": "1906904360294313985", "env": 5,
            "taskInstanceId": str(task_instance_id),
        }
        resp = requests.post(f"{BASE_URL}/api/logger/getQueryLog", headers=HEADERS, cookies=COOKIES, json=payload)
        rj = resp.json()
        if str(rj.get("code", "")) == "401":
            print("  ❌ Token 过期"); return None
        results = rj.get("data", [])
        if not results or not isinstance(results, list):
            if i % 5 == 0: print(f"  ... 已等 {(i+1)*3}s")
            continue
        record = results[0]
        columns = record.get("columns", [])
        if columns and len(columns) > 0:
            headers = columns[0]
            rows = columns[1:] if len(columns) > 1 else []
            print(f"  ✅ 查询完成: {len(rows)} 行")
            return {"headers": headers, "rows": rows}
        error_msg = record.get("errorMsg") or record.get("error_msg")
        if error_msg:
            print(f"  ❌ 查询失败: {str(error_msg)[:200]}"); return None
        if i % 5 == 0: print(f"  ... 已等 {(i+1)*3}s")
    print(f"  ⏰ 超时"); return None


def run_query(sql, label=""):
    tid = submit_sql(sql, label)
    if not tid: return None
    return get_result(tid)


# ============================================================
# 公共 CTE：全量用户 + 生命周期分层
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
all_users AS (
    SELECT gu.user_no, gu.grp,
        ufo.first_order_date,
        DATEDIFF('2026-02-12', ufo.first_order_date) AS days_since_first,
        CASE
            WHEN ufo.first_order_date >= '2026-01-28' THEN '0-15天'
            WHEN ufo.first_order_date >= '2026-01-13' THEN '16-30天'
            WHEN ufo.first_order_date IS NOT NULL THEN '31天+'
            ELSE '无订单'
        END AS lifecycle
    FROM grp_users gu
    LEFT JOIN user_first_order ufo ON gu.user_no = ufo.user_no
)
"""

# ============================================================
# S1: 用户结构 — 各组×生命周期人数
# ============================================================
SQL_S1_STRUCTURE = FULL_CTE + """
SELECT
    grp,
    lifecycle,
    COUNT(*) AS user_cnt
FROM all_users
GROUP BY grp, lifecycle
ORDER BY grp,
    CASE lifecycle WHEN '0-15天' THEN 1 WHEN '16-30天' THEN 2 WHEN '31天+' THEN 3 ELSE 4 END
"""

# ============================================================
# S2: 实验期指标 — 各组×生命周期的杯量、实收、单杯实收、转化率
# ============================================================
SQL_S2_METRICS = FULL_CTE + """,
exp_items AS (
    SELECT au.grp, au.lifecycle, au.user_no,
        item.pay_money, item.sku_num, item.origin_price
    FROM all_users au
    INNER JOIN ods_luckyus_sales_order.v_order o ON au.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
),
grp_total AS (
    SELECT grp, lifecycle, COUNT(*) AS total_users
    FROM all_users GROUP BY grp, lifecycle
)
SELECT
    gt.grp,
    gt.lifecycle,
    gt.total_users,
    COUNT(DISTINCT ei.user_no) AS buyers,
    ROUND(COUNT(DISTINCT ei.user_no) * 100.0 / gt.total_users, 1) AS conversion_rate,
    COALESCE(SUM(ei.sku_num), 0) AS total_cups,
    ROUND(COALESCE(SUM(ei.pay_money), 0), 2) AS total_revenue,
    ROUND(SUM(ei.pay_money) / NULLIF(SUM(ei.sku_num), 0), 2) AS unit_price,
    ROUND(COALESCE(SUM(ei.sku_num), 0) * 1.0 / NULLIF(COUNT(DISTINCT ei.user_no), 0), 2) AS cups_per_buyer
FROM grp_total gt
LEFT JOIN exp_items ei ON gt.grp = ei.grp AND gt.lifecycle = ei.lifecycle
GROUP BY gt.grp, gt.lifecycle, gt.total_users
ORDER BY gt.grp,
    CASE gt.lifecycle WHEN '0-15天' THEN 1 WHEN '16-30天' THEN 2 WHEN '31天+' THEN 3 ELSE 4 END
"""

# ============================================================
# S3: 各组合计指标（不分lifecycle，用于算大盘）
# ============================================================
SQL_S3_TOTAL = FULL_CTE + """,
exp_items AS (
    SELECT au.grp, au.user_no,
        item.pay_money, item.sku_num
    FROM all_users au
    INNER JOIN ods_luckyus_sales_order.v_order o ON au.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
),
grp_total AS (
    SELECT grp, COUNT(*) AS total_users FROM all_users GROUP BY grp
)
SELECT
    gt.grp,
    gt.total_users,
    COUNT(DISTINCT ei.user_no) AS buyers,
    ROUND(COUNT(DISTINCT ei.user_no) * 100.0 / gt.total_users, 1) AS conversion_rate,
    COALESCE(SUM(ei.sku_num), 0) AS total_cups,
    ROUND(COALESCE(SUM(ei.pay_money), 0), 2) AS total_revenue,
    ROUND(SUM(ei.pay_money) / NULLIF(SUM(ei.sku_num), 0), 2) AS unit_price,
    ROUND(COALESCE(SUM(ei.sku_num), 0) * 1.0 / NULLIF(COUNT(DISTINCT ei.user_no), 0), 2) AS cups_per_buyer
FROM grp_total gt
LEFT JOIN exp_items ei ON gt.grp = ei.grp
GROUP BY gt.grp, gt.total_users
ORDER BY gt.grp
"""

# ============================================================
# S4: 实验前基线（按组×生命周期，实验前14天 01-29~02-11 的表现）
# ============================================================
SQL_S4_BASELINE = FULL_CTE + """,
pre_items AS (
    SELECT au.grp, au.lifecycle, au.user_no,
        item.pay_money, item.sku_num
    FROM all_users au
    INNER JOIN ods_luckyus_sales_order.v_order o ON au.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-01-29' AND o.create_time < '2026-02-12'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
),
grp_total AS (
    SELECT grp, lifecycle, COUNT(*) AS total_users
    FROM all_users GROUP BY grp, lifecycle
)
SELECT
    gt.grp,
    gt.lifecycle,
    gt.total_users,
    COUNT(DISTINCT pi.user_no) AS pre_buyers,
    ROUND(COUNT(DISTINCT pi.user_no) * 100.0 / gt.total_users, 1) AS pre_conversion_rate,
    COALESCE(SUM(pi.sku_num), 0) AS pre_cups,
    ROUND(COALESCE(SUM(pi.pay_money), 0), 2) AS pre_revenue,
    ROUND(SUM(pi.pay_money) / NULLIF(SUM(pi.sku_num), 0), 2) AS pre_unit_price
FROM grp_total gt
LEFT JOIN pre_items pi ON gt.grp = pi.grp AND gt.lifecycle = pi.lifecycle
GROUP BY gt.grp, gt.lifecycle, gt.total_users
ORDER BY gt.grp,
    CASE gt.lifecycle WHEN '0-15天' THEN 1 WHEN '16-30天' THEN 2 WHEN '31天+' THEN 3 ELSE 4 END
"""


# ============================================================
# 主流程
# ============================================================
def main():
    queries = [
        ("S1: 用户结构", SQL_S1_STRUCTURE),
        ("S2: 实验期指标(组×生命周期)", SQL_S2_METRICS),
        ("S3: 各组合计", SQL_S3_TOTAL),
        ("S4: 实验前基线(组×生命周期)", SQL_S4_BASELINE),
    ]

    if len(sys.argv) > 1:
        idx = int(sys.argv[1])
        queries = [queries[idx]]

    all_data = {}
    for label, sql in queries:
        result = run_query(sql, label)
        if result:
            # 打印
            headers = result["headers"]
            rows = result["rows"]
            widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
            print("  " + " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)))
            print("  " + "-+-".join("-" * w for w in widths))
            for row in rows[:30]:
                print("  " + " | ".join(str(row[i] if i < len(row) else "").ljust(widths[i]) for i in range(len(headers))))
            if len(rows) > 30:
                print(f"  ... 共 {len(rows)} 行")

            # 转为 dict 列表
            all_data[label] = [dict(zip(headers, row)) for row in rows]
        print()

    # 保存 JSON
    out_path = "/Users/xiaoxiao/Vibe coding/0212_structure_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n📄 数据已保存: {out_path}")

    return all_data


if __name__ == "__main__":
    main()
