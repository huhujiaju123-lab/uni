#!/usr/bin/env python3
"""
Lucky US 周度日报生成脚本
生成包含经营数据、用户结构、单杯实收、频次、次周留存率的周度报表
"""

import json
import subprocess
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 配置
AUTH_FILE = Path.home() / ".claude/skills/cyberdata-query/auth.json"
EXCLUDED_SHOPS = "('NJ Test Kitchen', 'NJ Test Kitchen 2')"

def load_auth():
    """加载认证信息"""
    with open(AUTH_FILE) as f:
        return json.load(f)

def run_sql(sql: str, max_retries: int = 5) -> list:
    """执行 SQL 查询并返回结果"""
    import requests

    auth = load_auth()
    cookies = auth['cookies']
    jwttoken = auth['jwttoken']
    timestamp = int(time.time() * 1000)

    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json; charset=UTF-8',
        'jwttoken': jwttoken,
        'productkey': 'CyberData',
        'origin': 'https://idpcd.luckincoffee.us',
        'Cookie': cookies
    }

    payload = {
        "_t": timestamp,
        "tenantId": "1001",
        "userId": "47",
        "projectId": "1906904360294313985",
        "resourceGroupId": 1,
        "taskId": "1990991087752757249",
        "variables": {},
        "sqlStatement": sql,
        "env": 5
    }

    # 提交查询
    resp = requests.post(
        'https://idpcd.luckincoffee.us/api/dev/task/run',
        headers=headers,
        json=payload
    )
    response = resp.json()

    if response.get('code') != '200':
        raise Exception(f"查询提交失败: {response}")

    task_id = response['data']
    print(f"  任务ID: {task_id}")

    # 等待执行
    time.sleep(8)

    # 获取结果
    for retry in range(max_retries):
        timestamp = int(time.time() * 1000)
        result_payload = {
            "_t": timestamp,
            "tenantId": "1001",
            "userId": "47",
            "projectId": "1906904360294313985",
            "env": 5,
            "taskInstanceId": task_id
        }

        resp = requests.post(
            'https://idpcd.luckincoffee.us/api/logger/getQueryLog',
            headers=headers,
            json=result_payload
        )
        response = resp.json()

        if response.get('code') == '200' and response.get('data'):
            for item in response['data']:
                columns_data = item.get('columns', [])
                if columns_data and len(columns_data) > 1:  # 至少有表头和一行数据
                    print(f"  获取到 {len(columns_data) - 1} 行数据")
                    return columns_data
                # 检查是否还在运行
                status = item.get('status', '')
                if status:
                    print(f"  任务状态: {status}")

        # 如果还没完成，等待后重试
        print(f"  等待结果... (重试 {retry + 1}/{max_retries})")
        if retry < max_retries - 1:
            time.sleep(5)

    print("  查询超时或无结果")
    # Debug: 打印最后一次响应
    print(f"  最后响应: {json.dumps(response, ensure_ascii=False)[:500]}")
    return []

def get_week_dates(year_week: str) -> tuple:
    """将 YYYYWW 格式转换为日期范围（周一到周日）"""
    year = int(year_week[:4])
    week = int(year_week[4:])

    # 找到该年第一个周一
    jan1 = datetime(year, 1, 1)
    # ISO 周从周一开始
    days_to_monday = (7 - jan1.weekday()) % 7
    if jan1.weekday() <= 3:  # 周一到周四
        first_monday = jan1 - timedelta(days=jan1.weekday())
    else:
        first_monday = jan1 + timedelta(days=7 - jan1.weekday())

    # 计算目标周的周一
    week_monday = first_monday + timedelta(weeks=week - 1)
    week_sunday = week_monday + timedelta(days=6)

    return week_monday.strftime('%Y-%m-%d'), week_sunday.strftime('%Y-%m-%d')

