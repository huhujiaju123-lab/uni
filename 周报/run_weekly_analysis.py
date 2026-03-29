#!/usr/bin/env python3
"""
瑞幸周度数据分析执行脚本
"""
import sys
sys.path.insert(0, '/Users/xiaoxiao/.claude/skills/luckyus-data-query/scripts')

from cyberdata_query import CyberDataClient
import pandas as pd

# 时间参数
LAST_WEEK_BEGIN = '2025-01-27'
LAST_WEEK_END = '2025-02-02'
PREV_WEEK_BEGIN = '2025-01-20'
PREV_WEEK_END = '2025-01-26'


# SQL 1: 店均杯量
SQL_SHOP_AVG = f"""
WITH weekly_shop_stats AS (
    SELECT
        CASE
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN '{LAST_WEEK_BEGIN}' AND '{LAST_WEEK_END}' THEN '上周'
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN '{PREV_WEEK_BEGIN}' AND '{PREV_WEEK_END}' THEN '上上周'
        END AS week_label,
        b.shop_name,
        COUNT(*) AS cup_cnt
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    WHERE INSTR(a.tenant, 'IQ') = 0
      AND b.status = 90
      AND b.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND a.one_category_name = 'Drink'
      AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN '{PREV_WEEK_BEGIN}' AND '{LAST_WEEK_END}'
    GROUP BY week_label, b.shop_name
)
SELECT
    week_label AS 周期,
    SUM(cup_cnt) AS 总杯量,
    COUNT(DISTINCT shop_name) AS 门店数,
    ROUND(SUM(cup_cnt) / COUNT(DISTINCT shop_name), 2) AS 店均杯量
FROM weekly_shop_stats
WHERE week_label IS NOT NULL
GROUP BY week_label
ORDER BY week_label DESC
"""


# SQL 2: 用户结构明细
SQL_USER_STRUCTURE = f"""
WITH
user_register AS (
    SELECT
        user_no,
        DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) AS register_date
    FROM ods_luckyus_sales_crm.t_user
    WHERE INSTR(tenant, 'IQ') = 0
),
user_first_order AS (
    SELECT
        b.user_no,
        MIN(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York'))) AS first_order_date
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    WHERE INSTR(a.tenant, 'IQ') = 0
      AND b.status = 90
      AND b.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND a.one_category_name = 'Drink'
    GROUP BY b.user_no
),
order_with_segment AS (
    SELECT
        CASE
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN '{LAST_WEEK_BEGIN}' AND '{LAST_WEEK_END}' THEN '上周'
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN '{PREV_WEEK_BEGIN}' AND '{PREV_WEEK_END}' THEN '上上周'
        END AS week_label,
        b.user_no,
        a.order_id,
        DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) AS order_date,
        ur.register_date,
        ufo.first_order_date,
        CASE
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) = ur.register_date THEN '新客'
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) BETWEEN 1 AND 15 THEN '0-15天老客'
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) BETWEEN 16 AND 30 THEN '16-30天老客'
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) >= 31 THEN '31天+老客'
            ELSE '未知'
        END AS user_segment
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    LEFT JOIN user_register ur ON b.user_no = ur.user_no
    LEFT JOIN user_first_order ufo ON b.user_no = ufo.user_no
    WHERE INSTR(a.tenant, 'IQ') = 0
      AND b.status = 90
      AND b.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND a.one_category_name = 'Drink'
      AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN '{PREV_WEEK_BEGIN}' AND '{LAST_WEEK_END}'
),
segment_stats AS (
    SELECT
        week_label,
        user_segment,
        COUNT(DISTINCT user_no) AS user_cnt,
        COUNT(DISTINCT order_id) AS order_cnt,
        COUNT(*) AS cup_cnt,
        ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT user_no), 2) AS cups_per_user,
        ROUND(COUNT(DISTINCT user_no) * 100.0 / SUM(COUNT(DISTINCT user_no)) OVER(PARTITION BY week_label), 2) AS user_pct,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(PARTITION BY week_label), 2) AS cup_pct
    FROM order_with_segment
    WHERE week_label IS NOT NULL
    GROUP BY week_label, user_segment
)
SELECT
    week_label AS 周期,
    user_segment AS 人群,
    user_cnt AS 下单人数,
    order_cnt AS 订单数,
    cup_cnt AS 杯量,
    cups_per_user AS 人均杯量,
    user_pct AS 人数占比,
    cup_pct AS 杯量占比
FROM segment_stats
ORDER BY week_label DESC,
    CASE user_segment
        WHEN '新客' THEN 1
        WHEN '0-15天老客' THEN 2
        WHEN '16-30天老客' THEN 3
        WHEN '31天+老客' THEN 4
        ELSE 5
    END
"""


