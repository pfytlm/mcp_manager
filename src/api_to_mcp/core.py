from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class ParameterLocation(str, Enum):
    QUERY = "query"
    PATH = "path"
    BODY = "body"
    HEADER = "header"


@dataclass
class APIParameter:
    name: str
    location: ParameterLocation
    type: Type = str
    required: bool = True
    description: str = ""
    default: Any = None


@dataclass
class APIEndpoint:
    name: str
    path: str
    method: HTTPMethod
    description: str = ""
    parameters: List[APIParameter] = field(default_factory=list)
    request_model: Optional[Type[BaseModel]] = None
    response_model: Optional[Type[BaseModel]] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class APIToolDefinition:
    name: str
    description: str
    endpoint: APIEndpoint
    parameter_descriptions: Dict[str, str] = field(default_factory=dict)


class MCPToolBuilder:
    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.verify_ssl = verify_ssl
        self.endpoints: Dict[str, APIEndpoint] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=30.0,
                verify=self.verify_ssl,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def register_endpoint(self, endpoint: APIEndpoint) -> None:
        self.endpoints[endpoint.name] = endpoint

    def build_url(self, path: str, path_params: Dict[str, Any]) -> str:
        url = path
        for key, value in path_params.items():
            url = url.replace(f"{{{key}}}", str(value))
        return url

    def _get_all_param_info(self, endpoint: APIEndpoint) -> Dict[str, Dict[str, Any]]:
        param_info: Dict[str, Dict[str, Any]] = {}

        for param in endpoint.parameters:
            param_info[param.name] = {
                "type": param.type,
                "required": param.required,
                "description": param.description or param.name,
                "default": param.default,
            }

        if endpoint.request_model:
            for name, field in endpoint.request_model.model_fields.items():
                if name not in param_info:
                    annotation = field.annotation
                    if annotation is None:
                        annotation = str
                    is_required = field.is_required()
                    param_info[name] = {
                        "type": annotation,
                        "required": is_required,
                        "description": field.description or name,
                        "default": field.default if not is_required else None,
                    }

        return param_info

    async def call_endpoint(
        self,
        endpoint_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        endpoint = self.endpoints.get(endpoint_name)
        if not endpoint:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")

        client = await self._get_client()

        path_params = {}
        query_params = {}
        body = None
        headers = {**self.headers}

        for param in endpoint.parameters:
            value = params.get(param.name, param.default)
            if param.required and value is None:
                raise ValueError(f"Missing required parameter: {param.name}")
            if value is None:
                continue

            if param.location == ParameterLocation.PATH:
                path_params[param.name] = value
            elif param.location == ParameterLocation.QUERY:
                query_params[param.name] = value
            elif param.location == ParameterLocation.BODY:
                if body is None:
                    body = {}
                body[param.name] = value
            elif param.location == ParameterLocation.HEADER:
                headers[param.name] = value

        remaining_body_params = {
            k: v for k, v in params.items()
            if k not in path_params
            and k not in query_params
            and k not in {p.name for p in endpoint.parameters}
        }

        if endpoint.request_model and remaining_body_params:
            model_instance = endpoint.request_model(**remaining_body_params)
            body = model_instance.model_dump(exclude_none=True)
        elif remaining_body_params:
            if body is None:
                body = {}
            body.update(remaining_body_params)

        url = self.build_url(endpoint.path, path_params)

        response = await client.request(
            method=endpoint.method.value,
            url=url,
            params=query_params if query_params else None,
            json=body,
            headers=headers,
        )

        response.raise_for_status()

        if response.status_code == 204:
            return {"success": True}

        try:
            return response.json()
        except json.JSONDecodeError:
            return {"text": response.text, "success": True}


def _create_tool_function(
    endpoint_name: str,
    endpoint_desc: str,
    param_info: Dict[str, Dict[str, Any]],
    builder: MCPToolBuilder,
):
    import inspect

    if not param_info:
        async def tool_fn():
            try:
                result = await builder.call_endpoint(endpoint_name, {})
                return json.dumps(result, ensure_ascii=False, indent=2)
            except httpx.HTTPStatusError as e:
                error_msg = f"API调用失败: HTTP {e.response.status_code}"
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {json.dumps(error_detail, ensure_ascii=False)}"
                except Exception:
                    error_msg += f" - {e.response.text[:500]}"
                return json.dumps({"error": error_msg}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": str(e)}, ensure_ascii=False)
    else:
        async def tool_fn(**kwargs):
            try:
                result = await builder.call_endpoint(endpoint_name, kwargs)
                return json.dumps(result, ensure_ascii=False, indent=2)
            except httpx.HTTPStatusError as e:
                error_msg = f"API调用失败: HTTP {e.response.status_code}"
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {json.dumps(error_detail, ensure_ascii=False)}"
                except Exception:
                    error_msg += f" - {e.response.text[:500]}"
                return json.dumps({"error": error_msg}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": str(e)}, ensure_ascii=False)

        sig_params = []
        annotations = {}
        defaults = {}
        for pname, pinfo in param_info.items():
            ptype = pinfo["type"]
            description = pinfo["description"]
            if pinfo["required"]:
                default_val = Field(description=description)
                param = inspect.Parameter(
                    pname,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=default_val,
                    annotation=ptype,
                )
            else:
                default_val = Field(
                    default=pinfo["default"] if pinfo["default"] is not None else None,
                    description=description,
                )
                param = inspect.Parameter(
                    pname,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=default_val,
                    annotation=Optional[ptype],
                )
            sig_params.append(param)
            annotations[pname] = ptype if pinfo["required"] else Optional[ptype]

        tool_fn.__signature__ = inspect.Signature(sig_params)
        tool_fn.__annotations__ = annotations

    tool_fn.__name__ = endpoint_name
    tool_fn.__doc__ = endpoint_desc
    return tool_fn


def create_mcp_server_from_api(
    server_name: str,
    base_url: str,
    endpoints: List[APIEndpoint],
    headers: Optional[Dict[str, str]] = None,
    instructions: Optional[str] = None,
    verify_ssl: bool = True,
) -> tuple[FastMCP, MCPToolBuilder]:
    mcp = FastMCP(server_name, instructions=instructions)
    builder = MCPToolBuilder(base_url=base_url, headers=headers, verify_ssl=verify_ssl)

    for endpoint in endpoints:
        builder.register_endpoint(endpoint)
        param_info = builder._get_all_param_info(endpoint)
        tool_fn = _create_tool_function(
            endpoint.name,
            endpoint.description or f"Call {endpoint.method.value} {endpoint.path}",
            param_info,
            builder,
        )
        mcp.tool()(tool_fn)

    @mcp.resource("api://endpoints")
    def get_endpoints() -> str:
        endpoint_info = []
        for name, ep in builder.endpoints.items():
            param_infos = []
            param_info = builder._get_all_param_info(ep)
            for pname, pinfo in param_info.items():
                param_infos.append({
                    "name": pname,
                    "type": getattr(pinfo["type"], "__name__", str(pinfo["type"])),
                    "required": pinfo["required"],
                    "description": pinfo["description"],
                })
            info = {
                "name": name,
                "method": ep.method.value,
                "path": ep.path,
                "description": ep.description,
                "parameters": param_infos,
            }
            endpoint_info.append(info)
        return json.dumps(endpoint_info, ensure_ascii=False, indent=2)

    return mcp, builder


def build_service_metadata(
    server_name: str,
    base_url: str,
    endpoints: List[APIEndpoint],
    headers: Optional[Dict[str, str]] = None,
    instructions: Optional[str] = None,
    description: str = "",
    extra_resources: Optional[List[Dict[str, Any]]] = None,
    extra_prompts: Optional[List[Dict[str, Any]]] = None,
    extra_tools: Optional[List[Dict[str, Any]]] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    from .registry import MCPToolInfo, MCPResourceInfo, MCPPromptInfo, MCPServiceDefinition

    builder = MCPToolBuilder(base_url=base_url, headers=headers)
    tools = []

    for endpoint in endpoints:
        builder.register_endpoint(endpoint)
        param_info = builder._get_all_param_info(endpoint)

        param_locations = {}
        for p in endpoint.parameters:
            param_locations[p.name] = p.location.value

        param_list = []
        schema_props = {}
        required_params = []

        for pname, pinfo in param_info.items():
            ptype = pinfo["type"]
            type_name = getattr(ptype, "__name__", str(ptype)).lower()
            location = param_locations.get(pname, "body")
            param_list.append({
                "name": pname,
                "type": type_name,
                "required": pinfo["required"],
                "description": pinfo["description"],
                "location": location,
            })
            schema_props[pname] = {
                "type": type_name if type_name not in ("list", "dict") else "object",
                "description": pinfo["description"],
            }
            if pinfo["required"]:
                required_params.append(pname)

        tools.append(MCPToolInfo(
            name=endpoint.name,
            description=endpoint.description or f"Call {endpoint.method.value} {endpoint.path}",
            method=endpoint.method.value,
            path=endpoint.path,
            parameters=param_list,
            input_schema={
                "type": "object",
                "properties": schema_props,
                "required": required_params,
            },
        ))

    if extra_tools:
        for t in extra_tools:
            tools.append(MCPToolInfo(**t))

    resources = [
        MCPResourceInfo(
            uri="api://endpoints",
            name="API Endpoints",
            description="所有已注册API端点的完整列表",
        )
    ]
    if extra_resources:
        for r in extra_resources:
            resources.append(MCPResourceInfo(**r))

    prompts = []
    if extra_prompts:
        for p in extra_prompts:
            prompts.append(MCPPromptInfo(**p))

    return {
        "name": server_name,
        "description": description,
        "base_url": base_url,
        "instructions": instructions,
        "has_auth": bool(headers),
        "auth_type": "Bearer Token" if headers and "Authorization" in headers else None,
        "tools": tools,
        "resources": resources,
        "prompts": prompts,
        "tags": tags or [],
    }

