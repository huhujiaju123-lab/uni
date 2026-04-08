SET @biz_date = '2025-06-30'
SELECT  origin
       ,SUM0(1)                             AS all_user_cnt -- 截止当前累积用户数
       ,SUM(IF(is_cal_day_reg = 1,1,0))     AS cal_day_reg_user_cnt -- 当日注册用户数
       ,SUM0(IF(b.user_no IS NOT NULL,1,0)) AS coupon_user_cnt -- 领取新人券包用户数
       ,SUM0(IF(c.user_no IS NOT NULL,1,0)) AS order_user_cnt -- 下单用户数
       ,SUM0(IF(c.order_cnt = 1,1,0))       AS first_order_user_cnt -- 首单用户数
       ,SUM0(IF(c.order_cnt = 2,1,0))       AS sec2_order_user_cnt -- 2单用户数
       ,SUM0(IF(c.order_cnt = 3,1,0))       AS sec3_order_user_cnt -- 3单用户数
       ,SUM0(IF(c.order_cnt = 4,1,0))       AS sec4_order_user_cnt -- 4单用户数
       ,SUM0(IF(c.order_cnt = 5,1,0))       AS sec5_order_user_cnt -- 5单用户数
       ,SUM0(IF(c.order_cnt > 5,1,0))       AS morE6_order_user_cnt -- 6单及以上用户数
       ,SUM0(IF(c.order_cnt = 0,1,0))       AS 0_order_user_cnt -- 0单用户数 
FROM
(
  SELECT  dt
         ,user_no
         ,origin --注册来源:0-系统, 1-后台, 4-h5, 5-android, 6-iphone, 7-pos, 10-自助下单机, 11-grab
         ,IF(DAET(CONVERT_TZ(usr_reg_time,@@time_zone,reg_day_timezone_offset)) = @biz_date,1,0) is_cal_day_reg
  FROM dw_dim.dim_user_base_info_d_his
  WHERE dt = @biz_date 
) a
LEFT JOIN
(
  SELECT  user_no
  FROM dw_dwd.dwd_t_mkt_coupon_use_record_d_inc
  WHERE proposal_id = 814 --新人券包方案编号：LKUSCP117524731544281088
  AND DATE(CONVERT_TZ(receive_time, @@time_zone, default_time_zone)) = @biz_date
  GROUP BY  user_no
) b
ON a.user_no = b.user_no
LEFT JOIN
(
  SELECT  user_no
         ,COUNT(DISTINCT order_id)                        AS order_cnt
         ,SUM0(1)                                         AS item_cnt
         ,COUNT(DISTINCT IF(is_refund = 1,order_id,NULL)) AS refund_order_cnt
         ,SUM0(IF(is_refund = 1,1,0))                     AS item_return_cnt
  FROM
  (
    SELECT  a.tenant
           ,b.user_no
           ,a.order_id
           ,a.spu_code
           ,DATE(a.create_time)          AS cre_date
           ,a.refunded_money
           ,IF(a.refunded_money > 0,1,0) AS is_refund
           ,b.channel --订单渠道(1-安卓/2-IOS/3-H5/4-自助下单机/5-Grab/6-EPoint)
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b
    ON a.order_id = b.id
    WHERE INSTR(a.tenant, 'IQ') = 0
    AND b.status = 90 --订单完成
    AND b.order_category = 1  --门店订单
    AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) <= @biz_date 
  ) order_cal
  GROUP BY  user_no
)c
ON a.user_no = c.user_no