"""批量执行 0212 涨价实验 SQL 查询并保存 CSV"""
import json, time, urllib.request, csv, os

COOKIES = 'iluckyauth_session_prod=MTc3MTk4ODI1MXxOd3dBTkRaWE5EVXlUVEkwTTBaSVdVRkNTRFkyUlZoYVJVSk9Ta05EVVVGTlJsVlBUek5UVlRVM05sSlVWbGd6V1VwSlNFbzJWRkU9fB0vQr_1EqiawoixRyFifVKNrEWKHZx7sSH9C8ZaIozl; LK_PROD.US_ILUCKYADMINWEB_OAUTH_UID=d9e3275f-bfb6-4b06-beaa-4dfd223c8468; LK_PROD.US_ILUCKYADMINWEB_SID=4lnBwaNugUay97ExdOMknkkGgL_W1jtnfdK-90JQHnlzXyp5mFgsRuSd5oceD1WNKrMJNzhWCa3m_Z3KB_HxWpuPY6o5C4O2_qISxbL9y_JtX9zL7lwKGfNb4bqFf7SyYNVc9Z-A5xiBiACSfmwBROAZIhvmURMyENDMMpjIlmQ='
JWT = 'eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFMyNTYifQ.eyJyb2wiOnsiQUxMIjpbNF0sIkN5YmVyRGF0YSI6WzRdfSwianRpIjoiMTAwMSw0NyIsImlzcyI6IlNuYWlsQ2xpbWIiLCJpYXQiOjE3NzIwNzE2MjIsInN1YiI6IuadjuWutemchCxudWxsLGxpeGlhb3hpYW8iLCJhdWQiOiJbe1wicm9sZUlkXCI6NCxcInZlcnNpb25OYW1lXCI6XCJDeWJlckRhdGFcIixcInZlcnNpb25JZFwiOjMsXCJyb2xlTmFtZVwiOlwiRGF0YUJhc2ljUm9sZVwifV0ifQ.HlEon-i-yxbBxMvITp1HMxMm8Xb3DEK0AdR6MGrIDCo'
BASE = 'https://idpcd.luckincoffee.us/api'
HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'content-type': 'application/json; charset=UTF-8',
    'Cookie': COOKIES,
    'jwttoken': JWT,
    'productkey': 'CyberData',
    'origin': 'https://idpcd.luckincoffee.us',
}
OUT = '/Users/xiaoxiao/Downloads'

