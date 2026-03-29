"""0119 新客涨价实验 - 基线检验 + 1/22起重新分析"""
import json, time, requests, os, csv

AUTH_FILE = os.path.expanduser("~/.claude/skills/cyberdata-query/auth.json")
with open(AUTH_FILE) as f:
    auth = json.load(f)

HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json; charset=UTF-8',
    'JwtToken': auth['jwttoken'],
    'ProductKey': 'CyberData',
    'Referer': 'https://idpcd.luckincoffee.us/',
}
BASE_URL = 'https://idpcd.luckincoffee.us/api'
OUTPUT_DIR = os.path.expanduser("~/Downloads/newcust_exp")
os.makedirs(OUTPUT_DIR, exist_ok=True)

ACT_299 = 'LKUSCA118314788899184640'
ACT_399 = 'LKUSCA118703120581779456'

def run_sql(sql, name="query", wait=8, max_retries=4):
    ts = str(int(time.time()*1000))
    payload = {
        "_t": ts, "tenantId": "1001", "userId": "47",
        "projectId": "1906904360294313985", "resourceGroupId": 1,
        "taskId": "1990991087752757249", "variables": {},
        "sqlStatement": sql, "env": 5
    }
    r = requests.post(f"{BASE_URL}/dev/task/run", headers=HEADERS, json=payload)
    data = r.json()
    if data.get('code') != '200':
        print(f"  [{name}] 提交失败: {data}")
        return None
    task_id = data['data']
    print(f"  [{name}] 任务ID: {task_id}")
    time.sleep(wait)
    for retry in range(max_retries):
        ts = str(int(time.time()*1000))
        payload2 = {
            "_t": ts, "tenantId": "1001", "userId": "47",
            "projectId": "1906904360294313985", "env": 5,
            "taskInstanceId": task_id
        }
        r2 = requests.post(f"{BASE_URL}/logger/getQueryLog", headers=HEADERS, json=payload2)
        result = r2.json()
        if result.get('code') == '200' and result.get('data'):
            for item in result['data']:
                cols = item.get('columns', [])
                if cols and len(cols) > 1:
                    print(f"  [{name}] ✅ {len(cols)-1} 行")
                    return cols
        if retry < max_retries - 1:
            print(f"  [{name}] 等待...")
            time.sleep(5)
    print(f"  [{name}] ❌ 获取失败")
    return None

