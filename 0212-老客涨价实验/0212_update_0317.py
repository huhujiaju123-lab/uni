"""
0212涨价实验 — 数据更新 (截止03-16)
方法论：DWD表 + type排除 + 仅饮品 + order_category过滤 + 生命周期分层
"""
import subprocess, json, time, sys

def run_sql(sql, label=""):
    print(f"\n{'='*60}\n  {label}\n{'='*60}")
    result = subprocess.run(
        ["/Users/xiaoxiao/.claude/skills/cyberdata-query/run_sql.sh", sql],
        capture_output=True, text=True, timeout=300
    )
    output = result.stdout.strip()
    if result.returncode != 0 or "错误" in output or "过期" in output:
        print(f"  ❌ {output[:300]}")
        return None
    lines = output.split("\n")
    # Skip "提交查询...", "任务ID: ...", "等待执行..." lines
    data_lines = []
    skip = True
    for line in lines:
        if skip and (line.startswith("提交") or line.startswith("任务") or line.startswith("等待")):
            continue
        skip = False
        data_lines.append(line)
    if len(data_lines) < 2:
        print(f"  ⚠️ 无数据返回")
        return None
    headers = data_lines[0].split("\t")
    rows = [line.split("\t") for line in data_lines[1:] if line.strip()]
    print(f"  ✅ {len(rows)} 行")
    # Print table
    for row in rows[:30]:
        print("  " + " | ".join(str(v) for v in row))
    return {"headers": headers, "rows": rows}


# ============================================================
# Q1: 核心指标 — 按组×生命周期分层
# 用 DWD order item (推荐) + 用户排除 + 仅饮品
# ============================================================
SQL_Q1 = """
WITH grp_users AS (
    SELECT DISTINCT g.user_no,
        CASE
            WHEN g.group_name LIKE '%涨价组1%' THEN '涨价组1'
            WHEN g.group_name LIKE '%涨价组2%' THEN '涨价组2'
            WHEN g.group_name LIKE '%对照组3%' THEN '对照组3'
        END AS grp
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    WHERE g.tenant = 'LKUS' AND g.dt = '2026-02-28'
        AND (g.group_name LIKE '%0212价格实验%涨价组1%'
          OR g.group_name LIKE '%0212价格实验%涨价组2%'
          OR g.group_name LIKE '%0212价格实验%对照组3%')
),
valid_users AS (
    SELECT gu.user_no, gu.grp
    FROM grp_users gu
    INNER JOIN ods_luckyus_sales_crm.t_user u ON gu.user_no = u.user_no
    WHERE u.type NOT IN (3, 4, 5)
),
user_first_order AS (
    SELECT user_no, MIN(dt) AS first_order_dt
    FROM dw_dwd.dwd_t_ord_order_item_d_inc
    WHERE order_status = 90 AND order_category = '门店订单'
        AND one_category_name = 'Drink'
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY user_no
),
user_lc AS (
    SELECT vu.user_no, vu.grp,
        CASE
            WHEN ufo.first_order_dt IS NULL THEN '未购'
            WHEN DATEDIFF('2026-02-12', ufo.first_order_dt) <= 15 THEN '0-15天'
            WHEN DATEDIFF('2026-02-12', ufo.first_order_dt) <= 30 THEN '16-30天'
            ELSE '31天+'
        END AS lifecycle
    FROM valid_users vu
    LEFT JOIN user_first_order ufo ON vu.user_no = ufo.user_no
),
base AS (
    SELECT grp, lifecycle, COUNT(*) AS total_users
    FROM user_lc GROUP BY grp, lifecycle
),
exp_drinks AS (
    SELECT ul.grp, ul.lifecycle, ul.user_no,
        oi.order_id,
        oi.pay_amount AS drink_pay,
        oi.sku_num AS drink_cups
    FROM user_lc ul
    INNER JOIN dw_dwd.dwd_t_ord_order_item_d_inc oi ON ul.user_no = oi.user_no
        AND oi.order_status = 90
        AND oi.order_category = '门店订单'
        AND oi.one_category_name = 'Drink'
        AND oi.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
        AND oi.dt >= '2026-02-13' AND oi.dt <= '2026-03-16'
)
SELECT
    b.grp, b.lifecycle, b.total_users,
    COUNT(DISTINCT ed.user_no) AS order_users,
    COUNT(DISTINCT ed.order_id) AS order_cnt,
    SUM(ed.drink_cups) AS total_cups,
    ROUND(SUM(ed.drink_pay), 2) AS total_drink_rev,
    ROUND(SUM(ed.drink_pay) / NULLIF(SUM(ed.drink_cups), 0), 2) AS unit_price,
    ROUND(SUM(ed.drink_pay) / NULLIF(b.total_users, 0), 2) AS arpu_itt,
    ROUND(SUM(ed.drink_cups) / NULLIF(b.total_users, 0), 4) AS cups_per_user
FROM base b
LEFT JOIN exp_drinks ed ON b.grp = ed.grp AND b.lifecycle = ed.lifecycle
GROUP BY b.grp, b.lifecycle, b.total_users
ORDER BY b.grp,
    CASE b.lifecycle WHEN '0-15天' THEN 1 WHEN '16-30天' THEN 2 WHEN '31天+' THEN 3 ELSE 4 END
"""

