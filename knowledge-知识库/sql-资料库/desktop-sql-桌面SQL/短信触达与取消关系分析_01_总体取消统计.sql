-- 短信触达与取消授权关系分析 - 01 总体取消用户统计
-- 分析所有取消用户中有短信历史和无短信历史的分布

SET @cal_begin_date = DATE_SUB(DATE(CONVERT_TZ(NOW(), @@time_zone, 'America/New_York')), INTERVAL 90 DAY);
SET @cal_end_date = DATE_SUB(DATE(CONVERT_TZ(NOW(), @@time_zone, 'America/New_York')), INTERVAL 0 DAY);

WITH all_cancelled_users AS (
    -- 获取所有取消授权的用户（不限制是否收到短信）
    SELECT DISTINCT
        user_no,
        cancel_time_grant,
        DATE(cancel_time_grant) as cancel_date,
        is_success_order
    FROM dw_ads.ads_marketing_t_user_grant_d_his
    WHERE cancel_time_grant IS NOT NULL
      AND DATE(cancel_time_grant) >= @cal_begin_date
      AND DATE(cancel_time_grant) <= @cal_end_date
      AND INSTR(COALESCE(tenant, 'LKUS'), 'IQ') = 0
),
sms_history_for_cancelled AS (
    -- 获取所有取消用户的历史短信接收情况（不限日期）
    SELECT 
        c.user_no,
        c.cancel_time_grant,
        c.cancel_date,
        c.is_success_order,
        COUNT(DISTINCT s.id) as sms_count,
        CASE WHEN COUNT(DISTINCT s.id) > 0 THEN 1 ELSE 0 END as ever_received_sms,
        MAX(s.cdp_push_time) as last_sms_time
    FROM all_cancelled_users c
    LEFT JOIN dw_dwd.dwd_marketing_t_push_receipt_d_inc s ON c.user_no = s.user_no 
        AND s.cdp_push_time < c.cancel_time_grant  -- 取消前收到的短信
        AND s.cdp_push_state = 1
        AND s.message_id IS NOT NULL
        AND s.cdp_execute_state = 1
        AND s.contact_channel = 1  -- 只统计短信渠道
    GROUP BY c.user_no, c.cancel_time_grant, c.cancel_date, c.is_success_order
)

SELECT 
    '总体取消用户统计' as analysis_type,
    COUNT(DISTINCT user_no) as total_cancelled_users,
    COUNT(DISTINCT CASE WHEN ever_received_sms = 1 THEN user_no END) as cancelled_with_sms_history,
    COUNT(DISTINCT CASE WHEN ever_received_sms = 0 THEN user_no END) as cancelled_without_sms_history,
    ROUND(COUNT(DISTINCT CASE WHEN ever_received_sms = 1 THEN user_no END) * 100.0 / 
          COUNT(DISTINCT user_no), 2) as with_sms_history_rate,
    COUNT(DISTINCT CASE WHEN ever_received_sms = 1 AND is_success_order = 1 THEN user_no END) as cancelled_with_sms_and_order,
    COUNT(DISTINCT CASE WHEN ever_received_sms = 0 AND is_success_order = 1 THEN user_no END) as cancelled_without_sms_but_with_order,
    ROUND(SUM(CASE WHEN ever_received_sms = 1 THEN sms_count ELSE 0 END) / 
          NULLIF(COUNT(DISTINCT CASE WHEN ever_received_sms = 1 THEN user_no END), 0), 2) as avg_sms_per_cancelled_user
FROM sms_history_for_cancelled;