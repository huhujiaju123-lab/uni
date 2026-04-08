-- AB实验 不同客群的实验分流情况及后续表现分析
-- 结合短信触达漏斗指标，分析各实验组的转化表现
-- 锁定9月12日划分的人群，追踪后续每日表现

-- 设置时间参数
SET @group_date = DATE('2025-09-12');        -- 人群划分日期
SET @cal_begin_date = DATE('2025-09-12');    -- 分析开始日期
SET @cal_end_date = DATE('2025-09-22');      -- 分析结束日期

WITH experiment_users AS (
    -- 锁定9月12日的实验分流用户
    SELECT 
        group_name,
        user_no,
        dt as group_date
    FROM 
        dw_ads.ads_marketing_t_user_group_d_his
    WHERE 
        tenant = 'LKUS' 
        AND group_name = '828-911买5赠1 free drink圈人，≤15 day, ≤4 orders'
        AND dt = @group_date
),
sms_data AS (
    -- SMS触达数据 - 9月12日的触达记录
    SELECT DISTINCT
        user_no
    FROM dw_dwd.dwd_marketing_t_push_receipt_d_inc
    WHERE DATE(CONVERT_TZ(cdp_push_time, @@time_zone, 'America/New_York')) = @group_date
      AND cdp_push_time IS NOT NULL
      AND activity_name = '0912买5赠1活动通知'
),
-- 确定用户分组（触达组/对照组）
user_groups AS (
    SELECT 
        e.user_no,
        CASE 
            WHEN s.user_no IS NOT NULL THEN 'Treatment_30pct'
            ELSE 'Control_70pct'
        END as user_group_type
    FROM experiment_users e
    LEFT JOIN sms_data s ON e.user_no = s.user_no
),
-- 用户历史订单数（9月12日之前）
historical_orders AS (
    SELECT
        b.user_no,
        COUNT(DISTINCT b.id) as historical_order_count
    FROM ods_luckyus_sales_order.v_order b
    WHERE INSTR(b.tenant, 'IQ') = 0
      AND b.status = 90
      AND DATE(CONVERT_TZ(b.create_time, @@time_zone, 'America/New_York')) < @cal_begin_date
    GROUP BY b.user_no
),
-- APP流量数据汇总（避免笛卡尔积）
traffic_summary AS (
    SELECT
        dt as traffic_date,
        user_no,
        1 as has_app_open,
        MAX(CASE WHEN screen_name = 'menu' THEN 1 ELSE 0 END) as has_menu_view
    FROM dw_dws.dws_mg_log_user_screen_name_d_1d
    WHERE dt >= @cal_begin_date
      AND dt <= @cal_end_date
    GROUP BY dt, user_no
),
-- 订单数据汇总
order_summary AS (
    SELECT 
        b.user_no,
        DATE(CONVERT_TZ(b.create_time, @@time_zone, 'America/New_York')) as order_date,
        COUNT(DISTINCT b.id) as order_count,
        SUM(b.pay_money) as pay_amount
    FROM ods_luckyus_sales_order.v_order b
    WHERE INSTR(b.tenant, 'IQ') = 0
      AND b.status = 90
      AND DATE(CONVERT_TZ(b.create_time, @@time_zone, 'America/New_York')) >= @cal_begin_date
      AND DATE(CONVERT_TZ(b.create_time, @@time_zone, 'America/New_York')) <= @cal_end_date
    GROUP BY b.user_no, DATE(CONVERT_TZ(b.create_time, @@time_zone, 'America/New_York'))
),
-- 每日表现数据（统一结构）
daily_performance AS (
    -- 9月12日
    SELECT
        DATE('2025-09-12') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-12')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-12')
    
    UNION ALL
    
    -- 9月13日
    SELECT
        DATE('2025-09-13') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-13')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-13')
    
    UNION ALL
    
    -- 9月14日
    SELECT
        DATE('2025-09-14') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-14')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-14')
    
    UNION ALL
    
    -- 9月15日
    SELECT
        DATE('2025-09-15') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-15')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-15')

    UNION ALL

    -- 9月16日
    SELECT
        DATE('2025-09-16') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-16')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-16')

    UNION ALL

    -- 9月17日
    SELECT
        DATE('2025-09-17') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-17')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-17')

    UNION ALL

    -- 9月18日
    SELECT
        DATE('2025-09-18') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-18')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-18')

    UNION ALL

    -- 9月19日
    SELECT
        DATE('2025-09-19') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-19')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-19')

    UNION ALL

    -- 9月20日
    SELECT
        DATE('2025-09-20') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-20')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-20')

    UNION ALL

    -- 9月21日
    SELECT
        DATE('2025-09-21') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-21')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-21')

    UNION ALL

    -- 9月22日
    SELECT
        DATE('2025-09-22') as analysis_date,
        u.user_no,
        u.user_group_type,
        COALESCE(h.historical_order_count, 0) as hist_orders,
        CASE WHEN t.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_app_open,
        CASE WHEN t.has_menu_view = 1 THEN 1 ELSE 0 END as daily_menu_view,
        CASE WHEN o.user_no IS NOT NULL THEN 1 ELSE 0 END as daily_has_order,
        COALESCE(o.order_count, 0) as daily_orders,
        COALESCE(o.pay_amount, 0) as daily_revenue
    FROM user_groups u
    LEFT JOIN historical_orders h ON u.user_no = h.user_no
    LEFT JOIN traffic_summary t ON u.user_no = t.user_no AND t.traffic_date = DATE('2025-09-22')
    LEFT JOIN order_summary o ON u.user_no = o.user_no AND o.order_date = DATE('2025-09-22')
),
-- 计算累积订单（用于判断是否达到第5单）
cumulative_orders AS (
    SELECT
        p.analysis_date,
        p.user_no,
        p.user_group_type,
        p.hist_orders,
        -- 计算截至当前日期的累积订单数
        p.hist_orders + SUM(p2.daily_orders) as total_cumulative_orders
    FROM daily_performance p
    LEFT JOIN daily_performance p2 
        ON p.user_no = p2.user_no 
        AND p2.analysis_date <= p.analysis_date
    GROUP BY p.analysis_date, p.user_no, p.user_group_type, p.hist_orders
)

