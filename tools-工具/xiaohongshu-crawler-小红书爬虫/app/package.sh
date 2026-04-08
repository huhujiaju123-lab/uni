#!/bin/bash

# 小红书笔记抓取工具 - 打包脚本
echo "📦 开始打包 Chrome 扩展..."

# 设置变量
OUTPUT_FILE="xiaohongshu-crawler-v3.1.zip"
TEMP_DIR="temp_package"

# 创建临时目录
echo "📁 创建临时打包目录..."
mkdir -p $TEMP_DIR

# 复制需要的文件
echo "📋 复制文件..."
cp manifest.json $TEMP_DIR/
cp background.js $TEMP_DIR/
cp -r content $TEMP_DIR/
cp -r popup $TEMP_DIR/
cp -r icons $TEMP_DIR/
cp PRIVACY_POLICY.md $TEMP_DIR/ 2>/dev/null || echo "⚠️  PRIVACY_POLICY.md 不存在，跳过"

# 删除临时文件
echo "🧹 清理临时文件..."
find $TEMP_DIR -name ".DS_Store" -delete

# 检查图标文件
echo "🔍 检查图标文件..."
required_icons=("icon16.png" "icon32.png" "icon48.png" "icon128.png")
all_icons_exist=true

for icon in "${required_icons[@]}"; do
    if [ ! -f "$TEMP_DIR/icons/$icon" ]; then
        echo "❌ 缺少图标: icons/$icon"
        all_icons_exist=false
    fi
done

if [ "$all_icons_exist" = false ]; then
    echo ""
    echo "⚠️  警告：缺少必需的图标文件！"
    echo "📌 请先打开 icons/icon-generator.html 生成图标"
    echo ""
    read -p "是否继续打包？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        rm -rf $TEMP_DIR
        echo "❌ 打包已取消"
        exit 1
    fi
fi

# 创建 zip 文件
echo "📦 创建 ZIP 文件..."
cd $TEMP_DIR
zip -r ../$OUTPUT_FILE . -x "*.DS_Store"
cd ..

# 清理临时目录
echo "🧹 清理临时目录..."
rm -rf $TEMP_DIR

# 完成
if [ -f $OUTPUT_FILE ]; then
    FILE_SIZE=$(du -h $OUTPUT_FILE | cut -f1)
    echo ""
    echo "✅ 打包完成！"
    echo "📦 文件名: $OUTPUT_FILE"
    echo "📊 文件大小: $FILE_SIZE"
    echo ""
    echo "📋 下一步："
    echo "1. 打开 icons/icon-generator.html 生成图标（如果还没有）"
    echo "2. 访问 https://chrome.google.com/webstore/devconsole"
    echo "3. 上传 $OUTPUT_FILE"
    echo "4. 填写商店列表信息（参考 STORE_LISTING.md）"
    echo "5. 提交审核"
    echo ""
else
    echo "❌ 打包失败！"
    exit 1
fi
