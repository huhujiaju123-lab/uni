#!/bin/bash
# 启动套件库存计算系统

echo "正在启动套件库存计算系统..."
echo "启动后请在浏览器中访问: http://localhost:8501"
echo ""

cd "$(dirname "$0")"
python3 -m streamlit run app.py
