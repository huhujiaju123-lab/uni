#!/usr/bin/env python3
"""
播客可视化 Web 平台
启动：python3 app.py
访问：http://localhost:5000
"""

import sys
from pathlib import Path
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from core import OUTPUT_DIR
from web import web
from api import api

app = Flask(__name__)

# 注册路由
app.register_blueprint(web)   # Web 路由：/、/process、/progress、/stream、/view
app.register_blueprint(api)   # API 路由：/api/history、/api/process、/api/status、/api/episode


# 安全响应头
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("🎙️  播客可视化平台启动中...")
    print("   访问 http://localhost:5000")
    app.run(debug=True, port=5000, threaded=True)
