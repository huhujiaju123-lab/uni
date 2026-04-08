-- 来访未购买用户分析SQL
-- 统计过去7天访问APP但未产生订单的用户数据
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

-- 目标用户在过去7天的页面访问统计（按页面类型聚合）
user_page_visits AS (
    SELECT
        COUNT(DISTINCT CASE WHEN t.screen_name = 'home' THEN t.user_no END) AS home_users,
        COUNT(DISTINCT CASE WHEN t.screen_name = 'menu' THEN t.user_no END) AS menu_users,
        COUNT(DISTINCT CASE WHEN t.screen_name = 'productdetail' THEN t.user_no END) AS productdetail_users,
        COUNT(DISTINCT CASE WHEN t.screen_name = 'confirmorder' THEN t.user_no END) AS confirmorder_users,
        COUNT(DISTINCT CASE WHEN t.screen_name = 'orderdetail' THEN t.user_no END) AS orderdetail_users
    FROM target_users tu
    INNER JOIN dw_dws.dws_mg_log_user_screen_name_d_1d t
        ON tu.user_no = t.user_no
        AND t.dt >= @cal_begin_date
        AND t.dt <= @cal_end_date
),

-- 目标用户基础统计
target_user_stats AS (
    SELECT
        COUNT(DISTINCT user_no) AS target_user_cnt,
        ROUND(AVG(days_since_first_order), 1) AS avg_days_since_first_order,
        ROUND(AVG(days_since_last_order), 1) AS avg_days_since_last_order,
        MIN(days_since_first_order) AS min_days_since_first_order,
        MAX(days_since_first_order) AS max_days_since_first_order,
        MIN(days_since_last_order) AS min_days_since_last_order,
        MAX(days_since_last_order) AS max_days_since_last_order
    FROM target_users
)

-- 最终输出：过去7天来访未购买的目标用户统计
SELECT
    -- 统计周期
    @cal_begin_date AS stat_begin_date,
    @cal_end_date AS stat_end_date,

    -- 目标用户总数
    ts.target_user_cnt,

    -- 用户首单和末单距今天数分布
    ts.avg_days_since_first_order,
    ts.avg_days_since_last_order,
    ts.min_days_since_first_order,
    ts.max_days_since_first_order,
    ts.min_days_since_last_order,
    ts.max_days_since_last_order,

    -- 页面访问漏斗：访问过该页面的用户数
    pv.home_users AS home_visit_users,
    pv.menu_users AS menu_visit_users,
    pv.productdetail_users AS productdetail_visit_users,
    pv.confirmorder_users AS confirmorder_visit_users,
    pv.orderdetail_users AS orderdetail_visit_users,

    -- 漏斗转化率
    ROUND(pv.home_users * 100.0 / NULLIF(ts.target_user_cnt, 0), 2) AS home_visit_rate_pct,
    ROUND(pv.menu_users * 100.0 / NULLIF(ts.target_user_cnt, 0), 2) AS menu_visit_rate_pct,
    ROUND(pv.productdetail_users * 100.0 / NULLIF(ts.target_user_cnt, 0), 2) AS productdetail_visit_rate_pct,
    ROUND(pv.confirmorder_users * 100.0 / NULLIF(ts.target_user_cnt, 0), 2) AS confirmorder_visit_rate_pct,

    -- 对比数据：过去7天总访问和总下单用户数
    (SELECT COUNT(DISTINCT user_no) FROM recent_7d_visitors) AS total_7d_visitors,
    (SELECT COUNT(DISTINCT user_no) FROM recent_7d_purchasers) AS total_7d_purchasers,

    -- 目标用户占比
    ROUND(ts.target_user_cnt * 100.0 /
          NULLIF((SELECT COUNT(DISTINCT user_no) FROM recent_7d_visitors), 0), 2) AS target_user_rate_pct

FROM target_user_stats ts
CROSS JOIN user_page_visits pv

LIMIT 50000
