from __future__ import annotations

import asyncio
import os
from typing import Dict, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from api_to_mcp.core import (
    APIEndpoint,
    APIParameter,
    HTTPMethod,
    ParameterLocation,
    build_service_metadata,
    create_mcp_server_from_api,
)
from .todo_models import TodoCreate, TodoUpdate

load_dotenv()

API_BASE_URL = os.getenv("TODO_API_BASE_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("TODO_API_KEY", None)


def get_todo_endpoints():
    return [
        APIEndpoint(
            name="list_todos",
            path="/todos",
            method=HTTPMethod.GET,
            description="获取待办事项列表，支持按状态、优先级、标签筛选，支持分页",
            parameters=[
                APIParameter(
                    name="status",
                    location=ParameterLocation.QUERY,
                    type=str,
                    required=False,
                    description="按状态筛选: pending(待办), in_progress(进行中), completed(已完成)",
                ),
                APIParameter(
                    name="priority",
                    location=ParameterLocation.QUERY,
                    type=str,
                    required=False,
                    description="按优先级筛选: low(低), medium(中), high(高)",
                ),
                APIParameter(
                    name="tag",
                    location=ParameterLocation.QUERY,
                    type=str,
                    required=False,
                    description="按标签筛选，传入单个标签名称",
                ),
                APIParameter(
                    name="page",
                    location=ParameterLocation.QUERY,
                    type=int,
                    required=False,
                    default=1,
                    description="页码，从1开始",
                ),
                APIParameter(
                    name="page_size",
                    location=ParameterLocation.QUERY,
                    type=int,
                    required=False,
                    default=20,
                    description="每页数量，最大100",
                ),
            ],
            tags=["待办事项"],
        ),
        APIEndpoint(
            name="get_todo",
            path="/todos/{todo_id}",
            method=HTTPMethod.GET,
            description="根据ID获取单个待办事项的详细信息",
            parameters=[
                APIParameter(
                    name="todo_id",
                    location=ParameterLocation.PATH,
                    type=str,
                    required=True,
                    description="待办事项的UUID",
                ),
            ],
            tags=["待办事项"],
        ),
        APIEndpoint(
            name="create_todo",
            path="/todos",
            method=HTTPMethod.POST,
            description="创建新的待办事项",
            parameters=[],
            request_model=TodoCreate,
            tags=["待办事项"],
        ),
        APIEndpoint(
            name="update_todo",
            path="/todos/{todo_id}",
            method=HTTPMethod.PUT,
            description="更新已存在的待办事项，可以部分更新",
            parameters=[
                APIParameter(
                    name="todo_id",
                    location=ParameterLocation.PATH,
                    type=str,
                    required=True,
                    description="待办事项的UUID",
                ),
            ],
            request_model=TodoUpdate,
            tags=["待办事项"],
        ),
        APIEndpoint(
            name="delete_todo",
            path="/todos/{todo_id}",
            method=HTTPMethod.DELETE,
            description="删除指定的待办事项",
            parameters=[
                APIParameter(
                    name="todo_id",
                    location=ParameterLocation.PATH,
                    type=str,
                    required=True,
                    description="待办事项的UUID",
                ),
            ],
            tags=["待办事项"],
        ),
        APIEndpoint(
            name="complete_todo",
            path="/todos/{todo_id}/complete",
            method=HTTPMethod.POST,
            description="将待办事项标记为已完成",
            parameters=[
                APIParameter(
                    name="todo_id",
                    location=ParameterLocation.PATH,
                    type=str,
                    required=True,
                    description="待办事项的UUID",
                ),
            ],
            tags=["待办事项"],
        ),
        APIEndpoint(
            name="get_todo_stats",
            path="/todos/stats/summary",
            method=HTTPMethod.GET,
            description="获取待办事项统计信息，包括总数、按状态分组、按优先级分组",
            parameters=[],
            tags=["待办事项", "统计"],
        ),
        APIEndpoint(
            name="health_check",
            path="/health",
            method=HTTPMethod.GET,
            description="检查API服务的健康状态",
            parameters=[],
            tags=["系统"],
        ),
    ]


def get_todo_service_metadata(base_url: Optional[str] = None, api_key: Optional[str] = None) -> Dict:
    url = base_url or API_BASE_URL
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    endpoints = get_todo_endpoints()

    instructions = """
你是一个待办事项管理助手，可以帮助用户管理他们的待办事项列表。

## 可用功能
你可以通过以下工具来管理待办事项：

1. **list_todos** - 查看待办事项列表，可以按状态、优先级、标签筛选
2. **get_todo** - 查看单个待办事项的详细信息
3. **create_todo** - 创建新的待办事项
4. **update_todo** - 更新待办事项
5. **delete_todo** - 删除待办事项
6. **complete_todo** - 将待办事项标记为已完成
7. **get_todo_stats** - 查看统计信息
8. **health_check** - 检查服务状态
"""

    return build_service_metadata(
        server_name="todo-mcp-server",
        base_url=url,
        endpoints=endpoints,
        headers=headers,
        instructions=instructions,
        description="待办事项管理MCP服务 - 提供完整的CRUD操作、筛选、统计功能及组合工具",
        extra_resources=[
            {"uri": "todo://guide", "name": "Todo Guide", "description": "待办事项使用指南和工作流说明"}
        ],
        extra_prompts=[
            {"name": "daily_review", "description": "每日待办事项回顾模板"}
        ],
        extra_tools=[
            {
                "name": "get_daily_overview",
                "description": "获取每日概览报告：统计摘要 + 待办列表 + 最近完成（聚合3个API）",
                "method": "COMPOSITE",
                "path": "聚合: GET /todos/stats/summary + GET /todos (pending) + GET /todos (completed)",
                "parameters": [
                    {"name": "include_completed", "type": "boolean", "required": False, "description": "是否包含已完成任务", "location": "composite"},
                ],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "include_completed": {"type": "boolean", "description": "是否包含已完成任务"},
                    },
                    "required": [],
                },
            },
            {
                "name": "complete_todo_and_get_next",
                "description": "完成指定任务并自动获取下一个高优先级待办（编排2个API）",
                "method": "COMPOSITE",
                "path": "编排: POST /todos/{id}/complete → GET /todos (priority=high, status=pending, limit=1)",
                "parameters": [
                    {"name": "todo_id", "type": "string", "required": True, "description": "要完成的待办事项ID", "location": "composite"},
                ],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "todo_id": {"type": "string", "description": "要完成的待办事项ID"},
                    },
                    "required": ["todo_id"],
                },
            },
            {
                "name": "bulk_create_todos",
                "description": "批量创建多个待办事项（循环调用创建API）",
                "method": "COMPOSITE",
                "path": "批量: 循环调用 POST /todos 多次",
                "parameters": [
                    {"name": "titles", "type": "array", "required": True, "description": "待办标题列表（可传多个）", "location": "composite"},
                    {"name": "priority", "type": "string", "required": False, "description": "统一优先级，默认medium", "location": "composite"},
                ],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "titles": {"type": "array", "description": "待办标题列表（可传多个）", "items": {"type": "string"}},
                        "priority": {"type": "string", "description": "统一优先级，默认medium"},
                    },
                    "required": ["titles"],
                },
            },
        ],
        tags=["示例", "任务管理", "CRUD", "组合工具"],
    )


