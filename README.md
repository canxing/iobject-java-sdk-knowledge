# SDK 知识库系统

SuperMap iObjects Java SDK 知识库系统，基于语义搜索的 API 文档查询工具。

## 功能概述

- **语义搜索**: 使用 sentence-transformers 模型进行自然语言查询，找到最相关的 API 方法
- **Javadoc 解析**: 自动解析 Javadoc HTML 文档，提取类、方法、签名和描述
- **向量数据库**: 使用 ChromaDB 存储和检索向量化的 API 文档
- **HTTP API**: 提供 FastAPI 构建的 RESTful API 服务
- **CLI 工具**: 提供方便的命令行查询工具

## 快速开始

### 1. 构建项目

```bash
# 运行完整构建脚本
./build.sh
```

**注意**: 如果下载依赖较慢，可以使用清华镜像加速：

```bash
# Linux/macOS: 复制 pip 配置文件
cp pip.conf ~/.pip/pip.conf

# Windows: 复制 pip 配置文件
mkdir %APPDATA%\pip
copy pip.ini %APPDATA%\pip\pip.ini

# 或使用环境变量
export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple  # Linux/macOS
set PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple      # Windows
```

构建脚本会自动完成以下步骤：
1. 检查并安装 Python 依赖
2. 解析 Javadoc HTML 文档
3. 构建向量数据库
4. 构建 Docker 镜像
5. 导出镜像为 `sdk-kb.tar`

### 2. 部署服务

```bash
# 导入镜像
docker load -i sdk-kb.tar

# 启动容器
docker run -d \
    --name sdk-kb \
    -p 8000:8000 \
    -v $(pwd)/data:/app/data:ro \
    sdk-kb:latest
```

### 3. 使用 CLI 查询

```bash
# 使用 query-sdk 脚本（推荐）
./query-sdk "如何创建数据源"
./query-sdk "Workspace 打开方法" -t 10
./query-sdk --check

# 或使用 Python 客户端
python scripts/query_client.py "查询空间数据"
```

## 项目结构

```
.
├── build.sh                    # 完整构建脚本
├── Dockerfile                  # 多阶段 Docker 镜像构建
├── query-sdk                   # CLI 包装脚本
├── requirements.txt            # Python 依赖
│
├── scripts/                    # Python 脚本
│   ├── __init__.py
│   ├── parse_javadoc.py        # Javadoc HTML 解析器
│   ├── build_vector_db.py      # 向量数据库构建器
│   ├── api_server.py           # FastAPI HTTP 服务
│   └── query_client.py         # CLI 查询客户端
│
├── data/                       # 数据目录
│   ├── sdk_knowledge.json      # 解析后的 API 数据
│   └── chroma_db/              # ChromaDB 向量数据库
│
├── models/                     # 本地模型缓存
├── tests/                      # 测试文件
├── docs/                       # 文档目录
└── SuperMap iObjects Java Javadoc/  # Javadoc HTML 源文件
```

## 开发指南

### 环境设置

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 手动构建流程

如果不想使用 `build.sh`，可以手动执行各个步骤：

```bash
# 1. 解析 HTML
python scripts/parse_javadoc.py \
    "SuperMap iObjects Java Javadoc" \
    data/sdk_knowledge.json

# 2. 构建向量数据库
python scripts/build_vector_db.py \
    data/sdk_knowledge.json \
    data/chroma_db

# 3. 构建 Docker 镜像
docker build -t sdk-kb:latest .

# 4. 导出镜像
docker save -o sdk-kb.tar sdk-kb:latest
```

### 运行测试

```bash
# 运行所有测试
pytest

# 带覆盖率报告
pytest --cov=scripts --cov-report=html
```

### 本地运行 API 服务

```bash
# 直接运行（需要数据目录已构建）
python scripts/api_server.py

# 或使用 uvicorn
uvicorn scripts.api_server:app --host 0.0.0.0 --port 8000
```

## CLI 使用示例

### 基本查询

```bash
# 查询前 5 个结果（默认）
./query-sdk "如何创建数据源"

# 查询前 10 个结果
./query-sdk "Workspace 打开方法" -t 10

# 输出原始 JSON
./query-sdk "查询空间数据" --raw
```

### 容器管理

```bash
# 检查服务健康状态
./query-sdk --check

# 停止容器
./query-sdk --stop

# 重启容器
./query-sdk --restart
```

### 环境变量

```bash
# 自定义 API 地址
export SDK_API_URL=http://localhost:8000
./query-sdk "查询"
```

## API 端点说明

### 1. 根端点

```
GET /
```

返回 API 基本信息和可用端点列表。

**响应示例**:
```json
{
  "name": "SDK 知识库 API",
  "version": "1.0.0",
  "description": "SuperMap iObjects Java SDK 知识库语义搜索服务",
  "endpoints": [
    {"path": "/", "method": "GET", "description": "API 信息"},
    {"path": "/health", "method": "GET", "description": "健康检查"},
    {"path": "/search", "method": "POST", "description": "语义搜索"}
  ]
}
```

### 2. 健康检查

```
GET /health
```

检查服务健康状态和数据库统计信息。

**响应示例**:
```json
{
  "status": "healthy",
  "collection": "sdk_api",
  "document_count": 1234,
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

### 3. 搜索

```
POST /search
Content-Type: application/json

{
  "query": "如何创建数据源",
  "top_k": 5
}
```

**参数说明**:
- `query` (string, required): 搜索查询文本，长度 1-1000
- `top_k` (integer, optional): 返回结果数量，范围 1-20，默认 5

**响应示例**:
```json
{
  "results": [
    {
      "class": "Workspace",
      "method": "openDatasource",
      "signature": "public Datasource openDatasource(String alias, String driver, String server)",
      "description": "打开指定的数据源",
      "similarity": 0.9234
    }
  ],
  "total": 5
}
```

### 4. 交互式 API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 依赖项

### Python 包
- `beautifulsoup4>=4.12.0` - HTML 解析
- `lxml>=4.9.0` - XML/HTML 解析器
- `sentence-transformers>=2.2.0` - 文本向量化模型
- `chromadb>=0.4.0` - 向量数据库
- `fastapi>=0.104.0` - Web 框架
- `uvicorn>=0.24.0` - ASGI 服务器
- `requests>=2.31.0` - HTTP 请求
- `pydantic>=2.0.0` - 数据验证

### 系统要求
- Docker 20.10+
- Python 3.9+ (开发环境)
- 4GB+ 内存（推荐）
- 2GB+ 磁盘空间

## 许可证

MIT License

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request
