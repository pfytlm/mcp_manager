#!/bin/bash

set -e

ECS_IP=""
ECS_USER="root"
ECS_PORT="22"
SSH_KEY=""
PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_NAME="mcp_manager"
DEPLOY_DIR="/opt/mcp_manager"
DOMAIN="mcp.pfytlm.top"
HTTPS_MODE=${HTTPS_MODE:-"true"}

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --ip) ECS_IP="$2"; shift ;;
        --user) ECS_USER="$2"; shift ;;
        --port) ECS_PORT="$2"; shift ;;
        --key) SSH_KEY="$2"; shift ;;
        --domain) DOMAIN="$2"; shift ;;
        --http) HTTPS_MODE="false"; shift ;;
        --https) HTTPS_MODE="true"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

if [[ -z "$ECS_IP" ]]; then
    echo "❌ 请指定ECS IP地址: --ip <IP地址>"
    exit 1
fi

SSH_OPTS=""
if [[ -n "$SSH_KEY" ]]; then
    SSH_OPTS="-i $SSH_KEY"
fi

SSH_OPTS="$SSH_OPTS -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

echo "=============================================="
echo "  🚀 部署 $PROJECT_NAME 到 ECS"
echo "  目标服务器: $ECS_USER@$ECS_IP:$ECS_PORT"
echo "  域名: $DOMAIN"
echo "  HTTPS: $HTTPS_MODE"
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
    ".venv/"
    "venv/"
    "*.tar.gz"
)

EXCLUDE_PATTERNS=""
for f in "${EXCLUDE_FILES[@]}"; do
    EXCLUDE_PATTERNS="$EXCLUDE_PATTERNS --exclude=$f"
done

TAR_FILE="${PROJECT_NAME}.tar.gz"
tar -czvf "$TAR_FILE" $EXCLUDE_PATTERNS src pyproject.toml uv.lock start.sh .env.example
echo "✅ 打包完成: $TAR_FILE"

echo ""
echo "📤 2. 上传到ECS..."
scp $SSH_OPTS -P "$ECS_PORT" "$TAR_FILE" "${ECS_USER}@${ECS_IP}:/tmp/"
echo "✅ 上传完成"

echo ""
echo "🔧 3. 在ECS上解压并部署..."
ssh $SSH_OPTS -p "$ECS_PORT" "${ECS_USER}@${ECS_IP}" << EOF
set -e

PROJECT_NAME="$PROJECT_NAME"
DEPLOY_DIR="$DEPLOY_DIR"
DOMAIN="$DOMAIN"
HTTPS_MODE="$HTTPS_MODE"
TAR_FILE="/tmp/\${PROJECT_NAME}.tar.gz"

echo "📂 创建部署目录..."
mkdir -p "\$DEPLOY_DIR"

echo "📥 解压项目..."
tar -xzvf "\$TAR_FILE" -C "\$DEPLOY_DIR"

echo "✅ 解压完成"

echo ""
echo "📦 4. 安装依赖..."
cd "\$DEPLOY_DIR"

if ! command -v uv &> /dev/null; then
    echo "🔧 安装 uv..."
    curl -sSf https://astral.sh/uv/install.sh | sh
    export PATH="\$HOME/.local/bin:\$PATH"
fi

export PATH="\$HOME/.local/bin:\$PATH"

echo "🔧 安装项目依赖..."
uv sync --frozen
echo "✅ 依赖安装完成"

echo ""
echo "⚙️ 5. 配置环境变量..."
if [[ ! -f "\$DEPLOY_DIR/.env" ]]; then
    cp "\$DEPLOY_DIR/.env.example" "\$DEPLOY_DIR/.env"
    sed -i "s|PLATFORM_HOST=.*|PLATFORM_HOST=\$DOMAIN|g" "\$DEPLOY_DIR/.env"
    if [[ "\$HTTPS_MODE" == "true" ]]; then
        sed -i "s|PLATFORM_SCHEME=.*|PLATFORM_SCHEME=https|g" "\$DEPLOY_DIR/.env"
    else
        sed -i "s|PLATFORM_SCHEME=.*|PLATFORM_SCHEME=http|g" "\$DEPLOY_DIR/.env"
    fi
    echo "✅ 环境变量配置完成"
else
    echo "ℹ️  环境变量已存在，跳过配置"
fi

echo ""
echo "🚀 6. 启动服务..."

pkill -f "uvicorn.*api_to_mcp" 2>/dev/null || true
sleep 2

cd "\$DEPLOY_DIR"

export PATH="\$HOME/.local/bin:\$PATH"

if [[ "\$HTTPS_MODE" == "true" ]]; then
    echo "启动HTTPS模式 (端口443)..."
    nohup uv run python -m uvicorn api_to_mcp.gateway:_unified_gateway_factory --factory --host 0.0.0.0 --port 443 --ssl-certfile=certs/\$DOMAIN.crt --ssl-keyfile=certs/\$DOMAIN.key > /var/log/mcp-gateway.log 2>&1 &
else
    echo "启动HTTP模式 (端口80)..."
    nohup uv run python -m uvicorn api_to_mcp.gateway:_unified_gateway_factory --factory --host 0.0.0.0 --port 80 > /var/log/mcp-gateway.log 2>&1 &
fi

echo "  PID: \$!"

sleep 5

echo ""
echo "📊 7. 检查服务状态..."

if [[ "\$HTTPS_MODE" == "true" ]]; then
    HEALTH_URL="https://127.0.0.1:443/health"
    SERVICES_URL="https://127.0.0.1:443/api/services"
    CURL_OPTS="-k -s"
else
    HEALTH_URL="http://127.0.0.1:80/health"
    SERVICES_URL="http://127.0.0.1:80/api/services"
    CURL_OPTS="-s"
fi

echo -n "健康检查:       "
curl \$CURL_OPTS "\$HEALTH_URL" | grep -q healthy && echo "✅" || echo "❌"

echo -n "管理后台API:    "
curl \$CURL_OPTS "\$SERVICES_URL" | grep -q total && echo "✅" || echo "❌"

echo ""
echo "🎉 部署完成！"
echo "管理后台:   \$([[ \$HTTPS_MODE == "true" ]] && echo "https" || echo "http")://\$DOMAIN/"
echo "MCP网关:    \$([[ \$HTTPS_MODE == "true" ]] && echo "https" || echo "http")://\$DOMAIN/mcp"
echo "TODO MCP:   \$([[ \$HTTPS_MODE == "true" ]] && echo "https" || echo "http")://\$DOMAIN/mcp/todo"
echo "计算器MCP:  \$([[ \$HTTPS_MODE == "true" ]] && echo "https" || echo "http")://\$DOMAIN/mcp/calc"
echo "日志:       tail -f /var/log/mcp-gateway.log"
EOF

echo ""
echo "🗑️ 清理本地打包文件..."
rm -f "$TAR_FILE"

echo ""
echo "🎉 部署流程完成！"
if [[ "$HTTPS_MODE" == "true" ]]; then
    echo "访问地址: https://$DOMAIN/"
else
    echo "访问地址: http://$DOMAIN/"
fi
