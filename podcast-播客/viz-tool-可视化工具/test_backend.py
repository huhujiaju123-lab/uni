#!/usr/bin/env python3
"""
后端接口回测脚本
逐一测试所有路由，验证返回状态和内容
"""

import sys
import json
import time
sys.path.insert(0, ".")

from app import app, tasks, OUTPUT_DIR

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
print("\n=== 1. GET / (首页) ===")
# ──────────────────────────────────────────────
resp = client.get("/")
test("状态码 200", resp.status_code == 200, f"got {resp.status_code}")
test("包含输入框", b'name="url"' in resp.data, "missing url input")
test("包含标题", b"\xe6\x92\xad\xe5\xae\xa2\xe5\x8f\xaf\xe8\xa7\x86\xe5\x8c\x96" in resp.data, "missing title")  # 播客可视化

# 检查历史记录（EP91 有 visualization.html）
test("显示历史记录", b"698b27ae66e2c30377d88131" in resp.data, "missing history for EP91")

# ──────────────────────────────────────────────
print("\n=== 2. POST /process — 无效 URL ===")
# ──────────────────────────────────────────────
resp = client.post("/process", data={"url": ""})
test("空 URL 返回错误页", resp.status_code == 200, f"got {resp.status_code}")
test("包含错误提示", b"\xe8\xaf\xb7\xe8\xbe\x93\xe5\x85\xa5" in resp.data, "missing error message")  # 请输入

resp = client.post("/process", data={"url": "https://google.com"})
test("非小宇宙链接返回错误", b"\xe8\xaf\xb7\xe8\xbe\x93\xe5\x85\xa5" in resp.data, "missing error for non-xiaoyuzhou URL")

# ──────────────────────────────────────────────
print("\n=== 3. POST /process — 有效 URL（已有完整数据的 EP91）===")
# ──────────────────────────────────────────────
resp = client.post(
    "/process",
    data={"url": "https://www.xiaoyuzhoufm.com/episode/698b27ae66e2c30377d88131"},
    follow_redirects=False,
)
test("返回 302 重定向", resp.status_code == 302, f"got {resp.status_code}")
test("重定向到 /progress/", "/progress/" in resp.headers.get("Location", ""), f"location: {resp.headers.get('Location')}")

# 提取 task_id
location = resp.headers.get("Location", "")
task_id = location.split("/progress/")[-1] if "/progress/" in location else None
test("task_id 已生成", task_id is not None and task_id in tasks, f"task_id={task_id}")

# ──────────────────────────────────────────────
print("\n=== 4. GET /progress/<task_id> ===")
# ──────────────────────────────────────────────
if task_id:
    resp = client.get(f"/progress/{task_id}")
    test("状态码 200", resp.status_code == 200, f"got {resp.status_code}")
    test("包含 task_id", task_id.encode() in resp.data, "missing task_id in page")
    test("包含步骤 UI", b"\xe8\x8e\xb7\xe5\x8f\x96\xe5\x85\x83\xe6\x95\xb0\xe6\x8d\xae" in resp.data, "missing step names")  # 获取元数据

    # 测试不存在的 task_id
    resp = client.get("/progress/nonexistent")
    test("不存在的 task 重定向首页", resp.status_code == 302, f"got {resp.status_code}")

# ──────────────────────────────────────────────
print("\n=== 5. GET /stream/<task_id> (SSE) ===")
# ──────────────────────────────────────────────
if task_id:
    # 等流水线跑完（EP91 全部文件已有，应该秒完）
    for _ in range(20):
        if tasks.get(task_id, {}).get("status") in ("done", "error"):
            break
        time.sleep(0.5)

    task_status = tasks.get(task_id, {}).get("status")
    test("流水线完成", task_status == "done", f"status={task_status}, error={tasks.get(task_id, {}).get('error')}")

    # 测试 SSE 端点
    resp = client.get(f"/stream/{task_id}")
    test("SSE content-type", "text/event-stream" in resp.content_type, f"got {resp.content_type}")

    # 读取 SSE 数据
    sse_data = resp.data.decode("utf-8")
    test("SSE 包含 data:", "data:" in sse_data, "no SSE data")

    # 解析最后一条 SSE 消息
    lines = [l for l in sse_data.strip().split("\n") if l.startswith("data:")]
    if lines:
        last_msg = json.loads(lines[-1].replace("data: ", ""))
        test("SSE done=True", last_msg.get("done") is True, f"done={last_msg.get('done')}")
        test("SSE episode_id", last_msg.get("episode_id") == "698b27ae66e2c30377d88131",
             f"episode_id={last_msg.get('episode_id')}")
        test("SSE 所有步骤 done", all(s["status"] == "done" for s in last_msg.get("steps", [])),
             f"steps={[s['status'] for s in last_msg.get('steps', [])]}")

# ──────────────────────────────────────────────
print("\n=== 6. GET /view/<episode_id> ===")
# ──────────────────────────────────────────────
resp = client.get("/view/698b27ae66e2c30377d88131")
test("EP91 返回 200", resp.status_code == 200, f"got {resp.status_code}")
test("返回 HTML", "text/html" in resp.content_type, f"got {resp.content_type}")
test("HTML 内容非空", len(resp.data) > 1000, f"got {len(resp.data)} bytes")

# 不存在的 episode
resp = client.get("/view/nonexistent")
test("不存在的 episode 重定向首页", resp.status_code == 302, f"got {resp.status_code}")

# ──────────────────────────────────────────────
print("\n=== 7. 流水线缓存逻辑（EP91 全部文件已有 → 全部 skip）===")
# ──────────────────────────────────────────────
if task_id:
    task = tasks[task_id]
    steps = task["steps"]
    # 所有步骤应该都是 done（因为文件已存在）
    for i, step in enumerate(steps):
        test(f"Step {i+1} '{step['name']}' = done", step["status"] == "done",
             f"status={step['status']}, detail={step['detail']}")
    # 检查 skip 提示
    test("Step 2 跳过转录", "跳过" in steps[1]["detail"] or "已有" in steps[1]["detail"],
         f"detail={steps[1]['detail']}")
    test("Step 3 跳过分析", "跳过" in steps[2]["detail"] or "已有" in steps[2]["detail"],
         f"detail={steps[2]['detail']}")

# ──────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"结果：✅ {passed} 通过 / ❌ {failed} 失败")
print(f"{'='*50}")
sys.exit(1 if failed > 0 else 0)
