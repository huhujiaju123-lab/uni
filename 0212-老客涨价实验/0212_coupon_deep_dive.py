"""
0212涨价实验 — 0-15天用户用券深度分析
验证假设：涨价组1的75折券是否没被真正使用，导致实收没涨起来
"""
import requests
import json
import time
import sys

# ============================================================
# CyberData API 配置
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
    """提交 SQL 查询"""
    payload = {**TASK_PAYLOAD_BASE, "_t": int(time.time() * 1000), "sqlStatement": sql}
    print(f"\n{'='*60}")
    print(f"  提交查询: {label}")
    print(f"{'='*60}")
    resp = requests.post(f"{BASE_URL}/api/dev/task/run", headers=HEADERS, cookies=COOKIES, json=payload)
    data = resp.json()
    code = data.get("code")
    if str(code) != "200":
        print(f"  ❌ 提交失败: {data}")
        return None
    # data 字段可能直接是 taskInstanceId 字符串，也可能是对象
    raw_data = data.get("data")
    if isinstance(raw_data, str):
        task_instance_id = raw_data
    elif isinstance(raw_data, dict):
        task_instance_id = raw_data.get("taskInstanceId")
    else:
        task_instance_id = str(raw_data)
    print(f"  ✅ 提交成功, taskInstanceId: {task_instance_id}")
    return task_instance_id


def get_result(task_instance_id, max_wait=180, label=""):
    """轮询获取查询结果"""
    print(f"  ⏳ 等待结果...")
    for i in range(max_wait // 3):
        time.sleep(3)
        payload = {
            "_t": int(time.time() * 1000),
            "tenantId": "1001",
            "userId": "47",
            "projectId": "1906904360294313985",
            "env": 5,
            "taskInstanceId": str(task_instance_id),
        }
        resp = requests.post(f"{BASE_URL}/api/logger/getQueryLog", headers=HEADERS, cookies=COOKIES, json=payload)
        rj = resp.json()

        code = str(rj.get("code", ""))
        if code == "401":
            print("  ❌ Token 过期，请更新认证")
            return None

        results = rj.get("data", [])
        if not results or not isinstance(results, list):
            if i % 5 == 0:
                print(f"  ... 等待中, 已等 {(i+1)*3}s")
            continue

        # 检查是否有 columns 数据
        record = results[0]
        columns = record.get("columns", [])

        if columns and len(columns) > 0:
            headers = columns[0] if columns else []
            rows = columns[1:] if len(columns) > 1 else []
            print(f"  ✅ 查询完成: {len(rows)} 行")
            return {"headers": headers, "rows": rows}

        # 检查是否有错误
        error_msg = record.get("errorMsg") or record.get("error_msg")
        if error_msg:
            print(f"  ❌ 查询失败: {str(error_msg)[:200]}")
            return None

        if i % 5 == 0:
            print(f"  ... 等待中, 已等 {(i+1)*3}s")

    print(f"  ⏰ 超时 ({max_wait}s)")
    return None


def run_query(sql, label=""):
    """提交并获取结果"""
    tid = submit_sql(sql, label)
    if not tid:
        return None
    return get_result(tid, label=label)


def print_table(result, max_rows=30):
    """格式化打印结果表"""
    if not result or not result["headers"]:
        print("  (无数据)")
        return
    headers = result["headers"]
    rows = result["rows"][:max_rows]

    # 计算列宽
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(val)))

    # 打印
    header_line = " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * w for w in widths)
    print(f"  {header_line}")
    print(f"  {sep_line}")
    for row in rows:
        line = " | ".join(str(row[i] if i < len(row) else "").ljust(widths[i]) for i in range(len(headers)))
        print(f"  {line}")
    if len(result["rows"]) > max_rows:
        print(f"  ... (共 {len(result['rows'])} 行，仅显示前 {max_rows} 行)")


# ============================================================
# 公共 CTE：实验分组 + 0-15天用户筛选
# ============================================================
# 0-15天 = 首单日期在实验开始前15天内 (2026-01-28 ~ 2026-02-11)
COMMON_CTE = """
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
target_users AS (
    SELECT gu.user_no, gu.grp
    FROM grp_users gu
    INNER JOIN user_first_order ufo ON gu.user_no = ufo.user_no
    WHERE ufo.first_order_date >= '2026-01-28'
      AND ufo.first_order_date < '2026-02-12'
)
"""

# ============================================================
# Query 0: 诊断 — 各组0-15天用户数
# ============================================================
SQL_Q0_USER_COUNT = COMMON_CTE + """
SELECT grp, COUNT(*) AS user_cnt
FROM target_users
GROUP BY grp
ORDER BY grp
"""

