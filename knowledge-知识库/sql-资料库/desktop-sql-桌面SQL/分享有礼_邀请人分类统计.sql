-- =====================================================
-- 分享有礼 - 邀请人按成功邀请人数分类统计
-- 活动编号: LKUSNR118429103010545664
-- 功能: 统计每个邀请人的成功邀请人数，并按邀请人数进行分类
-- =====================================================

SET @cal_begin_date = DATE_SUB(CURDATE(), INTERVAL 30 DAY);
SET @cal_end_date = DATE_SUB(CURDATE(), INTERVAL 1 DAY);

-- 邀请人成功邀请统计及分类
WITH inviter_stats AS (
    -- 统计每个邀请人的成功邀请人数
    SELECT
        inviter_user_no,
        COUNT(DISTINCT CASE WHEN invitation_success = 1 THEN invitee_user_no END) AS success_invite_count,
        COUNT(DISTINCT invitee_user_no) AS total_invite_count,
        MIN(FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d')) AS first_invite_date,
        MAX(FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d')) AS last_invite_date
    FROM ods_luckyus_sales_marketing.t_user_invitation_info
    WHERE
        activity_no = 'LKUSNR118429103010545664'
        AND FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') >= @cal_begin_date
        AND FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') <= @cal_end_date
    GROUP BY inviter_user_no
),

inviter_classified AS (
    -- 按成功邀请人数分类
    SELECT
        inviter_user_no,
        success_invite_count,
        total_invite_count,
        first_invite_date,
        last_invite_date,
        CASE
            WHEN success_invite_count = 0 THEN '0_no_success'
            WHEN success_invite_count = 1 THEN '1_one_success'
            WHEN success_invite_count = 2 THEN '2_two_success'
            WHEN success_invite_count = 3 THEN '3_three_success'
            WHEN success_invite_count BETWEEN 4 AND 5 THEN '4_four_to_five'
            WHEN success_invite_count BETWEEN 6 AND 10 THEN '5_six_to_ten'
            ELSE '6_more_than_ten'
        END AS invite_category
    FROM inviter_stats
)

-- 汇总统计结果
SELECT
    invite_category,
    COUNT(DISTINCT inviter_user_no) AS inviter_count,
    SUM(success_invite_count) AS total_success_invites,
    SUM(total_invite_count) AS total_invites,
    ROUND(AVG(success_invite_count), 2) AS avg_success_per_inviter,
    ROUND(SUM(success_invite_count) * 100.0 / NULLIF(SUM(total_invite_count), 0), 2) AS success_rate_pct
FROM inviter_classified
GROUP BY invite_category
ORDER BY invite_category
LIMIT 50000;


-- =====================================================
-- 明细查询: 每个邀请人的详细统计
-- =====================================================

SET @cal_begin_date = DATE_SUB(CURDATE(), INTERVAL 30 DAY);
SET @cal_end_date = DATE_SUB(CURDATE(), INTERVAL 1 DAY);

WITH inviter_detail AS (
    SELECT
        inviter_user_no,
        COUNT(DISTINCT CASE WHEN invitation_success = 1 THEN invitee_user_no END) AS success_invite_count,
        COUNT(DISTINCT invitee_user_no) AS total_invite_count,
        MIN(FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d')) AS first_invite_date,
        MAX(FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d')) AS last_invite_date
    FROM ods_luckyus_sales_marketing.t_user_invitation_info
    WHERE
        activity_no = 'LKUSNR118429103010545664'
        AND FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') >= @cal_begin_date
        AND FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') <= @cal_end_date
    GROUP BY inviter_user_no
)

SELECT
    inviter_user_no,
    success_invite_count,
    total_invite_count,
    ROUND(success_invite_count * 100.0 / NULLIF(total_invite_count, 0), 2) AS success_rate_pct,
    first_invite_date,
    last_invite_date,
    CASE
        WHEN success_invite_count = 0 THEN '0_no_success'
        WHEN success_invite_count = 1 THEN '1_one_success'
        WHEN success_invite_count = 2 THEN '2_two_success'
        WHEN success_invite_count = 3 THEN '3_three_success'
        WHEN success_invite_count BETWEEN 4 AND 5 THEN '4_four_to_five'
        WHEN success_invite_count BETWEEN 6 AND 10 THEN '5_six_to_ten'
        ELSE '6_more_than_ten'
    END AS invite_category
FROM inviter_detail
ORDER BY success_invite_count DESC, total_invite_count DESC
LIMIT 50000
