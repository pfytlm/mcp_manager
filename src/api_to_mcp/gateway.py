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

认证方式:
  Bearer Token 认证 (Authorization: Bearer <token>)
  配置: MCP_AUTH_TOKENS=token1,token2
"""
from __future__ import annotations

import os
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from mcp.server.transport_security import TransportSecuritySettings
from pathlib import Path

from .config import config
from .examples.todo_api import app as todo_api_app
from .examples.calc_api import app as calc_api_app
from .examples.todo_mcp import create_todo_mcp_server
from .examples.calc_mcp import create_calc_mcp_server
from .manager import register_example_services


def _get_valid_tokens() -> set[str]:
    """获取有效的认证 token 集合"""
    token_str = os.getenv("MCP_AUTH_TOKENS", "")
    if not token_str:
        return set()
    return {t.strip() for t in token_str.split(",") if t.strip()}


VALID_TOKENS = _get_valid_tokens()


async def _auth_middleware(request: Request, call_next):
    """Bearer Token 认证中间件"""
    if not VALID_TOKENS:
        return await call_next(request)

    if request.url.path.startswith("/mcp/todo") or request.url.path.startswith("/mcp/calc"):
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Unauthorized", "message": "Missing or invalid Authorization header"},
            )
        token = auth_header[7:]
        if token not in VALID_TOKENS:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Unauthorized", "message": "Invalid token"},
            )
    return await call_next(request)


def _create_mcp_app(service_key: str):
    """创建指定服务的 MCP streamable-http 应用"""
    if service_key == "todo":
        mcp_server, _ = create_todo_mcp_server(
            base_url=config.todo_api_url,
            verify_ssl=False,
        )
    elif service_key == "calc":
        mcp_server, _ = create_calc_mcp_server(
            base_url=config.calc_api_url,
            verify_ssl=False,
        )
    else:
        raise ValueError(f"未知的MCP服务: {service_key}")

    mcp_server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=[],
        allowed_origins=[],
    )
    return mcp_server


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

    app.middleware("http")(_auth_middleware)

    register_example_services()

    import httpx

    todo_mcp_server = _create_mcp_app("todo")
    calc_mcp_server = _create_mcp_app("calc")

    todo_mcp_port = 18001
    calc_mcp_port = 18003

    async def _start_mcp_servers():
        import asyncio
        from uvicorn import Config, Server

        async def start_server(mcp_server, port):
            config = Config(
                app=mcp_server.streamable_http_app(),
                host="127.0.0.1",
                port=port,
                loop="asyncio",
                log_level="error",
            )
            server = Server(config)
            await server.serve()

        await asyncio.gather(
            start_server(todo_mcp_server, todo_mcp_port),
            start_server(calc_mcp_server, calc_mcp_port),
        )

    import asyncio
    asyncio.create_task(_start_mcp_servers())

    @app.post("/mcp/todo")
    async def proxy_todo_mcp(request: Request):
        from fastapi.responses import StreamingResponse
        
        async with httpx.AsyncClient(verify=False) as client:
            headers = dict(request.headers)
            headers.pop("host", None)
            headers.pop("content-length", None)
            
            body = await request.body()
            
            response = await client.post(
                f"http://127.0.0.1:{todo_mcp_port}/mcp",
                content=body,
                headers=headers,
                timeout=30,
            )
            
            response_headers = {k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding"]}
            
            return StreamingResponse(response.aiter_bytes(), status_code=response.status_code, headers=response_headers)

    @app.post("/mcp/calc")
    async def proxy_calc_mcp(request: Request):
        from fastapi.responses import StreamingResponse
        
        async with httpx.AsyncClient(verify=False) as client:
            headers = dict(request.headers)
            headers.pop("host", None)
            headers.pop("content-length", None)
            
            body = await request.body()
            
            response = await client.post(
                f"http://127.0.0.1:{calc_mcp_port}/mcp",
                content=body,
                headers=headers,
                timeout=30,
            )
            
            response_headers = {k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding"]}
            
            return StreamingResponse(response.aiter_bytes(), status_code=response.status_code, headers=response_headers)

    @app.get("/mcp/todo")
    async def proxy_todo_mcp_get(request: Request):
        async with httpx.AsyncClient(verify=False) as client:
            headers = dict(request.headers)
            headers.pop("host", None)
            
            response = await client.get(
                f"http://127.0.0.1:{todo_mcp_port}/mcp",
                headers=headers,
                timeout=30,
            )
            
            response_headers = {k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding"]}
            
            return StreamingResponse(response.aiter_bytes(), status_code=response.status_code, headers=response_headers)

    @app.get("/mcp/calc")
    async def proxy_calc_mcp_get(request: Request):
        async with httpx.AsyncClient(verify=False) as client:
            headers = dict(request.headers)
            headers.pop("host", None)
            
            response = await client.get(
                f"http://127.0.0.1:{calc_mcp_port}/mcp",
                headers=headers,
                timeout=30,
            )
            
            response_headers = {k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding"]}
            
            return StreamingResponse(response.aiter_bytes(), status_code=response.status_code, headers=response_headers)

    print("✅ 已挂载: /mcp/todo -> TODO MCP 服务")
    print("✅ 已挂载: /mcp/calc -> 计算器 MCP 服务")

    app.mount("/api/todo", todo_api_app, name="todo-api")
    print("✅ 已挂载: /api/todo -> TODO REST API")

    app.mount("/api/calc", calc_api_app, name="calc-api")
    print("✅ 已挂载: /api/calc -> 计算器 REST API")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "auth_enabled": len(VALID_TOKENS) > 0}

    print("✅ 已挂载: /health -> 健康检查")

    @app.get("/mcp")
    async def mcp_gateway():
        return JSONResponse(
            content={
                "message": "MCP Service Gateway",
                "auth_enabled": len(VALID_TOKENS) > 0,
                "services": {
                    "todo": {"name": "todo-mcp-server", "endpoint": "/mcp/todo"},
                    "calc": {"name": "calculator-mcp-server", "endpoint": "/mcp/calc"},
                }
            }
        )

    print("✅ 已挂载: /mcp -> MCP 网关首页")

    from .manager import create_manager_router, _init_api_keys

    _init_api_keys()

    manager_router = create_manager_router()
    app.include_router(manager_router)

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", response_class=HTMLResponse)
        async def index():
            index_file = static_dir / "index.html"
            if index_file.exists():
                return index_file.read_text(encoding="utf-8")
            return HTMLResponse(content="<h1>MCP Manager</h1>")

    print("✅ 已挂载: / -> 管理后台")

    if VALID_TOKENS:
        print(f"🔒 认证已启用，共 {len(VALID_TOKENS)} 个有效 token")
    else:
        print("⚠️ 认证未启用 (MCP_AUTH_TOKENS 未配置)")

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
