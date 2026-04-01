#!/usr/bin/env python3
"""上传已生成的特别版成片到服务器并更新 RSS。"""

import argparse
import json
import subprocess
from pathlib import Path

import daily_pipeline as dp


BASE_DIR = Path(__file__).parent


def resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    return (BASE_DIR / path).resolve()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_meta(config: dict, duration: int) -> dict:
    description = config["description"]
    topics = config.get("topics", [])
    if topics:
        description += "\n\n话题：\n" + "\n".join(
            ("★ " if t.get("grade") == "S" else "● " if t.get("grade") == "A" else "· ") + t.get("title", "")
            for t in topics
        )
    return {
        "title": config["title"],
        "description": description,
        "duration": duration,
    }


def upload_file(local_path: Path, remote_name: str):
    result = subprocess.run(
        [
            "sshpass",
            "-p",
            dp.SERVER_PASS,
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            str(local_path),
            f"root@{dp.SERVER}:{dp.SERVER_PODCAST_DIR}/episodes/{remote_name}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"failed to upload {local_path.name}")


def remote_finalize(slug: str, remote_touch: str):
    command = f"python3 {dp.SERVER_PODCAST_DIR}/rss-generator.py"
    if remote_touch:
        command = (
            f"touch -t {remote_touch} "
            f"{dp.SERVER_PODCAST_DIR}/episodes/{slug}.mp3 "
            f"{dp.SERVER_PODCAST_DIR}/episodes/{slug}.json && "
            + command
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
        raise RuntimeError(result.stderr.strip() or "remote finalize failed")


def main():
    parser = argparse.ArgumentParser(description="上传已生成的特别版")
    parser.add_argument("config", help="特别版配置 JSON")
    parser.add_argument("mp3", help="本地 mp3 路径")
    parser.add_argument("--duration", type=int, required=True, help="音频时长（秒）")
    args = parser.parse_args()

    config = load_json(resolve_path(args.config))
    mp3_path = resolve_path(args.mp3)
    slug = config["slug"]
    meta = build_meta(config, args.duration)

    meta_path = BASE_DIR / f"meta-{slug}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    upload_file(mp3_path, f"{slug}.mp3")
    upload_file(meta_path, f"{slug}.json")
    remote_finalize(slug, config.get("remote_touch", ""))

    print("特别版上传完成。")
    print(f"slug: {slug}")


if __name__ == "__main__":
    main()
