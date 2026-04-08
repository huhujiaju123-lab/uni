"""2月涨价实验月报：全量数据查询脚本
覆盖：大实验整体 + 分生命周期小实验 + 行为标签探索
日期范围：2026-02-12 ~ 2026-02-28
"""
import json, time, urllib.request, csv, os

# ============================================================
# Auth (2026-03-01 刷新)
# ============================================================
COOKIES = 'iluckyauth_session_prod=MTc3MjE3OTQxM3xOd3dBTkVsQlVVMVJXRXhQV0V4SU0wRk1WMVV5UzBOUVFsVkZOVkExTnpZek5UZEJSMHBFTjFoR1JGbEVWVVJSVGtOUE0weFhXVkU9fEyRkHDEaTpszGHX5A3YRFH6OB_GFfbl_ujhLLcQkZTH; LK_PROD.US_ILUCKYADMINWEB_OAUTH_UID=d9e3275f-bfb6-4b06-beaa-4dfd223c8468; LK_PROD.US_ILUCKYADMINWEB_SID=4lnBwaNugUay97ExdOMknkkGgL_W1jtnfdK-90JQHnlzXyp5mFgsRuSd5oceD1WNKrMJNzhWCa3m_Z3KB_HxWpuPY6o5C4O2_qISxbL9y_JtX9zL7lwKGfNb4bqFf7SyYNVc9Z-A5xiBiACSfmwBROAZIhvmURMyENDMMpjIlmQ='
JWT = 'eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFMyNTYifQ.eyJyb2wiOnsiQUxMIjpbNF0sIkN5YmVyRGF0YSI6WzRdfSwianRpIjoiMTAwMSw0NyIsImlzcyI6IlNuYWlsQ2xpbWIiLCJpYXQiOjE3NzI0MjA0NDksInN1YiI6IuadjuWutemchCxudWxsLGxpeGlhb3hpYW8iLCJhdWQiOiJbe1wicm9sZUlkXCI6NCxcInZlcnNpb25OYW1lXCI6XCJDeWJlckRhdGFcIixcInZlcnNpb25JZFwiOjMsXCJyb2xlTmFtZVwiOlwiRGF0YUJhc2ljUm9sZVwifV0ifQ.gff2zbRZAnVdxhaoOeBENESv_x0rIuX0Rj40_DGMBxc'
BASE = 'https://idpcd.luckincoffee.us/api'
HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'content-type': 'application/json; charset=UTF-8',
    'Cookie': COOKIES, 'jwttoken': JWT,
    'productkey': 'CyberData',
    'origin': 'https://idpcd.luckincoffee.us',
}

# ============================================================
# 配置
# ============================================================
EXP_START = '2026-02-12'
EXP_END = '2026-02-28'
EXP_END_NEXT = '2026-03-01'
DT_LATEST = '2026-02-28'
REP3_CUTOFF = '2026-02-25'  # 3日复购窗口: 2/25+3天=2/28
REP7_CUTOFF = '2026-02-21'  # 7日复购窗口: 2/21+7天=2/28

OUT = '/Users/xiaoxiao/Downloads/feb_monthly'
os.makedirs(OUT, exist_ok=True)

