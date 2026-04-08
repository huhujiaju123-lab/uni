# -*- coding: utf-8 -*-
"""
Lucky US 日报函数 — CyberData 后台版 v2
每天定时触发，自动查数据 + 推飞书

input 参数：
  jwttoken  - CyberData JWT token
  cookies   - 登录 cookie（去掉 sensorsdata 那段中文）
  date      - 可选，指定日期 YYYY-MM-DD，不填则自动取美东昨天
"""
import json
import time
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

# ── 配置 ──────────────────────────────────────────────────────────────
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/0670509d-eabb-4f2a-b1d9-25bf06aa7fe8"
CYBERDATA_BASE = "https://idpcd.luckincoffee.us"
TENANT_ID      = "1001"
USER_ID        = "47"
PROJECT_ID     = "1906904360294313985"
TASK_ID        = "1990991087752757249"
ENV            = 5

CTX = ssl._create_unverified_context()

# ── HTTP 工具 ─────────────────────────────────────────────────────────
def ascii_only(s):
    return s.encode("ascii", errors="ignore").decode("ascii")

def post_json(url, payload_dict, jwttoken, cookies):
    payload = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("accept", "application/json, text/plain, */*")
    req.add_header("content-type", "application/json; charset=UTF-8")
    req.add_header("jwttoken", ascii_only(jwttoken))
    req.add_header("productkey", "CyberData")
    req.add_header("origin", CYBERDATA_BASE)
    req.add_header("Cookie", ascii_only(cookies))
    with urllib.request.urlopen(req, context=CTX, timeout=30) as resp:
        return resp.read().decode("utf-8")

def run_sql(sql, jwttoken, cookies, wait=12):
    """提交 SQL → 等待 → 返回 list of dict"""
    submit_body = post_json(f"{CYBERDATA_BASE}/api/dev/task/run", {
        "_t": int(time.time() * 1000),
        "tenantId": TENANT_ID, "userId": USER_ID,
        "projectId": PROJECT_ID, "resourceGroupId": 1,
        "taskId": TASK_ID, "variables": {},
        "sqlStatement": sql, "env": ENV
    }, jwttoken, cookies)

    resp = json.loads(submit_body)
    if resp.get("code") != "200":
        raise RuntimeError(f"SQL 提交失败: {submit_body[:300]}")
    task_id = resp["data"]

    time.sleep(wait)

    poll_body = post_json(f"{CYBERDATA_BASE}/api/logger/getQueryLog", {
        "_t": int(time.time() * 1000),
        "tenantId": TENANT_ID, "userId": USER_ID,
        "projectId": PROJECT_ID, "env": ENV,
        "taskInstanceId": task_id
    }, jwttoken, cookies)

    poll = json.loads(poll_body)
    if poll.get("code") != "200":
        raise RuntimeError(f"SQL 轮询失败: {poll_body[:300]}")

    data = poll.get("data", [])
    if not data:
        return []
    columns = data[0].get("columns", [])
    return cols_to_dicts(columns)

def cols_to_dicts(columns):
    """
    CyberData columns 格式：
    [["dt","2026-03-29","2026-03-28",...], ["杯量","3645","3827",...]]
    第一个元素是列名，后面是各行的值
    转成：[{"dt":"2026-03-29","杯量":"3645"}, {"dt":"2026-03-28","杯量":"3827"}, ...]
    """
    if not columns or len(columns[0]) < 2:
        return []
    headers = [col[0] for col in columns]
    n_rows = len(columns[0]) - 1
    rows = []
    for i in range(1, n_rows + 1):
        row = {headers[j]: columns[j][i] for j in range(len(headers))}
        rows.append(row)
    return rows

# ── 格式化工具 ────────────────────────────────────────────────────────
def safe_float(v):
    try:
        return float(v)
    except:
        return None

def fmt(v, style="int"):
    f = safe_float(v)
    if f is None:
        return "-"
    if style == "int":    return f"{int(f):,}"
    if style == "pct":    return f"{f:.1f}%"
    if style == "dollar": return f"${f:.2f}"
    if style == "f1":     return f"{f:.1f}"
    return str(v)

def dod(cur, prev):
    c, p = safe_float(cur), safe_float(prev)
    if c is None or p is None or p == 0:
        return ""
    change = (c - p) / p * 100
    arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
    return f" {arrow}{abs(change):.1f}%"

# ── 日期工具 ──────────────────────────────────────────────────────────
def get_et_yesterday():
    et = timezone(timedelta(hours=-4))  # EDT 夏令时
    return (datetime.now(et) - timedelta(days=1)).strftime("%Y-%m-%d")

