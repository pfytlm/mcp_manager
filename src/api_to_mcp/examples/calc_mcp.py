"""
计算器 MCP 服务
将计算器 REST API 转化为 MCP 服务
"""
from __future__ import annotations

import os
from typing import Dict, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from api_to_mcp.core import (
    APIEndpoint,
    APIParameter,
    HTTPMethod,
    ParameterLocation,
    build_service_metadata,
    create_mcp_server_from_api,
)

load_dotenv()

API_BASE_URL = os.getenv("CALC_API_BASE_URL", "http://127.0.0.1:8002")


def get_calc_endpoints() -> list[APIEndpoint]:
    """获取计算器API端点定义"""
    return [
        APIEndpoint(
            name="add",
            path="/calc/add",
            method=HTTPMethod.GET,
            description="加法运算 - 计算两个数的和",
            parameters=[
                APIParameter(name="a", location=ParameterLocation.QUERY, type=float, required=True, description="第一个加数"),
                APIParameter(name="b", location=ParameterLocation.QUERY, type=float, required=True, description="第二个加数"),
            ],
        ),
        APIEndpoint(
            name="subtract",
            path="/calc/subtract",
            method=HTTPMethod.GET,
            description="减法运算 - 计算两个数的差",
            parameters=[
                APIParameter(name="a", location=ParameterLocation.QUERY, type=float, required=True, description="被减数"),
                APIParameter(name="b", location=ParameterLocation.QUERY, type=float, required=True, description="减数"),
            ],
        ),
        APIEndpoint(
            name="multiply",
            path="/calc/multiply",
            method=HTTPMethod.GET,
            description="乘法运算 - 计算两个数的乘积",
            parameters=[
                APIParameter(name="a", location=ParameterLocation.QUERY, type=float, required=True, description="第一个乘数"),
                APIParameter(name="b", location=ParameterLocation.QUERY, type=float, required=True, description="第二个乘数"),
            ],
        ),
        APIEndpoint(
            name="divide",
            path="/calc/divide",
            method=HTTPMethod.GET,
            description="除法运算 - 计算两个数的商，除数不能为零",
            parameters=[
                APIParameter(name="a", location=ParameterLocation.QUERY, type=float, required=True, description="被除数"),
                APIParameter(name="b", location=ParameterLocation.QUERY, type=float, required=True, description="除数（不能为零）"),
            ],
        ),
        APIEndpoint(
            name="power",
            path="/calc/power",
            method=HTTPMethod.GET,
            description="幂运算 - 计算 base 的 exponent 次方",
            parameters=[
                APIParameter(name="base", location=ParameterLocation.QUERY, type=float, required=True, description="底数"),
                APIParameter(name="exponent", location=ParameterLocation.QUERY, type=float, required=True, description="指数"),
            ],
        ),
        APIEndpoint(
            name="sqrt",
            path="/calc/sqrt",
            method=HTTPMethod.GET,
            description="平方根运算 - 计算一个非负数的平方根",
            parameters=[
                APIParameter(name="number", location=ParameterLocation.QUERY, type=float, required=True, description="非负数"),
            ],
        ),
        APIEndpoint(
            name="modulo",
            path="/calc/modulo",
            method=HTTPMethod.GET,
            description="取模运算 - 计算两个整数相除的余数",
            parameters=[
                APIParameter(name="a", location=ParameterLocation.QUERY, type=int, required=True, description="被除数"),
                APIParameter(name="b", location=ParameterLocation.QUERY, type=int, required=True, description="除数（不能为零）"),
            ],
        ),
    ]


def get_calc_service_metadata(base_url: Optional[str] = None) -> Dict:
    """获取计算器服务元数据（用于管理后台注册）"""
    url = base_url or API_BASE_URL
    endpoints = get_calc_endpoints()

    instructions = """
你是一个计算器助手，可以帮助用户进行各种数学计算。

## 可用运算
1. **add** - 加法运算
2. **subtract** - 减法运算
3. **multiply** - 乘法运算
4. **divide** - 除法运算（注意除数不能为零）
5. **power** - 幂运算（计算次方）
6. **sqrt** - 平方根运算
7. **modulo** - 取模运算（求余数）

## 使用建议
- 简单计算直接使用对应工具
- 复杂计算可以分步进行，或者使用组合工具
- 除法和取模运算时注意除数不能为零
"""

    return build_service_metadata(
        server_name="calculator-mcp-server",
        base_url=url,
        endpoints=endpoints,
        headers={},
        instructions=instructions,
        description="计算器MCP服务 - 提供基础数学运算和高级运算功能",
        extra_resources=[
            {"uri": "calc://guide", "name": "Calculator Guide", "description": "计算器使用指南和运算说明"}
        ],
        extra_prompts=[
            {"name": "calc_help", "description": "计算器使用帮助模板"}
        ],
        extra_tools=[
            {
                "name": "batch_calculate",
                "description": "批量计算 - 一次性执行多个运算（组合工具）",
                "method": "COMPOSITE",
                "path": "组合: 循环调用多个计算API",
                "parameters": [
                    {"name": "expressions", "type": "array", "required": True, "description": "表达式列表，每个表达式包含 op(运算类型), a, b 或 number", "location": "composite"},
                ],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expressions": {
                            "type": "array",
                            "description": "表达式列表",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "op": {"type": "string", "description": "运算类型: add/subtract/multiply/divide/power/modulo/sqrt"},
                                    "a": {"type": "number", "description": "第一个数"},
                                    "b": {"type": "number", "description": "第二个数"},
                                    "number": {"type": "number", "description": "数字（sqrt时用）"},
                                },
                            },
                        },
                    },
                    "required": ["expressions"],
                },
            },
        ],
        tags=["计算器", "数学运算", "工具"],
    )