# ============================================================
# Query 1: 0-15天用户订单的促销来源 TOP（用了什么券/活动下单）
# ============================================================
SQL_Q1_PROMOTION_SOURCE = COMMON_CTE + """
SELECT tu.grp,
    COALESCE(pd.promotion_name, '无优惠/全价') AS promotion_name,
    COUNT(DISTINCT o.id) AS order_cnt,
    COUNT(DISTINCT tu.user_no) AS user_cnt,
    ROUND(AVG(o.pay_money), 2) AS avg_order_pay
FROM target_users tu
INNER JOIN ods_luckyus_sales_order.v_order o ON tu.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
LEFT JOIN ods_luckyus_sales_order.t_order_promotion_detail pd ON o.id = pd.order_id
GROUP BY tu.grp, promotion_name
ORDER BY tu.grp, order_cnt DESC
"""

# ============================================================
# Query 2: 折扣深度分布（按杯级 pay_money/origin_price 分段）
# ============================================================
SQL_Q2_DISCOUNT_DIST = COMMON_CTE + """,
exp_orders AS (
    SELECT o.id AS order_id, tu.grp
    FROM target_users tu
    INNER JOIN ods_luckyus_sales_order.v_order o ON tu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT eo.grp,
    CASE
        WHEN item.origin_price = 0 OR item.origin_price IS NULL THEN '免费/赠品'
        WHEN item.pay_money / item.origin_price < 0.30 THEN '<3折'
        WHEN item.pay_money / item.origin_price < 0.50 THEN '3-5折'
        WHEN item.pay_money / item.origin_price < 0.60 THEN '5-6折'
        WHEN item.pay_money / item.origin_price < 0.70 THEN '6-7折'
        WHEN item.pay_money / item.origin_price < 0.75 THEN '7-7.5折'
        WHEN item.pay_money / item.origin_price < 0.80 THEN '7.5-8折'
        WHEN item.pay_money / item.origin_price < 0.90 THEN '8-9折'
        ELSE '9折+'
    END AS discount_band,
    COUNT(*) AS cup_cnt,
    ROUND(AVG(item.pay_money / NULLIF(item.sku_num, 0)), 2) AS avg_cup_price,
    ROUND(SUM(item.pay_money), 2) AS total_revenue
FROM exp_orders eo
INNER JOIN ods_luckyus_sales_order.t_order_item item ON eo.order_id = item.order_id
GROUP BY eo.grp, discount_band
ORDER BY eo.grp, discount_band
"""

# ============================================================
# Query 3: 券领取与核销（从 t_coupon_record 看实验期间发的券）
# ============================================================
SQL_Q3_COUPON_REDEMPTION = COMMON_CTE + """
SELECT tu.grp,
    cr.coupon_name,
    COUNT(*) AS issued_cnt,
    SUM(CASE WHEN cr.use_status = 1 THEN 1 ELSE 0 END) AS used_cnt,
    ROUND(SUM(CASE WHEN cr.use_status = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS redemption_rate,
    ROUND(AVG(cr.coupon_denomination), 2) AS avg_denomination
FROM target_users tu
INNER JOIN ods_luckyus_sales_marketing.t_coupon_record cr ON tu.user_no = cr.member_no
    AND cr.create_time >= '2026-02-12' AND cr.create_time < '2026-03-01'
GROUP BY tu.grp, cr.coupon_name
HAVING COUNT(*) >= 5
ORDER BY tu.grp, issued_cnt DESC
"""

# ============================================================
# Query 4: 单杯实收对比（3组，0-15天用户 vs 全量老客）
# ============================================================
SQL_Q4_UNIT_PRICE_COMPARE = COMMON_CTE + """,
-- 全量老客（实验前有订单）
all_old_users AS (
    SELECT gu.user_no, gu.grp
    FROM grp_users gu
    INNER JOIN user_first_order ufo ON gu.user_no = ufo.user_no
    WHERE ufo.first_order_date < '2026-02-12'
),
-- 0-15天用户的杯级数据
cups_015 AS (
    SELECT tu.grp,
        SUM(item.pay_money) AS total_pay,
        SUM(item.sku_num) AS total_cups
    FROM target_users tu
    INNER JOIN ods_luckyus_sales_order.v_order o ON tu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    GROUP BY tu.grp
),
-- 全量老客的杯级数据
cups_all AS (
    SELECT au.grp,
        SUM(item.pay_money) AS total_pay,
        SUM(item.sku_num) AS total_cups
    FROM all_old_users au
    INNER JOIN ods_luckyus_sales_order.v_order o ON au.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    GROUP BY au.grp
)
SELECT '0-15天' AS segment, grp,
    ROUND(total_pay / NULLIF(total_cups, 0), 2) AS unit_price,
    total_cups AS cups
FROM cups_015
UNION ALL
SELECT '全量老客' AS segment, grp,
    ROUND(total_pay / NULLIF(total_cups, 0), 2) AS unit_price,
    total_cups AS cups
FROM cups_all
ORDER BY segment, grp
"""


