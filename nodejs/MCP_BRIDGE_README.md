# MCP Bridge (Node.js)

通过 Node.js 实现 MCP 协议，远程调用 SDK 知识库 API。

## 安装

```bash
npm install
```

## 配置 Claude Code

在 `.mcp.json` 中添加：

```json
{
  "mcpServers": {
    "sdk-knowledge-base": {
      "command": "node",
      "args": [
        "D:/code/iobject-java-sdk-knowledge/mcp-bridge.js"
      ],
      "env": {
        "SDK_API_URL": "http://172.27.16.134:8000"
      }
    }
  }
}
```

## 环境变量

- `SDK_API_URL`: API 服务器地址（默认: http://172.27.16.134:8000）

## 可用工具

1. **search_sdk_api** - 搜索 SDK API
   - query: 自然语言查询
   - top_k: 返回结果数量（1-10）

2. **get_sdk_api_info** - 获取知识库信息

## 测试

```bash
# 直接运行
node mcp-bridge.js

# 或带环境变量
SDK_API_URL=http://172.27.16.134:8000 node mcp-bridge.js
```
