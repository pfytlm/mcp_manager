from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .registry import MCPToolInfo, MCPResourceInfo, MCPPromptInfo, MCPServiceDefinition, get_registry
from .config import config


class ToolCallRequest(BaseModel):
    service_name: str
    tool_name: str
    arguments: Dict[str, Any] = {}
    key_id: Optional[str] = None


class ResourceReadRequest(BaseModel):
    service_name: str
    uri: str
    key_id: Optional[str] = None


class PromptGetRequest(BaseModel):
    service_name: str
    prompt_name: str
    arguments: Dict[str, Any] = {}
    key_id: Optional[str] = None


class ApiKeyCreate(BaseModel):
    name: str
    key: Optional[str] = None
    is_default: bool = False


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_default: Optional[bool] = None


class ApiKeyInfo(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_default: bool
    created_at: str


class MCPServiceCreate(BaseModel):
    name: str
    description: str
    base_url: str
    instructions: Optional[str] = None
    transport: str = "streamable-http"
    auth_type: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    resources: List[Dict[str, Any]] = Field(default_factory=list)
    prompts: List[Dict[str, Any]] = Field(default_factory=list)


class MCPServiceUpdate(BaseModel):
    description: Optional[str] = None
    base_url: Optional[str] = None
    instructions: Optional[str] = None
    auth_type: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    tags: Optional[List[str]] = None


def _get_mcp_url(service_name: str) -> Optional[str]:
    registry = get_registry()
    service = registry.get(service_name)
    if not service:
        return None
    return service.base_url


def _generate_mcp_curl(mcp_url: str, method: str, params: Dict[str, Any], auth_header: Optional[str] = None) -> str:
    import uuid
    session_id = f"test-session-{uuid.uuid4().hex[:8]}"
    request_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    auth_line = ''
    if auth_header:
        auth_line = f'  -H "Authorization: {auth_header}" \\\n'
    body_str = json.dumps(request_body, ensure_ascii=False, indent=2).replace("'", "'\\''")
    return f'''curl -X POST "{mcp_url}?sessionId={session_id}" \\
{auth_line}  -H "Accept: application/json, text/event-stream" \\
  -H "Content-Type: application/json" \\
  -d '{body_str}\''''


async def _call_mcp_tool(mcp_url: str, tool_name: str, arguments: Dict[str, Any], auth_header: Optional[str] = None) -> Dict[str, Any]:
    from mcp.client.streamable_http import streamable_http_client
    from mcp import ClientSession
    from mcp.client.session import ClientSession as Session

    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    async with streamable_http_client(
        mcp_url,
        http_client=httpx.AsyncClient(verify=False, timeout=30, headers=headers),
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


async def _read_mcp_resource(mcp_url: str, uri: str, auth_header: Optional[str] = None) -> Dict[str, Any]:
    from mcp.client.streamable_http import streamable_http_client
    from mcp import ClientSession

    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    async with streamable_http_client(
        mcp_url,
        http_client=httpx.AsyncClient(verify=False, timeout=30, headers=headers),
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


async def _get_mcp_prompt(mcp_url: str, prompt_name: str, arguments: Dict[str, Any], auth_header: Optional[str] = None) -> Dict[str, Any]:
    from mcp.client.streamable_http import streamable_http_client
    from mcp import ClientSession

    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    async with streamable_http_client(
        mcp_url,
        http_client=httpx.AsyncClient(verify=False, timeout=30, headers=headers),
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


_api_keys: Dict[str, Dict[str, Any]] = {}


def _init_api_keys():
    global _api_keys
    token_str = os.getenv("MCP_AUTH_TOKENS", "")
    if token_str.strip():
        tokens = [t.strip() for t in token_str.split(",") if t.strip()]
        for i, token in enumerate(tokens):
            key_id = f"key_{i+1}"
            _api_keys[key_id] = {
                "id": key_id,
                "name": f"默认Key-{i+1}",
                "key": token,
                "is_default": i == 0,
                "created_at": datetime.now().isoformat(),
            }


def _get_default_key() -> Optional[str]:
    for key_data in _api_keys.values():
        if key_data["is_default"]:
            return key_data["key"]
    return None


def _serialize_service(service) -> Dict[str, Any]:
    has_auth = bool(service.headers) or bool(service.auth_type)
    auth_type = service.auth_type or ("Bearer Token" if service.headers and "Authorization" in service.headers else None)
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


def create_manager_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/services", tags=["MCP管理"])
    async def list_services():
        registry = get_registry()
        services = registry.list_services()
        return {
            "total": len(services),
            "services": [_serialize_service(s) for s in services]
        }

    @router.get("/api/services/{service_name}", tags=["MCP管理"])
    async def get_service(service_name: str):
        registry = get_registry()
        service = registry.get(service_name)
        if not service:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        return _serialize_service(service)

    @router.post("/api/services", tags=["MCP管理"])
    async def create_service(req: MCPServiceCreate):
        registry = get_registry()
        if registry.get(req.name):
            raise HTTPException(status_code=400, detail=f"Service {req.name} already exists")

        tools = []
        for t in req.tools:
            tool_dict = dict(t)
            tool_dict.setdefault("method", "POST")
            tool_dict.setdefault("path", "")
            tools.append(MCPToolInfo(**tool_dict))
        resources = [MCPResourceInfo(**r) for r in req.resources]
        prompts = [MCPPromptInfo(**p) for p in req.prompts]

        service = MCPServiceDefinition(
            name=req.name,
            description=req.description,
            base_url=req.base_url,
            instructions=req.instructions,
            transport=req.transport,
            auth_type=req.auth_type,
            headers=req.headers,
            tags=req.tags,
            tools=tools,
            resources=resources,
            prompts=prompts,
        )
        registry.register(service)
        return {"success": True, "service": _serialize_service(service)}

    @router.put("/api/services/{service_name}", tags=["MCP管理"])
    async def update_service(service_name: str, req: MCPServiceUpdate):
        registry = get_registry()
        service = registry.get(service_name)
        if not service:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")

        if req.description is not None:
            service.description = req.description
        if req.base_url is not None:
            service.base_url = req.base_url
        if req.instructions is not None:
            service.instructions = req.instructions
        if req.auth_type is not None:
            service.auth_type = req.auth_type
        if req.headers is not None:
            service.headers = req.headers
        if req.tags is not None:
            service.tags = req.tags

        return {"success": True, "service": _serialize_service(service)}

    @router.delete("/api/services/{service_name}", tags=["MCP管理"])
    async def delete_service(service_name: str):
        registry = get_registry()
        if not registry.unregister(service_name):
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        return {"success": True, "message": f"Service {service_name} deleted"}

    @router.get("/api/services/example/sample", tags=["MCP管理"])
    async def get_service_example():
        return {
            "name": "example-service",
            "description": "示例MCP服务定义",
            "base_url": "https://example.com/mcp",
            "instructions": "这是一个示例服务的系统提示词",
            "transport": "streamable-http",
            "auth_type": "Bearer Token",
            "headers": {},
            "tags": ["示例", "测试"],
            "tools": [
                {
                    "name": "example_tool",
                    "description": "示例工具",
                    "method": "GET",
                    "path": "/api/example",
                    "parameters": [
                        {"name": "param1", "type": "str", "required": True, "description": "参数1", "location": "query"}
                    ],
                    "input_schema": {
                        "type": "object",
                        "properties": {"param1": {"type": "string", "description": "参数1"}},
                        "required": ["param1"]
                    }
                }
            ],
            "resources": [
                {
                    "uri": "example://info",
                    "name": "Example Info",
                    "description": "示例资源",
                    "mime_type": "application/json"
                }
            ],
            "prompts": [
                {
                    "name": "example_prompt",
                    "description": "示例提示词",
                    "arguments": []
                }
            ]
        }

    @router.get("/api/health", tags=["系统"])
    async def health():
        registry = get_registry()
        return {
            "status": "healthy",
            "services_count": len(registry.list_services()),
        }

    @router.post("/api/test/tool", tags=["MCP测试"])
    async def test_tool(req: ToolCallRequest, request: Request):
        mcp_url = _get_mcp_url(req.service_name)
        if not mcp_url:
            raise HTTPException(status_code=404, detail=f"Service {req.service_name} not found")

        auth_header = request.headers.get("authorization")
        if not auth_header and req.key_id:
            key_data = _api_keys.get(req.key_id)
            if key_data:
                auth_header = f"Bearer {key_data['key']}"
        if not auth_header:
            default_key = _get_default_key()
            if default_key:
                auth_header = f"Bearer {default_key}"

        try:
            result = await _call_mcp_tool(mcp_url, req.tool_name, req.arguments, auth_header)
            curl_cmd = _generate_mcp_curl(
                mcp_url, "tools/call",
                {"name": req.tool_name, "arguments": req.arguments},
                auth_header
            )
            return {
                "success": True,
                "tool": req.tool_name,
                "result": result["result"],
                "mcp_url": mcp_url,
                "method": "tools/call",
                "curl_command": curl_cmd,
            }
        except Exception as e:
            curl_cmd = _generate_mcp_curl(
                mcp_url, "tools/call",
                {"name": req.tool_name, "arguments": req.arguments},
                auth_header
            )
            return {
                "success": False,
                "tool": req.tool_name,
                "error": str(e),
                "mcp_url": mcp_url,
                "curl_command": curl_cmd,
            }

    @router.post("/api/test/resource", tags=["MCP测试"])
    async def test_resource(req: ResourceReadRequest, request: Request):
        mcp_url = _get_mcp_url(req.service_name)
        if not mcp_url:
            raise HTTPException(status_code=404, detail=f"Service {req.service_name} not found")

        auth_header = request.headers.get("authorization")
        if not auth_header and req.key_id:
            key_data = _api_keys.get(req.key_id)
            if key_data:
                auth_header = f"Bearer {key_data['key']}"
        if not auth_header:
            default_key = _get_default_key()
            if default_key:
                auth_header = f"Bearer {default_key}"

        try:
            result = await _read_mcp_resource(mcp_url, req.uri, auth_header)
            curl_cmd = _generate_mcp_curl(
                mcp_url, "resources/read",
                {"uri": req.uri},
                auth_header
            )
            return {
                "success": True,
                "uri": req.uri,
                "result": result["result"],
                "mcp_url": mcp_url,
                "method": "resources/read",
                "curl_command": curl_cmd,
            }
        except Exception as e:
            curl_cmd = _generate_mcp_curl(
                mcp_url, "resources/read",
                {"uri": req.uri},
                auth_header
            )
            return {
                "success": False,
                "uri": req.uri,
                "error": str(e),
                "mcp_url": mcp_url,
                "curl_command": curl_cmd,
            }

    @router.post("/api/test/prompt", tags=["MCP测试"])
    async def test_prompt(req: PromptGetRequest, request: Request):
        mcp_url = _get_mcp_url(req.service_name)
        if not mcp_url:
            raise HTTPException(status_code=404, detail=f"Service {req.service_name} not found")

        auth_header = request.headers.get("authorization")
        if not auth_header and req.key_id:
            key_data = _api_keys.get(req.key_id)
            if key_data:
                auth_header = f"Bearer {key_data['key']}"
        if not auth_header:
            default_key = _get_default_key()
            if default_key:
                auth_header = f"Bearer {default_key}"

        try:
            result = await _get_mcp_prompt(mcp_url, req.prompt_name, req.arguments, auth_header)
            curl_cmd = _generate_mcp_curl(
                mcp_url, "prompts/get",
                {"name": req.prompt_name, "arguments": req.arguments},
                auth_header
            )
            return {
                "success": True,
                "prompt": req.prompt_name,
                "result": result["result"],
                "mcp_url": mcp_url,
                "method": "prompts/get",
                "curl_command": curl_cmd,
            }
        except Exception as e:
            curl_cmd = _generate_mcp_curl(
                mcp_url, "prompts/get",
                {"name": req.prompt_name, "arguments": req.arguments},
                auth_header
            )
            return {
                "success": False,
                "prompt": req.prompt_name,
                "error": str(e),
                "mcp_url": mcp_url,
                "curl_command": curl_cmd,
            }

    @router.get("/api/keys", tags=["Key管理"])
    async def list_keys():
        keys = []
        for key_data in _api_keys.values():
            keys.append({
                "id": key_data["id"],
                "name": key_data["name"],
                "key_prefix": key_data["key"][:8] + "..." if len(key_data["key"]) > 8 else key_data["key"],
                "is_default": key_data["is_default"],
                "created_at": key_data["created_at"],
            })
        return {"total": len(keys), "keys": keys}

    @router.post("/api/keys", tags=["Key管理"])
    async def create_key(req: ApiKeyCreate):
        global _api_keys
        key_id = f"key_{uuid.uuid4().hex[:8]}"
        key_value = req.key or f"mcp_{uuid.uuid4().hex}"

        if req.is_default:
            for k in _api_keys.values():
                k["is_default"] = False

        _api_keys[key_id] = {
            "id": key_id,
            "name": req.name,
            "key": key_value,
            "is_default": req.is_default,
            "created_at": datetime.now().isoformat(),
        }

        return {
            "success": True,
            "key": {
                "id": key_id,
                "name": req.name,
                "key": key_value,
                "is_default": req.is_default,
                "created_at": _api_keys[key_id]["created_at"],
            }
        }

    @router.put("/api/keys/{key_id}", tags=["Key管理"])
    async def update_key(key_id: str, req: ApiKeyUpdate):
        if key_id not in _api_keys:
            raise HTTPException(status_code=404, detail="Key not found")

        key_data = _api_keys[key_id]

        if req.name is not None:
            key_data["name"] = req.name

        if req.is_default is not None and req.is_default:
            for k in _api_keys.values():
                k["is_default"] = False
            key_data["is_default"] = True
        elif req.is_default is not None and not req.is_default:
            key_data["is_default"] = False

        return {
            "success": True,
            "key": {
                "id": key_id,
                "name": key_data["name"],
                "key_prefix": key_data["key"][:8] + "...",
                "is_default": key_data["is_default"],
                "created_at": key_data["created_at"],
            }
        }

    @router.delete("/api/keys/{key_id}", tags=["Key管理"])
    async def delete_key(key_id: str):
        if key_id not in _api_keys:
            raise HTTPException(status_code=404, detail="Key not found")
        del _api_keys[key_id]
        return {"success": True, "message": "Key deleted"}

    @router.get("/api/config", tags=["配置"])
    async def get_config():
        default_key = _get_default_key()
        return {
            "platform_url": config.platform_url,
            "platform_host": config.PLATFORM_HOST,
            "platform_port": config.PLATFORM_PORT,
            "platform_scheme": config.PLATFORM_SCHEME,
            "todo_mcp_url": config.todo_mcp_url,
            "calc_mcp_url": config.calc_mcp_url,
            "default_key_prefix": default_key[:8] + "..." if default_key else None,
        }

    return router


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

    router = create_manager_router()
    app.include_router(router)

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

    auth_enabled = bool(os.getenv("MCP_AUTH_TOKENS", "").strip())
    auth_type = "Bearer Token" if auth_enabled else None

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
        auth_type=auth_type,
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
        auth_type=auth_type,
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
