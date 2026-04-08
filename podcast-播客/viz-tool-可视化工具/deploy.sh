#!/bin/bash
# ==============================
# 播客可视化平台 — 一键部署脚本
# 适配 OpenCloudOS / CentOS / Ubuntu
# ==============================

set -e

APP_DIR="/opt/podcast-viz"

echo "========================================="
echo "  播客可视化平台 — 部署开始"
echo "========================================="

# 1. 安装系统依赖
echo ""
echo ">>> Step 1/5：安装系统依赖..."

if command -v dnf &> /dev/null; then
    dnf install -y python3-pip 2>&1 | tail -3
    dnf install -y nginx 2>&1 | tail -3 || true
elif command -v yum &> /dev/null; then
    yum install -y python3-pip 2>&1 | tail -3
    yum install -y nginx 2>&1 | tail -3 || true
elif command -v apt-get &> /dev/null; then
    apt-get update -qq
    apt-get install -y python3 python3-pip python3-venv nginx 2>&1 | tail -3
fi

# 兜底：如果 pip3 还是没有，用 ensurepip
if ! command -v pip3 &> /dev/null; then
    python3 -m ensurepip --upgrade 2>&1 || true
fi

python3 --version
pip3 --version || python3 -m pip --version
nginx -v 2>&1 || echo "    nginx 未安装，将直接暴露 gunicorn"
echo "    OK 系统依赖就绪"

# 2. 部署项目文件
echo ""
echo ">>> Step 2/5：部署项目文件..."
mkdir -p $APP_DIR/output
cp -r ./* $APP_DIR/
echo "    OK 文件已部署到 $APP_DIR"

# 3. 创建虚拟环境 + 安装依赖
echo ""
echo ">>> Step 3/5：安装 Python 依赖..."
cd $APP_DIR

python3 -m venv venv 2>/dev/null || python3 -m virtualenv venv 2>/dev/null || {
    echo "    venv 创建失败，直接用系统 pip"
    pip3 install -r requirements.txt
}

if [ -d "$APP_DIR/venv" ]; then
    source venv/bin/activate
    pip install --upgrade pip -q 2>/dev/null || true
    pip install -r requirements.txt
fi
echo "    OK 依赖安装完成"

# 4. 配置环境变量
echo ""
echo ">>> Step 4/5：配置环境变量..."
if [ ! -f $APP_DIR/.env ]; then
    cat > $APP_DIR/.env << 'ENVEOF'
# 请填入你的 API Key
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here
ENVEOF
    echo "    !! 请编辑 $APP_DIR/.env 填入 API Key"
else
    echo "    OK .env 已存在，跳过"
fi

# 5. 创建专用运行用户（安全加固）
echo ""
echo ">>> Step 5/6：创建运行用户..."
useradd -r -s /bin/false -d $APP_DIR podcast-viz 2>/dev/null || true
chown -R podcast-viz:podcast-viz $APP_DIR
chmod 600 $APP_DIR/.env 2>/dev/null || true
echo "    OK 用户 podcast-viz 就绪"

# 6. 配置系统服务
echo ""
echo ">>> Step 6/6：配置系统服务..."

# 判断 gunicorn 路径
if [ -f "$APP_DIR/venv/bin/gunicorn" ]; then
    GUNICORN="$APP_DIR/venv/bin/gunicorn"
else
    GUNICORN=$(which gunicorn 2>/dev/null || echo "/usr/local/bin/gunicorn")
fi

cat > /etc/systemd/system/podcast-viz.service << SVCEOF
[Unit]
Description=Podcast Visualization Platform
After=network.target

[Service]
User=podcast-viz
Group=podcast-viz
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$GUNICORN -w 1 --threads 4 -b 0.0.0.0:5000 --timeout 600 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

# Nginx 反代（如果 nginx 可用）
if command -v nginx &> /dev/null; then
    # 写入 conf.d
    mkdir -p /etc/nginx/conf.d
    cat > /etc/nginx/conf.d/podcast-viz.conf << 'NGXEOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;
    proxy_read_timeout 600;
    proxy_connect_timeout 60;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
NGXEOF
    # 移除默认站点
    rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

    nginx -t && systemctl enable nginx && systemctl restart nginx
    echo "    OK Nginx 反代已配置（:80 -> :5000）"
    ACCESS_PORT=80
else
    echo "    Nginx 不可用，Gunicorn 直接监听 :80"
    # 修改 service 文件让 gunicorn 直接监听 80
    sed -i 's/0.0.0.0:5000/0.0.0.0:80/' /etc/systemd/system/podcast-viz.service
    ACCESS_PORT=80
fi

# 启动应用
systemctl daemon-reload
systemctl enable podcast-viz
systemctl restart podcast-viz

# 等 1 秒检查是否启动成功
sleep 2
if systemctl is-active --quiet podcast-viz; then
    echo "    OK 服务启动成功"
else
    echo "    !! 服务启动失败，查看日志：journalctl -u podcast-viz -n 20"
    journalctl -u podcast-viz -n 10 --no-pager
fi

SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "134.175.228.73")

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
echo "  访问地址：http://$SERVER_IP:$ACCESS_PORT"
echo ""
echo "  重要：编辑 API Key："
echo "    nano $APP_DIR/.env"
echo "    systemctl restart podcast-viz"
echo ""
echo "  常用命令："
echo "    systemctl status podcast-viz"
echo "    journalctl -u podcast-viz -f"
echo "    systemctl restart podcast-viz"
echo ""
