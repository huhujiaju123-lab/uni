-- 老客留存率分析SQL
-- 分析老客户（非当天新客）的留存购买情况
-- 参数设置
SET @cal_begin_date = DATE_SUB(DATE(NOW()), INTERVAL 30 DAY);
--参数3:自动计算纽约时间滚动8天的结束时间（今天）
SET @cal_end_date = DATE_SUB(DATE(NOW()), INTERVAL 0 DAY);

SET @max_retention_days = 30;        -- 最大留存分析天数

WITH 
-- 1. 获取用户首次交易信息（用于判断新用户）
user_first_transaction AS (
    SELECT 
        b.user_no,
        b.shop_name,
        MIN(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York'))) AS first_transaction_date
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    WHERE INSTR(a.tenant, 'IQ') = 0
    AND b.status = 90
    AND one_category_name='Drink'
    GROUP BY b.user_no, b.shop_name
),

-- 2. 获取当天老客户交易用户（不是当天新客就是老客）
target_day_users AS (
    SELECT 
        DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) AS trade_date,
        b.user_no,
        b.shop_name
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    INNER JOIN user_first_transaction uft ON b.user_no = uft.user_no 
        AND b.shop_name = uft.shop_name
        AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) > uft.first_transaction_date
    WHERE INSTR(a.tenant, 'IQ') = 0
    AND b.status = 90
    AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) >= @cal_begin_date
    AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) <= @cal_end_date
    AND one_category_name='Drink'
    GROUP BY DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), b.user_no, b.shop_name
),

-- 3. 获取这些老客户后续的交易活动（包含店铺信息）
user_future_activities AS (
    SELECT 
        tdu.trade_date,
        tdu.user_no,
        tdu.shop_name,
        DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) AS activity_date,
        DATEDIFF(
            DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), 
            tdu.trade_date
        ) AS days_since_target_date,
        b.id AS order_id,
        1 AS item_quantity  -- 订单项数量（杯量）
    FROM target_day_users tdu
    JOIN ods_luckyus_sales_order.v_order b ON tdu.user_no = b.user_no AND tdu.shop_name = b.shop_name
    JOIN ods_luckyus_sales_order.t_order_item a ON b.id = a.order_id
    WHERE INSTR(a.tenant, 'IQ') = 0
    AND b.status = 90
    AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) >= tdu.trade_date
    AND DATEDIFF(
        DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), 
        tdu.trade_date
    ) <= @max_retention_days
    and one_category_name='Drink'
),

-- 4. 计算留存率基础数据（包含杯量信息和店铺维度）
retention_base AS (
    SELECT 
        trade_date,
        shop_name,
        days_since_target_date,
        COUNT(DISTINCT user_no) AS retained_users,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(item_quantity) AS total_cups,
        ROUND(COUNT(DISTINCT order_id) / COUNT(DISTINCT user_no), 2) AS avg_orders_per_user,
        ROUND(SUM(item_quantity) / COUNT(DISTINCT user_no), 2) AS avg_cups_per_user
    FROM user_future_activities
    GROUP BY trade_date, shop_name, days_since_target_date
),

-- 5. 计算累计留存数据（包含店铺维度）
cumulative_retention_base AS (
    SELECT 
        tdu.trade_date,
        tdu.shop_name,
        d.days_since_target_date,
        COUNT(DISTINCT CASE 
            WHEN ufa.user_no IS NOT NULL THEN ufa.user_no 
        END) AS cumulative_retained_users,
        SUM(CASE 
            WHEN ufa.user_no IS NOT NULL THEN ufa.item_quantity 
            ELSE 0 
        END) AS cumulative_total_cups
    FROM target_day_users tdu
    CROSS JOIN (
        SELECT DISTINCT days_since_target_date 
        FROM user_future_activities 
        WHERE days_since_target_date <= @max_retention_days
    ) d
    LEFT JOIN user_future_activities ufa ON tdu.trade_date = ufa.trade_date 
        AND tdu.user_no = ufa.user_no 
        AND tdu.shop_name = ufa.shop_name
        AND ufa.days_since_target_date BETWEEN 
            CASE WHEN d.days_since_target_date = 0 THEN 0 ELSE 1 END 
            AND d.days_since_target_date
    GROUP BY tdu.trade_date, tdu.shop_name, d.days_since_target_date
),

-- 6. 计算当天老客户交易用户总数（按店铺维度）
daily_trade_users AS (
    SELECT 
        trade_date,
        shop_name,
        COUNT(DISTINCT user_no) AS total_users
    FROM target_day_users
    GROUP BY trade_date, shop_name
),

-- 7. 获取7日内有复购的老客户
d7_repurchase_users AS (
    SELECT DISTINCT
        tdu.trade_date,
        tdu.user_no,
        tdu.shop_name
    FROM target_day_users tdu
    JOIN ods_luckyus_sales_order.v_order b ON tdu.user_no = b.user_no AND tdu.shop_name = b.shop_name
    JOIN ods_luckyus_sales_order.t_order_item a ON b.id = a.order_id
    WHERE INSTR(a.tenant, 'IQ') = 0
    AND b.status = 90
    AND one_category_name='Drink'
    AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) > tdu.trade_date
    AND DATEDIFF(
        DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), 
        tdu.trade_date
    ) BETWEEN 1 AND 7
),

