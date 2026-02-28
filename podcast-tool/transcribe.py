#!/usr/bin/env python3
"""
Deepgram 音频转录脚本 (兼容 SDK v5.x)
用于 Claude Code Skill
"""

import os
import sys
import json
import argparse
from datetime import datetime, date, timedelta
from deepgram import DeepgramClient
from deepgram.core.request_options import RequestOptions

# Nova-3 支持的语言列表（中文暂不支持 Nova-3，实测 2026-02 确认）
NOVA3_LANGUAGES = {
    "en", "es", "fr", "de", "it", "pt", "nl", "ja", "ko", "ru",
    "sv", "da", "no", "fi", "pl", "tr", "uk", "cs", "el", "ro",
    "hu", "bg", "hr", "sk", "sl", "lt", "lv", "et", "hi", "ta",
    "te", "bn", "th", "vi", "id", "ms", "tl", "ar", "he",
}


class DateTimeEncoder(json.JSONEncoder):
    """处理 Deepgram response 中的 datetime 对象"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def format_timestamp(seconds):
    """将秒数格式化为 HH:MM:SS 或 MM:SS"""
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def pick_model(language):
    """根据语言选择最佳模型"""
    if language in NOVA3_LANGUAGES:
        return "nova-3"
    return "nova-2"


def transcribe_audio(url, language="zh", output_prefix="transcript", output_dir="."):
    """
    使用 Deepgram 转录音频（兼容 SDK v5.x）

    Args:
        url: 音频文件 URL
        language: 语言代码 (zh=中文, en=英语, 等)
        output_prefix: 输出文件名前缀
        output_dir: 输出目录

    Returns:
        dict: 转录结果摘要
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        return {"success": False, "error": "DEEPGRAM_API_KEY 环境变量未设置"}

    model = pick_model(language)
    print(f"开始转录...")
    print(f"  URL: {url}")
    print(f"  语言: {language} | 模型: {model}")
    print(f"  处理中，请等待...\n")

    try:
        client = DeepgramClient(api_key=api_key)

        def _call_deepgram(use_model):
            return client.listen.v1.media.transcribe_url(
                url=url,
                model=use_model,
                language=language,
                smart_format=True,
                punctuate=True,
                paragraphs=True,
                diarize=True,
                request_options=RequestOptions(timeout_in_seconds=3600),
            )

        # 尝试 Nova-3，不支持则自动回退 Nova-2
        try:
            response = _call_deepgram(model)
        except Exception as e:
            err_msg = str(e).lower()
            if model == "nova-3" and ("no such model" in err_msg or "bad request" in err_msg):
                print(f"  Nova-3 不支持 {language}，回退到 Nova-2...")
                model = "nova-2"
                response = _call_deepgram(model)
            else:
                raise

        # 转为 dict（兼容不同版本）
        if hasattr(response, "dict"):
            result = response.dict()
        elif hasattr(response, "to_dict"):
            result = response.to_dict()
        else:
            result = json.loads(json.dumps(response, default=str))

        # 保存文件
        txt_path = os.path.join(output_dir, f"{output_prefix}.txt")
        json_path = os.path.join(output_dir, f"{output_prefix}.json")

        save_json(result, json_path)
        stats = save_txt(result, txt_path)

        duration_sec = result.get("metadata", {}).get("duration", 0)
        duration_str = format_timestamp(duration_sec)

        print(f"转录完成！")
        print(f"  文本文件: {txt_path}")
        print(f"  JSON文件: {json_path}")
        print(f"  时长: {duration_str}")
        print(f"  字符数: {stats['char_count']:,}")
        print(f"  段落数: {stats['para_count']}")
        print(f"  置信度: {stats['confidence']:.1%}")

        return {
            "success": True,
            "txt_file": txt_path,
            "json_file": json_path,
            "duration": duration_str,
            "duration_sec": duration_sec,
            "char_count": stats["char_count"],
            "para_count": stats["para_count"],
            "confidence": stats["confidence"],
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def save_json(result, path):
    """保存 JSON（处理 datetime 序列化）"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)


def save_txt(result, path):
    """保存易读的 TXT 文件，返回统计信息"""
    channels = result.get("results", {}).get("channels", [])
    if not channels:
        with open(path, "w", encoding="utf-8") as f:
            f.write("（无转录结果）\n")
        return {"char_count": 0, "para_count": 0, "confidence": 0}

    alt = channels[0].get("alternatives", [{}])[0]
    transcript = alt.get("transcript", "")
    confidence = alt.get("confidence", 0)

    paragraphs_data = alt.get("paragraphs", {})
    paragraphs_list = paragraphs_data.get("paragraphs", []) if paragraphs_data else []

    with open(path, "w", encoding="utf-8") as f:
        # 分段版本（带时间戳 + 说话人）
        if paragraphs_list:
            for para in paragraphs_list:
                speaker = para.get("speaker", "?")
                start = format_timestamp(para.get("start", 0))
                end = format_timestamp(para.get("end", 0))

                sentences = para.get("sentences", [])
                text = "".join(s.get("text", "") for s in sentences)

                f.write(f"[{start} - {end}] 说话人{speaker}\n")
                f.write(f"{text}\n\n")
        else:
            f.write(transcript + "\n")

    return {
        "char_count": len(transcript),
        "para_count": len(paragraphs_list),
        "confidence": confidence,
    }


def main():
    parser = argparse.ArgumentParser(description="Deepgram 音频转录")
    parser.add_argument("url", help="音频文件 URL")
    parser.add_argument("--language", "-l", default="zh", help="语言代码 (默认: zh)")
    parser.add_argument("--output-prefix", "-p", default="transcript", help="输出文件名前缀 (默认: transcript)")
    parser.add_argument("--output-dir", "-o", default=".", help="输出目录 (默认: 当前目录)")

    args = parser.parse_args()
    result = transcribe_audio(args.url, args.language, args.output_prefix, args.output_dir)

    if result["success"]:
        sys.exit(0)
    else:
        print(f"转录失败: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
