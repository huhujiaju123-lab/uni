-- =====================================================
-- 分享有礼活动监控SQL
-- 用途: 监控分享有礼活动的实际线上数据
-- 目标: 追踪达成10%拉新贡献占比的各项指标
-- =====================================================

-- 日期参数设置
SET @cal_begin_date = DATE_SUB(DATE(NOW()), INTERVAL 30 DAY);  -- 监控开始日期
SET @cal_end_date = DATE_SUB(DATE(NOW()), INTERVAL 0 DAY);     -- 监控结束日期
SET @activity_pattern = '%LKUS%';                                -- 活动编号匹配模式

-- =====================================================
-- CTE 1: 基础邀请数据
-- =====================================================
WITH base_invitation_data AS (
    SELECT
        DATE(CONVERT_TZ(created_time, '+00:00', 'America/New_York')) AS invite_date,
        inviter_user_no,
        invitee_user_no,
        invitation_id,
        activity_no,
        status AS invitation_status,  -- 邀请状态
        created_time AS invitation_time,
        -- 判断是否成功邀请（根据业务逻辑调整）
        CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END AS is_success_invite
    FROM ods_luckyus_sales_marketing.t_user_invitation_info
    WHERE activity_no LIKE @activity_pattern
        AND DATE(CONVERT_TZ(created_time, '+00:00', 'America/New_York')) BETWEEN @cal_begin_date AND @cal_end_date
),

-- =====================================================
-- CTE 2: 用户首次注册时间（区分新老用户）
-- =====================================================
user_first_register AS (
    SELECT
        user_no,
        DATE(CONVERT_TZ(MIN(created_time), '+00:00', 'America/New_York')) AS first_register_date
    FROM ods_luckyus_sales_user.t_user
    WHERE user_no IS NOT NULL
    GROUP BY user_no
),

-- =====================================================
-- CTE 3: 分享行为数据（曝光、点击、分享）
-- =====================================================
share_behavior_data AS (
    SELECT
        DATE(CONVERT_TZ(event_time, '+00:00', 'America/New_York')) AS event_date,
        user_no,
        event_type,  -- 'EXPOSURE' / 'CLICK' / 'SHARE'
        COUNT(*) AS event_count
    FROM ods_luckyus_sales_marketing.t_share_event_log
    WHERE activity_no LIKE @activity_pattern
        AND DATE(CONVERT_TZ(event_time, '+00:00', 'America/New_York')) BETWEEN @cal_begin_date AND @cal_end_date
    GROUP BY
        DATE(CONVERT_TZ(event_time, '+00:00', 'America/New_York')),
        user_no,
        event_type
),

-- =====================================================
-- CTE 4: 被邀请人订单数据
-- =====================================================
invitee_order_data AS (
    SELECT
        o.user_no AS invitee_user_no,
        DATE(CONVERT_TZ(o.created_time, '+00:00', 'America/New_York')) AS order_date,
        o.order_no,
        o.order_status,
        o.total_amount,
        -- 计算杯量
        SUM(oi.quantity) AS cup_count
    FROM ods_luckyus_sales_order.v_order o
    LEFT JOIN ods_luckyus_sales_order.t_order_item oi
        ON o.order_no = oi.order_no
    WHERE o.order_status IN ('COMPLETED', 'PAID')
        AND DATE(CONVERT_TZ(o.created_time, '+00:00', 'America/New_York')) BETWEEN @cal_begin_date AND @cal_end_date
    GROUP BY
        o.user_no,
        DATE(CONVERT_TZ(o.created_time, '+00:00', 'America/New_York')),
        o.order_no,
        o.order_status,
        o.total_amount
),

-- =====================================================
-- CTE 5: 邀请人奖励发放数据
-- =====================================================
inviter_reward_data AS (
    SELECT
        user_no AS inviter_user_no,
        DATE(CONVERT_TZ(grant_time, '+00:00', 'America/New_York')) AS grant_date,
        reward_type,  -- 券类型
        reward_count,
        success_invite_count  -- 基于几人成功发放的奖励
    FROM ods_luckyus_sales_marketing.t_reward_grant_log
    WHERE activity_no LIKE @activity_pattern
        AND DATE(CONVERT_TZ(grant_time, '+00:00', 'America/New_York')) BETWEEN @cal_begin_date AND @cal_end_date
),

