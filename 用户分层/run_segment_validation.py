"""分群小实验前置检验：基线特征 + SRM
对每个生命周期段检验3组是否可比
"""
import json, time, urllib.request, csv, os

COOKIES = 'iluckyauth_session_prod=MTc3MjE3OTQxM3xOd3dBTkVsQlVVMVJXRXhQV0V4SU0wRk1WMVV5UzBOUVFsVkZOVkExTnpZek5UZEJSMHBFTjFoR1JGbEVWVVJSVGtOUE0weFhXVkU9fEyRkHDEaTpszGHX5A3YRFH6OB_GFfbl_ujhLLcQkZTH; LK_PROD.US_ILUCKYADMINWEB_OAUTH_UID=d9e3275f-bfb6-4b06-beaa-4dfd223c8468; LK_PROD.US_ILUCKYADMINWEB_SID=4lnBwaNugUay97ExdOMknkkGgL_W1jtnfdK-90JQHnlzXyp5mFgsRuSd5oceD1WNKrMJNzhWCa3m_Z3KB_HxWpuPY6o5C4O2_qISxbL9y_JtX9zL7lwKGfNb4bqFf7SyYNVc9Z-A5xiBiACSfmwBROAZIhvmURMyENDMMpjIlmQ='
JWT = 'eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFMyNTYifQ.eyJyb2wiOnsiQUxMIjpbNF0sIkN5YmVyRGF0YSI6WzRdfSwianRpIjoiMTAwMSw0NyIsImlzcyI6IlNuYWlsQ2xpbWIiLCJpYXQiOjE3NzI0MjA0NDksInN1YiI6IuadjuWutemchCxudWxsLGxpeGlhb3hpYW8iLCJhdWQiOiJbe1wicm9sZUlkXCI6NCxcInZlcnNpb25OYW1lXCI6XCJDeWJlckRhdGFcIixcInZlcnNpb25JZFwiOjMsXCJyb2xlTmFtZVwiOlwiRGF0YUJhc2ljUm9sZVwifV0ifQ.gff2zbRZAnVdxhaoOeBENESv_x0rIuX0Rj40_DGMBxc'
BASE = 'https://idpcd.luckincoffee.us/api'
HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'content-type': 'application/json; charset=UTF-8',
    'Cookie': COOKIES, 'jwttoken': JWT,
    'productkey': 'CyberData', 'origin': 'https://idpcd.luckincoffee.us',
}
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

# 带生命周期的CTE
CTE = """WITH grp_users_raw AS (
    SELECT DISTINCT g.user_no,
        CASE WHEN g.group_name LIKE '%涨价组1%' THEN '涨价组1'
             WHEN g.group_name LIKE '%涨价组2%' THEN '涨价组2'
             WHEN g.group_name LIKE '%对照组3%' THEN '对照组3' END AS grp
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN (SELECT DISTINCT user_no FROM ods_luckyus_sales_order.v_order
        WHERE status = 90 AND INSTR(tenant, 'IQ') = 0 AND create_time < '2026-02-12'
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')) hist ON g.user_no = hist.user_no
    WHERE g.tenant = 'LKUS' AND g.dt = '2026-02-28'
        AND (g.group_name LIKE '%0212价格实验%涨价组1%'
          OR g.group_name LIKE '%0212价格实验%涨价组2%'
          OR g.group_name LIKE '%0212价格实验%对照组3%')
),
first_orders AS (
    SELECT user_no, MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_order_dt
    FROM ods_luckyus_sales_order.v_order
    WHERE status = 90 AND INSTR(tenant, 'IQ') = 0
        AND create_time < '2026-02-12'
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY user_no
),
grp_users AS (
    SELECT gu.user_no, gu.grp,
        DATEDIFF('2026-02-12', fo.first_order_dt) AS days_since_first,
        CASE
            WHEN DATEDIFF('2026-02-12', fo.first_order_dt) <= 15 THEN '0-15天'
            WHEN DATEDIFF('2026-02-12', fo.first_order_dt) <= 30 THEN '16-30天'
            ELSE '31天+'
        END AS lifecycle
    FROM grp_users_raw gu
    LEFT JOIN first_orders fo ON gu.user_no = fo.user_no
)"""