def save(cols, filename):
    fp = os.path.join(OUTPUT_DIR, filename)
    with open(fp, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(cols)
    print(f"  => {fp}")

# ==============================================================
print("=" * 60)
print("Part 1: 基线检验")
print("=" * 60)

# C1: 用户重叠检查
print("\n[C1] 用户重叠...")
c1 = run_sql(f"""
SELECT
  COUNT(DISTINCT a.member_no) AS overlap_users,
  (SELECT COUNT(DISTINCT member_no) FROM ods_luckyus_sales_marketing.t_coupon_record WHERE activity_no = '{ACT_299}') AS grp_299_users,
  (SELECT COUNT(DISTINCT member_no) FROM ods_luckyus_sales_marketing.t_coupon_record WHERE activity_no = '{ACT_399}') AS grp_399_users
FROM ods_luckyus_sales_marketing.t_coupon_record a
JOIN ods_luckyus_sales_marketing.t_coupon_record b
  ON a.member_no = b.member_no
  AND a.activity_no = '{ACT_299}'
  AND b.activity_no = '{ACT_399}'
""", "用户重叠", wait=8)
if c1: save(c1, "C1_用户重叠.csv")

# C2: 每日新增领券用户数（看分流节奏）
print("\n[C2] 每日领券人数...")
c2 = run_sql(f"""
WITH first_coupon AS (
  SELECT member_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
    MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_dt
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
  GROUP BY member_no, grp
)
SELECT grp, first_dt, COUNT(*) AS new_users
FROM first_coupon
GROUP BY grp, first_dt
ORDER BY first_dt, grp
""", "每日领券", wait=8)
if c2: save(c2, "C2_每日领券.csv")

# C3: 渠道分布
print("\n[C3] 渠道分布...")
c3 = run_sql(f"""
WITH ab AS (
  SELECT DISTINCT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
),
first_ord AS (
  SELECT ab.user_no, ab.grp, o.channel,
    ROW_NUMBER() OVER(PARTITION BY ab.user_no ORDER BY o.create_time) AS rn
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= '2026-01-19'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT grp,
  SUM(CASE WHEN channel = 1 THEN 1 ELSE 0 END) AS android,
  SUM(CASE WHEN channel = 2 THEN 1 ELSE 0 END) AS ios,
  SUM(CASE WHEN channel NOT IN (1,2) THEN 1 ELSE 0 END) AS other,
  COUNT(*) AS total
FROM first_ord WHERE rn = 1
GROUP BY grp
""", "渠道分布", wait=8)
if c3: save(c3, "C3_渠道分布.csv")

# C4: 注册到首购时间分布
print("\n[C4] 领券到首购时间...")
c4 = run_sql(f"""
WITH ab AS (
  SELECT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
    MIN(create_time) AS coupon_time
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
  GROUP BY member_no, grp
),
first_ord AS (
  SELECT ab.user_no, ab.grp, ab.coupon_time,
    MIN(o.create_time) AS first_order_time
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= ab.coupon_time
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
  GROUP BY ab.user_no, ab.grp, ab.coupon_time
)
SELECT grp,
  COUNT(*) AS buyers,
  ROUND(AVG(TIMESTAMPDIFF(HOUR, coupon_time, first_order_time)), 1) AS avg_hours,
  SUM(CASE WHEN TIMESTAMPDIFF(HOUR, coupon_time, first_order_time) < 1 THEN 1 ELSE 0 END) AS within_1h,
  SUM(CASE WHEN TIMESTAMPDIFF(HOUR, coupon_time, first_order_time) < 24 THEN 1 ELSE 0 END) AS within_1d,
  SUM(CASE WHEN TIMESTAMPDIFF(HOUR, coupon_time, first_order_time) < 72 THEN 1 ELSE 0 END) AS within_3d,
  SUM(CASE WHEN TIMESTAMPDIFF(HOUR, coupon_time, first_order_time) >= 72 THEN 1 ELSE 0 END) AS after_3d
FROM first_ord
GROUP BY grp
""", "领券到首购", wait=10)
if c4: save(c4, "C4_领券到首购.csv")

# ==============================================================
print("\n" + "=" * 60)
print("Part 2: 从 1月22日 起重新分析")
print("=" * 60)

# 先看1/22之后的用户数
# 只看1/22之后领券的用户
EXP_START2 = '2026-01-22'

# R1: 1/22起的用户数+转化+收入
print("\n[R1] 1/22起 转化收入...")
r1 = run_sql(f"""
WITH ab AS (
  SELECT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
    MIN(create_time) AS coupon_time
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
  GROUP BY member_no, grp
  HAVING MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) >= '{EXP_START2}'
)
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
  AND o.create_time >= ab.coupon_time
  AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY ab.grp
""", "R1_转化收入", wait=10)
if r1: save(r1, "R1_转化收入_0122.csv")

# R2: 1/22起复购率
print("\n[R2] 1/22起 复购率...")
r2 = run_sql(f"""
WITH ab AS (
  SELECT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
    MIN(create_time) AS coupon_time
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
  GROUP BY member_no, grp
  HAVING MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) >= '{EXP_START2}'
),
first_order AS (
  SELECT ab.user_no, ab.grp,
    MIN(DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York'))) AS first_dt
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= ab.coupon_time
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
    AND o.create_time >= '2026-01-22'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
  fo.grp,
  COUNT(DISTINCT fo.user_no) AS total_buyers,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-27' THEN fo.user_no END) AS d3_elig,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-27' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 3 DAY) THEN fo.user_no END) AS d3_rep,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-23' THEN fo.user_no END) AS d7_elig,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-23' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 7 DAY) THEN fo.user_no END) AS d7_rep,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-16' THEN fo.user_no END) AS d14_elig,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-02-16' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 14 DAY) THEN fo.user_no END) AS d14_rep,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-01-31' THEN fo.user_no END) AS d30_elig,
  COUNT(DISTINCT CASE WHEN fo.first_dt <= '2026-01-31' AND ro.order_dt <= DATE_ADD(fo.first_dt, INTERVAL 30 DAY) THEN fo.user_no END) AS d30_rep
FROM first_order fo
LEFT JOIN repeat_orders ro ON fo.user_no = ro.user_no AND fo.grp = ro.grp
GROUP BY fo.grp
""", "R2_复购率", wait=12)
if r2: save(r2, "R2_复购率_0122.csv")

# R3: 1/22起单杯实收
print("\n[R3] 1/22起 单杯实收...")
r3 = run_sql(f"""
WITH ab AS (
  SELECT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
    MIN(create_time) AS coupon_time
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
  GROUP BY member_no, grp
  HAVING MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) >= '{EXP_START2}'
),
ab_orders AS (
  SELECT ab.grp, o.id AS order_id
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= ab.coupon_time
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
""", "R3_单杯实收", wait=15)
if r3: save(r3, "R3_单杯实收_0122.csv")

# R4: 1/22起 LTV
print("\n[R4] 1/22起 LTV...")
r4 = run_sql(f"""
WITH ab AS (
  SELECT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
    MIN(create_time) AS coupon_time
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
  GROUP BY member_no, grp
  HAVING MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) >= '{EXP_START2}'
),
orders AS (
  SELECT ab.user_no, ab.grp, ab.coupon_time,
    o.pay_money,
    DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) AS order_dt
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= ab.coupon_time
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT
  ab.grp,
  COUNT(DISTINCT ab.user_no) AS total_users,
  ROUND(SUM(CASE WHEN od.order_dt <= DATE_ADD(DATE(CONVERT_TZ(ab.coupon_time, @@time_zone, 'America/New_York')), INTERVAL 7 DAY) THEN od.pay_money ELSE 0 END), 2) AS rev_7d,
  ROUND(SUM(CASE WHEN od.order_dt <= DATE_ADD(DATE(CONVERT_TZ(ab.coupon_time, @@time_zone, 'America/New_York')), INTERVAL 14 DAY) THEN od.pay_money ELSE 0 END), 2) AS rev_14d,
  ROUND(SUM(CASE WHEN od.order_dt <= DATE_ADD(DATE(CONVERT_TZ(ab.coupon_time, @@time_zone, 'America/New_York')), INTERVAL 30 DAY) THEN od.pay_money ELSE 0 END), 2) AS rev_30d,
  ROUND(SUM(od.pay_money), 2) AS rev_total
FROM ab
LEFT JOIN orders od ON ab.user_no = od.user_no AND ab.grp = od.grp
GROUP BY ab.grp
""", "R4_LTV", wait=10)
if r4: save(r4, "R4_LTV_0122.csv")

# R5: 1/22起 首单vs非首单
print("\n[R5] 1/22起 首单vs非首单...")
r5 = run_sql(f"""
WITH ab AS (
  SELECT member_no AS user_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
    MIN(create_time) AS coupon_time
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
  GROUP BY member_no, grp
  HAVING MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) >= '{EXP_START2}'
),
ranked AS (
  SELECT ab.grp, o.id AS order_id, o.pay_money,
    ROW_NUMBER() OVER(PARTITION BY ab.user_no ORDER BY o.create_time) AS rn
  FROM ab
  JOIN ods_luckyus_sales_order.v_order o
    ON ab.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= ab.coupon_time
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT grp,
  CASE WHEN rn = 1 THEN '首单' ELSE '非首单' END AS order_type,
  COUNT(DISTINCT order_id) AS orders,
  ROUND(AVG(pay_money), 2) AS avg_pay
FROM ranked
GROUP BY grp, order_type
ORDER BY grp, order_type
""", "R5_首单非首单", wait=10)
if r5: save(r5, "R5_首单非首单_0122.csv")

# R6: 1/22起 券核销
print("\n[R6] 1/22起 券核销...")
r6 = run_sql(f"""
WITH first_coupon AS (
  SELECT member_no,
    CASE WHEN activity_no = '{ACT_399}' THEN '$3.99组' ELSE '$2.99组' END AS grp,
    MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_dt
  FROM ods_luckyus_sales_marketing.t_coupon_record
  WHERE activity_no IN ('{ACT_299}', '{ACT_399}')
  GROUP BY member_no, grp
  HAVING first_dt >= '{EXP_START2}'
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
""", "R6_券核销", wait=10)
if r6: save(r6, "R6_券核销_0122.csv")

print("\n" + "=" * 60)
print("全部完成！")
print("=" * 60)
