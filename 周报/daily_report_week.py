#!/usr/bin/env python3
"""拉取最近一周日报数据 (3/5-3/11)"""
import json, time, urllib.request, ssl, os

AUTH_FILE = os.path.expanduser("~/.claude/skills/cyberdata-query/auth.json")
BASE = "https://idpcd.luckincoffee.us"
OUTPUT = "daily_report_week_data.json"

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

QUERIES = {}

# Q1: 每日杯量/订单/销售额（ads表，秒出）
QUERIES["daily_sales"] = {
    "desc": "每日杯量/订单/销售额",
    "wait": 6,
    "sql": """
SELECT dt,
  SUM(sku_cnt) AS cups,
  SUM(order_cnt) AS orders,
  ROUND(SUM(pay_amount), 2) AS revenue
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '2026-03-05' AND '2026-03-11'
  AND tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY dt ORDER BY dt
"""
}

# Q2: 门店杯量（每日Top门店）
QUERIES["shop_daily"] = {
    "desc": "门店每日杯量",
    "wait": 6,
    "sql": """
SELECT dt, shop_name,
  SUM(sku_cnt) AS cups,
  SUM(order_cnt) AS orders,
  ROUND(SUM(pay_amount), 2) AS revenue
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '2026-03-05' AND '2026-03-11'
  AND tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY dt, shop_name ORDER BY dt, cups DESC
"""
}

# Q3: 新老客每日（v_order）
QUERIES["new_old"] = {
    "desc": "新老客每日分布",
    "wait": 10,
    "sql": """
WITH first_order AS (
  SELECT user_no, MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_date
  FROM ods_luckyus_sales_order.v_order
  WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
  GROUP BY user_no
)
SELECT
  DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) AS dt,
  CASE WHEN f.first_date = DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) THEN '新客' ELSE '老客' END AS user_type,
  COUNT(DISTINCT o.user_no) AS users,
  COUNT(*) AS orders
FROM ods_luckyus_sales_order.v_order o
JOIN first_order f ON o.user_no = f.user_no
WHERE INSTR(o.tenant, 'IQ') = 0 AND o.status = 90
  AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) BETWEEN '2026-03-05' AND '2026-03-11'
GROUP BY dt, user_type ORDER BY dt, user_type
"""
}

# Q4: 品类分布（Drink vs Food vs Merch）
QUERIES["category"] = {
    "desc": "品类每日分布",
    "wait": 6,
    "sql": """
SELECT dt, one_category_name AS category,
  SUM(sku_cnt) AS cups,
  ROUND(SUM(pay_amount), 2) AS revenue
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '2026-03-05' AND '2026-03-11'
  AND tenant = 'LKUS'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY dt, category ORDER BY dt, revenue DESC
"""
}

# Q5: TOP10 商品
QUERIES["top_products"] = {
    "desc": "TOP10商品（周累计）",
    "wait": 6,
    "sql": """
SELECT sku_name AS product,
  SUM(sku_cnt) AS cups,
  ROUND(SUM(pay_amount), 2) AS revenue,
  ROUND(SUM(pay_amount) / SUM(sku_cnt), 2) AS avg_price
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '2026-03-05' AND '2026-03-11'
  AND tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY product ORDER BY cups DESC LIMIT 10
"""
}

# Q6: 上一周对比数据（2/26-3/4）
QUERIES["last_week"] = {
    "desc": "上周对比数据",
    "wait": 6,
    "sql": """
SELECT dt,
  SUM(sku_cnt) AS cups,
  SUM(order_cnt) AS orders,
  ROUND(SUM(pay_amount), 2) AS revenue
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '2026-02-26' AND '2026-03-04'
  AND tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY dt ORDER BY dt
"""
}

def main():
    auth = load_auth()
    print(f"认证: {auth.get('last_updated', '?')}\n")

    results = {}
    for key, q in QUERIES.items():
        print(f"[{key}] {q['desc']}")
        try:
            data = run_query(q["sql"], auth, wait=q.get("wait", 8))
            if isinstance(data, dict) and "error" in data:
                print(f"  ❌ {data['error']}\n")
                results[key] = {"error": data["error"]}
            else:
                print(f"  ✅ {len(data)} rows\n")
                results[key] = data
        except Exception as e:
            print(f"  ❌ {e}\n")
            results[key] = {"error": str(e)}

    with open(OUTPUT, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n数据已保存到 {OUTPUT}")

if __name__ == "__main__":
    main()
