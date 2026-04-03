# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于语义搜索的 SuperMap iObjects Java SDK 知识库系统。系统将 Javadoc HTML 文档解析为结构化数据，使用 sentence-transformers 模型生成向量，存储在 ChromaDB 中，通过 FastAPI 提供 HTTP 服务，并可通过 MCP (Model Context Protocol) 与 Claude Code 集成。

## 系统架构

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Javadoc HTML   │────▶│  parse_javadoc   │────▶│  JSON Data      │
│  (GB2312编码)   │     │  (HTML解析器)    │     │  (结构化API)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
┌─────────────────┐     ┌──────────────────┐              │
│  HTTP API       │────▶│  api_server      │◀─────────────┘
│  (/search)      │     │  (FastAPI服务)   │    build_vector_db
└─────────────────┘     └──────────────────┘    (向量化+ChromaDB)
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  query_client   │────▶│  Docker Container│
│  (CLI工具)      │     │  (sdk-kb:latest) │
└─────────────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│  MCP Server     │◀──── Claude Code 集成
│  (mcp_server.py)│
└─────────────────┘
```

## 常用命令

### 构建

```bash
# 完整构建（解析 → 向量化 → Docker镜像 → 导出）
./build.sh

# 手动构建流程
python scripts/parse_javadoc.py "SuperMap iObjects Java Javadoc" data/parsed_javadoc.json
python scripts/build_vector_db.py --input data/parsed_javadoc.json --output data/chroma_db
docker build -t sdk-kb:latest .
docker save -o sdk-kb.tar sdk-kb:latest
```

### 开发/测试

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest
pytest tests/test_parse_javadoc.py -v
pytest --cov=scripts --cov-report=html

# 本地运行 API 服务（需要 data/chroma_db 已构建）
python scripts/api_server.py
# 或使用 uvicorn
uvicorn scripts.api_server:app --host 0.0.0.0 --port 8000

# 本地 CLI 查询
python scripts/query_client.py "如何创建数据源"
```

### 部署

```bash
# 导入镜像
docker load -i sdk-kb.tar

# 启动服务
docker run -d \
    --name sdk-kb \
    -p 8000:8000 \
    -v $(pwd)/data:/app/data:ro \
    sdk-kb:latest

# 或使用 query-sdk 脚本（自动管理容器）
./query-sdk "如何创建数据源"
./query-sdk --check      # 健康检查
./query-sdk --stop       # 停止容器
./query-sdk --restart    # 重启容器
```

## 代码结构

### scripts/parse_javadoc.py
解析 Javadoc HTML 文件（GB2312 编码），提取类名、包名、方法签名和描述。

关键类：`JavadocParser`
- `parse_file(path)` - 解析单个 HTML 文件
- `parse_directory(input_dir, output_json)` - 批量解析目录
- 输出格式：`[{class, package, full_class, file, methods: [{name, signature, modifiers, description}]}]`

### scripts/build_vector_db.py
使用 sentence-transformers/all-MiniLM-L6-v2 模型将 API 信息转换为向量，存储到 ChromaDB。

关键类：`VectorDBBuilder`
- `build(json_path, batch_size=100)` - 构建向量数据库
- `query(query_text, n_results=5)` - 查询相似文档
- 向量维度：384
- 距离度量：余弦相似度 (cosine)

### scripts/api_server.py
FastAPI HTTP 服务，提供 RESTful API。

端点：
- `GET /` - API 信息
- `GET /health` - 健康检查（返回文档数量、模型名称）
- `POST /search` - 语义搜索（参数：query, top_k）

### scripts/mcp_server.py
MCP 服务器实现，暴露两个工具：
- `search_sdk_api` - 搜索 SDK API（query, top_k）
- `get_sdk_api_info` - 获取知识库信息

通过 stdio 与 Claude Code 通信，内部调用 HTTP API。

### nodejs/mcp-bridge.js
Node.js MCP 桥接器，用于远程 API 场景。当 API 服务运行在远程服务器时使用。

## MCP 配置

项目已配置 `.mcp.json`，Claude Code 会自动加载：

```json
{
  "mcpServers": {
    "sdk-knowledge-base": {
      "command": "D:/code/iobject-java-sdk-knowledge/venv/Scripts/python.exe",
      "args": ["D:/code/iobject-java-sdk-knowledge/scripts/mcp_server.py"],
      "env": {"SDK_API_URL": "http://localhost:8000"}
    }
  }
}
```

远程 API 配置（使用 Node.js 桥接器）：

```json
{
  "mcpServers": {
    "sdk-knowledge-base": {
      "command": "node",
      "args": ["D:/code/iobject-java-sdk-knowledge/nodejs/mcp-bridge.js"],
      "env": {"SDK_API_URL": "http://remote-host:8000"}
    }
  }
}
```

## 数据流

1. **解析阶段**：`SuperMap iObjects Java Javadoc/` → `data/parsed_javadoc.json`
2. **向量化阶段**：`data/parsed_javadoc.json` → `data/chroma_db/` (ChromaDB 持久化存储)
3. **服务阶段**：`data/chroma_db/` + `models/` → Docker 容器
4. **查询阶段**：自然语言查询 → 向量编码 → ChromaDB 相似度搜索 → 返回 API 信息

## 关键设计决策

### HTML 编码
Javadoc HTML 文件使用 GB2312 编码，解析器默认使用此编码。如果解析其他项目文档，可能需要调整 `JavadocParser.encoding`。

### 文档 ID 生成
为避免方法重载冲突，文档 ID 格式为：`{full_class}.{method_name}_{signature_hash:04x}`，其中 signature_hash 是方法签名的哈希值。

### 模型选择
使用 `sentence-transformers/all-MiniLM-L6-v2`（384维），在性能和准确度之间平衡。模型在 Docker 构建阶段预下载并保存到 `/app/models/`。

### 容器化策略
多阶段 Dockerfile：
- Stage 1 (builder)：安装编译依赖、Python 包、下载模型
- Stage 2 (runner)：复制虚拟环境和模型，运行非 root 用户

## 测试

测试文件位于 `tests/` 目录：
- `test_parse_javadoc.py` - HTML 解析器测试
- `test_build_vector_db.py` - 向量数据库构建测试
- `test_api_server.py` - API 服务测试

测试数据：`tests/fixtures/sample_class.html`（GB2312 编码的样本 Javadoc HTML）

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SDK_API_URL` | http://localhost:8000 | API 服务地址 |
| `CHROMA_PATH` | data/chroma_db | ChromaDB 存储路径 |
| `MODEL_PATH` | models | 模型缓存路径 |
| `MODEL_NAME` | sentence-transformers/all-MiniLM-L6-v2 | 向量模型名称 |
| `COLLECTION_NAME` | sdk_api | ChromaDB 集合名称 |