# ============================================================
# Query 5: 剔除5折及以下后的单杯实收
# ============================================================
SQL_Q5_UNIT_PRICE_CLEAN = COMMON_CTE + """,
exp_orders AS (
    SELECT o.id AS order_id, tu.grp, tu.user_no
    FROM target_users tu
    INNER JOIN ods_luckyus_sales_order.v_order o ON tu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT eo.grp,
    COUNT(*) AS total_cups,
    SUM(CASE WHEN item.origin_price > 0 AND item.pay_money / item.origin_price >= 0.55 THEN 1 ELSE 0 END) AS clean_cups,
    SUM(CASE WHEN item.origin_price > 0 AND item.pay_money / item.origin_price >= 0.55 THEN item.pay_money ELSE 0 END) AS clean_revenue,
    ROUND(
        SUM(CASE WHEN item.origin_price > 0 AND item.pay_money / item.origin_price >= 0.55 THEN item.pay_money ELSE 0 END)
        / NULLIF(SUM(CASE WHEN item.origin_price > 0 AND item.pay_money / item.origin_price >= 0.55 THEN item.sku_num ELSE 0 END), 0)
    , 2) AS clean_unit_price,
    ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS raw_unit_price,
    SUM(CASE WHEN item.origin_price > 0 AND item.pay_money / item.origin_price < 0.55 THEN 1 ELSE 0 END) AS excluded_cups,
    ROUND(SUM(CASE WHEN item.origin_price > 0 AND item.pay_money / item.origin_price < 0.55 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS excluded_pct
FROM exp_orders eo
INNER JOIN ods_luckyus_sales_order.t_order_item item ON eo.order_id = item.order_id
GROUP BY eo.grp
ORDER BY eo.grp
"""

# ============================================================
# Query 6: 剔除5折后的折扣深度分布
# ============================================================
SQL_Q6_DISCOUNT_CLEAN = COMMON_CTE + """,
exp_orders AS (
    SELECT o.id AS order_id, tu.grp
    FROM target_users tu
    INNER JOIN ods_luckyus_sales_order.v_order o ON tu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
)
SELECT eo.grp,
    CASE
        WHEN item.pay_money / item.origin_price < 0.60 THEN '5.5-6折'
        WHEN item.pay_money / item.origin_price < 0.70 THEN '6-7折'
        WHEN item.pay_money / item.origin_price < 0.75 THEN '7-7.5折'
        WHEN item.pay_money / item.origin_price < 0.80 THEN '7.5-8折'
        WHEN item.pay_money / item.origin_price < 0.90 THEN '8-9折'
        ELSE '9折+'
    END AS discount_band,
    COUNT(*) AS cup_cnt,
    ROUND(AVG(item.pay_money / NULLIF(item.sku_num, 0)), 2) AS avg_cup_price,
    ROUND(SUM(item.pay_money), 2) AS total_revenue
FROM exp_orders eo
INNER JOIN ods_luckyus_sales_order.t_order_item item ON eo.order_id = item.order_id
WHERE item.origin_price > 0
    AND item.pay_money / item.origin_price >= 0.55
GROUP BY eo.grp, discount_band
ORDER BY eo.grp, discount_band
"""

# ============================================================
# Query 7: 剔除5折后的促销来源
# ============================================================
SQL_Q7_PROMO_CLEAN = COMMON_CTE + """
SELECT tu.grp,
    COALESCE(pd.promotion_name, '无优惠/全价') AS promotion_name,
    COUNT(DISTINCT o.id) AS order_cnt,
    COUNT(DISTINCT tu.user_no) AS user_cnt,
    ROUND(AVG(o.pay_money), 2) AS avg_order_pay
FROM target_users tu
INNER JOIN ods_luckyus_sales_order.v_order o ON tu.user_no = o.user_no
    AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
    AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
    AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
LEFT JOIN ods_luckyus_sales_order.t_order_promotion_detail pd ON o.id = pd.order_id
WHERE COALESCE(pd.promotion_name, '') NOT IN (
    'Student Perks – 50% Off',
    '50% OFF Any Drink',
    'Share The Luck Reward',
    'Coffee Pass',
    'Coffee Pass-5 for $19.9',
    'Luck In Love: Free Tiramisu Drink',
    'Sampling Coupon'
)
GROUP BY tu.grp, promotion_name
ORDER BY tu.grp, order_cnt DESC
"""

