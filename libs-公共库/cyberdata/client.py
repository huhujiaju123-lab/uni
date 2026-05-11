"""
CyberData API Client — 统一的数据查询接口
Unified CyberData query client for all experiment/report scripts.

Usage:
    from libs_cyberdata import CyberDataClient
    # or: import sys; sys.path.insert(0, '<workspace>/libs-公共库/cyberdata'); from client import CyberDataClient

    client = CyberDataClient()
    headers, rows = client.run_sql("SELECT 1")
"""

import json
import os
import subprocess
import time


_DEFAULT_AUTH_FILE = os.path.expanduser("~/.claude/skills/cyberdata-query/auth.json")

_API_BASE = "https://idpcd.luckincoffee.us"
_PROJECT_ID = "1906904360294313985"
_TENANT_ID = "1001"
_USER_ID = "47"
_TASK_ID = "1990991087752757249"
_ENV = 5
# Appended by curl -w after response body (body must not contain this literal).
_HTTP_SEP = "###CYBERDATA_HTTP###"


def _curl_json(r: subprocess.CompletedProcess, step: str) -> dict:
    """Split curl stdout into body + HTTP status from -w (see run)."""
    raw = r.stdout or ""
    if not raw.strip():
        raise RuntimeError(
            f"CyberData {step}: empty response (often HTTP 401). "
            "Refresh jwttoken in ~/.claude/skills/cyberdata-query/auth.json "
            "(e.g. libs-公共库/cyberdata/refresh_auth_jwt.py)."
        )
    if _HTTP_SEP in raw:
        body, http = raw.rsplit(_HTTP_SEP, 1)
        http = http.strip()
    else:
        body, http = raw, ""
    if http and http != "200":
        raise RuntimeError(
            f"CyberData {step}: HTTP {http}. "
            "Refresh jwttoken (or cookies if session expired). "
            f"Body preview: {body[:300]!r}"
        )
    if not body.strip():
        raise RuntimeError(
            f"CyberData {step}: empty body with HTTP {http or 'unknown'}. "
            "Refresh jwttoken (often 401)."
        )
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"CyberData {step}: not JSON ({e}). First 300 chars: {body[:300]!r}"
        ) from None


class CyberDataClient:
    def __init__(self, auth_file=None):
        auth_file = auth_file or _DEFAULT_AUTH_FILE
        with open(auth_file) as f:
            auth = json.load(f)
        self._cookies = auth["cookies"]
        self._jwttoken = auth["jwttoken"]

    def run_sql(self, sql, wait=6, max_poll=5):
        """Submit SQL and poll for results. Returns (headers, rows)."""
        ts = str(int(time.time() * 1000))

        submit_body = json.dumps({
            "_t": int(ts), "tenantId": _TENANT_ID, "userId": _USER_ID,
            "projectId": _PROJECT_ID, "resourceGroupId": 1,
            "taskId": _TASK_ID, "variables": {},
            "sqlStatement": sql, "env": _ENV,
        })

        r = subprocess.run(
            ["curl", "-sS", "-w", f"{_HTTP_SEP}%{{http_code}}", f"{_API_BASE}/api/dev/task/run",
             "-H", "accept: application/json, text/plain, */*",
             "-H", "content-type: application/json; charset=UTF-8",
             "-b", self._cookies, "-H", f"jwttoken: {self._jwttoken}",
             "-H", "productkey: CyberData",
             "-H", f"origin: {_API_BASE}",
             "--data-raw", submit_body],
            capture_output=True, text=True, timeout=30,
        )

        resp = _curl_json(r, "task/run")
        if resp.get("code") != "200":
            raise RuntimeError(f"Submit failed: {resp}")

        task_id = resp["data"]

        for _ in range(max_poll):
            time.sleep(wait)
            ts = str(int(time.time() * 1000))
            get_body = json.dumps({
                "_t": int(ts), "tenantId": _TENANT_ID, "userId": _USER_ID,
                "projectId": _PROJECT_ID, "env": _ENV,
                "taskInstanceId": task_id,
            })

            r = subprocess.run(
                ["curl", "-sS", "-w", f"{_HTTP_SEP}%{{http_code}}", f"{_API_BASE}/api/logger/getQueryLog",
                 "-H", "accept: application/json, text/plain, */*",
                 "-H", "content-type: application/json; charset=UTF-8",
                 "-b", self._cookies, "-H", f"jwttoken: {self._jwttoken}",
                 "-H", "productkey: CyberData",
                 "-H", f"origin: {_API_BASE}",
                 "--data-raw", get_body],
                capture_output=True, text=True, timeout=30,
            )

            resp = _curl_json(r, "getQueryLog")
            if resp.get("code") == "200" and resp.get("data"):
                columns = resp["data"][0].get("columns", [])
                if columns and len(columns) >= 1:
                    headers = columns[0]
                    rows = columns[1:] if len(columns) > 1 else []
                    return headers, rows

        raise TimeoutError(f"Query timed out after {max_poll} polls (task: {task_id})")

    def query(self, name, sql, wait=6, max_poll=5):
        """Run a named query with timing output."""
        print(f"\n{'='*50}")
        print(f"[{name}] Running...")
        start = time.time()
        headers, rows = self.run_sql(sql, wait=wait, max_poll=max_poll)
        elapsed = time.time() - start
        print(f"[{name}] Done in {elapsed:.1f}s — {len(rows)} rows")
        return headers, rows