def date_minus(date_str, n):
    return (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=n)).strftime("%Y-%m-%d")

def date_range(date_str, n=3):
    base = datetime.strptime(date_str, "%Y-%m-%d")
    return [(base - timedelta(days=n-1-i)).strftime("%Y-%m-%d") for i in range(n)]

def dates_in(dates):
    return "'" + "','".join(dates) + "'"

# ── SQL 模板 ──────────────────────────────────────────────────────────
def sql_business(dates):
    return f"""
SELECT dt AS 日期,
    COUNT(DISTINCT shop_name) AS 营业店铺数,
    SUM(sku_cnt) AS 杯量,
    SUM(order_cnt) AS 订单数,
    ROUND(SUM(pay_amount),2) AS 销售额,
    ROUND(SUM(pay_amount)/SUM(sku_cnt),2) AS 单杯实收,
    ROUND(SUM(sku_cnt)/COUNT(DISTINCT shop_name),0) AS 店日均杯量
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE tenant='LKUS' AND one_category_name='Drink'
  AND shop_name NOT IN ('NJ Test Kitchen','NJ Test Kitchen 2')
  AND dt IN ({dates_in(dates)})
GROUP BY dt ORDER BY dt
"""

def sql_user(date, date_7d_ago):
    return f"""
WITH day_orders AS (
    SELECT DISTINCT user_no FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant,'IQ')=0 AND status=90
      AND shop_name NOT IN ('NJ Test Kitchen','NJ Test Kitchen 2')
      AND DATE(CONVERT_TZ(create_time,@@time_zone,'America/New_York'))='{date}'
),
all_user_first AS (
    SELECT user_no, MIN(DATE(CONVERT_TZ(create_time,@@time_zone,'America/New_York'))) AS first_date
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant,'IQ')=0 AND status=90 GROUP BY user_no
),
user_type_calc AS (
    SELECT d.user_no,
        CASE WHEN uf.first_date='{date}' THEN '新客' ELSE '老客' END AS user_type
    FROM day_orders d LEFT JOIN all_user_first uf ON d.user_no=uf.user_no
),
new_users_7d_ago AS (SELECT user_no FROM all_user_first WHERE first_date='{date_7d_ago}'),
new_user_retention AS (
    SELECT COUNT(DISTINCT user_no) AS retained_new_users
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant,'IQ')=0 AND status=90
      AND user_no IN (SELECT user_no FROM new_users_7d_ago)
      AND DATE(CONVERT_TZ(create_time,@@time_zone,'America/New_York'))>'{date_7d_ago}'
      AND DATE(CONVERT_TZ(create_time,@@time_zone,'America/New_York'))<='{date}'
),
old_users_7d_ago AS (
    SELECT DISTINCT o.user_no FROM ods_luckyus_sales_order.v_order o
    JOIN all_user_first uf ON o.user_no=uf.user_no
    WHERE INSTR(o.tenant,'IQ')=0 AND o.status=90
      AND DATE(CONVERT_TZ(o.create_time,@@time_zone,'America/New_York'))='{date_7d_ago}'
      AND uf.first_date<'{date_7d_ago}'
),
old_user_retention AS (
    SELECT COUNT(DISTINCT user_no) AS retained_old_users
    FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant,'IQ')=0 AND status=90
      AND user_no IN (SELECT user_no FROM old_users_7d_ago)
      AND DATE(CONVERT_TZ(create_time,@@time_zone,'America/New_York'))>'{date_7d_ago}'
      AND DATE(CONVERT_TZ(create_time,@@time_zone,'America/New_York'))<='{date}'
),
reg_users AS (
    SELECT COUNT(*) AS reg_count FROM ods_luckyus_sales_crm.t_user
    WHERE INSTR(tenant,'IQ')=0
      AND DATE(CONVERT_TZ(create_time,@@time_zone,'America/New_York'))='{date}'
),
shop_count AS (
    SELECT COUNT(DISTINCT shop_name) AS shop_cnt FROM ods_luckyus_sales_order.v_order
    WHERE INSTR(tenant,'IQ')=0 AND status=90
      AND shop_name NOT IN ('NJ Test Kitchen','NJ Test Kitchen 2')
      AND DATE(CONVERT_TZ(create_time,@@time_zone,'America/New_York'))='{date}'
)
SELECT '{date}' AS 日期,
    (SELECT shop_cnt FROM shop_count) AS 营业店铺数,
    (SELECT reg_count FROM reg_users) AS 注册用户数,
    SUM(CASE WHEN user_type='新客' THEN 1 ELSE 0 END) AS 新客数,
    SUM(CASE WHEN user_type='老客' THEN 1 ELSE 0 END) AS 老客数,
    (SELECT COUNT(*) FROM new_users_7d_ago) AS 七日前新客数,
    (SELECT retained_new_users FROM new_user_retention) AS 新客7日留存人数,
    (SELECT COUNT(*) FROM old_users_7d_ago) AS 七日前老客数,
    (SELECT retained_old_users FROM old_user_retention) AS 老客7日留存人数
FROM user_type_calc
"""

