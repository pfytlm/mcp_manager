# MCP Manager

一个完整的 **Model Context Protocol (MCP)** 服务管理框架，提供 REST API 转 MCP 服务的转换能力、MCP 服务注册中心、管理后台 UI 和 MCP 协议测试工具。

## ✨ 功能特性

- **API → MCP 转换框架**: 将现有的 REST API 服务自动转换为 MCP 服务
- **MCP 服务注册中心**: 集中管理多个 MCP 服务，支持服务发现
- **管理后台 UI**: 可视化查看和管理所有 MCP 服务配置
- **MCP 协议测试**: 通过 streamable-HTTP 协议测试 MCP 的 Tools/Resources/Prompts
- **组合工具支持**: 支持一个 Tool 内部调用多个 API 的组合模式
- **HTTPS 支持**: 完整的 SSL/TLS 支持，可配置证书路径

## 🚀 快速开始

### 环境要求

- Python >= 3.10
- uv (推荐的 Python 包管理器)

### 安装

```bash
# 克隆仓库
git clone https://github.com/pfytlm/mcp_manager.git
cd mcp_manager

# 使用 uv 安装依赖
uv install
```

### 配置

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

配置项说明：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| PLATFORM_HOST | 管理后台主机 | localhost |
| PLATFORM_PORT | 管理后台端口 | 8080 |
| PLATFORM_SCHEME | 协议 (http/https) | http |
| ENABLE_HTTPS | 是否启用 HTTPS | false |
| TODO_API_HOST/PORT | TODO API 服务配置 | 127.0.0.1:8000 |
| CALC_API_HOST/PORT | 计算器 API 服务配置 | 127.0.0.1:8002 |
| TODO_MCP_HOST/PORT | TODO MCP 服务配置 | localhost:8001 |
| CALC_MCP_HOST/PORT | 计算器 MCP 服务配置 | localhost:8003 |
| SSL_CERT_PATH | SSL 证书路径 | certs/server.crt |
| SSL_KEY_PATH | SSL 私钥路径 | certs/server.key |

### 启动服务

```bash
# 启动所有服务（推荐）
./start.sh

# HTTP 模式启动
HTTP_MODE=true ./start.sh

# 或分别启动
uv run api-to-mcp serve-api          # REST API 服务 (8000)
uv run api-to-mcp serve-mcp          # MCP SSE 服务 (8001)
uv run api-to-mcp serve-ui           # 管理后台 (8080)
uv run api-to-mcp calc-api           # 计算器 API (8002)
uv run api-to-mcp calc-mcp           # 计算器 MCP (8003)
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 管理后台 | http://localhost:8080 |
| TODO API | http://localhost:8000 |
| TODO MCP | http://localhost:8001/mcp |
| 计算器 API | http://localhost:8002 |
| 计算器 MCP | http://localhost:8003/mcp |

## 🏗️ 项目结构

```
src/api_to_mcp/
├── __init__.py
├── cli.py              # 命令行入口
├── config.py           # 配置管理
├── core.py             # API → MCP 转换核心
├── registry.py         # MCP 服务注册中心
├── manager.py          # 管理后台 FastAPI 应用
├── sse_server.py       # MCP SSE 服务器
├── examples/           # 示例服务
│   ├── todo_api.py     # TODO REST API
│   ├── todo_mcp.py     # TODO MCP 服务
│   ├── todo_models.py  # TODO 数据模型
│   ├── calc_api.py     # 计算器 REST API
│   └── calc_mcp.py     # 计算器 MCP 服务
└── static/
    └── index.html      # 管理后台前端页面