-- 8. 获取这些7日复购用户在后续14天内的复购情况
d7_users_future_purchases AS (
    SELECT 
        d7ru.trade_date,
        d7ru.user_no,
        d7ru.shop_name,
        DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) AS purchase_date,
        DATEDIFF(
            DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), 
            d7ru.trade_date
        ) AS days_since_first_purchase,
        b.id AS order_id
    FROM d7_repurchase_users d7ru
    JOIN ods_luckyus_sales_order.v_order b ON d7ru.user_no = b.user_no AND d7ru.shop_name = b.shop_name
    JOIN ods_luckyus_sales_order.t_order_item a ON b.id = a.order_id
    WHERE INSTR(a.tenant, 'IQ') = 0
    AND b.status = 90
    AND one_category_name='Drink'
    AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) > d7ru.trade_date
    AND DATEDIFF(
        DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), 
        d7ru.trade_date
    ) BETWEEN 8 AND 21  -- 第8天到第21天（7日复购后的14天内）
),

-- 9. 计算复购占比基础数据
repurchase_analysis AS (
    SELECT 
        dtu.trade_date,
        dtu.shop_name,
        COUNT(DISTINCT dtu.user_no) AS total_old_users,
        COUNT(DISTINCT d7ru.user_no) AS d7_repurchase_users,
        COUNT(DISTINCT d7ufp.user_no) AS d7_users_with_d8_d21_repurchase,
        ROUND(COUNT(DISTINCT d7ru.user_no) * 100.0 / COUNT(DISTINCT dtu.user_no), 2) AS d7_repurchase_rate_pct,
        ROUND(COUNT(DISTINCT d7ufp.user_no) * 100.0 / COUNT(DISTINCT d7ru.user_no), 2) AS d7_users_d8_d21_repurchase_rate_pct,
        ROUND(COUNT(DISTINCT d7ufp.user_no) * 100.0 / COUNT(DISTINCT dtu.user_no), 2) AS d7_users_d8_d21_vs_total_old_users_pct
    FROM target_day_users dtu
    LEFT JOIN d7_repurchase_users d7ru ON dtu.trade_date = d7ru.trade_date 
        AND dtu.user_no = d7ru.user_no 
        AND dtu.shop_name = d7ru.shop_name
    LEFT JOIN d7_users_future_purchases d7ufp ON dtu.trade_date = d7ufp.trade_date 
        AND dtu.user_no = d7ufp.user_no 
        AND dtu.shop_name = d7ufp.shop_name
    GROUP BY dtu.trade_date, dtu.shop_name
)

-- 7. 最终老客户留存率分析表（包含当日留存、累计留存和店铺维度）
SELECT 
    rb.trade_date AS cohort_date,
    rb.shop_name,
    dtu.total_users AS day0_users,
    rb.days_since_target_date AS retention_day,
    
    -- 当日留存数据
    rb.retained_users AS daily_retained_users,
    ROUND(rb.retained_users * 100.0 / dtu.total_users, 2) AS daily_retention_rate_pct,
    rb.total_cups AS daily_total_cups,
    rb.avg_cups_per_user AS daily_avg_cups_per_user,
    
    -- 累计留存数据
    crb.cumulative_retained_users,
    ROUND(crb.cumulative_retained_users * 100.0 / dtu.total_users, 2) AS cumulative_retention_rate_pct,
    crb.cumulative_total_cups,
    ROUND(crb.cumulative_total_cups / crb.cumulative_retained_users, 2) AS cumulative_avg_cups_per_user,
    
    -- 添加关键留存节点标识
    CASE 
        WHEN rb.days_since_target_date = 0 THEN 'D0当天'
        WHEN rb.days_since_target_date = 1 THEN 'D1留存'
        WHEN rb.days_since_target_date = 3 THEN 'D3留存'
        WHEN rb.days_since_target_date = 7 THEN 'D7留存'
        WHEN rb.days_since_target_date = 14 THEN 'D14留存'
        WHEN rb.days_since_target_date = 30 THEN 'D30留存'
        ELSE CONCAT('D', rb.days_since_target_date, '留存')
    END AS retention_milestone
    
FROM retention_base rb
JOIN daily_trade_users dtu ON rb.trade_date = dtu.trade_date AND rb.shop_name = dtu.shop_name
JOIN cumulative_retention_base crb ON rb.trade_date = crb.trade_date 
    AND rb.shop_name = crb.shop_name
    AND rb.days_since_target_date = crb.days_since_target_date
WHERE rb.days_since_target_date <= @max_retention_days
ORDER BY rb.trade_date DESC, rb.shop_name, rb.days_since_target_date
limit 20000;