#!/usr/bin/env python3
"""
安全专项测试 — 验证安全加固是否生效
"""

import sys
import json
import time
sys.path.insert(0, ".")

from app import app, tasks, _rate_limit

app.config["TESTING"] = True
client = app.test_client()

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name} — {detail}")
        failed += 1


# ──────────────────────────────────────────────
print("\n=== 1. 路径遍历防护 ===")
# ──────────────────────────────────────────────

# ../  遍历尝试 (302 重定向或 404 都算拦截成功)
resp = client.get("/view/..%2f.env")
test("../  .env 被拦截", resp.status_code in (302, 404), f"got {resp.status_code}")

resp = client.get("/view/..%2f..%2f..%2fetc%2fpasswd")
test("../../etc/passwd 被拦截", resp.status_code in (302, 404), f"got {resp.status_code}")

resp = client.get("/view/....//....//etc//passwd")
test("双点遍历被拦截", resp.status_code in (302, 404), f"got {resp.status_code}")

# 非法字符
resp = client.get("/view/abc123!@#$")
test("非法字符 episode_id 被拦截", resp.status_code in (302, 404))

# 过长 ID
resp = client.get("/view/" + "a" * 100)
test("超长 episode_id 被拦截", resp.status_code == 302)

# 合法 ID 仍然正常
resp = client.get("/view/698b27ae66e2c30377d88131")
test("合法 episode_id 正常返回", resp.status_code == 200)


# ──────────────────────────────────────────────
print("\n=== 2. URL 输入校验 ===")
# ──────────────────────────────────────────────

# 非 https 协议
resp = client.post("/process", data={"url": "http://www.xiaoyuzhoufm.com/episode/abc123"})
test("http (非 https) 被拒绝", b"\xe8\xaf\xb7\xe8\xbe\x93\xe5\x85\xa5" in resp.data)

# 非小宇宙域名
resp = client.post("/process", data={"url": "https://evil.com/episode/abc123"})
test("恶意域名被拒绝", b"\xe8\xaf\xb7\xe8\xbe\x93\xe5\x85\xa5" in resp.data)

# JavaScript 注入
resp = client.post("/process", data={"url": "javascript:alert(1)"})
test("JS 注入被拒绝", b"\xe8\xaf\xb7\xe8\xbe\x93\xe5\x85\xa5" in resp.data)

# 超长 URL
long_url = "https://www.xiaoyuzhoufm.com/episode/" + "a" * 300
resp = client.post("/process", data={"url": long_url})
test("超长 URL 被拒绝", b"\xe8\xaf\xb7\xe8\xbe\x93\xe5\x85\xa5" in resp.data or b"\xe5\xbc\x82\xe5\xb8\xb8" in resp.data)


# ──────────────────────────────────────────────
print("\n=== 3. 速率限制 ===")
# ──────────────────────────────────────────────
_rate_limit.clear()  # 清空限流状态

valid_url = "https://www.xiaoyuzhoufm.com/episode/698b27ae66e2c30377d88131"
blocked = False
for i in range(7):
    resp = client.post("/process", data={"url": valid_url}, follow_redirects=False)
    if b"\xe9\xa2\x91\xe7\xb9\x81" in resp.data:  # 频繁
        blocked = True
        test(f"第 {i+1} 次请求被限流", True)
        break
test("速率限制生效", blocked, "7次请求都没被限流")


# ──────────────────────────────────────────────
print("\n=== 4. 并发限制 ===")
# ──────────────────────────────────────────────
_rate_limit.clear()

# 手动填充 3 个 started 任务
for i in range(3):
    tasks[f"fake-{i}"] = {"status": "started", "url": "", "steps": [], "episode_id": None, "error": None, "metadata": None}

resp = client.post("/process", data={"url": valid_url})
test("并发满时拒绝新任务", b"\xe4\xbb\xbb\xe5\x8a\xa1\xe8\xbe\x83\xe5\xa4\x9a" in resp.data)  # 任务较多

# 清理
for i in range(3):
    del tasks[f"fake-{i}"]


# ──────────────────────────────────────────────
print("\n=== 5. 安全响应头 ===")
# ──────────────────────────────────────────────
resp = client.get("/")
test("X-Content-Type-Options", resp.headers.get("X-Content-Type-Options") == "nosniff")
test("X-Frame-Options", resp.headers.get("X-Frame-Options") == "DENY")
test("X-XSS-Protection", resp.headers.get("X-XSS-Protection") == "1; mode=block")
test("Referrer-Policy", resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin")


# ──────────────────────────────────────────────
print("\n=== 6. 错误信息脱敏 ===")
# ──────────────────────────────────────────────
from app import _sanitize_error

msg1 = _sanitize_error("FileNotFoundError: /opt/podcast-viz/.env not found")
test("隐藏 /opt/podcast-viz 路径", "/opt/podcast-viz" not in msg1, f"got: {msg1}")

msg2 = _sanitize_error(f"Error at {sys.path[0]}/analyzer.py line 42")
test("隐藏项目根路径", "/Users/" not in msg2 and "/opt/" not in msg2, f"got: {msg2}")

msg3 = _sanitize_error("x" * 500)
test("错误信息截断到 200 字符", len(msg3) <= 200, f"got len={len(msg3)}")


# ──────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"安全测试结果：✅ {passed} 通过 / ❌ {failed} 失败")
print(f"{'='*50}")
sys.exit(1 if failed > 0 else 0)
