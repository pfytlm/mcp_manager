#!/usr/bin/env python3
"""集成测试：验证API服务和MCP转化是否正常工作"""

import asyncio
import json
import sys
import time
from multiprocessing import Process

import httpx
import uvicorn

from api_to_mcp.examples.todo_api import app
from api_to_mcp.examples.todo_mcp import create_todo_mcp_server


def extract_text(result_item):
    return getattr(result_item, 'text', None) or getattr(result_item, 'content', str(result_item))


def run_api_server():
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="error")


async def test_api():
    """测试REST API服务"""
    print("=" * 60)
    print("测试1: REST API 服务")
    print("=" * 60)

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8765") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        print("✅ 健康检查通过")

        resp = await client.get("/todos")
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 3
        print(f"✅ 获取待办列表成功，共 {data['total']} 条")

        new_todo = {"title": "测试待办事项", "priority": "high", "tags": ["测试"]}
        resp = await client.post("/todos", json=new_todo)
        assert resp.status_code == 201
        todo = resp.json()
        todo_id = todo["id"]
        print(f"✅ 创建待办成功: {todo_id}")

        resp = await client.get(f"/todos/{todo_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "测试待办事项"
        print("✅ 获取单个待办成功")

        resp = await client.post(f"/todos/{todo_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        print("✅ 标记完成成功")

        resp = await client.delete(f"/todos/{todo_id}")
        assert resp.status_code == 204
        print("✅ 删除待办成功")

        resp = await client.get("/todos/stats/summary")
        assert resp.status_code == 200
        stats = resp.json()
        print(f"✅ 获取统计成功: {json.dumps(stats, ensure_ascii=False)}")

    print()


async def test_mcp_tools():
    """测试MCP工具直接调用"""
    print("=" * 60)
    print("测试2: MCP 工具转化")
    print("=" * 60)

    mcp, builder = create_todo_mcp_server(base_url="http://127.0.0.1:8765")

    try:
        tools = await mcp.list_tools()
        print(f"✅ MCP服务器注册了 {len(tools)} 个工具:")
        for tool in tools:
            desc = str(tool.description)[:50] if tool.description else ""
            print(f"   - {tool.name}: {desc}...")

        result = await mcp.call_tool("health_check", {})
        health = json.loads(extract_text(result[0]))
        assert health["status"] == "healthy"
        print("✅ health_check 工具调用成功")

        result = await mcp.call_tool("get_todo_stats", {})
        stats = json.loads(extract_text(result[0]))
        assert "total" in stats
        print(f"✅ get_todo_stats 工具调用成功: 总计 {stats['total']} 条")

        result = await mcp.call_tool("list_todos", {"status": "pending", "page_size": 5})
        todos = json.loads(extract_text(result[0]))
        assert "items" in todos
        print(f"✅ list_todos 工具调用成功: 获取 {len(todos['items'])} 条待办")

        result = await mcp.call_tool("create_todo", {
            "title": "MCP创建的测试待办",
            "description": "通过MCP工具创建",
            "priority": "high",
            "tags": ["MCP", "测试"]
        })
        new_todo = json.loads(extract_text(result[0]))
        assert "id" in new_todo
        todo_id = new_todo["id"]
        print(f"✅ create_todo 工具调用成功: ID={todo_id}")

        result = await mcp.call_tool("complete_todo", {"todo_id": todo_id})
        completed = json.loads(extract_text(result[0]))
        assert completed["status"] == "completed"
        print("✅ complete_todo 工具调用成功")

        result = await mcp.call_tool("delete_todo", {"todo_id": todo_id})
        print("✅ delete_todo 工具调用成功")

        resources = await mcp.list_resources()
        resource_uris = [str(r.uri) for r in resources]
        print(f"  可用资源: {resource_uris}")
        has_endpoints = any("endpoints" in uri for uri in resource_uris)
        assert has_endpoints, f"Expected api endpoints resource, got {resource_uris}"
        print(f"✅ MCP资源可用: {len(resource_uris)} 个资源")

        prompts = await mcp.list_prompts()
        prompt_names = [str(p.name) for p in prompts]
        print(f"  可用提示词: {prompt_names}")
        has_daily = any("daily" in p for p in prompt_names)
        assert has_daily, f"Expected daily review prompt, got {prompt_names}"
        print(f"✅ MCP提示词可用: {len(prompt_names)} 个")

    finally:
        await builder.close()

    print()


async def main():
    print("\n🚀 启动API服务进行集成测试...\n")

    api_process = Process(target=run_api_server, daemon=True)
    api_process.start()
    time.sleep(2)

    try:
        await test_api()
        await test_mcp_tools()

        print("=" * 60)
        print("🎉 所有测试通过!")
        print("=" * 60)
        print()
        print("📋 API → MCP 转化验证成功!")
        print()
        print("📁 项目结构:")
        print("  src/api_to_mcp/core.py           - 核心转化框架")
        print("  src/api_to_mcp/examples/todo_api.py    - 示例REST API")
        print("  src/api_to_mcp/examples/todo_mcp.py    - 示例MCP服务")
        print("  src/api_to_mcp/examples/todo_models.py - 数据模型")
        print()
        print("🚀 快速启动:")
        print("  终端1: uv run api-to-mcp serve-api")
        print("  终端2: uv run api-to-mcp serve-mcp")
        print("  测试:  uv run api-to-mcp inspect")
        print()
        return 0
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        api_process.terminate()
        api_process.join()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
