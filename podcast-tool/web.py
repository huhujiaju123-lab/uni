"""
Web 路由 — 浏览器端（HTML 渲染）
"""

import json
import time
import uuid

from flask import Blueprint, request, render_template, redirect, url_for, Response, send_file, make_response

from core import (
    OUTPUT_DIR, tasks,
    MAX_CONCURRENT_TASKS, check_rate_limit, sanitize_error,
    is_valid_episode_id, get_history, get_user_history, record_user_episode,
    create_task, check_cache, get_showcase,
)

web = Blueprint("web", __name__)

ADMIN_KEY = "lkus2026"


def _get_or_set_uid(resp=None):
    """获取当前用户 uid，如果没有则生成一个"""
    uid = request.cookies.get("uid")
    if not uid:
        uid = uuid.uuid4().hex[:8]
        if resp:
            resp.set_cookie("uid", uid, max_age=365 * 86400, httponly=True, samesite="Lax")
    return uid


@web.route("/")
def index():
    uid = request.cookies.get("uid")
    is_admin = request.args.get("admin") == ADMIN_KEY
    if is_admin:
        history = get_history()
    elif uid:
        history = get_user_history(uid)
    else:
        history = []
    showcase = get_showcase()
    resp = make_response(render_template("index.html", history=history, showcase=showcase))
    if not uid:
        uid = uuid.uuid4().hex[:8]
        resp.set_cookie("uid", uid, max_age=365 * 86400, httponly=True, samesite="Lax")
    return resp


@web.route("/process", methods=["POST"])
def process():
    client_ip = request.headers.get("X-Real-IP", request.remote_addr)
    if not check_rate_limit(client_ip):
        return render_template("index.html", error="请求过于频繁，请稍后再试", history=[])

    active = sum(1 for t in tasks.values() if t["status"] == "started")
    if active >= MAX_CONCURRENT_TASKS:
        return render_template("index.html", error="当前处理任务较多，请稍后再试", history=[])

    url = request.form.get("url", "").strip()
    if len(url) > 200 or not url.startswith("https://www.xiaoyuzhoufm.com/episode/"):
        return render_template("index.html", error="请输入有效的小宇宙单集链接", history=[])

    cached = check_cache(url)
    if cached:
        uid = request.cookies.get("uid", "")
        record_user_episode(uid, cached)
        return redirect(url_for("web.view", episode_id=cached))

    uid = request.cookies.get("uid", "")
    task_id = create_task(url, uid=uid)
    return redirect(url_for("web.progress", task_id=task_id))


@web.route("/progress/<task_id>")
def progress(task_id):
    task = tasks.get(task_id)
    if not task:
        return redirect(url_for("web.index"))
    if task["status"] == "done" and task.get("episode_id"):
        return redirect(url_for("web.view", episode_id=task["episode_id"]))
    return render_template("progress.html", task_id=task_id)


@web.route("/stream/<task_id>")
def stream(task_id):
    """SSE 端点 — 推送实时进度"""
    def generate():
        last_sent = ""
        while True:
            task = tasks.get(task_id)
            if not task:
                yield f"data: {json.dumps({'done': True, 'error': 'Task not found'})}\n\n"
                break

            now = time.time()
            payload = json.dumps({
                "steps": task["steps"],
                "episode_id": task["episode_id"],
                "error": task["error"],
                "metadata": task["metadata"],
                "done": task["status"] in ("done", "error"),
                "elapsed": round(now - task.get("started_at", now)),
                "step_elapsed": round(now - task.get("step_started_at", now)),
            }, ensure_ascii=False)

            if payload != last_sent:
                yield f"data: {payload}\n\n"
                last_sent = payload

            if task["status"] in ("done", "error"):
                break

            time.sleep(1)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@web.route("/view/<episode_id>")
def view(episode_id):
    if not is_valid_episode_id(episode_id):
        return redirect(url_for("web.index"))
    html_path = (OUTPUT_DIR / episode_id / "visualization.html").resolve()
    if not str(html_path).startswith(str(OUTPUT_DIR.resolve())):
        return redirect(url_for("web.index"))
    if not html_path.exists():
        return redirect(url_for("web.index"))
    return send_file(html_path, mimetype="text/html")
