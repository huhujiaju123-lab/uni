-- menu转化率小时报表 - 按小时统计，限定5个核心页面
-- 日期范围：最近30天

-- 分小时、页面、事件统计
SELECT
      DATE(CONVERT_TZ(_flush_time_form, @@time_zone, 'America/New_York')) AS dt,
      COUNT(CASE WHEN event = '$page.menu$model.cmdty$content.0$action.bw' THEN 1 END) AS menu_exposure_count,
      COUNT(DISTINCT CASE WHEN event = '$page.menu$model.cmdty$content.0$action.bw' THEN p_login_id END) AS menu_exposure_users,
      COUNT(CASE WHEN event = '$page.menu$model.cmdty$content.0$action.ck' THEN 1 END) AS menu_click_count,
      COUNT(DISTINCT CASE WHEN event = '$page.menu$model.cmdty$content.0$action.ck' THEN p_login_id END) AS menu_click_users,
      -- 商品详情页面商品曝光和点击（事件级别）
      COUNT(CASE WHEN event = '$page.productdetail$model.0$content.0$action.start' THEN 1 END) AS productdetail_click_count,
      COUNT(DISTINCT CASE WHEN event = '$page.productdetail$model.0$content.0$action.start' THEN p_login_id END) AS productdetail_click_users,
      -- 订单页面曝光和点击（事件级别）
      COUNT(CASE WHEN event = '$page.confirmorder$model.pay$content.0$action.ck' THEN 1 END) AS orderdetail_click_count,
      COUNT(DISTINCT CASE WHEN event = '$page.confirmorder$model.pay$content.0$action.ck' THEN p_login_id END) AS orderdetail_click_users,
      -- 总用户数
      COUNT(DISTINCT p_login_id) AS total_users,

      -- 当天下单的用户数
      COUNT(DISTINCT CASE WHEN vo_today.user_no IS NOT NULL THEN p_login_id END) AS same_day_ordered_users,

      -- 【新客】当天首次下单的用户数
      COUNT(DISTINCT CASE
          WHEN vo_today.user_no IS NOT NULL
          AND vo.first_order_date = DATE(sub._flush_time_form)
          THEN p_login_id
      END) AS new_customer_users,

      -- 【老客】当天下单但非首单的用户数
      COUNT(DISTINCT CASE
          WHEN vo_today.user_no IS NOT NULL
          AND vo.first_order_date < DATE(sub._flush_time_form)
          THEN p_login_id
      END) AS old_customer_users,

      -- 历史下过单但当天未下单的用户数
      COUNT(DISTINCT CASE WHEN vo.user_no IS NOT NULL AND vo_today.user_no IS NULL THEN p_login_id END) AS historical_ordered_users,

      -- 从未下过单的用户数
      COUNT(DISTINCT CASE WHEN vo.user_no IS NULL THEN p_login_id END) AS never_ordered_users,

      -- 当天下单用户占比
      ROUND(COUNT(DISTINCT CASE WHEN vo_today.user_no IS NOT NULL THEN p_login_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT p_login_id), 0), 2) AS same_day_order_rate,

      -- 【新客占比】新客在当天下单用户中的占比
      ROUND(COUNT(DISTINCT CASE
          WHEN vo_today.user_no IS NOT NULL
          AND vo.first_order_date = DATE(sub._flush_time_form)
          THEN p_login_id
      END) * 100.0 / NULLIF(COUNT(DISTINCT CASE
          WHEN vo_today.user_no IS NOT NULL
          THEN p_login_id
      END), 0), 2) AS new_customer_rate,

      -- 【老客占比】老客在当天下单用户中的占比
      ROUND(COUNT(DISTINCT CASE
          WHEN vo_today.user_no IS NOT NULL
          AND vo.first_order_date < DATE(sub._flush_time_form)
          THEN p_login_id
      END) * 100.0 / NULLIF(COUNT(DISTINCT CASE
          WHEN vo_today.user_no IS NOT NULL
          THEN p_login_id
      END), 0), 2) AS old_customer_rate,

      -- 历史下单但当天未下单用户占比
      ROUND(COUNT(DISTINCT CASE WHEN vo.user_no IS NOT NULL AND vo_today.user_no IS NULL THEN p_login_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT p_login_id), 0), 2) AS historical_order_rate,

      -- 从未下单用户占比
      ROUND(COUNT(DISTINCT CASE WHEN vo.user_no IS NULL THEN p_login_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT p_login_id), 0), 2) AS never_order_rate,

      -- 当天注册的用户数（新客）
      COUNT(DISTINCT CASE WHEN DATE(u.reg_date) = DATE(sub._flush_time_form) THEN p_login_id END) AS same_day_registered_users,

      -- 之前注册的用户数（老客）
      COUNT(DISTINCT CASE WHEN DATE(u.reg_date) < DATE(sub._flush_time_form) THEN p_login_id END) AS historical_registered_users,

      -- 当天注册用户占比
      ROUND(COUNT(DISTINCT CASE WHEN DATE(u.reg_date) = DATE(sub._flush_time_form) THEN p_login_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT p_login_id), 0), 2) AS same_day_reg_rate,

      -- 之前注册用户占比
      ROUND(COUNT(DISTINCT CASE WHEN DATE(u.reg_date) < DATE(sub._flush_time_form) THEN p_login_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT p_login_id), 0), 2) AS historical_reg_rate,

      -- 【新增】新注册用户中访问Menu的用户数
      COUNT(DISTINCT CASE
          WHEN DATE(u.reg_date) = DATE(sub._flush_time_form)
          AND event = '$page.menu$model.cmdty$content.0$action.bw'
          THEN p_login_id
      END) AS new_registered_menu_exposure_users,

      -- 【新增】新注册用户访问Menu的比例
      ROUND(COUNT(DISTINCT CASE
          WHEN DATE(u.reg_date) = DATE(sub._flush_time_form)
          AND event = '$page.menu$model.cmdty$content.0$action.bw'
          THEN p_login_id
      END) * 100.0 /
          NULLIF(COUNT(DISTINCT CASE WHEN DATE(u.reg_date) = DATE(sub._flush_time_form) THEN p_login_id END), 0), 2) AS new_registered_menu_exposure_rate