queries = {
    # 分段基线：实验前90天消费特征
    'V_分段基线特征.csv': {
        'sql': CTE + """,
hist AS (
    SELECT gu.grp, gu.lifecycle, gu.user_no,
        COUNT(DISTINCT o.id) AS order_cnt,
        ROUND(SUM(o.pay_money), 2) AS total_spend,
        ROUND(AVG(o.pay_money), 2) AS avg_aov
    FROM grp_users gu
    LEFT JOIN ods_luckyus_sales_order.v_order o
        ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2025-11-14' AND o.create_time < '2026-02-12'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY gu.grp, gu.lifecycle, gu.user_no
)
SELECT grp, lifecycle,
    COUNT(*) AS total_users,
    COUNT(CASE WHEN order_cnt > 0 THEN 1 END) AS active_users,
    ROUND(COUNT(CASE WHEN order_cnt > 0 THEN 1 END) * 100.0 / COUNT(*), 2) AS active_rate,
    ROUND(AVG(order_cnt), 4) AS avg_orders,
    ROUND(AVG(CASE WHEN order_cnt > 0 THEN total_spend END), 2) AS avg_spend,
    ROUND(AVG(CASE WHEN order_cnt > 0 THEN avg_aov END), 2) AS avg_aov
FROM hist
GROUP BY grp, lifecycle
ORDER BY lifecycle, grp""",
        'wait': 15
    },

    # 来访未购分段基线
    'V_来访未购基线.csv': {
        'sql': """WITH grp_users AS (
    SELECT DISTINCT g.user_no,
        CASE WHEN g.group_name LIKE '%涨价组1%' THEN '涨价组1'
             WHEN g.group_name LIKE '%涨价组2%' THEN '涨价组2'
             WHEN g.group_name LIKE '%对照组3%' THEN '对照组3' END AS grp
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    INNER JOIN (SELECT DISTINCT user_no FROM ods_luckyus_sales_order.v_order
        WHERE status = 90 AND INSTR(tenant, 'IQ') = 0 AND create_time < '2026-02-12'
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')) hist ON g.user_no = hist.user_no
    WHERE g.tenant = 'LKUS' AND g.dt = '2026-02-28'
        AND (g.group_name LIKE '%0212价格实验%涨价组1%'
          OR g.group_name LIKE '%0212价格实验%涨价组2%'
          OR g.group_name LIKE '%0212价格实验%对照组3%')
),
vnb AS (
    SELECT DISTINCT user_no FROM dw_ads.ads_marketing_t_user_group_d_his
    WHERE tenant = 'LKUS' AND dt = '2026-02-28' AND group_name = '0212来访未购'
),
grp_vnb AS (
    SELECT gu.user_no, gu.grp FROM grp_users gu INNER JOIN vnb ON gu.user_no = vnb.user_no
),
hist AS (
    SELECT gv.grp, gv.user_no,
        COUNT(DISTINCT o.id) AS order_cnt,
        ROUND(SUM(o.pay_money), 2) AS total_spend,
        ROUND(AVG(o.pay_money), 2) AS avg_aov
    FROM grp_vnb gv
    LEFT JOIN ods_luckyus_sales_order.v_order o
        ON gv.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
        AND o.create_time >= '2025-11-14' AND o.create_time < '2026-02-12'
        AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY gv.grp, gv.user_no
)
SELECT grp,
    COUNT(*) AS total_users,
    COUNT(CASE WHEN order_cnt > 0 THEN 1 END) AS active_users,
    ROUND(COUNT(CASE WHEN order_cnt > 0 THEN 1 END) * 100.0 / COUNT(*), 2) AS active_rate,
    ROUND(AVG(order_cnt), 4) AS avg_orders,
    ROUND(AVG(CASE WHEN order_cnt > 0 THEN total_spend END), 2) AS avg_spend,
    ROUND(AVG(CASE WHEN order_cnt > 0 THEN avg_aov END), 2) AS avg_aov
FROM hist
GROUP BY grp ORDER BY grp""",
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
