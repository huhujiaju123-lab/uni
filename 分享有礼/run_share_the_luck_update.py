#!/usr/bin/env python3
"""分享有礼数据更新脚本 - 数据截止 2026-03-04"""

import requests
import json
import time

BASE_URL = "https://idpcd.luckincoffee.us"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json; charset=UTF-8",
    "jwttoken": "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFMyNTYifQ.eyJyb2wiOnsiQUxMIjpbNF0sIkN5YmVyRGF0YSI6WzRdfSwianRpIjoiMTAwMSw0NyIsImlzcyI6IlNuYWlsQ2xpbWIiLCJpYXQiOjE3NzI2ODEwODgsInN1YiI6IuadjuWutemchCxudWxsLGxpeGlhb3hpYW8iLCJhdWQiOiJbe1wicm9sZUlkXCI6NCxcInZlcnNpb25OYW1lXCI6XCJDeWJlckRhdGFcIixcInZlcnNpb25JZFwiOjMsXCJyb2xlTmFtZVwiOlwiRGF0YUJhc2ljUm9sZVwifV0ifQ.5g6rohLs83835-qHAfE-CLMzPtONC1IggxxDNa04g_E",
    "productkey": "CyberData",
    "origin": "https://idpcd.luckincoffee.us",
    "referer": "https://idpcd.luckincoffee.us/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
}
COOKIES = {
    "LK_PROD.US_ILUCKYADMINWEB_SID": "up56OsMH3tYz6cGT8lyBLSc-oGD8nOhxLTvORgJwCG2nzx65syFZri_ubCcWV6Vqzz-yqLx_3-xzz7b4VJynozyt8J86A2UBkZziqgN4zdSEDbWchchd_fFLwlcrHKbb5i4DIzk4Z-SI06c5qkCWfZrzFUwFk1JJ_IJugfTYyHg=",
    "iluckyauth_session_prod": "MTc3MjY5ODA5NHxOd3dBTkRKSlZGTTFRMDVIVGtGTVNUTkdTVk0zU2xsSlJUWlhSVlkzVmxsQ1RFczBVazlVVDFsYVVFcEhOMXBHVlZKTFZVZElORkU9fHdlkGQ08ksN6yrqY5Qm7msREs6cVNMCxELpf65SWDKa",
}

def submit_sql(sql, label=""):
    payload = {
        "_t": int(time.time() * 1000),
        "tenantId": "1001",
        "userId": "47",
        "projectId": "1906904360294313985",
        "resourceGroupId": 1,
        "taskId": "1985617719742480386",
        "variables": {},
        "sqlStatement": sql,
        "env": 5
    }
    resp = requests.post(f"{BASE_URL}/api/dev/task/run", json=payload, headers=HEADERS, cookies=COOKIES)
    data = resp.json()
    if data.get("code") not in [0, "200", 200]:
        print(f"[{label}] Submit failed: {data}")
        return None
    # data field is directly the taskInstanceId string
    task_id = data["data"] if isinstance(data["data"], str) else data["data"].get("taskInstanceId", data["data"])
    print(f"[{label}] Submitted, taskInstanceId={task_id}")
    return task_id