# SQL 3: 周环比变化
SQL_WOW_CHANGE = f"""
WITH
user_register AS (
    SELECT
        user_no,
        DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) AS register_date
    FROM ods_luckyus_sales_crm.t_user
    WHERE INSTR(tenant, 'IQ') = 0
),
user_first_order AS (
    SELECT
        b.user_no,
        MIN(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York'))) AS first_order_date
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    WHERE INSTR(a.tenant, 'IQ') = 0
      AND b.status = 90
      AND b.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND a.one_category_name = 'Drink'
    GROUP BY b.user_no
),
order_with_segment AS (
    SELECT
        CASE
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN '{LAST_WEEK_BEGIN}' AND '{LAST_WEEK_END}' THEN '上周'
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN '{PREV_WEEK_BEGIN}' AND '{PREV_WEEK_END}' THEN '上上周'
        END AS week_label,
        b.user_no,
        a.order_id,
        CASE
            WHEN DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) = ur.register_date THEN '新客'
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) BETWEEN 1 AND 15 THEN '0-15天老客'
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) BETWEEN 16 AND 30 THEN '16-30天老客'
            WHEN DATEDIFF(DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')), ufo.first_order_date) >= 31 THEN '31天+老客'
            ELSE '未知'
        END AS user_segment
    FROM ods_luckyus_sales_order.t_order_item a
    LEFT JOIN ods_luckyus_sales_order.v_order b ON a.order_id = b.id
    LEFT JOIN user_register ur ON b.user_no = ur.user_no
    LEFT JOIN user_first_order ufo ON b.user_no = ufo.user_no
    WHERE INSTR(a.tenant, 'IQ') = 0
      AND b.status = 90
      AND b.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND a.one_category_name = 'Drink'
      AND DATE(CONVERT_TZ(a.create_time, @@time_zone, 'America/New_York')) BETWEEN '{PREV_WEEK_BEGIN}' AND '{LAST_WEEK_END}'
),
segment_stats AS (
    SELECT
        week_label,
        user_segment,
        COUNT(DISTINCT user_no) AS user_cnt,
        COUNT(*) AS cup_cnt,
        ROUND(COUNT(DISTINCT user_no) * 100.0 / SUM(COUNT(DISTINCT user_no)) OVER(PARTITION BY week_label), 2) AS user_pct,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(PARTITION BY week_label), 2) AS cup_pct
    FROM order_with_segment
    WHERE week_label IS NOT NULL
    GROUP BY week_label, user_segment
)
SELECT
    user_segment AS 人群,
    MAX(CASE WHEN week_label = '上周' THEN user_cnt END) AS 上周人数,
    MAX(CASE WHEN week_label = '上上周' THEN user_cnt END) AS 上上周人数,
    MAX(CASE WHEN week_label = '上周' THEN user_pct END) AS 上周人数占比,
    MAX(CASE WHEN week_label = '上上周' THEN user_pct END) AS 上上周人数占比,
    ROUND(MAX(CASE WHEN week_label = '上周' THEN user_pct END) - MAX(CASE WHEN week_label = '上上周' THEN user_pct END), 2) AS 人数占比变化,
    MAX(CASE WHEN week_label = '上周' THEN cup_cnt END) AS 上周杯量,
    MAX(CASE WHEN week_label = '上上周' THEN cup_cnt END) AS 上上周杯量,
    MAX(CASE WHEN week_label = '上周' THEN cup_pct END) AS 上周杯量占比,
    MAX(CASE WHEN week_label = '上上周' THEN cup_pct END) AS 上上周杯量占比,
    ROUND(MAX(CASE WHEN week_label = '上周' THEN cup_pct END) - MAX(CASE WHEN week_label = '上上周' THEN cup_pct END), 2) AS 杯量占比变化
FROM segment_stats
GROUP BY user_segment
ORDER BY
    CASE user_segment
        WHEN '新客' THEN 1
        WHEN '0-15天老客' THEN 2
        WHEN '16-30天老客' THEN 3
        WHEN '31天+老客' THEN 4
        ELSE 5
    END
"""


def main():
    print("=" * 60)
    print("瑞幸周度数据分析")
    print(f"上周: {LAST_WEEK_BEGIN} ~ {LAST_WEEK_END}")
    print(f"上上周: {PREV_WEEK_BEGIN} ~ {PREV_WEEK_END}")
    print("=" * 60)

    client = CyberDataClient()

    # 执行 SQL 1: 店均杯量
    print("\n📊 [1/3] 店均杯量分析...")
    df1 = client.execute_task(sql=SQL_SHOP_AVG, timeout=300)
    print("\n结果:")
    print(df1.to_string(index=False))
    df1.to_csv('/Users/xiaoxiao/Vibe coding/result_shop_avg.csv', index=False, encoding='utf-8-sig')

    # 执行 SQL 2: 用户结构明细
    print("\n📊 [2/3] 用户结构分析...")
    df2 = client.execute_task(sql=SQL_USER_STRUCTURE, timeout=300)
    print("\n结果:")
    print(df2.to_string(index=False))
    df2.to_csv('/Users/xiaoxiao/Vibe coding/result_user_structure.csv', index=False, encoding='utf-8-sig')

    # 执行 SQL 3: 周环比变化
    print("\n📊 [3/3] 人群结构周环比...")
    df3 = client.execute_task(sql=SQL_WOW_CHANGE, timeout=300)
    print("\n结果:")
    print(df3.to_string(index=False))
    df3.to_csv('/Users/xiaoxiao/Vibe coding/result_wow_change.csv', index=False, encoding='utf-8-sig')

    print("\n" + "=" * 60)
    print("✅ 分析完成！结果已保存:")
    print("  - result_shop_avg.csv")
    print("  - result_user_structure.csv")
    print("  - result_wow_change.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()
