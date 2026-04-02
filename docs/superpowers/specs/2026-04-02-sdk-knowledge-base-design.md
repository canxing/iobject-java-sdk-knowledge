# SDK 知识库系统设计文档

**日期**: 2026-04-02
**主题**: 基于 Docker 的 SuperMap iObjects Java SDK 语义搜索知识库
**状态**: 已确认，待实现

---

## 1. 概述

### 1.1 目标
构建一个完全离线运行的 SDK 知识库系统，支持通过自然语言查询 SuperMap iObjects Java SDK 的 API 信息。

### 1.2 核心需求
- 解析 Javadoc HTML 文档，提取类、方法、参数、描述
- 使用语义向量模型（Sentence-Transformers）构建可搜索的向量数据库
- 提供 HTTP API 服务，支持自然语言查询
- Docker 打包，支持一键离线部署
- 与 Claude Code 集成（通过 CLI 或 MCP）

### 1.3 运行环境
- **构建环境**: 联网 Linux（用于下载模型、构建镜像）
- **离线运行环境**: Linux + Docker Desktop/Engine
- **客户端**: Windows 上的 Claude Code

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│  构建阶段（联网 Linux）                                        │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │
│  │ HTML 文档    │ → │ Python 解析器 │ → │ Chroma 向量库    │ │
│  │ (SuperMap)   │   │ + 向量化      │   │ (嵌入镜像)       │ │
│  └──────────────┘   └──────────────┘   └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Docker 镜像 sdk-kb:latest                                   │
│  ├─ Python 3.9 + FastAPI + Sentence-Transformers             │
│  ├─ 预构建的 Chroma 向量数据库                                │
│  ├─ 本地缓存的 all-MiniLM-L6-v2 模型                         │
│  └─ HTTP API 服务 (端口 8000)                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  离线环境（Linux + Docker）                                    │
│  ┌─────────────────┐      ┌─────────────────────────────┐   │
│  │ query-sdk CLI   │ ──── │ Windows 上运行              │   │
│  │ (包装脚本)       │      │ Claude Code → MCP/HTTP 调用 │   │
│  └─────────────────┘      └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

1. **解析**: HTML → JSON（提取类、方法、签名、描述）
2. **向量化**: JSON → Chroma（生成文本嵌入向量）
3. **查询**: 自然语言 → 向量 → 相似度搜索 → 返回最相关 API

---

## 3. 组件设计

### 3.1 HTML 解析器 (`scripts/parse_javadoc.py`)

**输入**: Javadoc HTML 文件目录
**输出**: `sdk_knowledge.json`

**提取字段**:
- 类名（完整包路径）
- 方法名
- 方法签名（返回类型、参数）
- 方法描述（Javadoc 注释）
- 示例代码（`<pre>` 标签内容）

**技术细节**:
- 使用 BeautifulSoup4 解析 HTML
- 处理 GB2312 编码
- 选择器针对标准 Javadoc 结构：`.memberSummary` 表格

### 3.2 向量构建器 (`scripts/build_vector_db.py`)

**输入**: `sdk_knowledge.json`
**输出**: `data/chroma_db/` 目录

**处理流程**:
1. 将每个方法转换为文本描述：
   ```
   Class: {class_name}
   Method: {signature}
   Description: {description}
   Example: {example}
   ```
2. 使用 `all-MiniLM-L6-v2` 模型生成 384 维向量
3. 批量存入 Chroma 集合 `sdk_api`

**配置**:
- 模型: `sentence-transformers/all-MiniLM-L6-v2` (~80MB)
- 批处理大小: 100
- 集合名称: `sdk_api`

### 3.3 API 服务 (`scripts/api_server.py`)

**框架**: FastAPI

**端点**:

```python
# 搜索 API
POST /search
Request:  {"query": "如何建立连接", "top_k": 5}
Response: {"results": [...]}

# 健康检查
GET /health
Response: {"status": "ok", "total_apis": 12345}
```

**搜索结果结构**:
```json
{
  "results": [
    {
      "class": "com.supermap.data.Workspace",
      "method": "open",
      "signature": "boolean open(String serverUrl, String userName, String password)",
      "description": "打开工作空间",
      "similarity": 0.92
    }
  ]
}
```

### 3.4 CLI 包装 (`query-sdk`)

**实现**: Bash 脚本

```bash
#!/bin/bash
# 调用 Docker 容器执行查询
QUERY="$1"
docker run --rm --network host sdk-kb:latest \
  python scripts/query_client.py "$QUERY"
```

---

## 4. Docker 设计

### 4.1 多阶段构建

**阶段 1**: 构建阶段（安装依赖、生成向量库）
- 安装 Python 依赖
- 下载 sentence-transformers 模型
- 运行解析和向量化脚本

