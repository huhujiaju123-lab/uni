#!/usr/bin/env python3
"""
Lucky US 日报生成脚本
包含：业务结果、用户模块、品类模块、核心商品渗透
"""

import json
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
                if columns_data and len(columns_data) > 1:
                    print(f"  获取到 {len(columns_data) - 1} 行数据")
                    return columns_data
                status = item.get('status', '')
                if status:
                    print(f"  任务状态: {status}")

        print(f"  等待结果... (重试 {retry + 1}/{max_retries})")
        if retry < max_retries - 1:
            time.sleep(5)

    print("  查询超时或无结果")
    return []


def get_recent_dates(n: int = 3) -> list:
    """获取最近 n 天的日期列表（不含今天）"""
    today = datetime.now()
    dates = []
    for i in range(n, 0, -1):
        date = today - timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
    return dates


def query_business_metrics(dates: list) -> pd.DataFrame:
    """模块1: 业务结果 - 杯量、单杯实收、店日均杯量"""
    print("\n【模块1】查询业务结果...")

    date_list = "'" + "','".join(dates) + "'"

    sql = f"""
    SELECT
        dt AS 日期,
        COUNT(DISTINCT shop_name) AS 营业店铺数,
        SUM(sku_cnt) AS 杯量,
        SUM(order_cnt) AS 订单数,
        ROUND(SUM(pay_amount), 2) AS 销售额,
        ROUND(SUM(pay_amount) / SUM(sku_cnt), 2) AS 单杯实收
    FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
    WHERE tenant = 'LKUS'
      AND one_category_name = 'Drink'
      AND shop_name NOT IN {EXCLUDED_SHOPS}
      AND dt IN ({date_list})
    GROUP BY dt
    ORDER BY dt
    """

    result = run_sql(sql)
    if not result:
        return pd.DataFrame()

    headers = result[0]
    data = result[1:]
    df = pd.DataFrame(data, columns=headers)

    # 转换数据类型
    for col in ['营业店铺数', '杯量', '订单数', '销售额', '单杯实收']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 计算店日均杯量
    df['店日均杯量'] = (df['杯量'] / df['营业店铺数']).round(0)

    return df