def create_todo_mcp_server(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    verify_ssl: bool = True,
) -> tuple[FastMCP, object]:
    url = base_url or API_BASE_URL
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    endpoints = get_todo_endpoints()

    instructions = """
你是一个待办事项管理助手，可以帮助用户管理他们的待办事项列表。

## 可用功能
你可以通过以下工具来管理待办事项：

1. **list_todos** - 查看待办事项列表，可以按状态、优先级、标签筛选
2. **get_todo** - 查看单个待办事项的详细信息
3. **create_todo** - 创建新的待办事项
4. **update_todo** - 更新待办事项
5. **delete_todo** - 删除待办事项
6. **complete_todo** - 将待办事项标记为已完成
7. **get_todo_stats** - 查看统计信息
8. **health_check** - 检查服务状态

## 使用建议
- 首先可以使用 get_todo_stats 了解整体情况
- 使用 list_todos 查看待办事项，可以根据状态筛选
- 创建待办事项时，必填字段是 title（标题）
- 完成任务后使用 complete_todo 标记完成
- 所有ID都是UUID格式，例如：550e8400-e29b-41d4-a716-446655440000
"""

    mcp_server, builder = create_mcp_server_from_api(
        server_name="todo-mcp-server",
        base_url=url,
        endpoints=endpoints,
        headers=headers,
        instructions=instructions,
        verify_ssl=verify_ssl,
    )

    @mcp_server.resource("todo://guide")
    def todo_guide() -> str:
        return """
# 待办事项MCP服务使用指南

## 数据模型
- **status（状态）**: pending（待办）、in_progress（进行中）、completed（已完成）
- **priority（优先级）**: low（低）、medium（中）、high（高）

## 典型工作流
1. 查看统计：get_todo_stats
2. 列出待办：list_todos(status="pending")
3. 创建待办：create_todo(title="...", priority="high")
4. 标记完成：complete_todo(todo_id="...")

## 注意事项
- title 是创建时唯一必填字段
- tags 是字符串数组
- due_date 格式为 ISO 8601 日期时间
"""

    @mcp_server.prompt()
    def daily_review() -> str:
        return """请帮我进行每日待办事项回顾：
1. 首先获取统计信息了解整体情况
2. 列出所有待处理的高优先级任务
3. 列出所有进行中的任务
4. 根据情况给出建议"""

    # ============================================================
    # 🔗 组合API工具 - 一个Tool调用多个后端API
    # ============================================================

    @mcp_server.tool(
        description="""获取每日概览报告。一次性返回：待办统计摘要 + 今日待办列表 + 最近完成的任务。
这是一个聚合工具，内部会调用3个API：统计接口、待办列表、已完成列表。
适合快速了解整体情况，不用分别调用多个工具。""",
    )
    async def get_daily_overview(
        include_completed: bool = True,
    ) -> str:
        """
        获取每日待办概览（聚合3个API的数据）

        Args:
            include_completed: 是否包含已完成的任务

        Returns:
            格式化的Markdown概览报告
        """
        import json

        client = await builder._get_client()

        # 并行调用API
        tasks = [
            client.get("/todos/stats/summary"),
            client.get("/todos", params={"status": "pending", "limit": 10}),
        ]
        if include_completed:
            tasks.append(client.get("/todos", params={"status": "completed", "limit": 5}))

        responses = await asyncio.gather(*tasks)

        stats = responses[0].json()
        pending_data = responses[1].json()
        pending_todos = pending_data.get("items", pending_data) if isinstance(pending_data, dict) else pending_data
        completed_todos = None
        if include_completed and len(responses) > 2:
            completed_data = responses[2].json()
            completed_todos = completed_data.get("items", completed_data) if isinstance(completed_data, dict) else completed_data

        # 聚合并格式化
        lines = [
            "# 📊 每日待办概览",
            "",
            "## 📈 统计摘要",
            f"- 总任务数: **{stats['total']}**",
            f"- 待办: {stats['by_status']['pending']} 个",
            f"- 进行中: {stats['by_status']['in_progress']} 个",
            f"- 已完成: {stats['by_status']['completed']} 个",
            "",
            "## ⏳ 待处理任务 (Top 10)",
        ]

        if pending_todos:
            for todo in pending_todos[:10]:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(todo["priority"], "⚪")
                lines.append(f"- {priority_icon} [{todo['id']}] {todo['title']}")
        else:
            lines.append("- 暂无待办任务 🎉")

        if completed_todos and include_completed:
            lines += [
                "",
                "## ✅ 最近完成 (Top 5)",
            ]
            for todo in completed_todos[:5]:
                lines.append(f"- ✅ {todo['title']}")

        return "\n".join(lines)

    @mcp_server.tool(
        description="""完成指定待办事项，并自动获取下一个待处理的高优先级任务。
这是一个工作流编排工具，内部调用2个API：先标记完成，再获取下一个任务。
适合按顺序逐个处理任务的场景。""",
    )
    async def complete_todo_and_get_next(
        todo_id: str,
    ) -> str:
        """
        完成当前任务并获取下一个待办（工作流编排）

        Args:
            todo_id: 要完成的待办事项ID

        Returns:
            完成结果和下一个待办的信息
        """
        client = await builder._get_client()

        # 步骤1: 标记任务完成
        complete_resp = await client.post(f"/todos/{todo_id}/complete")
        if complete_resp.status_code != 200:
            return f"❌ 完成任务失败: {complete_resp.status_code} - {complete_resp.text}"

        completed = complete_resp.json()

        # 步骤2: 获取下一个高优先级待办
        next_resp = await client.get(
            "/todos",
            params={"status": "pending", "priority": "high", "limit": 1, "sort_by": "created_at", "order": "asc"},
        )

        lines = [
            f"✅ 已完成任务: **{completed['title']}**",
            f"   ID: {completed['id']}",
            "",
        ]

        next_data = next_resp.json() if next_resp.status_code == 200 else {}
        next_list = next_data.get("items", next_data) if isinstance(next_data, dict) else next_data
        if next_list:
            next_todo = next_list[0]
            lines += [
                "## 🎯 下一个高优先级任务",
                f"- 标题: **{next_todo['title']}**",
                f"- ID: `{next_todo['id']}`",
                f"- 优先级: {next_todo['priority']}",
            ]
            if next_todo.get("description"):
                lines.append(f"- 描述: {next_todo['description']}")
        else:
            lines.append("🎉 没有更多待处理的高优先级任务了！")

        return "\n".join(lines)

    @mcp_server.tool(
        description="""批量创建多个待办事项。一次性传入多个标题，自动循环创建。
这是一个批量操作工具，内部会循环调用创建API多次。
适合一次添加多个任务的场景。""",
    )
    async def bulk_create_todos(
        titles: list[str],
        priority: str = "medium",
    ) -> str:
        """
        批量创建待办事项（循环调用创建API）

        Args:
            titles: 待办标题列表（可以传多个）
            priority: 统一的优先级，默认 medium

        Returns:
            批量创建结果汇总
        """
        client = await builder._get_client()

        results = []
        success_count = 0
        fail_count = 0

        # 循环调用创建API
        for title in titles:
            try:
                resp = await client.post(
                    "/todos",
                    json={"title": title, "priority": priority},
                )
                if resp.status_code in (200, 201):
                    todo = resp.json()
                    results.append(f"✅ [{todo['id']}] {title}")
                    success_count += 1
                else:
                    results.append(f"❌ {title} - HTTP {resp.status_code}")
                    fail_count += 1
            except Exception as e:
                results.append(f"❌ {title} - {str(e)}")
                fail_count += 1

        summary = [
            f"# 📦 批量创建结果",
            "",
            f"成功: **{success_count}** 个 | 失败: **{fail_count}** 个",
            "",
            "## 详细结果",
        ] + results

        return "\n".join(summary)

    return mcp_server, builder


def main():
    mcp_server, _ = create_todo_mcp_server()
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
