#!/usr/bin/env python3
"""转录小宇宙播客音频 - Deepgram SDK v5"""

import os
import json
import sys
from datetime import datetime, date
from deepgram import DeepgramClient
from deepgram.core.request_options import RequestOptions

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

AUDIO_URL = "https://media.xyzcdn.net/65a5fb7540d4ef949c0140ac/lgVw1W2F0SWH2xxhUjgG5Vyo3zdC.m4a"
OUTPUT_TXT = "podcast_transcript.txt"
OUTPUT_JSON = "podcast_transcript.json"

def main():
    api_key = os.environ.get("DEEPGRAM_API_KEY")
    if not api_key:
        print("错误：未设置 DEEPGRAM_API_KEY")
        sys.exit(1)

    print("开始转录播客...")
    print(f"音频URL: {AUDIO_URL}")
    print(f"预计时长: ~89分钟，请耐心等待...")

    client = DeepgramClient(api_key=api_key)

    response = client.listen.v1.media.transcribe_url(
        url=AUDIO_URL,
        model="nova-2",
        language="zh",
        smart_format=True,
        diarize=True,
        paragraphs=True,
        punctuate=True,
        utterances=True,
        request_options=RequestOptions(timeout=600),
    )

    # 转为 dict
    if hasattr(response, 'dict'):
        result = response.dict()
    elif hasattr(response, 'to_dict'):
        result = response.to_dict()
    else:
        result = json.loads(json.dumps(response, default=str))

    # 保存 JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    # 提取结果
    channels = result.get("results", {}).get("channels", [])
    if not channels:
        print("错误：未获取到转录结果")
        sys.exit(1)

    alt = channels[0].get("alternatives", [{}])[0]
    transcript = alt.get("transcript", "")
    confidence = alt.get("confidence", 0)

    paragraphs_data = alt.get("paragraphs", {})
    paragraphs_list = paragraphs_data.get("paragraphs", []) if paragraphs_data else []

    # 生成文本
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("播客转录：59 一生之敌｜没有天赋、不谈热爱，凡人的突围只有与自我的持久厮杀\n")
        f.write("=" * 60 + "\n\n")

        if paragraphs_list:
            f.write("【分段转录（带时间戳和说话人）】\n\n")
            for para in paragraphs_list:
                speaker = para.get("speaker", "?")
                start = para.get("start", 0)
                end = para.get("end", 0)
                start_min, start_sec = divmod(int(start), 60)
                end_min, end_sec = divmod(int(end), 60)

                sentences = para.get("sentences", [])
                text = "".join(s.get("text", "") for s in sentences)

                f.write(f"[{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}] 说话人 {speaker}\n")
                f.write(f"{text}\n\n")
        else:
            f.write("【完整转录】\n\n")
            f.write(transcript + "\n")

    char_count = len(transcript)
    duration_sec = result.get("metadata", {}).get("duration", 0)
    duration_min = int(duration_sec) // 60
    duration_s = int(duration_sec) % 60

    print(f"\n转录完成！")
    print(f"  文本文件: {OUTPUT_TXT}")
    print(f"  JSON文件: {OUTPUT_JSON}")
    print(f"  时长: {duration_min}分{duration_s}秒")
    print(f"  字符数: {char_count:,}")
    print(f"  置信度: {confidence:.1%}")

if __name__ == "__main__":
    main()
