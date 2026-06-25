from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="api-to-mcp",
    help="将REST API服务转化为MCP (Model Context Protocol) 服务的工具",
)

CERT_DIR = Path(__file__).parent.parent.parent / "certs"
DEFAULT_CERT = CERT_DIR / "localhost.crt"
DEFAULT_KEY = CERT_DIR / "localhost.key"


def _get_ssl_options(use_https: bool):
    if not use_https:
        return {}
    if DEFAULT_CERT.exists() and DEFAULT_KEY.exists():
        return {
            "ssl_certfile": str(DEFAULT_CERT),
            "ssl_keyfile": str(DEFAULT_KEY),
        }
    typer.echo(f"⚠️  未找到SSL证书，将使用HTTP模式", err=True)
    typer.echo(f"   证书路径: {DEFAULT_CERT}")
    typer.echo(f"   运行: python -m api_to_mcp.cli gencerts 生成证书", err=True)
    return {}


def _scheme(use_https: bool) -> str:
    return "https" if use_https else "http"


@app.command()
def gencerts(
    output_dir: Path = typer.Option(CERT_DIR, help="证书输出目录"),
    domain: str = typer.Option("localhost", help="证书域名"),
    days: int = typer.Option(365, help="证书有效期（天）"),
):
    """生成自签名SSL证书"""
    import subprocess

    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "localhost.crt"
    key_path = output_dir / "localhost.key"

    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", str(key_path),
        "-out", str(cert_path),
        "-days", str(days),
        "-nodes",
        "-subj", f"/CN={domain}/O=MCP Dev/C=CN",
        "-addext", f"subjectAltName=DNS:{domain},DNS:*.{domain},IP:127.0.0.1",
    ]

    typer.echo(f"🔐 生成自签名SSL证书...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        typer.echo(f"❌ 生成失败: {result.stderr}", err=True)
        raise typer.Exit(1)

    typer.echo(f"✅ 证书生成成功!")
    typer.echo(f"   证书文件: {cert_path}")
    typer.echo(f"   私钥文件: {key_path}")
    typer.echo()
    typer.echo(f"💡 提示: 浏览器访问时会提示不安全，这是正常的（自签名证书）")
    typer.echo(f"   macOS信任证书: sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain {cert_path}")


@app.command()
def serve_api(
    host: str = typer.Option("127.0.0.1", help="API服务监听地址"),
    port: int = typer.Option(8000, help="API服务端口"),
    https: bool = typer.Option(False, "--https", help="启用HTTPS"),
):
    """启动示例TODO REST API服务"""
    import uvicorn

    scheme = _scheme(https)
    ssl_opts = _get_ssl_options(https)

    typer.echo(f"🚀 启动TODO API服务: {scheme}://{host}:{port}")
    typer.echo(f"📖 API文档: {scheme}://{host}:{port}/docs")
    if ssl_opts:
        typer.echo(f"🔐 HTTPS已启用 (自签名证书)")
    uvicorn.run(
        "api_to_mcp.examples.todo_api:app",
        host=host,
        port=port,
        reload=True,
        **ssl_opts,
    )


@app.command()
def serve_mcp(
    api_url: str = typer.Option(
        "http://127.0.0.1:8000", help="后端API服务地址"
    ),
    transport: str = typer.Option(
        "stdio", help="传输协议: stdio / sse / streamable-http"
    ),
    port: int = typer.Option(8001, help="SSE/HTTP模式下的端口"),
    https: bool = typer.Option(False, "--https", help="启用HTTPS"),
    verify_ssl: bool = typer.Option(False, "--verify-ssl/--no-verify-ssl", help="验证API的SSL证书（自签名证书时用--no-verify-ssl）"),
):
    """启动TODO MCP服务"""
    import uvicorn

    from api_to_mcp.examples.todo_mcp import create_todo_mcp_server

    scheme = _scheme(https)
    ssl_opts = _get_ssl_options(https)

    typer.echo(f"🔌 启动TODO MCP服务，连接API: {api_url}")
    typer.echo(f"📡 传输模式: {transport}")

    if not verify_ssl and api_url.startswith("https"):
        import os
        os.environ["SSL_CERT_FILE"] = ""

    mcp_server, builder = create_todo_mcp_server(base_url=api_url, verify_ssl=verify_ssl)

    if transport == "stdio":
        mcp_server.run(transport="stdio")
    elif transport == "sse":
        typer.echo(f"🌐 SSE服务地址: {scheme}://127.0.0.1:{port}/sse")
        if ssl_opts:
            typer.echo(f"🔐 HTTPS已启用 (自签名证书)")
        sse_app = mcp_server.sse_app()
        uvicorn.run(sse_app, host="127.0.0.1", port=port, log_level="info", **ssl_opts)
    elif transport == "streamable-http":
        typer.echo(f"🌐 Streamable HTTP服务地址: {scheme}://127.0.0.1:{port}/mcp")
        if ssl_opts:
            typer.echo(f"🔐 HTTPS已启用 (自签名证书)")
        http_app = mcp_server.streamable_http_app()
        uvicorn.run(http_app, host="127.0.0.1", port=port, log_level="info", **ssl_opts)
    else:
        typer.echo(f"❌ 不支持的传输模式: {transport}", err=True)
        raise typer.Exit(1)


@app.command()
def inspect():
    """使用MCP检查器测试MCP服务"""
    import subprocess
    import sys

    typer.echo("🔍 启动MCP Inspector...")
    typer.echo("请确保API服务已在 8000 端口启动")
    subprocess.run(
        [sys.executable, "-m", "mcp", "dev", "src/api_to_mcp/examples/todo_mcp.py"],
        check=True,
    )


@app.command()
def serve_ui(
    host: str = typer.Option("127.0.0.1", help="管理后台监听地址"),
    port: int = typer.Option(8080, help="管理后台端口"),
    https: bool = typer.Option(False, "--https", help="启用HTTPS"),
):
    """启动MCP服务管理后台（Web UI）"""
    import uvicorn

    from api_to_mcp.manager import create_manager_app, register_example_services

    scheme = _scheme(https)
    ssl_opts = _get_ssl_options(https)

    typer.echo(f"🎛️  启动MCP服务管理后台: {scheme}://{host}:{port}")
    typer.echo(f"📊 API服务列表: {scheme}://{host}:{port}/api/services")
    if ssl_opts:
        typer.echo(f"🔐 HTTPS已启用 (自签名证书)")
    typer.echo()

    register_example_services()
    app = create_manager_app()
    uvicorn.run(app, host=host, port=port, **ssl_opts)


@app.command()
def info():
    """显示项目信息和使用指南"""
    info_text = """
╔══════════════════════════════════════════════════════════════╗
║           API → MCP 转化框架                                  ║
╚══════════════════════════════════════════════════════════════╝

📋 快速开始:

1. 生成SSL证书（启用HTTPS时需要）:
   $ api-to-mcp gencerts

2. 启动API服务（终端1）:
   $ api-to-mcp serve-api --https
   或者: uv run todo-api

3. 启动MCP服务（终端2）:
   $ api-to-mcp serve-mcp --transport sse --https --port 8001
   或者: uv run todo-mcp

4. 启动管理后台UI（终端3）:
   $ api-to-mcp serve-ui --https
   访问: https://127.0.0.1:8080

5. 使用MCP Inspector测试:
   $ api-to-mcp inspect

🔧 将你自己的API转化为MCP:

参考 src/api_to_mcp/examples/todo_mcp.py 中的模式:
1. 定义APIEndpoint列表，描述每个API端点
2. 使用create_mcp_server_from_api()创建MCP服务器
3. 添加自定义资源(resources)和提示词(prompts)
4. 使用build_service_metadata()注册到管理后台

📁 项目结构:
src/api_to_mcp/
├── core.py              # 核心转化框架
├── registry.py          # MCP服务注册中心
├── manager.py           # 管理后台API和Web服务器
├── cli.py               # 命令行入口
├── static/
│   └── index.html       # 管理后台前端页面
└── examples/
    ├── todo_models.py   # 数据模型
    ├── todo_api.py      # 示例REST API
    └── todo_mcp.py      # 示例MCP服务

certs/                   # SSL证书目录
├── localhost.crt        # 自签名证书
└── localhost.key        # 私钥
    """
    typer.echo(info_text)


if __name__ == "__main__":
    app()
