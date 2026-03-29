#!/usr/bin/env python3
"""Lucky US 频次诊断 — 数据采集 (Step 1+2)
运行: python3 growth_task_diagnosis.py
输出: growth_task_data.json
"""
import json, time, urllib.request, ssl, os, sys

AUTH_FILE = os.path.expanduser("~/.claude/skills/cyberdata-query/auth.json")
BASE = "https://idpcd.luckincoffee.us"
OUTPUT = "growth_task_data.json"

def load_auth():
    with open(AUTH_FILE) as f:
        return json.load(f)

def api_call(url, payload, auth):
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Cookie": auth["cookies"],
        "jwttoken": auth["jwttoken"],
        "productkey": "CyberData",
        "Origin": BASE
    }
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read())

def run_query(sql, auth, wait=8, max_retries=3):
    ts = int(time.time() * 1000)
    res = api_call(f"{BASE}/api/dev/task/run", {
        "_t": ts, "tenantId": "1001", "userId": "47",
        "projectId": "1906904360294313985", "resourceGroupId": 1,
        "taskId": "1990991087752757249", "variables": {},
        "sqlStatement": sql, "env": 5
    }, auth)
    if res.get("code") != "200":
        return {"error": f"Submit failed: {res}"}
    task_id = res["data"]
    print(f"  TaskID: {task_id}, wait {wait}s...")

    for attempt in range(max_retries):
        time.sleep(wait)
        ts = int(time.time() * 1000)
        res = api_call(f"{BASE}/api/logger/getQueryLog", {
            "_t": ts, "tenantId": "1001", "userId": "47",
            "projectId": "1906904360294313985", "env": 5,
            "taskInstanceId": task_id
        }, auth)
        if res.get("code") == "200" and res.get("data"):
            cols = res["data"][0].get("columns", [])
            if len(cols) > 1:
                header = cols[0]
                return [dict(zip(header, row)) for row in cols[1:]]
            return []
        if attempt < max_retries - 1:
            wait = int(wait * 1.5)
            print(f"  retry {attempt+1}, wait {wait}s...")
    return {"error": "Timeout"}

# ─── SQL Queries ───────────────────────────────────────────

QUERIES = {}

QUERIES["Q1a_weekly_freq"] = {
    "desc": "周频次分布（近4周）",
    "wait": 10,
    "sql": """
SELECT yearweek, freq, COUNT(*) AS users
FROM (
  SELECT user_no,
    YEARWEEK(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')), 1) AS yearweek,
    CASE WHEN COUNT(*) = 1 THEN '1' WHEN COUNT(*) = 2 THEN '2'
         WHEN COUNT(*) = 3 THEN '3' WHEN COUNT(*) = 4 THEN '4' ELSE '5+' END AS freq
  FROM ods_luckyus_sales_order.v_order
  WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '2026-02-10'
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '2026-03-10'
  GROUP BY user_no, yearweek
) t GROUP BY yearweek, freq ORDER BY yearweek, freq
"""
}

QUERIES["Q1b_interval"] = {
    "desc": "相邻订单间隔分布",
    "wait": 15,
    "sql": """
SELECT interval_days, COUNT(*) AS cnt
FROM (
  SELECT user_no,
    DATEDIFF(
      DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')),
      LAG(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')))
        OVER (PARTITION BY user_no ORDER BY create_time)
    ) AS interval_days
  FROM ods_luckyus_sales_order.v_order
  WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '2026-01-01'
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '2026-03-10'
) t WHERE interval_days IS NOT NULL AND interval_days > 0
GROUP BY interval_days ORDER BY interval_days
"""
}

QUERIES["Q1c_monthly_freq"] = {
    "desc": "月频次趋势（12月/1月/2月）",
    "wait": 12,
    "sql": """
SELECT month_str, freq, COUNT(*) AS users
FROM (
  SELECT user_no,
    DATE_FORMAT(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')), '%Y-%m') AS month_str,
    CASE WHEN COUNT(*) = 1 THEN '1' WHEN COUNT(*) = 2 THEN '2'
         WHEN COUNT(*) BETWEEN 3 AND 4 THEN '3-4' WHEN COUNT(*) BETWEEN 5 AND 7 THEN '5-7'
         ELSE '8+' END AS freq
  FROM ods_luckyus_sales_order.v_order
  WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '2025-12-01'
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '2026-03-01'
  GROUP BY user_no, month_str
) t GROUP BY month_str, freq ORDER BY month_str, freq
"""
}

