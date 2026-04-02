"""
测试 API 服务

使用 FastAPI TestClient 进行测试
"""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# 确保导入路径正确
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.api_server import (
    APIInfo,
    HealthResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    app,
)

# 创建测试客户端
client = TestClient(app)


class TestRootEndpoint:
    """测试根端点"""

    def test_root_returns_api_info(self):
        """测试根端点返回 API 信息"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "SDK 知识库 API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert len(data["endpoints"]) == 3

    def test_root_endpoints_structure(self):
        """测试端点列表结构"""
        response = client.get("/")
        data = response.json()

        endpoints = data["endpoints"]
        paths = [ep["path"] for ep in endpoints]

        assert "/" in paths
        assert "/health" in paths
        assert "/search" in paths


class TestHealthEndpoint:
    """测试健康检查端点"""

    def test_health_uninitialized(self):
        """测试服务未初始化时的健康检查"""
        # 注意：这依赖于全局状态
        # 在实际测试中可能需要 mock
        response = client.get("/health")

        # 如果服务未初始化，应该返回 503
        # 如果已初始化，应该返回 200
        assert response.status_code in [200, 503]

    def test_health_response_structure(self):
        """测试健康检查响应结构"""
        response = client.get("/health")

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "collection" in data
            assert "document_count" in data
            assert "model" in data
            assert data["status"] == "healthy"


class TestSearchEndpoint:
    """测试搜索端点"""

    def test_search_missing_body(self):
        """测试缺少请求体"""
        response = client.post("/search", json={})

        # 应该返回 422 验证错误
        assert response.status_code == 422

    def test_search_empty_query(self):
        """测试空查询字符串"""
        response = client.post("/search", json={"query": ""})

        assert response.status_code == 422

    def test_search_invalid_top_k(self):
        """测试无效的 top_k"""
        response = client.post("/search", json={"query": "test", "top_k": 0})

        assert response.status_code == 422

    def test_search_top_k_too_large(self):
        """测试过大的 top_k"""
        response = client.post("/search", json={"query": "test", "top_k": 100})

        assert response.status_code == 422

    def test_search_valid_request(self):
        """测试有效的搜索请求"""
        # 注意：这个测试需要服务已初始化
        response = client.post("/search", json={"query": "查询空间数据", "top_k": 3})

        # 如果服务未初始化，返回 503
        # 如果已初始化，返回 200
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "results" in data
            assert "total" in data
            assert isinstance(data["results"], list)
            assert isinstance(data["total"], int)


class TestSearchModels:
    """测试 Pydantic 模型"""

    def test_search_request_defaults(self):
        """测试搜索请求默认值"""
        request = SearchRequest(query="test query")

        assert request.query == "test query"
        assert request.top_k == 5  # 默认值

    def test_search_request_custom_top_k(self):
        """测试自定义 top_k"""
        request = SearchRequest(query="test query", top_k=10)

        assert request.top_k == 10

    def test_search_result_model(self):
        """测试搜索结果模型"""
        result = SearchResult(
            **{
                "class": "DatasetVector",
                "method": "query",
                "signature": "Recordset query(QueryParameter parameter)",
                "description": "根据查询条件进行空间查询。",
                "similarity": 0.95,
            }
        )

        assert result.class_ == "DatasetVector"
        assert result.method == "query"
        assert result.similarity == 0.95

    def test_search_response_model(self):
        """测试搜索响应模型"""
        results = [
            SearchResult(
                **{
                    "class": "TestClass",
                    "method": "testMethod",
                    "signature": "void testMethod()",
                    "description": "测试方法",
                    "similarity": 0.9,
                }
            )
        ]

        response = SearchResponse(results=results, total=1)

        assert len(response.results) == 1
        assert response.total == 1
        assert response.results[0].class_ == "TestClass"


class TestEnvironmentVariables:
    """测试环境变量配置"""

    def test_default_chroma_path(self):
        """测试默认 Chroma 路径"""
        from scripts.api_server import DEFAULT_CHROMA_PATH

        assert DEFAULT_CHROMA_PATH == "data/chroma_db"

    def test_default_collection_name(self):
        """测试默认集合名称"""
        from scripts.api_server import DEFAULT_COLLECTION_NAME

        assert DEFAULT_COLLECTION_NAME == "sdk_api"

    def test_default_model_name(self):
        """测试默认模型名称"""
        from scripts.api_server import DEFAULT_MODEL_NAME

        assert DEFAULT_MODEL_NAME == "sentence-transformers/all-MiniLM-L6-v2"


class TestAPIInfoModel:
    """测试 API 信息模型"""

    def test_api_info_creation(self):
        """测试创建 API 信息"""
        info = APIInfo(
            name="Test API",
            version="1.0.0",
            description="Test description",
            endpoints=[{"path": "/test", "method": "GET", "description": "Test"}],
        )

        assert info.name == "Test API"
        assert info.version == "1.0.0"
        assert len(info.endpoints) == 1


class TestHealthResponseModel:
    """测试健康响应模型"""

    def test_health_response_creation(self):
        """测试创建健康响应"""
        response = HealthResponse(
            status="healthy",
            collection="test_collection",
            document_count=100,
            model="test-model",
        )

        assert response.status == "healthy"
        assert response.document_count == 100


class TestErrorHandling:
    """测试错误处理"""

    def test_404_error(self):
        """测试 404 错误"""
        response = client.get("/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed(self):
        """测试方法不允许"""
        response = client.get("/search")  # GET 不被允许

        assert response.status_code == 405
