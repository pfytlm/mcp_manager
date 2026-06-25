from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .registry import get_registry
from .config import config


class ToolCallRequest(BaseModel):
    service_name: str
    tool_name: str
    arguments: Dict[str, Any] = {}


class ResourceReadRequest(BaseModel):
    service_name: str
    uri: str


class PromptGetRequest(BaseModel):
    service_name: str
    prompt_name: str
    arguments: Dict[str, Any] = {}


def _get_mcp_url(service_name: str) -> Optional[str]:
    registry = get_registry()
    service = registry.get(service_name)
    if not service:
        return None
    return service.base_url


async def _call_mcp_tool(mcp_url: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    from mcp.client.streamable_http import streamable_http_client
    from mcp import ClientSession
    from mcp.client.session import ClientSession as Session

    async with streamable_http_client(
        mcp_url,
        http_client=httpx.AsyncClient(verify=False, timeout=30),
    ) as streams:
        read_stream, write_stream = streams[0], streams[1]
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

            text_parts = []
            if hasattr(result, 'content'):
                for item in result.content:
                    if hasattr(item, 'text'):
                        text_parts.append(item.text)
                    elif isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])

            output = '\n'.join(text_parts) if text_parts else str(result)
            return {"success": True, "result": output}


async def _read_mcp_resource(mcp_url: str, uri: str) -> Dict[str, Any]:
    from mcp.client.streamable_http import streamable_http_client
    from mcp import ClientSession

    async with streamable_http_client(
        mcp_url,
        http_client=httpx.AsyncClient(verify=False, timeout=30),
    ) as streams:
        read_stream, write_stream = streams[0], streams[1]
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.read_resource(uri)

            text_parts = []
            if hasattr(result, 'contents'):
                for item in result.contents:
                    if hasattr(item, 'text'):
                        text_parts.append(item.text)
                    elif hasattr(item, 'content'):
                        text_parts.append(item.content)
                    elif isinstance(item, dict):
                        if 'text' in item:
                            text_parts.append(item['text'])
                        elif 'content' in item:
                            text_parts.append(item['content'])

            output = '\n'.join(text_parts) if text_parts else str(result)
            return {"success": True, "result": output}