-- =====================================================
-- CTE 6: 数据关联与计算
-- =====================================================
enriched_data AS (
    SELECT
        bid.invite_date,
        bid.inviter_user_no,
        bid.invitee_user_no,
        bid.invitation_id,
        bid.is_success_invite,

        -- 邀请人信息
        ufr_inviter.first_register_date AS inviter_first_register_date,
        CASE
            WHEN ufr_inviter.first_register_date >= @cal_begin_date THEN 'NEW'
            ELSE 'OLD'
        END AS inviter_type,

        -- 被邀请人信息
        ufr_invitee.first_register_date AS invitee_register_date,
        CASE
            WHEN ufr_invitee.first_register_date IS NOT NULL THEN 1
            ELSE 0
        END AS is_invitee_registered,

        -- 被邀请人订单信息
        iod.order_date AS invitee_order_date,
        iod.order_no AS invitee_order_no,
        iod.total_amount AS invitee_order_amount,
        iod.cup_count AS invitee_cup_count,

        -- 时间差计算
        DATEDIFF(ufr_invitee.first_register_date, bid.invite_date) AS days_to_register,
        DATEDIFF(iod.order_date, bid.invite_date) AS days_to_order,

        -- 转化标记
        CASE
            WHEN ufr_invitee.first_register_date = bid.invite_date THEN 1
            ELSE 0
        END AS is_register_same_day,

        CASE
            WHEN ufr_invitee.first_register_date <= DATE_ADD(bid.invite_date, INTERVAL 7 DAY) THEN 1
            ELSE 0
        END AS is_register_within_7d,

        CASE
            WHEN iod.order_date = bid.invite_date THEN 1
            ELSE 0
        END AS is_order_same_day,

        CASE
            WHEN iod.order_date <= DATE_ADD(bid.invite_date, INTERVAL 7 DAY) THEN 1
            ELSE 0
        END AS is_order_within_7d

    FROM base_invitation_data bid
    LEFT JOIN user_first_register ufr_inviter
        ON bid.inviter_user_no = ufr_inviter.user_no
    LEFT JOIN user_first_register ufr_invitee
        ON bid.invitee_user_no = ufr_invitee.user_no
    LEFT JOIN invitee_order_data iod
        ON bid.invitee_user_no = iod.invitee_user_no
),

-- =====================================================
-- CTE 7: 按日期汇总统计
-- =====================================================
daily_stats AS (
    SELECT
        ed.invite_date AS stat_date,

        -- =================== 邀请人指标 ===================
        -- 总邀请人数
        COUNT(DISTINCT ed.inviter_user_no) AS total_inviter_count,

        -- 新老邀请人数
        COUNT(DISTINCT CASE WHEN ed.inviter_type = 'NEW' THEN ed.inviter_user_no END) AS new_inviter_count,
        COUNT(DISTINCT CASE WHEN ed.inviter_type = 'OLD' THEN ed.inviter_user_no END) AS old_inviter_count,

        -- 成功邀请人数（至少1次成功）
        COUNT(DISTINCT CASE WHEN ed.is_success_invite = 1 THEN ed.inviter_user_no END) AS success_inviter_count_daily,

        -- 成功邀请人数（7天内转化）
        COUNT(DISTINCT CASE WHEN ed.is_register_within_7d = 1 THEN ed.inviter_user_no END) AS success_inviter_count_7d,

        -- 成功邀请人数（累计转化）
        COUNT(DISTINCT CASE WHEN ed.is_invitee_registered = 1 THEN ed.inviter_user_no END) AS success_inviter_count_total,

        -- =================== 邀请次数指标 ===================
        -- 总邀请次数
        COUNT(ed.invitation_id) AS total_invitation_count,

        -- 成功邀请次数（不同时间窗口）
        SUM(CASE WHEN ed.is_register_same_day = 1 THEN 1 ELSE 0 END) AS success_invitation_count_same_day,
        SUM(CASE WHEN ed.is_register_within_7d = 1 THEN 1 ELSE 0 END) AS success_invitation_count_7d,
        SUM(CASE WHEN ed.is_invitee_registered = 1 THEN 1 ELSE 0 END) AS success_invitation_count_total,

        -- =================== 被邀请人指标 ===================
        -- 总被邀请人数（去重）
        COUNT(DISTINCT ed.invitee_user_no) AS total_invitee_count,

        -- 注册人数（不同时间窗口）
        COUNT(DISTINCT CASE WHEN ed.is_register_same_day = 1 THEN ed.invitee_user_no END) AS registered_invitee_count_same_day,
        COUNT(DISTINCT CASE WHEN ed.is_register_within_7d = 1 THEN ed.invitee_user_no END) AS registered_invitee_count_7d,
        COUNT(DISTINCT CASE WHEN ed.is_invitee_registered = 1 THEN ed.invitee_user_no END) AS registered_invitee_count_total,

        -- 下单人数（不同时间窗口）
        COUNT(DISTINCT CASE WHEN ed.is_order_same_day = 1 THEN ed.invitee_user_no END) AS ordered_invitee_count_same_day,
        COUNT(DISTINCT CASE WHEN ed.is_order_within_7d = 1 THEN ed.invitee_user_no END) AS ordered_invitee_count_7d,
        COUNT(DISTINCT ed.invitee_order_no) AS ordered_invitee_count_total,

        -- =================== 订单指标 ===================
        -- 订单数
        COUNT(DISTINCT ed.invitee_order_no) AS invitee_order_count,

        -- 订单金额
        SUM(COALESCE(ed.invitee_order_amount, 0)) AS invitee_order_amount_total,

        -- 杯量
        SUM(COALESCE(ed.invitee_cup_count, 0)) AS invitee_cup_count_total,

        -- =================== 人均指标 ===================
        -- 人均邀请次数
        ROUND(COUNT(ed.invitation_id) * 1.0 / NULLIF(COUNT(DISTINCT ed.inviter_user_no), 0), 2) AS avg_invitation_per_inviter,

        -- 人均成功邀请次数（累计）
        ROUND(SUM(CASE WHEN ed.is_invitee_registered = 1 THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(DISTINCT ed.inviter_user_no), 0), 2) AS avg_success_invitation_per_inviter,

        -- 人均订单金额
        ROUND(SUM(COALESCE(ed.invitee_order_amount, 0)) * 1.0 / NULLIF(COUNT(DISTINCT CASE WHEN ed.is_invitee_registered = 1 THEN ed.invitee_user_no END), 0), 2) AS avg_order_amount_per_registered_invitee,

        -- 人均杯量
        ROUND(SUM(COALESCE(ed.invitee_cup_count, 0)) * 1.0 / NULLIF(COUNT(DISTINCT CASE WHEN ed.is_invitee_registered = 1 THEN ed.invitee_user_no END), 0), 2) AS avg_cup_per_registered_invitee

    FROM enriched_data ed
    GROUP BY ed.invite_date
),