# ============================================================
# Q2: 来访率 — 按组×生命周期
# ============================================================
SQL_Q2 = """
WITH grp_users AS (
    SELECT DISTINCT g.user_no,
        CASE
            WHEN g.group_name LIKE '%涨价组1%' THEN '涨价组1'
            WHEN g.group_name LIKE '%涨价组2%' THEN '涨价组2'
            WHEN g.group_name LIKE '%对照组3%' THEN '对照组3'
        END AS grp
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    WHERE g.tenant = 'LKUS' AND g.dt = '2026-02-28'
        AND (g.group_name LIKE '%0212价格实验%涨价组1%'
          OR g.group_name LIKE '%0212价格实验%涨价组2%'
          OR g.group_name LIKE '%0212价格实验%对照组3%')
),
valid_users AS (
    SELECT gu.user_no, gu.grp
    FROM grp_users gu
    INNER JOIN ods_luckyus_sales_crm.t_user u ON gu.user_no = u.user_no
    WHERE u.type NOT IN (3, 4, 5)
),
user_first_order AS (
    SELECT user_no, MIN(dt) AS first_order_dt
    FROM dw_dwd.dwd_t_ord_order_item_d_inc
    WHERE order_status = 90 AND order_category = '门店订单'
        AND one_category_name = 'Drink'
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY user_no
),
user_lc AS (
    SELECT vu.user_no, vu.grp,
        CASE
            WHEN ufo.first_order_dt IS NULL THEN '未购'
            WHEN DATEDIFF('2026-02-12', ufo.first_order_dt) <= 15 THEN '0-15天'
            WHEN DATEDIFF('2026-02-12', ufo.first_order_dt) <= 30 THEN '16-30天'
            ELSE '31天+'
        END AS lifecycle
    FROM valid_users vu
    LEFT JOIN user_first_order ufo ON vu.user_no = ufo.user_no
),
base AS (
    SELECT grp, lifecycle, COUNT(*) AS total_users
    FROM user_lc GROUP BY grp, lifecycle
),
visit_users AS (
    SELECT DISTINCT ul.grp, ul.lifecycle, ul.user_no
    FROM user_lc ul
    INNER JOIN dw_dwd.dwd_mg_log_detail_d_inc log ON ul.user_no = log.login_id
        AND log.event = 'AppStart'
        AND log.local_dt >= '2026-02-13' AND log.local_dt <= '2026-03-16'
)
SELECT
    b.grp, b.lifecycle, b.total_users,
    COUNT(DISTINCT vu.user_no) AS visit_users,
    ROUND(COUNT(DISTINCT vu.user_no) / NULLIF(b.total_users, 0) * 100, 2) AS visit_rate
FROM base b
LEFT JOIN visit_users vu ON b.grp = vu.grp AND b.lifecycle = vu.lifecycle
GROUP BY b.grp, b.lifecycle, b.total_users
ORDER BY b.grp,
    CASE b.lifecycle WHEN '0-15天' THEN 1 WHEN '16-30天' THEN 2 WHEN '31天+' THEN 3 ELSE 4 END
"""

