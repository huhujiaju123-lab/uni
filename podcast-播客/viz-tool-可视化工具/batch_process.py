#!/usr/bin/env python3
"""
批量预计算脚本 — 从 top_podcasts.json 读取播客列表，逐个处理最新 episode。
用完 Deepgram 额度前尽量多跑。

用法：
  python3 batch_process.py                    # 每个播客跑最新 3 集
  python3 batch_process.py --per-podcast 5    # 每个播客跑最新 5 集
  python3 batch_process.py --start 10         # 从第 10 名开始跑
  python3 batch_process.py --dry-run          # 只列出要跑的 episode，不实际处理
"""

import json
import re
import sys
import os
import time
import argparse
from pathlib import Path

# 确保能 import 同目录模块
sys.path.insert(0, str(Path(__file__).parent))

import httpx
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "output"
TOP_PODCASTS = BASE_DIR / "top_podcasts.json"
PROGRESS_FILE = BASE_DIR / "batch_progress.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def is_valid_episode_id(eid):
    return bool(re.fullmatch(r"[a-f0-9]{20,30}", eid))


def is_already_processed(episode_id):
    """检查是否已有完整的可视化文件"""
    viz = OUTPUT_DIR / episode_id / "visualization.html"
    return viz.exists()


def fetch_episode_list(podcast_url, limit=5):
    """从小宇宙播客主页抓取最新 episode 列表"""
    print(f"  📡 抓取 episode 列表: {podcast_url}")
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
            resp = client.get(podcast_url)
            resp.raise_for_status()
    except Exception as e:
        print(f"  ❌ 抓取失败: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    episodes = []
    seen = set()

    # 从页面中提取所有 episode 链接
    for tag in soup.find_all(["a", "link"], href=True):
        href = tag["href"]
        match = re.search(r"/episode/([a-f0-9]{20,30})", href)
        if match:
            eid = match.group(1)
            if eid not in seen:
                seen.add(eid)
                episodes.append({
                    "id": eid,
                    "url": f"https://www.xiaoyuzhoufm.com/episode/{eid}",
                })

    # 也从页面文本中正则搜索
    for match in re.finditer(r"/episode/([a-f0-9]{20,30})", resp.text):
        eid = match.group(1)
        if eid not in seen:
            seen.add(eid)
            episodes.append({
                "id": eid,
                "url": f"https://www.xiaoyuzhoufm.com/episode/{eid}",
            })

    print(f"  📋 找到 {len(episodes)} 个 episode")
    return episodes[:limit]


def process_episode(episode_url):
    """调用现有流水线处理单个 episode"""
    from fetcher import fetch_metadata
    from transcribe import transcribe_audio
    from analyzer import analyze_transcript
    from generator import render

    # Step 1: 元数据
    metadata = fetch_metadata(episode_url)
    episode_id = metadata["episode_id"]

    if not metadata.get("audio_url"):
        print(f"  ⚠️  跳过（无音频/付费内容）: {metadata.get('title', '')[:40]}")
        return {"status": "skipped", "reason": "no_audio", "episode_id": episode_id}

    output_dir = OUTPUT_DIR / episode_id
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Step 2: 转录
    txt_path = output_dir / "transcript.txt"
    if txt_path.exists() and txt_path.stat().st_size > 100:
        print(f"  ⏭️  转录文件已存在，跳过")
    else:
        print(f"  🎙️  Deepgram 转录中...")
        tr_result = transcribe_audio(
            url=metadata["audio_url"],
            language="zh",
            output_prefix="transcript",
            output_dir=str(output_dir),
        )
        if not tr_result["success"]:
            error = tr_result["error"]
            # 检测额度用完
            if "402" in str(error) or "insufficient" in str(error).lower() or "quota" in str(error).lower():
                print(f"\n🚫 Deepgram 额度已用完！")
                return {"status": "quota_exhausted", "episode_id": episode_id}
            raise RuntimeError(f"转录失败: {error}")

    # Step 3: AI 分析
    episode_json_path = output_dir / "episode.json"
    if episode_json_path.exists() and episode_json_path.stat().st_size > 100:
        print(f"  ⏭️  分析文件已存在，跳过")
    else:
        print(f"  🤖 AI 分析中...")
        analyze_transcript(str(txt_path), str(episode_json_path), metadata)

    # Step 4: 生成 HTML
    viz_path = output_dir / "visualization.html"
    print(f"  🎨 生成可视化...")
    render(str(episode_json_path), str(viz_path))

    duration = metadata.get("duration_sec", 0)
    cost = round(duration / 60 * 0.0056, 3) if duration else 0
    print(f"  ✅ 完成! 时长 {duration//60}分{duration%60}秒, 预估 Deepgram 成本 ${cost}")

    return {
        "status": "done",
        "episode_id": episode_id,
        "title": metadata.get("title", ""),
        "duration_sec": duration,
        "cost_usd": cost,
    }


def load_progress():
    """加载进度文件"""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {"processed": [], "skipped": [], "failed": [], "total_cost_usd": 0}


def save_progress(progress):
    """保存进度"""
    PROGRESS_FILE.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description="批量预计算播客可视化")
    parser.add_argument("--per-podcast", type=int, default=3, help="每个播客处理最新几集 (默认 3)")
    parser.add_argument("--start", type=int, default=1, help="从第几名播客开始 (默认 1)")
    parser.add_argument("--end", type=int, default=None, help="到第几名播客结束")
    parser.add_argument("--dry-run", action="store_true", help="只列出要跑的 episode，不实际处理")
    args = parser.parse_args()

    # 加载播客列表
    podcasts = json.loads(TOP_PODCASTS.read_text(encoding="utf-8"))
    podcasts = [p for p in podcasts if p["rank"] >= args.start]
    if args.end:
        podcasts = [p for p in podcasts if p["rank"] <= args.end]

    print(f"{'='*60}")
    print(f"  批量预计算 — {len(podcasts)} 个播客, 每个最新 {args.per_podcast} 集")
    print(f"{'='*60}\n")

    progress = load_progress()
    processed_ids = set(progress["processed"])
    total_cost = progress["total_cost_usd"]
    total_done = 0
    total_skipped = 0

    for podcast in podcasts:
        name = podcast["name"]
        rank = podcast["rank"]
        url = podcast["podcast_url"]

        print(f"\n{'─'*60}")
        print(f"🎧 [{rank}] {name} ({podcast.get('subscribers', '')})")
        print(f"   {url}")

        # 获取 episode 列表
        episodes = fetch_episode_list(url, limit=args.per_podcast)
        if not episodes:
            print(f"  ⚠️  未找到 episode，跳过")
            continue

        for ep in episodes:
            eid = ep["id"]

            # 跳过已处理的
            if eid in processed_ids or is_already_processed(eid):
                print(f"  ⏭️  已处理: {eid[:12]}...")
                total_skipped += 1
                continue

            if args.dry_run:
                print(f"  📝 待处理: {ep['url']}")
                continue

            # 处理
            print(f"\n  ▶ 处理: {ep['url']}")
            try:
                result = process_episode(ep["url"])

                if result["status"] == "quota_exhausted":
                    print(f"\n{'='*60}")
                    print(f"  Deepgram 额度已用完!")
                    print(f"  本次共处理: {total_done} 集")
                    print(f"  累计预估成本: ${total_cost:.3f}")
                    print(f"{'='*60}")
                    save_progress(progress)
                    sys.exit(0)

                if result["status"] == "done":
                    total_done += 1
                    cost = result.get("cost_usd", 0)
                    total_cost += cost
                    progress["processed"].append(eid)
                    progress["total_cost_usd"] = round(total_cost, 3)
                    processed_ids.add(eid)
                elif result["status"] == "skipped":
                    progress["skipped"].append(eid)
                    total_skipped += 1

            except Exception as e:
                print(f"  ❌ 失败: {e}")
                progress["failed"].append({"id": eid, "error": str(e)[:200]})

            # 每集处理完保存进度
            save_progress(progress)

            # 请求间隔，避免被风控
            time.sleep(2)

        # 播客间隔
        time.sleep(3)

    # 最终汇总
    print(f"\n{'='*60}")
    print(f"  批量处理完成!")
    print(f"  处理成功: {total_done} 集")
    print(f"  跳过: {total_skipped} 集")
    print(f"  失败: {len(progress['failed'])} 集")
    print(f"  累计 Deepgram 预估成本: ${total_cost:.3f} (¥{total_cost*7.1:.1f})")
    print(f"{'='*60}")
    save_progress(progress)


if __name__ == "__main__":
    main()