FROM
(
    SELECT
    DATE_FORMAT(CONVERT_TZ(server_time_form, @@time_zone, 'America/New_York'), '%Y-%m-%d') AS dt,
    -- 优先使用 properties，为空时回退到表字段
    COALESCE(CAST(properties['platform'] AS VARCHAR), CAST(platform AS VARCHAR)) AS platform,
    -- 在 platform=3 时区分门店扫描页和其他渠道
    CASE
            WHEN (COALESCE(CAST(properties['platform'] AS VARCHAR), CAST(platform AS VARCHAR)) = '3'
        AND CAST(properties['$url'] AS VARCHAR) LIKE '%in.luckincoffee.us/shop/scancode%')
        OR event = '$page.scan$model.0$content.0$action.bw'
            THEN 'store_scan'
            ELSE COALESCE(CAST(properties['channel'] AS VARCHAR), channel)
        END AS channel,
    COALESCE(CAST(properties['login_id'] AS VARCHAR), login_id) AS p_login_id,
    CAST(properties['$app_version'] AS VARCHAR) AS app_version,
    -- 提取 $lib 字段并根据其值判断页面类型
    CASE
            WHEN CAST(properties['$lib'] AS VARCHAR) = 'js' THEN 'H5'
            ELSE 'App'
        END AS page_type,
    track_id,
    event,
    CONVERT_TZ(server_time_form, @@time_zone, 'America/New_York') AS _flush_time_form
FROM ods_luckyus_track.v_hmonitor_track_event_rt_new
WHERE
        INSTR(COALESCE(tenant, 'LKUS'), 'IQ') = 0
    AND DATE(CONVERT_TZ(dt, @@time_zone, 'America/New_York')) >= DATE_SUB(CURDATE(), 30)
    AND DATE(CONVERT_TZ(dt, @@time_zone, 'America/New_York')) <= CURDATE()
) sub
LEFT JOIN (
    -- 子查询1：获取用户首次下单信息（全历史）
    SELECT
        user_no,
        MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_order_date
    FROM ods_luckyus_sales_order.v_order
    WHERE status = 90
        AND INSTR(tenant, 'IQ') = 0
    GROUP BY user_no
) vo ON sub.p_login_id = vo.user_no
LEFT JOIN (
    -- 子查询2：获取用户每天的下单情况（仅查询日期范围内）
    SELECT
        user_no,
        DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) AS order_date
    FROM ods_luckyus_sales_order.v_order
    WHERE status = 90
        AND INSTR(tenant, 'IQ') = 0
        AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= DATE_SUB(CURDATE(), 30)
        AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) <= CURDATE()
    GROUP BY user_no, DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))
) vo_today ON sub.p_login_id = vo_today.user_no
    AND DATE(sub._flush_time_form) = vo_today.order_date
LEFT JOIN (
    -- 子查询3：获取用户注册信息
    SELECT
        user_no,
        DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) AS reg_date
    FROM ods_luckyus_sales_crm.t_user
    WHERE INSTR(COALESCE(tenant, 'LKUS'), 'IQ') = 0
) u ON sub.p_login_id = u.user_no


GROUP BY 
    DATE(CONVERT_TZ(_flush_time_form, @@time_zone, 'America/New_York'))


ORDER BY
    dt DESC

LIMIT 20000