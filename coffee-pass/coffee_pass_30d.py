#!/usr/bin/env python3
"""Coffee Pass R2: 购买前后30天消费频次对比"""
import requests, json, time, os

BASE_URL = "https://idpcd.luckincoffee.us"
AUTH_FILE = os.path.expanduser("~/.claude/skills/cyberdata-query/auth.json")

with open(AUTH_FILE) as f:
    auth = json.load(f)

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json; charset=UTF-8",
    "jwttoken": auth["jwttoken"],
    "productkey": "CyberData",
    "origin": BASE_URL,
}
COOKIES = {}
for part in auth["cookies"].split(";"):
    part = part.strip()
    if "=" in part:
        k, v = part.split("=", 1)
        COOKIES[k.strip()] = v.strip()


def submit_sql(sql, label=""):
    payload = {
        "_t": int(time.time() * 1000),
        "tenantId": "1001", "userId": "47",
        "projectId": "1906904360294313985", "resourceGroupId": 1,
        "taskId": "1985617719742480386", "variables": {},
        "sqlStatement": sql, "env": 5,
    }
    resp = requests.post(f"{BASE_URL}/api/dev/task/run", json=payload, headers=HEADERS, cookies=COOKIES)
    if resp.status_code != 200:
        print(f"[{label}] HTTP {resp.status_code}")
        return None
    if not resp.text.strip():
        print(f"[{label}] 空响应 — Token 可能已过期")
        return None
    data = resp.json()
    if data.get("code") not in [0, "200", 200]:
        print(f"[{label}] 提交失败: {data}")
        return None
    task_id = data["data"]
    print(f"[{label}] 已提交, taskInstanceId={task_id}")
    return task_id


def get_result(task_instance_id, label="", max_wait=300):
    payload = {
        "_t": int(time.time() * 1000),
        "tenantId": "1001", "userId": "47",
        "projectId": "1906904360294313985", "env": 5,
        "taskInstanceId": task_instance_id,
    }
    for i in range(max_wait // 3):
        time.sleep(3)
        try:
            resp = requests.post(f"{BASE_URL}/api/logger/getQueryLog", json=payload, headers=HEADERS, cookies=COOKIES, timeout=30)
        except Exception as e:
            print(f"[{label}] 网络错误，重试... {e}")
            time.sleep(5)
            continue
        data = resp.json()
        records = data.get("data", [])
        if not records:
            if i % 5 == 0:
                print(f"[{label}] 等待中... ({i*3}s)")
            continue
        rec = records[0]
        columns = rec.get("columns", [])
        if columns:
            header = columns[0]
            rows = columns[1:]
            print(f"[{label}] 完成: {len(rows)} 行")
            # Convert to list of dicts
            return [dict(zip(header, r)) for r in rows]
        err = rec.get("errorMessage", "")
        if err:
            print(f"[{label}] 失败: {err[:200]}")
            return None
    print(f"[{label}] TIMEOUT")
    return None


def run_query(sql, label=""):
    print(f">>> {label}")
    qid = submit_sql(sql, label)
    if not qid:
        return None
    return get_result(qid, label)


# --- 购买前后30天对比（单次扫描，避免 UNION 超时） ---
# 先跑购买前30天
sql_before = """
WITH buyers AS (
    SELECT member_no,
           DATE(CONVERT_TZ(MIN(create_time), @@time_zone, 'America/New_York')) AS buy_dt
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE proposal_no = 'LKUSCP118713952489488385'
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) BETWEEN '2026-02-06' AND '2026-02-15'
    GROUP BY member_no
)
SELECT '购买前30天' AS period,
       COUNT(DISTINCT b.member_no) AS total_buyers,
       COUNT(DISTINCT CASE WHEN o.id IS NOT NULL THEN b.member_no END) AS active_users,
       COUNT(o.id) AS total_orders,
       ROUND(COUNT(o.id) / COUNT(DISTINCT b.member_no), 1) AS avg_orders,
       ROUND(SUM(COALESCE(o.actual_amount, 0)), 2) AS total_pay
FROM buyers b
LEFT JOIN ods_luckyus_sales.v_order o
  ON o.member_no = b.member_no
  AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
  AND o.create_time >= '2026-01-06' AND o.create_time < '2026-02-16'
  AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York'))
      BETWEEN DATE_SUB(b.buy_dt, INTERVAL 30 DAY) AND DATE_SUB(b.buy_dt, INTERVAL 1 DAY)
"""

sql_after = """
WITH buyers AS (
    SELECT member_no,
           DATE(CONVERT_TZ(MIN(create_time), @@time_zone, 'America/New_York')) AS buy_dt
    FROM ods_luckyus_sales_marketing.t_coupon_record
    WHERE proposal_no = 'LKUSCP118713952489488385'
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) BETWEEN '2026-02-06' AND '2026-02-15'
    GROUP BY member_no
)
SELECT '购买后30天' AS period,
       COUNT(DISTINCT b.member_no) AS total_buyers,
       COUNT(DISTINCT CASE WHEN o.id IS NOT NULL THEN b.member_no END) AS active_users,
       COUNT(o.id) AS total_orders,
       ROUND(COUNT(o.id) / COUNT(DISTINCT b.member_no), 1) AS avg_orders,
       ROUND(SUM(COALESCE(o.actual_amount, 0)), 2) AS total_pay
FROM buyers b
LEFT JOIN ods_luckyus_sales.v_order o
  ON o.member_no = b.member_no
  AND o.status = 90 AND INSTR(o.tenant, 'IQ') = 0
  AND o.create_time >= '2026-02-06' AND o.create_time < '2026-03-20'
  AND DATE(CONVERT_TZ(o.create_time, @@time_zone, 'America/New_York'))
      BETWEEN b.buy_dt AND DATE_ADD(b.buy_dt, INTERVAL 30 DAY)
"""

r_before = run_query(sql_before, "购买前30天")
r_after = run_query(sql_after, "购买后30天")

result = []
if r_before:
    result.extend(r_before)
if r_after:
    result.extend(r_after)

if result:
    print("\n=== 购买前后30天对比 ===")
    for r in result:
        print(f"  {r['period']}: {r['active_users']}/{r['total_buyers']} 人活跃, "
              f"{r['total_orders']} 单, 人均 {r['avg_orders']} 单, ${r['total_pay']}")

    # 更新 R2 JSON 文件
    r2_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coffee_pass_data_r2.json")
    with open(r2_file) as f:
        r2_data = json.load(f)
    r2_data["R2_before_after"] = result
    with open(r2_file, "w") as f:
        json.dump(r2_data, f, ensure_ascii=False, indent=2)
    print(f"\n已更新 {r2_file}")
else:
    print("查询失败")
