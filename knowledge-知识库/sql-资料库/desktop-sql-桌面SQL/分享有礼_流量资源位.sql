-- 分享有礼活动：流量资源位分析
-- 统计资源位（Icon、Banner、弹窗）的曝光UV和点击UV

-- 参数设置：灵活配置统计时间范围
SET @cal_begin_date = DATE_SUB(DATE(NOW()), INTERVAL 10 DAY);
SET @cal_end_date = DATE_SUB(DATE(NOW()), INTERVAL 0 DAY);

SELECT
    DATE_FORMAT(CONVERT_TZ(server_time_form, @@time_zone, 'America/New_York'), '%Y-%m-%d') AS dt,
    COUNT(DISTINCT p_login_id) AS dau,
    -- Icon资源位（位置2）
    COUNT(DISTINCT CASE
        WHEN event = '$page.home$model.diamond$content.0$action.bw' AND p_location = '2'
        THEN COALESCE(p_login_id, login_id)
    END) AS Icon2ExposeUV,
    COUNT(DISTINCT CASE
        WHEN event = '$page.home$model.diamond$content.0$action.ck' AND p_location = '2'
        THEN COALESCE(p_login_id, login_id)
    END) AS Icon2ClickUV,
    -- Banner资源位
    COUNT(DISTINCT CASE
        WHEN event = '$page.0$model.resource$content.0$action.bw' -- 资源位banner 裂变活动
            -- and p_proposal_no='LKUSCP117705420616835072'
            AND p_pic_url IN (
                'https://ilucky-fe-outside-aws-prod.luckincdn.us/luckymedia/1762486265845_LKUSIMG118278451060056064.jpeg'
            )
        THEN p_login_id
    END) AS SlotExposeUV,
    COUNT(DISTINCT CASE
        WHEN event = '$page.0$model.resource$content.0$action.ck'
            -- and p_proposal_no='LKUSCP117705420616835072'
            AND p_pic_url IN (
                'https://ilucky-fe-outside-aws-prod.luckincdn.us/luckymedia/1762486265845_LKUSIMG118278451060056064.jpeg'
            )
        THEN p_login_id
    END) AS SlotClickUV,
    -- 弹窗资源位
    COUNT(DISTINCT CASE
        WHEN event = '$page.0$model.popupwin$content.0$action.bw' -- 弹层 裂变活动
            AND p_proposal_no = 'LKUSCP117864583917731840'
        THEN COALESCE(p_login_id, login_id)
    END) AS PopExposeUV,
    COUNT(DISTINCT CASE
        WHEN event = '$page.0$model.popupwin$content.0$action.ck'
            AND p_proposal_no = 'LKUSCP117864583917731840'
            AND p_ck_type = 'main_button'
        THEN COALESCE(p_login_id, login_id)
    END) AS PopClickUV,
    -- 总曝光UV（三种资源位合计）
    COUNT(DISTINCT CASE
        WHEN (event = '$page.0$model.resource$content.0$action.bw'
            -- AND p_proposal_no = 'LKUSCP117705420616835072')
            AND p_pic_url IN (
                'https://ilucky-fe-outside-aws-prod.luckincdn.us/luckymedia/1762486265845_LKUSIMG118278451060056064.jpeg'
            ))
            OR (event = '$page.0$model.popupwin$content.0$action.bw'
            AND p_proposal_no = 'LKUSCP117864583917731840')
            OR (event = '$page.home$model.diamond$content.0$action.bw' AND p_location = '2')
        THEN COALESCE(p_login_id, login_id)
    END) AS TotalExposeUV,
    -- 总点击UV（三种资源位合计）
    COUNT(DISTINCT CASE
        WHEN (event = '$page.0$model.resource$content.0$action.ck'
            -- AND p_proposal_no = 'LKUSCP117705420616835072')
            AND p_pic_url IN (
                'https://ilucky-fe-outside-aws-prod.luckincdn.us/luckymedia/1762486265845_LKUSIMG118278451060056064.jpeg'
            ))
            OR (event = '$page.0$model.popupwin$content.0$action.ck'
            AND p_proposal_no = 'LKUSCP117864583917731840' AND p_ck_type = 'main_button')
            OR (event = '$page.home$model.diamond$content.0$action.ck' AND p_location = '2')
            -- proposal_no 方案编号，ck_type 点击按钮main_button是主按钮
        THEN COALESCE(p_login_id, login_id) -- 合并两个Id统计
    END) AS TotalClickUV
FROM ods_luckyus_track.v_hmonitor_track_event_rt
WHERE dt >= @cal_begin_date
      AND dt <= @cal_end_date
      -- AND platform != 3
      -- 提前过滤相关事件，大幅减少处理数据量
      AND (
          event IN (
              '$page.home$model.diamond$content.0$action.bw',
              '$page.home$model.diamond$content.0$action.ck',
              '$page.0$model.resource$content.0$action.bw',
              '$page.0$model.resource$content.0$action.ck',
              '$page.0$model.popupwin$content.0$action.bw',
              '$page.0$model.popupwin$content.0$action.ck'
          )
          OR p_login_id IS NOT NULL -- 确保DAU计算的数据不被过滤掉
      )
GROUP BY 1
ORDER BY 1
LIMIT 100000