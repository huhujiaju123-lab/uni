#!/bin/bash
# 智能补货系统启动脚本
# 双击此文件即可启动

cd "$(dirname "$0")"
echo "🚀 正在启动智能补货系统..."
echo "   浏览器将自动打开，请稍候..."
echo ""
python3 -m streamlit run app.py --server.headless true
