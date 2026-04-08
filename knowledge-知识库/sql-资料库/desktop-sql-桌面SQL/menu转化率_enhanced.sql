-- 页面漏斗转化率分析SQL
-- 基于dw_dws.dws_mg_log_user_screen_name_d_1d数据分析用户页面转化路径
-- show create table dw_dws.dws_mg_log_user_screen_name_d_1d;


-- 参数设置
-- SET @cal_begin_date = '2025-06-30';
-- --参数3:自动计算纽约时间滚动8天的结束时间（今天）
-- SET @cal_end_date ='2025-09-04';
SET @cal_begin_date = DATE_SUB(DATE(NOW()), INTERVAL 15 DAY);
--参数3:自动计算纽约时间滚动8天的结束时间（今天）
SET @cal_end_date = DATE_SUB(DATE(NOW()), INTERVAL 0 DAY);



SELECT
    dt,
    is_new_uer,
    -- maturity_level_no_0_name,
    -- 各页面访问用户数
    COUNT(DISTINCT user_no) AS total_users,
    COUNT(DISTINCT CASE WHEN screen_name = 'home' THEN user_no END) AS home_users,
    COUNT(DISTINCT CASE WHEN screen_name = 'menu' THEN user_no END) AS menu_users,
    COUNT(DISTINCT CASE WHEN screen_name = 'productdetail' THEN user_no END) AS productdetail_users,
    COUNT(DISTINCT CASE WHEN screen_name = 'confirmorder' THEN user_no END) AS confirmorder_users,
    COUNT(DISTINCT CASE WHEN screen_name = 'orderdetail' THEN user_no END) AS orderdetail_users,
    
    -- 各页面总PV
    SUM(CASE WHEN screen_name = 'home' THEN pv ELSE 0 END) AS home_pv,
    SUM(CASE WHEN screen_name = 'menu' THEN pv ELSE 0 END) AS menu_pv,
    SUM(CASE WHEN screen_name = 'productdetail' THEN pv ELSE 0 END) AS productdetail_pv,
    SUM(CASE WHEN screen_name = 'confirmorder' THEN pv ELSE 0 END) AS confirmorder_pv,
    SUM(CASE WHEN screen_name = 'orderdetail' THEN pv ELSE 0 END) AS orderdetail_pv
FROM dw_dws.dws_mg_log_user_screen_name_d_1d
WHERE dt BETWEEN @cal_begin_date AND @cal_end_date
    -- AND event_code = 'page_start'
GROUP BY dt, is_new_uer