-- =====================================================
-- CTE 8: 分享行为汇总（与邀请数据独立）
-- =====================================================
daily_share_stats AS (
    SELECT
        event_date AS stat_date,

        -- 曝光指标
        COUNT(DISTINCT CASE WHEN event_type = 'EXPOSURE' THEN user_no END) AS exposure_user_count,
        SUM(CASE WHEN event_type = 'EXPOSURE' THEN event_count ELSE 0 END) AS exposure_count,

        -- 点击指标
        COUNT(DISTINCT CASE WHEN event_type = 'CLICK' THEN user_no END) AS click_user_count,
        SUM(CASE WHEN event_type = 'CLICK' THEN event_count ELSE 0 END) AS click_count,

        -- 分享指标
        COUNT(DISTINCT CASE WHEN event_type = 'SHARE' THEN user_no END) AS share_user_count,
        SUM(CASE WHEN event_type = 'SHARE' THEN event_count ELSE 0 END) AS share_count

    FROM share_behavior_data
    GROUP BY event_date
),

-- =====================================================
-- CTE 9: 奖励发放汇总
-- =====================================================
daily_reward_stats AS (
    SELECT
        grant_date AS stat_date,

        -- 获得奖励的人数（按邀请人数分层）
        COUNT(DISTINCT CASE WHEN success_invite_count = 1 THEN inviter_user_no END) AS reward_user_1_invite,
        COUNT(DISTINCT CASE WHEN success_invite_count = 2 THEN inviter_user_no END) AS reward_user_2_invite,
        COUNT(DISTINCT CASE WHEN success_invite_count = 3 THEN inviter_user_no END) AS reward_user_3_invite,
        COUNT(DISTINCT CASE WHEN success_invite_count >= 4 THEN inviter_user_no END) AS reward_user_4plus_invite,

        -- 奖励发放总数
        SUM(reward_count) AS total_reward_granted

    FROM inviter_reward_data
    GROUP BY grant_date
)