def get_result(task_instance_id, label="", max_wait=120):
    payload = {
        "_t": int(time.time() * 1000),
        "tenantId": "1001",
        "userId": "47",
        "projectId": "1906904360294313985",
        "env": 5,
        "taskInstanceId": task_instance_id
    }
    for i in range(max_wait // 3):
        time.sleep(3)
        resp = requests.post(f"{BASE_URL}/api/logger/getQueryLog", json=payload, headers=HEADERS, cookies=COOKIES)
        data = resp.json()
        code = data.get("code")
        records = data.get("data", [])
        # API returns code='200' for both pending and completed
        if not records:
            print(f"[{label}] Waiting... ({i*3}s)")
            continue
        rec = records[0]
        # Check if columns exist (means query completed)
        columns = rec.get("columns", [])
        if columns:
            header = columns[0]
            rows = columns[1:]
            print(f"[{label}] Done: {len(rows)} rows")
            return header, rows
        # Check for status/error fields
        status = rec.get("status")
        if status == 3 or rec.get("log"):
            print(f"[{label}] Failed: {str(rec)[:200]}")
            return None, None
        print(f"[{label}] Waiting... ({i*3}s)")
    print(f"[{label}] Timeout after {max_wait}s")
    return None, None

def run_query(sql, label=""):
    task_id = submit_sql(sql, label)
    if not task_id:
        return None, None
    return get_result(task_id, label)

# ============================================================
# SQL Queries
# ============================================================

# 0. 诊断: 确认3月资源位配置
SQL_DIAG_RESOURCE = """
SELECT event, p_proposal_no, p_pic_url, COUNT(*) AS cnt
FROM ods_luckyus_track.v_hmonitor_track_event_rt
WHERE dt >= '2026-03-01' AND dt <= '2026-03-04'
    AND (event LIKE '%popupwin%' OR event LIKE '%resource%')
GROUP BY event, p_proposal_no, p_pic_url
ORDER BY cnt DESC
LIMIT 50
"""

# 1. 获客结果 (02-01 ~ 03-04)
SQL_ACQUISITION = """
WITH share_invitees AS (
    SELECT FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') AS register_dt,
        invitee_user_no, invitation_success
    FROM ods_luckyus_sales_marketing.t_user_invitation_info
    WHERE FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') >= '2026-02-01'
        AND FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') <= '2026-03-04'
        AND activity_no LIKE '%LKUS%'
),
share_daily AS (
    SELECT register_dt,
        COUNT(DISTINCT invitee_user_no) AS share_register_cnt,
        COUNT(DISTINCT CASE WHEN invitation_success = 1 THEN invitee_user_no END) AS share_order_cnt
    FROM share_invitees GROUP BY register_dt
),
all_new_orders AS (
    SELECT user_no,
        MIN(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS first_order_dt
    FROM ods_luckyus_sales_order.v_order
    WHERE status = 90 AND INSTR(tenant, 'IQ') = 0
        AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
    GROUP BY user_no
    HAVING first_order_dt >= '2026-02-01' AND first_order_dt <= '2026-03-04'
),
all_new_daily AS (
    SELECT first_order_dt AS dt, COUNT(DISTINCT user_no) AS total_new_order_cnt
    FROM all_new_orders GROUP BY first_order_dt
)
SELECT COALESCE(s.register_dt, a.dt) AS dt,
    COALESCE(s.share_register_cnt, 0) AS share_register_cnt,
    COALESCE(s.share_order_cnt, 0) AS share_order_cnt,
    COALESCE(a.total_new_order_cnt, 0) AS total_new_order_cnt,
    ROUND(COALESCE(s.share_order_cnt, 0) * 100.0 / NULLIF(a.total_new_order_cnt, 0), 2) AS share_order_pct
FROM share_daily s
LEFT JOIN all_new_daily a ON s.register_dt = a.dt
ORDER BY 1
LIMIT 100000
"""

# 2. 邀请数据 (02-01 ~ 03-04)
SQL_INVITATION = """
WITH base_data AS (
    SELECT
        FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') AS register_dt,
        inviter_user_no, invitee_user_no, invitation_success,
        CASE WHEN invitation_success = 1
            THEN DATEDIFF(
                FROM_UNIXTIME(UNIX_TIMESTAMP(modify_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d'),
                FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d'))
            ELSE NULL END AS order_days_from_register
    FROM ods_luckyus_sales_marketing.t_user_invitation_info
    WHERE FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') >= '2026-02-01'
        AND FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') <= '2026-03-04'
        AND activity_no LIKE '%LKUS%'
)
SELECT register_dt,
    COUNT(DISTINCT invitee_user_no) AS register_invitee_cnt,
    COUNT(DISTINCT inviter_user_no) AS inviter_cnt,
    COUNT(DISTINCT CASE WHEN order_days_from_register = 0 THEN invitee_user_no END) AS order_d0_invitee_cnt,
    COUNT(DISTINCT CASE WHEN order_days_from_register >= 0 AND order_days_from_register <= 2 THEN invitee_user_no END) AS order_d3_invitee_cnt,
    COUNT(DISTINCT CASE WHEN order_days_from_register >= 0 AND order_days_from_register <= 6 THEN invitee_user_no END) AS order_d7_invitee_cnt,
    COUNT(DISTINCT CASE WHEN order_days_from_register >= 0 AND order_days_from_register <= 13 THEN invitee_user_no END) AS order_d14_invitee_cnt,
    ROUND(COUNT(DISTINCT invitee_user_no) * 1.0 / NULLIF(COUNT(DISTINCT inviter_user_no), 0), 2) AS avg_register_per_inviter
FROM base_data
GROUP BY register_dt ORDER BY register_dt LIMIT 100000
"""

# 3. 分享意愿 (02-01 ~ 03-04)
SQL_SHARE_INTENT = """
SELECT
    DATE_FORMAT(CONVERT_TZ(server_time_form, @@time_zone, 'America/New_York'), '%Y-%m-%d') AS dt,
    COUNT(DISTINCT CASE WHEN event = '$page.H5sharepage$model.0$content.0$action.bw' THEN COALESCE(p_login_id, login_id) END) AS share_page_uv,
    COUNT(DISTINCT CASE WHEN event = '$page.H5sharepage$model.0$content.0$action.ck' THEN COALESCE(p_login_id, login_id) END) AS share_button_click_uv
FROM ods_luckyus_track.v_hmonitor_track_event_rt
WHERE dt >= '2026-02-01' AND dt <= '2026-03-04'
    AND event IN ('$page.H5sharepage$model.0$content.0$action.bw', '$page.H5sharepage$model.0$content.0$action.ck')
GROUP BY 1
ORDER BY 1
LIMIT 100000
"""

# 4. 流量资源位 - 先用2月已知配置跑，3月配置等诊断结果确认
# 2月: popup=LKUSCP118430296139038721, banner=luckymedia/1767772777170
SQL_TRAFFIC_FEB = """
SELECT
    DATE_FORMAT(CONVERT_TZ(server_time_form, @@time_zone, 'America/New_York'), '%Y-%m-%d') AS dt,
    COUNT(DISTINCT CASE WHEN event = '$page.home$model.diamond$content.0$action.bw' AND p_location = '2' THEN COALESCE(p_login_id, login_id) END) AS icon_expose_uv,
    COUNT(DISTINCT CASE WHEN event = '$page.home$model.diamond$content.0$action.ck' AND p_location = '2' THEN COALESCE(p_login_id, login_id) END) AS icon_click_uv,
    COUNT(DISTINCT CASE WHEN event = '$page.0$model.resource$content.0$action.bw' AND p_pic_url = 'https://ilucky-fe-outside-aws-prod.luckincdn.us/luckymedia/1767772777170_LKUSIMG118633222874660864.jpeg' THEN COALESCE(p_login_id, login_id) END) AS slot_expose_uv,
    COUNT(DISTINCT CASE WHEN event = '$page.0$model.resource$content.0$action.ck' AND p_pic_url = 'https://ilucky-fe-outside-aws-prod.luckincdn.us/luckymedia/1767772777170_LKUSIMG118633222874660864.jpeg' THEN COALESCE(p_login_id, login_id) END) AS slot_click_uv,
    COUNT(DISTINCT CASE WHEN event = '$page.0$model.popupwin$content.0$action.bw' AND p_proposal_no = 'LKUSCP118430296139038721' THEN COALESCE(p_login_id, login_id) END) AS popup_expose_uv,
    COUNT(DISTINCT CASE WHEN event = '$page.0$model.popupwin$content.0$action.ck' AND p_proposal_no = 'LKUSCP118430296139038721' AND p_ck_type = 'main_button' THEN COALESCE(p_login_id, login_id) END) AS popup_click_uv
FROM ods_luckyus_track.v_hmonitor_track_event_rt
WHERE dt >= '2026-02-01' AND dt <= '2026-03-04'
    AND event IN ('$page.home$model.diamond$content.0$action.bw', '$page.home$model.diamond$content.0$action.ck', '$page.0$model.resource$content.0$action.bw', '$page.0$model.resource$content.0$action.ck', '$page.0$model.popupwin$content.0$action.bw', '$page.0$model.popupwin$content.0$action.ck')
GROUP BY 1
ORDER BY 1
LIMIT 100000
"""

# 5. 邀请分布 (整体，02-01 ~ 03-04)
SQL_INVITE_DIST = """
WITH inviter_stats AS (
    SELECT inviter_user_no,
        COUNT(DISTINCT invitee_user_no) AS invite_cnt
    FROM ods_luckyus_sales_marketing.t_user_invitation_info
    WHERE FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') >= '2026-02-01'
        AND FROM_UNIXTIME(UNIX_TIMESTAMP(create_time, '%Y-%m-%d %H:%i:%s'), '%Y-%m-%d') <= '2026-03-04'
        AND activity_no LIKE '%LKUS%'
    GROUP BY inviter_user_no
)
SELECT invite_cnt, COUNT(*) AS inviter_count
FROM inviter_stats
GROUP BY invite_cnt
ORDER BY invite_cnt
LIMIT 50
"""

if __name__ == "__main__":
    results = {}

    # Phase 1: 非埋点表查询（快速）+ 资源位诊断
    print("=" * 60)
    print("Phase 1: 提交快速查询")
    print("=" * 60)

    # 先提交所有快速查询
    tasks = {}
    for name, sql in [
        ("acquisition", SQL_ACQUISITION),
        ("invitation", SQL_INVITATION),
        ("invite_dist", SQL_INVITE_DIST),
    ]:
        tid = submit_sql(sql, name)
        if tid:
            tasks[name] = tid
        time.sleep(1)

    # 等待结果
    for name, tid in tasks.items():
        h, r = get_result(tid, name)
        results[name] = (h, r)

    # Phase 2: 埋点表查询（较慢）
    print("\n" + "=" * 60)
    print("Phase 2: 提交埋点表查询")
    print("=" * 60)

    tasks2 = {}
    for name, sql in [
        ("diag_resource", SQL_DIAG_RESOURCE),
        ("share_intent", SQL_SHARE_INTENT),
        ("traffic", SQL_TRAFFIC_FEB),
    ]:
        tid = submit_sql(sql, name)
        if tid:
            tasks2[name] = tid
        time.sleep(1)

    for name, tid in tasks2.items():
        h, r = get_result(tid, name, max_wait=180)
        results[name] = (h, r)

    # 保存结果
    output = {}
    for name, (h, r) in results.items():
        if h is not None:
            output[name] = {"header": h, "rows": r}
        else:
            output[name] = {"header": None, "rows": None, "error": True}

    out_path = "/Users/xiaoxiao/Vibe coding/share_the_luck_data_0304.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nAll results saved to {out_path}")
