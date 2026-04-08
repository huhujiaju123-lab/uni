"""验证实验是否受到非实验券干扰
检查：1. 各组订单的用券情况  2. 非实验券是否均匀分布  3. 实际折扣差异
"""
import json, time, urllib.request, csv, os

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
OUT = '/Users/xiaoxiao/Downloads/feb_monthly'

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

# 基础CTE：实验分组
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

queries = {
    # Q1: 各组订单中用券 vs 无券占比
    # v_order.activity_no 不为空表示使用了券
    'F_订单用券占比.csv': {
        'sql': CTE_BASE + f"""
            SELECT gu.grp,
                COUNT(DISTINCT o.id) AS total_orders,
                COUNT(DISTINCT CASE WHEN o.activity_no IS NOT NULL AND o.activity_no != '' THEN o.id END) AS coupon_orders,
                COUNT(DISTINCT CASE WHEN o.activity_no IS NULL OR o.activity_no = '' THEN o.id END) AS no_coupon_orders,
                ROUND(COUNT(DISTINCT CASE WHEN o.activity_no IS NOT NULL AND o.activity_no != '' THEN o.id END) * 100.0
                    / NULLIF(COUNT(DISTINCT o.id), 0), 2) AS coupon_order_pct,
                ROUND(AVG(CASE WHEN o.activity_no IS NOT NULL AND o.activity_no != '' THEN o.pay_money END), 2) AS avg_coupon_aov,
                ROUND(AVG(CASE WHEN o.activity_no IS NULL OR o.activity_no = '' THEN o.pay_money END), 2) AS avg_nocoupon_aov
            FROM grp_users gu
            INNER JOIN ods_luckyus_sales_order.v_order o
                ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
                AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
                AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
            GROUP BY gu.grp ORDER BY gu.grp""",
        'wait': 12
    },

    # Q2: 各组使用的券名称TOP10（按使用量排序），看哪些是实验券哪些是非实验券
    'F_用券明细_按组.csv': {
        'sql': CTE_BASE + f"""
            SELECT gu.grp, c.coupon_name,
                COUNT(*) AS used_cnt,
                COUNT(DISTINCT gu.user_no) AS used_users,
                ROUND(AVG(c.coupon_denomination), 2) AS avg_denomination
            FROM grp_users gu
            INNER JOIN ods_luckyus_sales_marketing.t_coupon_record c
                ON gu.user_no = c.member_no
                AND c.use_status = 1
                AND c.use_time >= '{EXP_START}' AND c.use_time < '{EXP_END_NEXT}'
            GROUP BY gu.grp, c.coupon_name
            HAVING used_cnt >= 10
            ORDER BY gu.grp, used_cnt DESC""",
        'wait': 15
    },

    # Q3: 各组每用户平均持有的非实验券数（检查是否均匀）
    # 非实验券 = 学生专属权益、Lunch Break、Luckin Day、Coffee Pass等通用券
    'F_非实验券持有均匀性.csv': {
        'sql': CTE_BASE + f"""
            SELECT gu.grp,
                COUNT(DISTINCT gu.user_no) AS total_users,
                COUNT(DISTINCT CASE WHEN c.coupon_name IN ('学生专属权益', 'Lunch Break Special - Buy 1 Get 1 Free',
                    'Luckin Day - Wednesday Special', 'Coffee Pass', 'Share The Luck Reward',
                    'Luck In Love: Free Tiramisu Drink', 'Luck In Love: Tiramisu Drinks BOGO',
                    'Luck In Love: 30% OFF') THEN c.id END) AS non_exp_coupons,
                COUNT(DISTINCT CASE WHEN c.coupon_name IN ('学生专属权益', 'Lunch Break Special - Buy 1 Get 1 Free',
                    'Luckin Day - Wednesday Special', 'Coffee Pass', 'Share The Luck Reward',
                    'Luck In Love: Free Tiramisu Drink', 'Luck In Love: Tiramisu Drinks BOGO',
                    'Luck In Love: 30% OFF') AND c.use_status = 1 THEN c.id END) AS non_exp_used,
                ROUND(COUNT(DISTINCT CASE WHEN c.coupon_name IN ('学生专属权益', 'Lunch Break Special - Buy 1 Get 1 Free',
                    'Luckin Day - Wednesday Special', 'Coffee Pass', 'Share The Luck Reward',
                    'Luck In Love: Free Tiramisu Drink', 'Luck In Love: Tiramisu Drinks BOGO',
                    'Luck In Love: 30% OFF') AND c.use_status = 1 THEN c.id END) * 1.0
                    / NULLIF(COUNT(DISTINCT gu.user_no), 0), 4) AS non_exp_used_per_user
            FROM grp_users gu
            LEFT JOIN ods_luckyus_sales_marketing.t_coupon_record c
                ON gu.user_no = c.member_no
                AND c.create_time >= '{EXP_START}' AND c.create_time < '{EXP_END_NEXT}'
            GROUP BY gu.grp ORDER BY gu.grp""",
        'wait': 15
    },

    # Q4: 各组无券订单的客单价对比（纯净价格信号）
    'F_无券订单客单价.csv': {
        'sql': CTE_BASE + f"""
            SELECT gu.grp,
                COUNT(DISTINCT o.id) AS no_coupon_orders,
                COUNT(DISTINCT o.user_no) AS no_coupon_users,
                ROUND(AVG(o.pay_money), 2) AS avg_aov,
                ROUND(SUM(o.pay_money), 2) AS total_revenue
            FROM grp_users gu
            INNER JOIN ods_luckyus_sales_order.v_order o
                ON gu.user_no = o.user_no AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
                AND o.create_time >= '{EXP_START}' AND o.create_time < '{EXP_END_NEXT}'
                AND o.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
                AND (o.activity_no IS NULL OR o.activity_no = '')
            GROUP BY gu.grp ORDER BY gu.grp""",
        'wait': 10
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
