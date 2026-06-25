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
git clone https://github.com/your-username/mcp_manager.git
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
# 启动所有服务
./start_all.sh

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
