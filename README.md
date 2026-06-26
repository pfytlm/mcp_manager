# MCP Manager

一个完整的 **Model Context Protocol (MCP)** 服务管理框架，提供统一网关、REST API 转 MCP 服务的转换能力、MCP 服务注册中心、管理后台 UI 和 MCP 协议测试工具。

## ✨ 功能特性

- **统一网关架构**: 所有服务共享一个端口，通过 URL 路径区分（/mcp/todo, /mcp/calc）
- **API → MCP 转换框架**: 将现有的 REST API 服务自动转换为 MCP 服务
- **MCP 服务注册中心**: 集中管理多个 MCP 服务，支持服务发现
- **管理后台 UI**: 可视化查看和管理所有 MCP 服务配置
- **Token 管理**: API Key 管理功能，支持默认 Token，请求认证验证
- **MCP 协议测试**: 通过 streamable-HTTP 协议测试 MCP 的 Tools/Resources/Prompts
- **组合工具支持**: 支持一个 Tool 内部调用多个 API 的组合模式
- **HTTPS 支持**: 完整的 SSL/TLS 支持，可配置证书路径
- **Bearer Token 认证**: 统一的 Authorization 头认证机制

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
| MCP_AUTH_TOKENS | 认证 Token（逗号分隔） | dev_token_123,dev_token_456 |
| SSL_CERT_PATH | SSL 证书路径 | certs/server.crt |
| SSL_KEY_PATH | SSL 私钥路径 | certs/server.key |

### 启动服务

```bash
# 开发模式（热重载）
./dev.sh

# 生产模式（HTTPS）
./start.sh

# 或使用 uv run
uv run python -m uvicorn api_to_mcp.gateway:_unified_gateway_factory --factory --host 0.0.0.0 --port 8080
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 管理后台 | http://localhost:8080 |
| MCP 网关 | http://localhost:8080/mcp |
| TODO MCP | http://localhost:8080/mcp/todo |
| 计算器 MCP | http://localhost:8080/mcp/calc |
| REST API | http://localhost:8080/api/todo |

## 🏗️ 项目结构

```
src/api_to_mcp/
├── __init__.py
├── auth.py              # 认证中间件
├── cli.py               # 命令行入口
├── config.py            # 配置管理
├── core.py              # API → MCP 转换核心
├── gateway.py           # 统一网关（核心入口）
├── manager.py           # 管理后台 API 路由
├── registry.py          # MCP 服务注册中心
├── sse_server.py        # MCP SSE 服务器
├── examples/            # 示例服务
│   ├── todo_api.py      # TODO REST API
│   ├── todo_mcp.py      # TODO MCP 服务
│   ├── todo_models.py   # TODO 数据模型
│   ├── calc_api.py      # 计算器 REST API
│   └── calc_mcp.py      # 计算器 MCP 服务
└── static/
    └── index.html       # 管理后台前端页面
```

## 🏗️ 架构设计

### 统一网关架构

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    统一网关 (gateway.py)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ 认证中间件   │ →│ 路由分发    │ →│ 服务处理            │ │
│  │ auth.py     │  │ APIRouter   │  │ manager/gateway     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
    │                    │                    │
    ▼                    ▼                    ▼
 /api/*            /mcp/todo            /mcp/calc
    │                    │                    │
    ▼                    ▼                    ▼
管理后台           TODO MCP服务         计算器MCP服务
manager.py        todo_mcp.py          calc_mcp.py
    │                    │                    │
    └────────────────────┴────────────────────┘
                         │
                         ▼
                   注册中心 (registry.py)
```

### 模块职责

| 模块 | 职责 |
|------|------|
| **gateway.py** | 统一网关入口，组合所有路由和中间件 |
| **manager.py** | 管理后台 API 路由（服务管理、Token 管理、测试） |
| **auth.py** | Bearer Token 认证中间件 |
| **core.py** | API→MCP 转换核心框架 |
| **registry.py** | MCP 服务注册中心，数据结构定义 |
| **config.py** | 全局配置管理 (.env 加载) |

## 🔧 API 端点

### 服务管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/services` | GET | 获取服务列表 |
| `/api/services/{name}` | GET | 获取服务详情 |
| `/api/services` | POST | 创建新服务 |
| `/api/services/{name}` | PUT | 更新服务 |
| `/api/services/{name}` | DELETE | 删除服务 |

### Token 管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/keys` | GET | 获取 Token 列表 |
| `/api/keys` | POST | 创建新 Token |
| `/api/keys/{key_id}` | PUT | 更新 Token |
| `/api/keys/{key_id}` | DELETE | 删除 Token |

### MCP 测试

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/test/tool` | POST | 测试工具调用 |
| `/api/test/resource` | POST | 测试资源读取 |
| `/api/test/prompt` | POST | 测试提示词获取 |

### 健康检查

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |

## 🔐 认证机制

所有 MCP 请求（`/mcp/*`）需要携带 Bearer Token：

```bash
curl -H "Authorization: Bearer your_token_here" https://mcp.pfytlm.top/mcp/todo
```

Token 通过环境变量 `MCP_AUTH_TOKENS` 配置，多个 Token 用逗号分隔：

```env
MCP_AUTH_TOKENS=token1,token2,token3
```

## 📡 MCP 协议测试

管理后台提供 MCP 协议测试功能，支持测试：

1. **Tools** - 调用 MCP 工具
2. **Resources** - 读取 MCP 资源
3. **Prompts** - 获取 MCP 提示词

测试结果会显示：
- 响应数据
- 完整的 CURL 命令（包含 Authorization 头）

## 🔐 HTTPS 配置

### 使用自签名证书

```bash
# 生成证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout certs/server.key \
    -out certs/server.crt \
    -subj "/CN=localhost"

# 启用 HTTPS 启动服务
uv run python -m uvicorn api_to_mcp.gateway:_unified_gateway_factory --factory \
    --host 0.0.0.0 --port 443 \
    --ssl-certfile=certs/server.crt \
    --ssl-keyfile=certs/server.key
```

### 使用正式证书

将证书文件放入 `certs/` 目录即可。

## 📖 MCP 协议说明

MCP (Model Context Protocol) 是 Anthropic 提出的开放协议，让 AI 安全地与外部工具/数据交互。

### 三大核心能力

| 能力 | 描述 | 示例 |
|------|------|------|
| **Tools** | 可调用的操作（类似 API） | 创建待办、查询数据 |
| **Resources** | 只读上下文数据（类似知识库） | 文档、指南 |
| **Prompts** | 预定义对话模板（类似工作流） | 帮助提示、流程指导 |

## 🚀 ECS 部署

```bash
# 部署到 ECS
./deploy_ecs.sh --ip <ECS_IP> --domain <DOMAIN> --https
```

部署脚本会自动：
- 安装依赖
- 配置环境变量
- 生成 SSL 证书（如不存在）
- 启动 HTTPS 服务

## 🤝 贡献

欢迎提交 PR 和 Issue！

## 📄 许可证

MIT License