# ============================================================
# API helpers
# ============================================================
def api(path, body):
    body['_t'] = int(time.time() * 1000)
    data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(f'{BASE}/{path}', data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def run_sql(sql, wait=8, max_retries=15):
    r = api('dev/task/run', {
        'tenantId': '1001', 'userId': '47',
        'projectId': '1906904360294313985', 'resourceGroupId': 1,
        'taskId': '2025093402876882945', 'variables': {},
        'sqlStatement': sql, 'env': 5
    })
    tid = r['data']
    print(f'  taskInstanceId: {tid}')
    time.sleep(wait)
    for attempt in range(max_retries):
        r2 = api('logger/getQueryLog', {
            'tenantId': '1001', 'userId': '47',
            'projectId': '1906904360294313985', 'env': 5,
            'taskInstanceId': tid
        })
        if r2.get('code') == '200' and r2.get('data'):
            items = r2['data']
            if items and items[0].get('columns'):
                return items[0]['columns']
        print(f'  waiting... (attempt {attempt+2})')
        time.sleep(5)
    raise Exception(f'Query timeout for {tid}')

def save_csv(rows, filename):
    path = os.path.join(OUT, filename)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
    print(f'  -> {path} ({len(rows)-1} rows)')
    return path

# ============================================================
# 公共 CTE: 基础分组（剔除新客）
# ============================================================
CTE_BASE = f"""WITH grp_users AS (
    SELECT DISTINCT g.user_no,
        CASE WHEN g.group_name LIKE '%涨价组1%' THEN '涨价组1'
             WHEN g.group_name LIKE '%涨价组2%' THEN '涨价组2'
             WHEN g.group_name LIKE '%对照组3%' THEN '对照组3' END AS grp
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN (SELECT DISTINCT user_no FROM ods_luckyus_sales_order.v_order
        WHERE status = 90 AND INSTR(tenant, 'IQ') = 0 AND create_time < '{EXP_START}'
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')) hist ON g.user_no = hist.user_no
    WHERE g.tenant = 'LKUS' AND g.dt = '{DT_LATEST}'
        AND (g.group_name LIKE '%0212价格实验%涨价组1%'
          OR g.group_name LIKE '%0212价格实验%涨价组2%'
          OR g.group_name LIKE '%0212价格实验%对照组3%')
)"""

# 公共 CTE: 带生命周期标签
CTE_LIFECYCLE = f"""WITH grp_users_raw AS (
    SELECT DISTINCT g.user_no,
        CASE WHEN g.group_name LIKE '%涨价组1%' THEN '涨价组1'
             WHEN g.group_name LIKE '%涨价组2%' THEN '涨价组2'
             WHEN g.group_name LIKE '%对照组3%' THEN '对照组3' END AS grp
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN (SELECT DISTINCT user_no FROM ods_luckyus_sales_order.v_order
        WHERE status = 90 AND INSTR(tenant, 'IQ') = 0 AND create_time < '{EXP_START}'
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')) hist ON g.user_no = hist.user_no
    WHERE g.tenant = 'LKUS' AND g.dt = '{DT_LATEST}'
        AND (g.group_name LIKE '%0212价格实验%涨价组1%'
          OR g.group_name LIKE '%0212价格实验%涨价组2%'
          OR g.group_name LIKE '%0212价格实验%对照组3%')
),
first_orders AS (
    SELECT user_no, MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_order_dt
    FROM ods_luckyus_sales_order.v_order
    WHERE status = 90 AND INSTR(tenant, 'IQ') = 0
        AND create_time < '{EXP_START}'
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY user_no
),
grp_users AS (
    SELECT gu.user_no, gu.grp,
        DATEDIFF('{EXP_START}', fo.first_order_dt) AS days_since_first,
        CASE
            WHEN DATEDIFF('{EXP_START}', fo.first_order_dt) <= 15 THEN '0-15天'
            WHEN DATEDIFF('{EXP_START}', fo.first_order_dt) <= 30 THEN '16-30天'
            ELSE '31天+'
        END AS lifecycle
    FROM grp_users_raw gu
    LEFT JOIN first_orders fo ON gu.user_no = fo.user_no
)"""

# ============================================================
# Part A: 整体大实验 (7 queries)
# ============================================================
queries_overall = {
    'A_各组用户数.csv': {
        'sql': CTE_BASE + " SELECT grp, COUNT(*) AS total_users FROM grp_users GROUP BY grp ORDER BY grp",
        'wait': 6
    },
    'A_每日订单.csv': {
        'sql': CTE_BASE + f""" SELECT gu.grp, DATE(o.create_time) AS dt,
            COUNT(DISTINCT o.user_no) AS order_users, COUNT(DISTINCT o.id) AS order_cnt,
            ROUND(SUM(o.pay_money), 2) AS revenue
            FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
            ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
            GROUP BY gu.grp, DATE(o.create_time) ORDER BY dt, grp""",
        'wait': 10
    },
    'A_每日访问.csv': {
        'sql': CTE_BASE + f""" SELECT gu.grp, dau.dt, COUNT(DISTINCT dau.user_no) AS visit_users
            FROM grp_users gu INNER JOIN dw_dws.dws_mg_log_user_screen_name_d_1d dau
            ON gu.user_no = dau.user_no AND dau.dt >= '{EXP_START}' AND dau.dt <= '{EXP_END}'
            GROUP BY gu.grp, dau.dt ORDER BY dau.dt, gu.grp""",
        'wait': 12
    },
    'A_每日杯量.csv': {
        'sql': CTE_BASE + f""", exp_orders AS (
            SELECT o.id AS order_id, gu.grp, DATE(o.create_time) AS dt
            FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
            ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT eo.grp, eo.dt, SUM(item.sku_num) AS cups,
            ROUND(SUM(item.pay_money), 2) AS item_revenue,
            ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS unit_price
            FROM exp_orders eo INNER JOIN ods_luckyus_sales_order.t_order_item item
            ON eo.order_id = item.order_id GROUP BY eo.grp, eo.dt ORDER BY eo.dt, eo.grp""",
        'wait': 18
    },
    'A_汇总指标.csv': {
        'sql': CTE_BASE + f""" SELECT gu.grp, COUNT(DISTINCT o.user_no) AS period_order_users,
            COUNT(DISTINCT o.id) AS period_order_cnt, ROUND(SUM(o.pay_money), 2) AS period_revenue
            FROM grp_users gu LEFT JOIN ods_luckyus_sales_order.v_order o
            ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
            GROUP BY gu.grp ORDER BY gu.grp""",
        'wait': 8
    },
    'A_3日复购.csv': {
        'sql': CTE_BASE + f""", user_daily AS (
            SELECT DISTINCT gu.grp, gu.user_no, DATE(o.create_time) AS order_date
            FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
            ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT a.grp, a.order_date, COUNT(DISTINCT a.user_no) AS day_buyers,
            COUNT(DISTINCT b.user_no) AS repurchase_users,
            ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_3d
            FROM user_daily a LEFT JOIN user_daily b ON a.user_no = b.user_no AND a.grp = b.grp
            AND b.order_date > a.order_date AND DATEDIFF(b.order_date, a.order_date) <= 3
            WHERE a.order_date <= '{REP3_CUTOFF}' GROUP BY a.grp, a.order_date ORDER BY a.order_date, a.grp""",
        'wait': 15
    },
    'A_7日复购.csv': {
        'sql': CTE_BASE + f""", user_daily AS (
            SELECT DISTINCT gu.grp, gu.user_no, DATE(o.create_time) AS order_date
            FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
            ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT a.grp, a.order_date, COUNT(DISTINCT a.user_no) AS day_buyers,
            COUNT(DISTINCT b.user_no) AS repurchase_users,
            ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_7d
            FROM user_daily a LEFT JOIN user_daily b ON a.user_no = b.user_no AND a.grp = b.grp
            AND b.order_date > a.order_date AND DATEDIFF(b.order_date, a.order_date) <= 7
            WHERE a.order_date <= '{REP7_CUTOFF}' GROUP BY a.grp, a.order_date ORDER BY a.order_date, a.grp""",
        'wait': 15
    },
}

# ============================================================
# Part B: 分生命周期小实验 (4 queries)
# ============================================================
queries_lifecycle = {
    'B_分段用户数.csv': {
        'sql': CTE_LIFECYCLE + """
            SELECT grp, lifecycle, COUNT(*) AS total_users
            FROM grp_users GROUP BY grp, lifecycle ORDER BY lifecycle, grp""",
        'wait': 10
    },
    'B_分段订单指标.csv': {
        'sql': CTE_LIFECYCLE + f"""
            SELECT gu.grp, gu.lifecycle,
                COUNT(DISTINCT gu.user_no) AS total_users,
                COUNT(DISTINCT o.user_no) AS order_users,
                COUNT(DISTINCT o.id) AS order_cnt,
                ROUND(SUM(o.pay_money), 2) AS revenue,
                ROUND(COUNT(DISTINCT o.user_no) * 100.0 / COUNT(DISTINCT gu.user_no), 2) AS conversion_rate,
                ROUND(SUM(o.pay_money) / NULLIF(COUNT(DISTINCT o.user_no), 0), 2) AS arpu_buyer
            FROM grp_users gu
            LEFT JOIN ods_luckyus_sales_order.v_order o
                ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
                AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
                AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
            GROUP BY gu.grp, gu.lifecycle ORDER BY gu.lifecycle, gu.grp""",
        'wait': 15
    },
    'B_分段杯量.csv': {
        'sql': CTE_LIFECYCLE + f""",
            exp_orders AS (
                SELECT o.id AS order_id, gu.grp, gu.lifecycle
                FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
                ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
                AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
                AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT eo.grp, eo.lifecycle,
                SUM(item.sku_num) AS cups,
                ROUND(SUM(item.pay_money), 2) AS item_revenue,
                ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS unit_price
            FROM exp_orders eo INNER JOIN ods_luckyus_sales_order.t_order_item item
                ON eo.order_id = item.order_id
            GROUP BY eo.grp, eo.lifecycle ORDER BY eo.lifecycle, eo.grp""",
        'wait': 20
    },
    'B_分段3日复购.csv': {
        'sql': CTE_LIFECYCLE + f""",
            user_daily AS (
                SELECT DISTINCT gu.grp, gu.lifecycle, gu.user_no, DATE(o.create_time) AS order_date
                FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
                ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
                AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
                AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT a.grp, a.lifecycle,
                COUNT(DISTINCT a.user_no) AS buyers,
                COUNT(DISTINCT b.user_no) AS repurchase_users,
                ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_3d
            FROM user_daily a LEFT JOIN user_daily b ON a.user_no = b.user_no AND a.grp = b.grp
                AND b.order_date > a.order_date AND DATEDIFF(b.order_date, a.order_date) <= 3
            WHERE a.order_date <= '{REP3_CUTOFF}'
            GROUP BY a.grp, a.lifecycle ORDER BY a.lifecycle, a.grp""",
        'wait': 18
    },
    'B_分段7日复购.csv': {
        'sql': CTE_LIFECYCLE + f""",
            user_daily AS (
                SELECT DISTINCT gu.grp, gu.lifecycle, gu.user_no, DATE(o.create_time) AS order_date
                FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
                ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
                AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
                AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT a.grp, a.lifecycle,
                COUNT(DISTINCT a.user_no) AS buyers,
                COUNT(DISTINCT b.user_no) AS repurchase_users,
                ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_7d
            FROM user_daily a LEFT JOIN user_daily b ON a.user_no = b.user_no AND a.grp = b.grp
                AND b.order_date > a.order_date AND DATEDIFF(b.order_date, a.order_date) <= 7
            WHERE a.order_date <= '{REP7_CUTOFF}'
            GROUP BY a.grp, a.lifecycle ORDER BY a.lifecycle, a.grp""",
        'wait': 18
    },
}

# ============================================================
# Part C: 探索性查询 - 查看所有0212实验相关分组名
# ============================================================
queries_explore = {
    'C_实验分组名列表.csv': {
        'sql': f"""SELECT DISTINCT group_name, COUNT(DISTINCT user_no) AS user_cnt
            FROM dw_ads.ads_marketing_t_user_group_d_his
            WHERE tenant = 'LKUS' AND dt = '{DT_LATEST}'
                AND group_name LIKE '%0212%'
            GROUP BY group_name ORDER BY group_name""",
        'wait': 8
    },
    'C_券核销_全组.csv': {
        'sql': CTE_BASE + f"""
            SELECT gu.grp, c.coupon_name, c.coupon_denomination,
                COUNT(*) AS issued,
                COUNT(CASE WHEN c.use_status = 1 THEN 1 END) AS used,
                ROUND(COUNT(CASE WHEN c.use_status = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS use_rate
            FROM grp_users gu
            INNER JOIN ods_luckyus_sales_marketing.t_coupon_record c
                ON gu.user_no = c.member_no
                AND c.create_time >= '{EXP_START}' AND c.create_time < '{EXP_END_NEXT}'
            GROUP BY gu.grp, c.coupon_name, c.coupon_denomination
            ORDER BY gu.grp, used DESC""",
        'wait': 12
    },
}

# ============================================================
# 执行
# ============================================================
def run_all(query_groups):
    results = {}
    for group_name, queries in query_groups:
        print(f'\n{"="*60}')
        print(f'  {group_name}')
        print(f'{"="*60}')
        for filename, q in queries.items():
            print(f'\n[{filename}]')
            try:
                rows = run_sql(q['sql'], wait=q['wait'])
                save_csv(rows, filename)
                results[filename] = True
            except Exception as e:
                print(f'  ERROR: {e}')
                results[filename] = False
    return results

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        target = sys.argv[1]
        if target == 'overall':
            run_all([('Part A: 整体大实验', queries_overall)])
        elif target == 'lifecycle':
            run_all([('Part B: 分生命周期', queries_lifecycle)])
        elif target == 'explore':
            run_all([('Part C: 探索性查询', queries_explore)])
        else:
            print(f'Unknown target: {target}. Use: overall, lifecycle, explore')
    else:
        # 全部执行
        results = run_all([
            ('Part A: 整体大实验', queries_overall),
            ('Part B: 分生命周期', queries_lifecycle),
            ('Part C: 探索性查询', queries_explore),
        ])

        print(f'\n{"="*60}')
        print('  执行汇总')
        print(f'{"="*60}')
        for fname, ok in results.items():
            status = 'OK' if ok else 'FAILED'
            print(f'  {status}: {fname}')

        failed = sum(1 for ok in results.values() if not ok)
        print(f'\n  总计: {len(results)} 个查询, {len(results)-failed} 成功, {failed} 失败')