def sql_funnel(dates):
    return f"""
SELECT dt AS 日期,
    COUNT(DISTINCT CASE WHEN screen_name='menu' THEN user_no END) AS menu_uv,
    COUNT(DISTINCT CASE WHEN screen_name='productdetail' THEN user_no END) AS productdetail_uv,
    COUNT(DISTINCT CASE WHEN screen_name='confirmorder' THEN user_no END) AS confirmorder_uv,
    COUNT(DISTINCT CASE WHEN screen_name='orderdetail' THEN user_no END) AS orderdetail_uv
FROM dw_dws.dws_mg_log_user_screen_name_d_1d
WHERE dt IN ({dates_in(dates)})
  AND screen_name IN ('menu','productdetail','confirmorder','orderdetail')
GROUP BY dt ORDER BY dt
"""

def sql_product(dates):
    return f"""
SELECT dt AS 日期,
    SUM(order_cnt) AS 总订单数,
    SUM(CASE WHEN spu_name LIKE '%Coconut%' THEN order_cnt ELSE 0 END) AS Coconut_orders,
    SUM(CASE WHEN spu_name LIKE '%Cold Brew%' THEN order_cnt ELSE 0 END) AS ColdBrew_orders,
    SUM(CASE WHEN spu_name LIKE '%Pineapple%' THEN order_cnt ELSE 0 END) AS Pineapple_orders,
    SUM(CASE WHEN spu_name LIKE '%Matcha%' THEN order_cnt ELSE 0 END) AS Matcha_orders,
    SUM(CASE WHEN spu_name LIKE '%Velvet%' THEN order_cnt ELSE 0 END) AS Velvet_orders
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE tenant='LKUS' AND one_category_name='Drink'
  AND shop_name NOT IN ('NJ Test Kitchen','NJ Test Kitchen 2')
  AND dt IN ({dates_in(dates)})
GROUP BY dt ORDER BY dt
"""

