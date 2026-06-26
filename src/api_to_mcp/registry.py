from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel


@dataclass
class MCPToolInfo:
    name: str
    description: str
    method: str
    path: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResourceInfo:
    uri: str
    name: str
    description: str = ""
    mime_type: str = "application/json"


@dataclass
class MCPPromptInfo:
    name: str
    description: str = ""
    arguments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MCPServiceDefinition:
    name: str
    description: str
    base_url: str
    instructions: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"
    tools: List[MCPToolInfo] = field(default_factory=list)
    resources: List[MCPResourceInfo] = field(default_factory=list)
    prompts: List[MCPPromptInfo] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    auth_type: Optional[str] = None


class MCPServiceRegistry:
    def __init__(self):
        self._services: Dict[str, MCPServiceDefinition] = {}

    def register(self, service: MCPServiceDefinition) -> None:
        self._services[service.name] = service

    def get(self, name: str) -> Optional[MCPServiceDefinition]:
        return self._services.get(name)

    def list_services(self) -> List[MCPServiceDefinition]:
        return list(self._services.values())

    def unregister(self, name: str) -> bool:
        if name in self._services:
            del self._services[name]
            return True
        return False

    def clear(self) -> None:
        self._services.clear()


_registry = MCPServiceRegistry()


def get_registry() -> MCPServiceRegistry:
    return _registry
