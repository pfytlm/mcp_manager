#!/bin/bash
set -e

HTTP_MODE=${HTTP_MODE:-"false"}
SSL_CERT=${SSL_CERT:-"certs/mcp.pfytlm.top.crt"}
SSL_KEY=${SSL_KEY:-"certs/mcp.pfytlm.top.key"}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

if [ "$HTTP_MODE" = "true" ]; then
    SSL_OPTS=""
    PROTOCOL="http"
    PORT=80
else
    SSL_OPTS="--ssl-certfile=$SSL_CERT --ssl-keyfile=$SSL_KEY"
    PROTOCOL="https"
    PORT=443
fi

echo "=== 停止所有服务 ==="
pkill -f "uvicorn.*api_to_mcp" 2>/dev/null || true
sleep 2

mkdir -p /var/log

echo ""
echo "=== 启动统一网关（包含所有服务）==="

echo "启动统一网关 (${PORT}, ${PROTOCOL})..."
nohup python -m uvicorn api_to_mcp.gateway:_unified_gateway_factory --factory --host 0.0.0.0 --port $PORT $SSL_OPTS > /var/log/mcp-gateway.log 2>&1 &
echo "  PID: $!"

sleep 5

echo ""
echo "=== 服务状态检查 ==="

if [ "$HTTP_MODE" = "true" ]; then
    echo -n "网关首页 (${PORT}):       "
    curl -s http://127.0.0.1:${PORT}/health | grep -q healthy && echo "✅" || echo "❌"

    echo -n "管理后台 /admin:        "
    curl -s http://127.0.0.1:${PORT}/admin/api/services | grep -q total && echo "✅" || echo "❌"

    echo -n "MCP网关 /mcp:          "
    curl -s http://127.0.0.1:${PORT}/mcp | grep -q todo && echo "✅" || echo "❌"

    echo -n "TODO MCP /mcp/todo:    "
    curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${PORT}/mcp/todo | grep -q 307 && echo "✅" || echo "❌"

    echo -n "计算器MCP /mcp/calc:   "
    curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${PORT}/mcp/calc | grep -q 307 && echo "✅" || echo "❌"

    echo -n "TODO API /api/todo:    "
    curl -s http://127.0.0.1:${PORT}/api/todo/health | grep -q healthy && echo "✅" || echo "❌"

    echo -n "计算器API /api/calc:   "
    curl -s http://127.0.0.1:${PORT}/api/calc/health | grep -q healthy && echo "✅" || echo "❌"
else
    echo -n "网关首页 (${PORT}):       "
    curl -s -k https://127.0.0.1:${PORT}/health | grep -q healthy && echo "✅" || echo "❌"

    echo -n "管理后台 /admin:        "
    curl -s -k https://127.0.0.1:${PORT}/admin/api/services | grep -q total && echo "✅" || echo "❌"

    echo -n "MCP网关 /mcp:          "
    curl -s -k https://127.0.0.1:${PORT}/mcp | grep -q todo && echo "✅" || echo "❌"

    echo -n "TODO MCP /mcp/todo:    "
    curl -s -k -o /dev/null -w "%{http_code}" https://127.0.0.1:${PORT}/mcp/todo | grep -q 307 && echo "✅" || echo "❌"

    echo -n "计算器MCP /mcp/calc:   "
    curl -s -k -o /dev/null -w "%{http_code}" https://127.0.0.1:${PORT}/mcp/calc | grep -q 307 && echo "✅" || echo "❌"

    echo -n "TODO API /api/todo:    "
    curl -s -k https://127.0.0.1:${PORT}/api/todo/health | grep -q healthy && echo "✅" || echo "❌"

    echo -n "计算器API /api/calc:   "
    curl -s -k https://127.0.0.1:${PORT}/api/calc/health | grep -q healthy && echo "✅" || echo "❌"
fi

echo ""
echo "=== 部署完成 ==="
echo "管理后台:   ${PROTOCOL}://mcp.pfytlm.top/admin"
echo "MCP网关:    ${PROTOCOL}://mcp.pfytlm.top/mcp"
echo "TODO MCP:   ${PROTOCOL}://mcp.pfytlm.top/mcp/todo"
echo "计算器MCP:  ${PROTOCOL}://mcp.pfytlm.top/mcp/calc"
echo "TODO API:   ${PROTOCOL}://mcp.pfytlm.top/api/todo"
echo "计算器API:  ${PROTOCOL}://mcp.pfytlm.top/api/calc"
