#!/usr/bin/env python3
"""日报 v2 — 完整数据采集 (3/5-3/11)
表选择对齐最新约定：
- 门店/商品聚合 → ads_mg_sku_shop_sales_statistic_d_1d（秒出）
- 用户/新老客/折扣 → dwd_t_ord_order_item_d_inc（DWD层，推荐）
- 漏斗 → dws_mg_log_user_screen_name_d_1d
- 来访 → dwd_mg_log_detail_d_inc

口径：
- 杯量 = COUNT(*) WHERE one_category_name='Drink'（不是 COUNT(DISTINCT order_id)）
- 单杯实收 = SUM(pay_amount) / COUNT(*)（item级，非order级）
- 成功订单 = order_status=90（DWD）或 status=90（ODS）
- 排除测试店 = shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
"""
import json, time, urllib.request, ssl, os

AUTH_FILE = os.path.expanduser("~/.claude/skills/cyberdata-query/auth.json")
BASE = "https://idpcd.luckincoffee.us"
OUTPUT = "daily_report_week_v2_data.json"

THIS_WEEK = ("2026-03-05", "2026-03-11")
LAST_WEEK = ("2026-02-26", "2026-03-04")

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

def run_query(sql, auth, wait=8, max_retries=6):
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

# ─── Part 1 模块1: 业务结果 ─────────────────────────────
# 用 ads 表（秒出）：杯量/订单/收入/门店数/店均
QUERIES["Q1_biz_thisweek"] = {
    "desc": "本周业务结果（ads表）",
    "wait": 6,
    "sql": f"""
SELECT dt,
  COUNT(DISTINCT shop_name) AS shops,
  SUM(sku_cnt) AS cups,
  SUM(order_cnt) AS orders,
  ROUND(SUM(pay_amount), 2) AS revenue,
  ROUND(SUM(pay_amount) / NULLIF(SUM(sku_cnt), 0), 2) AS avg_cup_price
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '{THIS_WEEK[0]}' AND '{THIS_WEEK[1]}'
  AND tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY dt ORDER BY dt
"""
}

QUERIES["Q1_biz_lastweek"] = {
    "desc": "上周业务结果（ads表）",
    "wait": 6,
    "sql": f"""
SELECT dt,
  COUNT(DISTINCT shop_name) AS shops,
  SUM(sku_cnt) AS cups,
  SUM(order_cnt) AS orders,
  ROUND(SUM(pay_amount), 2) AS revenue,
  ROUND(SUM(pay_amount) / NULLIF(SUM(sku_cnt), 0), 2) AS avg_cup_price
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '{LAST_WEEK[0]}' AND '{LAST_WEEK[1]}'
  AND tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY dt ORDER BY dt
"""
}

# ─── Part 1 模块2: 用户（新老客）─────────────────────────
# DWD 表无 is_new_user 字段，改用 LEFT JOIN t_user（注册日=下单日→新客）
for i, dt in enumerate([
    "2026-03-05","2026-03-06","2026-03-07","2026-03-08",
    "2026-03-09","2026-03-10","2026-03-11"
]):
    QUERIES[f"Q2_user_{dt}"] = {
        "desc": f"新老客 {dt}（DWD+t_user）",
        "wait": 10,
        "sql": f"""
SELECT '{dt}' AS dt,
  CASE WHEN u.user_no IS NOT NULL THEN '新客' ELSE '老客' END AS user_type,
  COUNT(DISTINCT d.user_no) AS users,
  COUNT(*) AS cups,
  ROUND(SUM(d.pay_amount), 2) AS revenue,
  ROUND(SUM(d.pay_amount) / NULLIF(COUNT(*), 0), 2) AS avg_cup_price
FROM dw_dwd.dwd_t_ord_order_item_d_inc d
LEFT JOIN (
  SELECT DISTINCT user_no FROM ods_luckyus_sales_crm.t_user
  WHERE DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) = '{dt}'
    AND type NOT IN (3, 4, 5)
) u ON d.user_no = u.user_no
WHERE d.dt = '{dt}'
  AND d.order_status = 90
  AND d.one_category_name = 'Drink'
  AND d.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY user_type
"""
    }

# ─── Part 1 模块3: 折扣分布 ──────────────────────────────
QUERIES["Q3_discount"] = {
    "desc": "折扣分布（DWD表，本周汇总）",
    "wait": 10,
    "sql": f"""
SELECT dt,
  CASE
    WHEN pay_amount / NULLIF(origin_price, 0) <= 0.3 THEN 'A_≤3折'
    WHEN pay_amount / NULLIF(origin_price, 0) <= 0.5 THEN 'B_3-5折'
    WHEN pay_amount / NULLIF(origin_price, 0) <= 0.7 THEN 'C_5-7折'
    ELSE 'D_7折+'
  END AS discount_tier,
  COUNT(*) AS cups,
  ROUND(SUM(pay_amount), 2) AS revenue
FROM dw_dwd.dwd_t_ord_order_item_d_inc
WHERE dt BETWEEN '{THIS_WEEK[0]}' AND '{THIS_WEEK[1]}'
  AND order_status = 90
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
  AND origin_price > 0
GROUP BY dt, discount_tier ORDER BY dt, discount_tier
"""
}