def query_user_metrics(dates: list) -> pd.DataFrame:
    """模块3: 用户 - 注册用户数、新客数、老客数、7日留存率、店日均"""
    print("\n【模块3】查询用户指标...")

    all_results = []

    for date in dates:
        print(f"  查询 {date}...")

        # 计算7天前的日期（用于7日留存计算）
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        date_7d_ago = (date_obj - timedelta(days=7)).strftime('%Y-%m-%d')

        sql = f"""
        WITH day_orders AS (
            -- 当日有订单的用户
            SELECT DISTINCT user_no
            FROM ods_luckyus_sales_order.v_order
            WHERE INSTR(tenant, 'IQ') = 0
              AND status = 90
              AND shop_name NOT IN {EXCLUDED_SHOPS}
              AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) = '{date}'
        ),
        all_user_first AS (
            -- 所有用户的首购日期（全量）
            SELECT user_no, MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_date
            FROM ods_luckyus_sales_order.v_order
            WHERE INSTR(tenant, 'IQ') = 0 AND status = 90
            GROUP BY user_no
        ),
        user_type_calc AS (
            SELECT
                d.user_no,
                CASE WHEN uf.first_date = '{date}' THEN '新客' ELSE '老客' END AS user_type
            FROM day_orders d
            LEFT JOIN all_user_first uf ON d.user_no = uf.user_no
        ),
        -- 7天前的新客（首购日期=7天前）
        new_users_7d_ago AS (
            SELECT user_no
            FROM all_user_first
            WHERE first_date = '{date_7d_ago}'
        ),
        -- 7天前新客的7日内复购（不含首购当天）
        new_user_retention AS (
            SELECT COUNT(DISTINCT user_no) AS retained_new_users
            FROM ods_luckyus_sales_order.v_order
            WHERE INSTR(tenant, 'IQ') = 0
              AND status = 90
              AND user_no IN (SELECT user_no FROM new_users_7d_ago)
              AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) > '{date_7d_ago}'
              AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) <= '{date}'
        ),
        -- 7天前下单的老客（首购日期<7天前）
        old_users_7d_ago AS (
            SELECT DISTINCT o.user_no
            FROM ods_luckyus_sales_order.v_order o
            JOIN all_user_first uf ON o.user_no = uf.user_no
            WHERE INSTR(o.tenant, 'IQ') = 0
              AND o.status = 90
              AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York')) = '{date_7d_ago}'
              AND uf.first_date < '{date_7d_ago}'
        ),
        -- 7天前老客的7日内复购
        old_user_retention AS (
            SELECT COUNT(DISTINCT user_no) AS retained_old_users
            FROM ods_luckyus_sales_order.v_order
            WHERE INSTR(tenant, 'IQ') = 0
              AND status = 90
              AND user_no IN (SELECT user_no FROM old_users_7d_ago)
              AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) > '{date_7d_ago}'
              AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) <= '{date}'
        ),
        -- 当日注册用户数
        reg_users AS (
            SELECT COUNT(*) AS reg_count
            FROM ods_luckyus_sales_crm.t_user
            WHERE INSTR(tenant, 'IQ') = 0
              AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) = '{date}'
        ),
        -- 当日营业店铺数
        shop_count AS (
            SELECT COUNT(DISTINCT shop_name) AS shop_cnt
            FROM ods_luckyus_sales_order.v_order
            WHERE INSTR(tenant, 'IQ') = 0
              AND status = 90
              AND shop_name NOT IN {EXCLUDED_SHOPS}
              AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) = '{date}'
        )
        SELECT
            '{date}' AS 日期,
            (SELECT shop_cnt FROM shop_count) AS 营业店铺数,
            (SELECT reg_count FROM reg_users) AS 注册用户数,
            SUM(CASE WHEN user_type = '新客' THEN 1 ELSE 0 END) AS 新客数,
            SUM(CASE WHEN user_type = '老客' THEN 1 ELSE 0 END) AS 老客数,
            (SELECT COUNT(*) FROM new_users_7d_ago) AS 七日前新客数,
            (SELECT retained_new_users FROM new_user_retention) AS 新客7日留存人数,
            (SELECT COUNT(*) FROM old_users_7d_ago) AS 七日前老客数,
            (SELECT retained_old_users FROM old_user_retention) AS 老客7日留存人数
        FROM user_type_calc
        """

        result = run_sql(sql)
        if result and len(result) > 1:
            headers = result[0]
            data = result[1:]
            day_df = pd.DataFrame(data, columns=headers)
            all_results.append(day_df)

    if not all_results:
        return pd.DataFrame()

    df = pd.concat(all_results, ignore_index=True)

    # 转换数据类型
    numeric_cols = ['营业店铺数', '注册用户数', '新客数', '老客数', '七日前新客数', '新客7日留存人数', '七日前老客数', '老客7日留存人数']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 计算留存率（避免除零）
    df['新客7日留存率'] = df.apply(
        lambda x: round(x['新客7日留存人数'] / x['七日前新客数'] * 100, 1) if x['七日前新客数'] > 0 else 0, axis=1
    )
    df['老客7日留存率'] = df.apply(
        lambda x: round(x['老客7日留存人数'] / x['七日前老客数'] * 100, 1) if x['七日前老客数'] > 0 else 0, axis=1
    )

    # 计算店日均
    df['店日均新客'] = (df['新客数'] / df['营业店铺数']).round(1)
    df['店日均老客'] = (df['老客数'] / df['营业店铺数']).round(1)

    # 计算新老客占比
    df['总下单用户'] = df['新客数'] + df['老客数']
    df['新客占比'] = (df['新客数'] / df['总下单用户'] * 100).round(1)
    df['老客占比'] = (df['老客数'] / df['总下单用户'] * 100).round(1)

    return df


