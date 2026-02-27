#!/usr/bin/env python3
"""
播客可视化 Web 平台
启动：python3 app.py
访问：http://localhost:5000
"""

import os
import sys
import json
import re
import uuid
import time
import threading
from collections import defaultdict
from pathlib import Path

from flask import Flask, request, render_template, redirect, url_for, Response, send_file, jsonify

# 项目路径
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "output"

sys.path.insert(0, str(BASE_DIR))

app = Flask(__name__)

# 全局任务状态存储
tasks = {}

# ──────────────────────────────────────────────
# 安全：速率限制 + 并发限制
# ──────────────────────────────────────────────
MAX_CONCURRENT_TASKS = 3
RATE_LIMIT_WINDOW = 60   # 秒
RATE_LIMIT_MAX = 5       # 每 IP 每窗口最多请求数

_rate_limit = defaultdict(list)


def _check_rate_limit(ip):
    """IP 级别速率限制，返回 True=放行 False=拒绝"""
    now = time.time()
    _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit[ip].append(now)
    return True


def _sanitize_error(msg):
    """脱敏错误信息，隐藏内部路径"""
    msg = str(msg)
    msg = msg.replace(str(BASE_DIR), "[APP]")
    msg = msg.replace("/opt/podcast-viz", "[APP]")
    return msg[:200]


# ──────────────────────────────────────────────
# 安全响应头
# ──────────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ──────────────────────────────────────────────
# 路由
# ──────────────────────────────────────────────

@app.route("/")
def index():
    """首页 — 输入框"""
    # 收集已生成的历史记录
    history = []
    if OUTPUT_DIR.exists():
        for d in sorted(OUTPUT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if d.is_dir():
                viz = d / "visualization.html"
                meta = d / "metadata.json"
                if viz.exists() and meta.exists():
                    try:
                        m = json.loads(meta.read_text(encoding="utf-8"))
                        history.append({
                            "episode_id": d.name,
                            "title": m.get("title", "未知标题"),
                            "podcast_name": m.get("podcast_name", ""),
                        })
                    except Exception:
                        pass
    return render_template("index.html", history=history)


@app.route("/process", methods=["POST"])
def process():
    """接收 URL，启动后台任务"""
    # 速率限制
    client_ip = request.headers.get("X-Real-IP", request.remote_addr)
    if not _check_rate_limit(client_ip):
        return render_template("index.html", error="请求过于频繁，请稍后再试", history=[])

    # 并发限制
    active = sum(1 for t in tasks.values() if t["status"] == "started")
    if active >= MAX_CONCURRENT_TASKS:
        return render_template("index.html", error="当前处理任务较多，请稍后再试", history=[])

    url = request.form.get("url", "").strip()
    if len(url) > 200 or not url.startswith("https://www.xiaoyuzhoufm.com/episode/"):
        return render_template("index.html", error="请输入有效的小宇宙单集链接", history=[])

    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "status": "started",
        "url": url,
        "steps": [
            {"name": "获取元数据", "status": "pending", "detail": ""},
            {"name": "音频转录", "status": "pending", "detail": ""},
            {"name": "AI 内容分析", "status": "pending", "detail": ""},
            {"name": "生成可视化", "status": "pending", "detail": ""},
        ],
        "episode_id": None,
        "error": None,
        "metadata": None,
    }

    thread = threading.Thread(target=_run_pipeline, args=(task_id, url), daemon=True)
    thread.start()

    return redirect(url_for("progress", task_id=task_id))


@app.route("/progress/<task_id>")
def progress(task_id):
    """进度页面"""
    if task_id not in tasks:
        return redirect(url_for("index"))
    return render_template("progress.html", task_id=task_id)


@app.route("/stream/<task_id>")
def stream(task_id):
    """SSE 端点 — 推送实时进度"""
    def generate():
        last_sent = ""
        while True:
            task = tasks.get(task_id)
            if not task:
                yield f"data: {json.dumps({'done': True, 'error': 'Task not found'})}\n\n"
                break

            payload = json.dumps({
                "steps": task["steps"],
                "episode_id": task["episode_id"],
                "error": task["error"],
                "metadata": task["metadata"],
                "done": task["status"] in ("done", "error"),
            }, ensure_ascii=False)

            if payload != last_sent:
                yield f"data: {payload}\n\n"
                last_sent = payload

            if task["status"] in ("done", "error"):
                break

            time.sleep(1)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/view/<episode_id>")
