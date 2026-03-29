"""2月月报：周六日消费工作日发券实验查询
通过 Weekday Deals 券的 activity_no 映射到实验组
"""
import json, time, urllib.request, csv, os

# Auth (2026-03-01 刷新)
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
REP3_CUTOFF = '2026-02-25'
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

# ============================================================
# 通过 Weekday Deals 券 activity_no 映射实验组
# 涨价组1: LKUSCA118842385500635136 (1,204 users)
# 涨价组2: LKUSCA118842825801867264 (1,201 users)
# 对照组3: LKUSCA118842387245465600 (1,805 users)
# ============================================================
CTE_WEEKEND = f"""WITH weekend_users AS (
    SELECT DISTINCT c.member_no AS user_no,
        CASE
            WHEN c.activity_no = 'LKUSCA118842385500635136' THEN '涨价组1'
            WHEN c.activity_no = 'LKUSCA118842825801867264' THEN '涨价组2'
            WHEN c.activity_no = 'LKUSCA118842387245465600' THEN '对照组3'
        END AS grp
    FROM ods_luckyus_sales_marketing.t_coupon_record c
    WHERE c.activity_no IN (
        'LKUSCA118842385500635136',
        'LKUSCA118842825801867264',
        'LKUSCA118842387245465600'
    )
)"""

queries = {
    # 1. 用户数
    'E_周六日_用户数.csv': {
        'sql': CTE_WEEKEND + """
            SELECT grp, COUNT(DISTINCT user_no) AS total_users
            FROM weekend_users GROUP BY grp ORDER BY grp""",
        'wait': 8
    },
    # 2. 券核销率
    'E_周六日_券核销.csv': {
        'sql': f"""SELECT
                CASE
                    WHEN c.activity_no = 'LKUSCA118842385500635136' THEN '涨价组1'
                    WHEN c.activity_no = 'LKUSCA118842825801867264' THEN '涨价组2'
                    WHEN c.activity_no = 'LKUSCA118842387245465600' THEN '对照组3'
                END AS grp,
                COUNT(*) AS issued,
                SUM(CASE WHEN c.use_status = 1 THEN 1 ELSE 0 END) AS used,
                ROUND(SUM(CASE WHEN c.use_status = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS use_rate,
                COUNT(DISTINCT CASE WHEN c.use_status = 1 THEN c.member_no END) AS used_users
            FROM ods_luckyus_sales_marketing.t_coupon_record c
            WHERE c.activity_no IN (
                'LKUSCA118842385500635136',
                'LKUSCA118842825801867264',
                'LKUSCA118842387245465600'
            )
            GROUP BY grp ORDER BY grp""",
        'wait': 8
    },
    # 3. 订单指标（实验期间所有订单）
    'E_周六日_订单指标.csv': {
        'sql': CTE_WEEKEND + f"""
            SELECT wu.grp,
                COUNT(DISTINCT wu.user_no) AS total_users,
                COUNT(DISTINCT o.user_no) AS order_users,
                COUNT(DISTINCT o.id) AS order_cnt,
                ROUND(SUM(o.pay_money), 2) AS revenue,
                ROUND(COUNT(DISTINCT o.user_no) * 100.0 / COUNT(DISTINCT wu.user_no), 2) AS conversion_rate,
                ROUND(SUM(o.pay_money) / NULLIF(COUNT(DISTINCT o.user_no), 0), 2) AS arpu_buyer
            FROM weekend_users wu
            LEFT JOIN ods_luckyus_sales_order.v_order o
                ON wu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
                AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
                AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
            GROUP BY wu.grp ORDER BY wu.grp""",
        'wait': 10
    },
    # 4. 杯量 & 单杯实收
    'E_周六日_杯量.csv': {
        'sql': CTE_WEEKEND + f""",
            exp_orders AS (
                SELECT o.id AS order_id, wu.grp
                FROM weekend_users wu INNER JOIN ods_luckyus_sales_order.v_order o
                ON wu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
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
    # 5. 3日复购率
    'E_周六日_3日复购.csv': {
        'sql': CTE_WEEKEND + f""",
            user_daily AS (
                SELECT DISTINCT wu.grp, wu.user_no, DATE(o.create_time) AS order_date
                FROM weekend_users wu INNER JOIN ods_luckyus_sales_order.v_order o
                ON wu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
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
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for filename, q in queries.items():
        if target != 'all' and target not in filename:
            continue
        print(f'\n[{filename}]')
        try:
            rows = run_sql(q['sql'], wait=q['wait'])
            save_csv(rows, filename)
        except Exception as e:
            print(f'  ERROR: {e}')
    print('\nDone!')
