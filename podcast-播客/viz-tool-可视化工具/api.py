"""
API 路由 — 小程序端（JSON）
"""

import json

from flask import Blueprint, request, jsonify

from core import (
    OUTPUT_DIR, tasks,
    MAX_CONCURRENT_TASKS, check_rate_limit,
    is_valid_episode_id, get_history, create_task, check_cache,
)

api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/history")
def history():
    return jsonify({"episodes": get_history()})


@api.route("/process", methods=["POST"])
def process():
    client_ip = request.headers.get("X-Real-IP", request.remote_addr)
    if not check_rate_limit(client_ip):
        return jsonify({"error": "请求过于频繁，请稍后再试"}), 429

    active = sum(1 for t in tasks.values() if t["status"] == "started")
    if active >= MAX_CONCURRENT_TASKS:
        return jsonify({"error": "当前处理任务较多，请稍后再试"}), 503

    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if len(url) > 200 or not url.startswith("https://www.xiaoyuzhoufm.com/episode/"):
        return jsonify({"error": "请输入有效的小宇宙单集链接"}), 400

    cached = check_cache(url)
    if cached:
        return jsonify({"episode_id": cached, "cached": True})

    task_id = create_task(url)
    return jsonify({"task_id": task_id})


@api.route("/status/<task_id>")
def status(task_id):
    """轮询任务进度"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"done": True, "error": "Task not found"})
    return jsonify({
        "steps": task["steps"],
        "episode_id": task["episode_id"],
        "error": task["error"],
        "metadata": task["metadata"],
        "done": task["status"] in ("done", "error"),
    })


@api.route("/episode/<episode_id>")
def episode(episode_id):
    """返回完整 episode 数据"""
    if not is_valid_episode_id(episode_id):
        return jsonify({"error": "无效 ID"}), 400
    json_path = (OUTPUT_DIR / episode_id / "episode.json").resolve()
    if not str(json_path).startswith(str(OUTPUT_DIR.resolve())) or not json_path.exists():
        return jsonify({"error": "未找到"}), 404
    data = json.loads(json_path.read_text(encoding="utf-8"))
    from generator import prepare_episode_data
    data = prepare_episode_data(data)
    return jsonify(data)
