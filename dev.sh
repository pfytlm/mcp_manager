#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-8080}"
HOST="${HOST:-127.0.0.1}"
MCP_AUTH_TOKENS="${MCP_AUTH_TOKENS:-dev_token_123,dev_token_456}"

echo "=========================================="
echo "  🚀 MCP Manager - 本地开发模式"
echo "  地址: http://$HOST:$PORT"
echo "  Token: $MCP_AUTH_TOKENS"
echo "=========================================="
echo ""

pkill -f "uvicorn.*api_to_mcp" 2>/dev/null || true
sleep 1

export MCP_AUTH_TOKENS
export PLATFORM_HOST="$HOST"
export PLATFORM_PORT="$PORT"
export PLATFORM_SCHEME="http"
export PYTHONPATH="src"

if [ -f .venv/bin/python ]; then
    PYTHON=".venv/bin/python"
elif [ -f venv/bin/python ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

echo "📍 管理后台:    http://$HOST:$PORT/"
echo "📍 MCP网关:     http://$HOST:$PORT/mcp"
echo "📍 TODO MCP:    http://$HOST:$PORT/mcp/todo"
echo "📍 计算器MCP:   http://$HOST:$PORT/mcp/calc"
echo "📍 健康检查:    http://$HOST:$PORT/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

$PYTHON -m uvicorn api_to_mcp.gateway:_unified_gateway_factory \
    --factory \
    --host "$HOST" \
    --port "$PORT" \
    --reload
