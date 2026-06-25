#!/bin/bash
set -e

cd /opt/api-to-mcp
source .venv/bin/activate

echo "=== 启动服务 ==="
pkill -f uvicorn 2>/dev/null || true
sleep 1

mkdir -p /var/log

echo "启动TODO API (8000)..."
nohup python -m api_to_mcp.examples.todo_api > /var/log/todo-api.log 2>&1 &
echo "PID: $!"

echo "启动计算器API (8002)..."
nohup python -m api_to_mcp.examples.calc_api > /var/log/calc-api.log 2>&1 &
echo "PID: $!"

echo "启动管理后台 (8080)..."
nohup python -m uvicorn api_to_mcp.manager:app --host 0.0.0.0 --port 8080 > /var/log/api-to-mcp.log 2>&1 &
echo "PID: $!"

sleep 5

echo ""
echo "=== 服务状态检查 ==="
echo -n "TODO API: "
curl -s http://127.0.0.1:8000/health || echo "FAIL"
echo ""
echo -n "计算器API: "
curl -s http://127.0.0.1:8002/health || echo "FAIL"
echo ""
echo -n "管理后台: "
curl -s http://127.0.0.1:8080/api/services | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f"OK, {d[\"total\"]}个服务")' 2>/dev/null || echo "FAIL"
echo ""

echo "=== 部署完成 ==="
