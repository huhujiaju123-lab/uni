-- 分享有礼活动：分享人贡献分析（增强版）
-- 统计维度：
-- 1. 分享人：当日总数、当日成功、7天内成功、累计成功
-- 2. 被分享人：当日注册、7天内注册、累计注册、当日下单、7天内下单、累计下单
-- 特点：所有被分享人指标都基于"当天的分享人"贡献，准确反映当日分享活动效果

-- 参数设置：灵活配置统计时间范围
-- 默认统计最近30天的数据
SET @cal_begin_date = DATE_SUB(DATE(NOW()), INTERVAL 100 DAY);
SET @cal_end_date = DATE_SUB(DATE(NOW()), INTERVAL 0 DAY);

WITH
    -- 基础数据准备
    base_data AS (
        SELECT
            -- 被分享人注册日期（核心日期维度）
            FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') AS register_dt,
            inviter_user_no,
            invitee_user_no,
            invitation_success,
            create_time,
            modify_time
        FROM ods_luckyus_sales_marketing.t_user_invitation_info
        WHERE
            FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') >= @cal_begin_date
            AND FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') <= @cal_end_date
            AND activity_no LIKE '%LKUS%'
    ),

    -- 获取每个分享人首次带来注册的日期（用于区分新老分享人）
    inviter_history AS (
        SELECT
            inviter_user_no,
            MIN(FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d')) AS first_register_dt
        FROM ods_luckyus_sales_marketing.t_user_invitation_info
        WHERE activity_no LIKE '%LKUS%'
        GROUP BY inviter_user_no
    ),

    -- 获取被分享人的订单杯量数据
    invitee_orders AS (
        SELECT
            o.user_no,
            DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) AS order_date,
            o.id AS order_id,
            COUNT(*) AS item_cnt
        FROM ods_luckyus_sales_order.v_order o
        LEFT JOIN ods_luckyus_sales_order.t_order_item i ON o.id = i.order_id
        WHERE o.status = 90
            AND INSTR(o.tenant, 'IQ') = 0
            AND i.one_category_name = 'Drink'
            AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) >= @cal_begin_date
        GROUP BY o.user_no, DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')), o.id
    ),

    -- 处理分享数据，计算时间差
    enriched_data AS (
        SELECT
            b.register_dt,
            b.inviter_user_no,
            b.invitee_user_no,
            b.invitation_success,
            -- 被分享人的注册日期（每条记录的create_time就是该被分享人通过该分享链接的注册时间）
            FROM_UNIXTIME(UNIX_TIMESTAMP(b.create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') AS invitee_register_dt,
            -- 被分享人的下单日期
            CASE
                WHEN b.invitation_success = 1
                THEN FROM_UNIXTIME(UNIX_TIMESTAMP(b.modify_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d')
                ELSE NULL
            END AS invitee_order_dt,
            -- 计算下单时间差（被分享人下单时间 - 注册时间）
            CASE
                WHEN b.invitation_success = 1
                THEN DATEDIFF(
                    FROM_UNIXTIME(UNIX_TIMESTAMP(b.modify_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d'),
                    b.register_dt
                )
                ELSE NULL
            END AS order_days_from_register,
            -- 标记新老分享人（基于该分享人是否首次带来注册）
            CASE
                WHEN h.first_register_dt = b.register_dt THEN 'new'
                ELSE 'old'
            END AS inviter_type,
            -- 关联订单杯量
            COALESCE(ord.item_cnt, 0) AS order_item_cnt
        FROM base_data b
        LEFT JOIN inviter_history h ON b.inviter_user_no = h.inviter_user_no
        LEFT JOIN invitee_orders ord ON b.invitee_user_no = ord.user_no
            AND CASE
                WHEN b.invitation_success = 1
                THEN FROM_UNIXTIME(UNIX_TIMESTAMP(b.modify_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d')
                ELSE NULL
            END = ord.order_date
    ),

    -- 按日期统计分享人和被分享人指标
    daily_stats AS (
        SELECT
            register_dt,

            -- ========== 分享人指标 ==========
            -- 当日带来注册的分享人总数
            COUNT(DISTINCT inviter_user_no) AS daily_inviter_cnt,

            -- 当日新分享人（首次带来注册）
            COUNT(DISTINCT CASE
                WHEN inviter_type = 'new'
                THEN inviter_user_no
            END) AS daily_new_inviter_cnt,

            -- 当日老分享人（非首次带来注册）
            COUNT(DISTINCT CASE
                WHEN inviter_type = 'old'
                THEN inviter_user_no
            END) AS daily_old_inviter_cnt,

            -- 当日成功的分享人（被分享人当天注册且当天下单）
            COUNT(DISTINCT CASE
                WHEN order_days_from_register = 0
                THEN inviter_user_no
            END) AS daily_success_inviter_cnt,
            -- 新分享人当日成功
            COUNT(DISTINCT CASE
                WHEN order_days_from_register = 0 AND inviter_type = 'new'
                THEN inviter_user_no
            END) AS daily_new_success_inviter_cnt,
            -- 老分享人当日成功
            COUNT(DISTINCT CASE
                WHEN order_days_from_register = 0 AND inviter_type = 'old'
                THEN inviter_user_no
            END) AS daily_old_success_inviter_cnt,

            -- 7天内成功的分享人（被分享人当天注册后7天内下单）
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0 AND order_days_from_register <= 6
                THEN inviter_user_no
            END) AS seven_day_success_inviter_cnt,
            -- 新分享人7天内成功
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0 AND order_days_from_register <= 6 AND inviter_type = 'new'
                THEN inviter_user_no
            END) AS seven_day_new_success_inviter_cnt,
            -- 老分享人7天内成功
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0 AND order_days_from_register <= 6 AND inviter_type = 'old'
                THEN inviter_user_no
            END) AS seven_day_old_success_inviter_cnt,

            -- 累计成功的分享人（被分享人当天注册后最终下单）
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0
                THEN inviter_user_no
            END) AS total_success_inviter_cnt,
            -- 新分享人累计成功
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0 AND inviter_type = 'new'
                THEN inviter_user_no
            END) AS total_new_success_inviter_cnt,
            -- 老分享人累计成功
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0 AND inviter_type = 'old'
                THEN inviter_user_no
            END) AS total_old_success_inviter_cnt,

            -- ========== 被分享人注册指标 ==========
            -- 当日注册的被分享人（总体）
            COUNT(DISTINCT invitee_user_no) AS daily_register_invitee_cnt,
            -- 新分享人贡献
            COUNT(DISTINCT CASE
                WHEN inviter_type = 'new'
                THEN invitee_user_no
            END) AS daily_register_invitee_from_new_cnt,
            -- 老分享人贡献
            COUNT(DISTINCT CASE
                WHEN inviter_type = 'old'
                THEN invitee_user_no
            END) AS daily_register_invitee_from_old_cnt,

            -- 7天内注册的被分享人（与当日注册相同，因为按注册日期分组）
            COUNT(DISTINCT invitee_user_no) AS seven_day_register_invitee_cnt,
            -- 新分享人贡献
            COUNT(DISTINCT CASE
                WHEN inviter_type = 'new'
                THEN invitee_user_no
            END) AS seven_day_register_invitee_from_new_cnt,
            -- 老分享人贡献
            COUNT(DISTINCT CASE
                WHEN inviter_type = 'old'
                THEN invitee_user_no
            END) AS seven_day_register_invitee_from_old_cnt,

            -- 累计注册的被分享人（与当日注册相同，因为按注册日期分组）
            COUNT(DISTINCT invitee_user_no) AS total_register_invitee_cnt,
            -- 新分享人贡献
            COUNT(DISTINCT CASE
                WHEN inviter_type = 'new'
                THEN invitee_user_no
            END) AS total_register_invitee_from_new_cnt,
            -- 老分享人贡献
            COUNT(DISTINCT CASE
                WHEN inviter_type = 'old'
                THEN invitee_user_no
            END) AS total_register_invitee_from_old_cnt,

            -- ========== 被分享人下单指标 ==========
            -- 当日下单的被分享人（总体）
            COUNT(DISTINCT CASE
                WHEN order_days_from_register = 0
                THEN invitee_user_no
            END) AS daily_order_invitee_cnt,
            -- 新分享人贡献
            COUNT(DISTINCT CASE
                WHEN order_days_from_register = 0 AND inviter_type = 'new'
                THEN invitee_user_no
            END) AS daily_order_invitee_from_new_cnt,
            -- 老分享人贡献
            COUNT(DISTINCT CASE
                WHEN order_days_from_register = 0 AND inviter_type = 'old'
                THEN invitee_user_no
            END) AS daily_order_invitee_from_old_cnt,

            -- 7天内下单的被分享人（总体）
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0 AND order_days_from_register <= 6
                THEN invitee_user_no
            END) AS seven_day_order_invitee_cnt,
            -- 新分享人贡献
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0 AND order_days_from_register <= 6 AND inviter_type = 'new'
                THEN invitee_user_no
            END) AS seven_day_order_invitee_from_new_cnt,
            -- 老分享人贡献
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0 AND order_days_from_register <= 6 AND inviter_type = 'old'
                THEN invitee_user_no
            END) AS seven_day_order_invitee_from_old_cnt,

            -- 累计下单的被分享人（总体）
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0
                THEN invitee_user_no
            END) AS total_order_invitee_cnt,
            -- 新分享人贡献
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0 AND inviter_type = 'new'
                THEN invitee_user_no
            END) AS total_order_invitee_from_new_cnt,
            -- 老分享人贡献
            COUNT(DISTINCT CASE
                WHEN order_days_from_register >= 0 AND inviter_type = 'old'
                THEN invitee_user_no
            END) AS total_order_invitee_from_old_cnt,

            -- ========== 被分享人下单杯量指标 ==========
            -- 当日下单杯量（总体）
            SUM(CASE
                WHEN order_days_from_register = 0
                THEN order_item_cnt
                ELSE 0
            END) AS daily_order_item_cnt,
            -- 新分享人贡献
            SUM(CASE
                WHEN order_days_from_register = 0 AND inviter_type = 'new'
                THEN order_item_cnt
                ELSE 0
            END) AS daily_order_item_from_new_cnt,
            -- 老分享人贡献
            SUM(CASE
                WHEN order_days_from_register = 0 AND inviter_type = 'old'
                THEN order_item_cnt
                ELSE 0
            END) AS daily_order_item_from_old_cnt,

            -- 7天内下单杯量（总体）
            SUM(CASE
                WHEN order_days_from_register >= 0 AND order_days_from_register <= 6
                THEN order_item_cnt
                ELSE 0
            END) AS seven_day_order_item_cnt,
            -- 新分享人贡献
            SUM(CASE
                WHEN order_days_from_register >= 0 AND order_days_from_register <= 6 AND inviter_type = 'new'
                THEN order_item_cnt
                ELSE 0
            END) AS seven_day_order_item_from_new_cnt,
            -- 老分享人贡献
            SUM(CASE
                WHEN order_days_from_register >= 0 AND order_days_from_register <= 6 AND inviter_type = 'old'
                THEN order_item_cnt
                ELSE 0
            END) AS seven_day_order_item_from_old_cnt,

            -- 累计下单杯量（总体）
            SUM(CASE
                WHEN order_days_from_register >= 0
                THEN order_item_cnt
                ELSE 0
            END) AS total_order_item_cnt,
            -- 新分享人贡献
            SUM(CASE
                WHEN order_days_from_register >= 0 AND inviter_type = 'new'
                THEN order_item_cnt
                ELSE 0
            END) AS total_order_item_from_new_cnt,
            -- 老分享人贡献
            SUM(CASE
                WHEN order_days_from_register >= 0 AND inviter_type = 'old'
                THEN order_item_cnt
                ELSE 0
            END) AS total_order_item_from_old_cnt,

            -- ========== 分享次数统计 ==========
            COUNT(*) AS total_share_attempts,
            COUNT(CASE WHEN inviter_type = 'new' THEN 1 END) AS new_inviter_share_attempts,
            COUNT(CASE WHEN inviter_type = 'old' THEN 1 END) AS old_inviter_share_attempts,
            COUNT(DISTINCT CONCAT(inviter_user_no, '_', invitee_user_no)) AS unique_share_pairs,
            COUNT(DISTINCT CASE WHEN inviter_type = 'new' THEN CONCAT(inviter_user_no, '_', invitee_user_no) END) AS new_unique_share_pairs,
            COUNT(DISTINCT CASE WHEN inviter_type = 'old' THEN CONCAT(inviter_user_no, '_', invitee_user_no) END) AS old_unique_share_pairs

        FROM enriched_data
        GROUP BY register_dt
    )