def query_category_metrics(dates: list) -> pd.DataFrame:
    """模块4: 品类 - 折扣率分布（从t_order_item查询，较慢）"""
    print("\n【模块4】查询品类指标...")

    all_results = []

    for date in dates:
        print(f"  查询 {date} 折扣分布...")

        sql = f"""
        SELECT
            '{date}' AS 日期,
            COUNT(*) AS 总订单项数,
            SUM(CASE WHEN pay_money = 0.99 THEN 1 ELSE 0 END) AS 零点九九订单,
            SUM(CASE WHEN origin_price > 0 AND pay_money / origin_price < 0.3 THEN 1 ELSE 0 END) AS 三折以内,
            SUM(CASE WHEN origin_price > 0 AND pay_money / origin_price >= 0.3 AND pay_money / origin_price < 0.5 THEN 1 ELSE 0 END) AS 三至五折,
            SUM(CASE WHEN origin_price > 0 AND pay_money / origin_price >= 0.5 AND pay_money / origin_price < 0.7 THEN 1 ELSE 0 END) AS 五至七折,
            SUM(CASE WHEN origin_price > 0 AND pay_money / origin_price >= 0.7 THEN 1 ELSE 0 END) AS 七折以上,
            ROUND(AVG(CASE WHEN origin_price > 0 THEN pay_money / origin_price END), 3) AS 平均折扣率
        FROM ods_luckyus_sales_order.t_order_item
        WHERE INSTR(tenant, 'IQ') = 0
          AND one_category_name = 'Drink'
          AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) = '{date}'
        """

        result = run_sql(sql)
        if result and len(result) > 1:
            headers = result[0]
            data = result[1:]
            day_df = pd.DataFrame(data, columns=headers)
            all_results.append(day_df)

    if not all_results:
        return pd.DataFrame()

    df = pd.concat(all_results, ignore_index=True)

    # 转换并计算占比
    numeric_cols = ['总订单项数', '零点九九订单', '三折以内', '三至五折', '五至七折', '七折以上']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['平均折扣率'] = pd.to_numeric(df['平均折扣率'], errors='coerce')

    # 计算占比
    total = df['总订单项数']
    df['0.99占比'] = (df['零点九九订单'] / total * 100).round(1)
    df['3折以内占比'] = (df['三折以内'] / total * 100).round(1)
    df['3~5折占比'] = (df['三至五折'] / total * 100).round(1)
    df['5~7折占比'] = (df['五至七折'] / total * 100).round(1)
    df['7折以上占比'] = (df['七折以上'] / total * 100).round(1)

    return df


def query_funnel_metrics(dates: list) -> pd.DataFrame:
    """模块4: 漏斗转化率"""
    print("\n【模块4】查询漏斗转化...")

    date_list = "'" + "','".join(dates) + "'"

    sql = f"""
    SELECT
        dt AS 日期,
        COUNT(DISTINCT CASE WHEN screen_name = 'menu' THEN user_no END) AS menu_uv,
        COUNT(DISTINCT CASE WHEN screen_name = 'productdetail' THEN user_no END) AS productdetail_uv,
        COUNT(DISTINCT CASE WHEN screen_name = 'confirmorder' THEN user_no END) AS confirmorder_uv,
        COUNT(DISTINCT CASE WHEN screen_name = 'orderdetail' THEN user_no END) AS orderdetail_uv
    FROM dw_dws.dws_mg_log_user_screen_name_d_1d
    WHERE dt IN ({date_list})
      AND screen_name IN ('menu', 'productdetail', 'confirmorder', 'orderdetail')
    GROUP BY dt
    ORDER BY dt
    """

    result = run_sql(sql)
    if not result:
        return pd.DataFrame()

    headers = result[0]
    data = result[1:]
    df = pd.DataFrame(data, columns=headers)

    # 转换数据类型
    for col in ['menu_uv', 'productdetail_uv', 'confirmorder_uv', 'orderdetail_uv']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 计算转化率
    df['Menu转化率'] = (df['productdetail_uv'] / df['menu_uv'] * 100).round(1)
    df['商品详情页转化率'] = (df['confirmorder_uv'] / df['productdetail_uv'] * 100).round(1)
    df['确认订单转化率'] = (df['orderdetail_uv'] / df['confirmorder_uv'] * 100).round(1)

    return df


def query_product_penetration(dates: list) -> pd.DataFrame:
    """模块5: 核心商品渗透率 - 使用汇总表"""
    print("\n【模块5】查询核心商品渗透...")

    date_list = "'" + "','".join(dates) + "'"

    # 核心商品关键词
    products = ['Coconut', 'Cold Brew', 'Pineapple', 'Matcha', 'Velvet']

    # 使用汇总表计算，按 spu_name 匹配
    product_cases = []
    for p in products:
        product_cases.append(f"SUM(CASE WHEN spu_name LIKE '%{p}%' THEN order_cnt ELSE 0 END) AS `{p}_orders`")

    product_sql = ",\n        ".join(product_cases)

    sql = f"""
    SELECT
        dt AS 日期,
        SUM(order_cnt) AS 总订单数,
        {product_sql}
    FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
    WHERE tenant = 'LKUS'
      AND one_category_name = 'Drink'
      AND shop_name NOT IN {EXCLUDED_SHOPS}
      AND dt IN ({date_list})
    GROUP BY dt
    ORDER BY dt
    """

    result = run_sql(sql)
    if not result:
        return pd.DataFrame()

    headers = result[0]
    data = result[1:]
    df = pd.DataFrame(data, columns=headers)

    # 转换数据类型
    df['总订单数'] = pd.to_numeric(df['总订单数'], errors='coerce').fillna(0)

    # 计算渗透率（用订单占比代替用户渗透率）
    for p in products:
        col = f'{p}_orders'
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df[f'{p}渗透率'] = (df[col] / df['总订单数'] * 100).round(1)

    return df