async def _get_mcp_prompt(mcp_url: str, prompt_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    from mcp.client.streamable_http import streamable_http_client
    from mcp import ClientSession

    async with streamable_http_client(
        mcp_url,
        http_client=httpx.AsyncClient(verify=False, timeout=30),
    ) as streams:
        read_stream, write_stream = streams[0], streams[1]
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.get_prompt(prompt_name, arguments)

            text_parts = []
            if hasattr(result, 'messages'):
                for msg in result.messages:
                    if hasattr(msg, 'content'):
                        content = msg.content
                        if hasattr(content, 'text'):
                            text_parts.append(content.text)
                        elif isinstance(content, list):
                            for item in content:
                                if hasattr(item, 'text'):
                                    text_parts.append(item.text)

            output = '\n'.join(text_parts) if text_parts else str(result)
            return {"success": True, "result": output}


def create_manager_app() -> FastAPI:
    app = FastAPI(
        title="MCP Service Manager",
        description="MCP服务管理后台 - 查看和管理所有MCP服务配置",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _serialize_service(service) -> Dict[str, Any]:
        has_auth = bool(service.headers)
        auth_type = "Bearer Token" if service.headers and "Authorization" in service.headers else None
        data = {
            "name": service.name,
            "description": service.description,
            "base_url": service.base_url,
            "instructions": service.instructions,
            "transport": service.transport,
            "has_auth": has_auth,
            "auth_type": auth_type,
            "tags": service.tags,
            "tools": [],
            "resources": [],
            "prompts": [],
        }
        for tool in service.tools:
            data["tools"].append({
                "name": tool.name,
                "description": tool.description,
                "method": tool.method,
                "path": tool.path,
                "parameters": tool.parameters,
                "input_schema": tool.input_schema,
            })
        for res in service.resources:
            data["resources"].append({
                "uri": res.uri,
                "name": res.name,
                "description": res.description,
                "mime_type": res.mime_type,
            })
        for prompt in service.prompts:
            data["prompts"].append({
                "name": prompt.name,
                "description": prompt.description,
                "arguments": prompt.arguments,
            })
        return data

    @app.get("/api/services", tags=["MCP管理"])
    async def list_services():
        registry = get_registry()
        services = registry.list_services()
        return {
            "total": len(services),
            "services": [_serialize_service(s) for s in services]
        }

    @app.get("/api/services/{service_name}", tags=["MCP管理"])
    async def get_service(service_name: str):
        registry = get_registry()
        service = registry.get(service_name)
        if not service:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        return _serialize_service(service)

    @app.get("/api/health", tags=["系统"])
    async def health():
        registry = get_registry()
        return {
            "status": "healthy",
            "services_count": len(registry.list_services()),
        }

    @app.post("/api/test/tool", tags=["MCP测试"])
    async def test_tool(req: ToolCallRequest):
        mcp_url = _get_mcp_url(req.service_name)
        if not mcp_url:
            raise HTTPException(status_code=404, detail=f"Service {req.service_name} not found")

        try:
            result = await _call_mcp_tool(mcp_url, req.tool_name, req.arguments)
            return {
                "success": True,
                "tool": req.tool_name,
                "result": result["result"],
                "mcp_url": mcp_url,
                "method": "tools/call",
            }
        except Exception as e:
            return {
                "success": False,
                "tool": req.tool_name,
                "error": str(e),
                "mcp_url": mcp_url,
            }

    @app.post("/api/test/resource", tags=["MCP测试"])
    async def test_resource(req: ResourceReadRequest):
        mcp_url = _get_mcp_url(req.service_name)
        if not mcp_url:
            raise HTTPException(status_code=404, detail=f"Service {req.service_name} not found")

        try:
            result = await _read_mcp_resource(mcp_url, req.uri)
            return {
                "success": True,
                "uri": req.uri,
                "result": result["result"],
                "mcp_url": mcp_url,
                "method": "resources/read",
            }
        except Exception as e:
            return {
                "success": False,
                "uri": req.uri,
                "error": str(e),
                "mcp_url": mcp_url,
            }

    @app.post("/api/test/prompt", tags=["MCP测试"])
    async def test_prompt(req: PromptGetRequest):
        mcp_url = _get_mcp_url(req.service_name)
        if not mcp_url:
            raise HTTPException(status_code=404, detail=f"Service {req.service_name} not found")

        try:
            result = await _get_mcp_prompt(mcp_url, req.prompt_name, req.arguments)
            return {
                "success": True,
                "prompt": req.prompt_name,
                "result": result["result"],
                "mcp_url": mcp_url,
                "method": "prompts/get",
            }
        except Exception as e:
            return {
                "success": False,
                "prompt": req.prompt_name,
                "error": str(e),
                "mcp_url": mcp_url,
            }

    @app.get("/api/config", tags=["配置"])
    async def get_config():
        return {
            "platform_url": config.platform_url,
            "platform_host": config.PLATFORM_HOST,
            "platform_port": config.PLATFORM_PORT,
            "platform_scheme": config.PLATFORM_SCHEME,
            "todo_mcp_url": config.todo_mcp_url,
            "calc_mcp_url": config.calc_mcp_url,
        }

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", response_class=HTMLResponse, tags=["UI"])
        async def index():
            index_file = static_dir / "index.html"
            if index_file.exists():
                return index_file.read_text(encoding="utf-8")
            return HTMLResponse(content="<h1>MCP Manager</h1>")

    return app


def register_example_services():
    from .examples.todo_mcp import get_todo_service_metadata
    from .examples.calc_mcp import get_calc_service_metadata
    from .registry import MCPServiceDefinition, get_registry

    registry = get_registry()

    metadata = get_todo_service_metadata(base_url=config.todo_mcp_url)
    service = MCPServiceDefinition(
        name=metadata["name"],
        description=metadata["description"],
        base_url=config.todo_mcp_url,
        instructions=metadata["instructions"],
        headers={},
        transport="streamable-http",
        tools=metadata["tools"],
        resources=metadata["resources"],
        prompts=metadata["prompts"],
        tags=metadata["tags"],
    )
    registry.register(service)

    calc_metadata = get_calc_service_metadata(base_url=config.calc_mcp_url)
    calc_service = MCPServiceDefinition(
        name=calc_metadata["name"],
        description=calc_metadata["description"],
        base_url=config.calc_mcp_url,
        instructions=calc_metadata["instructions"],
        headers={},
        transport="streamable-http",
        tools=calc_metadata["tools"],
        resources=calc_metadata["resources"],
        prompts=calc_metadata["prompts"],
        tags=calc_metadata["tags"],
    )
    registry.register(calc_service)


def main():
    register_example_services()
    app = create_manager_app()
    print(f"\n🚀 MCP服务管理后台启动: {config.platform_url}")
    print(f"📊 API端点: {config.platform_url}/api/services")
    print()
    ssl_opts = config.get_ssl_context()
    uvicorn.run(app, host="0.0.0.0", port=config.PLATFORM_PORT, **(ssl_opts or {}))


register_example_services()
app = create_manager_app()


if __name__ == "__main__":
    main()
