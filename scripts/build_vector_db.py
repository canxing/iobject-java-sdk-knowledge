"""
向量数据库构建器

将解析后的 API 信息转换为向量并存储到 Chroma 数据库
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class VectorDBBuilder:
    """向量数据库构建器类"""

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    DEFAULT_COLLECTION = "sdk_api"
    DEFAULT_BATCH_SIZE = 100

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        chroma_path: str = "data/chroma_db/",
        collection_name: str = DEFAULT_COLLECTION,
    ):
        """
        初始化向量数据库构建器

        Args:
            model_name: sentence-transformers 模型名称
            chroma_path: Chroma 数据库存储路径
            collection_name: 集合名称
        """
        self.model_name = model_name
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.model: SentenceTransformer | None = None
        self.client: chromadb.Client | None = None
        self.collection: chromadb.Collection | None = None

    def load_model(self) -> SentenceTransformer:
        """
        加载 sentence-transformers 模型

        Returns:
            加载的模型实例
        """
        print(f"正在加载模型: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        print(f"模型加载完成，维度: {self.model.get_sentence_embedding_dimension()}")
        return self.model

    def _init_chroma(self) -> None:
        """初始化 Chroma 客户端和集合"""
        # 确保目录存在
        os.makedirs(self.chroma_path, exist_ok=True)

        # 初始化 Chroma 客户端
        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"Chroma 集合 '{self.collection_name}' 已准备就绪")

    def generate_documents(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        从 JSON 数据生成文档

        文档格式:
        {
            "id": "com.example.Class.method",
            "text": "Class: com.example.Class\nMethod: methodName(...)\nDescription: ...",
            "metadata": {
                "class": "com.example.Class",
                "method": "methodName",
                "signature": "...",
                "package": "com.example"
            }
        }

        Args:
            data: 解析后的 API 数据列表

        Returns:
            生成的文档列表
        """
        documents = []

        for class_data in data:
            class_name = class_data.get("class", "")
            package = class_data.get("package", "")
            full_class = class_data.get("full_class", "")
            methods = class_data.get("methods", [])

            # 跳过没有方法或类名为空的条目
            if not methods or not full_class or not package:
                continue

            for idx, method in enumerate(methods):
                method_name = method.get("name", "")
                signature = method.get("signature", "")
                description = method.get("description", "")
                modifiers = method.get("modifiers", "")

                # 生成唯一 ID（包含签名以区分重载方法）
                signature_hash = hash(signature) & 0xFFFF
                doc_id = f"{full_class}.{method_name}_{signature_hash:04x}"

                # 生成文本内容
                text_parts = [
                    f"Class: {full_class}",
                    f"Method: {method_name}({signature})",
                ]
                if description:
                    text_parts.append(f"Description: {description}")

                text = "\n".join(text_parts)

                # 创建文档
                document = {
                    "id": doc_id,
                    "text": text,
                    "metadata": {
                        "class": class_name,
                        "method": method_name,
                        "signature": signature,
                        "package": package,
                        "full_class": full_class,
                        "modifiers": modifiers if modifiers else "",
                        "description": description if description else "",
                    },
                }
                documents.append(document)

        return documents

    def build(
        self,
        json_path: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> Dict[str, Any]:
        """
        构建向量数据库

        Args:
            json_path: JSON 文件路径
            batch_size: 批处理大小

        Returns:
            构建统计信息
        """
        # 加载模型
        if self.model is None:
            self.load_model()

        # 初始化 Chroma
        self._init_chroma()

        # 加载 JSON 数据
        print(f"正在加载数据: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"加载完成，共 {len(data)} 个类")

        # 生成文档
        print("正在生成文档...")
        documents = self.generate_documents(data)
        print(f"生成完成，共 {len(documents)} 个文档")

        if not documents:
            print("没有文档需要处理")
            return {"total_documents": 0, "batches": 0, "status": "no_documents"}

        # 分批处理
        total_batches = (len(documents) + batch_size - 1) // batch_size
        print(f"开始处理，批大小: {batch_size}，共 {total_batches} 批")

        for i in tqdm(range(0, len(documents), batch_size), desc="Vectorizing", total=total_batches):
            batch = documents[i : i + batch_size]

            # 提取数据
            ids = [doc["id"] for doc in batch]
            texts = [doc["text"] for doc in batch]
            metadatas = [doc["metadata"] for doc in batch]

            # 生成向量
            embeddings = self.model.encode(texts, show_progress_bar=False)

            # 添加到 Chroma
            self.collection.add(
                ids=ids,
                embeddings=embeddings.tolist(),
                metadatas=metadatas,
                documents=texts,
            )

        # 统计信息
        count = self.collection.count()
        stats = {
            "total_documents": len(documents),
            "batches": total_batches,
            "collection_count": count,
            "chroma_path": self.chroma_path,
            "collection_name": self.collection_name,
            "model": self.model_name,
            "status": "success",
        }

        print(f"\n向量数据库构建完成!")
        print(f"- 文档数: {len(documents)}")
        print(f"- 批次数: {total_batches}")
        print(f"- 集合中的文档数: {count}")
        print(f"- 存储路径: {self.chroma_path}")

        return stats

    def query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        查询向量数据库

        Args:
            query_text: 查询文本
            n_results: 返回结果数量

        Returns:
            查询结果
        """
        if self.model is None:
            raise RuntimeError("模型未加载，请先调用 load_model()")

        if self.collection is None:
            raise RuntimeError("集合未初始化，请先调用 build()")

        # 生成查询向量
        query_embedding = self.model.encode([query_text])

        # 查询
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results,
        )

        return results


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="构建 SDK 知识库向量数据库")
    parser.add_argument(
        "--input",
        type=str,
        default="data/parsed_javadoc.json",
        help="输入 JSON 文件路径",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/chroma_db/",
        help="输出 Chroma 数据库路径",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="sentence-transformers 模型名称",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="sdk_api",
        help="Chroma 集合名称",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="批处理大小",
    )

    args = parser.parse_args()

    builder = VectorDBBuilder(
        model_name=args.model,
        chroma_path=args.output,
        collection_name=args.collection,
    )

    builder.build(args.input, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