-- 最终输出结果
SELECT
    register_dt AS 注册日期,

    -- 分享人指标
    daily_inviter_cnt AS 当日带来注册的分享人总数,
    daily_new_inviter_cnt AS 当日新分享人数量,
    daily_old_inviter_cnt AS 当日老分享人数量,

    -- 成功分享人指标（总体）
    daily_success_inviter_cnt AS 当日成功分享的分享人,
    seven_day_success_inviter_cnt AS 七天内成功分享的分享人,
    total_success_inviter_cnt AS 累计成功分享的分享人,

    -- 成功分享人指标（新分享人）
    daily_new_success_inviter_cnt AS 当日新分享人成功数,
    seven_day_new_success_inviter_cnt AS 七天内新分享人成功数,
    total_new_success_inviter_cnt AS 累计新分享人成功数,

    -- 成功分享人指标（老分享人）
    daily_old_success_inviter_cnt AS 当日老分享人成功数,
    seven_day_old_success_inviter_cnt AS 七天内老分享人成功数,
    total_old_success_inviter_cnt AS 累计老分享人成功数,

    -- 被分享人注册指标（总体）
    daily_register_invitee_cnt AS 当日注册的被分享人,
    seven_day_register_invitee_cnt AS 七天内注册的被分享人,
    total_register_invitee_cnt AS 累计注册的被分享人,

    -- 被分享人注册指标（新分享人贡献）
    daily_register_invitee_from_new_cnt AS 新分享人贡献当日注册,
    seven_day_register_invitee_from_new_cnt AS 新分享人贡献七天注册,
    total_register_invitee_from_new_cnt AS 新分享人贡献累计注册,

    -- 被分享人注册指标（老分享人贡献）
    daily_register_invitee_from_old_cnt AS 老分享人贡献当日注册,
    seven_day_register_invitee_from_old_cnt AS 老分享人贡献七天注册,
    total_register_invitee_from_old_cnt AS 老分享人贡献累计注册,

    -- 被分享人下单指标（总体）
    daily_order_invitee_cnt AS 当日下单的被分享人,
    seven_day_order_invitee_cnt AS 七天内下单的被分享人,
    total_order_invitee_cnt AS 累计下单的被分享人,

    -- 被分享人下单指标（新分享人贡献）
    daily_order_invitee_from_new_cnt AS 新分享人贡献当日下单,
    seven_day_order_invitee_from_new_cnt AS 新分享人贡献七天下单,
    total_order_invitee_from_new_cnt AS 新分享人贡献累计下单,

    -- 被分享人下单指标（老分享人贡献）
    daily_order_invitee_from_old_cnt AS 老分享人贡献当日下单,
    seven_day_order_invitee_from_old_cnt AS 老分享人贡献七天下单,
    total_order_invitee_from_old_cnt AS 老分享人贡献累计下单,

    -- 被分享人下单杯量指标（总体）
    daily_order_item_cnt AS 当日下单杯量,
    seven_day_order_item_cnt AS 七天内下单杯量,
    total_order_item_cnt AS 累计下单杯量,

    -- 被分享人下单杯量指标（新分享人贡献）
    daily_order_item_from_new_cnt AS 新分享人贡献当日杯量,
    seven_day_order_item_from_new_cnt AS 新分享人贡献七天杯量,
    total_order_item_from_new_cnt AS 新分享人贡献累计杯量,

    -- 被分享人下单杯量指标（老分享人贡献）
    daily_order_item_from_old_cnt AS 老分享人贡献当日杯量,
    seven_day_order_item_from_old_cnt AS 老分享人贡献七天杯量,
    total_order_item_from_old_cnt AS 老分享人贡献累计杯量,

    -- 转化率指标（总体）
    ROUND(daily_success_inviter_cnt * 100.0 / NULLIF(daily_inviter_cnt, 0), 2) AS 当日分享人成功率,
    ROUND(seven_day_success_inviter_cnt * 100.0 / NULLIF(daily_inviter_cnt, 0), 2) AS 七天分享人成功率,
    ROUND(total_success_inviter_cnt * 100.0 / NULLIF(daily_inviter_cnt, 0), 2) AS 累计分享人成功率,

    -- 转化率指标（新分享人）
    ROUND(daily_new_success_inviter_cnt * 100.0 / NULLIF(daily_new_inviter_cnt, 0), 2) AS 新分享人当日成功率,
    ROUND(seven_day_new_success_inviter_cnt * 100.0 / NULLIF(daily_new_inviter_cnt, 0), 2) AS 新分享人七天成功率,
    ROUND(total_new_success_inviter_cnt * 100.0 / NULLIF(daily_new_inviter_cnt, 0), 2) AS 新分享人累计成功率,

    -- 转化率指标（老分享人）
    ROUND(daily_old_success_inviter_cnt * 100.0 / NULLIF(daily_old_inviter_cnt, 0), 2) AS 老分享人当日成功率,
    ROUND(seven_day_old_success_inviter_cnt * 100.0 / NULLIF(daily_old_inviter_cnt, 0), 2) AS 老分享人七天成功率,
    ROUND(total_old_success_inviter_cnt * 100.0 / NULLIF(daily_old_inviter_cnt, 0), 2) AS 老分享人累计成功率,

    -- 被分享人转化率（总体）
    ROUND(daily_order_invitee_cnt * 100.0 / NULLIF(daily_register_invitee_cnt, 0), 2) AS 当日转化率,
    ROUND(seven_day_order_invitee_cnt * 100.0 / NULLIF(seven_day_register_invitee_cnt, 0), 2) AS 七天转化率,
    ROUND(total_order_invitee_cnt * 100.0 / NULLIF(total_register_invitee_cnt, 0), 2) AS 累计转化率,

    -- 被分享人转化率（新分享人贡献）
    ROUND(daily_order_invitee_from_new_cnt * 100.0 / NULLIF(daily_register_invitee_from_new_cnt, 0), 2) AS 新分享人贡献当日转化率,
    ROUND(seven_day_order_invitee_from_new_cnt * 100.0 / NULLIF(seven_day_register_invitee_from_new_cnt, 0), 2) AS 新分享人贡献七天转化率,
    ROUND(total_order_invitee_from_new_cnt * 100.0 / NULLIF(total_register_invitee_from_new_cnt, 0), 2) AS 新分享人贡献累计转化率,

    -- 被分享人转化率（老分享人贡献）
    ROUND(daily_order_invitee_from_old_cnt * 100.0 / NULLIF(daily_register_invitee_from_old_cnt, 0), 2) AS 老分享人贡献当日转化率,
    ROUND(seven_day_order_invitee_from_old_cnt * 100.0 / NULLIF(seven_day_register_invitee_from_old_cnt, 0), 2) AS 老分享人贡献七天转化率,
    ROUND(total_order_invitee_from_old_cnt * 100.0 / NULLIF(total_register_invitee_from_old_cnt, 0), 2) AS 老分享人贡献累计转化率,

    -- 额外指标（总体）
    total_share_attempts AS 当日分享次数,
    unique_share_pairs AS 当日分享组合数,
    ROUND(total_share_attempts * 1.0 / NULLIF(daily_inviter_cnt, 0), 2) AS 人均分享次数,

    -- 额外指标（新分享人）
    new_inviter_share_attempts AS 新分享人分享次数,
    new_unique_share_pairs AS 新分享人分享组合数,
    ROUND(new_inviter_share_attempts * 1.0 / NULLIF(daily_new_inviter_cnt, 0), 2) AS 新分享人人均分享次数,

    -- 额外指标（老分享人）
    old_inviter_share_attempts AS 老分享人分享次数,
    old_unique_share_pairs AS 老分享人分享组合数,
    ROUND(old_inviter_share_attempts * 1.0 / NULLIF(daily_old_inviter_cnt, 0), 2) AS 老分享人人均分享次数,

    -- 新老分享人占比
    ROUND(daily_new_inviter_cnt * 100.0 / NULLIF(daily_inviter_cnt, 0), 2) AS 新分享人占比,
    ROUND(daily_old_inviter_cnt * 100.0 / NULLIF(daily_inviter_cnt, 0), 2) AS 老分享人占比

FROM daily_stats
ORDER BY register_dt
LIMIT 100000;