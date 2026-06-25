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

    TODO_MCP_PATH: str = os.getenv("TODO_MCP_PATH", "/mcp/todo")
    CALC_MCP_PATH: str = os.getenv("CALC_MCP_PATH", "/mcp/calc")

    SSL_CERT_PATH: str = os.getenv("SSL_CERT_PATH", "certs/localhost.crt")
    SSL_KEY_PATH: str = os.getenv("SSL_KEY_PATH", "certs/localhost.key")

    @property
    def platform_url(self) -> str:
        port = self.PLATFORM_PORT
        if (self.PLATFORM_SCHEME == "https" and port == 443) or \
           (self.PLATFORM_SCHEME == "http" and port == 80):
            return f"{self.PLATFORM_SCHEME}://{self.PLATFORM_HOST}"
        return f"{self.PLATFORM_SCHEME}://{self.PLATFORM_HOST}:{self.PLATFORM_PORT}"

    @property
    def todo_api_url(self) -> str:
        return f"{self.platform_url}/api/todo"

    @property
    def calc_api_url(self) -> str:
        return f"{self.platform_url}/api/calc"

    @property
    def todo_mcp_url(self) -> str:
        path = self.TODO_MCP_PATH.rstrip("/")
        return f"{self.platform_url}{path}"

    @property
    def calc_mcp_url(self) -> str:
        path = self.CALC_MCP_PATH.rstrip("/")
        return f"{self.platform_url}{path}"

    def get_ssl_context(self):
        if not self.ENABLE_HTTPS:
            return None
        return {
            "ssl_keyfile": self.SSL_KEY_PATH,
            "ssl_certfile": self.SSL_CERT_PATH,
        }


config = PlatformConfig()