QUERIES["Q1d_multi_cup"] = {
    "desc": "多杯订单率（2月）",
    "wait": 15,
    "sql": """
SELECT cups_bucket, COUNT(*) AS order_cnt
FROM (
  SELECT order_id,
    CASE WHEN COUNT(*) = 1 THEN '1杯' WHEN COUNT(*) = 2 THEN '2杯'
         WHEN COUNT(*) = 3 THEN '3杯' ELSE '4+杯' END AS cups_bucket
  FROM ods_luckyus_sales_order.t_order_item
  WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
    AND one_category_name = 'Drink'
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '2026-02-01'
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '2026-03-01'
  GROUP BY order_id
) t GROUP BY cups_bucket ORDER BY cups_bucket
"""
}

QUERIES["Q2a_migration"] = {
    "desc": "频次迁移矩阵（1月→2月）",
    "wait": 15,
    "sql": """
WITH jan AS (
  SELECT user_no, COUNT(*) AS cnt,
    CASE WHEN COUNT(*) = 1 THEN '1次' WHEN COUNT(*) = 2 THEN '2次'
         WHEN COUNT(*) BETWEEN 3 AND 4 THEN '3-4次' ELSE '5+次' END AS tier
  FROM ods_luckyus_sales_order.v_order
  WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '2026-01-01'
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '2026-02-01'
  GROUP BY user_no
),
feb AS (
  SELECT user_no, COUNT(*) AS cnt,
    CASE WHEN COUNT(*) = 1 THEN '1次' WHEN COUNT(*) = 2 THEN '2次'
         WHEN COUNT(*) BETWEEN 3 AND 4 THEN '3-4次' ELSE '5+次' END AS tier
  FROM ods_luckyus_sales_order.v_order
  WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '2026-02-01'
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '2026-03-01'
  GROUP BY user_no
)
SELECT jan_tier, feb_tier, COUNT(*) AS users FROM (
  SELECT j.tier AS jan_tier, COALESCE(f.tier, '流失') AS feb_tier
  FROM jan j LEFT JOIN feb f ON j.user_no = f.user_no
  UNION ALL
  SELECT '新增' AS jan_tier, f.tier AS feb_tier
  FROM feb f LEFT JOIN jan j ON f.user_no = j.user_no WHERE j.user_no IS NULL
) t GROUP BY jan_tier, feb_tier ORDER BY jan_tier, feb_tier
"""
}

QUERIES["Q2c_freq_tiers"] = {
    "desc": "频次分层用户规模（近4周）",
    "wait": 10,
    "sql": """
SELECT freq_tier, COUNT(*) AS users, ROUND(AVG(total_orders), 1) AS avg_orders
FROM (
  SELECT user_no, COUNT(*) AS total_orders,
    CASE
      WHEN COUNT(*) / 4.0 < 0.5 THEN 'A_极低频(<0.5/周)'
      WHEN COUNT(*) / 4.0 < 1   THEN 'B_低频(0.5-1/周)'
      WHEN COUNT(*) / 4.0 < 2   THEN 'C_中低频(1-2/周)'
      WHEN COUNT(*) / 4.0 < 3   THEN 'D_中频(2-3/周)'
      ELSE 'E_高频(3+/周)'
    END AS freq_tier
  FROM ods_luckyus_sales_order.v_order
  WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '2026-02-10'
    AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '2026-03-10'
  GROUP BY user_no
) t GROUP BY freq_tier ORDER BY freq_tier
"""
}