def view(episode_id):
    """展示生成的可视化网页"""
    # 安全：白名单校验 episode_id（小宇宙 ID 为 24 位十六进制）
    if not re.fullmatch(r"[a-f0-9]{20,30}", episode_id):
        return redirect(url_for("index"))
    html_path = (OUTPUT_DIR / episode_id / "visualization.html").resolve()
    # 安全：确保路径在 OUTPUT_DIR 内，防止遍历
    if not str(html_path).startswith(str(OUTPUT_DIR.resolve())):
        return redirect(url_for("index"))
    if not html_path.exists():
        return redirect(url_for("index"))
    return send_file(html_path, mimetype="text/html")


# ──────────────────────────────────────────────
# 后台流水线
# ──────────────────────────────────────────────

def _update_step(task_id, step_index, status, detail=""):
    tasks[task_id]["steps"][step_index]["status"] = status
    tasks[task_id]["steps"][step_index]["detail"] = detail


def _run_pipeline(task_id, url):
    """后台执行 4 步流水线"""
    try:
        # Step 1: 获取元数据
        _update_step(task_id, 0, "running", "正在访问小宇宙...")
        from fetcher import fetch_metadata
        metadata = fetch_metadata(url)
        episode_id = metadata["episode_id"]
        tasks[task_id]["episode_id"] = episode_id
        tasks[task_id]["metadata"] = {
            "title": metadata.get("title", ""),
            "podcast_name": metadata.get("podcast_name", ""),
        }

        if not metadata.get("audio_url"):
            raise RuntimeError("无法获取音频直链，可能为付费内容")

        output_dir = OUTPUT_DIR / episode_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存元数据
        (output_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _update_step(task_id, 0, "done", metadata.get("title", "")[:40])

        # Step 2: 转录
        txt_path = output_dir / "transcript.txt"
        if txt_path.exists() and txt_path.stat().st_size > 100:
            _update_step(task_id, 1, "done", "已有转录文件，跳过")
        else:
            _update_step(task_id, 1, "running", "Deepgram 转录中，请耐心等待...")
            from transcribe import transcribe_audio
            tr_result = transcribe_audio(
                url=metadata["audio_url"],
                language="zh",
                output_prefix="transcript",
                output_dir=str(output_dir),
            )
            if not tr_result["success"]:
                raise RuntimeError(f"转录失败：{tr_result['error']}")
            _update_step(task_id, 1, "done", f"转录完成 · {tr_result.get('duration', '')}")

        # Step 3: AI 分析
        episode_json_path = output_dir / "episode.json"
        if episode_json_path.exists() and episode_json_path.stat().st_size > 100:
            _update_step(task_id, 2, "done", "已有分析文件，跳过")
        else:
            _update_step(task_id, 2, "running", "AI 正在分析内容...")
            from analyzer import analyze_transcript
            analyze_transcript(str(txt_path), str(episode_json_path), metadata)
            _update_step(task_id, 2, "done", "分析完成")

        # Step 4: 生成 HTML
        _update_step(task_id, 3, "running", "渲染可视化网页...")
        from generator import render
        render(str(episode_json_path), str(output_dir / "visualization.html"))
        _update_step(task_id, 3, "done", "生成完成")

        tasks[task_id]["status"] = "done"

    except Exception as e:
        safe_msg = _sanitize_error(e)
        tasks[task_id]["error"] = safe_msg
        tasks[task_id]["status"] = "error"
        for step in tasks[task_id]["steps"]:
            if step["status"] == "running":
                step["status"] = "error"
                step["detail"] = safe_msg[:100]


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("🎙️  播客可视化平台启动中...")
    print("   访问 http://localhost:5000")
    app.run(debug=True, port=5000, threaded=True)
