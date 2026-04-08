-- 券使用率分析SQL（支持累计使用率和时间维度分析）
-- 分析新人券包的领取和使用情况，按券模板和时间维度分组统计
-- 参数设置
SET @cal_begin_date = '2025-06-30';
SET @cal_end_date = '2025-07-08';
SET @proposal_id = 814; -- 新人券包方案编号：LKUSCP117524731544281088

-- 基础数据准备
WITH base_data AS (
    SELECT 
        id,
        user_no,
        coupon_template_id,
        coupon_name,
        coupon_show_name,
        coupon_denomination,
        coupon_discount_type,
        proposal_name,
        use_status,
        is_use_same_day,
        DATE(CONVERT_TZ(receive_time, @@time_zone, 'America/New_York')) AS receive_date,
        DATE(CONVERT_TZ(use_time, @@time_zone, 'America/New_York')) AS use_date,
        receive_time,
        use_time
    FROM dw_dwd.dwd_t_mkt_coupon_use_record_d_inc
    WHERE INSTR(tenant, 'IQ') = 0
        AND proposal_id = @proposal_id
        AND DATE(CONVERT_TZ(receive_time, @@time_zone, 'America/New_York')) >= @cal_begin_date
        AND DATE(CONVERT_TZ(receive_time, @@time_zone, 'America/New_York')) <= @cal_end_date
),

-- 累计使用率计算（按领取日期累计）
cumulative_usage AS (
    SELECT 
        bd1.receive_date,
        bd1.coupon_template_id,
        bd1.coupon_name,
        bd1.coupon_show_name,
        bd1.coupon_denomination,
        bd1.proposal_name,
        
        -- 当日领取统计
        COUNT(DISTINCT bd1.user_no) AS daily_received_users,
        COUNT(bd1.id) AS daily_received_coupons,
        
        -- 累计使用统计（截止到当前日期的所有使用情况）
        COUNT(DISTINCT CASE WHEN bd2.use_status = 1 AND bd2.receive_date <= bd1.receive_date THEN bd2.user_no END) AS cumulative_used_users,
        COUNT(CASE WHEN bd2.use_status = 1 AND bd2.receive_date <= bd1.receive_date THEN bd2.id END) AS cumulative_used_coupons,
        
        -- 当日使用统计
        COUNT(DISTINCT CASE WHEN bd1.use_status = 1 AND bd1.is_use_same_day = 1 THEN bd1.user_no END) AS same_day_used_users,
        COUNT(CASE WHEN bd1.use_status = 1 AND bd1.is_use_same_day = 1 THEN bd1.id END) AS same_day_used_coupons,
        
        -- 后续使用统计（领取后非当日使用）
        COUNT(DISTINCT CASE WHEN bd1.use_status = 1 AND bd1.is_use_same_day = 0 THEN bd1.user_no END) AS later_used_users,
        COUNT(CASE WHEN bd1.use_status = 1 AND bd1.is_use_same_day = 0 THEN bd1.id END) AS later_used_coupons
        
    FROM base_data bd1
    LEFT JOIN base_data bd2 ON bd1.coupon_template_id = bd2.coupon_template_id
    GROUP BY bd1.receive_date, bd1.coupon_template_id, bd1.coupon_name, bd1.coupon_show_name, 
             bd1.coupon_denomination, bd1.proposal_name
),

-- 券模板整体统计
template_summary AS (
    SELECT 
        coupon_template_id,
        coupon_name,
        coupon_show_name,
        coupon_denomination,
        proposal_name,
        
        -- 总领取统计
        COUNT(DISTINCT user_no) AS total_received_users,
        COUNT(*) AS total_received_coupons,
        
        -- 总使用统计
        COUNT(DISTINCT CASE WHEN use_status = 1 THEN user_no END) AS total_used_users,
        COUNT(CASE WHEN use_status = 1 THEN 1 END) AS total_used_coupons,
        
        -- 使用率计算
        ROUND(COUNT(DISTINCT CASE WHEN use_status = 1 THEN user_no END) * 100.0 / COUNT(DISTINCT user_no), 2) AS user_usage_rate_pct,
        ROUND(COUNT(CASE WHEN use_status = 1 THEN 1 END) * 100.0 / COUNT(*), 2) AS coupon_usage_rate_pct,
        
        -- 时间分布
        COUNT(CASE WHEN use_status = 1 AND is_use_same_day = 1 THEN 1 END) AS same_day_used_total,
        COUNT(CASE WHEN use_status = 1 AND is_use_same_day = 0 THEN 1 END) AS later_used_total,
        
        -- 使用时间分析
        MIN(receive_date) AS first_receive_date,
        MAX(receive_date) AS last_receive_date,
        MIN(use_date) AS first_use_date,
        MAX(use_date) AS last_use_date
        
    FROM base_data
    GROUP BY coupon_template_id, coupon_name, coupon_show_name, coupon_denomination, proposal_name
)

-- 1. 券模板整体使用率统计
SELECT 
    '=== 券模板整体使用率统计 ===' AS section_title,
    NULL AS coupon_template_id,
    NULL AS coupon_name,
    NULL AS received_users,
    NULL AS used_users,
    NULL AS usage_rate,
    NULL AS same_day_rate,
    NULL AS later_rate
    