```

## 🏗️ 架构设计

### 模块调用关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          启动入口层 (cli.py)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │ serve_api()     │  │ serve_mcp()     │  │ serve_ui()      │           │
│  │ todo_api.py     │  │ todo_mcp.py     │  │ manager.py      │           │
│  │ calc_api.py     │  │ calc_mcp.py     │  │                 │           │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘           │
└───────────┼────────────────────┼────────────────────┼─────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           核心框架层 (core.py)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  create_mcp_server_from_api()                                        │   │
│  │  ├── FastMCP(server_name, instructions)                              │   │
│  │  ├── MCPToolBuilder(base_url, headers, verify_ssl)                   │   │
│  │  │   └── httpx.AsyncClient → REST API                                │   │
│  │  └── mcp.tool() → 动态注册工具函数                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  build_service_metadata() → 返回服务元数据字典                         │   │
│  │  └── 调用 registry.py 数据结构                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          元数据层 (registry.py)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌───────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │ MCPToolInfo │ │MCPResourceInfo│ │ MCPPromptInfo│ │MCPServiceDefinition │ │
│  └──────┬──────┘ └───────┬───────┘ └──────┬───────┘ └──────────┬──────────┘ │
│         │                │                │                   │            │
│         └────────────────┼────────────────┘                   │            │
│                          ▼                                    │            │
│              ┌─────────────────────┐                          │            │
│              │ MCPServiceRegistry  │◄─────────────────────────┘            │
│              │ - register()        │                                       │
│              │ - get()             │                                       │
│              │ - list_services()   │                                       │
│              └─────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           配置层 (config.py)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PlatformConfig (dataclass)                                        │   │
│  │  ├── PLATFORM_HOST / PORT / SCHEME                                 │   │
│  │  ├── TODO_API_HOST / PORT / SCHEME                                 │   │
│  │  ├── CALC_API_HOST / PORT / SCHEME                                 │   │
│  │  ├── TODO_MCP_HOST / PORT / SCHEME                                 │   │
│  │  ├── CALC_MCP_HOST / PORT / SCHEME                                 │   │
│  │  └── SSL_CERT_PATH / SSL_KEY_PATH                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  config = PlatformConfig()  # 全局单例                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    服务启动层 (sse_server.py / manager.py)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────┐      ┌──────────────────────────────┐    │
│  │        sse_server.py         │      │        manager.py            │    │
│  │  ┌────────────────────────┐  │      │  ┌────────────────────────┐  │    │
│  │  │ create_mcp_server()    │  │      │  │ create_manager_app()    │  │    │
│  │  │ └── todo_mcp.py        │  │      │  │ └── FastAPI             │  │    │
│  │  │ └── calc_mcp.py        │  │      │  │ └── /api/services       │  │    │
│  │  ├────────────────────────┤  │      │  │ └── /api/test/tool      │  │    │
│  │  │ create_mcp_sse_app()   │  │      │  │ └── /api/test/resource  │  │    │
│  │  │ create_mcp_http_app()  │  │      │  │ └── /api/test/prompt    │  │    │
│  │  └────────────────────────┘  │      │  ├────────────────────────┤  │    │
│  │  返回 FastAPI 应用给 uvicorn │      │  │ register_example_       │  │    │
│  │                              │      │  │ services()              │  │    │
│  └──────────────────────────────┘      │  │ └── todo_mcp.py         │  │    │
│                                        │  │ └── calc_mcp.py         │  │    │
│                                        │  └────────────────────────┘  │    │
│                                        └──────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 模块职责和调用关系表

| 模块 | 职责 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| **cli.py** | 命令行入口，启动各服务 | 用户终端 | `todo_api`, `todo_mcp`, `manager`, `uvicorn` |
| **config.py** | 全局配置管理 (.env 加载) | `manager`, `sse_server`, `todo_mcp`, `calc_mcp` | `dotenv` |
| **core.py** | API→MCP 转换核心框架 | `todo_mcp`, `calc_mcp` | `FastMCP`, `httpx`, `registry` |
| **registry.py** | MCP 服务注册中心，数据结构定义 | `core`, `manager` | 无（纯数据层） |
| **manager.py** | 管理后台 FastAPI 应用 | `cli`, `uvicorn` | `registry`, `config`, `mcp.client` |
| **sse_server.py** | MCP HTTP/SSE 服务启动 | `uvicorn`（工厂模式） | `todo_mcp`, `calc_mcp`, `config` |

### 核心调用流程

#### 流程 1：创建 MCP 服务

```
cli.serve_mcp()
    │
    ▼
todo_mcp.create_todo_mcp_server()
    │
    ▼
core.create_mcp_server_from_api()
    │
    ├── FastMCP(server_name, instructions)    ← 创建 MCP 服务器
    ├── MCPToolBuilder(base_url, verify_ssl)  ← 创建 API 调用器
    │       │
    │       ▼
    │   httpx.AsyncClient → REST API
    │
    └── mcp.tool()(tool_fn)                   ← 动态注册工具
