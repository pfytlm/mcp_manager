"""
MCP HTTP 服务启动模块
将 MCP 服务通过 HTTP 对外暴露（SSE 和 streamable-http 两种传输模式）
外部 AI 客户端可以通过 MCP 协议的 HTTP 传输方式连接
"""
from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .config import config
from .examples.todo_mcp import create_todo_mcp_server
from .examples.calc_mcp import create_calc_mcp_server


def create_mcp_server(server_name: str, host: str = "0.0.0.0") -> FastMCP:
    """
    创建指定名称的MCP服务器实例

    Args:
        server_name: MCP服务名称 (todo-mcp-server / calculator-mcp-server)
        host: 允许访问的host（用于Host header验证，0.0.0.0表示允许所有）

    Returns:
        FastMCP 实例
    """
    if server_name == "todo-mcp-server":
        mcp_server, _ = create_todo_mcp_server(
            base_url=config.todo_api_url,
            verify_ssl=False,
        )
    elif server_name == "calculator-mcp-server":
        mcp_server, _ = create_calc_mcp_server(
            base_url=config.calc_api_url,
            verify_ssl=False,
        )
    else:
        raise ValueError(f"未知的MCP服务: {server_name}")

    mcp_server.host = host
    mcp_server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=[],
        allowed_origins=[],
    )
    return mcp_server


def create_mcp_sse_app(server_name: str) -> FastAPI:
    """
    创建指定MCP服务的SSE FastAPI应用

    Args:
        server_name: MCP服务名称

    Returns:
        FastAPI 应用（包含 SSE 端点）
    """
    mcp_server = create_mcp_server(server_name)
    return mcp_server.sse_app()


def create_mcp_streamable_http_app(server_name: str) -> FastAPI:
    """
    创建指定MCP服务的Streamable HTTP FastAPI应用

    Args:
        server_name: MCP服务名称

    Returns:
        FastAPI 应用（包含 streamable-http 端点）
    """
    mcp_server = create_mcp_server(server_name)
    return mcp_server.streamable_http_app()


def run_mcp_sse_server(server_name: str, host: str = "0.0.0.0", port: int = 8001):
    """
    启动MCP SSE服务

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
    启动MCP Streamable HTTP服务

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


def run_todo_sse():
    """启动TODO MCP SSE服务（端口8001）"""
    run_mcp_sse_server("todo-mcp-server", port=8001)


def run_calc_sse():
    """启动计算器MCP SSE服务（端口8003）"""
    run_mcp_sse_server("calculator-mcp-server", port=8003)


def run_todo_streamable_http():
    """启动TODO MCP Streamable HTTP服务（端口8001）"""
    run_mcp_streamable_http_server("todo-mcp-server", port=8001)


def run_calc_streamable_http():
    """启动计算器MCP Streamable HTTP服务（端口8003）"""
    run_mcp_streamable_http_server("calculator-mcp-server", port=8003)


def _todo_sse_app_factory():
    """uvicorn工厂函数: 创建TODO MCP SSE应用"""
    return create_mcp_sse_app("todo-mcp-server")


def _calc_sse_app_factory():
    """uvicorn工厂函数: 创建计算器MCP SSE应用"""
    return create_mcp_sse_app("calculator-mcp-server")


def _todo_streamable_http_app_factory():
    """uvicorn工厂函数: 创建TODO MCP Streamable HTTP应用"""
    return create_mcp_streamable_http_app("todo-mcp-server")


def _calc_streamable_http_app_factory():
    """uvicorn工厂函数: 创建计算器MCP Streamable HTTP应用"""
    return create_mcp_streamable_http_app("calculator-mcp-server")
