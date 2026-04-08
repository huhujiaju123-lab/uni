-- 短信触达与取消授权关系分析 - 04 按活动分析
-- 按短信活动名称分析取消授权情况

SET @cal_begin_date = DATE_SUB(DATE(CONVERT_TZ(NOW(), @@time_zone, 'America/New_York')), INTERVAL 90 DAY);
SET @cal_end_date = DATE_SUB(DATE(CONVERT_TZ(NOW(), @@time_zone, 'America/New_York')), INTERVAL 0 DAY);

WITH user_grant_status AS (
    -- 获取用户授权状态变化（去重）
    SELECT DISTINCT
        user_no,
        cancel_time_grant,
        is_success_order
    FROM dw_ads.ads_marketing_t_user_grant_d_his
    WHERE dt >= @cal_begin_date
      AND dt <= @cal_end_date
      AND INSTR(COALESCE(tenant, 'LKUS'), 'IQ') = 0
),
sms_sent_users AS (
    -- 获取短信发送用户
    SELECT 
        user_no,
        DATE(CONVERT_TZ(cdp_push_time, @@time_zone, 'America/New_York')) as push_date,
        activity_name,
        user_receipt_state,
        cdp_push_time,
        id
    FROM dw_dwd.dwd_marketing_t_push_receipt_d_inc
    WHERE DATE(CONVERT_TZ(cdp_push_time, @@time_zone, 'America/New_York')) >= @cal_begin_date
      AND DATE(CONVERT_TZ(cdp_push_time, @@time_zone, 'America/New_York')) <= @cal_end_date 
      AND cdp_push_time IS NOT NULL
      AND id IS NOT NULL
      AND cdp_push_state = 1
      AND message_id IS NOT NULL
      AND cdp_execute_state = 1
      AND contact_channel = 1  -- 只统计短信渠道
),
last_sms_before_cancel AS (
    -- 获取每个取消用户取消前的最后一条短信活动
    SELECT 
        s.user_no,
        s.activity_name as cancel_trigger_activity,
        s.cdp_push_time,
        g.cancel_time_grant,
        g.is_success_order,
        ROW_NUMBER() OVER (PARTITION BY s.user_no ORDER BY s.cdp_push_time DESC) as rn
    FROM sms_sent_users s
    JOIN user_grant_status g ON s.user_no = g.user_no 
        AND g.cancel_time_grant IS NOT NULL 
        AND g.cancel_time_grant > s.cdp_push_time
),
cancel_attribution AS (
    -- 每个用户只归因到最后一个触发取消的活动
    SELECT 
        user_no,
        cancel_trigger_activity,
        cdp_push_time,
        cancel_time_grant,
        is_success_order,
        TIMESTAMPDIFF(DAY, cdp_push_time, cancel_time_grant) as days_to_cancel
    FROM last_sms_before_cancel 
    WHERE rn = 1
),
order_data AS (
    -- 获取用户订单数据
    SELECT
        b.user_no,
        DATE(CONVERT_TZ(b.create_time, @@time_zone, 'America/New_York')) as order_date
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    WHERE INSTR(b.tenant, 'IQ') = 0
      AND b.status = 90
      AND DATE(CONVERT_TZ(b.create_time, @@time_zone, 'America/New_York')) >= @cal_begin_date
      AND DATE(CONVERT_TZ(b.create_time, @@time_zone, 'America/New_York')) <= @cal_end_date
)

-- 按活动分析（包含取消归因）
SELECT 
    s.activity_name,
    COUNT(DISTINCT s.user_no) as total_sms_users,
    COUNT(DISTINCT s.id) as total_sms_sends,
    
    -- 归因后的取消统计（每个取消用户只归因到最后触发的活动）
    COUNT(DISTINCT CASE WHEN c.cancel_trigger_activity = s.activity_name THEN c.user_no END) as attributed_cancelled_users,
    ROUND(COUNT(DISTINCT CASE WHEN c.cancel_trigger_activity = s.activity_name THEN c.user_no END) * 100.0 / 
          COUNT(DISTINCT s.user_no), 2) as attributed_cancel_rate,
    
    -- 归因后1天内取消
    COUNT(DISTINCT CASE WHEN c.cancel_trigger_activity = s.activity_name AND c.days_to_cancel <= 1 THEN c.user_no END) as attributed_cancelled_within_1day,
    ROUND(COUNT(DISTINCT CASE WHEN c.cancel_trigger_activity = s.activity_name AND c.days_to_cancel <= 1 THEN c.user_no END) * 100.0 / 
          COUNT(DISTINCT s.user_no), 2) as attributed_cancel_rate_1day,
    
    -- 平均取消间隔天数（仅针对归因到该活动的取消）
    ROUND(AVG(CASE WHEN c.cancel_trigger_activity = s.activity_name THEN c.days_to_cancel END), 1) as avg_days_to_cancel,
    
    -- 订单转化率
    COUNT(DISTINCT CASE WHEN o.user_no IS NOT NULL THEN s.user_no END) as users_with_order,
    ROUND(COUNT(DISTINCT CASE WHEN o.user_no IS NOT NULL THEN s.user_no END) * 100.0 / 
          COUNT(DISTINCT s.user_no), 2) as order_rate,
    
    -- 归因取消用户中有订单的比例
    COUNT(DISTINCT CASE WHEN c.cancel_trigger_activity = s.activity_name AND c.is_success_order = 1 THEN c.user_no END) as attributed_cancelled_with_order,
    ROUND(COUNT(DISTINCT CASE WHEN c.cancel_trigger_activity = s.activity_name AND c.is_success_order = 1 THEN c.user_no END) * 100.0 / 
          NULLIF(COUNT(DISTINCT CASE WHEN c.cancel_trigger_activity = s.activity_name THEN c.user_no END), 0), 2) as cancelled_users_with_order_rate

FROM sms_sent_users s
LEFT JOIN cancel_attribution c ON c.cancel_trigger_activity = s.activity_name
LEFT JOIN order_data o ON s.user_no = o.user_no AND o.order_date = s.push_date
GROUP BY s.activity_name
ORDER BY attributed_cancel_rate DESC
LIMIT 100;