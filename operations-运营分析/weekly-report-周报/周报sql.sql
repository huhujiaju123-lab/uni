-- ============================================================
-- Lucky US 周度日报 SQL 查询集合
-- 生成时间: 2026-02-05
-- ============================================================

-- ============================================================
-- 一、经营数据查询
-- 数据源: dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
-- ============================================================
SELECT
    YEARWEEK(dt, 1) AS week_id,
    COUNT(DISTINCT shop_name) AS shop_count,
    COUNT(DISTINCT dt) AS biz_days,
    SUM(sku_cnt) AS total_cups,
    SUM(order_cnt) AS total_orders,
    ROUND(SUM(pay_amount), 2) AS total_revenue,
    -- 店日均杯量 = 总杯量 / (店铺数 × 营业天数)
    ROUND(SUM(sku_cnt) / (COUNT(DISTINCT shop_name) * COUNT(DISTINCT dt)), 0) AS daily_cups_per_shop,
    -- 单杯实收 = 总收入 / 总杯量
    ROUND(SUM(pay_amount) / SUM(sku_cnt), 2) AS avg_price
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
  AND dt >= '2025-12-22'  -- 修改为目标日期范围
  AND dt <= '2026-02-02'
GROUP BY week_id
ORDER BY week_id;


-- ============================================================
-- 二、门店日均杯量明细
-- 数据源: dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
-- ============================================================
SELECT
    shop_name,
    YEARWEEK(dt, 1) AS week_id,
    COUNT(DISTINCT dt) AS biz_days,
    SUM(sku_cnt) AS cups,
    ROUND(SUM(sku_cnt) / COUNT(DISTINCT dt), 0) AS daily_cups,
    SUM(order_cnt) AS orders,
    ROUND(SUM(pay_amount), 2) AS revenue
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE tenant = 'LKUS'
  AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
  AND dt >= '2025-12-22'
  AND dt <= '2026-02-02'
GROUP BY shop_name, week_id
ORDER BY shop_name, week_id;


-- ============================================================
-- 三、用户结构查询（新客/留存/回流）
-- 数据源: ods_luckyus_sales_order.v_order + t_order_item
-- 注意: 需要按周分别执行，替换 {week_start} 和 {week_end}
-- ============================================================

-- 示例: 查询 202605 周 (2026-01-26 ~ 2026-02-01)
WITH week_orders AS (
    SELECT id AS order_id, user_no, pay_money
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant, 'IQ') = 0
      AND status = 90
      AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '2026-01-26'
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) <= '2026-02-01'
),
week_cups AS (
    SELECT wo.user_no, SUM(oi.quantity) AS cups
    FROM week_orders wo
    JOIN ods_luckyus_sales_order.t_order_item oi ON wo.order_id = oi.order_id
    WHERE oi.one_category_name = 'Drink'
    GROUP BY wo.user_no
),
week_order_detail AS (
    SELECT wo.user_no, COUNT(*) AS order_cnt, SUM(wo.pay_money) AS revenue, COALESCE(wc.cups, 0) AS cups
    FROM week_orders wo
    LEFT JOIN week_cups wc ON wo.user_no = wc.user_no
    GROUP BY wo.user_no, wc.cups
),
user_first AS (
    SELECT user_no, MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_date
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
      AND user_no IN (SELECT user_no FROM week_order_detail)
    GROUP BY user_no
),
user_prev AS (
    SELECT user_no, MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS prev_date
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
      AND user_no IN (SELECT user_no FROM week_order_detail)
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '2026-01-26'
    GROUP BY user_no
),
user_type_calc AS (
    SELECT
        wo.user_no,
        wo.order_cnt,
        wo.revenue,
        wo.cups,
        CASE
            WHEN uf.first_date >= '2026-01-26' THEN '新客'
            WHEN up.prev_date IS NULL THEN '留存'
            WHEN DATEDIFF('2026-01-26', up.prev_date) <= 30 THEN '留存'
            ELSE '回流'
        END AS user_type
    FROM week_order_detail wo
    LEFT JOIN user_first uf ON wo.user_no = uf.user_no
    LEFT JOIN user_prev up ON wo.user_no = up.user_no
)
SELECT
    '202605' AS week_id,
    user_type,
    COUNT(*) AS user_count,
    SUM(order_cnt) AS order_count,
    ROUND(SUM(revenue), 2) AS total_revenue,
    SUM(cups) AS total_cups,
    -- 单杯实收 = 总收入 / 总杯量
    ROUND(SUM(revenue) / NULLIF(SUM(cups), 0), 2) AS avg_price_per_cup,
    -- 频次 = 订单数 / 用户数
    ROUND(SUM(order_cnt) / COUNT(*), 2) AS frequency
FROM user_type_calc
GROUP BY user_type;


-- ============================================================
-- 四、次周留存率
-- 数据源: dw_ads.ads_user_order_rep_info_d_nw
-- ============================================================
SELECT
    YEARWEEK(src_week_first_date, 1) AS week_id,
    src_week_first_date,
    SUM(src_usr_cnt) AS src_users,
    SUM(dst_usr_cnt) AS retained_users,
    ROUND(SUM(dst_usr_cnt) / SUM(src_usr_cnt) * 100, 1) AS retention_rate
FROM dw_ads.ads_user_order_rep_info_d_nw
WHERE tenant = 'LKUS'
  AND src_week_first_date IN ('2025-12-22', '2025-12-29', '2026-01-05', '2026-01-12', '2026-01-19', '2026-01-26')
GROUP BY week_id, src_week_first_date
ORDER BY week_id;


-- ============================================================
-- 五、用户分群定义说明
-- ============================================================
/*
| 分群 | 定义 |
|------|------|
| 新客 | 本周首单用户（首购日期在本周内） |
| 留存 | 上一单距今 0-30 天 |
| 回流 | 上一单距今 31 天以上 |

更细分的人群划分：
| 人群类型 | 圈选条件 |
|----------|----------|
| 0-15天老客 | 首购后 1-15 天 |
| 16-30天老客 | 首购后 16-30 天 |
| 31天+老客 | 首购后 31 天以上 |
| 来访未购 | 7天内有访问但未购买 |
| 上月消费本月未消费 | 上月有消费，本月至今无消费 |
| 沉默用户 | 距离上次下单 30 天以上 |
| 新购用户 | 首次下单 15 天以内 |
*/


-- ============================================================
-- 六、关键口径说明
-- ============================================================
/*
1. 租户过滤: tenant = 'LKUS' 或 INSTR(tenant, 'IQ') = 0
2. 成功订单: status = 90
3. 时区转换: DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))
4. 排除测试店: shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
5. 饮品类目: one_category_name = 'Drink'
6. 店日均杯量 = 总杯量 / (店铺数 × 营业天数)
7. 单杯实收 = 总收入 / 总杯量
8. 频次 = 订单数 / 用户数
9. 次周留存率 = 下周下单用户数 / 本周下单用户数
*/