# ============================================================
# Q3: 按周趋势 — 全量（不分层），看趋势变化
# ============================================================
SQL_Q3 = """
WITH grp_users AS (
    SELECT DISTINCT g.user_no,
        CASE
            WHEN g.group_name LIKE '%涨价组1%' THEN '涨价组1'
            WHEN g.group_name LIKE '%涨价组2%' THEN '涨价组2'
            WHEN g.group_name LIKE '%对照组3%' THEN '对照组3'
        END AS grp
    FROM dw_ads.ads_marketing_t_user_group_d_his g
    WHERE g.tenant = 'LKUS' AND g.dt = '2026-02-28'
        AND (g.group_name LIKE '%0212价格实验%涨价组1%'
          OR g.group_name LIKE '%0212价格实验%涨价组2%'
          OR g.group_name LIKE '%0212价格实验%对照组3%')
),
valid_users AS (
    SELECT gu.user_no, gu.grp
    FROM grp_users gu
    INNER JOIN ods_luckyus_sales_crm.t_user u ON gu.user_no = u.user_no
    WHERE u.type NOT IN (3, 4, 5)
),
base AS (
    SELECT grp, COUNT(*) AS total_users
    FROM valid_users GROUP BY grp
),
exp_drinks AS (
    SELECT vu.grp, vu.user_no, oi.order_id, oi.dt,
        YEARWEEK(oi.dt, 1) AS yw,
        oi.pay_amount AS drink_pay, oi.sku_num AS drink_cups
    FROM valid_users vu
    INNER JOIN dw_dwd.dwd_t_ord_order_item_d_inc oi ON vu.user_no = oi.user_no
        AND oi.order_status = 90 AND oi.order_category = '门店订单'
        AND oi.one_category_name = 'Drink'
        AND oi.shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
        AND oi.dt >= '2026-02-13' AND oi.dt <= '2026-03-16'
)
SELECT
    ed.grp, ed.yw AS week,
    b.total_users,
    COUNT(DISTINCT ed.user_no) AS order_users,
    COUNT(DISTINCT ed.order_id) AS order_cnt,
    SUM(ed.drink_cups) AS total_cups,
    ROUND(SUM(ed.drink_pay), 2) AS total_drink_rev,
    ROUND(SUM(ed.drink_pay) / NULLIF(SUM(ed.drink_cups), 0), 2) AS unit_price,
    ROUND(SUM(ed.drink_pay) / NULLIF(b.total_users, 0), 2) AS arpu_itt,
    ROUND(COUNT(DISTINCT ed.user_no) / NULLIF(b.total_users, 0) * 100, 2) AS order_rate
FROM exp_drinks ed
INNER JOIN base b ON ed.grp = b.grp
GROUP BY ed.grp, ed.yw, b.total_users
ORDER BY ed.yw, ed.grp
"""


def main():
    queries = [
        ("Q1: 核心指标(组×生命周期) 02-13~03-16", SQL_Q1),
        ("Q2: 来访率(组×生命周期)", SQL_Q2),
        ("Q3: 按周趋势(全量)", SQL_Q3),
    ]

    if len(sys.argv) > 1:
        idx = int(sys.argv[1])
        queries = [queries[idx]]

    all_data = {}
    for label, sql in queries:
        result = run_sql(sql, label)
        if result:
            all_data[label] = [dict(zip(result["headers"], row)) for row in result["rows"]]

    out_path = "/Users/xiaoxiao/Vibe coding/0212-老客涨价实验/0212_update_0317_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n📄 数据已保存: {out_path}")


if __name__ == "__main__":
    main()