# ============================================================
# Query 8: 剔除5折后的拉齐对比（含买家数、人均杯量、人均实收）
# ============================================================
SQL_Q8_NORMALIZED = COMMON_CTE + """,
exp_items AS (
    SELECT tu.grp, tu.user_no, item.pay_money, item.sku_num, item.origin_price
    FROM target_users tu
    INNER JOIN ods_luckyus_sales_order.v_order o ON tu.user_no = o.user_no
        AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
),
grp_total AS (
    SELECT grp, COUNT(*) AS total_users FROM target_users GROUP BY grp
)
SELECT
    gt.grp,
    gt.total_users,
    -- 全量（含5折）
    COUNT(DISTINCT ei.user_no) AS all_buyers,
    SUM(ei.sku_num) AS all_cups,
    ROUND(SUM(ei.pay_money), 2) AS all_revenue,
    ROUND(SUM(ei.pay_money) / NULLIF(SUM(ei.sku_num), 0), 2) AS all_unit_price,
    -- 剔除5折后
    COUNT(DISTINCT CASE WHEN ei.origin_price > 0 AND ei.pay_money / ei.origin_price >= 0.55 THEN ei.user_no END) AS clean_buyers,
    SUM(CASE WHEN ei.origin_price > 0 AND ei.pay_money / ei.origin_price >= 0.55 THEN ei.sku_num ELSE 0 END) AS clean_cups,
    ROUND(SUM(CASE WHEN ei.origin_price > 0 AND ei.pay_money / ei.origin_price >= 0.55 THEN ei.pay_money ELSE 0 END), 2) AS clean_revenue,
    ROUND(
        SUM(CASE WHEN ei.origin_price > 0 AND ei.pay_money / ei.origin_price >= 0.55 THEN ei.pay_money ELSE 0 END)
        / NULLIF(SUM(CASE WHEN ei.origin_price > 0 AND ei.pay_money / ei.origin_price >= 0.55 THEN ei.sku_num ELSE 0 END), 0)
    , 2) AS clean_unit_price
FROM grp_total gt
LEFT JOIN exp_items ei ON gt.grp = ei.grp
GROUP BY gt.grp, gt.total_users
ORDER BY gt.grp
"""

# ============================================================
# Query 9: 0-15天用户画像明细（每用户一行）
# ============================================================
SQL_Q9_USER_PROFILE = COMMON_CTE + """,
-- 注册信息
user_reg AS (
    SELECT user_no,
        DATE(create_time) AS reg_date,
        DATEDIFF('2026-02-12', DATE(create_time)) AS reg_days,
        origin AS reg_origin,
        type AS user_type
    FROM ods_luckyus_sales_crm.t_user
),
-- 实验前订单汇总
pre_orders AS (
    SELECT o.user_no,
        COUNT(DISTINCT o.id) AS pre_order_cnt,
        MIN(DATE(o.create_time)) AS first_order_date,
        MAX(DATE(o.create_time)) AS last_order_date,
        DATEDIFF('2026-02-12', MIN(DATE(o.create_time))) AS first_order_days,
        DATEDIFF('2026-02-12', MAX(DATE(o.create_time))) AS recency_days,
        ROUND(AVG(o.pay_money), 2) AS pre_avg_order_pay,
        ROUND(SUM(o.pay_money), 2) AS pre_total_pay
    FROM ods_luckyus_sales_order.v_order o
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time < '2026-02-12'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
-- 实验前杯量和折扣
pre_cups AS (
    SELECT o.user_no,
        SUM(item.sku_num) AS pre_cups,
        ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS pre_unit_price,
        ROUND(AVG(CASE WHEN item.origin_price > 0 THEN item.pay_money / item.origin_price END), 3) AS pre_avg_discount
    FROM ods_luckyus_sales_order.v_order o
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time < '2026-02-12'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
-- 首单渠道
first_channel AS (
    SELECT user_no, channel AS first_channel
    FROM (
        SELECT user_no, channel,
            ROW_NUMBER() OVER (PARTITION BY user_no ORDER BY create_time) AS rn
        FROM ods_luckyus_sales_order.v_order
        WHERE status = 90 AND INSTR(tenant, 'IQ') = 0
            AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    ) t WHERE rn = 1
),
-- 是否用过学生券
is_student AS (
    SELECT DISTINCT member_no AS user_no, 1 AS is_student
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE coupon_name LIKE '%Student%' OR coupon_name LIKE '%学生%'
),
-- 实验期间订单
exp_orders_agg AS (
    SELECT o.user_no,
        COUNT(DISTINCT o.id) AS exp_order_cnt,
        ROUND(SUM(o.pay_money), 2) AS exp_total_pay
    FROM ods_luckyus_sales_order.v_order o
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
-- 实验期间杯量
exp_cups AS (
    SELECT o.user_no,
        SUM(item.sku_num) AS exp_cups,
        ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS exp_unit_price,
        ROUND(AVG(CASE WHEN item.origin_price > 0 THEN item.pay_money / item.origin_price END), 3) AS exp_avg_discount
    FROM ods_luckyus_sales_order.v_order o
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
-- 实验期间APP访问天数
exp_visits AS (
    SELECT user_no, COUNT(DISTINCT dt) AS visit_days
    FROM dw_dws.dws_mg_log_user_screen_name_d_1d
    WHERE dt >= '2026-02-12' AND dt <= '2026-02-28'
    GROUP BY user_no
)
SELECT
    tu.grp,
    tu.user_no,
    -- 注册
    ur.reg_date,
    ur.reg_days,
    ur.reg_origin,
    -- 首单
    po.first_order_date,
    po.first_order_days,
    fc.first_channel,
    -- 活跃度
    po.last_order_date,
    po.recency_days,
    -- 实验前消费
    po.pre_order_cnt,
    pc.pre_cups,
    po.pre_avg_order_pay,
    pc.pre_unit_price,
    ROUND(pc.pre_avg_discount * 100, 1) AS pre_discount_pct,
    po.pre_total_pay,
    -- 是否学生
    COALESCE(stu.is_student, 0) AS is_student,
    -- 实验期间
    COALESCE(ev.visit_days, 0) AS exp_visit_days,
    COALESCE(eo.exp_order_cnt, 0) AS exp_order_cnt,
    COALESCE(ec.exp_cups, 0) AS exp_cups,
    ec.exp_unit_price,
    ROUND(ec.exp_avg_discount * 100, 1) AS exp_discount_pct,
    COALESCE(eo.exp_total_pay, 0) AS exp_total_pay
FROM target_users tu
LEFT JOIN user_reg ur ON tu.user_no = ur.user_no
LEFT JOIN pre_orders po ON tu.user_no = po.user_no
LEFT JOIN pre_cups pc ON tu.user_no = pc.user_no
LEFT JOIN first_channel fc ON tu.user_no = fc.user_no
LEFT JOIN is_student stu ON tu.user_no = stu.user_no
LEFT JOIN exp_orders_agg eo ON tu.user_no = eo.user_no
LEFT JOIN exp_cups ec ON tu.user_no = ec.user_no
LEFT JOIN exp_visits ev ON tu.user_no = ev.user_no
ORDER BY tu.grp, ec.exp_cups DESC
"""

