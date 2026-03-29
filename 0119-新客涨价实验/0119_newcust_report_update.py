"""
0119 新客涨价实验 — 更新报告数据到 03-04
$2.99组(对照) vs $3.99组(涨价)，从 1/22 起算（剔除历史复用数据）
"""
import requests, json, time, sys, os

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

# ============================================================
# 实验配置
# ============================================================
ACT_299 = 'LKUSCA118314788899184640'  # $2.99 对照组
ACT_399 = 'LKUSCA118703120581779456'  # $3.99 涨价组
EXP_START = '2026-01-22'              # 清洗后起始日
DATA_END  = '2026-03-05'              # 数据截止（不含）

# 复购窗口 eligible 截止日 = 2026-03-04 - N天
D3_CUTOFF  = '2026-03-01'   # 首购<=此日的用户有3天观察窗
D7_CUTOFF  = '2026-02-25'
D14_CUTOFF = '2026-02-18'
D30_CUTOFF = '2026-02-02'
D45_CUTOFF = '2026-01-18'

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
# 公共 CTE — 从 1/22 起的清洗用户
# ============================================================
AB_CTE = f"""
WITH ab AS (
  SELECT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
    MIN(create_time) AS coupon_time
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
  GROUP BY member_no, grp
  HAVING MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) >= '{EXP_START}'
)
"""

# ============================================================
# Q1: 券核销（1/22起）
# ============================================================
SQL_Q1_COUPON = f"""
WITH first_coupon AS (
  SELECT member_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
    MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_dt
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
  GROUP BY member_no, grp
  HAVING first_dt >= '{EXP_START}'
)
SELECT
  CASE WHEN c.activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
  c.coupon_name, c.coupon_denomination,
  COUNT(*) AS total,
  SUM(CASE WHEN c.use_status = 1 THEN 1 ELSE 0 END) AS used,
  ROUND(SUM(CASE WHEN c.use_status = 1 THEN 1 ELSE 0 END)/COUNT(*)*100, 2) AS redeem_pct
FROM ods_luckyus_sales_marketing.t_coupon_record c
JOIN first_coupon fc ON c.member_no = fc.member_no
  AND CASE WHEN c.activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END = fc.grp
WHERE c.activity_no IN ('{ACT_299}', '{ACT_399}')
GROUP BY grp, c.coupon_name, c.coupon_denomination
ORDER BY grp, c.coupon_denomination
"""

# ============================================================
# Q2: 转化 + 收入汇总
# ============================================================
SQL_Q2_CONVERSION = AB_CTE + f"""
SELECT
  ab.grp,
  COUNT(DISTINCT ab.user_no) AS total_users,
  COUNT(DISTINCT o.user_no) AS order_users,
  ROUND(COUNT(DISTINCT o.user_no)/COUNT(DISTINCT ab.user_no)*100, 2) AS conv_rate,
  COUNT(DISTINCT o.id) AS order_cnt,
  ROUND(SUM(o.pay_money), 2) AS total_revenue,
  ROUND(SUM(o.pay_money) / NULLIF(COUNT(DISTINCT o.id), 0), 2) AS avg_order_value
FROM ab
LEFT JOIN ods_luckyus_sales_order.v_order o
  ON ab.user_no = o.user_no
  AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
  AND o.create_time >= ab.coupon_time AND o.create_time < '{DATA_END}'
  AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY ab.grp
"""

# ============================================================
# Q3: 每日趋势
# ============================================================
SQL_Q3_DAILY = AB_CTE + f"""
SELECT
  ab.grp,
  DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) AS dt,
  COUNT(DISTINCT o.user_no) AS order_users,
  COUNT(DISTINCT o.id) AS order_cnt,
  ROUND(SUM(o.pay_money), 2) AS revenue
FROM ab
JOIN ods_luckyus_sales_order.v_order o
  ON ab.user_no = o.user_no
  AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
  AND o.create_time >= ab.coupon_time AND o.create_time < '{DATA_END}'
  AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY ab.grp, dt
ORDER BY dt, ab.grp
"""

# ============================================================
# Q4: 复购率（D3/D7/D14/D30/D45）
# ============================================================
SQL_Q4_REPURCHASE = AB_CTE + f""",
first_order AS (
  SELECT ab.user_no, ab.grp,
    MIN(DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York'))) AS first_dt
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= ab.coupon_time AND o.create_time < '{DATA_END}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
  GROUP BY ab.user_no, ab.grp
),
repeat_orders AS (
  SELECT fo.user_no, fo.grp, fo.first_dt,
    DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) AS order_dt
  FROM first_order fo
  JOIN ods_luckyus_sales_order.v_order o
    ON fo.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) > fo.first_dt
    AND o.create_time >= '{EXP_START}' AND o.create_time < '{DATA_END}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
  fo.grp,
  COUNT(DISTINCT fo.user_no) AS total_buyers,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '{D3_CUTOFF}' THEN fo.user_no END) AS d3_elig,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '{D3_CUTOFF}' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 3 DAY) THEN fo.user_no END) AS d3_rep,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '{D7_CUTOFF}' THEN fo.user_no END) AS d7_elig,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '{D7_CUTOFF}' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 7 DAY) THEN fo.user_no END) AS d7_rep,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '{D14_CUTOFF}' THEN fo.user_no END) AS d14_elig,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '{D14_CUTOFF}' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 14 DAY) THEN fo.user_no END) AS d14_rep,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '{D30_CUTOFF}' THEN fo.user_no END) AS d30_elig,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '{D30_CUTOFF}' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 30 DAY) THEN fo.user_no END) AS d30_rep,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '{D45_CUTOFF}' THEN fo.user_no END) AS d45_elig,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '{D45_CUTOFF}' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 45 DAY) THEN fo.user_no END) AS d45_rep
FROM first_order fo
LEFT JOIN repeat_orders ro ON fo.user_no = ro.user_no AND fo.grp = ro.grp
GROUP BY fo.grp
"""