QUERIES["Q3a_dow"] = {
    "desc": "星期分布",
    "wait": 8,
    "sql": """
SELECT
  DAYOFWEEK(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS dow,
  CASE DAYOFWEEK(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')))
    WHEN 1 THEN 'Sun' WHEN 2 THEN 'Mon' WHEN 3 THEN 'Tue' WHEN 4 THEN 'Wed'
    WHEN 5 THEN 'Thu' WHEN 6 THEN 'Fri' WHEN 7 THEN 'Sat' END AS day_name,
  COUNT(*) AS orders,
  COUNT(DISTINCT user_no) AS users
FROM ods_luckyus_sales_order.v_order
WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
  AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '2026-02-01'
  AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '2026-03-10'
GROUP BY dow, day_name ORDER BY dow
"""
}

QUERIES["Q3b_consecutive"] = {
    "desc": "最长连续消费天数分布",
    "wait": 20,
    "sql": """
SELECT streak_bucket, COUNT(*) AS users
FROM (
  SELECT user_no, MAX(streak_len) AS max_streak,
    CASE WHEN MAX(streak_len) = 1 THEN '1天' WHEN MAX(streak_len) = 2 THEN '2天'
         WHEN MAX(streak_len) = 3 THEN '3天' WHEN MAX(streak_len) BETWEEN 4 AND 5 THEN '4-5天'
         ELSE '6+天' END AS streak_bucket
  FROM (
    SELECT user_no, grp, COUNT(*) AS streak_len
    FROM (
      SELECT user_no, order_date,
        DATE_SUB(order_date, INTERVAL ROW_NUMBER() OVER (PARTITION BY user_no ORDER BY order_date) DAY) AS grp
      FROM (
        SELECT DISTINCT user_no, DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) AS order_date
        FROM ods_luckyus_sales_order.v_order
        WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
          AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '2026-01-01'
          AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '2026-03-10'
      ) raw
    ) streaks GROUP BY user_no, grp
  ) streak_lengths GROUP BY user_no
) t GROUP BY streak_bucket ORDER BY streak_bucket
"""
}

# ─── Step 2: Load existing data ───────────────────────────

def load_existing_data():
    """Load Coffee Pass / 0212 experiment / Share the Luck data."""
    existing = {}
    files = {
        "coffee_pass": "coffee_pass_data.json",
        "coffee_pass_r2": "coffee_pass_data_r2.json",
        "pricing_0212": "0212_report_data_0304.json",
        "share_the_luck": "share_the_luck_data_0304.json",
    }
    for key, fname in files.items():
        path = os.path.join(os.path.dirname(__file__) or ".", fname)
        if os.path.exists(path):
            with open(path) as f:
                existing[key] = json.load(f)
            print(f"  ✅ {fname}")
        else:
            print(f"  ⚠️ {fname} not found")
    return existing

# ─── Main ─────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("Lucky US 频次诊断 — 数据采集")
    print("=" * 50)

    # Auth
    try:
        auth = load_auth()
        print(f"\n✅ 认证加载完成 (更新: {auth.get('last_updated', '?')})\n")
    except Exception as e:
        print(f"\n❌ 认证加载失败: {e}")
        print("请更新 auth.json（浏览器 F12 → Copy as cURL）")
        sys.exit(1)

    # Step 1: Run SQL queries
    print("─── Step 1: SQL 查询 ───\n")
    results = {}
    for key, q in QUERIES.items():
        print(f"[{key}] {q['desc']}")
        try:
            data = run_query(q["sql"], auth, wait=q.get("wait", 8))
            if isinstance(data, dict) and "error" in data:
                print(f"  ❌ {data['error']}\n")
                results[key] = {"error": data["error"], "desc": q["desc"]}
            else:
                print(f"  ✅ {len(data)} rows\n")
                results[key] = {"data": data, "desc": q["desc"]}
        except Exception as e:
            print(f"  ❌ {e}\n")
            results[key] = {"error": str(e), "desc": q["desc"]}

    # Step 2: Load existing data
    print("─── Step 2: 已有数据整合 ───\n")
    results["existing"] = load_existing_data()

    # Save
    with open(OUTPUT, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for k, v in results.items() if k != "existing" and "data" in v)
    fail = sum(1 for k, v in results.items() if k != "existing" and "error" in v)
    print(f"\n{'=' * 50}")
    print(f"完成! SQL查询 {ok}/{ok+fail} 成功")
    print(f"数据已保存到 {OUTPUT}")
    print(f"{'=' * 50}")

if __name__ == "__main__":
    main()