# ============================================================
# Query 10: 0-15天用户画像按组汇总
# ============================================================
SQL_Q10_USER_PROFILE_AGG = COMMON_CTE + """,
user_reg AS (
    SELECT user_no,
        DATEDIFF('2026-02-12', DATE(create_time)) AS reg_days
    FROM ods_luckyus_sales_crm.t_user
),
pre_stats AS (
    SELECT o.user_no,
        COUNT(DISTINCT o.id) AS pre_order_cnt,
        DATEDIFF('2026-02-12', MIN(DATE(o.create_time))) AS first_order_days,
        DATEDIFF('2026-02-12', MAX(DATE(o.create_time))) AS recency_days,
        ROUND(AVG(o.pay_money), 2) AS pre_avg_order_pay,
        ROUND(SUM(o.pay_money), 2) AS pre_total_pay
    FROM ods_luckyus_sales_order.v_order o
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time < '2026-02-12'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
pre_cup_stats AS (
    SELECT o.user_no,
        SUM(item.sku_num) AS pre_cups,
        ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS pre_unit_price,
        ROUND(AVG(CASE WHEN item.origin_price > 0 THEN item.pay_money / item.origin_price END), 3) AS pre_avg_discount
    FROM ods_luckyus_sales_order.v_order o
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time < '2026-02-12'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
is_student AS (
    SELECT DISTINCT member_no AS user_no, 1 AS is_student
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE coupon_name LIKE '%Student%' OR coupon_name LIKE '%学生%'
),
exp_stats AS (
    SELECT o.user_no,
        COUNT(DISTINCT o.id) AS exp_order_cnt,
        ROUND(SUM(o.pay_money), 2) AS exp_total_pay
    FROM ods_luckyus_sales_order.v_order o
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
exp_cup_stats AS (
    SELECT o.user_no,
        SUM(item.sku_num) AS exp_cups,
        ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS exp_unit_price
    FROM ods_luckyus_sales_order.v_order o
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
exp_visits AS (
    SELECT user_no, COUNT(DISTINCT dt) AS visit_days
    FROM dw_dws.dws_mg_log_user_screen_name_d_1d
    WHERE dt >= '2026-02-12' AND dt <= '2026-02-28'
    GROUP BY user_no
)
SELECT
    tu.grp,
    COUNT(*) AS total_users,
    -- 注册
    ROUND(AVG(ur.reg_days), 1) AS avg_reg_days,
    -- 实验前
    ROUND(AVG(ps.first_order_days), 1) AS avg_first_order_days,
    ROUND(AVG(ps.recency_days), 1) AS avg_recency_days,
    ROUND(AVG(ps.pre_order_cnt), 2) AS avg_pre_orders,
    ROUND(AVG(pcs.pre_cups), 2) AS avg_pre_cups,
    ROUND(AVG(ps.pre_avg_order_pay), 2) AS avg_pre_order_pay,
    ROUND(AVG(pcs.pre_unit_price), 2) AS avg_pre_unit_price,
    ROUND(AVG(pcs.pre_avg_discount) * 100, 1) AS avg_pre_discount_pct,
    -- 学生占比
    ROUND(SUM(COALESCE(stu.is_student, 0)) * 100.0 / COUNT(*), 1) AS student_pct,
    -- 实验期间
    ROUND(AVG(COALESCE(ev.visit_days, 0)), 2) AS avg_exp_visit_days,
    SUM(CASE WHEN es.exp_order_cnt > 0 THEN 1 ELSE 0 END) AS exp_buyers,
    ROUND(SUM(CASE WHEN es.exp_order_cnt > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS exp_conversion_rate,
    ROUND(AVG(COALESCE(es.exp_order_cnt, 0)), 2) AS avg_exp_orders,
    ROUND(AVG(COALESCE(ecs.exp_cups, 0)), 2) AS avg_exp_cups,
    ROUND(SUM(COALESCE(ecs.exp_cups, 0)) * 1.0 / NULLIF(SUM(CASE WHEN es.exp_order_cnt > 0 THEN 1 ELSE 0 END), 0), 2) AS cups_per_buyer,
    ROUND(AVG(ecs.exp_unit_price), 2) AS avg_exp_unit_price
FROM target_users tu
LEFT JOIN user_reg ur ON tu.user_no = ur.user_no
LEFT JOIN pre_stats ps ON tu.user_no = ps.user_no
LEFT JOIN pre_cup_stats pcs ON tu.user_no = pcs.user_no
LEFT JOIN is_student stu ON tu.user_no = stu.user_no
LEFT JOIN exp_stats es ON tu.user_no = es.user_no
LEFT JOIN exp_cup_stats ecs ON tu.user_no = ecs.user_no
LEFT JOIN exp_visits ev ON tu.user_no = ev.user_no
GROUP BY tu.grp
ORDER BY tu.grp
"""