def get_week_from_date(date_str: str) -> str:
    """从日期获取 YYYYWW 格式的周"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return f"{dt.isocalendar()[0]}{dt.isocalendar()[1]:02d}"

def get_recent_weeks(n: int = 6) -> list:
    """获取最近 n 周的 YYYYWW 列表"""
    today = datetime.now()
    # 找到本周一
    monday = today - timedelta(days=today.weekday())
    # 从上周开始（因为本周数据不完整）
    monday = monday - timedelta(weeks=1)

    weeks = []
    for i in range(n):
        week_monday = monday - timedelta(weeks=i)
        year_week = f"{week_monday.isocalendar()[0]}{week_monday.isocalendar()[1]:02d}"
        weeks.append(year_week)

    return list(reversed(weeks))  # 从早到晚排序


def query_business_metrics(weeks: list) -> pd.DataFrame:
    """查询经营数据指标 - 在数据库端完成聚合"""
    print("查询经营数据...")

    # 获取完整日期范围
    all_start = get_week_dates(weeks[0])[0]
    all_end = get_week_dates(weeks[-1])[1]

    # 基础指标查询（从汇总表），包含营业天数
    sql = f"""
    SELECT
        YEARWEEK(dt, 1) AS week_id,
        COUNT(DISTINCT shop_name) AS shop_count,
        COUNT(DISTINCT dt) AS biz_days,
        SUM(sku_cnt) AS total_cups,
        SUM(order_cnt) AS total_orders,
        ROUND(SUM(pay_amount), 2) AS total_revenue
    FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
    WHERE tenant = 'LKUS'
      AND one_category_name = 'Drink'
      AND shop_name NOT IN {EXCLUDED_SHOPS}
      AND dt >= '{all_start}'
      AND dt <= '{all_end}'
    GROUP BY week_id
    ORDER BY week_id
    """

    result = run_sql(sql)
    if not result:
        return pd.DataFrame()

    headers = result[0]
    data = result[1:]
    df = pd.DataFrame(data, columns=headers)

    if df.empty:
        return pd.DataFrame()

    # 转换数据类型
    df['shop_count'] = df['shop_count'].astype(float)
    df['biz_days'] = df['biz_days'].astype(float)
    df['total_cups'] = df['total_cups'].astype(float)
    df['total_orders'] = df['total_orders'].astype(float)
    df['total_revenue'] = df['total_revenue'].astype(float)

    # 计算衍生指标
    # 店日均杯量 = 总杯量 / (店铺数 × 营业天数)
    df['daily_cups_per_shop'] = df['total_cups'] / (df['shop_count'] * df['biz_days'])
    df['avg_price'] = df['total_revenue'] / df['total_cups']

    return df


def query_channel_metrics(weeks: list) -> pd.DataFrame:
    """
    查询渠道指标
    注意：Lucky US 当前没有外卖渠道(channel=5)，主要渠道是:
    - 1=安卓, 2=iOS, 3=H5
    - 8, 9, 10 可能是新增渠道
    暂时跳过外卖占比计算
    """
    print("查询渠道数据... (跳过，无外卖渠道)")
    return pd.DataFrame()

def query_shop_details(weeks: list) -> pd.DataFrame:
    """查询各门店日均杯量 - 在数据库端完成聚合"""
    print("查询门店明细...")

    # 获取完整日期范围
    all_start = get_week_dates(weeks[0])[0]
    all_end = get_week_dates(weeks[-1])[1]

    sql = f"""
    SELECT
        shop_name,
        YEARWEEK(dt, 1) AS week_id,
        COUNT(DISTINCT dt) AS biz_days,
        SUM(sku_cnt) AS cups,
        SUM(order_cnt) AS orders,
        ROUND(SUM(pay_amount), 2) AS revenue
    FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
    WHERE tenant = 'LKUS'
      AND one_category_name = 'Drink'
      AND shop_name NOT IN {EXCLUDED_SHOPS}
      AND dt >= '{all_start}'
      AND dt <= '{all_end}'
    GROUP BY shop_name, week_id
    ORDER BY shop_name, week_id
    """

    result = run_sql(sql)
    if not result:
        return pd.DataFrame()

    headers = result[0]
    data = result[1:]
    df = pd.DataFrame(data, columns=headers)

    if not df.empty:
        df['cups'] = df['cups'].astype(float)
        df['biz_days'] = df['biz_days'].astype(float)
        # 计算日均杯量
        df['daily_cups'] = df['cups'] / df['biz_days']

    return df


def query_user_structure(weeks: list) -> pd.DataFrame:
    """
    查询用户结构（新客/留存/回流）- 单周查询版本
    为避免超时，按周分别查询
    """
    print("查询用户结构...")

    all_results = []

    for week in weeks:
        week_start, week_end = get_week_dates(week)
        print(f"  查询 {week} ({week_start} ~ {week_end})...")

        # 使用简化 SQL（不 JOIN t_order_item 避免超时）
        sql = f"""
        WITH week_order_detail AS (
            SELECT user_no, COUNT(*) AS order_cnt, SUM(pay_money) AS revenue
            FROM ods_luckyus_sales_order.v_order
            WHERE INSTR(tenant, 'IQ') = 0
              AND status = 90
              AND shop_name NOT IN {EXCLUDED_SHOPS}
              AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= '{week_start}'
              AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) <= '{week_end}'
            GROUP BY user_no
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
              AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) < '{week_start}'
            GROUP BY user_no
        ),
        user_type_calc AS (
            SELECT
                wo.user_no,
                wo.order_cnt,
                wo.revenue,
                CASE
                    WHEN uf.first_date >= '{week_start}' THEN '新客'
                    WHEN up.prev_date IS NULL THEN '留存'
                    WHEN DATEDIFF('{week_start}', up.prev_date) <= 30 THEN '留存'
                    ELSE '回流'
                END AS user_type
            FROM week_order_detail wo
            LEFT JOIN user_first uf ON wo.user_no = uf.user_no
            LEFT JOIN user_prev up ON wo.user_no = up.user_no
        )
        SELECT
            '{week}' AS week_id,
            user_type,
            COUNT(*) AS user_count,
            SUM(order_cnt) AS order_count,
            ROUND(SUM(revenue), 2) AS total_revenue
        FROM user_type_calc
        GROUP BY user_type
        """

        result = run_sql(sql)
        if result and len(result) > 1:
            headers = result[0]
            data = result[1:]
            week_df = pd.DataFrame(data, columns=headers)
            all_results.append(week_df)

    if not all_results:
        return pd.DataFrame()

    result_df = pd.concat(all_results, ignore_index=True)
    result_df['user_count'] = result_df['user_count'].astype(float)
    result_df['order_count'] = result_df['order_count'].astype(float)
    result_df['total_revenue'] = result_df['total_revenue'].astype(float)

    return result_df


def query_weekly_retention(weeks: list) -> pd.DataFrame:
    """查询次周留存率（使用预计算表）"""
    print("查询次周留存率...")

    # 将 YYYYWW 转换为周一日期
    week_dates = [get_week_dates(w)[0] for w in weeks]
    week_list = "'" + "','".join(week_dates) + "'"

    sql = f"""
    SELECT
        YEARWEEK(src_week_first_date, 1) AS week_id,
        SUM(src_usr_cnt) AS src_users,
        SUM(dst_usr_cnt) AS retained_users
    FROM dw_ads.ads_user_order_rep_info_d_nw
    WHERE tenant = 'LKUS'
      AND src_week_first_date IN ({week_list})
    GROUP BY week_id
    ORDER BY week_id
    """

    result = run_sql(sql)
    if not result:
        return pd.DataFrame()

    headers = result[0]
    data = result[1:]
    df = pd.DataFrame(data, columns=headers)

    df['src_users'] = df['src_users'].astype(float)
    df['retained_users'] = df['retained_users'].astype(float)
    df['retention_rate'] = df['retained_users'] / df['src_users'] * 100

    return df


def calculate_wow_change(current: float, previous: float) -> str:
    """计算周环比"""
    if previous == 0 or pd.isna(previous):
        return "N/A"
    change = (current - previous) / previous * 100
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.1f}%"


def generate_report(weeks: list):
    """生成完整周度日报"""
    print(f"\n生成 {weeks[0]} ~ {weeks[-1]} 周度日报\n")
    print("=" * 60)

    # 1. 经营数据（基础指标）
    business_df = query_business_metrics(weeks)

    # 2. 渠道数据（外卖占比等）
    channel_df = query_channel_metrics(weeks)

    # 合并数据
    if not business_df.empty and not channel_df.empty:
        # 转换 week_id 类型以便合并
        business_df['week_id'] = business_df['week_id'].astype(str)
        channel_df['week_id'] = channel_df['week_id'].astype(str)
        merged_df = business_df.merge(channel_df[['week_id', 'delivery_ratio']], on='week_id', how='left')
    else:
        merged_df = business_df

    if not merged_df.empty:
        print("\n【模块1: 经营数据】")
        print("-" * 40)

        # 过滤掉本周（数据不完整）
        target_weeks = [str(w) for w in weeks]
        merged_df = merged_df[merged_df['week_id'].isin(target_weeks)]

        metrics = [
            ('总杯量', 'total_cups', '.0f'),
            ('总订单数', 'total_orders', '.0f'),
            ('店日均杯量', 'daily_cups_per_shop', '.0f'),
            ('累计店铺', 'shop_count', '.0f'),
            ('营业天数', 'biz_days', '.0f'),
            ('单杯实收', 'avg_price', '.2f', '$'),
            ('总销售额', 'total_revenue', '.0f', '$'),
        ]

        # 如果有渠道数据，添加外卖占比
        if 'delivery_ratio' in merged_df.columns:
            metrics.insert(3, ('外卖占比', 'delivery_ratio', '.1f', '%'))

        # 输出表格
        header = ['指标'] + list(merged_df['week_id']) + ['环比']
        print('\t'.join([str(h) for h in header]))

        for metric in metrics:
            name = metric[0]
            col = metric[1]
            fmt = metric[2]
            suffix = metric[3] if len(metric) > 3 else ''

            if col not in merged_df.columns:
                continue

            values = merged_df[col].tolist()
            row = [name]
            for v in values:
                if pd.isna(v):
                    row.append("N/A")
                elif suffix == '%':
                    row.append(f"{v:{fmt}}{suffix}")
                elif suffix == '$':
                    row.append(f"{suffix}{v:{fmt}}")
                else:
                    row.append(f"{v:{fmt}}")

            # 环比
            if len(values) >= 2 and not pd.isna(values[-1]) and not pd.isna(values[-2]):
                wow = calculate_wow_change(values[-1], values[-2])
            else:
                wow = "N/A"
            row.append(wow)

            print('\t'.join(row))

        # 保存到 CSV
        merged_df.to_csv('result_business_metrics.csv', index=False)
        print("\n经营数据已保存到 result_business_metrics.csv")

    # 2. 用户结构
    user_df = query_user_structure(weeks)
    if not user_df.empty:
        print("\n【模块2: 用户结构】")
        print("-" * 40)

        user_df['user_count'] = user_df['user_count'].astype(float)
        user_df['order_count'] = user_df['order_count'].astype(float)
        user_df['total_revenue'] = user_df['total_revenue'].astype(float)

        # 按周汇总
        weekly_totals = user_df.groupby('week_id').agg({
            'user_count': 'sum',
            'order_count': 'sum',
            'total_revenue': 'sum'
        }).reset_index()
        weekly_totals['user_type'] = '总计'

        # 合并
        combined_df = pd.concat([user_df, weekly_totals], ignore_index=True)

        # 计算占比和频次
        pivot_users = combined_df.pivot(index='user_type', columns='week_id', values='user_count')
        pivot_orders = combined_df.pivot(index='user_type', columns='week_id', values='order_count')
        pivot_revenue = combined_df.pivot(index='user_type', columns='week_id', values='total_revenue')

        # 用户数
        print("\n用户数:")
        user_types = ['总计', '新客', '留存', '回流']
        header = ['分群'] + list(pivot_users.columns) + ['环比']
        print('\t'.join(header))
        for ut in user_types:
            if ut in pivot_users.index:
                values = pivot_users.loc[ut].tolist()
                row = [ut] + [f"{int(v)}" for v in values]
                if len(values) >= 2:
                    row.append(calculate_wow_change(values[-1], values[-2]))
                else:
                    row.append("N/A")
                print('\t'.join(row))

        # 用户占比
        print("\n用户占比:")
        for ut in ['新客', '留存', '回流']:
            if ut in pivot_users.index and '总计' in pivot_users.index:
                ratios = pivot_users.loc[ut] / pivot_users.loc['总计'] * 100
                row = [ut] + [f"{v:.1f}%" for v in ratios.tolist()]
                if len(ratios) >= 2:
                    row.append(calculate_wow_change(ratios.iloc[-1], ratios.iloc[-2]))
                else:
                    row.append("N/A")
                print('\t'.join(row))

        # 客单价（按用户类型）= 收入 / 订单数
        print("\n客单价（按用户类型）:")
        for ut in user_types:
            if ut in pivot_revenue.index and ut in pivot_orders.index:
                avg_price = pivot_revenue.loc[ut] / pivot_orders.loc[ut]
                row = [ut] + [f"${v:.2f}" if not pd.isna(v) and v != float('inf') else "N/A" for v in avg_price.tolist()]
                if len(avg_price) >= 2 and not pd.isna(avg_price.iloc[-1]) and not pd.isna(avg_price.iloc[-2]):
                    row.append(calculate_wow_change(avg_price.iloc[-1], avg_price.iloc[-2]))
                else:
                    row.append("N/A")
                print('\t'.join(row))

        # 频次
        print("\n频次（订单数/用户数）:")
        for ut in user_types:
            if ut in pivot_users.index and ut in pivot_orders.index:
                freq = pivot_orders.loc[ut] / pivot_users.loc[ut]
                row = [ut] + [f"{v:.2f}" for v in freq.tolist()]
                if len(freq) >= 2:
                    row.append(calculate_wow_change(freq.iloc[-1], freq.iloc[-2]))
                else:
                    row.append("N/A")
                print('\t'.join(row))

        # 保存用户结构
        combined_df.to_csv('result_user_structure.csv', index=False)
        print("\n用户结构已保存到 result_user_structure.csv")

    # 3. 次周留存率
    retention_df = query_weekly_retention(weeks)
    if not retention_df.empty:
        print("\n【模块3: 次周留存率】")
        print("-" * 40)

        header = ['指标'] + list(retention_df['week_id']) + ['环比']
        print('\t'.join(header))

        values = retention_df['retention_rate'].tolist()
        row = ['留存率'] + [f"{v:.1f}%" for v in values]
        if len(values) >= 2:
            row.append(calculate_wow_change(values[-1], values[-2]))
        else:
            row.append("N/A")
        print('\t'.join(row))

        retention_df.to_csv('result_retention.csv', index=False)
        print("\n留存率已保存到 result_retention.csv")

    # 4. 门店明细
    shop_df = query_shop_details(weeks)

    print("\n" + "=" * 60)
    print("报表生成完成!")

    # 生成 Markdown 格式报表
    generate_markdown_report(weeks, merged_df if not business_df.empty else None,
                             user_df if not user_df.empty else None,
                             retention_df if not retention_df.empty else None,
                             shop_df if not shop_df.empty else None)


def generate_markdown_report(weeks, business_df, user_df, retention_df, shop_df):
    """生成 Markdown 格式的周度日报"""
    output = []
    output.append(f"# Lucky US 周度日报")
    output.append(f"\n**报告周期**: {weeks[0]} ~ {weeks[-1]}")
    output.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 经营数据
    if business_df is not None and not business_df.empty:
        output.append("\n## 一、经营数据")
        output.append("\n| 指标 | " + " | ".join([str(w) for w in business_df['week_id']]) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in business_df['week_id']]) + "|------|")

        metrics = [
            ('总杯量', 'total_cups', '.0f', ''),
            ('总订单数', 'total_orders', '.0f', ''),
            ('店日均杯量', 'daily_cups_per_shop', '.0f', ''),
            ('累计店铺', 'shop_count', '.0f', ''),
            ('营业天数', 'biz_days', '.0f', ''),
            ('单杯实收', 'avg_price', '.2f', '$'),
            ('总销售额', 'total_revenue', '.0f', '$'),
        ]

        for name, col, fmt, prefix in metrics:
            if col not in business_df.columns:
                continue
            values = business_df[col].tolist()
            formatted = []
            for v in values:
                if prefix == '$':
                    formatted.append(f"${v:{fmt}}")
                else:
                    formatted.append(f"{v:{fmt}}")
            wow = calculate_wow_change(values[-1], values[-2]) if len(values) >= 2 else "N/A"
            output.append(f"| {name} | " + " | ".join(formatted) + f" | {wow} |")

    # 用户结构
    if user_df is not None and not user_df.empty:
        output.append("\n## 二、用户结构")

        # 计算汇总
        weekly_totals = user_df.groupby('week_id').agg({
            'user_count': 'sum',
            'order_count': 'sum',
            'total_revenue': 'sum'
        }).reset_index()
        weekly_totals['user_type'] = '总计'
        combined_df = pd.concat([user_df, weekly_totals], ignore_index=True)

        pivot_users = combined_df.pivot(index='user_type', columns='week_id', values='user_count')
        pivot_orders = combined_df.pivot(index='user_type', columns='week_id', values='order_count')
        pivot_revenue = combined_df.pivot(index='user_type', columns='week_id', values='total_revenue')

        # 用户数表格
        output.append("\n### 用户数")
        output.append("\n| 分群 | " + " | ".join([str(c) for c in pivot_users.columns]) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in pivot_users.columns]) + "|------|")

        for ut in ['总计', '新客', '留存', '回流']:
            if ut in pivot_users.index:
                values = pivot_users.loc[ut].tolist()
                formatted = [f"{int(v):,}" for v in values]
                wow = calculate_wow_change(values[-1], values[-2]) if len(values) >= 2 else "N/A"
                output.append(f"| {ut} | " + " | ".join(formatted) + f" | {wow} |")

        # 用户占比
        output.append("\n### 用户占比")
        output.append("\n| 分群 | " + " | ".join([str(c) for c in pivot_users.columns]) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in pivot_users.columns]) + "|------|")

        for ut in ['新客', '留存', '回流']:
            if ut in pivot_users.index and '总计' in pivot_users.index:
                ratios = pivot_users.loc[ut] / pivot_users.loc['总计'] * 100
                formatted = [f"{v:.1f}%" for v in ratios.tolist()]
                wow = calculate_wow_change(ratios.iloc[-1], ratios.iloc[-2]) if len(ratios) >= 2 else "N/A"
                output.append(f"| {ut} | " + " | ".join(formatted) + f" | {wow} |")

        # 客单价（按用户类型）= 收入 / 订单数
        output.append("\n### 客单价（收入/订单数）")
        output.append("\n| 分群 | " + " | ".join([str(c) for c in pivot_users.columns]) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in pivot_users.columns]) + "|------|")

        for ut in ['总计', '新客', '留存', '回流']:
            if ut in pivot_revenue.index and ut in pivot_orders.index:
                avg_price = pivot_revenue.loc[ut] / pivot_orders.loc[ut]
                formatted = [f"${v:.2f}" if not pd.isna(v) and v != float('inf') else "N/A" for v in avg_price.tolist()]
                if len(avg_price) >= 2 and not pd.isna(avg_price.iloc[-1]) and not pd.isna(avg_price.iloc[-2]):
                    wow = calculate_wow_change(avg_price.iloc[-1], avg_price.iloc[-2])
                else:
                    wow = "N/A"
                output.append(f"| {ut} | " + " | ".join(formatted) + f" | {wow} |")

        # 频次
        output.append("\n### 频次（订单数/用户数）")
        output.append("\n| 分群 | " + " | ".join([str(c) for c in pivot_users.columns]) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in pivot_users.columns]) + "|------|")

        for ut in ['总计', '新客', '留存', '回流']:
            if ut in pivot_users.index and ut in pivot_orders.index:
                freq = pivot_orders.loc[ut] / pivot_users.loc[ut]
                formatted = [f"{v:.2f}" for v in freq.tolist()]
                wow = calculate_wow_change(freq.iloc[-1], freq.iloc[-2]) if len(freq) >= 2 else "N/A"
                output.append(f"| {ut} | " + " | ".join(formatted) + f" | {wow} |")

    # 次周留存率
    if retention_df is not None and not retention_df.empty:
        output.append("\n## 三、次周留存率")
        output.append("\n| 指标 | " + " | ".join([str(w) for w in retention_df['week_id']]) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in retention_df['week_id']]) + "|------|")

        values = retention_df['retention_rate'].tolist()
        formatted = [f"{v:.1f}%" for v in values]
        wow = calculate_wow_change(values[-1], values[-2]) if len(values) >= 2 else "N/A"
        output.append(f"| 留存率 | " + " | ".join(formatted) + f" | {wow} |")

    # 门店明细（日均杯量）
    if shop_df is not None and not shop_df.empty:
        output.append("\n## 四、门店日均杯量")

        # 使用日均杯量
        pivot_shop = shop_df.pivot(index='shop_name', columns='week_id', values='daily_cups')

        output.append("\n| 门店 | " + " | ".join([str(c) for c in pivot_shop.columns]) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in pivot_shop.columns]) + "|------|")

        for shop in pivot_shop.index:
            values = pivot_shop.loc[shop].tolist()
            formatted = [f"{int(v)}" if not pd.isna(v) else "-" for v in values]
            if len(values) >= 2 and not pd.isna(values[-1]) and not pd.isna(values[-2]):
                wow = calculate_wow_change(values[-1], values[-2])
            else:
                wow = "N/A"
            output.append(f"| {shop} | " + " | ".join(formatted) + f" | {wow} |")

    # 写入文件
    report_content = "\n".join(output)
    with open('weekly_report.md', 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"\nMarkdown 报表已保存到 weekly_report.md")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Lucky US 周度日报生成工具')
    parser.add_argument('-n', '--num-weeks', type=int, default=6,
                        help='分析最近N周数据 (默认: 6)')
    parser.add_argument('-w', '--weeks', nargs='+',
                        help='指定周列表，格式: YYYYWW (例如: 202601 202602)')
    parser.add_argument('-o', '--output', default='weekly_report.md',
                        help='输出文件名 (默认: weekly_report.md)')

    args = parser.parse_args()

    if args.weeks:
        weeks = args.weeks
    else:
        weeks = get_recent_weeks(args.num_weeks)

    print(f"分析周期: {weeks}")

    # 生成报表
    generate_report(weeks)


if __name__ == "__main__":
    main()
