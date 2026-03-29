#!/bin/bash
# 列出 inbox 中待消化的文章
# 用法: ./scripts/list.sh

INBOX_DIR="$(dirname "$0")/../inbox-收藏箱"
DIGESTED_DIR="$(dirname "$0")/../digested-已消化"

echo "📥 待消化文章："
echo "─────────────────────────────"

count=0
for f in "$INBOX_DIR"/*.txt "$INBOX_DIR"/*.md; do
    [ -f "$f" ] || continue
    basename=$(basename "$f")
    # 跳过 README
    [ "$basename" = "README.md" ] && continue

    # 检查是否已消化
    if [ -f "$DIGESTED_DIR/$basename" ]; then
        continue
    fi

    count=$((count + 1))
    # 显示文件名和前两行
    echo ""
    echo "  [$count] $basename"
    head -2 "$f" | sed 's/^/       /'
done

if [ $count -eq 0 ]; then
    echo ""
    echo "  （空）没有待消化的文章"
    echo ""
    echo "  添加方式："
    echo "  1. 直接把 .txt/.md 文件拖进 inbox/ 文件夹"
    echo "  2. 运行 ./scripts/add.sh \"URL\""
    echo "  3. 新建文件粘贴内容"
fi

echo ""
echo "─────────────────────────────"
echo "已消化: $(ls "$DIGESTED_DIR"/*.txt "$DIGESTED_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ') 篇"
