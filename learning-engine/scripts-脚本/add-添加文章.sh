#!/bin/bash
# 快速添加文章到 inbox
# 用法: ./scripts/add.sh "https://example.com/article"
#        ./scripts/add.sh   (无参数则打开inbox目录)

INBOX_DIR="$(dirname "$0")/../inbox-收藏箱"
DATE=$(date +%Y-%m-%d)

if [ -z "$1" ]; then
    echo "📥 inbox 目录: $INBOX_DIR"
    echo "直接把 .txt/.md 文件拖进去即可"
    echo ""
    echo "或者用: $0 \"URL\" 从网页抓取"
    open "$INBOX_DIR"
    exit 0
fi

URL="$1"
# 从URL提取标题作为文件名
TITLE=$(curl -sL "$URL" | grep -oP '(?<=<title>).*?(?=</title>)' | head -1 | sed 's/[^a-zA-Z0-9\u4e00-\u9fff]/_/g' | cut -c1-50)
if [ -z "$TITLE" ]; then
    TITLE="article_$(date +%H%M%S)"
fi

FILENAME="${DATE}-${TITLE}.txt"
FILEPATH="${INBOX_DIR}/${FILENAME}"

echo "正在抓取: $URL"

# 用 python 提取正文（比 curl+sed 靠谱）
python3 -c "
import urllib.request, re, html
try:
    req = urllib.request.Request('$URL', headers={'User-Agent': 'Mozilla/5.0'})
    raw = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    # 去HTML标签
    text = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = html.unescape(text)
    # 去多余空行
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    text = '\n'.join(lines)
    with open('$FILEPATH', 'w') as f:
        f.write('来源: $URL\n日期: $DATE\n\n' + text)
    print(f'✅ 已保存到 $FILENAME')
except Exception as e:
    print(f'❌ 抓取失败: {e}')
    print('你可以手动复制内容到 $FILEPATH')
"