```

#### 流程 2：管理后台获取服务列表

```
manager.create_manager_app()
    │
    ▼
manager.register_example_services()
    │
    ├── todo_mcp.get_todo_service_metadata()
    │       │
    │       ▼
    │   core.build_service_metadata()
    │       │
    │       ▼
    │   registry.MCPToolInfo / MCPResourceInfo / MCPPromptInfo
    │
    └── registry.register(service)            ← 注册到全局注册中心

    │
    ▼
manager.list_services()
    │
    ▼
registry.get_registry().list_services()       ← 返回所有已注册服务
```

#### 流程 3：测试 MCP 工具调用

```
前端 → manager /api/test/tool
    │
    ▼
manager._call_mcp_tool(mcp_url, tool_name, arguments)
    │
    ▼
mcp.client.streamable_http.streamable_http_client()
    │
    ▼
mcp.ClientSession
    │
    ├── session.initialize()                  ← 获取 sessionId
    └── session.call_tool(tool_name, args)    ← 调用 MCP 工具
            │
            ▼
        MCP Server (8001/8003)
            │
            ▼
        core.MCPToolBuilder.call_endpoint()
            │
            ▼
        REST API (8000/8002)
```

### 架构设计要点

1. **协议层与业务层分离**：`core.py` 只负责 API→MCP 的转换逻辑，不关心具体业务
2. **元数据驱动**：通过 `registry.py` 的数据结构，实现 UI 自动渲染和服务发现
3. **配置集中管理**：`config.py` 提供全局配置单例，所有模块共享同一配置
4. **工厂模式**：`sse_server.py` 提供工厂函数，支持 uvicorn 的 `--factory` 参数启动
5. **服务注册模式**：`registry.py` 使用单例模式，管理后台和 MCP 服务共享服务定义

## 🔧 CLI 命令

```bash
# 生成自签名证书
uv run api-to-mcp gencerts

# 启动 REST API 服务
uv run api-to-mcp serve-api [--https] [--host HOST] [--port PORT]

# 启动 MCP SSE 服务
uv run api-to-mcp serve-mcp [--https] [--host HOST] [--port PORT]

# 启动管理后台
uv run api-to-mcp serve-ui [--https] [--host HOST] [--port PORT]

# 启动计算器 API
uv run api-to-mcp calc-api [--https]

# 启动计算器 MCP
uv run api-to-mcp calc-mcp [--https]
```

## 📡 MCP 协议测试

管理后台提供 MCP 协议测试功能，支持测试：

1. **Tools** - 调用 MCP 工具
2. **Resources** - 读取 MCP 资源
3. **Prompts** - 获取 MCP 提示词

测试结果会显示：
- 响应数据
- 完整的 CURL 命令（可复制）

## 🔐 HTTPS 配置

### 使用自签名证书

```bash
# 生成证书
uv run api-to-mcp gencerts

# 启用 HTTPS 启动服务
uv run api-to-mcp serve-ui --https
```

### 使用正式证书

将证书文件放入 `certs/` 目录，并在 `.env` 中配置路径：

```env
SSL_CERT_PATH=certs/your-domain.crt
SSL_KEY_PATH=certs/your-domain.key
ENABLE_HTTPS=true
```

## 📖 MCP 协议说明

MCP (Model Context Protocol) 是 Anthropic 提出的开放协议，让 AI 安全地与外部工具/数据交互。

### 三大核心能力

| 能力 | 描述 | 示例 |
|------|------|------|
| **Tools** | 可调用的操作（类似 API） | 创建待办、查询数据 |
| **Resources** | 只读上下文数据（类似知识库） | 文档、指南 |
| **Prompts** | 预定义对话模板（类似工作流） | 帮助提示、流程指导 |

### Session 协商流程

1. 客户端发起 `initialize` 请求（不携带 sessionId）
2. 服务端生成 sessionId，通过 `mcp-session-id` Header 返回
3. 后续请求通过 `mcp-session-id` Header 携带 sessionId

## 🤝 贡献

欢迎提交 PR 和 Issue！

## 📄 许可证

MIT License
