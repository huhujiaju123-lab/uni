-- 用户消费频次分布分析（与留存率分析相同口径）
-- 参数设置
SET @cal_begin_date = '2025-06-30';
SET @cal_end_date = '2025-07-08';

-- 第一步：获取交易数据（与留存率分析相同的过滤条件）
WITH weekly_orders AS (
    SELECT  
        b.user_no,
        a.order_id,
        DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) AS order_date,
        a.pay_money,
        b.shop_name,
        b.channel,
        a.spu_name,
        a.one_category_name
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    WHERE INSTR(a.tenant, 'IQ') = 0
    AND b.status = 90  -- 与留存率分析一致：只统计成功订单
    AND a.one_category_name = 'Drink'  -- 与留存率分析一致：只统计饮品
    AND b.shop_name IN ('8th & Broadway', '28th & 6th')  -- 与留存率分析一致：特定店铺
    AND b.user_no IS NOT NULL  -- 确保有用户ID
    AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) >= @cal_begin_date
    AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) <= @cal_end_date
),

-- 第二步：计算每个用户的消费频次
user_frequency AS (
    SELECT 
        user_no,
        COUNT(DISTINCT order_id) AS order_count,
        COUNT(DISTINCT order_date) AS visit_days,
        SUM(pay_money) AS total_amount,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date,
        GROUP_CONCAT(DISTINCT shop_name) AS visited_shops,
        COUNT(1) AS total_items  -- 总杯量（订单项数量）
    FROM weekly_orders
    GROUP BY user_no
),

-- 第三步：频次分组
frequency_groups AS (
    SELECT 
        user_no,
        order_count,
        visit_days,
        total_amount,
        total_items,
        first_order_date,
        last_order_date,
        visited_shops,
        CASE 
            WHEN order_count = 1 THEN '1次'
            WHEN order_count = 2 THEN '2次'
            WHEN order_count = 3 THEN '3次'
            WHEN order_count = 4 THEN '4次'
            WHEN order_count = 5 THEN '5次'
            WHEN order_count = 6 THEN '6次'
            WHEN order_count = 7 THEN '7次'
            ELSE '7+次'
        END AS frequency_group,
        CASE 
            WHEN order_count = 1 THEN 1
            WHEN order_count = 2 THEN 2
            WHEN order_count = 3 THEN 3
            WHEN order_count = 4 THEN 4
            WHEN order_count = 5 THEN 5
            WHEN order_count = 6 THEN 6
            WHEN order_count = 7 THEN 7
            ELSE 8
        END AS sort_order
    FROM user_frequency
)

-- 第四步：统计结果
SELECT 
    frequency_group AS '消费频次',
    COUNT(*) AS '用户数量',
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS '用户占比(%)',
    ROUND(AVG(order_count), 1) AS '平均订单数',
    ROUND(AVG(visit_days), 1) AS '平均到店天数',
    ROUND(AVG(total_amount), 2) AS '平均消费金额',
    ROUND(SUM(total_amount), 2) AS '总消费金额',
    ROUND(SUM(total_amount) * 100.0 / SUM(SUM(total_amount)) OVER(), 2) AS '金额占比(%)',
    ROUND(SUM(total_amount) / COUNT(*), 2) AS '人均消费金额',
    -- 新增：杯量相关统计
    ROUND(AVG(total_items), 1) AS '平均杯量',
    ROUND(SUM(total_items), 0) AS '总杯量',
    ROUND(SUM(total_items) * 100.0 / SUM(SUM(total_items)) OVER(), 2) AS '杯量占比(%)',
    ROUND(SUM(total_items) / COUNT(*), 1) AS '人均杯量',
    -- 新增：价值分析
    ROUND(AVG(total_amount / total_items), 2) AS '平均杯单价'
FROM frequency_groups
GROUP BY frequency_group, sort_order
ORDER BY sort_order;

-- 附加分析：按店铺分别统计
SELECT 
    '=== 按店铺分别统计 ===' AS section_title,
    NULL AS shop_name,
    NULL AS frequency_group,
    NULL AS user_count,
    NULL AS user_percentage,
    NULL AS total_amount,
    NULL AS total_items

UNION ALL

SELECT 
    '店铺维度分析' AS section_title,
    visited_shops AS shop_name,
    frequency_group,
    COUNT(*) AS user_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(PARTITION BY visited_shops), 2) AS user_percentage,
    ROUND(SUM(total_amount), 2) AS total_amount,
    SUM(total_items) AS total_items
FROM frequency_groups
WHERE visited_shops IN ('8th & Broadway', '28th & 6th')  -- 单店铺用户
GROUP BY visited_shops, frequency_group, sort_order
ORDER BY visited_shops, sort_order;

-- 汇总对比：新RFM vs 原RFM
SELECT 
    '=== 口径对比汇总 ===' AS comparison_title,
    NULL AS metric_name,
    NULL AS new_rfm_value,
    NULL AS difference

UNION ALL

SELECT 
    '对比说明' AS comparison_title,
    '本RFM分析采用与留存率分析相同的过滤条件' AS metric_name,
    '1. 只统计成功订单(status=90)' AS new_rfm_value,
    '2. 只统计饮品类商品' AS difference

UNION ALL

SELECT 
    '过滤条件' AS comparison_title,
    '3. 只统计指定店铺' AS metric_name,
    '4. 相同的时间范围' AS new_rfm_value,
    '预期结果应与留存率分析更接近' AS difference;