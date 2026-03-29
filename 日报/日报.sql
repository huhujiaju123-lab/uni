-- ============================================================
-- Lucky US 日报 SQL 模板
-- 使用前替换日期变量：{date}, {date_7d_ago}, {date_list}
-- ============================================================

-- ============================================================
-- 模块1: 业务结果 - 杯量、店日均杯量、单杯实收
-- ============================================================
SELECT
    dt AS 日期,
    COUNT(DISTINCT shop_name) AS 营业店铺数,
    SUM(sku_cnt) AS 杯量,
    SUM(order_cnt) AS 订单数,
    ROUND(SUM(pay_amount), 2) AS 销售额,
    ROUND(SUM(pay_amount) / SUM(sku_cnt), 2) AS 单杯实收,
    ROUND(SUM(sku_cnt) / COUNT(DISTINCT shop_name), 0) AS 店日均杯量
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
  AND dt IN ('2026-01-29','2026-01-30','2026-01-31','2026-02-01','2026-02-02','2026-02-03','2026-02-04')
GROUP BY dt
ORDER BY dt;


-- ============================================================
-- 模块3: 用户 - 注册用户数、新客数、老客数、7日留存率、店日均
-- 注意：需要按天逐个查询，{date} 替换为具体日期
-- ============================================================
WITH day_orders AS (
    -- 当日有订单的用户
    SELECT DISTINCT user_no
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant, 'IQ') = 0
      AND status = 90
      AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) = '{date}'
),
all_user_first AS (
    -- 所有用户的首购日期（全量）
    SELECT user_no, MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_date
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
    GROUP BY user_no
),
user_type_calc AS (
    SELECT
        d.user_no,
        CASE WHEN uf.first_date = '{date}' THEN '新客' ELSE '老客' END AS user_type
    FROM day_orders d
    LEFT JOIN all_user_first uf ON d.user_no = uf.user_no
),
-- 7天前的新客（首购日期=7天前）
new_users_7d_ago AS (
    SELECT user_no
    FROM all_user_first
    WHERE first_date = '{date_7d_ago}'
),
-- 7天前新客的7日内复购（不含首购当天）
new_user_retention AS (
    SELECT COUNT(DISTINCT user_no) AS retained_new_users
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant, 'IQ') = 0
      AND status = 90
      AND user_no IN (SELECT user_no FROM new_users_7d_ago)
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) > '{date_7d_ago}'
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) <= '{date}'
),
-- 7天前下单的老客（首购日期<7天前）
old_users_7d_ago AS (
    SELECT DISTINCT o.user_no
    FROM ods_luckyus_sales_order.v_order o
    JOIN all_user_first uf ON o.user_no = uf.user_no
    WHERE INSTR(o.tenant, 'IQ') = 0
      AND o.status = 90
      AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) = '{date_7d_ago}'
      AND uf.first_date < '{date_7d_ago}'
),
-- 7天前老客的7日内复购
old_user_retention AS (
    SELECT COUNT(DISTINCT user_no) AS retained_old_users
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant, 'IQ') = 0
      AND status = 90
      AND user_no IN (SELECT user_no FROM old_users_7d_ago)
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) > '{date_7d_ago}'
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) <= '{date}'
),
-- 当日注册用户数
reg_users AS (
    SELECT COUNT(*) AS reg_count
    FROM ods_luckyus_sales_crm.t_user
    WHERE INSTR(tenant, 'IQ') = 0
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) = '{date}'
),
-- 当日营业店铺数
shop_count AS (
    SELECT COUNT(DISTINCT shop_name) AS shop_cnt
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant, 'IQ') = 0
      AND status = 90
      AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) = '{date}'
)
SELECT
    '{date}' AS 日期,
    (SELECT shop_cnt FROM shop_count) AS 营业店铺数,
    (SELECT reg_count FROM reg_users) AS 注册用户数,
    SUM(CASE WHEN user_type = '新客' THEN 1 ELSE 0 END) AS 新客数,
    SUM(CASE WHEN user_type = '老客' THEN 1 ELSE 0 END) AS 老客数,
    (SELECT COUNT(*) FROM new_users_7d_ago) AS 七日前新客数,
    (SELECT retained_new_users FROM new_user_retention) AS 新客7日留存人数,
    (SELECT COUNT(*) FROM old_users_7d_ago) AS 七日前老客数,
    (SELECT retained_old_users FROM old_user_retention) AS 老客7日留存人数
