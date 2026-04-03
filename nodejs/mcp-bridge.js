#!/usr/bin/env node
/**
 * MCP Bridge - Node.js
 * 通过 HTTP 调用远程 SDK 知识库 API
 */

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { CallToolRequestSchema, ListToolsRequestSchema } = require('@modelcontextprotocol/sdk/types.js');

const API_BASE_URL = process.env.SDK_API_URL || 'http://172.27.16.134:8000';

// 创建 MCP 服务器
const server = new Server(
  {
    name: 'sdk-knowledge-bridge',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// 列出可用工具
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'search_sdk_api',
        description: '搜索 SuperMap iObjects Java SDK API。使用自然语言描述来查找相关的类和方法。' +
          '\n***强制触发条件***:当你遇到来自以下包(package) 的类、接口、注解或方法调用时，必须调用此工具，来查询文档' +
          '\n+ com.supermap.analyst.addressmatching' +
          '\n+ com.supermap.analyst.navigation' +
          '\n+ com.supermap.analyst.networkanalyst' +
          '\n+ com.supermap.analyst.spatialanalyst' +
          '\n+ com.supermap.analyst.spatialstatistics' +
          '\n+ com.supermap.analyst.terrainanalyst' +
          '\n+ com.supermap.analyst.trafficanalyst' +
          '\n+ com.supermap.chart' +
          '\n+ com.supermap.chart.conversion' +
          '\n+ com.supermap.data' +
          '\n+ com.supermap.data.bslicense' +
          '\n+ com.supermap.data.cloudlicense' +
          '\n+ com.supermap.data.conversion' +
          '\n+ com.supermap.data.edu' +
          '\n+ com.supermap.data.processing' +
          '\n+ com.supermap.data.processing.cache' +
          '\n+ com.supermap.data.reviewer' +
          '\n+ com.supermap.data.topology' +
          '\n+ com.supermap.image.processing' +
          '\n+ com.supermap.image.processing.uav' +
          '\n+ com.supermap.layout' +
          '\n+ com.supermap.mapping' +
          '\n+ com.supermap.mapping.benchmark' +
          '\n+ com.supermap.maritime.conversion' +
          '\n+ com.supermap.maritime.data' +
          '\n+ com.supermap.maritime.editor.entity' +
          '\n+ com.supermap.maritime.editor.enums' +
          '\n+ com.supermap.maritime.editor.history' +
          '\n+ com.supermap.maritime.editor.operator' +
          '\n+ com.supermap.maritime.editor.topology' +
          '\n+ com.supermap.maritime.editor.topology.data' +
          '\n+ com.supermap.maritime.editor.topology.data.cache' +
          '\n+ com.supermap.maritime.editor.topology.data.cache.entity' +
          '\n+ com.supermap.maritime.editor.topology.entity' +
          '\n+ com.supermap.maritime.editor.ui' +
          '\n+ com.supermap.maritime.editor.util' +
          '\n+ com.supermap.maritime.editor.view' +
          '\n+ com.supermap.maritime.editor.view.entity' +
          '\n+ com.supermap.maritime.mapping' +
          '\n+ com.supermap.mobjects' +
          '\n+ com.supermap.mobjects.animation' +
          '\n+ com.supermap.mobjects.auxiliaryplotting' +
          '\n+ com.supermap.mobjects.common' +
          '\n+ com.supermap.mobjects.electromagnetism' +
          '\n+ com.supermap.mobjects.mapdata' +
          '\n+ com.supermap.mobjects.plotmodelgroup' +
          '\n+ com.supermap.mobjects.situation' +
          '\n+ com.supermap.mobjects.situationmonitor' +
          '\n+ com.supermap.mobjects.situationsimulation' +
          '\n+ com.supermap.mobjects.urbandata' +
          '\n+ com.supermap.plot' +
          '\n+ com.supermap.realspace' +
          '\n+ com.supermap.realspace.networkanalyst' +
          '\n+ com.supermap.realspace.spatialanalyst' +
          '\n+ com.supermap.realspace.threeddesigner' +
          '\n+ com.supermap.realspace.threeddesigner.citygmlconvertor' +
          '\n+ com.supermap.realspace.threeddesigner.GIMConvert' +
          '\n+ com.supermap.realspace.threeddesigner.street' +
          '\n+ com.supermap.realspace.threeddesigner.subProcess' +
          '\n+ com.supermap.realspace.ui' +
          '\n+ com.supermap.tilestorage' +
          '\n+ com.supermap.ui',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: '自然语言查询，例如："如何打开工作空间"、"创建数据源的方法"'
            },
            top_k: {
              type: 'integer',
              description: '返回结果数量（默认 5，最大 10）',
              default: 5,
              minimum: 1,
              maximum: 10
            }
          },
          required: ['query']
        }
      },
      {
        name: 'get_sdk_api_info',
        description: '获取 SDK 知识库的基本信息',
        inputSchema: {
          type: 'object',
          properties: {}
        }
      }
    ]
  };
});

// 处理工具调用
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    if (name === 'search_sdk_api') {
      const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: args.query,
          top_k: args.top_k || 5
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();

      // 格式化结果
      let text = `搜索: "${args.query}"\n找到 ${data.results.length} 个结果:\n\n`;
      data.results.forEach((result, index) => {
        text += `[${index + 1}] ${result.class}.${result.method}\n`;
        text += `    签名: ${result.signature}\n`;
        text += `    描述: ${result.description}\n`;
        text += `    相似度: ${(result.similarity * 100).toFixed(2)}%\n\n`;
      });

      return {
        content: [{ type: 'text', text }]
      };
    }

    if (name === 'get_sdk_api_info') {
      const response = await fetch(`${API_BASE_URL}/health`);
      const data = await response.json();

      return {
        content: [{
          type: 'text',
          text: `SDK 知识库信息:\n- 状态: ${data.status}\n- 文档数量: ${data.document_count}\n- 模型: ${data.model}\n- 集合: ${data.collection}`
        }]
      };
    }

    throw new Error(`未知工具: ${name}`);

  } catch (error) {
    return {
      content: [{ type: 'text', text: `错误: ${error.message}` }],
      isError: true
    };
  }
});

// 启动服务器
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`MCP Bridge 已启动，连接 API: ${API_BASE_URL}`);
}

main().catch(console.error);
