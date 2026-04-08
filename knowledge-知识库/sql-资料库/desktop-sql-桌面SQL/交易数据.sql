-- 交易数据提取SQL
-- 参数1:传入spu_code
-- SET @spu_code = 'LKUS117416678824034305';
--参数2:传入需要统计的开始时间
SET @cal_begin_date = '2025-07-03';
--参数3:传入需要统计的结束时间
SET @cal_end_date = '2025-07-03';

SELECT  
    order_date, --日期
    time_segment, --时段
    shop_name, --店铺名称
    channel,
    spu_name,
    one_category_name,
    two_category_name,
    three_category_name,
    pay_type, --支付类型分类
    COUNT(DISTINCT order_id) AS order_cnt,
    SUM(1) AS item_cnt,
    COUNT(DISTINCT user_no) AS user_cnt,
    COUNT(DISTINCT IF(is_refund = 1,order_id,NULL)) AS refund_order_cnt,
    SUM(IF(is_refund = 1,1,0)) AS item_return_cnt,
    SUM(origin_price) AS total_origin_price,
    SUM(pay_money) AS total_pay_money
FROM
(
  SELECT  a.tenant
         ,b.user_no
         ,a.order_id
         ,a.spu_code
         ,a.spu_name
         ,a.one_category_name
         ,a.two_category_name
         ,a.three_category_name
         ,b.shop_name --店铺名称
         ,DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) AS order_date --下单日期
         ,DATE(a.create_time) AS cre_date
         ,a.refunded_money
         ,IF(a.refunded_money > 0,1,0) AS is_refund
         ,b.channel --订单渠道(1-安卓/2-IOS/3-H5/4-自助下单机/5-Grab/6-EPoint)
         ,a.origin_price
         ,a.pay_money
         ,CASE 
           WHEN HOUR(CONVERT_TZ(a.create_time,@@time_zone,'America/New_York')) BETWEEN 7 AND 8 THEN '7:00～9:00'
           WHEN HOUR(CONVERT_TZ(a.create_time,@@time_zone,'America/New_York')) BETWEEN 9 AND 10 THEN '9:00～11:00'
           WHEN HOUR(CONVERT_TZ(a.create_time,@@time_zone,'America/New_York')) BETWEEN 11 AND 12 THEN '11:00～13:00'
           WHEN HOUR(CONVERT_TZ(a.create_time,@@time_zone,'America/New_York')) BETWEEN 13 AND 14 THEN '13:00～15:00'
           WHEN HOUR(CONVERT_TZ(a.create_time,@@time_zone,'America/New_York')) BETWEEN 15 AND 16 THEN '15:00～17:00'
           WHEN HOUR(CONVERT_TZ(a.create_time,@@time_zone,'America/New_York')) BETWEEN 17 AND 18 THEN '17:00～19:00'
           WHEN HOUR(CONVERT_TZ(a.create_time,@@time_zone,'America/New_York')) BETWEEN 19 AND 20 THEN '19:00～21:00'
           ELSE '其他时段'
         END AS time_segment --时段划分
         ,CASE 
           WHEN a.pay_money = 0 THEN '免费订单'
           WHEN a.pay_money > 0 AND a.origin_price > 0 THEN
             CASE 
               WHEN a.pay_money / a.origin_price <= 0.3 THEN '付费订单-3折以内'
               WHEN a.pay_money / a.origin_price <= 0.5 THEN '付费订单-3～5折'
               WHEN a.pay_money / a.origin_price <= 0.7 THEN '付费订单-5～7折'
               WHEN a.pay_money / a.origin_price > 0.7 THEN '付费订单-7折以上'
               ELSE '付费订单-未知折扣'
             END
           WHEN a.pay_money > 0 AND a.origin_price = 0 THEN '付费订单-原价为0'
           ELSE '未知'
         END AS pay_type --支付类型分类（含折扣区间）
  FROM ods_luckyus_sales_order.t_order_item a
  LEFT JOIN ods_luckyus_sales_order.v_order b
  ON a.order_id = b.id
  WHERE INSTR(a.tenant, 'IQ') = 0
  --- AND spu_code IN (@spu_code)
  and status = 90
  AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) >= @cal_begin_date
  AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) <= @cal_end_date 
) order_cal
-- WHERE shop_name='8th & Broadway'
GROUP BY order_date, time_segment, shop_name, channel, spu_name, one_category_name, two_category_name, three_category_name, pay_type
ORDER BY order_date, time_segment, shop_name, channel, spu_name, one_category_name, two_category_name, three_category_name, pay_type