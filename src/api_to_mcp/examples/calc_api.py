"""
计算器 REST API 服务
提供基础的数学计算 API 端点
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from ..config import config


app = FastAPI(
    title="Calculator API",
    description="计算器 REST API 服务 - 基础数学运算",
    version="1.0.0",
)


class CalculationResult(BaseModel):
    operation: str
    result: float
    expression: str


class BatchCalculationRequest(BaseModel):
    operations: list[dict]


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "calculator-api"}


@app.get("/calc/add", tags=["基础运算"], response_model=CalculationResult)
async def add(a: float, b: float):
    """加法运算"""
    result = a + b
    return CalculationResult(
        operation="add",
        result=result,
        expression=f"{a} + {b} = {result}",
    )


@app.get("/calc/subtract", tags=["基础运算"], response_model=CalculationResult)
async def subtract(a: float, b: float):
    """减法运算"""
    result = a - b
    return CalculationResult(
        operation="subtract",
        result=result,
        expression=f"{a} - {b} = {result}",
    )


@app.get("/calc/multiply", tags=["基础运算"], response_model=CalculationResult)
async def multiply(a: float, b: float):
    """乘法运算"""
    result = a * b
    return CalculationResult(
        operation="multiply",
        result=result,
        expression=f"{a} * {b} = {result}",
    )


@app.get("/calc/divide", tags=["基础运算"], response_model=CalculationResult)
async def divide(a: float, b: float):
    """除法运算"""
    if b == 0:
        raise HTTPException(status_code=400, detail="除数不能为零")
    result = a / b
    return CalculationResult(
        operation="divide",
        result=result,
        expression=f"{a} / {b} = {result}",
    )


@app.get("/calc/power", tags=["高级运算"], response_model=CalculationResult)
async def power(base: float, exponent: float):
    """幂运算 (base^exponent)"""
    result = base ** exponent
    return CalculationResult(
        operation="power",
        result=result,
        expression=f"{base}^{exponent} = {result}",
    )


@app.get("/calc/sqrt", tags=["高级运算"], response_model=CalculationResult)
async def sqrt(number: float):
    """平方根运算"""
    if number < 0:
        raise HTTPException(status_code=400, detail="负数没有实数平方根")
    import math
    result = math.sqrt(number)
    return CalculationResult(
        operation="sqrt",
        result=result,
        expression=f"√{number} = {result}",
    )


@app.get("/calc/modulo", tags=["基础运算"], response_model=CalculationResult)
async def modulo(a: int, b: int):
    """取模运算 (求余数)"""
    if b == 0:
        raise HTTPException(status_code=400, detail="除数不能为零")
    result = a % b
    return CalculationResult(
        operation="modulo",
        result=float(result),
        expression=f"{a} % {b} = {result}",
    )


@app.get("/stats/summary", tags=["统计"])
async def stats_summary():
    """计算服务统计信息"""
    return {
        "service": "calculator-api",
        "total_operations_supported": 7,
        "categories": ["基础运算", "高级运算"],
        "operations": {
            "basic": ["add", "subtract", "multiply", "divide", "modulo"],
            "advanced": ["power", "sqrt"],
        },
    }


def main():
    ssl_opts = config.get_ssl_context()
    uvicorn.run(
        "api_to_mcp.examples.calc_api:app",
        host="0.0.0.0",
        port=config.CALC_API_PORT,
        reload=True,
        **(ssl_opts or {}),
    )


if __name__ == "__main__":
    main()