def create_calc_mcp_server(
    base_url: Optional[str] = None,
    verify_ssl: bool = True,
) -> tuple[FastMCP, object]:
    """创建计算器MCP服务器"""
    import asyncio

    url = base_url or API_BASE_URL
    endpoints = get_calc_endpoints()

    instructions = """
你是一个计算器助手，可以帮助用户进行各种数学计算。

## 可用运算
1. **add** - 加法运算
2. **subtract** - 减法运算
3. **multiply** - 乘法运算
4. **divide** - 除法运算（注意除数不能为零）
5. **power** - 幂运算（计算次方）
6. **sqrt** - 平方根运算
7. **modulo** - 取模运算（求余数）

## 使用建议
- 简单计算直接使用对应工具
- 复杂计算可以分步进行，或者使用组合工具
- 除法和取模运算时注意除数不能为零
"""

    mcp_server, builder = create_mcp_server_from_api(
        server_name="calculator-mcp-server",
        base_url=url,
        endpoints=endpoints,
        headers={},
        instructions=instructions,
        verify_ssl=verify_ssl,
    )

    @mcp_server.resource("calc://guide")
    def calc_guide() -> str:
        return """
# 计算器MCP服务使用指南

## 基础运算
- **add(a, b)** - 加法: a + b
- **subtract(a, b)** - 减法: a - b
- **multiply(a, b)** - 乘法: a * b
- **divide(a, b)** - 除法: a / b (b ≠ 0)
- **modulo(a, b)** - 取模: a % b (b ≠ 0, 整数)

## 高级运算
- **power(base, exponent)** - 幂运算: base^exponent
- **sqrt(number)** - 平方根: √number (number ≥ 0)

## 注意事项
- 除法和取模运算中除数不能为零
- 平方根运算中被开方数必须非负
- 所有运算结果以浮点数返回
"""

    @mcp_server.prompt()
    def calc_help() -> str:
        return """请帮我计算这个数学表达式：
1. 先分析需要使用哪些运算
2. 分步进行计算
3. 给出最终结果和计算过程"""

    # 组合工具: 批量计算
    @mcp_server.tool(
        description="批量执行多个数学运算。一次性传入多个表达式，自动计算并返回所有结果。支持 add/subtract/multiply/divide/power/modulo/sqrt 七种运算。",
    )
    async def batch_calculate(
        expressions: list[dict],
    ) -> str:
        """
        批量计算（组合工具 - 调用多个运算API）

        Args:
            expressions: 表达式列表，每个字典包含 op(运算类型) 和参数

        Returns:
            格式化的批量计算结果
        """
        client = await builder._get_client()

        results = []
        success_count = 0
        fail_count = 0

        for i, expr in enumerate(expressions):
            op = expr.get("op", "")
            try:
                if op == "sqrt":
                    number = expr.get("number", 0)
                    resp = await client.get(f"/calc/sqrt", params={"number": number})
                elif op == "power":
                    base = expr.get("base", expr.get("a", 0))
                    exponent = expr.get("exponent", expr.get("b", 0))
                    resp = await client.get(f"/calc/power", params={"base": base, "exponent": exponent})
                else:
                    a = expr.get("a", 0)
                    b = expr.get("b", 0)
                    resp = await client.get(f"/calc/{op}", params={"a": a, "b": b})

                if resp.status_code == 200:
                    data = resp.json()
                    results.append(f"  [{i+1}] ✅ {data['expression']}")
                    success_count += 1
                else:
                    results.append(f"  [{i+1}] ❌ {op} - HTTP {resp.status_code}: {resp.text}")
                    fail_count += 1
            except Exception as e:
                results.append(f"  [{i+1}] ❌ {op} - {str(e)}")
                fail_count += 1

        lines = [
            "# 🧮 批量计算结果",
            "",
            f"成功: **{success_count}** | 失败: **{fail_count}**",
            "",
            "## 详细结果",
        ] + results

        return "\n".join(lines)

    return mcp_server, builder


def main():
    mcp_server, _ = create_calc_mcp_server()
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
