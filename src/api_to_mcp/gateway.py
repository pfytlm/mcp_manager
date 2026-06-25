"""
统一网关模块
将所有服务（管理后台、MCP服务、API服务）整合到同一个端口
通过 URL 路径前缀区分不同服务

URL 结构:
  /                    -> 管理后台 UI + API
  /mcp                 -> MCP 网关首页
  /mcp/todo            -> TODO MCP 服务
  /mcp/calc            -> 计算器 MCP 服务
  /api/todo            -> TODO REST API
  /api/calc            -> 计算器 REST API
"""
from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings

from .config import config
from .examples.todo_api import app as todo_api_app
from .examples.calc_api import app as calc_api_app
from .examples.todo_mcp import create_todo_mcp_server
from .examples.calc_mcp import create_calc_mcp_server
from .manager import create_manager_app, register_example_services


def _create_mcp_app(service_key: str):
    """创建指定服务的 MCP streamable-http 应用"""
    if service_key == "todo":
        mcp_server, _ = create_todo_mcp_server(
            base_url=f"{config.PLATFORM_SCHEME}://{config.PLATFORM_HOST}/api/todo",
            verify_ssl=False,
        )
    elif service_key == "calc":
        mcp_server, _ = create_calc_mcp_server(
            base_url=f"{config.PLATFORM_SCHEME}://{config.PLATFORM_HOST}/api/calc",
            verify_ssl=False,
        )
    else:
        raise ValueError(f"未知的MCP服务: {service_key}")

    mcp_server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=[],
        allowed_origins=[],
    )
    return mcp_server.streamable_http_app()


def create_unified_gateway() -> FastAPI:
    """
    创建统一网关应用，所有服务共享同一个端口

    Returns:
        FastAPI 统一网关应用
    """
    app = FastAPI(
        title="MCP Manager Platform",
        description="统一的 MCP 服务管理平台 - 管理后台、MCP服务、API服务",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_example_services()

    app.mount("/mcp/todo", _create_mcp_app("todo"), name="todo-mcp")
    print("✅ 已挂载: /mcp/todo -> TODO MCP 服务")

    app.mount("/mcp/calc", _create_mcp_app("calc"), name="calc-mcp")
    print("✅ 已挂载: /mcp/calc -> 计算器 MCP 服务")

    app.mount("/api/todo", todo_api_app, name="todo-api")
    print("✅ 已挂载: /api/todo -> TODO REST API")

    app.mount("/api/calc", calc_api_app, name="calc-api")
    print("✅ 已挂载: /api/calc -> 计算器 REST API")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    print("✅ 已挂载: /health -> 健康检查")

    @app.get("/mcp")
    async def mcp_gateway():
        return JSONResponse(
            content={
                "message": "MCP Service Gateway",
                "services": {
                    "todo": {"name": "todo-mcp-server", "endpoint": "/mcp/todo"},
                    "calc": {"name": "calculator-mcp-server", "endpoint": "/mcp/calc"},
                }
            }
        )

    print("✅ 已挂载: /mcp -> MCP 网关首页")

    manager_app = create_manager_app()
    app.mount("/", manager_app, name="manager")
    print("✅ 已挂载: / -> 管理后台")

    return app


def run_unified_gateway(host: str = "0.0.0.0", port: int = 8080):
    """
    启动统一网关服务

    Args:
        host: 监听地址
        port: 监听端口
    """
    app = create_unified_gateway()
    ssl_opts = config.get_ssl_context() or {}
    protocol = "https" if ssl_opts else "http"
    print(f"\n🚀 MCP Manager 统一网关启动")
    print(f"   地址: {protocol}://{host}:{port}")
    print(f"   管理后台: {protocol}://{host}:{port}/")
    print(f"   MCP网关:  {protocol}://{host}:{port}/mcp")
    print(f"   TODO MCP: {protocol}://{host}:{port}/mcp/todo")
    print(f"   计算器MCP: {protocol}://{host}:{port}/mcp/calc")
    print(f"   TODO API: {protocol}://{host}:{port}/api/todo")
    print(f"   计算器API: {protocol}://{host}:{port}/api/calc")
    print()
    uvicorn.run(app, host=host, port=port, **ssl_opts)


def _unified_gateway_factory():
    """uvicorn工厂函数: 创建统一网关应用"""
    return create_unified_gateway()
