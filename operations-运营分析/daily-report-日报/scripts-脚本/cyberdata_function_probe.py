# -*- coding: utf-8 -*-
"""
CyberData 函数环境探测脚本
目的：贴进后台函数编辑器 → 点"测试" → 看返回，判断函数环境能做什么

探测项：
1. 能否 import http.client / json / time（标准库）
2. 能否从函数内部调 CyberData SQL 接口（同域 localhost 或 idpcd.luckincoffee.us）
3. 能否访问外网（飞书 webhook）
"""
import json
import time

def handler(input):
    results = {}

    # ── 探测1：标准库可用性 ──
    try:
        import http.client
        import urllib.request
        import urllib.parse
        results["stdlib"] = "ok"
    except Exception as e:
        results["stdlib"] = f"fail: {e}"

    # ── 探测2：能否调 CyberData 内部 SQL 接口 ──
    # 用最简单的 SELECT 1 测试
    try:
        import http.client
        conn = http.client.HTTPSConnection("idpcd.luckincoffee.us", timeout=15)

        # 从 input 里读认证信息（测试时手动填）
        jwttoken = input.get("jwttoken", "")
        cookies = input.get("cookies", "")

        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json; charset=UTF-8",
            "jwttoken": jwttoken,
            "productkey": "CyberData",
            "origin": "https://idpcd.luckincoffee.us",
            "Cookie": cookies
        }

        payload = json.dumps({
            "_t": int(time.time() * 1000),
            "tenantId": "1001",
            "userId": "47",
            "projectId": "1906904360294313985",
            "resourceGroupId": 1,
            "taskId": "1990991087752757249",
            "variables": {},
            "sqlStatement": "SELECT 1 AS probe_ok",
            "env": 5
        })

        conn.request("POST", "/api/dev/task/run", body=payload, headers=headers)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        conn.close()

        resp_json = json.loads(body)
        if resp_json.get("code") == "200":
            task_id = resp_json.get("data", "")
            results["sql_submit"] = f"ok, taskId={task_id}"

            # 等几秒再轮询结果
            time.sleep(8)

            conn2 = http.client.HTTPSConnection("idpcd.luckincoffee.us", timeout=15)
            poll_payload = json.dumps({
                "_t": int(time.time() * 1000),
                "tenantId": "1001",
                "userId": "47",
                "projectId": "1906904360294313985",
                "env": 5,
                "taskInstanceId": task_id
            })
            conn2.request("POST", "/api/logger/getQueryLog", body=poll_payload, headers=headers)
            resp2 = conn2.getresponse()
            body2 = resp2.read().decode("utf-8")
            conn2.close()

            resp2_json = json.loads(body2)
            if resp2_json.get("code") == "200" and resp2_json.get("data"):
                for item in resp2_json["data"]:
                    columns = item.get("columns", [])
                    if columns and len(columns) > 1:
                        results["sql_result"] = f"ok, got {len(columns)-1} rows"
                        break
                    status = item.get("status", "")
                    if status:
                        results["sql_result"] = f"pending, status={status}"
                else:
                    results["sql_result"] = f"poll returned but no columns yet"
            else:
                results["sql_result"] = f"poll fail: {body2[:200]}"
        else:
            results["sql_submit"] = f"fail: {body[:200]}"

    except Exception as e:
        results["sql_submit"] = f"error: {e}"

    # ── 探测3：能否访问外网（飞书 webhook） ──
    try:
        import http.client
        conn3 = http.client.HTTPSConnection("open.feishu.cn", timeout=10)
        conn3.request("GET", "/open-apis/bot/v2/hook/test-probe")
        resp3 = conn3.getresponse()
        results["feishu_network"] = f"ok, status={resp3.status}"
        conn3.close()
    except Exception as e:
        results["feishu_network"] = f"fail: {e}"

    return results


if __name__ == '__main__':
    import sys
    input_json = sys.stdin.read()
    input_data = json.loads(input_json) if input_json else {}
    result = handler(input_data)
    print(json.dumps(result, ensure_ascii=False))
