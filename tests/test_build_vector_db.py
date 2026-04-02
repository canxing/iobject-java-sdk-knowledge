"""
测试向量数据库构建器
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from scripts.build_vector_db import VectorDBBuilder


@pytest.fixture
def sample_data():
    """示例 API 数据"""
    return [
        {
            "class": "AgencyS57",
            "package": "com.supermap.chart",
            "full_class": "com.supermap.chart.AgencyS57",
            "file": "com/supermap/chart/AgencyS57.html",
            "methods": [
                {
                    "name": "dispose",
                    "signature": "void dispose()",
                    "modifiers": None,
                    "description": "释放 AgencyS57 对象所占用的本地资源。",
                },
                {
                    "name": "getAgencyName",
                    "signature": "String getAgencyName()",
                    "modifiers": None,
                    "description": "返回机构名称。",
                },
            ],
        },
        {
            "class": "DatasetVector",
            "package": "com.supermap.data",
            "full_class": "com.supermap.data.DatasetVector",
            "file": "com/supermap/data/DatasetVector.html",
            "methods": [
                {
                    "name": "query",
                    "signature": "Recordset query(QueryParameter parameter)",
                    "modifiers": None,
                    "description": "根据查询条件进行空间查询。",
                },
            ],
        },
    ]


@pytest.fixture
def temp_json_file(sample_data):
    """临时 JSON 文件"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
        temp_path = f.name

    yield temp_path

    # 清理
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_chroma_path():
    """临时 Chroma 数据库路径"""
    temp_dir = tempfile.mkdtemp()
    chroma_path = os.path.join(temp_dir, "chroma_db")

    yield chroma_path

    # 清理 - 忽略 Windows 上的文件锁定错误
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass  # 忽略清理错误


class TestVectorDBBuilder:
    """测试 VectorDBBuilder 类"""

    def test_init(self):
        """测试初始化"""
        builder = VectorDBBuilder(
            model_name="test-model",
            chroma_path="/tmp/chroma",
            collection_name="test_collection",
        )

        assert builder.model_name == "test-model"
        assert builder.chroma_path == "/tmp/chroma"
        assert builder.collection_name == "test_collection"
        assert builder.model is None
        assert builder.client is None
        assert builder.collection is None

    def test_init_defaults(self):
        """测试默认参数初始化"""
        builder = VectorDBBuilder()

        assert builder.model_name == VectorDBBuilder.DEFAULT_MODEL
        assert builder.chroma_path == "data/chroma_db/"
        assert builder.collection_name == VectorDBBuilder.DEFAULT_COLLECTION

    def test_generate_documents(self, sample_data):
        """测试文档生成"""
        builder = VectorDBBuilder()
        documents = builder.generate_documents(sample_data)

        assert len(documents) == 3  # 2 + 1 = 3 个方法

        # 检查第一个文档 - ID 包含签名哈希
        doc = documents[0]
        assert doc["id"].startswith("com.supermap.chart.AgencyS57.dispose_")
        assert "Class: com.supermap.chart.AgencyS57" in doc["text"]
        assert "Method: dispose(void dispose())" in doc["text"]
        assert "释放 AgencyS57 对象所占用的本地资源。" in doc["text"]

        # 检查 metadata
        assert doc["metadata"]["class"] == "AgencyS57"
        assert doc["metadata"]["method"] == "dispose"
        assert doc["metadata"]["package"] == "com.supermap.chart"
        assert doc["metadata"]["full_class"] == "com.supermap.chart.AgencyS57"
        assert doc["metadata"]["signature"] == "void dispose()"

    def test_generate_documents_skips_empty_methods(self, sample_data):
        """测试跳过空方法列表"""
        # 添加一个没有方法的类
        sample_data.append(
            {
                "class": "EmptyClass",
                "package": "com.test",
                "full_class": "com.test.EmptyClass",
                "file": "com/test/EmptyClass.html",
                "methods": [],
            }
        )

        builder = VectorDBBuilder()
        documents = builder.generate_documents(sample_data)

        # 仍然是 3 个，因为空类被跳过
        assert len(documents) == 3

    def test_generate_documents_skips_empty_package(self):
        """测试跳过空 package"""
        data = [
            {
                "class": "AllClasses",
                "package": None,
                "full_class": None,
                "file": "allclasses.html",
                "methods": [],
            }
        ]

        builder = VectorDBBuilder()
        documents = builder.generate_documents(data)

        assert len(documents) == 0

    @pytest.mark.slow
    def test_load_model(self):
        """测试模型加载"""
        builder = VectorDBBuilder()
        model = builder.load_model()

        assert model is not None
        assert builder.model is not None
        assert builder.model.get_sentence_embedding_dimension() > 0

    @pytest.mark.slow
    def test_build(self, temp_json_file, temp_chroma_path):
        """测试完整构建流程"""
        builder = VectorDBBuilder(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            chroma_path=temp_chroma_path,
            collection_name="test_api",
        )

        stats = builder.build(temp_json_file, batch_size=10)

        assert stats["status"] == "success"
        assert stats["total_documents"] == 3
        assert stats["batches"] == 1
        assert stats["collection_count"] == 3
        assert stats["model"] == "sentence-transformers/all-MiniLM-L6-v2"

        # 验证数据库文件已创建
        assert os.path.exists(temp_chroma_path)

    @pytest.mark.slow
    def test_query(self, temp_json_file, temp_chroma_path):
        """测试查询功能"""
        builder = VectorDBBuilder(
            chroma_path=temp_chroma_path,
            collection_name="test_query",
        )

        builder.build(temp_json_file, batch_size=10)

        # 查询
        results = builder.query("释放资源", n_results=2)

        assert "ids" in results
        assert "distances" in results
        assert "metadatas" in results
        assert len(results["ids"][0]) <= 2

    def test_build_empty_data(self, temp_chroma_path):
        """测试空数据构建"""
        # 创建空数据文件
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump([], f)
            empty_file = f.name

        try:
            builder = VectorDBBuilder(
                chroma_path=temp_chroma_path,
                collection_name="empty_test",
            )

            stats = builder.build(empty_file, batch_size=10)

            assert stats["status"] == "no_documents"
            assert stats["total_documents"] == 0
        finally:
            os.unlink(empty_file)

    @pytest.mark.slow
    def test_batch_processing(self, temp_chroma_path):
        """测试批处理"""
        # 创建大量数据
        large_data = []
        for i in range(25):
            large_data.append(
                {
                    "class": f"TestClass{i}",
                    "package": "com.test",
                    "full_class": f"com.test.TestClass{i}",
                    "file": f"TestClass{i}.html",
                    "methods": [
                        {"name": f"method{j}", "signature": "void method()", "modifiers": None, "description": f"Description {i}-{j}"}
                        for j in range(2)
                    ],
                }
            )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(large_data, f)
            large_file = f.name

        try:
            builder = VectorDBBuilder(
                chroma_path=temp_chroma_path,
                collection_name="batch_test",
            )

            stats = builder.build(large_file, batch_size=10)

            # 25 个类，每个 2 个方法 = 50 个文档
            assert stats["total_documents"] == 50
            # 批大小 10，需要 5 批
            assert stats["batches"] == 5
        finally:
            os.unlink(large_file)