# ============================================================
# Query 11: 上一单 vs 实验期 — 用户级 before/after 明细
# ============================================================
SQL_Q11_BEFORE_AFTER = COMMON_CTE + """,
-- 实验前最后一单（每人一行）
last_pre_order AS (
    SELECT user_no, order_id, order_pay, order_date, channel
    FROM (
        SELECT o.user_no, o.id AS order_id, o.pay_money AS order_pay,
            DATE(o.create_time) AS order_date, o.channel,
            ROW_NUMBER() OVER (PARTITION BY o.user_no ORDER BY o.create_time DESC) AS rn
        FROM ods_luckyus_sales_order.v_order o
        WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time < '2026-02-12'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    ) t WHERE rn = 1
),
-- 上一单的杯级数据
last_pre_cups AS (
    SELECT lpo.user_no,
        SUM(item.sku_num) AS last_cups,
        ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS last_unit_price,
        ROUND(AVG(CASE WHEN item.origin_price > 0 THEN item.pay_money / item.origin_price END), 3) AS last_discount_ratio
    FROM last_pre_order lpo
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON lpo.order_id = item.order_id
    GROUP BY lpo.user_no
),
-- 实验期杯级汇总
exp_cup_agg AS (
    SELECT o.user_no,
        COUNT(DISTINCT o.id) AS exp_order_cnt,
        SUM(item.sku_num) AS exp_cups,
        ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS exp_unit_price,
        ROUND(AVG(CASE WHEN item.origin_price > 0 THEN item.pay_money / item.origin_price END), 3) AS exp_discount_ratio,
        ROUND(SUM(item.pay_money), 2) AS exp_total_pay
    FROM ods_luckyus_sales_order.v_order o
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
)
SELECT
    tu.grp,
    tu.user_no,
    -- 上一单
    lpo.order_date AS last_order_date,
    lpo.order_pay AS last_order_pay,
    lpc.last_cups,
    lpc.last_unit_price,
    ROUND(lpc.last_discount_ratio * 100, 1) AS last_discount_pct,
    -- 实验期
    COALESCE(eca.exp_order_cnt, 0) AS exp_order_cnt,
    COALESCE(eca.exp_cups, 0) AS exp_cups,
    eca.exp_unit_price,
    ROUND(eca.exp_discount_ratio * 100, 1) AS exp_discount_pct,
    eca.exp_total_pay,
    -- 变化
    ROUND(eca.exp_unit_price - lpc.last_unit_price, 2) AS unit_price_change,
    ROUND((eca.exp_discount_ratio - lpc.last_discount_ratio) * 100, 1) AS discount_change_pp
FROM target_users tu
INNER JOIN last_pre_order lpo ON tu.user_no = lpo.user_no
INNER JOIN last_pre_cups lpc ON tu.user_no = lpc.user_no
LEFT JOIN exp_cup_agg eca ON tu.user_no = eca.user_no
ORDER BY tu.grp, eca.exp_cups DESC
"""

