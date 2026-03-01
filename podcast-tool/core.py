"""
共享核心逻辑：任务管理、流水线执行、安全工具
Web 路由和 API 路由共用此模块。
"""

import json
import re
import time
import uuid
import threading
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "output"

# ── 全局任务状态 ──────────────────────────────
tasks = {}

MAX_CONCURRENT_TASKS = 3
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 5
_rate_limit = defaultdict(list)


def check_rate_limit(ip):
    """IP 级别速率限制，返回 True=放行 False=拒绝"""
    now = time.time()
    _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit[ip].append(now)
    return True


def sanitize_error(msg):
    """脱敏错误信息，隐藏内部路径"""
    msg = str(msg)
    msg = msg.replace(str(BASE_DIR), "[APP]")
    msg = msg.replace("/opt/podcast-viz", "[APP]")
    return msg[:200]


def is_valid_episode_id(episode_id):
    return bool(re.fullmatch(r"[a-f0-9]{20,30}", episode_id))


USER_INDEX_PATH = OUTPUT_DIR / ".user_index.json"


def _load_user_index():
    if USER_INDEX_PATH.exists():
        try:
            return json.loads(USER_INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_user_index(index):
    OUTPUT_DIR.mkdir(exist_ok=True)
    USER_INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")


def record_user_episode(uid, episode_id):
    """记录用户生成的 episode"""
    if not uid:
        return
    index = _load_user_index()
    index.setdefault(uid, [])
    if episode_id not in index[uid]:
        index[uid].append(episode_id)
    _save_user_index(index)


def get_history():
    """扫描 output 目录，返回全部历史 episode 列表"""
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
                            "cover_url": m.get("cover_url", ""),
                            "created_at": int(d.stat().st_mtime),
                        })
                    except Exception:
                        pass
    return history


def get_user_history(uid):
    """返回指定用户生成的 episode 列表"""
    index = _load_user_index()
    user_episodes = set(index.get(uid, []))
    return [h for h in get_history() if h["episode_id"] in user_episodes]


# ── 精选样例 ──────────────────────────────────
SHOWCASE_TAGS = {
    "69a34eaa66e2c30377cc4071": ["国际", "时政"],      # 美国为什么打伊朗
    "699beb2c66e2c3037715508a": ["家庭", "成长"],      # 和马女士聊天
    "6914ab11cbba038b4242c92c": ["商业", "餐饮"],      # 达美乐中国
    "6900bb4e740634ca476f82de": ["科学", "思维"],      # 贝叶斯定理
    "6895a38746542d8c4120d691": ["习惯", "成长"],      # 李笑来x脱不花
    "6985a3ab88663289fe893c16": ["故事", "日本"],      # 妈妈桑
}


def get_showcase():
    """返回带标签的精选样例列表"""
    showcase = []
    for item in get_history():
        eid = item["episode_id"]
        if eid in SHOWCASE_TAGS:
            item["tags"] = SHOWCASE_TAGS[eid]
            showcase.append(item)
    return showcase


def create_task(url, uid=""):
    """创建新任务并启动后台流水线，返回 task_id"""
    task_id = str(uuid.uuid4())[:8]
    now = time.time()
    tasks[task_id] = {
        "status": "started",
        "url": url,
        "uid": uid,
        "steps": [
            {"name": "获取元数据", "status": "pending", "detail": ""},
            {"name": "音频转录", "status": "pending", "detail": ""},
            {"name": "AI 内容分析", "status": "pending", "detail": ""},
            {"name": "生成可视化", "status": "pending", "detail": ""},
        ],
        "episode_id": None,
        "error": None,
        "metadata": None,
        "started_at": now,
        "step_started_at": now,
    }

    thread = threading.Thread(target=_run_pipeline, args=(task_id, url), daemon=True)
    thread.start()

    return task_id


def check_cache(url):
    """检查 URL 对应的 episode 是否已生成，返回 episode_id 或 None"""
    episode_id = url.split("/episode/")[-1].split("?")[0].strip("/")
    if is_valid_episode_id(episode_id):
        viz_path = OUTPUT_DIR / episode_id / "visualization.html"
        if viz_path.exists():
            return episode_id
    return None


# ── 流水线 ────────────────────────────────────

def _update_step(task_id, step_index, status, detail=""):
    tasks[task_id]["steps"][step_index]["status"] = status
    tasks[task_id]["steps"][step_index]["detail"] = detail
    if status == "running":
        tasks[task_id]["step_started_at"] = time.time()


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
            "duration_sec": metadata.get("duration_sec", 0),
        }

        if not metadata.get("audio_url"):
            raise RuntimeError("无法获取音频直链，可能为付费内容")

        output_dir = OUTPUT_DIR / episode_id
        output_dir.mkdir(parents=True, exist_ok=True)

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
        record_user_episode(tasks[task_id].get("uid", ""), episode_id)

    except Exception as e:
        safe_msg = sanitize_error(e)
        tasks[task_id]["error"] = safe_msg
        tasks[task_id]["status"] = "error"
        for step in tasks[task_id]["steps"]:
            if step["status"] == "running":
                step["status"] = "error"
                step["detail"] = safe_msg[:100]
