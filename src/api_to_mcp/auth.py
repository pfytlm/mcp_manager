"""
认证模块
提供 Bearer Token 认证功能
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class TokenAuth(HTTPBearer):
    """Bearer Token 认证类"""

    def __init__(self, tokens: list[str], auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.tokens = set(tokens)

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials:
            if credentials.scheme.lower() == "bearer" and credentials.credentials in self.tokens:
                return credentials
            raise HTTPException(status_code=401, detail="无效的认证 token")
        return None


def get_valid_tokens() -> list[str]:
    """获取有效的认证 token 列表"""
    token_str = os.getenv("MCP_AUTH_TOKENS", "")
    if not token_str:
        return []
    return [t.strip() for t in token_str.split(",") if t.strip()]


def create_auth_middleware():
    """创建认证中间件"""
    tokens = get_valid_tokens()
    if not tokens:
        return None
    return TokenAuth(tokens=tokens)
