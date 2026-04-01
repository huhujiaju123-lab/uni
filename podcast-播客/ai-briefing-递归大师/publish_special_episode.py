#!/usr/bin/env python3
"""单次特别版发布脚本。

目的：
1. 复用递归大师既有 TTS / 上传 / RSS 链路
2. 不改日更 cron 入口
3. 允许特别版使用独立 slug，避免占用当天常规档期
"""

import argparse
import asyncio
import json
import subprocess
from pathlib import Path

import daily_pipeline as dp


BASE_DIR = Path(__file__).parent


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    return (BASE_DIR / path).resolve()


def build_plan(config: dict) -> dict:
    return {
        "title": config["title"],
        "description": config["description"],
        "topics": config.get("topics", []),
    }


def retime_remote_episode(slug: str, remote_touch: str):
    if not remote_touch:
        return
    command = (
        f"touch -t {remote_touch} "
        f"{dp.SERVER_PODCAST_DIR}/episodes/{slug}.mp3 "
        f"{dp.SERVER_PODCAST_DIR}/episodes/{slug}.json && "
        f"python3 {dp.SERVER_PODCAST_DIR}/rss-generator.py"
    )
    result = subprocess.run(
        [
            "sshpass",
            "-p",
            dp.SERVER_PASS,
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            f"root@{dp.SERVER}",
            command,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "remote retime failed")


def main():
    parser = argparse.ArgumentParser(description="生成或发布递归大师特别版")
    parser.add_argument("config", help="特别版配置 JSON")
    parser.add_argument("--publish", action="store_true", help="上传服务器并更新 RSS")
    parser.add_argument("--push-feishu", action="store_true", help="发布后推送飞书")
    args = parser.parse_args()

    config_path = resolve_path(args.config)
    config = load_json(config_path)
    script_path = resolve_path(config["script_path"])
    script = load_json(script_path)
    plan = build_plan(config)
    slug = config["slug"]

    dp.TODAY = slug

    print("=" * 50)
    print("递归大师特别版")
    print(f"slug: {slug}")
    print(f"title: {plan['title']}")
    print("=" * 50)

    passed, warnings = dp.validate_script(script)
    if not passed:
        raise SystemExit(f"脚本未通过质量检查: {warnings}")

    if warnings:
        print("质量提示：")
        for warning in warnings:
            print(f"  - {warning}")

    mp3_path, duration = asyncio.run(dp.generate_audio(script))
    dp.save_script_text(script, plan)

    if not args.publish:
        print("已完成本地音频生成，未执行正式发布。")
        print(f"音频: {mp3_path}")
        print(f"时长: {duration // 60}分{duration % 60}秒")
        return

    title = dp.upload_to_server(mp3_path, duration, script, plan)
    retime_remote_episode(slug, config.get("remote_touch", ""))

    if args.push_feishu or config.get("notify_feishu", False):
        mp3_url = f"http://{dp.SERVER}:8081/podcast/episodes/{slug}.mp3"
        dp.push_to_feishu(title, mp3_url, duration, warnings)

    print("特别版已发布。")
    print(f"RSS: http://podcast.huhu.world/podcast/feed.xml")


if __name__ == "__main__":
    main()