# ============================================================
# Q5: 单杯实收（t_order_item级别）
# ============================================================
SQL_Q5_UNIT_PRICE = AB_CTE + f""",
ab_orders AS (
  SELECT ab.grp, o.id AS order_id
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= ab.coupon_time AND o.create_time < '{DATA_END}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
  ao.grp,
  SUM(i.sku_num) AS total_cups,
  ROUND(SUM(i.pay_money), 2) AS item_revenue,
  ROUND(SUM(i.pay_money) / SUM(i.sku_num), 2) AS unit_price
FROM ab_orders ao
JOIN ods_luckyus_sales_order.t_order_item i ON ao.order_id = i.order_id
GROUP BY ao.grp
"""

# ============================================================
# Q6: LTV（按领券后 7/14/30/45 天窗口）
# ============================================================
SQL_Q6_LTV = AB_CTE + f""",
orders AS (
  SELECT ab.user_no, ab.grp, ab.coupon_time,
    o.pay_money,
    DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) AS order_dt
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= ab.coupon_time AND o.create_time < '{DATA_END}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
  ab.grp,
  COUNT(DISTINCT ab.user_no) AS total_users,
  ROUND(SUM(CASE WHEN od.order_dt <= DATE_ADD(DATE(CONVERT_TZ(ab.coupon_time, @@time_zone, 'America/New_York')), INTERVAL 7 DAY) THEN od.pay_money ELSE 0 END), 2) AS rev_7d,
  ROUND(SUM(CASE WHEN od.order_dt <= DATE_ADD(DATE(CONVERT_TZ(ab.coupon_time, @@time_zone, 'America/New_York')), INTERVAL 14 DAY) THEN od.pay_money ELSE 0 END), 2) AS rev_14d,
  ROUND(SUM(CASE WHEN od.order_dt <= DATE_ADD(DATE(CONVERT_TZ(ab.coupon_time, @@time_zone, 'America/New_York')), INTERVAL 30 DAY) THEN od.pay_money ELSE 0 END), 2) AS rev_30d,
  ROUND(SUM(CASE WHEN od.order_dt <= DATE_ADD(DATE(CONVERT_TZ(ab.coupon_time, @@time_zone, 'America/New_York')), INTERVAL 45 DAY) THEN od.pay_money ELSE 0 END), 2) AS rev_45d,
  ROUND(SUM(od.pay_money), 2) AS rev_total
FROM ab
LEFT JOIN orders od ON ab.user_no = od.user_no AND ab.grp = od.grp
GROUP BY ab.grp
"""

# ============================================================
# Q7: 按下单顺序归因（杯级，含单杯实收）
# ============================================================
SQL_Q7_ORDER_SEQ = AB_CTE + f""",
user_orders AS (
  SELECT ab.grp, ab.user_no, o.id AS order_id, o.create_time,
    ROW_NUMBER() OVER (PARTITION BY ab.user_no ORDER BY o.create_time) AS order_seq
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= ab.coupon_time AND o.create_time < '{DATA_END}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
  uo.grp,
  CASE WHEN uo.order_seq <= 3 THEN CAST(uo.order_seq AS CHAR) ELSE '4+' END AS seq,
  COUNT(DISTINCT uo.order_id) AS orders,
  COUNT(DISTINCT uo.user_no) AS users,
  SUM(i.sku_num) AS cups,
  ROUND(SUM(i.pay_money), 2) AS revenue,
  ROUND(SUM(i.pay_money) / NULLIF(SUM(i.sku_num), 0), 2) AS unit_price,
  ROUND(SUM(i.pay_money) / NULLIF(COUNT(DISTINCT uo.order_id), 0), 2) AS avg_order_value
FROM user_orders uo
JOIN ods_luckyus_sales_order.t_order_item i ON uo.order_id = i.order_id
GROUP BY uo.grp, seq
ORDER BY uo.grp, seq
"""


def main():
    queries = [
        ("Q1: 券核销", SQL_Q1_COUPON),
        ("Q2: 转化收入", SQL_Q2_CONVERSION),
        ("Q3: 每日趋势", SQL_Q3_DAILY),
        ("Q4: 复购率", SQL_Q4_REPURCHASE),
        ("Q5: 单杯实收", SQL_Q5_UNIT_PRICE),
        ("Q6: LTV", SQL_Q6_LTV),
        ("Q7: 下单归因", SQL_Q7_ORDER_SEQ),
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
            # 打印预览
            widths = [max(len(str(h)), max((len(str(r[i])) for r in rows[:5]), default=0)) for i, h in enumerate(headers)]
            print("  " + " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)))
            print("  " + "-+-".join("-" * w for w in widths))
            for row in rows[:20]:
                print("  " + " | ".join(str(row[i] if i < len(row) else "").ljust(widths[i]) for i in range(len(headers))))
            if len(rows) > 20:
                print(f"  ... 共 {len(rows)} 行")
            all_data[label] = [dict(zip(headers, row)) for row in rows]
        print()

    out_path = "/Users/xiaoxiao/Vibe coding/0119_newcust_data_0304.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n📄 数据已保存: {out_path}")


if __name__ == "__main__":
    main()