-- =====================================================
-- 最终输出: 合并所有指标
-- =====================================================
SELECT
    ds.stat_date AS '日期',

    -- =================== L1层: 流量指标 ===================
    COALESCE(dss.exposure_user_count, 0) AS '曝光人数',
    COALESCE(dss.exposure_count, 0) AS '曝光次数',
    COALESCE(dss.click_user_count, 0) AS '点击人数',
    COALESCE(dss.click_count, 0) AS '点击次数',
    CONCAT(ROUND(COALESCE(dss.click_user_count, 0) * 100.0 / NULLIF(dss.exposure_user_count, 0), 2), '%') AS '点击率',

    -- =================== L2层: 分享指标 ===================
    COALESCE(dss.share_user_count, 0) AS '分享人数',
    COALESCE(dss.share_count, 0) AS '分享次数',
    CONCAT(ROUND(COALESCE(dss.share_user_count, 0) * 100.0 / NULLIF(dss.click_user_count, 0), 2), '%') AS '分享率',

    -- =================== L3层: 邀请指标 ===================
    ds.total_inviter_count AS '邀请人数',
    ds.new_inviter_count AS '新用户邀请人数',
    ds.old_inviter_count AS '老用户邀请人数',
    ds.total_invitation_count AS '邀请次数',
    ds.avg_invitation_per_inviter AS '人均邀请次数',

    -- 成功邀请人数（不同时间窗口）
    ds.success_inviter_count_daily AS '成功邀请人数_当日',
    ds.success_inviter_count_7d AS '成功邀请人数_7天',
    ds.success_inviter_count_total AS '成功邀请人数_累计',

    -- 成功率（基于7天窗口）
    CONCAT(ROUND(ds.success_inviter_count_7d * 100.0 / NULLIF(ds.total_inviter_count, 0), 2), '%') AS '邀请成功率_7天',

    -- =================== L4层: 注册转化指标 ===================
    ds.total_invitee_count AS '被邀请人数',
    ds.registered_invitee_count_same_day AS '注册人数_当日',
    ds.registered_invitee_count_7d AS '注册人数_7天',
    ds.registered_invitee_count_total AS '注册人数_累计',

    -- 注册转化率
    CONCAT(ROUND(ds.registered_invitee_count_7d * 100.0 / NULLIF(ds.total_invitee_count, 0), 2), '%') AS '注册转化率_7天',

    -- =================== L5层: 订单转化指标 ===================
    ds.ordered_invitee_count_same_day AS '下单人数_当日',
    ds.ordered_invitee_count_7d AS '下单人数_7天',
    ds.ordered_invitee_count_total AS '下单人数_累计',
    ds.invitee_order_count AS '订单数',

    -- 下单转化率
    CONCAT(ROUND(ds.ordered_invitee_count_7d * 100.0 / NULLIF(ds.registered_invitee_count_7d, 0), 2), '%') AS '下单转化率_7天',

    -- =================== 订单价值指标 ===================
    ds.invitee_order_amount_total AS '订单总金额',
    ds.invitee_cup_count_total AS '总杯量',
    ds.avg_order_amount_per_registered_invitee AS '人均订单金额',
    ds.avg_cup_per_registered_invitee AS '人均杯量',

    -- =================== 奖励发放指标 ===================
    COALESCE(drs.reward_user_1_invite, 0) AS '获奖人数_邀1人',
    COALESCE(drs.reward_user_2_invite, 0) AS '获奖人数_邀2人',
    COALESCE(drs.reward_user_3_invite, 0) AS '获奖人数_邀3人',
    COALESCE(drs.reward_user_4plus_invite, 0) AS '获奖人数_邀4人以上',
    COALESCE(drs.total_reward_granted, 0) AS '奖励发放总数',

    -- =================== 核心ROI指标 ===================
    -- 拉新贡献率（基于7天窗口）
    CONCAT(ROUND(ds.registered_invitee_count_7d * 100.0 /
        NULLIF((SELECT SUM(daily_new_user_count)
                FROM ods_luckyus_sales_user.daily_user_stats
                WHERE stat_date = ds.stat_date), 0), 2), '%') AS '拉新贡献率_7天',

    -- 成本效率（券成本/注册人数）
    ROUND(COALESCE(drs.total_reward_granted, 0) * 1.0 / NULLIF(ds.registered_invitee_count_7d, 0), 2) AS '人均获客成本_券数'

FROM daily_stats ds
LEFT JOIN daily_share_stats dss
    ON ds.stat_date = dss.stat_date
LEFT JOIN daily_reward_stats drs
    ON ds.stat_date = drs.stat_date
ORDER BY ds.stat_date DESC;


-- =====================================================
-- 补充查询: 人均邀请人数分布（用于优化奖励规则）
-- =====================================================

-- 查看邀请人数分布（与CSV数据对比）
SELECT
    success_invite_count AS '成功邀请人数',
    COUNT(DISTINCT inviter_user_no) AS '邀请人数量',
    CONCAT(ROUND(COUNT(DISTINCT inviter_user_no) * 100.0 /
        (SELECT COUNT(DISTINCT inviter_user_no)
         FROM base_invitation_data
         WHERE is_success_invite = 1), 2), '%') AS '占比',
    SUM(COUNT(DISTINCT inviter_user_no)) OVER (ORDER BY success_invite_count) AS '累计人数',
    CONCAT(ROUND(SUM(COUNT(DISTINCT inviter_user_no)) OVER (ORDER BY success_invite_count) * 100.0 /
        (SELECT COUNT(DISTINCT inviter_user_no)
         FROM base_invitation_data
         WHERE is_success_invite = 1), 2), '%') AS '累计占比'
FROM (
    SELECT
        inviter_user_no,
        SUM(is_success_invite) AS success_invite_count
    FROM enriched_data
    GROUP BY inviter_user_no
) t
GROUP BY success_invite_count
ORDER BY success_invite_count;