**阶段 2**: 运行阶段（仅包含运行时必需文件）
- Python 3.9-slim 基础镜像
- 复制预构建的向量库和模型
- 启动 FastAPI 服务

### 4.2 镜像内容

```
/app/
├── scripts/
│   ├── api_server.py      # FastAPI 服务
│   └── query_client.py    # CLI 客户端
├── data/
│   └── chroma_db/         # 向量数据库（预构建）
├── models/
│   └── all-MiniLM-L6-v2/  # 本地模型缓存
└── requirements.txt
```

### 4.3 运行时配置

- **端口**: 8000
- **环境变量**:
  - `CHROMA_PATH=/app/data/chroma_db`
  - `MODEL_PATH=/app/models`
- **启动命令**: `uvicorn api_server:app --host 0.0.0.0 --port 8000`

---

## 5. 部署流程

### 5.1 构建阶段（联网 Linux）

```bash
# 1. 克隆/准备项目
# 2. 解析 HTML
python scripts/parse_javadoc.py "SuperMap iObjects Java Javadoc" data/sdk_knowledge.json

# 3. 构建向量库
python scripts/build_vector_db.py

# 4. 构建 Docker 镜像
docker build -t sdk-kb:latest .

# 5. 导出镜像（供离线传输）
docker save -o sdk-kb.tar sdk-kb:latest
```

### 5.2 离线部署（Linux + Docker）

```bash
# 1. 导入镜像
docker load -i sdk-kb.tar

# 2. 启动服务（后台）
docker run -d -p 8000:8000 --name sdk-kb sdk-kb:latest

# 3. 测试查询
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "如何建立连接", "top_k": 3}'

# 4. 配置 CLI 脚本（可选）
cp query-sdk /usr/local/bin/
chmod +x /usr/local/bin/query-sdk
```

---

## 6. Claude Code 集成

### 6.1 方法 A: CLI 集成

在项目 `.claude/context.md` 中添加：

```markdown
## SDK API 查询

使用以下命令查询 SuperMap SDK API：
```bash
query-sdk "自然语言描述"
```

示例：
- `query-sdk "如何打开工作空间"`
- `query-sdk "创建数据集"`
```

### 6.2 方法 B: MCP 服务器（已实现）

创建 MCP 服务器 `scripts/mcp_server.py`，通过 Model Context Protocol 与 Claude Code 集成。

**MCP 工具列表**:

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `search_sdk_api` | 搜索 SDK API | `query`: 自然语言查询<br>`top_k`: 结果数量(1-10，默认5) |
| `get_sdk_api_info` | 获取知识库信息 | 无 |

**配置方式**:

1. **项目级配置**（推荐）: 在项目根目录创建 `.mcp.json`
2. **全局配置**: 在 Claude Code 设置中添加

**使用方式**:

配置完成后，直接在 Claude Code 中提问：
```
"帮我查找打开工作空间的方法"
"如何创建数据集？"
```

Claude 会自动调用 `search_sdk_api` 工具并返回格式化的结果。

**技术实现**:
- 使用 `mcp` Python SDK 实现服务器
- 通过 stdio 与 Claude Code 通信
- 调用本地 HTTP API (`http://localhost:8000`) 获取数据
- 返回 Markdown 格式的搜索结果

---

## 7. 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 向量模型 | all-MiniLM-L6-v2 | 体积小(80MB)、速度快、效果足够 |
| 向量数据库 | Chroma | 轻量、纯 Python、支持持久化 |
| API 框架 | FastAPI | 现代、异步、自动生成文档 |
| 基础镜像 | python:3.9-slim | 体积小、兼容性好 |

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| HTML 结构变化 | 解析失败 | 记录 Javadoc 版本，提供配置化选择器 |
| 模型下载失败 | 构建中断 | 预下载模型到本地目录，不从 HuggingFace 实时拉取 |
| 镜像过大 | 传输困难 | 使用多阶段构建，仅保留运行时文件 |
| 向量库精度不足 | 搜索结果差 | 调优 top_k，支持重排序或混合搜索 |

---

## 9. 成功标准

1. **功能**: 能够解析至少 80% 的 Javadoc HTML 文件
2. **性能**: 单次查询响应时间 < 500ms
3. **准确度**: 常见查询的 Top-3 结果包含正确答案
4. **离线**: 无网络环境下完全可用
5. **部署**: 单命令启动，无需额外配置

---

## 10. 后续扩展（可选）

- [ ] 支持增量更新（SDK 版本升级时只更新变化的部分）
- [ ] 添加代码示例索引
- [ ] 支持类级别搜索
- [ ] 添加相关性反馈机制
- [x] MCP 服务器原生集成

---

**设计者**: Claude Code
**评审状态**: 待用户最终确认
