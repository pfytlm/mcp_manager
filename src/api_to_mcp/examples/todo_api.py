from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ..config import config

from .todo_models import (
    Todo,
    TodoCreate,
    TodoListResponse,
    TodoPriority,
    TodoStatus,
    TodoUpdate,
)

app = FastAPI(
    title="TODO API 服务",
    description="一个示例待办事项REST API服务，用于演示如何转化为MCP服务",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

todos_db: Dict[UUID, Todo] = {}


def _init_sample_data():
    sample_todos = [
        TodoCreate(
            title="学习MCP协议",
            description="深入了解Model Context Protocol的工作原理",
            priority=TodoPriority.HIGH,
            tags=["学习", "MCP", "AI"],
        ),
        TodoCreate(
            title="完成API到MCP的转化",
            description="将现有的REST API服务转化为MCP服务",
            priority=TodoPriority.HIGH,
            tags=["开发", "MCP"],
        ),
        TodoCreate(
            title="编写项目文档",
            description="为项目编写完整的使用文档",
            priority=TodoPriority.MEDIUM,
            status=TodoStatus.IN_PROGRESS,
            tags=["文档"],
        ),
    ]
    for todo_data in sample_todos:
        todo = Todo(**todo_data.model_dump())
        todos_db[todo.id] = todo


_init_sample_data()


@app.get("/", tags=["系统"])
async def root():
    return {
        "service": "TODO API Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["系统"])
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/todos", response_model=TodoListResponse, tags=["待办事项"])
async def list_todos(
    status: Optional[TodoStatus] = Query(None, description="按状态筛选"),
    priority: Optional[TodoPriority] = Query(None, description="按优先级筛选"),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    filtered = list(todos_db.values())

    if status:
        filtered = [t for t in filtered if t.status == status]
    if priority:
        filtered = [t for t in filtered if t.priority == priority]
    if tag:
        filtered = [t for t in filtered if tag in t.tags]

    filtered.sort(key=lambda x: x.created_at, reverse=True)

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    return TodoListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@app.get("/todos/{todo_id}", response_model=Todo, tags=["待办事项"])
async def get_todo(todo_id: UUID):
    todo = todos_db.get(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail=f"待办事项 {todo_id} 不存在")
    return todo


@app.post("/todos", response_model=Todo, status_code=201, tags=["待办事项"])
async def create_todo(todo_data: TodoCreate):
    todo = Todo(**todo_data.model_dump())
    todos_db[todo.id] = todo
    return todo


@app.put("/todos/{todo_id}", response_model=Todo, tags=["待办事项"])
async def update_todo(todo_id: UUID, todo_data: TodoUpdate):
    todo = todos_db.get(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail=f"待办事项 {todo_id} 不存在")

    update_dict = todo_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(todo, field, value)

    todo.updated_at = datetime.now()

    if todo.status == TodoStatus.COMPLETED and not todo.completed_at:
        todo.completed_at = datetime.now()
    elif todo.status != TodoStatus.COMPLETED:
        todo.completed_at = None

    todos_db[todo_id] = todo
    return todo


@app.delete("/todos/{todo_id}", status_code=204, tags=["待办事项"])
async def delete_todo(todo_id: UUID):
    if todo_id not in todos_db:
        raise HTTPException(status_code=404, detail=f"待办事项 {todo_id} 不存在")
    del todos_db[todo_id]
    return None


@app.post("/todos/{todo_id}/complete", response_model=Todo, tags=["待办事项"])
async def complete_todo(todo_id: UUID):
    todo = todos_db.get(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail=f"待办事项 {todo_id} 不存在")

    todo.status = TodoStatus.COMPLETED
    todo.completed_at = datetime.now()
    todo.updated_at = datetime.now()
    todos_db[todo_id] = todo
    return todo


@app.get("/todos/stats/summary", tags=["待办事项"])
async def get_stats():
    all_todos = list(todos_db.values())
    return {
        "total": len(all_todos),
        "by_status": {
            status.value: len([t for t in all_todos if t.status == status])
            for status in TodoStatus
        },
        "by_priority": {
            priority.value: len([t for t in all_todos if t.priority == priority])
            for priority in TodoPriority
        },
    }


def main():
    ssl_opts = config.get_ssl_context()
    uvicorn.run(
        "api_to_mcp.examples.todo_api:app",
        host="0.0.0.0",
        port=config.TODO_API_PORT,
        reload=True,
        **(ssl_opts or {}),
    )


if __name__ == "__main__":
    main()
