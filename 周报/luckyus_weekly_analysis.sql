-- =====================================================
-- 瑞幸周度数据分析：店均杯量 + 用户结构
-- 分析周期：上周(2025-01-27~02-02) vs 上上周(2025-01-20~01-26)
-- =====================================================

-- 时间参数
SET @last_week_begin = '2025-01-27';
SET @last_week_end = '2025-02-02';
SET @prev_week_begin = '2025-01-20';
SET @prev_week_end = '2025-01-26';


-- =====================================================
-- SQL 1: 店均杯量（两周对比）
-- =====================================================
WITH weekly_shop_stats AS (
    SELECT
        CASE
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN @last_week_begin AND @last_week_end THEN '上周'
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN @prev_week_begin AND @prev_week_end THEN '上上周'
        END AS week_label,
        b.shop_name,
        COUNT(*) AS cup_cnt
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    WHERE INSTR(a.tenant, 'IQ') = 0
      AND b.status = 90
      AND b.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND a.one_category_name = 'Drink'
      AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN @prev_week_begin AND @last_week_end
    GROUP BY week_label, b.shop_name
)

SELECT
    week_label AS 周期,
    SUM(cup_cnt) AS 总杯量,
    COUNT(DISTINCT shop_name) AS 门店数,
    ROUND(SUM(cup_cnt) / COUNT(DISTINCT shop_name), 2) AS 店均杯量
FROM weekly_shop_stats
WHERE week_label IS NOT NULL
GROUP BY week_label
ORDER BY week_label DESC;


-- =====================================================
-- SQL 2: 用户结构分析（按人群划分，含周环比）
-- =====================================================
WITH
-- 用户注册日期
user_register AS (
    SELECT
        user_no,
        DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) AS register_date
    FROM ods_luckyus_sales_crm.t_user
    WHERE INSTR(tenant, 'IQ') = 0
),

-- 用户首购日期（只统计 Drink）
user_first_order AS (
    SELECT
        b.user_no,
        MIN(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York'))) AS first_order_date
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    WHERE INSTR(a.tenant, 'IQ') = 0
      AND b.status = 90
      AND b.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND a.one_category_name = 'Drink'
    GROUP BY b.user_no
),

-- 订单明细 + 人群标签
order_with_segment AS (
    SELECT
        CASE
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN @last_week_begin AND @last_week_end THEN '上周'
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN @prev_week_begin AND @prev_week_end THEN '上上周'
        END AS week_label,
        b.user_no,
        a.order_id,
        DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) AS order_date,
        ur.register_date,
        ufo.first_order_date,
        CASE
            -- 新客：当日注册并完单（当天所有订单都算新客）
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) = ur.register_date THEN '新客'
            -- 0-15天老客：首购后 1-15 天
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) BETWEEN 1 AND 15 THEN '0-15天老客'
            -- 16-30天老客：首购后 16-30 天
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) BETWEEN 16 AND 30 THEN '16-30天老客'
            -- 31天+老客：首购后 31 天以上
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) >= 31 THEN '31天+老客'
            ELSE '未知'
        END AS user_segment
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    LEFT JOIN user_register ur ON b.user_no = ur.user_no
    LEFT JOIN user_first_order ufo ON b.user_no = ufo.user_no
    WHERE INSTR(a.tenant, 'IQ') = 0
      AND b.status = 90
      AND b.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND a.one_category_name = 'Drink'
      AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN @prev_week_begin AND @last_week_end
),

-- 汇总统计
segment_stats AS (
    SELECT
        week_label,
        user_segment,
        COUNT(DISTINCT user_no) AS user_cnt,
        COUNT(DISTINCT order_id) AS order_cnt,
        COUNT(*) AS cup_cnt,
        ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT user_no), 2) AS cups_per_user,
        ROUND(COUNT(DISTINCT user_no) * 100.0 / SUM(COUNT(DISTINCT user_no)) OVER(PARTITION BY week_label), 2) AS user_pct,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(PARTITION BY week_label), 2) AS cup_pct
    FROM order_with_segment
    WHERE week_label IS NOT NULL
    GROUP BY week_label, user_segment
)

