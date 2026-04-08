#!/usr/bin/env python3
"""
并发回测脚本 — 模拟多线程下 task 共享问题
验证：POST 创建的 task 能被 SSE stream 和 progress 页面正确读取
"""

import sys
import json
import time
import threading
sys.path.insert(0, ".")

from app import app, tasks

app.config["TESTING"] = True

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
print("\n=== 1. 模拟并发：POST 创建 task + 立即 SSE 读取 ===")
# ──────────────────────────────────────────────
with app.test_client() as c:
    # 提交任务
    resp = c.post(
        "/process",
        data={"url": "https://www.xiaoyuzhoufm.com/episode/698b27ae66e2c30377d88131"},
        follow_redirects=False,
    )
    location = resp.headers.get("Location", "")
    task_id = location.split("/progress/")[-1] if "/progress/" in location else None
    test("POST 创建 task", task_id is not None and task_id in tasks)

    if task_id:
        # 模拟另一个"线程"来读取 SSE（在同一进程内）
        resp_sse = c.get(f"/stream/{task_id}")
        sse_data = resp_sse.data.decode("utf-8")
        test("SSE 能找到 task", "Task not found" not in sse_data, f"got: {sse_data[:200]}")

        lines = [l for l in sse_data.strip().split("\n") if l.startswith("data:")]
        if lines:
            first_msg = json.loads(lines[0].replace("data: ", ""))
            test("SSE 有 steps 数据", "steps" in first_msg, f"msg={first_msg}")
            test("SSE error 为 None", first_msg.get("error") is None, f"error={first_msg.get('error')}")

        # 模拟 progress 页面读取
        resp_prog = c.get(f"/progress/{task_id}")
        test("progress 页面 200", resp_prog.status_code == 200)


# ──────────────────────────────────────────────
print("\n=== 2. 连续创建多个 task，全部可追踪 ===")
# ──────────────────────────────────────────────
with app.test_client() as c:
    task_ids = []
    for i in range(3):
        resp = c.post(
            "/process",
            data={"url": "https://www.xiaoyuzhoufm.com/episode/698b27ae66e2c30377d88131"},
            follow_redirects=False,
        )
        loc = resp.headers.get("Location", "")
        tid = loc.split("/progress/")[-1] if "/progress/" in loc else None
        task_ids.append(tid)

    test("创建了 3 个 task", len([t for t in task_ids if t]) == 3)
    test("3 个 task_id 互不相同", len(set(task_ids)) == 3, f"ids={task_ids}")

    # 全部可以通过 SSE 访问
    all_found = True
    for tid in task_ids:
        resp = c.get(f"/stream/{tid}")
        data = resp.data.decode("utf-8")
        if "Task not found" in data:
            all_found = False
    test("所有 task 通过 SSE 可读", all_found)


# ──────────────────────────────────────────────
print("\n=== 3. 手动模拟 task 生命周期 ===")
# ──────────────────────────────────────────────
# 直接往 tasks dict 插入，模拟完整生命周期
test_task_id = "test-lifecycle-001"
tasks[test_task_id] = {
    "status": "started",
    "url": "https://example.com",
    "steps": [
        {"name": "Step1", "status": "running", "detail": "进行中"},
        {"name": "Step2", "status": "pending", "detail": ""},
    ],
    "episode_id": None,
    "error": None,
    "metadata": None,
}

with app.test_client() as c:
    # SSE 读取 running 状态
    # 先把 task 标记完成，否则 SSE 会阻塞
    tasks[test_task_id]["status"] = "done"
    tasks[test_task_id]["steps"][0]["status"] = "done"
    tasks[test_task_id]["steps"][1]["status"] = "done"
    tasks[test_task_id]["episode_id"] = "test-ep"

    resp = c.get(f"/stream/{test_task_id}")
    data = resp.data.decode("utf-8")
    test("手动 task SSE 正常", "Task not found" not in data)

    lines = [l for l in data.strip().split("\n") if l.startswith("data:")]
    if lines:
        msg = json.loads(lines[-1].replace("data: ", ""))
        test("手动 task done=True", msg.get("done") is True)
        test("手动 task episode_id", msg.get("episode_id") == "test-ep")

# 清理
del tasks[test_task_id]


# ──────────────────────────────────────────────
print("\n=== 4. SSE 对不存在的 task 返回错误 ===")
# ──────────────────────────────────────────────
with app.test_client() as c:
    resp = c.get("/stream/totally-fake-id")
    data = resp.data.decode("utf-8")
    test("不存在 task 返回 Task not found", "Task not found" in data)

    lines = [l for l in data.strip().split("\n") if l.startswith("data:")]
    if lines:
        msg = json.loads(lines[0].replace("data: ", ""))
        test("done=True 结束 SSE", msg.get("done") is True)


# ──────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"并发回测结果：✅ {passed} 通过 / ❌ {failed} 失败")
print(f"{'='*50}")
sys.exit(1 if failed > 0 else 0)
