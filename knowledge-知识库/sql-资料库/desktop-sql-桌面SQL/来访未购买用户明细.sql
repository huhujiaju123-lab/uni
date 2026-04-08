-- 来访未购买用户明细SQL - 用户列表版
-- 导出过去7天访问APP但未产生订单的用户明细列表
-- 剔除：1) 距离上次下单30天以上的沉默用户 2) 首次下单15天以内的用户
-- 基于dw_dws.dws_mg_log_user_screen_name_d_1d流量数据和v_order订单数据

-- 参数设置：自动计算过去7天
SET @cal_begin_date = DATE_SUB(DATE(NOW()), INTERVAL 7 DAY);
SET @cal_end_date = DATE_SUB(DATE(NOW()), INTERVAL 1 DAY);
SET @today = DATE(NOW());

WITH
-- 过去7天有访问home页面的用户（去重）
recent_7d_visitors AS (
    SELECT DISTINCT user_no
    FROM dw_dws.dws_mg_log_user_screen_name_d_1d
    WHERE dt >= @cal_begin_date AND dt <= @cal_end_date
        AND screen_name = 'home'
),

-- 过去7天有下单的用户（去重）
recent_7d_purchasers AS (
    SELECT DISTINCT user_no
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant, 'IQ') = 0
        AND status = 90
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
        AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= @cal_begin_date
        AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) <= @cal_end_date
),

-- 用户首单和末单时间
user_order_info AS (
    SELECT
        user_no,
        MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_order_date,
        MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS last_order_date
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant, 'IQ') = 0
        AND status = 90
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY user_no
),

-- 过去7天来访但未下单的目标用户（剔除沉默用户和新购用户）
target_users AS (
    SELECT
        v.user_no,
        o.first_order_date,
        o.last_order_date,
        DATEDIFF(@today, o.first_order_date) AS days_since_first_order,
        DATEDIFF(@today, o.last_order_date) AS days_since_last_order
    FROM recent_7d_visitors v
    LEFT JOIN recent_7d_purchasers p ON v.user_no = p.user_no
    INNER JOIN user_order_info o ON v.user_no = o.user_no
    WHERE p.user_no IS NULL  -- 过去7天没有下单
        AND DATEDIFF(@today, o.first_order_date) > 15  -- 首次下单超过15天
        AND DATEDIFF(@today, o.last_order_date) < 30  -- 最后下单不超过30天
),

-- 目标用户在过去7天的页面访问明细（透视为列）
user_page_visits_pivot AS (
    SELECT
        tu.user_no,
        MAX(CASE WHEN t.screen_name = 'home' THEN 1 ELSE 0 END) AS visited_home,
        MAX(CASE WHEN t.screen_name = 'menu' THEN 1 ELSE 0 END) AS visited_menu,
        MAX(CASE WHEN t.screen_name = 'productdetail' THEN 1 ELSE 0 END) AS visited_productdetail,
        MAX(CASE WHEN t.screen_name = 'confirmorder' THEN 1 ELSE 0 END) AS visited_confirmorder,
        MAX(CASE WHEN t.screen_name = 'orderdetail' THEN 1 ELSE 0 END) AS visited_orderdetail,
        COUNT(DISTINCT t.dt) AS total_visit_days,
        COUNT(DISTINCT t.screen_name) AS unique_screens_visited
    FROM target_users tu
    INNER JOIN dw_dws.dws_mg_log_user_screen_name_d_1d t
        ON tu.user_no = t.user_no
        AND t.dt >= @cal_begin_date
        AND t.dt <= @cal_end_date
    GROUP BY tu.user_no
)

-- 最终输出：每个用户的明细数据
SELECT
    tu.user_no,
    tu.first_order_date,
    tu.last_order_date,
    tu.days_since_first_order,
    tu.days_since_last_order,

    -- 访问行为数据
    COALESCE(pv.total_visit_days, 0) AS visit_days_in_7d,
    COALESCE(pv.unique_screens_visited, 0) AS unique_screens_count,

    -- 页面访问标记
    COALESCE(pv.visited_home, 0) AS is_visited_home,
    COALESCE(pv.visited_menu, 0) AS is_visited_menu,
    COALESCE(pv.visited_productdetail, 0) AS is_visited_productdetail,
    COALESCE(pv.visited_confirmorder, 0) AS is_visited_confirmorder,
    COALESCE(pv.visited_orderdetail, 0) AS is_visited_orderdetail,

    -- 用户漏斗阶段判断
    CASE
        WHEN COALESCE(pv.visited_confirmorder, 0) = 1 THEN 'reached_confirmorder'
        WHEN COALESCE(pv.visited_productdetail, 0) = 1 THEN 'reached_productdetail'
        WHEN COALESCE(pv.visited_menu, 0) = 1 THEN 'reached_menu'
        WHEN COALESCE(pv.visited_home, 0) = 1 THEN 'reached_home'
        ELSE 'other_pages_only'
    END AS funnel_stage

FROM target_users tu
LEFT JOIN user_page_visits_pivot pv ON tu.user_no = pv.user_no
ORDER BY
    tu.days_since_last_order ASC,
    pv.total_visit_days DESC
LIMIT 50000
