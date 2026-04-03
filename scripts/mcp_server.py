#!/usr/bin/env python3
"""
SDK Knowledge Base MCP Server
通过 Model Context Protocol 暴露 SDK 查询能力给 Claude Code
"""
import json
import os
import sys
from typing import Any

import requests
from mcp.server import Server
from mcp.types import (
    TextContent,
    Tool,
)

# API 服务地址
API_BASE_URL = os.getenv("SDK_API_URL", "http://localhost:8000")

# 创建 MCP 服务器
app = Server("sdk-knowledge-base")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用的工具"""
    return [
        Tool(
            name="search_sdk_api",
            description="***强制触发条件***:当你遇到来自以下包(package) 的类、接口、注解或方法调用时，必须调用此工具，来查询文档" +
                "\n+ com.supermap.analyst.addressmatching" +
                "\n+ com.supermap.analyst.navigation" +
                "\n+ com.supermap.analyst.networkanalyst" +
                "\n+ com.supermap.analyst.spatialanalyst" +
                "\n+ com.supermap.analyst.spatialstatistics" +
                "\n+ com.supermap.analyst.terrainanalyst" +
                "\n+ com.supermap.analyst.trafficanalyst" +
                "\n+ com.supermap.chart" +
                "\n+ com.supermap.chart.conversion" +
                "\n+ com.supermap.data" +
                "\n+ com.supermap.data.bslicense" +
                "\n+ com.supermap.data.cloudlicense" +
                "\n+ com.supermap.data.conversion" +
                "\n+ com.supermap.data.edu" +
                "\n+ com.supermap.data.processing" +
                "\n+ com.supermap.data.processing.cache" +
                "\n+ com.supermap.data.reviewer" +
                "\n+ com.supermap.data.topology" +
                "\n+ com.supermap.image.processing" +
                "\n+ com.supermap.image.processing.uav" +
                "\n+ com.supermap.layout" +
                "\n+ com.supermap.mapping" +
                "\n+ com.supermap.mapping.benchmark" +
                "\n+ com.supermap.maritime.conversion" +
                "\n+ com.supermap.maritime.data" +
                "\n+ com.supermap.maritime.editor.entity" +
                "\n+ com.supermap.maritime.editor.enums" +
                "\n+ com.supermap.maritime.editor.history" +
                "\n+ com.supermap.maritime.editor.operator" +
                "\n+ com.supermap.maritime.editor.topology" +
                "\n+ com.supermap.maritime.editor.topology.data" +
                "\n+ com.supermap.maritime.editor.topology.data.cache" +
                "\n+ com.supermap.maritime.editor.topology.data.cache.entity" +
                "\n+ com.supermap.maritime.editor.topology.entity" +
                "\n+ com.supermap.maritime.editor.ui" +
                "\n+ com.supermap.maritime.editor.util" +
                "\n+ com.supermap.maritime.editor.view" +
                "\n+ com.supermap.maritime.editor.view.entity" +
                "\n+ com.supermap.maritime.mapping" +
                "\n+ com.supermap.mobjects" +
                "\n+ com.supermap.mobjects.animation" +
                "\n+ com.supermap.mobjects.auxiliaryplotting" +
                "\n+ com.supermap.mobjects.common" +
                "\n+ com.supermap.mobjects.electromagnetism" +
                "\n+ com.supermap.mobjects.mapdata" +
                "\n+ com.supermap.mobjects.plotmodelgroup" +
                "\n+ com.supermap.mobjects.situation" +
                "\n+ com.supermap.mobjects.situationmonitor" +
                "\n+ com.supermap.mobjects.situationsimulation" +
                "\n+ com.supermap.mobjects.urbandata" +
                "\n+ com.supermap.plot" +
                "\n+ com.supermap.realspace" +
                "\n+ com.supermap.realspace.networkanalyst" +
                "\n+ com.supermap.realspace.spatialanalyst" +
                "\n+ com.supermap.realspace.threeddesigner" +
                "\n+ com.supermap.realspace.threeddesigner.citygmlconvertor" +
                "\n+ com.supermap.realspace.threeddesigner.GIMConvert" +
                "\n+ com.supermap.realspace.threeddesigner.street" +
                "\n+ com.supermap.realspace.threeddesigner.subProcess" +
                "\n+ com.supermap.realspace.ui" +
                "\n+ com.supermap.tilestorage" +
                "\n+ com.supermap.ui",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "自然语言查询，例如：'如何打开工作空间'、'创建数据源的方法'、'Dispose 释放资源'"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量（默认 5，最大 10）",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_sdk_api_info",
            description="获取 SDK 知识库的基本信息",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """处理工具调用"""

    if name == "search_sdk_api":
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 5)

        if not query:
            return [TextContent(type="text", text="错误：请提供查询内容")]

        try:
            # 调用本地 API
            response = requests.post(
                f"{API_BASE_URL}/search",
                json={"query": query, "top_k": top_k},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # 格式化结果
            results = data.get("results", [])
            if not results:
                return [TextContent(type="text", text=f"未找到与 '{query}' 相关的 API")]

            # 构建 Markdown 格式的输出
            lines = [f"# SDK API 搜索结果", f"查询: `{query}`\n", f"找到 {len(results)} 个相关 API:\n"]

            for i, result in enumerate(results, 1):
                class_name = result.get("class", "")
                method = result.get("method", "")
                signature = result.get("signature", "")
                description = result.get("description", "")
                similarity = result.get("similarity", 0)

                lines.append(f"## {i}. {class_name}.{method}")
                lines.append(f"**相似度**: {similarity*100:.1f}%")
                lines.append(f"**签名**: `{signature}`")
                if description:
                    lines.append(f"**描述**: {description}")
                lines.append("")

            return [TextContent(type="text", text="\n".join(lines))]

        except requests.exceptions.ConnectionError:
            return [TextContent(
                type="text",
                text=f"错误：无法连接到 SDK API 服务 ({API_BASE_URL})\n\n请确保服务已启动:\n- 本地运行: `python scripts/api_server.py`\n- Docker 运行: `docker run -d -p 8000:8000 sdk-kb:latest`"
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"查询出错: {str(e)}")]

    elif name == "get_sdk_api_info":
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            response.raise_for_status()
            data = response.json()

            info = f"""# SDK Knowledge Base 信息

- **状态**: {data.get('status', 'unknown')}
- **文档数量**: {data.get('document_count', 0)}
- **模型**: {data.get('model', 'unknown')}
- **集合**: {data.get('collection', 'unknown')}
- **API 地址**: {API_BASE_URL}
"""
            return [TextContent(type="text", text=info)]
        except Exception as e:
            return [TextContent(type="text", text=f"获取信息失败: {str(e)}")]

    else:
        return [TextContent(type="text", text=f"未知工具: {name}")]


async def main():
    """主入口"""
    # 检查 API 服务是否可用
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        print(f"SDK API 服务已连接: {API_BASE_URL}", file=sys.stderr)
    except:
        print(f"警告：无法连接到 SDK API 服务 ({API_BASE_URL})", file=sys.stderr)
        print("请确保服务已启动", file=sys.stderr)

    # 启动 MCP 服务器 (stdio 模式)
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
