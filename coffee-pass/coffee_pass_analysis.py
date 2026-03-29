#!/usr/bin/env python3
"""Coffee Pass 卖券活动复盘分析 — 数据采集脚本
活动: Coffee Pass — 5 for $19.9
方案编号: LKUSCP118713952489488385
活动时间: 2026-02-06 ~ 2026-02-15
"""

import requests
import json
import time
import os

BASE_URL = "https://idpcd.luckincoffee.us"
AUTH_FILE = os.path.expanduser("~/.claude/skills/cyberdata-query/auth.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coffee_pass_data.json")

# 读取认证
with open(AUTH_FILE) as f:
    auth = json.load(f)

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json; charset=UTF-8",
    "jwttoken": auth["jwttoken"],
    "productkey": "CyberData",
    "origin": BASE_URL,
}
# 解析 cookies 字符串
cookie_str = auth["cookies"]
COOKIES = {}
for part in cookie_str.split(";"):
    part = part.strip()
    if "=" in part:
        k, v = part.split("=", 1)
        COOKIES[k.strip()] = v.strip()


def submit_sql(sql, label=""):
    payload = {
        "_t": int(time.time() * 1000),
        "tenantId": "1001",
        "userId": "47",
        "projectId": "1906904360294313985",
        "resourceGroupId": 1,
        "taskId": "1985617719742480386",
        "variables": {},
        "sqlStatement": sql,
        "env": 5,
    }
    resp = requests.post(f"{BASE_URL}/api/dev/task/run", json=payload, headers=HEADERS, cookies=COOKIES)
    if resp.status_code != 200:
        print(f"[{label}] HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    if not resp.text.strip():
        print(f"[{label}] 空响应 — Token 可能已过期，请更新认证")
        return None
    data = resp.json()
    if data.get("code") not in [0, "200", 200]:
        print(f"[{label}] 提交失败: {data}")
        return None
    task_id = data["data"] if isinstance(data["data"], str) else data["data"]
    print(f"[{label}] 已提交, taskInstanceId={task_id}")
    return task_id


def get_result(task_instance_id, label="", max_wait=180):
    payload = {
        "_t": int(time.time() * 1000),
        "tenantId": "1001",
        "userId": "47",
        "projectId": "1906904360294313985",
        "env": 5,
        "taskInstanceId": task_instance_id,
    }
    for i in range(max_wait // 3):
        time.sleep(3)
        resp = requests.post(f"{BASE_URL}/api/logger/getQueryLog", json=payload, headers=HEADERS, cookies=COOKIES)
        data = resp.json()
        records = data.get("data", [])
        if not records:
            print(f"[{label}] 等待中... ({i*3}s)")
            continue
        rec = records[0]
        columns = rec.get("columns", [])
        if columns:
            header = columns[0]
            rows = columns[1:]
            print(f"[{label}] 完成: {len(rows)} 行")
            return header, rows
        status = rec.get("status")
        if status == 3 or rec.get("log"):
            print(f"[{label}] 失败: {str(rec)[:300]}")
            return None, None
        print(f"[{label}] 等待中... ({i*3}s)")
    print(f"[{label}] 超时 ({max_wait}s)")
    return None, None


def run_query(sql, label=""):
    task_id = submit_sql(sql, label)
    if not task_id:
        return None, None
    return get_result(task_id, label)


def to_dicts(header, rows):
    """将 [header], [[row1], [row2]...] 转成 [{col: val}, ...]"""
    if not header or not rows:
        return []
    return [dict(zip(header, row)) for row in rows]


# ============================================================
# SQL 查询定义
# ============================================================

# Q0: 数据探查 — 确认 proposal_no 和 t_coupon_record 字段
SQL_Q0_EXPLORE = """
SELECT proposal_no, coupon_name, coupon_denomination,
       COUNT(*) AS cnt,
       COUNT(DISTINCT member_no) AS user_cnt,
       MIN(create_time) AS first_create,
       MAX(create_time) AS last_create
FROM ods_luckyus_sales_marketing.t_coupon_record
WHERE proposal_no = 'LKUSCP118713952489488385'
GROUP BY proposal_no, coupon_name, coupon_denomination
"""

# Q1: 销售概况 — 每日售出份数、收入、购买人数
# 每人购买5张券 = 1份，份数 = 券数/5
SQL_Q1_SALES = """
SELECT
    DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) AS dt,
    COUNT(*) AS total_coupons,
    ROUND(COUNT(*) / 5, 0) AS total_packs,
    COUNT(DISTINCT member_no) AS buyer_cnt,
    ROUND(COUNT(*) / 5 * 19.9, 2) AS total_revenue
FROM ods_luckyus_sales_marketing.t_coupon_record
WHERE proposal_no = 'LKUSCP118713952489488385'
GROUP BY DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))
ORDER BY dt
"""

# Q1b: 人均购买份数分布
SQL_Q1B_PACKS_DIST = """
SELECT packs, COUNT(*) AS user_cnt
FROM (
    SELECT member_no, ROUND(COUNT(*) / 5, 0) AS packs
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE proposal_no = 'LKUSCP118713952489488385'
    GROUP BY member_no
) t
GROUP BY packs
ORDER BY packs
"""

# Q2: 券核销率 — use_status 分布
SQL_Q2_REDEMPTION = """
SELECT
    use_status,
    COUNT(*) AS cnt,
    COUNT(DISTINCT member_no) AS user_cnt
FROM ods_luckyus_sales_marketing.t_coupon_record
WHERE proposal_no = 'LKUSCP118713952489488385'
GROUP BY use_status
"""

# Q2b: 人均核销张数分布
SQL_Q2B_REDEEM_DIST = """
SELECT used_cnt, COUNT(*) AS user_cnt
FROM (
    SELECT member_no,
           SUM(CASE WHEN use_status = 1 THEN 1 ELSE 0 END) AS used_cnt
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE proposal_no = 'LKUSCP118713952489488385'
    GROUP BY member_no
) t
GROUP BY used_cnt
ORDER BY used_cnt
"""

# Q3: 核销时效 — 购买后第几天核销
SQL_Q3_REDEEM_TIMING = """
SELECT
    DATEDIFF(
        DATE(CONVERT_TZ(use_time, @@time_zone, 'America/New_York')),
        DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))
    ) AS days_to_use,
    COUNT(*) AS cnt
FROM ods_luckyus_sales_marketing.t_coupon_record
WHERE proposal_no = 'LKUSCP118713952489488385'
  AND use_status = 1
GROUP BY days_to_use
ORDER BY days_to_use
"""

# Q4: 核销订单分析 — Coffee Pass 券使用的订单特征
SQL_Q4_ORDER_ANALYSIS = """
SELECT
    COUNT(DISTINCT o.id) AS order_cnt,
    COUNT(DISTINCT o.user_no) AS user_cnt,
    ROUND(AVG(o.pay_money), 2) AS avg_order_amount,
    ROUND(SUM(o.pay_money), 2) AS total_pay,
    ROUND(AVG(o.origin_amount), 2) AS avg_origin_amount
FROM ods_luckyus_sales_order.v_order o
JOIN ods_luckyus_sales_order.t_order_promotion_detail p ON o.id = p.order_id
WHERE p.promotion_name LIKE 'Coffee Pass%'
  AND o.status = 90
  AND INSTR(o.tenant, 'IQ') = 0
  AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
"""

# Q4b: 核销订单日趋势
SQL_Q4B_ORDER_TREND = """
SELECT
    DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) AS dt,
    COUNT(DISTINCT o.id) AS order_cnt,
    COUNT(DISTINCT o.user_no) AS user_cnt,
    ROUND(AVG(o.pay_money), 2) AS avg_pay,
    ROUND(SUM(o.pay_money), 2) AS total_pay
FROM ods_luckyus_sales_order.v_order o
JOIN ods_luckyus_sales_order.t_order_promotion_detail p ON o.id = p.order_id
WHERE p.promotion_name LIKE 'Coffee Pass%'
  AND o.status = 90
  AND INSTR(o.tenant, 'IQ') = 0
  AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York'))
ORDER BY dt
"""

# Q5: 门店分布 TOP10
SQL_Q5_SHOP_TOP10 = """
SELECT
    o.shop_name,
    COUNT(DISTINCT o.id) AS order_cnt,
    COUNT(DISTINCT o.user_no) AS user_cnt,
    ROUND(SUM(o.pay_money), 2) AS total_pay
FROM ods_luckyus_sales_order.v_order o
JOIN ods_luckyus_sales_order.t_order_promotion_detail p ON o.id = p.order_id
WHERE p.promotion_name LIKE 'Coffee Pass%'
  AND o.status = 90
  AND INSTR(o.tenant, 'IQ') = 0
  AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY o.shop_name
ORDER BY order_cnt DESC
LIMIT 10
"""

# Q6: 用户画像 — 购买者的新老客分布 + 历史消费频次
SQL_Q6_USER_PROFILE = """
WITH buyers AS (
    SELECT DISTINCT member_no AS user_no
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE proposal_no = 'LKUSCP118713952489488385'
),
first_orders AS (
    SELECT o.user_no,
           MIN(DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York'))) AS first_order_dt
    FROM ods_luckyus_sales_order.v_order o
    JOIN buyers b ON o.user_no = b.user_no
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    GROUP BY o.user_no
),
prior_orders AS (
    SELECT o.user_no,
           COUNT(DISTINCT o.id) AS prior_order_cnt
    FROM ods_luckyus_sales_order.v_order o
    JOIN buyers b ON o.user_no = b.user_no
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) >= '2026-01-07'
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) < '2026-02-06'
    GROUP BY o.user_no
)
SELECT
    CASE
        WHEN f.first_order_dt >= '2026-02-06' THEN '新客'
        WHEN DATEDIFF('2026-02-06', f.first_order_dt) <= 15 THEN '近15天活跃'
        WHEN DATEDIFF('2026-02-06', f.first_order_dt) <= 30 THEN '近16-30天活跃'
        ELSE '30天+老客'
    END AS user_type,
    COUNT(DISTINCT b.user_no) AS user_cnt,
    ROUND(AVG(COALESCE(p.prior_order_cnt, 0)), 1) AS avg_prior_orders
FROM buyers b
LEFT JOIN first_orders f ON b.user_no = f.user_no
LEFT JOIN prior_orders p ON b.user_no = p.user_no
GROUP BY user_type
ORDER BY user_cnt DESC
"""

# Q6b: 购买前30天消费频次分布
SQL_Q6B_FREQ_DIST = """
WITH buyers AS (
    SELECT DISTINCT member_no AS user_no
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE proposal_no = 'LKUSCP118713952489488385'
),
prior_freq AS (
    SELECT o.user_no,
           COUNT(DISTINCT o.id) AS order_cnt
    FROM ods_luckyus_sales_order.v_order o
    JOIN buyers b ON o.user_no = b.user_no
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) >= '2026-01-07'
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) < '2026-02-06'
    GROUP BY o.user_no
)
SELECT
    CASE
        WHEN COALESCE(p.order_cnt, 0) = 0 THEN '0单'
        WHEN p.order_cnt BETWEEN 1 AND 2 THEN '1-2单'
        WHEN p.order_cnt BETWEEN 3 AND 5 THEN '3-5单'
        WHEN p.order_cnt BETWEEN 6 AND 10 THEN '6-10单'
        ELSE '10单+'
    END AS freq_bucket,
    COUNT(DISTINCT b.user_no) AS user_cnt
FROM buyers b
LEFT JOIN prior_freq p ON b.user_no = p.user_no
GROUP BY freq_bucket
ORDER BY
    CASE freq_bucket
        WHEN '0单' THEN 1 WHEN '1-2单' THEN 2 WHEN '3-5单' THEN 3
        WHEN '6-10单' THEN 4 ELSE 5
    END
"""

# Q7: 前后消费对比 — 购买前14天 vs 购买后至今
SQL_Q7_BEFORE_AFTER = """
WITH buyers AS (
    SELECT member_no AS user_no,
           MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS buy_dt
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE proposal_no = 'LKUSCP118713952489488385'
    GROUP BY member_no
),
before_stats AS (
    SELECT b.user_no,
           COUNT(DISTINCT o.id) AS order_cnt,
           ROUND(SUM(o.pay_money), 2) AS total_pay
    FROM buyers b
    JOIN ods_luckyus_sales_order.v_order o ON b.user_no = o.user_no
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) >= DATE_SUB(b.buy_dt, INTERVAL 14 DAY)
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) < b.buy_dt
    GROUP BY b.user_no
),
after_stats AS (
    SELECT b.user_no,
           COUNT(DISTINCT o.id) AS order_cnt,
           ROUND(SUM(o.pay_money), 2) AS total_pay
    FROM buyers b
    JOIN ods_luckyus_sales_order.v_order o ON b.user_no = o.user_no
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) > b.buy_dt
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) <= '2026-03-08'
    GROUP BY b.user_no
)
SELECT
    '购买前14天' AS period,
    COUNT(DISTINCT b.user_no) AS total_buyers,
    COUNT(DISTINCT bf.user_no) AS active_users,
    COALESCE(SUM(bf.order_cnt), 0) AS total_orders,
    ROUND(COALESCE(AVG(bf.order_cnt), 0), 1) AS avg_orders,
    ROUND(COALESCE(SUM(bf.total_pay), 0), 2) AS total_pay
FROM buyers b LEFT JOIN before_stats bf ON b.user_no = bf.user_no
UNION ALL
SELECT
    '购买后至今' AS period,
    COUNT(DISTINCT b.user_no) AS total_buyers,
    COUNT(DISTINCT af.user_no) AS active_users,
    COALESCE(SUM(af.order_cnt), 0) AS total_orders,
    ROUND(COALESCE(AVG(af.order_cnt), 0), 1) AS avg_orders,
    ROUND(COALESCE(SUM(af.total_pay), 0), 2) AS total_pay
FROM buyers b LEFT JOIN after_stats af ON b.user_no = af.user_no
"""

# Q8: 退款/过期分析
SQL_Q8_EXPIRE = """
SELECT
    CASE
        WHEN use_status = 1 THEN '已核销'
        WHEN coupon_status = 2 THEN '已过期'
        ELSE '未使用(有效期内)'
    END AS coupon_state,
    COUNT(*) AS cnt,
    COUNT(DISTINCT member_no) AS user_cnt
FROM ods_luckyus_sales_marketing.t_coupon_record
WHERE proposal_no = 'LKUSCP118713952489488385'
GROUP BY coupon_state
ORDER BY cnt DESC
"""

# Q8b: 按人统计未用完张数分布
SQL_Q8B_UNUSED_DIST = """
SELECT unused_cnt, COUNT(*) AS user_cnt
FROM (
    SELECT member_no,
           SUM(CASE WHEN use_status != 1 THEN 1 ELSE 0 END) AS unused_cnt
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE proposal_no = 'LKUSCP118713952489488385'
    GROUP BY member_no
) t
GROUP BY unused_cnt
ORDER BY unused_cnt
"""

# Q9: 复购行为 — 用完5杯 vs 未用完 在活动后的消费
SQL_Q9_REPURCHASE = """
WITH buyers AS (
    SELECT member_no AS user_no,
           SUM(CASE WHEN use_status = 1 THEN 1 ELSE 0 END) AS used_cnt,
           COUNT(*) AS total_cnt
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE proposal_no = 'LKUSCP118713952489488385'
    GROUP BY member_no
),
buyer_type AS (
    SELECT user_no,
           CASE WHEN used_cnt = total_cnt THEN '全部用完' ELSE '未用完' END AS buyer_group
    FROM buyers
),
post_orders AS (
    SELECT o.user_no,
           COUNT(DISTINCT o.id) AS order_cnt,
           ROUND(SUM(o.pay_money), 2) AS total_pay
    FROM ods_luckyus_sales_order.v_order o
    JOIN buyer_type bt ON o.user_no = bt.user_no
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) >= '2026-02-16'
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) <= '2026-03-08'
      AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
)
SELECT
    bt.buyer_group,
    COUNT(DISTINCT bt.user_no) AS total_users,
    COUNT(DISTINCT po.user_no) AS active_users,
    ROUND(COUNT(DISTINCT po.user_no) * 100.0 / COUNT(DISTINCT bt.user_no), 1) AS return_rate,
    COALESCE(SUM(po.order_cnt), 0) AS total_orders,
    ROUND(COALESCE(AVG(po.order_cnt), 0), 1) AS avg_orders,
    ROUND(COALESCE(SUM(po.total_pay), 0), 2) AS total_pay
FROM buyer_type bt
LEFT JOIN post_orders po ON bt.user_no = po.user_no
GROUP BY bt.buyer_group
"""


# ============================================================
# 执行所有查询
# ============================================================
def main():
    results = {}

    queries = [
        ("Q0_explore", SQL_Q0_EXPLORE),
        ("Q1_sales", SQL_Q1_SALES),
        ("Q1b_packs_dist", SQL_Q1B_PACKS_DIST),
        ("Q2_redemption", SQL_Q2_REDEMPTION),
        ("Q2b_redeem_dist", SQL_Q2B_REDEEM_DIST),
        ("Q3_redeem_timing", SQL_Q3_REDEEM_TIMING),
        ("Q4_order_analysis", SQL_Q4_ORDER_ANALYSIS),
        ("Q4b_order_trend", SQL_Q4B_ORDER_TREND),
        ("Q5_shop_top10", SQL_Q5_SHOP_TOP10),
        ("Q6_user_profile", SQL_Q6_USER_PROFILE),
        ("Q6b_freq_dist", SQL_Q6B_FREQ_DIST),
        ("Q7_before_after", SQL_Q7_BEFORE_AFTER),
        ("Q8_expire", SQL_Q8_EXPIRE),
        ("Q8b_unused_dist", SQL_Q8B_UNUSED_DIST),
        ("Q9_repurchase", SQL_Q9_REPURCHASE),
    ]

    # 先跑 Q0 验证数据源
    print("=" * 60)
    print("Step 1: 数据探查")
    print("=" * 60)
    h, r = run_query(SQL_Q0_EXPLORE, "Q0_explore")
    if h:
        results["Q0_explore"] = to_dicts(h, r)
        print(f"  → 探查结果: {results['Q0_explore']}")
    else:
        print("  ⚠️  Q0 探查失败，请检查认证或 proposal_no")
        print("  如果 401 错误，请在 CyberData 浏览器 F12 复制 curl 命令更新认证")
        return

    # 批量跑 Q1-Q9
    print("\n" + "=" * 60)
    print("Step 2: 批量执行分析查询")
    print("=" * 60)

    # 提交所有查询（并行提交）
    task_ids = {}
    for label, sql in queries[1:]:  # 跳过 Q0
        task_id = submit_sql(sql, label)
        if task_id:
            task_ids[label] = task_id
        time.sleep(0.5)  # 避免频率限制

    # 等待所有结果
    print("\n收集查询结果...")
    for label, task_id in task_ids.items():
        h, r = get_result(task_id, label, max_wait=180)
        if h:
            results[label] = to_dicts(h, r)
        else:
            results[label] = []

    # 保存到 JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 数据已保存到: {OUTPUT_FILE}")
    print(f"共 {len(results)} 个查询结果")

    # 打印概要
    print("\n" + "=" * 60)
    print("数据概要")
    print("=" * 60)
    for k, v in results.items():
        print(f"  {k}: {len(v)} 行")


if __name__ == "__main__":
    main()
