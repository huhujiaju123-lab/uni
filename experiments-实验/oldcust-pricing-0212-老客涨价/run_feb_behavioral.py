"""2月月报：行为标签分组查询（来访未购 等）"""
import json, time, urllib.request, csv, os

# Auth (same as run_feb_monthly.py)
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

EXP_START = '2026-02-12'
EXP_END_NEXT = '2026-03-01'
DT_LATEST = '2026-02-28'
REP3_CUTOFF = '2026-02-25'
REP7_CUTOFF = '2026-02-21'
OUT = '/Users/xiaoxiao/Downloads/feb_monthly'
os.makedirs(OUT, exist_ok=True)

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
# 来访未购 CTE: 在0212实验用户中，标记来访未购标签
# ============================================================
CTE_BEHAVIORAL = f"""WITH grp_users AS (
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
visit_no_buy AS (
    SELECT DISTINCT g2.user_no
    FROM dw_ads.ads_marketing_t_user_group_d_his g2
    WHERE g2.tenant = 'LKUS' AND g2.dt = '{DT_LATEST}'
        AND g2.group_name = '0212来访未购'
),
grp_vnb AS (
    SELECT gu.user_no, gu.grp
    FROM grp_users gu
    INNER JOIN visit_no_buy vnb ON gu.user_no = vnb.user_no
)"""

queries = {
    'D_来访未购_用户数.csv': {
        'sql': CTE_BEHAVIORAL + """
            SELECT grp, COUNT(*) AS total_users
            FROM grp_vnb GROUP BY grp ORDER BY grp""",
        'wait': 8
    },
    'D_来访未购_订单指标.csv': {
        'sql': CTE_BEHAVIORAL + f"""
            SELECT gu.grp,
                COUNT(DISTINCT gu.user_no) AS total_users,
                COUNT(DISTINCT o.user_no) AS order_users,
                COUNT(DISTINCT o.id) AS order_cnt,
                ROUND(SUM(o.pay_money), 2) AS revenue,
                ROUND(COUNT(DISTINCT o.user_no) * 100.0 / COUNT(DISTINCT gu.user_no), 2) AS conversion_rate,
                ROUND(SUM(o.pay_money) / NULLIF(COUNT(DISTINCT o.user_no), 0), 2) AS arpu_buyer
            FROM grp_vnb gu
            LEFT JOIN ods_luckyus_sales_order.v_order o
                ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
                AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
                AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
            GROUP BY gu.grp ORDER BY gu.grp""",
        'wait': 10
    },
    'D_来访未购_杯量.csv': {
        'sql': CTE_BEHAVIORAL + f""",
            exp_orders AS (
                SELECT o.id AS order_id, gu.grp
                FROM grp_vnb gu INNER JOIN ods_luckyus_sales_order.v_order o
                ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
                AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
                AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT eo.grp,
                SUM(item.sku_num) AS cups,
                ROUND(SUM(item.pay_money), 2) AS item_revenue,
                ROUND(SUM(item.pay_money) / NULLIF(SUM(item.sku_num), 0), 2) AS unit_price
            FROM exp_orders eo INNER JOIN ods_luckyus_sales_order.t_order_item item
                ON eo.order_id = item.order_id
            GROUP BY eo.grp ORDER BY eo.grp""",
        'wait': 15
    },
    'D_来访未购_3日复购.csv': {
        'sql': CTE_BEHAVIORAL + f""",
            user_daily AS (
                SELECT DISTINCT gu.grp, gu.user_no, DATE(o.create_time) AS order_date
                FROM grp_vnb gu INNER JOIN ods_luckyus_sales_order.v_order o
                ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
                AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
                AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2'))
            SELECT a.grp,
                COUNT(DISTINCT a.user_no) AS buyers,
                COUNT(DISTINCT b.user_no) AS repurchase_users,
                ROUND(COUNT(DISTINCT b.user_no) * 100.0 / NULLIF(COUNT(DISTINCT a.user_no), 0), 2) AS repurchase_rate_3d
            FROM user_daily a LEFT JOIN user_daily b ON a.user_no = b.user_no AND a.grp = b.grp
                AND b.order_date > a.order_date AND DATEDIFF(b.order_date, a.order_date) <= 3
            WHERE a.order_date <= '{REP3_CUTOFF}'
            GROUP BY a.grp ORDER BY a.grp""",
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
