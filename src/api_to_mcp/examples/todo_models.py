from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TodoPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TodoBase(BaseModel):
    title: str = Field(..., description="待办事项标题", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="待办事项详细描述")
    status: TodoStatus = Field(TodoStatus.PENDING, description="待办事项状态")
    priority: TodoPriority = Field(TodoPriority.MEDIUM, description="优先级")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, description="待办事项标题", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="待办事项详细描述")
    status: Optional[TodoStatus] = Field(None, description="待办事项状态")
    priority: Optional[TodoPriority] = Field(None, description="优先级")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class Todo(TodoBase):
    id: UUID = Field(default_factory=uuid4, description="待办事项唯一ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    model_config = {"from_attributes": True}


class TodoListResponse(BaseModel):
    items: List[Todo] = Field(..., description="待办事项列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="错误信息")
    details: Optional[dict] = Field(None, description="错误详情")
