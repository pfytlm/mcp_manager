"""
MCP HTTP 服务启动模块
将多个 MCP 服务通过统一的 HTTP 网关对外暴露
支持通过 URL 路径区分不同服务：/todo/mcp 和 /calc/mcp
"""
from __future__ import annotations

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.routing import Mount
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .config import config
from .examples.todo_mcp import create_todo_mcp_server
from .examples.calc_mcp import create_calc_mcp_server


_SERVICE_MAP = {
    "todo": {
        "server_name": "todo-mcp-server",
        "create_func": create_todo_mcp_server,
        "api_url": config.todo_api_url,
    },
    "calc": {
        "server_name": "calculator-mcp-server",
        "create_func": create_calc_mcp_server,
        "api_url": config.calc_api_url,
    },
}


def create_mcp_server(service_key: str, host: str = "0.0.0.0") -> FastMCP:
    """
    创建指定服务的MCP服务器实例

    Args:
        service_key: 服务标识 (todo / calc)
        host: 允许访问的host（用于Host header验证，0.0.0.0表示允许所有）

    Returns:
        FastMCP 实例
    """
    service_info = _SERVICE_MAP.get(service_key)
    if not service_info:
        raise ValueError(f"未知的MCP服务: {service_key}")

    mcp_server, _ = service_info["create_func"](
        base_url=service_info["api_url"],
        verify_ssl=False,
    )

    mcp_server.host = host
    mcp_server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=[],
        allowed_origins=[],
    )
    return mcp_server


def create_unified_mcp_gateway() -> FastAPI:
    """
    创建统一的 MCP 网关应用，通过 URL 路径区分不同服务

    URL 结构:
    - https://host:8001/todo/mcp - TODO MCP 服务
    - https://host:8001/calc/mcp - 计算器 MCP 服务

    Returns:
        FastAPI 网关应用
    """
    app = FastAPI(
        title="MCP Service Gateway",
        description="统一的 MCP 服务网关，通过 URL 路径区分不同服务",
        version="1.0.0",
    )

    for service_key, service_info in _SERVICE_MAP.items():
        mcp_server = create_mcp_server(service_key)
        http_app = mcp_server.streamable_http_app()
        app.mount(f"/{service_key}/mcp", http_app, name=f"{service_key}-mcp")
        print(f"✅ 已挂载服务: /{service_key}/mcp -> {service_info['server_name']}")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "services": list(_SERVICE_MAP.keys())}

    @app.get("/")
    async def index():
        return {
            "message": "MCP Service Gateway",
            "services": {
                key: {
                    "name": info["server_name"],
                    "endpoint": f"/{key}/mcp",
                }
                for key, info in _SERVICE_MAP.items()
            }
        }

    return app


def create_mcp_sse_app(server_name: str) -> FastAPI:
    """
    创建指定MCP服务的SSE FastAPI应用（兼容旧版）

    Args:
        server_name: MCP服务名称

    Returns:
        FastAPI 应用（包含 SSE 端点）
    """
    mcp_server = create_mcp_server(server_name)
    return mcp_server.sse_app()


def create_mcp_streamable_http_app(server_name: str) -> FastAPI:
    """
    创建指定MCP服务的Streamable HTTP FastAPI应用（兼容旧版）

    Args:
        server_name: MCP服务名称

    Returns:
        FastAPI 应用（包含 streamable-http 端点）
    """
    mcp_server = create_mcp_server(server_name)
    return mcp_server.streamable_http_app()


def run_mcp_sse_server(server_name: str, host: str = "0.0.0.0", port: int = 8001):
    """
    启动MCP SSE服务（兼容旧版）

    Args:
        server_name: MCP服务名称
        host: 监听地址
        port: 监听端口
    """
    app = create_mcp_sse_app(server_name)
    print(f"\n🚀 MCP SSE Server 启动: {server_name}")
    print(f"   地址: http://{host}:{port}/sse")
    print(f"   协议: MCP over HTTP (SSE transport)\n")
    uvicorn.run(app, host=host, port=port)


def run_mcp_streamable_http_server(server_name: str, host: str = "0.0.0.0", port: int = 8001):
    """
    启动MCP Streamable HTTP服务（兼容旧版）

    Args:
        server_name: MCP服务名称
        host: 监听地址
        port: 监听端口
    """
    app = create_mcp_streamable_http_app(server_name)
    print(f"\n🚀 MCP Streamable HTTP Server 启动: {server_name}")
    print(f"   地址: http://{host}:{port}/mcp")
    print(f"   协议: MCP over HTTP (streamable-http transport)\n")
    uvicorn.run(app, host=host, port=port)


def run_unified_mcp_gateway(host: str = "0.0.0.0", port: int = 8001):
    """
    启动统一的 MCP 网关服务

    Args:
        host: 监听地址
        port: 监听端口
    """
    app = create_unified_mcp_gateway()
    print(f"\n🚀 MCP Unified Gateway 启动")
    print(f"   地址: http://{host}:{port}")
    print(f"   TODO MCP: http://{host}:{port}/todo/mcp")
    print(f"   计算器MCP: http://{host}:{port}/calc/mcp")
    print(f"   协议: MCP over HTTP (streamable-http transport)\n")
    uvicorn.run(app, host=host, port=port)


def run_todo_sse():
    """启动TODO MCP SSE服务（端口8001）"""
    run_mcp_sse_server("todo", port=8001)


def run_calc_sse():
    """启动计算器MCP SSE服务（端口8003）"""
    run_mcp_sse_server("calc", port=8003)


def run_todo_streamable_http():
    """启动TODO MCP Streamable HTTP服务（端口8001）"""
    run_mcp_streamable_http_server("todo", port=8001)


def run_calc_streamable_http():
    """启动计算器MCP Streamable HTTP服务（端口8003）"""
    run_mcp_streamable_http_server("calc", port=8003)


def _unified_mcp_gateway_factory():
    """uvicorn工厂函数: 创建统一MCP网关应用"""
    return create_unified_mcp_gateway()


def _todo_sse_app_factory():
    """uvicorn工厂函数: 创建TODO MCP SSE应用（兼容旧版）"""
    return create_mcp_sse_app("todo")


def _calc_sse_app_factory():
    """uvicorn工厂函数: 创建计算器MCP SSE应用（兼容旧版）"""
    return create_mcp_sse_app("calc")


def _todo_streamable_http_app_factory():
    """uvicorn工厂函数: 创建TODO MCP Streamable HTTP应用（兼容旧版）"""
    return create_mcp_streamable_http_app("todo")


def _calc_streamable_http_app_factory():
    """uvicorn工厂函数: 创建计算器MCP Streamable HTTP应用（兼容旧版）"""
    return create_mcp_streamable_http_app("calc")
