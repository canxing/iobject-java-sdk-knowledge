"""
SDK 知识库 API 服务

FastAPI HTTP 服务，提供搜索端点
"""

import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sentence_transformers import SentenceTransformer


# 配置
DEFAULT_CHROMA_PATH = "data/chroma_db"
DEFAULT_MODEL_PATH = "models"
DEFAULT_COLLECTION_NAME = "sdk_api"
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CHROMA_PATH = os.getenv("CHROMA_PATH", DEFAULT_CHROMA_PATH)
MODEL_PATH = os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
COLLECTION_NAME = os.getenv("COLLECTION_NAME", DEFAULT_COLLECTION_NAME)
MODEL_NAME = os.getenv("MODEL_NAME", DEFAULT_MODEL_NAME)

# 全局状态
global_state: Dict[str, Any] = {
    "model": None,
    "client": None,
    "collection": None,
    "initialized": False,
}


# 请求和响应模型
class SearchRequest(BaseModel):
    """搜索请求"""

    query: str = Field(..., description="搜索查询文本", min_length=1, max_length=1000)
    top_k: int = Field(5, description="返回结果数量", ge=1, le=20)


class SearchResult(BaseModel):
    """搜索结果项"""

    model_config = ConfigDict(populate_by_name=True)

    class_: str = Field(..., alias="class", description="类名")
    method: str = Field(..., description="方法名")
    signature: str = Field(..., description="方法签名")
    description: str = Field(..., description="方法描述")
    similarity: float = Field(..., description="相似度分数 (0-1)")


class SearchResponse(BaseModel):
    """搜索响应"""

    results: List[SearchResult] = Field(..., description="搜索结果列表")
    total: int = Field(..., description="返回结果数量")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="服务状态")
    collection: str = Field(..., description="集合名称")
    document_count: int = Field(..., description="文档总数")
    model: str = Field(..., description="模型名称")


class APIInfo(BaseModel):
    """API 信息"""

    name: str = Field(..., description="API 名称")
    version: str = Field(..., description="API 版本")
    description: str = Field(..., description="API 描述")
    endpoints: List[Dict[str, str]] = Field(..., description="可用端点列表")


def load_model() -> SentenceTransformer:
    """加载 sentence-transformers 模型"""
    print(f"正在加载模型: {MODEL_NAME}")

    # 检查本地模型路径
    local_model_path = os.path.join(MODEL_PATH, os.path.basename(MODEL_NAME))
    if os.path.exists(local_model_path):
        model_path = local_model_path
        print(f"使用本地模型: {model_path}")
    else:
        model_path = MODEL_NAME
        print(f"使用远程模型: {model_path}")

    model = SentenceTransformer(model_path)
    print(f"模型加载完成，维度: {model.get_sentence_embedding_dimension()}")
    return model


def init_chroma() -> tuple[chromadb.Client, chromadb.Collection]:
    """初始化 Chroma 客户端和集合"""
    print(f"正在初始化 Chroma 数据库: {CHROMA_PATH}")

    if not os.path.exists(CHROMA_PATH):
        raise RuntimeError(f"Chroma 数据库路径不存在: {CHROMA_PATH}")

    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False),
    )

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        print(f"Chroma 集合 '{COLLECTION_NAME}' 已加载，文档数: {collection.count()}")
    except Exception as e:
        raise RuntimeError(f"无法获取集合 '{COLLECTION_NAME}': {e}")

    return client, collection


def init_services():
    """初始化服务"""
    if global_state["initialized"]:
        return

    # 加载模型
    global_state["model"] = load_model()

    # 初始化 Chroma
    client, collection = init_chroma()
    global_state["client"] = client
    global_state["collection"] = collection
    global_state["initialized"] = True

    print("服务初始化完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    print("正在启动服务...")
    try:
        init_services()
        print("服务启动成功")
    except Exception as e:
        print(f"服务启动失败: {e}")
        raise

    yield

    # 关闭时清理
    print("正在关闭服务...")
    global_state.clear()


# 创建 FastAPI 应用
app = FastAPI(
    title="SDK 知识库 API",
    description="SuperMap iObjects Java SDK 知识库搜索服务",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", response_model=APIInfo)
async def root():
    """
    根端点，返回 API 信息
    """
    return APIInfo(
        name="SDK 知识库 API",
        version="1.0.0",
        description="SuperMap iObjects Java SDK 知识库语义搜索服务",
        endpoints=[
            {"path": "/", "method": "GET", "description": "API 信息"},
            {"path": "/health", "method": "GET", "description": "健康检查"},
            {"path": "/search", "method": "POST", "description": "语义搜索"},
        ],
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """
    健康检查端点
    """
    if not global_state["initialized"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务未初始化完成",
        )

    collection = global_state["collection"]
    count = collection.count() if collection else 0

    return HealthResponse(
        status="healthy",
        collection=COLLECTION_NAME,
        document_count=count,
        model=MODEL_NAME,
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    搜索端点

    根据查询文本进行语义搜索，返回最相关的 API 方法
    """
    if not global_state["initialized"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务未初始化完成",
        )

    model = global_state["model"]
    collection = global_state["collection"]

    # 生成查询向量
    try:
        query_embedding = model.encode([request.query])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询编码失败: {str(e)}",
        )

    # 查询向量数据库
    try:
        results = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=request.top_k,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}",
        )

    # 格式化结果
    search_results = []
    if results["ids"] and len(results["ids"]) > 0:
        ids = results["ids"][0]
        distances = results["distances"][0] if results["distances"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []

        for i, doc_id in enumerate(ids):
            metadata = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 0.0

            # 将距离转换为相似度 (余弦距离 -> 余弦相似度)
            similarity = 1.0 - float(distance)

            search_results.append(
                SearchResult(
                    class_=metadata.get("class", ""),
                    method=metadata.get("method", ""),
                    signature=metadata.get("signature", ""),
                    description=metadata.get("description", ""),
                    similarity=round(similarity, 4),
                )
            )

    return SearchResponse(
        results=search_results,
        total=len(search_results),
    )


def main():
    """命令行入口"""
    import uvicorn

    # 使用文件路径方式启动，避免模块导入问题
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