# ============================================================
# Query 12: 上一单 vs 实验期 — 按组汇总归因
# ============================================================
SQL_Q12_BEFORE_AFTER_AGG = COMMON_CTE + """,
last_pre_order AS (
    SELECT user_no, order_id, pay_money AS order_pay
    FROM (
        SELECT o.user_no, o.id AS order_id, o.pay_money,
            ROW_NUMBER() OVER (PARTITION BY o.user_no ORDER BY o.create_time DESC) AS rn
        FROM ods_luckyus_sales_order.v_order o
        WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time < '2026-02-12'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    ) t WHERE rn = 1
),
last_pre_cups AS (
    SELECT lpo.user_no,
        SUM(item.sku_num) AS last_cups,
        ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS last_unit_price,
        ROUND(AVG(CASE WHEN item.origin_price > 0 THEN item.pay_money / item.origin_price END), 3) AS last_discount_ratio
    FROM last_pre_order lpo
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON lpo.order_id = item.order_id
    GROUP BY lpo.user_no
),
exp_cup_agg AS (
    SELECT o.user_no,
        COUNT(DISTINCT o.id) AS exp_order_cnt,
        SUM(item.sku_num) AS exp_cups,
        ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS exp_unit_price,
        ROUND(AVG(CASE WHEN item.origin_price > 0 THEN item.pay_money / item.origin_price END), 3) AS exp_discount_ratio
    FROM ods_luckyus_sales_order.v_order o
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY o.user_no
),
-- 合并：所有用户（含未购买的）
combined AS (
    SELECT
        tu.grp,
        lpc.last_unit_price,
        lpc.last_discount_ratio,
        COALESCE(eca.exp_unit_price, 0) AS exp_unit_price,
        COALESCE(eca.exp_discount_ratio, 0) AS exp_discount_ratio,
        CASE WHEN eca.exp_order_cnt > 0 THEN 1 ELSE 0 END AS is_buyer,
        COALESCE(eca.exp_cups, 0) AS exp_cups
    FROM target_users tu
    INNER JOIN last_pre_cups lpc ON tu.user_no = lpc.user_no
    INNER JOIN last_pre_order lpo ON tu.user_no = lpo.user_no
    LEFT JOIN exp_cup_agg eca ON tu.user_no = eca.user_no
)
SELECT
    grp,
    COUNT(*) AS total_users,
    -- 上一单汇总
    ROUND(AVG(last_unit_price), 2) AS avg_last_unit_price,
    ROUND(AVG(last_discount_ratio) * 100, 1) AS avg_last_discount_pct,
    -- 实验期（仅买家）
    SUM(is_buyer) AS exp_buyers,
    ROUND(SUM(is_buyer) * 100.0 / COUNT(*), 1) AS conversion_rate,
    ROUND(AVG(CASE WHEN is_buyer = 1 THEN exp_unit_price END), 2) AS avg_exp_unit_price_buyers,
    ROUND(AVG(CASE WHEN is_buyer = 1 THEN exp_discount_ratio END) * 100, 1) AS avg_exp_discount_pct_buyers,
    -- 变化（仅买家）
    ROUND(AVG(CASE WHEN is_buyer = 1 THEN exp_unit_price - last_unit_price END), 2) AS avg_unit_price_change,
    ROUND(AVG(CASE WHEN is_buyer = 1 THEN (exp_discount_ratio - last_discount_ratio) * 100 END), 1) AS avg_discount_change_pp,
    -- 实收升 vs 降的人数
    SUM(CASE WHEN is_buyer = 1 AND exp_unit_price > last_unit_price THEN 1 ELSE 0 END) AS price_up_cnt,
    SUM(CASE WHEN is_buyer = 1 AND exp_unit_price <= last_unit_price THEN 1 ELSE 0 END) AS price_down_cnt,
    -- 买家人均杯量
    ROUND(AVG(CASE WHEN is_buyer = 1 THEN exp_cups END), 2) AS avg_cups_per_buyer
FROM combined
GROUP BY grp
ORDER BY grp
"""

