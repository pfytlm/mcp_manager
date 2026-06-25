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
else
    SSL_OPTS="--ssl-certfile=$SSL_CERT --ssl-keyfile=$SSL_KEY"
    PROTOCOL="https"
fi

echo "=== 停止所有服务 ==="
pkill -f "uvicorn.*api_to_mcp" 2>/dev/null || true
sleep 2

mkdir -p /var/log

echo ""
echo "=== 启动后端API服务 ==="

echo "启动TODO API (8000, ${PROTOCOL})..."
nohup python -m uvicorn api_to_mcp.examples.todo_api:app --host 0.0.0.0 --port 8000 $SSL_OPTS > /var/log/todo-api.log 2>&1 &
echo "  PID: $!"

echo "启动计算器API (8002, ${PROTOCOL})..."
nohup python -m uvicorn api_to_mcp.examples.calc_api:app --host 0.0.0.0 --port 8002 $SSL_OPTS > /var/log/calc-api.log 2>&1 &
echo "  PID: $!"

echo ""
echo "=== 启动统一MCP网关服务（对外暴露MCP协议）==="

echo "启动MCP Gateway (8001, ${PROTOCOL})..."
nohup python -m uvicorn api_to_mcp.sse_server:_unified_mcp_gateway_factory --factory --host 0.0.0.0 --port 8001 $SSL_OPTS > /var/log/mcp-gateway.log 2>&1 &
echo "  PID: $!"

echo ""
echo "=== 启动管理后台 ==="

echo "启动管理后台UI (8080, ${PROTOCOL})..."
nohup python -m uvicorn api_to_mcp.manager:app --host 0.0.0.0 --port 8080 $SSL_OPTS > /var/log/api-to-mcp.log 2>&1 &
echo "  PID: $!"

sleep 5

echo ""
echo "=== 服务状态检查 ==="

if [ "$HTTP_MODE" = "true" ]; then
    echo -n "TODO API (8000):      "
    curl -s http://127.0.0.1:8000/health | grep -q healthy && echo "✅" || echo "❌"

    echo -n "计算器API (8002):     "
    curl -s http://127.0.0.1:8002/health | grep -q healthy && echo "✅" || echo "❌"

    echo -n "MCP Gateway (8001):   "
    curl -s http://127.0.0.1:8001/health | grep -q healthy && echo "✅" || echo "❌"

    echo -n "管理后台 (8080):      "
    curl -s http://127.0.0.1:8080/api/services | grep -q total && echo "✅" || echo "❌"
else
    echo -n "TODO API (8000):      "
    curl -s -k https://127.0.0.1:8000/health | grep -q healthy && echo "✅" || echo "❌"

    echo -n "计算器API (8002):     "
    curl -s -k https://127.0.0.1:8002/health | grep -q healthy && echo "✅" || echo "❌"

    echo -n "MCP Gateway (8001):   "
    curl -s -k https://127.0.0.1:8001/health | grep -q healthy && echo "✅" || echo "❌"

    echo -n "管理后台 (8080):      "
    curl -s -k https://127.0.0.1:8080/api/services | grep -q total && echo "✅" || echo "❌"
fi

echo ""
echo "=== 部署完成 ==="
echo "管理后台:   ${PROTOCOL}://localhost:8080"
echo "TODO MCP:   ${PROTOCOL}://localhost:8001/todo/mcp"
echo "计算器MCP:  ${PROTOCOL}://localhost:8001/calc/mcp"