FROM user_type_calc;

-- 店日均新客 = 新客数 / 营业店铺数
-- 店日均老客 = 老客数 / 营业店铺数
-- 新客占比 = 新客数 / (新客数 + 老客数) * 100
-- 老客占比 = 老客数 / (新客数 + 老客数) * 100
-- 新客7日留存率 = 新客7日留存人数 / 七日前新客数 * 100
-- 老客7日留存率 = 老客7日留存人数 / 七日前老客数 * 100


-- ============================================================
-- 模块4: 品类 - 折扣分布
-- 注意：t_order_item 表较慢，建议按天查询
-- ============================================================
SELECT
    '{date}' AS 日期,
    COUNT(*) AS 总订单项数,
    SUM(CASE WHEN pay_money = 0.99 THEN 1 ELSE 0 END) AS 零点九九订单,
    SUM(CASE WHEN origin_price > 0 AND pay_money / origin_price < 0.3 THEN 1 ELSE 0 END) AS 三折以内,
    SUM(CASE WHEN origin_price > 0 AND pay_money / origin_price >= 0.3 AND pay_money / origin_price < 0.5 THEN 1 ELSE 0 END) AS 三至五折,
    SUM(CASE WHEN origin_price > 0 AND pay_money / origin_price >= 0.5 AND pay_money / origin_price < 0.7 THEN 1 ELSE 0 END) AS 五至七折,
    SUM(CASE WHEN origin_price > 0 AND pay_money / origin_price >= 0.7 THEN 1 ELSE 0 END) AS 七折以上,
    ROUND(AVG(CASE WHEN origin_price > 0 THEN pay_money / origin_price END), 3) AS 平均折扣率
FROM ods_luckyus_sales_order.t_order_item
WHERE INSTR(tenant, 'IQ') = 0
  AND one_category_name = 'Drink'
  AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) = '{date}';

-- 各占比 = 对应数量 / 总订单项数 * 100


-- ============================================================
-- 模块4: 漏斗转化
-- ============================================================
SELECT
    dt AS 日期,
    COUNT(DISTINCT CASE WHEN screen_name = 'menu' THEN user_no END) AS menu_uv,
    COUNT(DISTINCT CASE WHEN screen_name = 'productdetail' THEN user_no END) AS productdetail_uv,
    COUNT(DISTINCT CASE WHEN screen_name = 'confirmorder' THEN user_no END) AS confirmorder_uv,
    COUNT(DISTINCT CASE WHEN screen_name = 'orderdetail' THEN user_no END) AS orderdetail_uv
FROM dw_dws.dws_mg_log_user_screen_name_d_1d
WHERE dt IN ('2026-01-29','2026-01-30','2026-01-31','2026-02-01','2026-02-02','2026-02-03','2026-02-04')
  AND screen_name IN ('menu', 'productdetail', 'confirmorder', 'orderdetail')
GROUP BY dt
ORDER BY dt;

-- Menu转化率 = productdetail_uv / menu_uv * 100
-- 商品详情页转化率 = confirmorder_uv / productdetail_uv * 100
-- 确认订单转化率 = orderdetail_uv / confirmorder_uv * 100


-- ============================================================
-- 模块5: 核心商品渗透（订单占比）
-- ============================================================
SELECT
    dt AS 日期,
    SUM(order_cnt) AS 总订单数,
    SUM(CASE WHEN spu_name LIKE '%Coconut%' THEN order_cnt ELSE 0 END) AS Coconut_orders,
    SUM(CASE WHEN spu_name LIKE '%Cold Brew%' THEN order_cnt ELSE 0 END) AS ColdBrew_orders,
    SUM(CASE WHEN spu_name LIKE '%Pineapple%' THEN order_cnt ELSE 0 END) AS Pineapple_orders,
    SUM(CASE WHEN spu_name LIKE '%Matcha%' THEN order_cnt ELSE 0 END) AS Matcha_orders,
    SUM(CASE WHEN spu_name LIKE '%Velvet%' THEN order_cnt ELSE 0 END) AS Velvet_orders
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
  AND dt IN ('2026-01-29','2026-01-30','2026-01-31','2026-02-01','2026-02-02','2026-02-03','2026-02-04')
GROUP BY dt
ORDER BY dt;

-- 渗透率 = 商品订单数 / 总订单数 * 100