# ─── Part 1 模块3: 漏斗 ─────────────────────────────────
QUERIES["Q3_funnel"] = {
    "desc": "漏斗转化（dws表）",
    "wait": 8,
    "sql": f"""
SELECT dt,
  COUNT(DISTINCT CASE WHEN screen_name IS NOT NULL THEN user_no END) AS uv_total,
  COUNT(DISTINCT CASE WHEN screen_name = 'home' THEN user_no END) AS uv_home,
  COUNT(DISTINCT CASE WHEN screen_name = 'menu' THEN user_no END) AS uv_menu,
  COUNT(DISTINCT CASE WHEN screen_name = 'productdetail' THEN user_no END) AS uv_detail,
  COUNT(DISTINCT CASE WHEN screen_name = 'confirmorder' THEN user_no END) AS uv_confirm,
  COUNT(DISTINCT CASE WHEN screen_name = 'orderdetail' THEN user_no END) AS uv_order
FROM dw_dws.dws_mg_log_user_screen_name_d_1d
WHERE dt BETWEEN '{THIS_WEEK[0]}' AND '{THIS_WEEK[1]}'
GROUP BY dt ORDER BY dt
"""
}

# ─── Part 1 模块4: TOP10商品 ─────────────────────────────
QUERIES["Q4_top_products"] = {
    "desc": "TOP10商品（ads表，周累计）",
    "wait": 6,
    "sql": f"""
SELECT sku_name AS product,
  SUM(sku_cnt) AS cups,
  ROUND(SUM(pay_amount), 2) AS revenue,
  ROUND(SUM(pay_amount) / NULLIF(SUM(sku_cnt), 0), 2) AS avg_price
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '{THIS_WEEK[0]}' AND '{THIS_WEEK[1]}'
  AND tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY product ORDER BY cups DESC LIMIT 10
"""
}

# ─── Part 2 模块B: 门店 ──────────────────────────────────
QUERIES["Q5_shop"] = {
    "desc": "门店每日杯量（ads表）",
    "wait": 6,
    "sql": f"""
SELECT dt, shop_name,
  SUM(sku_cnt) AS cups,
  SUM(order_cnt) AS orders,
  ROUND(SUM(pay_amount), 2) AS revenue
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '{THIS_WEEK[0]}' AND '{THIS_WEEK[1]}'
  AND tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY dt, shop_name ORDER BY dt, cups DESC
"""
}

# ─── Part 2 模块C: 渠道 ─────────────────────────────────
QUERIES["Q6_channel"] = {
    "desc": "渠道分布（DWD表）",
    "wait": 10,
    "sql": f"""
SELECT dt,
  CASE order_channel
    WHEN 1 THEN 'Android'
    WHEN 2 THEN 'iOS'
    WHEN 3 THEN 'H5'
    WHEN 8 THEN 'DoorDash'
    WHEN 9 THEN 'GrubHub'
    WHEN 10 THEN 'UberEats'
    ELSE CONCAT('Other_', order_channel)
  END AS channel,
  COUNT(DISTINCT user_no) AS users,
  COUNT(*) AS cups,
  ROUND(SUM(pay_amount), 2) AS revenue
FROM dw_dwd.dwd_t_ord_order_item_d_inc
WHERE dt BETWEEN '{THIS_WEEK[0]}' AND '{THIS_WEEK[1]}'
  AND order_status = 90
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY dt, channel ORDER BY dt, cups DESC
"""
}

# ─── Part 1 模块5: 分时（按小时汇总本周） ───────────────
QUERIES["Q7_hourly"] = {
    "desc": "分时订单分布（v_order，本周汇总）",
    "wait": 12,
    "sql": f"""
SELECT
  HOUR(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) AS hr,
  COUNT(*) AS orders,
  COUNT(DISTINCT user_no) AS users
FROM ods_luckyus_sales_order.v_order
WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
  AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))
    BETWEEN '{THIS_WEEK[0]}' AND '{THIS_WEEK[1]}'
GROUP BY hr ORDER BY hr
"""
}

# ─── Part 1 模块3: 品类（Drink vs Food vs Others） ───────
QUERIES["Q8_category"] = {
    "desc": "品类分布（ads表）",
    "wait": 6,
    "sql": f"""
SELECT dt, one_category_name AS category,
  SUM(sku_cnt) AS items,
  ROUND(SUM(pay_amount), 2) AS revenue
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '{THIS_WEEK[0]}' AND '{THIS_WEEK[1]}'
  AND tenant = 'LKUS'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY dt, category ORDER BY dt, revenue DESC
"""
}

# ─── Part 2 模块A: 天气 ─────────────────────────────────
def fetch_weather():
    """Open-Meteo Archive API: NYC 温度"""
    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        "latitude=40.7128&longitude=-74.0060"
        f"&start_date={THIS_WEEK[0]}&end_date={THIS_WEEK[1]}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&timezone=America/New_York&temperature_unit=celsius"
    )
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read())
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            tmax = daily.get("temperature_2m_max", [])
            tmin = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_sum", [])
            return [
                {"dt": d, "tmax": tx, "tmin": tn, "precip": p}
                for d, tx, tn, p in zip(dates, tmax, tmin, precip)
            ]
    except Exception as e:
        print(f"  ⚠️ 天气API: {e}")
        return {"error": str(e)}


def main():
    auth = load_auth()
    print(f"认证: {auth.get('last_updated', '?')}")
    print(f"本周: {THIS_WEEK[0]} ~ {THIS_WEEK[1]}")
    print(f"上周: {LAST_WEEK[0]} ~ {LAST_WEEK[1]}\n")

    results = {}

    # SQL queries
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

    # 天气
    print("[weather] NYC天气")
    results["weather"] = fetch_weather()
    if isinstance(results["weather"], list):
        print(f"  ✅ {len(results['weather'])} days\n")
    else:
        print(f"  ❌\n")

    # Save
    with open(OUTPUT, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for k, v in results.items() if not (isinstance(v, dict) and "error" in v))
    fail = sum(1 for k, v in results.items() if isinstance(v, dict) and "error" in v)
    print(f"\n{'='*50}")
    print(f"完成! {ok}/{ok+fail} 成功")
    print(f"数据已保存到 {OUTPUT}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