-- 最终聚合
SELECT 
    d.analysis_date,
    d.user_group_type,
    COUNT(DISTINCT d.user_no) AS total_users,
    -- 当日行为指标
    SUM(d.daily_app_open) AS daily_app_open_users,
    SUM(d.daily_menu_view) AS daily_menu_view_users,
    SUM(d.daily_has_order) AS daily_order_users,
    SUM(d.daily_orders) AS daily_orders,
    SUM(d.daily_revenue) AS daily_revenue,
    -- 转化率
    ROUND(SUM(d.daily_app_open) * 100.0 / COUNT(DISTINCT d.user_no), 2) AS app_open_rate,
    ROUND(SUM(d.daily_menu_view) * 100.0 / COUNT(DISTINCT d.user_no), 2) AS menu_view_rate,
    ROUND(SUM(d.daily_has_order) * 100.0 / COUNT(DISTINCT d.user_no), 2) AS order_conversion_rate,
    -- 累积指标
    ROUND(AVG(d.hist_orders), 2) AS avg_historical_orders,
    SUM(c.total_cumulative_orders) AS cumulative_total_orders,
    ROUND(AVG(c.total_cumulative_orders), 2) AS avg_cumulative_orders,
    SUM(CASE WHEN c.total_cumulative_orders >= 5 THEN 1 ELSE 0 END) AS users_reached_5th_order,
    ROUND(100.0 * SUM(CASE WHEN c.total_cumulative_orders >= 5 THEN 1 ELSE 0 END) / COUNT(DISTINCT d.user_no), 2) AS pct_reached_5th_order
FROM daily_performance d
LEFT JOIN cumulative_orders c 
    ON d.user_no = c.user_no 
    AND d.analysis_date = c.analysis_date
GROUP BY 
    d.analysis_date,
    d.user_group_type
ORDER BY 
    d.analysis_date,
    d.user_group_type
LIMIT 10000;