SELECT
    week_label AS 周期,
    user_segment AS 人群,
    user_cnt AS 下单人数,
    order_cnt AS 订单数,
    cup_cnt AS 杯量,
    cups_per_user AS 人均杯量,
    user_pct AS 人数占比,
    cup_pct AS 杯量占比
FROM segment_stats
ORDER BY week_label DESC,
    CASE user_segment
        WHEN '新客' THEN 1
        WHEN '0-15天老客' THEN 2
        WHEN '16-30天老客' THEN 3
        WHEN '31天+老客' THEN 4
        ELSE 5
    END;


-- =====================================================
-- SQL 3: 人群结构周环比变化（横向对比视图）
-- =====================================================
WITH
user_register AS (
    SELECT
        user_no,
        DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) AS register_date
    FROM ods_luckyus_sales_crm.t_user
    WHERE INSTR(tenant, 'IQ') = 0
),

user_first_order AS (
    SELECT
        b.user_no,
        MIN(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York'))) AS first_order_date
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    WHERE INSTR(a.tenant, 'IQ') = 0
      AND b.status = 90
      AND b.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND a.one_category_name = 'Drink'
    GROUP BY b.user_no
),

order_with_segment AS (
    SELECT
        CASE
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN @last_week_begin AND @last_week_end THEN '上周'
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN @prev_week_begin AND @prev_week_end THEN '上上周'
        END AS week_label,
        b.user_no,
        a.order_id,
        CASE
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) = ur.register_date THEN '新客'
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) BETWEEN 1 AND 15 THEN '0-15天老客'
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) BETWEEN 16 AND 30 THEN '16-30天老客'
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) >= 31 THEN '31天+老客'
            ELSE '未知'
        END AS user_segment
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    LEFT JOIN user_register ur ON b.user_no = ur.user_no
    LEFT JOIN user_first_order ufo ON b.user_no = ufo.user_no
    WHERE INSTR(a.tenant, 'IQ') = 0
      AND b.status = 90
      AND b.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND a.one_category_name = 'Drink'
      AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN @prev_week_begin AND @last_week_end
),

segment_stats AS (
    SELECT
        week_label,
        user_segment,
        COUNT(DISTINCT user_no) AS user_cnt,
        COUNT(*) AS cup_cnt,
        ROUND(COUNT(DISTINCT user_no) * 100.0 / SUM(COUNT(DISTINCT user_no)) OVER(PARTITION BY week_label), 2) AS user_pct,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(PARTITION BY week_label), 2) AS cup_pct
    FROM order_with_segment
    WHERE week_label IS NOT NULL
    GROUP BY week_label, user_segment
)

SELECT
    user_segment AS 人群,
    MAX(CASE WHEN week_label = '上周' THEN user_cnt END) AS 上周人数,
    MAX(CASE WHEN week_label = '上上周' THEN user_cnt END) AS 上上周人数,
    MAX(CASE WHEN week_label = '上周' THEN user_pct END) AS 上周人数占比,
    MAX(CASE WHEN week_label = '上上周' THEN user_pct END) AS 上上周人数占比,
    ROUND(MAX(CASE WHEN week_label = '上周' THEN user_pct END) - MAX(CASE WHEN week_label = '上上周' THEN user_pct END), 2) AS 人数占比变化,
    MAX(CASE WHEN week_label = '上周' THEN cup_cnt END) AS 上周杯量,
    MAX(CASE WHEN week_label = '上上周' THEN cup_cnt END) AS 上上周杯量,
    MAX(CASE WHEN week_label = '上周' THEN cup_pct END) AS 上周杯量占比,
    MAX(CASE WHEN week_label = '上上周' THEN cup_pct END) AS 上上周杯量占比,
    ROUND(MAX(CASE WHEN week_label = '上周' THEN cup_pct END) - MAX(CASE WHEN week_label = '上上周' THEN cup_pct END), 2) AS 杯量占比变化
FROM segment_stats
GROUP BY user_segment
ORDER BY
    CASE user_segment
        WHEN '新客' THEN 1
        WHEN '0-15天老客' THEN 2
        WHEN '16-30天老客' THEN 3
        WHEN '31天+老客' THEN 4
        ELSE 5
    END;
