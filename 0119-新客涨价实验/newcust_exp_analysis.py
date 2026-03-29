"""0119 新客涨价实验分析
$2.99组(对照) vs $3.99组(涨价)
"""
import json, time, requests, os, csv

AUTH_FILE = os.path.expanduser("~/.claude/skills/cyberdata-query/auth.json")
with open(AUTH_FILE) as f:
    auth = json.load(f)

JWTTOKEN = auth['jwttoken']
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json; charset=UTF-8',
    'JwtToken': JWTTOKEN,
    'ProductKey': 'CyberData',
    'Referer': 'https://idpcd.luckincoffee.us/',
}

BASE_URL = 'https://idpcd.luckincoffee.us/api'
OUTPUT_DIR = os.path.expanduser("~/Downloads/newcust_exp")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_sql(sql, name="query", wait=8, max_retries=3):
    """Submit SQL and get results"""
    ts = str(int(time.time()*1000))
    payload = {
        "_t": ts,
        "tenantId": "1001",
        "userId": "47",
        "projectId": "1906904360294313985",
        "resourceGroupId": 1,
        "taskId": "1990991087752757249",
        "variables": {},
        "sqlStatement": sql,
        "env": 5
    }

    r = requests.post(f"{BASE_URL}/dev/task/run", headers=HEADERS, json=payload)
    data = r.json()
    if data.get('code') != '200':
        print(f"  [{name}] 提交失败: {data}")
        return None

    task_id = data['data']
    print(f"  [{name}] 任务提交成功: {task_id}")

    time.sleep(wait)

    for retry in range(max_retries):
        ts = str(int(time.time()*1000))
        payload2 = {
            "_t": ts,
            "tenantId": "1001",
            "userId": "47",
            "projectId": "1906904360294313985",
            "env": 5,
            "taskInstanceId": task_id
        }
        r2 = requests.post(f"{BASE_URL}/logger/getQueryLog", headers=HEADERS, json=payload2)
        result = r2.json()

        if result.get('code') == '200' and result.get('data'):
            for item in result['data']:
                cols = item.get('columns', [])
                if cols and len(cols) > 1:
                    print(f"  [{name}] 获取到 {len(cols)-1} 行数据")
                    return cols
            # Data not ready yet
            if retry < max_retries - 1:
                print(f"  [{name}] 数据未就绪，等待重试...")
                time.sleep(5)
        else:
            if retry < max_retries - 1:
                print(f"  [{name}] 等待中...")
                time.sleep(5)

    print(f"  [{name}] 获取失败")
    return None

def save_csv(cols, filename):
    """Save query results to CSV"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in cols:
            writer.writerow(row)
    print(f"  => 已保存: {filepath}")
    return filepath

# ============================================================
# 实验配置
# ============================================================
ACT_299 = 'LKUSCA118314788899184640'  # $2.99 对照组
ACT_399 = 'LKUSCA118703120581779456'  # $3.99 涨价组
EXP_START = '2026-01-19'

print("=" * 60)
print("0119 新客涨价实验分析")
print("=" * 60)

# ============================================================
# Q1: 券明细 - 每组有哪些券，核销率
# ============================================================
print("\n[Q1] 券明细...")
q1 = run_sql(f"""
SELECT
  CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
  coupon_name,
  coupon_denomination,
  COUNT(DISTINCT member_no) AS users,
  COUNT(*) AS total_coupons,
  SUM(CASE WHEN use_status = 1 THEN 1 ELSE 0 END) AS used,
  ROUND(SUM(CASE WHEN use_status = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS redeem_pct
FROM ods_luckyus_sales_marketing.t_coupon_record
WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
GROUP BY grp, coupon_name, coupon_denomination
ORDER BY grp, coupon_denomination
""", "券明细", wait=6)
if q1:
    save_csv(q1, "Q1_券明细.csv")

# ============================================================
# Q2: 各组用户数 + 转化率 + 订单 + 收入
# ============================================================
print("\n[Q2] 转化与收入...")
q2 = run_sql(f"""
WITH ab AS (
  SELECT DISTINCT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
)
SELECT
  ab.grp,
  COUNT(DISTINCT ab.user_no) AS total_users,
  COUNT(DISTINCT o.user_no) AS order_users,
  ROUND(COUNT(DISTINCT o.user_no)/COUNT(DISTINCT ab.user_no)*100, 2) AS conv_rate,
  COUNT(DISTINCT o.id) AS order_cnt,
  ROUND(SUM(o.pay_money), 2) AS total_revenue,
  ROUND(SUM(o.pay_money) / COUNT(DISTINCT o.id), 2) AS avg_order_value
FROM ab
LEFT JOIN ods_luckyus_sales_order.v_order o
  ON ab.user_no = o.user_no
  AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
  AND o.create_time >= '{EXP_START}'
  AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY ab.grp
""", "转化收入", wait=8)
if q2:
    save_csv(q2, "Q2_转化收入.csv")

# ============================================================
# Q3: 每日转化趋势
# ============================================================
print("\n[Q3] 每日转化趋势...")
q3 = run_sql(f"""
WITH ab AS (
  SELECT DISTINCT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
)
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
  AND o.create_time >= '{EXP_START}'
  AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY ab.grp, dt
ORDER BY dt, ab.grp
""", "每日趋势", wait=8)
if q3:
    save_csv(q3, "Q3_每日趋势.csv")

# ============================================================
# Q4: 复购率（3日/7日/14日/30日）
# ============================================================
print("\n[Q4] 复购率...")
q4 = run_sql(f"""
WITH ab AS (
  SELECT DISTINCT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
),
first_order AS (
  SELECT ab.user_no, ab.grp,
    MIN(DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York'))) AS first_dt
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= '{EXP_START}'
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
    AND o.create_time >= '{EXP_START}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
  fo.grp,
  COUNT(DISTINCT fo.user_no) AS total_buyers,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-27' THEN fo.user_no END) AS d3_eligible,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-27' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 3 DAY) THEN fo.user_no END) AS d3_repeat,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-23' THEN fo.user_no END) AS d7_eligible,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-23' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 7 DAY) THEN fo.user_no END) AS d7_repeat,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-16' THEN fo.user_no END) AS d14_eligible,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-16' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 14 DAY) THEN fo.user_no END) AS d14_repeat,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-01-31' THEN fo.user_no END) AS d30_eligible,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-01-31' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 30 DAY) THEN fo.user_no END) AS d30_repeat
