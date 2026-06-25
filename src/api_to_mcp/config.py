"""
平台配置模块
支持通过环境变量或.env文件配置平台参数
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class PlatformConfig:
    PLATFORM_HOST: str = os.getenv("PLATFORM_HOST", "127.0.0.1")
    PLATFORM_PORT: int = int(os.getenv("PLATFORM_PORT", "8080"))
    PLATFORM_SCHEME: str = os.getenv("PLATFORM_SCHEME", "http")
    ENABLE_HTTPS: bool = os.getenv("ENABLE_HTTPS", "false").lower() == "true"

    TODO_API_HOST: str = os.getenv("TODO_API_HOST", "127.0.0.1")
    TODO_API_PORT: int = int(os.getenv("TODO_API_PORT", "8000"))
    TODO_API_SCHEME: str = os.getenv("TODO_API_SCHEME", "http")

    CALC_API_HOST: str = os.getenv("CALC_API_HOST", "127.0.0.1")
    CALC_API_PORT: int = int(os.getenv("CALC_API_PORT", "8002"))
    CALC_API_SCHEME: str = os.getenv("CALC_API_SCHEME", "http")

    TODO_MCP_HOST: str = os.getenv("TODO_MCP_HOST", "127.0.0.1")
    TODO_MCP_PORT: int = int(os.getenv("TODO_MCP_PORT", "8001"))
    TODO_MCP_SCHEME: str = os.getenv("TODO_MCP_SCHEME", "http")

    CALC_MCP_HOST: str = os.getenv("CALC_MCP_HOST", "127.0.0.1")
    CALC_MCP_PORT: int = int(os.getenv("CALC_MCP_PORT", "8003"))
    CALC_MCP_SCHEME: str = os.getenv("CALC_MCP_SCHEME", "http")

    SSL_CERT_PATH: str = os.getenv("SSL_CERT_PATH", "certs/localhost.crt")
    SSL_KEY_PATH: str = os.getenv("SSL_KEY_PATH", "certs/localhost.key")

    @property
    def platform_url(self) -> str:
        return f"{self.PLATFORM_SCHEME}://{self.PLATFORM_HOST}:{self.PLATFORM_PORT}"

    @property
    def todo_api_url(self) -> str:
        return f"{self.TODO_API_SCHEME}://{self.TODO_API_HOST}:{self.TODO_API_PORT}"

    @property
    def calc_api_url(self) -> str:
        return f"{self.CALC_API_SCHEME}://{self.CALC_API_HOST}:{self.CALC_API_PORT}"

    @property
    def todo_mcp_url(self) -> str:
        return f"{self.TODO_MCP_SCHEME}://{self.TODO_MCP_HOST}:{self.TODO_MCP_PORT}/mcp"

    @property
    def calc_mcp_url(self) -> str:
        return f"{self.CALC_MCP_SCHEME}://{self.CALC_MCP_HOST}:{self.CALC_MCP_PORT}/mcp"

    def get_ssl_context(self):
        if not self.ENABLE_HTTPS:
            return None
        return {
            "ssl_keyfile": self.SSL_KEY_PATH,
            "ssl_certfile": self.SSL_CERT_PATH,
        }


config = PlatformConfig()