UNION ALL

SELECT 
    '券模板汇总' AS section_title,
    coupon_template_id,
    coupon_name,
    total_received_users AS received_users,
    total_used_users AS used_users,
    CONCAT(user_usage_rate_pct, '%') AS usage_rate,
    CONCAT(ROUND(same_day_used_total * 100.0 / NULLIF(total_used_coupons, 0), 2), '%') AS same_day_rate,
    CONCAT(ROUND(later_used_total * 100.0 / NULLIF(total_used_coupons, 0), 2), '%') AS later_rate
FROM template_summary
ORDER BY coupon_template_id;

-- 2. 按日期和券模板的累计使用率分析
SELECT 
    '=== 按日期累计使用率分析 ===' AS section_title,
    NULL AS receive_date,
    NULL AS template_id,
    NULL AS coupon_name,
    NULL AS daily_received,
    NULL AS cumulative_used,
    NULL AS cumulative_rate,
    NULL AS same_day_used,
    NULL AS later_used
    
UNION ALL

SELECT 
    '日期维度分析' AS section_title,
    receive_date,
    coupon_template_id AS template_id,
    coupon_name,
    daily_received_users AS daily_received,
    cumulative_used_users AS cumulative_used,
    CONCAT(ROUND(cumulative_used_users * 100.0 / NULLIF(daily_received_users, 0), 2), '%') AS cumulative_rate,
    same_day_used_users AS same_day_used,
    later_used_users AS later_used
FROM cumulative_usage
ORDER BY receive_date, coupon_template_id;

-- 3. 券使用情况详细分析（按使用的券模板ID拆分）
SELECT 
    '=== 券使用情况详细分析 ===' AS analysis_title,
    NULL AS used_template_id,
    NULL AS used_coupon_name,
    NULL AS used_users,
    NULL AS used_coupons,
    NULL AS avg_use_time_gap,
    NULL AS use_date_range
    
UNION ALL

SELECT 
    '使用券模板分析' AS analysis_title,
    coupon_template_id AS used_template_id,
    coupon_name AS used_coupon_name,
    COUNT(DISTINCT user_no) AS used_users,
    COUNT(*) AS used_coupons,
    ROUND(AVG(CASE 
        WHEN use_status = 1 THEN TIMESTAMPDIFF(HOUR, receive_time, use_time) 
        ELSE NULL 
    END), 2) AS avg_use_time_gap,
    CONCAT(MIN(use_date), ' 至 ', MAX(use_date)) AS use_date_range
FROM base_data
WHERE use_status = 1
GROUP BY coupon_template_id, coupon_name
ORDER BY coupon_template_id;

-- 4. 用户券使用序列分析（用户在不同券模板间的使用路径）
SELECT 
    '=== 用户券使用序列分析 ===' AS path_analysis,
    NULL AS user_no,
    NULL AS coupon_sequence,
    NULL AS template_usage_path,
    NULL AS total_usage_count,
    NULL AS usage_time_span
    
UNION ALL

SELECT 
    '用户使用路径' AS path_analysis,
    user_no,
    ROW_NUMBER() OVER (PARTITION BY user_no ORDER BY use_time) AS coupon_sequence,
    GROUP_CONCAT(DISTINCT coupon_template_id ORDER BY use_time) AS template_usage_path,
    COUNT(*) AS total_usage_count,
    CONCAT(
        TIMESTAMPDIFF(DAY, MIN(use_time), MAX(use_time)), 
        ' 天'
    ) AS usage_time_span
FROM base_data
WHERE use_status = 1
GROUP BY user_no
HAVING COUNT(*) > 1  -- 只显示使用了多张券的用户
ORDER BY total_usage_count DESC
LIMIT 20;

-- 5. 券模板使用时间分布分析
SELECT 
    '=== 券模板使用时间分布 ===' AS time_distribution,
    NULL AS template_id,
    NULL AS coupon_name,
    NULL AS within_1_hour,
    NULL AS within_1_day,
    NULL AS within_3_days,
    NULL AS over_3_days,
    NULL AS avg_hours_to_use
    
UNION ALL

SELECT 
    '使用时间分布' AS time_distribution,
    coupon_template_id,
    coupon_name,
    COUNT(CASE WHEN use_status = 1 AND TIMESTAMPDIFF(HOUR, receive_time, use_time) <= 1 THEN 1 END) AS within_1_hour,
    COUNT(CASE WHEN use_status = 1 AND TIMESTAMPDIFF(HOUR, receive_time, use_time) <= 24 THEN 1 END) AS within_1_day,
    COUNT(CASE WHEN use_status = 1 AND TIMESTAMPDIFF(HOUR, receive_time, use_time) <= 72 THEN 1 END) AS within_3_days,
    COUNT(CASE WHEN use_status = 1 AND TIMESTAMPDIFF(HOUR, receive_time, use_time) > 72 THEN 1 END) AS over_3_days,
    ROUND(AVG(CASE WHEN use_status = 1 THEN TIMESTAMPDIFF(HOUR, receive_time, use_time) END), 2) AS avg_hours_to_use
FROM base_data
GROUP BY coupon_template_id, coupon_name
ORDER BY coupon_template_id;