# ============================================================
# Query 13: 剔除5折后 — 上一单 vs 实验期汇总归因
# ============================================================
SQL_Q13_BEFORE_AFTER_CLEAN = COMMON_CTE + """,
last_pre_order AS (
    SELECT user_no, order_id, pay_money AS order_pay
    FROM (
        SELECT o.user_no, o.id AS order_id, o.pay_money,
            ROW_NUMBER() OVER (PARTITION BY o.user_no ORDER BY o.create_time DESC) AS rn
        FROM ods_luckyus_sales_order.v_order o
        WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time < '2026-02-12'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    ) t WHERE rn = 1
),
-- 上一单杯级（剔除5折）
last_pre_cups AS (
    SELECT lpo.user_no,
        SUM(item.sku_num) AS last_cups,
        ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS last_unit_price,
        ROUND(AVG(item.pay_money / item.origin_price), 3) AS last_discount_ratio
    FROM last_pre_order lpo
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON lpo.order_id = item.order_id
    WHERE item.origin_price > 0 AND item.pay_money / item.origin_price >= 0.55
    GROUP BY lpo.user_no
),
-- 实验期杯级（剔除5折）
exp_cup_agg AS (
    SELECT o.user_no,
        COUNT(DISTINCT o.id) AS exp_order_cnt,
        SUM(item.sku_num) AS exp_cups,
        ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS exp_unit_price,
        ROUND(AVG(item.pay_money / item.origin_price), 3) AS exp_discount_ratio,
        ROUND(SUM(item.pay_money), 2) AS exp_total_pay
    FROM ods_luckyus_sales_order.v_order o
    INNER JOIN ods_luckyus_sales_order.t_order_item item ON o.id = item.order_id
    WHERE o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2026-02-12' AND o.create_time < '2026-03-01'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
        AND item.origin_price > 0 AND item.pay_money / item.origin_price >= 0.55
    GROUP BY o.user_no
),
combined AS (
    SELECT
        tu.grp,
        lpc.last_unit_price,
        lpc.last_discount_ratio,
        COALESCE(eca.exp_unit_price, 0) AS exp_unit_price,
        COALESCE(eca.exp_discount_ratio, 0) AS exp_discount_ratio,
        CASE WHEN eca.exp_order_cnt > 0 THEN 1 ELSE 0 END AS is_buyer,
        COALESCE(eca.exp_cups, 0) AS exp_cups,
        COALESCE(eca.exp_total_pay, 0) AS exp_total_pay
    FROM target_users tu
    INNER JOIN last_pre_cups lpc ON tu.user_no = lpc.user_no
    LEFT JOIN exp_cup_agg eca ON tu.user_no = eca.user_no
)
SELECT
    grp,
    COUNT(*) AS total_users,
    -- 上一单（剔除5折后）
    ROUND(AVG(last_unit_price), 2) AS avg_last_unit_price,
    ROUND(AVG(last_discount_ratio) * 100, 1) AS avg_last_discount_pct,
    -- 实验期（剔除5折后，仅买家）
    SUM(is_buyer) AS exp_buyers,
    ROUND(SUM(is_buyer) * 100.0 / COUNT(*), 1) AS conversion_rate,
    ROUND(AVG(CASE WHEN is_buyer = 1 THEN exp_unit_price END), 2) AS avg_exp_unit_price_buyers,
    ROUND(AVG(CASE WHEN is_buyer = 1 THEN exp_discount_ratio END) * 100, 1) AS avg_exp_discount_pct_buyers,
    -- 变化（仅买家）
    ROUND(AVG(CASE WHEN is_buyer = 1 THEN exp_unit_price - last_unit_price END), 2) AS avg_unit_price_change,
    ROUND(AVG(CASE WHEN is_buyer = 1 THEN (exp_discount_ratio - last_discount_ratio) * 100 END), 1) AS avg_discount_change_pp,
    -- 涨/降人数
    SUM(CASE WHEN is_buyer = 1 AND exp_unit_price > last_unit_price THEN 1 ELSE 0 END) AS price_up_cnt,
    SUM(CASE WHEN is_buyer = 1 AND exp_unit_price <= last_unit_price THEN 1 ELSE 0 END) AS price_down_cnt,
    -- 买家人均杯量 & 总实收
    ROUND(AVG(CASE WHEN is_buyer = 1 THEN exp_cups END), 2) AS avg_cups_per_buyer,
    ROUND(SUM(exp_total_pay), 2) AS total_clean_revenue
FROM combined
GROUP BY grp
ORDER BY grp
"""

# ============================================================
# 主流程
# ============================================================
def main():
    queries = [
        ("Q0: 各组0-15天用户数", SQL_Q0_USER_COUNT),
        ("Q1: 促销来源TOP", SQL_Q1_PROMOTION_SOURCE),
        ("Q2: 折扣深度分布", SQL_Q2_DISCOUNT_DIST),
        ("Q3: 券领取与核销", SQL_Q3_COUPON_REDEMPTION),
        ("Q4: 单杯实收对比", SQL_Q4_UNIT_PRICE_COMPARE),
        ("Q5: 剔除5折后单杯实收", SQL_Q5_UNIT_PRICE_CLEAN),
        ("Q6: 剔除5折后折扣分布", SQL_Q6_DISCOUNT_CLEAN),
        ("Q7: 剔除5折后促销来源", SQL_Q7_PROMO_CLEAN),
        ("Q8: 剔除5折拉齐对比", SQL_Q8_NORMALIZED),
        ("Q9: 0-15天用户画像明细", SQL_Q9_USER_PROFILE),
        ("Q10: 0-15天用户画像汇总", SQL_Q10_USER_PROFILE_AGG),
        ("Q11: 上一单vs实验期明细", SQL_Q11_BEFORE_AFTER),
        ("Q12: 上一单vs实验期汇总归因", SQL_Q12_BEFORE_AFTER_AGG),
        ("Q13: 剔除5折-上一单vs实验期归因", SQL_Q13_BEFORE_AFTER_CLEAN),
    ]

    # 如果指定了参数，只跑对应的查询
    if len(sys.argv) > 1:
        idx = int(sys.argv[1])
        queries = [queries[idx]]

    results = {}
    for label, sql in queries:
        result = run_query(sql, label)
        if result:
            print_table(result)
            results[label] = result

            # Q9/Q11 明细自动存 CSV
            if ("Q9" in label or "Q11" in label) and result["headers"]:
                import csv
                csv_path = "/Users/xiaoxiao/Vibe coding/0212_user_profile_detail.csv" if "Q9" in label else "/Users/xiaoxiao/Vibe coding/0212_before_after_detail.csv"
                with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(result["headers"])
                    writer.writerows(result["rows"])
                print(f"\n  📄 明细已保存: {csv_path}")
        print()

    return results


if __name__ == "__main__":
    main()