# ── 报告构建 ──────────────────────────────────────────────────────────
def build_report(date, jwttoken, cookies):
    dates = date_range(date, 3)
    date_7d_ago = date_minus(date, 7)
    lines = [f"📊 Lucky US 日报 — {date}", f"对比: {dates[0]} ~ {dates[-1]}", ""]

    # 业务结果
    try:
        rows = run_sql(sql_business(dates), jwttoken, cookies, wait=10)
        if rows:
            lines.append("━━ 业务结果 ━━")
            last = rows[-1]
            prev = rows[-2] if len(rows) >= 2 else {}
            for label, col, style in [
                ("杯量",     "杯量",     "int"),
                ("店日均杯量", "店日均杯量", "int"),
                ("单杯实收",  "单杯实收",  "dollar"),
                ("订单数",   "订单数",   "int"),
                ("销售额",   "销售额",   "dollar"),
            ]:
                if col in last:
                    lines.append(f"  {label}: {fmt(last[col], style)}{dod(last[col], prev.get(col))}")
            lines.append("")
    except Exception as e:
        lines.append(f"  [业务结果查询失败: {e}]\n")

    # 用户
    try:
        rows = run_sql(sql_user(date, date_7d_ago), jwttoken, cookies, wait=20)
        if rows:
            lines.append("━━ 用户 ━━")
            r = rows[0]
            new_c  = safe_float(r.get("新客数", 0)) or 0
            old_c  = safe_float(r.get("老客数", 0)) or 0
            total  = new_c + old_c
            shop   = safe_float(r.get("营业店铺数", 1)) or 1
            new_7d = safe_float(r.get("七日前新客数", 0)) or 0
            old_7d = safe_float(r.get("七日前老客数", 0)) or 0
            new_ret = safe_float(r.get("新客7日留存人数", 0)) or 0
            old_ret = safe_float(r.get("老客7日留存人数", 0)) or 0
            lines.append(f"  注册用户: {fmt(r.get('注册用户数'), 'int')}")
            lines.append(f"  新客: {fmt(new_c, 'int')}  老客: {fmt(old_c, 'int')}")
            lines.append(f"  新客占比: {fmt(new_c/total*100 if total else 0, 'pct')}")
            lines.append(f"  店日均新客: {fmt(new_c/shop, 'f1')}")
            lines.append(f"  新客7日留存: {fmt(new_ret/new_7d*100 if new_7d else 0, 'pct')}")
            lines.append(f"  老客7日留存: {fmt(old_ret/old_7d*100 if old_7d else 0, 'pct')}")
            lines.append("")
    except Exception as e:
        lines.append(f"  [用户查询失败: {e}]\n")

    # 漏斗
    try:
        rows = run_sql(sql_funnel(dates), jwttoken, cookies, wait=10)
        if rows:
            lines.append("━━ 漏斗转化 ━━")
            last = rows[-1]
            prev = rows[-2] if len(rows) >= 2 else {}
            menu = safe_float(last.get("menu_uv", 0)) or 0
            pd   = safe_float(last.get("productdetail_uv", 0)) or 0
            co   = safe_float(last.get("confirmorder_uv", 0)) or 0
            od   = safe_float(last.get("orderdetail_uv", 0)) or 0
            p_menu = safe_float(prev.get("menu_uv", 0)) or 0
            p_pd   = safe_float(prev.get("productdetail_uv", 0)) or 0
            p_co   = safe_float(prev.get("confirmorder_uv", 0)) or 0
            p_od   = safe_float(prev.get("orderdetail_uv", 0)) or 0
            r1 = pd/menu*100 if menu else 0
            r2 = co/pd*100 if pd else 0
            r3 = od/co*100 if co else 0
            p1 = p_pd/p_menu*100 if p_menu else 0
            p2 = p_co/p_pd*100 if p_pd else 0
            p3 = p_od/p_co*100 if p_co else 0
            lines.append(f"  Menu→详情: {fmt(r1,'pct')}{dod(r1,p1)}")
            lines.append(f"  详情→确认: {fmt(r2,'pct')}{dod(r2,p2)}")
            lines.append(f"  确认→支付: {fmt(r3,'pct')}{dod(r3,p3)}")
            lines.append("")
    except Exception as e:
        lines.append(f"  [漏斗查询失败: {e}]\n")

    # 商品渗透
    try:
        rows = run_sql(sql_product(dates), jwttoken, cookies, wait=10)
        if rows:
            lines.append("━━ 核心商品渗透 ━━")
            last = rows[-1]
            prev = rows[-2] if len(rows) >= 2 else {}
            total   = safe_float(last.get("总订单数", 0)) or 0
            p_total = safe_float(prev.get("总订单数", 0)) or 0
            for name, col in [
                ("Coconut",   "Coconut_orders"),
                ("Cold Brew", "ColdBrew_orders"),
                ("Pineapple", "Pineapple_orders"),
                ("Matcha",    "Matcha_orders"),
                ("Velvet",    "Velvet_orders"),
            ]:
                v  = safe_float(last.get(col, 0)) or 0
                pv = safe_float(prev.get(col, 0)) or 0
                r  = v/total*100 if total else 0
                pr = pv/p_total*100 if p_total else 0
                lines.append(f"  {name}: {fmt(r,'pct')}{dod(r,pr)}")
            lines.append("")
    except Exception as e:
        lines.append(f"  [商品渗透查询失败: {e}]\n")

    et = timezone(timedelta(hours=-4))
    lines.append(f"⏱ 生成于 {datetime.now(et).strftime('%m/%d %H:%M')} ET")
    return "\n".join(lines)

# ── 飞书推送 ──────────────────────────────────────────────────────────
def send_feishu(text):
    payload = json.dumps({"msg_type": "text", "content": {"text": text}}).encode("utf-8")
    req = urllib.request.Request(FEISHU_WEBHOOK, data=payload, method="POST")
    req.add_header("content-type", "application/json; charset=UTF-8")
    with urllib.request.urlopen(req, context=CTX, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("code") != 0:
        raise RuntimeError(f"飞书发送失败: {result}")
    return result

# ── 入口 ──────────────────────────────────────────────────────────────
def handler(input):
    jwttoken = input.get("jwttoken", "")
    cookies  = input.get("cookies", "")
    date     = input.get("date", get_et_yesterday())

    try:
        report = build_report(date, jwttoken, cookies)
        send_feishu(report)
        return {"status": "ok", "date": date, "preview": report[:300]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == '__main__':
    import sys
    input_json = sys.stdin.read()
    input_data = json.loads(input_json) if input_json else {}
    result = handler(input_data)
    print(json.dumps(result, ensure_ascii=False))
