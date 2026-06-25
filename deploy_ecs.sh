#!/bin/bash

set -e

ECS_IP="69.5.22.219"
ECS_USER="root"
ECS_PORT="22"
SSH_KEY=""
PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_NAME="api-to-mcp"
DEPLOY_DIR="/opt/api-to-mcp"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --ip) ECS_IP="$2"; shift ;;
        --user) ECS_USER="$2"; shift ;;
        --port) ECS_PORT="$2"; shift ;;
        --key) SSH_KEY="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

SSH_OPTS=""
if [[ -n "$SSH_KEY" ]]; then
    SSH_OPTS="-i $SSH_KEY"
fi

echo "=============================================="
echo "  🚀 部署 $PROJECT_NAME 到阿里云ECS"
echo "  目标服务器: $ECS_USER@$ECS_IP:$ECS_PORT"
echo "  SSH密钥: ${SSH_KEY:-使用默认配置}"
echo "=============================================="

echo ""
echo "📦 1. 打包项目..."
cd "$PROJECT_DIR"

EXCLUDE_FILES=(
    ".git"
    "__pycache__"
    "*.pyc"
    "*.pyo"
    ".env"
    "*.log"
    "*.pid"
    "certs/"
)

EXCLUDE_PATTERNS=""
for f in "${EXCLUDE_FILES[@]}"; do
    EXCLUDE_PATTERNS="$EXCLUDE_PATTERNS --exclude=$f"
done

TAR_FILE="${PROJECT_NAME}.tar.gz"
tar -czvf "$TAR_FILE" $EXCLUDE_PATTERNS src pyproject.toml uv.lock
echo "✅ 打包完成: $TAR_FILE"

echo ""
echo "📤 2. 上传到ECS..."
scp $SSH_OPTS -P "$ECS_PORT" "$TAR_FILE" "${ECS_USER}@${ECS_IP}:/tmp/"
echo "✅ 上传完成"

echo ""
echo "🔧 3. 在ECS上解压并部署..."
ssh $SSH_OPTS -p "$ECS_PORT" "${ECS_USER}@${ECS_IP}" << 'EOF'
set -e

PROJECT_NAME="api-to-mcp"
DEPLOY_DIR="/opt/api-to-mcp"
TAR_FILE="/tmp/${PROJECT_NAME}.tar.gz"

echo "📂 创建部署目录..."
mkdir -p "$DEPLOY_DIR"

echo "📥 解压项目..."
tar -xzvf "$TAR_FILE" -C "$DEPLOY_DIR" --strip-components=0

echo "✅ 解压完成"

echo ""
echo "📦 4. 安装依赖..."
cd "$DEPLOY_DIR"

if ! command -v uv &> /dev/null; then
    echo "🔧 安装 uv..."
    curl -sSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.bashrc"
fi

echo "🔧 安装项目依赖..."
uv sync --frozen
echo "✅ 依赖安装完成"

echo ""
echo "⚙️ 5. 配置Nginx反向代理..."
if ! command -v nginx &> /dev/null; then
    echo "🔧 安装 Nginx..."
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y nginx
    elif command -v yum &> /dev/null; then
        yum install -y nginx
    elif command -v dnf &> /dev/null; then
        dnf install -y nginx
    fi
fi

cat > /etc/nginx/sites-available/api-to-mcp << 'NGINXCONF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
NGINXCONF

ln -sf /etc/nginx/sites-available/api-to-mcp /etc/nginx/sites-enabled/

if nginx -t 2>/dev/null; then
    systemctl reload nginx || service nginx reload
    echo "✅ Nginx配置完成"
else
    echo "⚠️ Nginx配置测试失败，请手动检查"
fi

echo ""
echo "🚀 6. 启动服务..."

# 停止可能已运行的服务
pkill -f "uvicorn" 2>/dev/null || true
sleep 2

# 启动管理后台
cd "$DEPLOY_DIR"
nohup uv run api-to-mcp serve-ui --host 0.0.0.0 --port 8080 > /var/log/api-to-mcp.log 2>&1 &
echo "✅ 管理后台已启动"

# 启动TODO API服务（后台运行）
nohup uv run todo-api > /var/log/todo-api.log 2>&1 &
echo "✅ TODO API服务已启动"

# 启动计算器API服务（后台运行）
nohup uv run calc-api > /var/log/calc-api.log 2>&1 &
echo "✅ 计算器API服务已启动"

sleep 3

echo ""
echo "📊 7. 检查服务状态..."
if curl -s http://127.0.0.1:8080/api/services > /dev/null; then
    echo "✅ 管理后台服务正常"
else
    echo "❌ 管理后台服务启动失败，请检查日志: /var/log/api-to-mcp.log"
fi

if curl -s http://127.0.0.1:8000/health > /dev/null; then
    echo "✅ TODO API服务正常"
else
    echo "❌ TODO API服务启动失败，请检查日志: /var/log/todo-api.log"
fi

if curl -s http://127.0.0.1:8002/health > /dev/null; then
    echo "✅ 计算器API服务正常"
else
    echo "❌ 计算器API服务启动失败，请检查日志: /var/log/calc-api.log"
fi

echo ""
echo "🎉 部署完成！"
echo "管理后台地址: http://69.5.22.219"
echo "TODO API文档: http://69.5.22.219:8000/docs"
echo "计算器API文档: http://69.5.22.219:8002/docs"
EOF

echo ""
echo "🗑️ 清理本地打包文件..."
rm -f "$TAR_FILE"

echo ""
echo "🎉 部署流程完成！"
echo "访问地址: http://69.5.22.219"