FROM first_order fo
LEFT JOIN repeat_orders ro ON fo.user_no = ro.user_no AND fo.grp = ro.grp
GROUP BY fo.grp
""", "复购率", wait=12)
if q4:
    save_csv(q4, "Q4_复购率.csv")

# ============================================================
# Q5: 单杯实收（通过 t_order_item）
# ============================================================
print("\n[Q5] 单杯实收...")
q5 = run_sql(f"""
WITH ab AS (
  SELECT DISTINCT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
),
ab_orders AS (
  SELECT ab.grp, o.id AS order_id
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= '{EXP_START}'
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
""", "单杯实收", wait=15)
if q5:
    save_csv(q5, "Q5_单杯实收.csv")

# ============================================================
# Q6: LTV - 按首购后天数的累计收入
# ============================================================
print("\n[Q6] LTV...")
q6 = run_sql(f"""
WITH ab AS (
  SELECT DISTINCT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
)
SELECT
  ab.grp,
  COUNT(DISTINCT ab.user_no) AS total_users,
  ROUND(SUM(CASE WHEN DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) <= DATE_ADD('{EXP_START}', INTERVAL 6 DAY) THEN o.pay_money ELSE 0 END), 2) AS rev_7d,
  ROUND(SUM(CASE WHEN DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) <= DATE_ADD('{EXP_START}', INTERVAL 13 DAY) THEN o.pay_money ELSE 0 END), 2) AS rev_14d,
  ROUND(SUM(CASE WHEN DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) <= DATE_ADD('{EXP_START}', INTERVAL 29 DAY) THEN o.pay_money ELSE 0 END), 2) AS rev_30d,
  ROUND(SUM(o.pay_money), 2) AS rev_total
FROM ab
LEFT JOIN ods_luckyus_sales_order.v_order o
  ON ab.user_no = o.user_no
  AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
  AND o.create_time >= '{EXP_START}'
  AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY ab.grp
""", "LTV", wait=8)
if q6:
    save_csv(q6, "Q6_LTV.csv")

# ============================================================
# Q7: 首单 vs 非首单 单杯实收
# ============================================================
print("\n[Q7] 首单vs非首单...")
q7 = run_sql(f"""
WITH ab AS (
  SELECT DISTINCT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
),
ranked AS (
  SELECT ab.grp, o.id AS order_id, o.pay_money,
    ROW_NUMBER() OVER(PARTITION BY ab.user_no ORDER BY o.create_time) AS rn
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= '{EXP_START}'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
  grp,
  CASE WHEN rn = 1 THEN '首单' ELSE '非首单' END AS order_type,
  COUNT(DISTINCT order_id) AS orders,
  ROUND(AVG(pay_money), 2) AS avg_pay
FROM ranked
GROUP BY grp, order_type
ORDER BY grp, order_type
""", "首单非首单", wait=10)
if q7:
    save_csv(q7, "Q7_首单非首单.csv")

print("\n" + "=" * 60)
print("所有查询完成！CSV 文件已保存到:", OUTPUT_DIR)
print("=" * 60)