def calculate_dod_change(current: float, previous: float) -> str:
    """计算日环比"""
    if previous == 0 or pd.isna(previous) or pd.isna(current):
        return "N/A"
    change = (current - previous) / previous * 100
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.1f}%"


def generate_daily_report(dates: list):
    """生成完整日报"""
    print(f"\n{'='*60}")
    print(f"Lucky US 日报 - {dates[-1]}")
    print(f"对比周期: {dates[0]} ~ {dates[-1]}")
    print(f"{'='*60}")

    # 收集所有数据
    business_df = query_business_metrics(dates)
    user_df = query_user_metrics(dates)
    category_df = query_category_metrics(dates)
    funnel_df = query_funnel_metrics(dates)
    product_df = query_product_penetration(dates)

    # 生成 Markdown 报告
    output = []
    output.append(f"# Lucky US 日报")
    output.append(f"\n**报告日期**: {dates[-1]}")
    output.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 模块1: 业务结果
    output.append("\n## 一、业务结果")
    if not business_df.empty:
        output.append("\n| 指标 | " + " | ".join(dates) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in dates]) + "|------|")

        metrics = [
            ('杯量', '杯量', ','),
            ('店日均杯量', '店日均杯量', '.0f'),
            ('单杯实收', '单杯实收', '$'),
        ]

        for name, col, fmt in metrics:
            if col in business_df.columns:
                values = business_df[col].tolist()
                if fmt == '$':
                    formatted = [f"${v:.2f}" for v in values]
                elif fmt == ',':
                    formatted = [f"{int(v):,}" for v in values]
                elif fmt == '.0f':
                    formatted = [f"{int(v)}" for v in values]
                else:
                    formatted = [f"{v}" for v in values]
                dod = calculate_dod_change(values[-1], values[-2]) if len(values) >= 2 else "N/A"
                output.append(f"| {name} | " + " | ".join(formatted) + f" | {dod} |")
    else:
        output.append("\n暂无数据")

    # 模块2: 渠道（暂时跳过）
    output.append("\n## 二、渠道")
    output.append("\n暂时跳过，后续补充")

    # 模块3: 用户
    output.append("\n## 三、用户")
    if not user_df.empty:
        output.append("\n| 指标 | " + " | ".join(dates) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in dates]) + "|------|")

        user_metrics = [
            ('注册用户数', '注册用户数', ','),
            ('新客数', '新客数', ','),
            ('新客占比', '新客占比', '%'),
            ('店日均新客', '店日均新客', '.1f'),
            ('新客7日留存率', '新客7日留存率', '%'),
            ('老客数', '老客数', ','),
            ('老客占比', '老客占比', '%'),
            ('店日均老客', '店日均老客', '.1f'),
            ('老客7日留存率', '老客7日留存率', '%'),
        ]

        for name, col, fmt in user_metrics:
            if col in user_df.columns:
                values = user_df[col].tolist()
                if fmt == '%':
                    formatted = [f"{v:.1f}%" if not pd.isna(v) else "N/A" for v in values]
                elif fmt == ',':
                    formatted = [f"{int(v):,}" if not pd.isna(v) else "N/A" for v in values]
                elif fmt == '.1f':
                    formatted = [f"{v:.1f}" if not pd.isna(v) else "N/A" for v in values]
                else:
                    formatted = [f"{v}" for v in values]
                dod = calculate_dod_change(values[-1], values[-2]) if len(values) >= 2 else "N/A"
                output.append(f"| {name} | " + " | ".join(formatted) + f" | {dod} |")
    else:
        output.append("\n暂无数据")

    # 模块4: 品类
    output.append("\n## 四、品类")

    # 折扣分布
    output.append("\n### 折扣分布")
    if not category_df.empty:
        output.append("\n| 指标 | " + " | ".join(dates) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in dates]) + "|------|")

        discount_metrics = [
            ('平均折扣率', '平均折扣率', '.1%'),
            ('0.99占比', '0.99占比', '%'),
            ('3折以内占比', '3折以内占比', '%'),
            ('3~5折占比', '3~5折占比', '%'),
            ('5~7折占比', '5~7折占比', '%'),
            ('7折以上占比', '7折以上占比', '%'),
        ]

        for name, col, fmt in discount_metrics:
            if col in category_df.columns:
                values = category_df[col].tolist()
                if fmt == '.1%':
                    formatted = [f"{v*100:.1f}%" if not pd.isna(v) else "N/A" for v in values]
                elif fmt == '%':
                    formatted = [f"{v:.1f}%" if not pd.isna(v) else "N/A" for v in values]
                else:
                    formatted = [f"{v}" for v in values]
                dod = calculate_dod_change(values[-1], values[-2]) if len(values) >= 2 else "N/A"
                output.append(f"| {name} | " + " | ".join(formatted) + f" | {dod} |")
    else:
        output.append("\n暂无数据")

    # 漏斗转化
    output.append("\n### 漏斗转化")
    if not funnel_df.empty:
        output.append("\n| 指标 | " + " | ".join(dates) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in dates]) + "|------|")

        funnel_metrics = [
            ('Menu→商品详情', 'Menu转化率', '%'),
            ('商品详情→确认订单', '商品详情页转化率', '%'),
            ('确认订单→支付成功', '确认订单转化率', '%'),
        ]

        for name, col, fmt in funnel_metrics:
            if col in funnel_df.columns:
                values = funnel_df[col].tolist()
                formatted = [f"{v:.1f}%" if not pd.isna(v) else "N/A" for v in values]
                dod = calculate_dod_change(values[-1], values[-2]) if len(values) >= 2 else "N/A"
                output.append(f"| {name} | " + " | ".join(formatted) + f" | {dod} |")
    else:
        output.append("\n暂无数据")

    # 模块5: 核心商品渗透
    output.append("\n## 五、核心商品渗透（订单占比）")
    if not product_df.empty:
        output.append("\n| 商品 | " + " | ".join(dates) + " | 环比 |")
        output.append("|------|" + "|".join(["------" for _ in dates]) + "|------|")

        products = ['Coconut', 'Cold Brew', 'Pineapple', 'Matcha', 'Velvet']
        for p in products:
            col = f'{p}渗透率'
            if col in product_df.columns:
                values = product_df[col].tolist()
                formatted = [f"{v:.1f}%" if not pd.isna(v) else "N/A" for v in values]
                dod = calculate_dod_change(values[-1], values[-2]) if len(values) >= 2 else "N/A"
                output.append(f"| {p} | " + " | ".join(formatted) + f" | {dod} |")
    else:
        output.append("\n暂无数据")

    # 写入文件
    report_content = "\n".join(output)
    report_file = f"daily_report_{dates[-1]}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"\n{'='*60}")
    print(f"日报已保存到: {report_file}")
    print(f"{'='*60}")

    # 也打印到控制台
    print("\n" + report_content)

    # 保存原始数据
    if not business_df.empty:
        business_df.to_csv('daily_business.csv', index=False)
    if not user_df.empty:
        user_df.to_csv('daily_user.csv', index=False)
    if not category_df.empty:
        category_df.to_csv('daily_category.csv', index=False)
    if not funnel_df.empty:
        funnel_df.to_csv('daily_funnel.csv', index=False)
    if not product_df.empty:
        product_df.to_csv('daily_product.csv', index=False)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Lucky US 日报生成工具')
    parser.add_argument('-n', '--num-days', type=int, default=3,
                        help='分析最近N天数据 (默认: 3)')
    parser.add_argument('-d', '--dates', nargs='+',
                        help='指定日期列表，格式: YYYY-MM-DD (例如: 2026-02-02 2026-02-03 2026-02-04)')

    args = parser.parse_args()

    if args.dates:
        dates = args.dates
    else:
        dates = get_recent_dates(args.num_days)

    print(f"分析日期: {dates}")

    # 生成日报
    generate_daily_report(dates)


if __name__ == "__main__":
    main()
