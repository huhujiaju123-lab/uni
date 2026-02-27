#!/usr/bin/env python3
"""
小宇宙播客元数据获取器
输入：小宇宙单集 URL（https://www.xiaoyuzhoufm.com/episode/xxx）
输出：dict 包含 title, description, audio_url, cover_url, podcast_name, episode_id
"""

import re
import sys
try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ 缺少依赖，请运行：pip install httpx beautifulsoup4")
    sys.exit(1)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def extract_episode_id(url: str) -> str:
    """从 URL 中提取 episode_id"""
    match = re.search(r"/episode/([a-f0-9]+)", url)
    if not match:
        raise ValueError(f"无法从 URL 中提取 episode_id：{url}")
    return match.group(1)


def fetch_metadata(url: str) -> dict:
    """
    获取小宇宙单集元数据

    Returns:
        dict: {
            episode_id, title, description, audio_url,
            cover_url, podcast_name, source_url
        }
    """
    print(f"🔍 正在获取元数据：{url}")

    episode_id = extract_episode_id(url)

    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"请求失败 HTTP {e.response.status_code}：{url}")
    except httpx.RequestError as e:
        raise RuntimeError(f"网络错误：{e}")

    soup = BeautifulSoup(response.text, "html.parser")

    def get_og(property_name: str) -> str:
        tag = soup.find("meta", property=property_name)
        if tag:
            return tag.get("content", "").strip()
        return ""

    title = get_og("og:title")
    description = get_og("og:description")
    audio_url = get_og("og:audio")
    cover_url = get_og("og:image")
    podcast_name = get_og("og:site_name")

    # 备选：从 JSON-LD 提取
    if not audio_url:
        audio_url = _extract_from_jsonld(soup, "contentUrl")

    if not title:
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

    if not audio_url:
        # 正则从页面全文找 media.xyzcdn.net 链接
        match = re.search(r'https://media\.xyzcdn\.net/[^\s"\']+\.m4a', response.text)
        if match:
            audio_url = match.group(0)

    metadata = {
        "episode_id": episode_id,
        "title": title,
        "description": description,
        "audio_url": audio_url,
        "cover_url": cover_url,
        "podcast_name": podcast_name,
        "source_url": url,
    }

    # 输出结果摘要
    print(f"✅ 元数据获取成功")
    print(f"   标题：{title[:60]}{'...' if len(title) > 60 else ''}")
    print(f"   播客：{podcast_name}")
    print(f"   音频：{audio_url[:80] if audio_url else '未找到'}{'...' if audio_url and len(audio_url) > 80 else ''}")

    if not audio_url:
        print("⚠️  警告：未找到音频直链，可能为付费内容")

    return metadata


def _extract_from_jsonld(soup: BeautifulSoup, key: str) -> str:
    """从 JSON-LD 结构化数据中提取字段"""
    import json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict) and key in data:
                return data[key]
            # 可能嵌套在 @graph 中
            if isinstance(data, dict) and "@graph" in data:
                for item in data["@graph"]:
                    if isinstance(item, dict) and key in item:
                        return item[key]
        except (json.JSONDecodeError, TypeError):
            continue
    return ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python3 fetcher.py <小宇宙单集URL>")
        print("示例：python3 fetcher.py https://www.xiaoyuzhoufm.com/episode/674a16478d5d7e073a18b4cc")
        sys.exit(1)

    result = fetch_metadata(sys.argv[1])
    import json
    print("\n完整元数据：")
    print(json.dumps(result, ensure_ascii=False, indent=2))