def api(path, body):
    body['_t'] = int(time.time() * 1000)
    data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(f'{BASE}/{path}', data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def run_sql(sql, wait=8, max_retries=10):
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

# ============================================================
# Common CTE
# ============================================================
CTE = """WITH grp_users AS (
    SELECT DISTINCT g.user_no,
        CASE WHEN g.group_name LIKE '%涨价组1%' THEN '涨价组1'
             WHEN g.group_name LIKE '%涨价组2%' THEN '涨价组2'
             WHEN g.group_name LIKE '%对照组3%' THEN '对照组3' END AS grp
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN (SELECT DISTINCT user_no FROM ods_luckyus_sales_order.v_order
        WHERE status = 90 AND INSTR(tenant, 'IQ') = 0 AND create_time < '2026-02-12'
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')) hist ON g.user_no = hist.user_no
    WHERE g.tenant = 'LKUS' AND g.dt = '2026-02-24'
        AND (g.group_name LIKE '%0212价格实验%涨价组1%'
          OR g.group_name LIKE '%0212价格实验%涨价组2%'
          OR g.group_name LIKE '%0212价格实验%对照组3%')
)"""

# ============================================================
queries = {
    '各组老客用户数（剔除新客）.csv': {
        'sql': CTE + " SELECT grp, COUNT(*) AS old_users FROM grp_users GROUP BY grp ORDER BY grp",
        'wait': 6
    },
    '每日订单指标.csv': {
        'sql': CTE + """ SELECT gu.grp, DATE(o.create_time) AS dt,
            COUNT(DISTINCT o.user_no) AS order_users, COUNT(DISTINCT o.id) AS order_cnt,
            ROUND(SUM(o.pay_money), 2) AS revenue
            FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
            ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time >= '2026-02-12' AND o.create_time < '2026-02-25'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
            GROUP BY gu.grp, DATE(o.create_time) ORDER BY dt, grp""",
        'wait': 8
    },
    '每日访问人数.csv': {
        'sql': CTE + """ SELECT gu.grp, dau.dt, COUNT(DISTINCT dau.user_no) AS visit_users
            FROM grp_users gu INNER JOIN dw_dws.dws_mg_log_user_screen_name_d_1d dau
            ON gu.user_no = dau.user_no AND dau.dt >= '2026-02-12' AND dau.dt <= '2026-02-24'
            GROUP BY gu.grp, dau.dt ORDER BY dau.dt, gu.grp""",
        'wait': 10
    },
    '每日杯量与单杯实收.csv': {
        'sql': CTE + """, exp_orders AS (
            SELECT o.id AS order_id, gu.grp, DATE(o.create_time) AS dt
            FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
            ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time >= '2026-02-12' AND o.create_time < '2026-02-25'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT eo.grp, eo.dt, SUM(item.sku_num) AS cups,
            ROUND(SUM(item.pay_money), 2) AS item_revenue,
            ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS unit_price
            FROM exp_orders eo INNER JOIN ods_luckyus_sales_order.t_order_item item
            ON eo.order_id = item.order_id GROUP BY eo.grp, eo.dt ORDER BY eo.dt, eo.grp""",
        'wait': 15
    },
    '汇总期间独立指标.csv': {
        'sql': CTE + """ SELECT gu.grp, COUNT(DISTINCT o.user_no) AS period_order_users,
            COUNT(DISTINCT o.id) AS period_order_cnt, ROUND(SUM(o.pay_money), 2) AS period_revenue
            FROM grp_users gu LEFT JOIN ods_luckyus_sales_order.v_order o
            ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time >= '2026-02-12' AND o.create_time < '2026-02-25'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
            GROUP BY gu.grp ORDER BY gu.grp""",
        'wait': 8
    },
    '3日复购率.csv': {
        'sql': CTE + """, user_daily AS (
            SELECT DISTINCT gu.grp, gu.user_no, DATE(o.create_time) AS order_date
            FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
            ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time >= '2026-02-12' AND o.create_time < '2026-02-25'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT a.grp, a.order_date, COUNT(DISTINCT a.user_no) AS day_buyers,
            COUNT(DISTINCT b.user_no) AS repurchase_users,
            ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_3d
            FROM user_daily a LEFT JOIN user_daily b ON a.user_no = b.user_no AND a.grp = b.grp
            AND b.order_date > a.order_date AND DATEDIFF(b.order_date, a.order_date) <= 3
            WHERE a.order_date <= '2026-02-21' GROUP BY a.grp, a.order_date ORDER BY a.order_date, a.grp""",
        'wait': 12
    },
    '7日复购率.csv': {
        'sql': CTE + """, user_daily AS (
            SELECT DISTINCT gu.grp, gu.user_no, DATE(o.create_time) AS order_date
            FROM grp_users gu INNER JOIN ods_luckyus_sales_order.v_order o
            ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
            AND o.create_time >= '2026-02-12' AND o.create_time < '2026-02-25'
            AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT a.grp, a.order_date, COUNT(DISTINCT a.user_no) AS day_buyers,
            COUNT(DISTINCT b.user_no) AS repurchase_users,
            ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_7d
            FROM user_daily a LEFT JOIN user_daily b ON a.user_no = b.user_no AND a.grp = b.grp
            AND b.order_date > a.order_date AND DATEDIFF(b.order_date, a.order_date) <= 7
            WHERE a.order_date <= '2026-02-17' GROUP BY a.grp, a.order_date ORDER BY a.order_date, a.grp""",
        'wait': 12
    },
}

if __name__ == '__main__':
    for filename, q in queries.items():
        print(f'\n[{filename}]')
        try:
            rows = run_sql(q['sql'], wait=q['wait'])
            save_csv(rows, filename)
        except Exception as e:
            print(f'  ERROR: {e}')
    print('\nDone!')
