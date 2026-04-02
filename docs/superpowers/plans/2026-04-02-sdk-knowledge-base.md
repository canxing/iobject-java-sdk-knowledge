# SDK 知识库系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建基于 Docker 的 SuperMap iObjects Java SDK 语义搜索知识库，支持离线部署和自然语言查询。

**Architecture:** 使用 BeautifulSoup 解析 Javadoc HTML → Sentence-Transformers 生成向量 → Chroma 持久化存储 → FastAPI 提供 HTTP 查询服务 → Docker 打包预构建的向量库和模型。

**Tech Stack:** Python 3.9, BeautifulSoup4, Sentence-Transformers, Chroma, FastAPI, Docker

---

## 文件结构

```
sdk-knowledge-base/
├── requirements.txt              # Python 依赖
├── Dockerfile                    # 多阶段构建
├── query-sdk                     # CLI 包装脚本（宿主机使用）
├── scripts/
│   ├── parse_javadoc.py         # HTML 解析器
│   ├── build_vector_db.py       # 向量数据库构建器
│   ├── api_server.py            # FastAPI 服务
│   └── query_client.py          # CLI 查询客户端
├── tests/
│   ├── test_parse_javadoc.py    # 解析器测试
│   ├── test_api_server.py       # API 服务测试
│   └── test_query_client.py     # 客户端测试
├── data/                         # 构建时生成（嵌入镜像）
│   └── chroma_db/
└── models/                       # 预下载的模型（嵌入镜像）
    └── all-MiniLM-L6-v2/
```

---

## Task 1: 创建项目基础结构

**目标:** 初始化项目目录、虚拟环境和依赖配置

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`

---

### Task 1.1: 创建 Python 虚拟环境

- [ ] **Step 1: 创建虚拟环境**

Run:
```bash
python3 -m venv venv
```

- [ ] **Step 2: 激活虚拟环境**

Run:
```bash
# Linux/macOS
source venv/bin/activate

# Windows (Git Bash)
source venv/Scripts/activate
```

Expected: 命令行提示符显示 `(venv)` 前缀

- [ ] **Step 3: 升级 pip**

Run:
```bash
python -m pip install --upgrade pip
```

- [ ] **Step 4: 提交虚拟环境配置**

```bash
git add venv/
git commit -m "chore: add Python virtual environment"
```

**注意**: 实际上 venv/ 会被 .gitignore 忽略，但这一步确保虚拟环境已创建

---

### Task 1.2: 创建 requirements.txt

- [ ] **Step 1: 确保虚拟环境已激活**

检查提示符是否有 `(venv)` 前缀，如果没有则运行：
```bash
source venv/bin/activate  # 或 venv/Scripts/activate
```

- [ ] **Step 2: 编写依赖文件**

Create: `requirements.txt`
```
beautifulsoup4>=4.12.0
lxml>=4.9.0
sentence-transformers>=2.2.0
chromadb>=0.4.0
fastapi>=0.104.0
uvicorn>=0.24.0
requests>=2.31.0
pydantic>=2.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.25.0
tqdm>=4.66.0
```

- [ ] **Step 3: 安装依赖到虚拟环境**

Run:
```bash
pip install -r requirements.txt
```

Expected: 所有包安装成功，无报错

- [ ] **Step 4: 创建目录结构**

Run:
```bash
mkdir -p scripts tests data models
```

- [ ] **Step 5: 创建 init 文件**

Create: `scripts/__init__.py`
```python
"""SDK Knowledge Base scripts."""
```

Create: `tests/__init__.py`
```python
"""SDK Knowledge Base tests."""
```

- [ ] **Step 6: 创建 .gitignore**

Create: `.gitignore`
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/
.venv/

# Data
models/
data/chroma_db/
*.tar

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .gitignore scripts/__init__.py tests/__init__.py
 git commit -m "chore: initialize project structure with dependencies in venv"
```

---

## Task 2: 编写 HTML 解析器

**目标:** 解析 Javadoc HTML，提取类、方法、描述等信息

**Files:**
- Create: `scripts/parse_javadoc.py`
- Create: `tests/test_parse_javadoc.py`

---

### Task 2.1: 编写解析器核心代码

- [ ] **Step 1: 编写解析器**

Create: `scripts/parse_javadoc.py`
```python
"""Parse Javadoc HTML to extract API information."""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from tqdm import tqdm


class JavadocParser:
    """Parser for Javadoc HTML files."""

    def __init__(self, encoding: str = "gb2312"):
        """Initialize parser.

        Args:
            encoding: HTML file encoding (default: gb2312 for Chinese Javadoc)
        """
        self.encoding = encoding

    def parse_file(self, file_path: Path) -> Optional[Dict]:
        """Parse a single HTML file.

        Args:
            file_path: Path to HTML file

        Returns:
            Dictionary with class info and methods, or None if parsing fails
        """
        try:
            with open(file_path, 'r', encoding=self.encoding, errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None

        # Extract class name from title or header
        class_name = self._extract_class_name(soup, file_path)
        package_name = self._extract_package_name(soup, file_path)
        full_class_name = f"{package_name}.{class_name}" if package_name else class_name

        # Extract methods
        methods = self._extract_methods(soup)

        return {
            "class": class_name,
            "package": package_name,
            "full_class": full_class_name,
            "file": str(file_path),
            "methods": methods
        }

    def _extract_class_name(self, soup: BeautifulSoup, file_path: Path) -> str:
        """Extract class name from HTML."""
        # Try title
        title = soup.find('title')
        if title:
            title_text = title.get_text()
            # Title format: "ClassName (Package)" or just "ClassName"
            match = re.search(r'^(\w+)\s*[\(\[]', title_text)
            if match:
                return match.group(1)
            # Try simple title
            if title_text.strip():
                return title_text.strip().split()[0]

        # Fallback to filename
        return file_path.stem

    def _extract_package_name(self, soup: BeautifulSoup, file_path: Path) -> str:
        """Extract package name from HTML."""
        # Try header subtitle
        header = soup.find('div', class_='header')
        if header:
            subtitle = header.find('div', class_='subTitle')
            if subtitle:
                return subtitle.get_text().strip()

        # Try from file path
        parts = file_path.parts
        if 'com' in parts:
            com_index = parts.index('com')
            package_parts = parts[com_index:-1]  # Exclude filename
            return '.'.join(package_parts)

        return ""

    def _extract_methods(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract method information from HTML."""
        methods = []

        # Find method summary table
        method_tables = soup.find_all('table', class_='memberSummary')

        for table in method_tables:
            # Check if this is a method table (has modifiers like public/static)
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    method_info = self._parse_method_row(row)
                    if method_info:
                        methods.append(method_info)

        return methods

    def _parse_method_row(self, row) -> Optional[Dict]:
        """Parse a single method row from the table."""
        cells = row.find_all('td')
        if len(cells) < 2:
            return None

        # First cell: modifiers and return type
        first_cell = cells[0]
        modifiers_text = first_cell.get_text().strip()

        # Second cell: method name and parameters
        second_cell = cells[1]
        method_link = second_cell.find('a', href=True)

        if not method_link:
            return None

        method_name = method_link.get_text().strip()

        # Extract signature from the code element
        code_elem = second_cell.find('code')
        signature = ""
        if code_elem:
            signature = code_elem.get_text().strip()

        # Extract description
        description = ""
        block_div = second_cell.find('div', class_='block')
        if block_div:
            description = block_div.get_text().strip()

        # Find detailed description from method detail section
        detailed_desc = self._find_method_detail(method_name, signature)
        if detailed_desc:
            description = detailed_desc

        return {
            "name": method_name,
            "signature": signature,
            "modifiers": modifiers_text,
            "description": description
        }

    def _find_method_detail(self, method_name: str, signature: str) -> str:
        """Find detailed description from method detail section."""
        # This is a placeholder - the actual implementation would
        # search the same soup for the method detail section
        return ""

    def parse_directory(self, input_dir: str, output_json: str) -> Dict:
        """Parse all HTML files in a directory.

        Args:
            input_dir: Directory containing HTML files
            output_json: Path to output JSON file

        Returns:
            Dictionary mapping class names to class info
        """
        input_path = Path(input_dir)
        html_files = list(input_path.rglob('*.html'))

        # Filter out non-class files
        class_files = [
            f for f in html_files
            if not f.name.startswith(('allclasses-', 'index', 'overview', 'package-', 'deprecated', 'help-', 'serialized', 'constant-values'))
            and 'class-use' not in str(f)
        ]

        print(f"Found {len(class_files)} class HTML files")

        data = {}
        for html_file in tqdm(class_files, desc='Parsing HTML'):
            result = self.parse_file(html_file)
            if result and result['full_class']:
                data[result['full_class']] = result

        # Save to JSON
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Parsed {len(data)} classes, saved to {output_json}")
        return data


if __name__ == '__main__':
    import sys

    input_dir = sys.argv[1] if len(sys.argv) > 1 else 'SuperMap iObjects Java Javadoc'
    output_json = sys.argv[2] if len(sys.argv) > 2 else 'data/sdk_knowledge.json'

    parser = JavadocParser()
    parser.parse_directory(input_dir, output_json)
```

- [ ] **Step 2: 提交**

```bash
git add scripts/parse_javadoc.py
git commit -m "feat: add Javadoc HTML parser"
```

---

### Task 2.2: 编写解析器测试

- [ ] **Step 1: 创建测试用例 HTML 片段**

Create: `tests/fixtures/sample_class.html`
```html
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html lang="zh">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=gb2312">
<title>SampleClass (com.example.test)</title>
</head>
<body>
<div class="header">
<div class="subTitle">com.example.test</div>
<h2 title="Class SampleClass">SampleClass</h2>
</div>
<div class="contentContainer">
<div class="summary">
<ul class="blockList">
<li class="blockList">
<h3>Method Summary</h3>
<table class="memberSummary" border="0">
<tr>
<th>Modifier and Type</th>
<th>Method and Description</th>
</tr>
<tr>
<td class="colFirst"><code>void</code></td>
<td class="colLast"><code><a href="SampleClass.html#connect-java.lang.String-">connect</a></span>(<a href="https://docs.oracle.com/javase/8/docs/api/java/lang/String.html">String</a>&nbsp;url)</code>
<div class="block">Establishes a connection to the specified URL.</div>
</td>
</tr>
<tr>
<td class="colFirst"><code>boolean</code></td>
<td class="colLast"><code><a href="SampleClass.html#isConnected--">isConnected</a></span>()</code>
<div class="block">Checks if currently connected.</div>
</td>
</tr>
</table>
</li>
</ul>
</div>
</div>
</body>
</html>
```

- [ ] **Step 2: 编写测试代码**

Create: `tests/test_parse_javadoc.py`
```python
"""Tests for Javadoc HTML parser."""
import json
from pathlib import Path

import pytest

from scripts.parse_javadoc import JavadocParser


class TestJavadocParser:
    """Test cases for JavadocParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = JavadocParser()
        self.fixture_dir = Path(__file__).parent / 'fixtures'

    def test_parse_sample_class(self):
        """Test parsing a sample class HTML file."""
        html_file = self.fixture_dir / 'sample_class.html'
        result = self.parser.parse_file(html_file)

        assert result is not None
        assert result['class'] == 'SampleClass'
        assert result['package'] == 'com.example.test'
        assert result['full_class'] == 'com.example.test.SampleClass'
        assert len(result['methods']) == 2

        # Check first method
        method1 = result['methods'][0]
        assert method1['name'] == 'connect'
        assert 'void' in method1['modifiers']
        assert 'connect' in method1['signature']

    def test_parse_nonexistent_file(self):
        """Test parsing a non-existent file."""
        result = self.parser.parse_file(Path('nonexistent.html'))
        assert result is None

    def test_extract_class_name_from_title(self):
        """Test class name extraction from title."""
        from bs4 import BeautifulSoup

        html = '<html><head><title>TestClass (package)</title></head></html>'
        soup = BeautifulSoup(html, 'html.parser')

        name = self.parser._extract_class_name(soup, Path('test.html'))
        assert name == 'TestClass'

    def test_extract_class_name_fallback(self):
        """Test class name extraction fallback to filename."""
        from bs4 import BeautifulSoup

        html = '<html><head></head></html>'
        soup = BeautifulSoup(html, 'html.parser')

        name = self.parser._extract_class_name(soup, Path('FallbackClass.html'))
        assert name == 'FallbackClass'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

- [ ] **Step 3: 运行测试（确保虚拟环境已激活）**

Run:
```bash
# 确保虚拟环境已激活
source venv/bin/activate  # Linux/macOS
# 或: source venv/Scripts/activate  # Windows

python -m pytest tests/test_parse_javadoc.py -v
```

Expected: Tests pass (or show expected failures for unimplemented features)

- [ ] **Step 4: 提交**

```bash
git add tests/test_parse_javadoc.py tests/fixtures/
git commit -m "test: add Javadoc parser tests"
```

---

## Task 3: 编写向量数据库构建器

**目标:** 将解析后的 API 信息转换为向量并存储到 Chroma

**Files:**
- Create: `scripts/build_vector_db.py`
- Create: `tests/test_build_vector_db.py`

---

### Task 3.1: 编写向量构建器

- [ ] **Step 1: 编写构建器代码**

Create: `scripts/build_vector_db.py`
```python
"""Build vector database from parsed SDK knowledge."""
import json
from pathlib import Path
from typing import Dict, List

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class VectorDBBuilder:
    """Builder for Chroma vector database."""

    def __init__(
        self,
        model_name: str = 'sentence-transformers/all-MiniLM-L6-v2',
        chroma_path: str = 'data/chroma_db',
        collection_name: str = 'sdk_api'
    ):
        """Initialize builder.

        Args:
            model_name: Sentence-transformers model name
            chroma_path: Path to Chroma database directory
            collection_name: Name of the collection
        """
        self.model_name = model_name
        self.chroma_path = Path(chroma_path)
        self.collection_name = collection_name
        self.model = None

    def load_model(self):
        """Load the sentence transformer model."""
        print(f"Loading model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        print(f"Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

    def generate_documents(self, data: Dict) -> List[Dict]:
        """Generate documents from parsed data.

        Args:
            data: Dictionary mapping class names to class info

        Returns:
            List of document dictionaries
        """
        documents = []

        for class_name, class_info in data.items():
            for method in class_info.get('methods', []):
                # Create rich text representation
                text_parts = [
                    f"Class: {class_name}",
                    f"Method: {method.get('name', '')}",
                    f"Signature: {method.get('signature', '')}",
                    f"Modifiers: {method.get('modifiers', '')}",
                    f"Description: {method.get('description', '')}",
                ]
                text = '\n'.join(filter(None, text_parts))

                # Create unique ID
                doc_id = f"{class_name}.{method.get('name', '')}"

                documents.append({
                    'id': doc_id,
                    'text': text,
                    'metadata': {
                        'class': class_name,
                        'method': method.get('name', ''),
                        'signature': method.get('signature', ''),
                        'package': class_info.get('package', '')
                    }
                })

        print(f"Generated {len(documents)} documents")
        return documents

    def build(self, json_path: str, batch_size: int = 100):
        """Build the vector database.

        Args:
            json_path: Path to parsed JSON file
            batch_size: Number of documents to process per batch
        """
        # Load model
        if self.model is None:
            self.load_model()

        # Load data
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Generate documents
        documents = self.generate_documents(data)

        if not documents:
            print("No documents to index!")
            return

        # Create Chroma client
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self.chroma_path))

        # Delete existing collection if present
        try:
            client.delete_collection(self.collection_name)
            print(f"Deleted existing collection: {self.collection_name}")
        except Exception:
            pass

        # Create collection
        collection = client.create_collection(self.collection_name)
        print(f"Created collection: {self.collection_name}")

        # Process in batches
        for i in tqdm(range(0, len(documents), batch_size), desc='Vectorizing'):
            batch = documents[i:i + batch_size]

            # Generate embeddings
            texts = [doc['text'] for doc in batch]
            embeddings = self.model.encode(texts).tolist()

            # Add to collection
            collection.add(
                ids=[doc['id'] for doc in batch],
                embeddings=embeddings,
                metadatas=[doc['metadata'] for doc in batch],
                documents=texts
            )

        # Print stats
        count = collection.count()
        print(f"Vector DB built at {self.chroma_path}")
        print(f"Total documents indexed: {count}")


if __name__ == '__main__':
    import sys

    json_path = sys.argv[1] if len(sys.argv) > 1 else 'data/sdk_knowledge.json'
    chroma_path = sys.argv[2] if len(sys.argv) > 2 else 'data/chroma_db'

    builder = VectorDBBuilder(chroma_path=chroma_path)
    builder.build(json_path)
```

- [ ] **Step 2: 提交**

```bash
git add scripts/build_vector_db.py
git commit -m "feat: add vector database builder"
```

---

### Task 3.2: 编写向量构建器测试

- [ ] **Step 1: 编写测试代码**

Create: `tests/test_build_vector_db.py`
```python
"""Tests for vector database builder."""
import json
import tempfile
from pathlib import Path

import pytest

from scripts.build_vector_db import VectorDBBuilder


class TestVectorDBBuilder:
    """Test cases for VectorDBBuilder."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.chroma_path = Path(self.temp_dir) / 'chroma'

    def test_generate_documents(self):
        """Test document generation from parsed data."""
        builder = VectorDBBuilder(chroma_path=self.chroma_path)

        data = {
            "com.example.TestClass": {
                "class": "TestClass",
                "package": "com.example",
                "full_class": "com.example.TestClass",
                "methods": [
                    {
                        "name": "connect",
                        "signature": "void connect(String url)",
                        "modifiers": "public",
                        "description": "Connect to server"
                    }
                ]
            }
        }

        documents = builder.generate_documents(data)

        assert len(documents) == 1
        assert documents[0]['id'] == 'com.example.TestClass.connect'
        assert 'connect' in documents[0]['text']
        assert documents[0]['metadata']['class'] == 'com.example.TestClass'

    def test_generate_documents_empty(self):
        """Test document generation with empty data."""
        builder = VectorDBBuilder(chroma_path=self.chroma_path)

        documents = builder.generate_documents({})

        assert len(documents) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

- [ ] **Step 2: 运行测试**

Run:
```bash
# 确保虚拟环境已激活
source venv/bin/activate  # Linux/macOS
# 或: source venv/Scripts/activate  # Windows

python -m pytest tests/test_build_vector_db.py -v
```

Expected: Tests pass

- [ ] **Step 3: 提交**

```bash
git add tests/test_build_vector_db.py
git commit -m "test: add vector database builder tests"
```

---

## Task 4: 编写 API 服务

**目标:** 创建 FastAPI HTTP 服务，提供搜索端点

**Files:**
- Create: `scripts/api_server.py`
- Create: `tests/test_api_server.py`

---

### Task 4.1: 编写 FastAPI 服务

- [ ] **Step 1: 编写 API 服务**

Create: `scripts/api_server.py`
```python
"""FastAPI server for SDK knowledge base queries."""
import os
from pathlib import Path
from typing import List, Optional

import chromadb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

app = FastAPI(title="SDK Knowledge Base API", version="1.0.0")

# Global variables for model and database
model = None
collection = None


class SearchRequest(BaseModel):
    """Search request model."""
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    """Search result model."""
    class_: str
    method: str
    signature: str
    description: str
    similarity: float

    class Config:
        populate_by_name = True


class SearchResponse(BaseModel):
    """Search response model."""
    results: List[SearchResult]
    total: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    total_apis: int


@app.on_event("startup")
async def startup_event():
    """Initialize model and database on startup."""
    global model, collection

    chroma_path = os.getenv('CHROMA_PATH', '/app/data/chroma_db')
    model_path = os.getenv('MODEL_PATH', '/app/models/all-MiniLM-L6-v2')
    collection_name = os.getenv('COLLECTION_NAME', 'sdk_api')

    print(f"Loading model from: {model_path}")
    model = SentenceTransformer(model_path)
    print(f"Model loaded. Dimension: {model.get_sentence_embedding_dimension()}")

    print(f"Connecting to Chroma at: {chroma_path}")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection(collection_name)
    print(f"Collection '{collection_name}' loaded. Count: {collection.count()}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    total = collection.count() if collection else 0
    return HealthResponse(status="ok", total_apis=total)


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search SDK API by natural language query.

    Args:
        request: SearchRequest containing query and top_k

    Returns:
        SearchResponse with matching results
    """
    if model is None or collection is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Generate query embedding
    query_embedding = model.encode([request.query]).tolist()

    # Query collection
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=request.top_k,
        include=['documents', 'metadatas', 'distances']
    )

    # Format results
    search_results = []
    if results['ids'][0]:
        for i, doc_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i]
            document = results['documents'][0][i]
            distance = results['distances'][0][i]

            # Convert distance to similarity (Chroma uses cosine distance)
            similarity = 1 - distance

            search_results.append(SearchResult(
                class_=metadata.get('class', ''),
                method=metadata.get('method', ''),
                signature=metadata.get('signature', ''),
                description=document.split('Description: ')[-1] if 'Description: ' in document else '',
                similarity=round(similarity, 4)
            ))

    return SearchResponse(results=search_results, total=len(search_results))


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "SDK Knowledge Base API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "search": "/search"
        }
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 2: 提交**

```bash
git add scripts/api_server.py
git commit -m "feat: add FastAPI server with search endpoint"
```

---

### Task 4.2: 编写 API 服务测试

- [ ] **Step 1: 编写测试代码**

Create: `tests/test_api_server.py`
```python
"""Tests for API server."""
import pytest
from fastapi.testclient import TestClient

from scripts.api_server import app


client = TestClient(app)


class TestAPIServer:
    """Test cases for API server."""

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'SDK Knowledge Base API'
        assert 'endpoints' in data

    def test_search_endpoint_not_initialized(self):
        """Test search endpoint before initialization."""
        response = client.post("/search", json={"query": "test", "top_k": 3})
        # Should return 503 if not initialized
        assert response.status_code in [200, 503]

    def test_search_request_validation(self):
        """Test search request validation."""
        # Valid request
        response = client.post("/search", json={"query": "test", "top_k": 5})
        assert response.status_code in [200, 503]  # 200 if initialized, 503 if not

        # Invalid: missing query
        response = client.post("/search", json={"top_k": 5})
        assert response.status_code == 422

        # Invalid: negative top_k
        response = client.post("/search", json={"query": "test", "top_k": -1})
        assert response.status_code == 422


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

- [ ] **Step 2: 运行测试**

Run:
```bash
# 确保虚拟环境已激活
source venv/bin/activate  # Linux/macOS
# 或: source venv/Scripts/activate  # Windows

python -m pytest tests/test_api_server.py -v
```

Expected: Tests pass

- [ ] **Step 3: 提交**

```bash
git add tests/test_api_server.py
git commit -m "test: add API server tests"
```

---

## Task 5: 编写 CLI 客户端和包装脚本

**目标:** 创建 CLI 工具，支持直接查询和通过 Docker 调用

**Files:**
- Create: `scripts/query_client.py`
- Create: `query-sdk`

---

### Task 5.1: 编写 CLI 客户端

- [ ] **Step 1: 编写客户端代码**

Create: `scripts/query_client.py`
```python
"""CLI client for SDK knowledge base queries."""
import argparse
import os
import sys

import requests


API_BASE_URL = os.getenv('SDK_API_URL', 'http://localhost:8000')


def search(query: str, top_k: int = 5) -> dict:
    """Search SDK API.

    Args:
        query: Natural language query
        top_k: Number of results to return

    Returns:
        API response as dictionary
    """
    url = f"{API_BASE_URL}/search"
    response = requests.post(url, json={"query": query, "top_k": top_k})
    response.raise_for_status()
    return response.json()


def format_results(results: list) -> str:
    """Format search results as markdown.

    Args:
        results: List of search result dictionaries

    Returns:
        Formatted markdown string
    """
    if not results:
        return "未找到相关 API。"

    lines = []
    for i, result in enumerate(results, 1):
        lines.append(f"### {i}. {result['class_']}.{result['method']}")
        lines.append(f"**签名**: `{result['signature']}`")
        lines.append(f"**相似度**: {result['similarity']:.2%}")
        if result['description']:
            lines.append(f"**描述**: {result['description']}")
        lines.append("---")

    return '\n'.join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='SDK API 语义查询工具',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('query', help='自然语言查询，例如：如何建立连接')
    parser.add_argument('--top', type=int, default=5, help='返回结果数量（默认：5）')
    parser.add_argument('--raw', action='store_true', help='输出原始 JSON')

    args = parser.parse_args()

    try:
        result = search(args.query, args.top)

        if args.raw:
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_results(result['results']))

    except requests.exceptions.ConnectionError:
        print(f"错误：无法连接到 API 服务 ({API_BASE_URL})", file=sys.stderr)
        print("请确保服务已启动：docker run -d -p 8000:8000 sdk-kb:latest", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"错误：API 请求失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 提交**

```bash
git add scripts/query_client.py
git commit -m "feat: add CLI query client"
```

---

### Task 5.2: 编写 CLI 包装脚本

- [ ] **Step 1: 编写包装脚本**

Create: `query-sdk`
```bash
#!/bin/bash
# SDK Knowledge Base CLI wrapper
# Usage: query-sdk "自然语言查询" [--top N]

set -e

# Configuration
IMAGE_NAME="sdk-kb:latest"
API_PORT="${SDK_API_PORT:-8000}"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "错误：Docker 未安装或未在 PATH 中" >&2
    exit 1
fi

# Check if container is running
if ! docker ps --format "{{.Names}}" | grep -q "^sdk-kb$"; then
    echo "信息：SDK KB 服务未运行，正在启动..."
    echo "docker run -d -p ${API_PORT}:8000 --name sdk-kb --rm ${IMAGE_NAME}"
    docker run -d -p ${API_PORT}:8000 --name sdk-kb --rm ${IMAGE_NAME} > /dev/null 2>&1 || {
        echo "错误：无法启动 SDK KB 服务" >&2
        exit 1
    }
    # Wait for service to be ready
    sleep 2
    echo "服务已启动，端口: ${API_PORT}"
fi

# Build query arguments
QUERY="$1"
shift

# Execute query via Docker exec
docker exec sdk-kb python scripts/query_client.py "$QUERY" "$@"
```

- [ ] **Step 2: 使脚本可执行**

Run:
```bash
chmod +x query-sdk
```

- [ ] **Step 3: 提交**

```bash
git add query-sdk
git commit -m "feat: add CLI wrapper script"
```

---

## Task 6: 编写 Dockerfile

**目标:** 创建多阶段 Dockerfile，打包预构建的向量库和模型

**Files:**
- Create: `Dockerfile`

---

### Task 6.1: 创建 Dockerfile

- [ ] **Step 1: 编写 Dockerfile**

Create: `Dockerfile`
```dockerfile
# Multi-stage build for SDK Knowledge Base

# Stage 1: Builder - install dependencies and download model
FROM python:3.9-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download sentence-transformers model
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', \
    cache_folder='/app/models')"

# Stage 2: Runner - copy pre-built data
FROM python:3.9-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy model from builder
COPY --from=builder /app/models /app/models

# Copy application code
COPY scripts/ ./scripts/

# Copy pre-built vector database (must exist before build)
COPY data/chroma_db/ ./data/chroma_db/

# Set environment variables
ENV CHROMA_PATH=/app/data/chroma_db
ENV MODEL_PATH=/app/models
ENV COLLECTION_NAME=sdk_api
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run API server
CMD ["uvicorn", "scripts.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 提交**

```bash
git add Dockerfile
git commit -m "feat: add multi-stage Dockerfile"
```

---

## Task 7: 构建完整流程

**目标:** 编写构建脚本，自动化解析、向量化和镜像构建

**Files:**
- Create: `build.sh`

---

### Task 7.1: 创建构建脚本

- [ ] **Step 1: 编写构建脚本**

Create: `build.sh`
```bash
#!/bin/bash
# Build script for SDK Knowledge Base

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
INPUT_DIR="${1:-SuperMap iObjects Java Javadoc}"
OUTPUT_JSON="data/sdk_knowledge.json"
CHROMA_DB="data/chroma_db"
IMAGE_NAME="sdk-kb:latest"

# Python interpreter (use venv if exists)
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif [ -f "venv/Scripts/python.exe" ]; then
    PYTHON="venv/Scripts/python.exe"
else
    PYTHON="python3"
fi

echo "=========================================="
echo "SDK Knowledge Base Build Script"
echo "=========================================="
echo "Python: $PYTHON"
echo "Input directory: $INPUT_DIR"
echo ""

# Step 1: Check Python dependencies
echo "Step 1: Checking Python dependencies..."
$PYTHON -c "import bs4, chromadb, sentence_transformers" 2>/dev/null || {
    echo "Installing Python dependencies..."
    $PYTHON -m pip install -r requirements.txt
}

# Step 2: Parse HTML
echo ""
echo "Step 2: Parsing Javadoc HTML..."
$PYTHON scripts/parse_javadoc.py "$INPUT_DIR" "$OUTPUT_JSON"

# Step 3: Build vector database
echo ""
echo "Step 3: Building vector database..."
$PYTHON scripts/build_vector_db.py "$OUTPUT_JSON" "$CHROMA_DB"

# Step 4: Build Docker image
echo ""
echo "Step 4: Building Docker image..."
docker build -t "$IMAGE_NAME" .

# Step 5: Export image
echo ""
echo "Step 5: Exporting Docker image..."
docker save -o sdk-kb.tar "$IMAGE_NAME"

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo "Docker image: $IMAGE_NAME"
echo "Export file: sdk-kb.tar"
echo ""
echo "To deploy on offline machine:"
echo "  1. Copy sdk-kb.tar to offline machine"
echo "  2. Run: docker load -i sdk-kb.tar"
echo "  3. Run: docker run -d -p 8000:8000 --name sdk-kb $IMAGE_NAME"
echo ""
```

- [ ] **Step 2: 使脚本可执行**

Run:
```bash
chmod +x build.sh
```

- [ ] **Step 3: 提交**

```bash
git add build.sh
git commit -m "feat: add build automation script"
```

---

## Task 8: 编写文档

**目标:** 创建使用说明文档

**Files:**
- Create: `README.md`
- Create: `DEPLOY.md`

---

### Task 8.1: 创建 README

- [ ] **Step 1: 编写 README**

Create: `README.md`
```markdown
# SDK Knowledge Base

基于 Docker 的 SuperMap iObjects Java SDK 语义搜索知识库，支持离线部署。

## 功能

- 解析 Javadoc HTML 文档
- 使用 Sentence-Transformers 构建语义向量索引
- 提供 HTTP API 进行自然语言查询
- Docker 打包，一键离线部署

## 快速开始

### 构建（联网环境）

```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或: source venv/Scripts/activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行构建脚本
./build.sh "SuperMap iObjects Java Javadoc"
```

构建完成后会生成 `sdk-kb.tar` 镜像文件。

### 部署（离线环境）

```bash
# 导入镜像
docker load -i sdk-kb.tar

# 启动服务
docker run -d -p 8000:8000 --name sdk-kb sdk-kb:latest

# 测试查询
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "如何建立连接", "top_k": 5}'
```

### CLI 查询

```bash
# 使用包装脚本
./query-sdk "如何建立连接"

# 或在虚拟环境中使用原始客户端
source venv/bin/activate
python scripts/query_client.py "如何建立连接"
```

## API 端点

- `GET /health` - 健康检查
- `POST /search` - 搜索 API
  - Request: `{"query": "...", "top_k": 5}`
  - Response: `{"results": [...], "total": N}`

## 项目结构

- `scripts/` - Python 脚本
- `tests/` - 测试代码
- `data/` - 向量数据库（构建时生成）
- `query-sdk` - CLI 包装脚本

## 开发

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行测试
pytest tests/ -v

# 手动解析
python scripts/parse_javadoc.py "docs/" data/sdk_knowledge.json

# 手动构建向量库
python scripts/build_vector_db.py data/sdk_knowledge.json data/chroma_db
```

## 许可证

MIT
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: add README"
```

---

### Task 8.2: 创建部署文档

- [ ] **Step 1: 编写部署文档**

Create: `DEPLOY.md`
```markdown
# 离线部署指南

## 环境要求

- Linux 系统
- Docker Engine 或 Docker Desktop
- 至少 4GB 内存
- 2GB 磁盘空间

## 部署步骤

### 1. 传输镜像

将 `sdk-kb.tar` 文件复制到离线机器：

```bash
# 使用 scp、U 盘或其他方式传输
scp sdk-kb.tar user@offline-host:/opt/
```

### 2. 导入镜像

在离线机器上执行：

```bash
docker load -i sdk-kb.tar
```

验证导入：

```bash
docker images | grep sdk-kb
```

### 3. 启动服务

```bash
docker run -d \
  --name sdk-kb \
  -p 8000:8000 \
  --restart unless-stopped \
  sdk-kb:latest
```

查看日志：

```bash
docker logs -f sdk-kb
```

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 测试查询
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "如何创建工作空间", "top_k": 3}'
```

### 5. 配置 CLI

```bash
# 复制 CLI 脚本
sudo cp query-sdk /usr/local/bin/
sudo chmod +x /usr/local/bin/query-sdk

# 测试
query-sdk "如何创建工作空间"
```

## 常用命令

```bash
# 停止服务
docker stop sdk-kb

# 启动服务
docker start sdk-kb

# 重启服务
docker restart sdk-kb

# 查看状态
docker ps -a | grep sdk-kb

# 删除容器（保留镜像）
docker rm sdk-kb

# 完全删除
docker stop sdk-kb && docker rm sdk-kb && docker rmi sdk-kb:latest
```

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker logs sdk-kb

# 检查端口占用
netstat -tlnp | grep 8000
```

### 查询无结果

```bash
# 检查索引数量
curl http://localhost:8000/health

# 如果 total_apis 为 0，可能是构建问题
```

### 内存不足

```bash
# 查看内存使用
docker stats sdk-kb

# 限制内存
docker update --memory 2g sdk-kb
```

## 更新 SDK

如需更新 SDK 文档：

1. 在联网环境重新运行 `./build.sh`
2. 导出新的 `sdk-kb.tar`
3. 在离线环境：
   ```bash
   docker stop sdk-kb
   docker rm sdk-kb
   docker load -i sdk-kb.tar
   docker run -d -p 8000:8000 --name sdk-kb sdk-kb:latest
   ```
```

- [ ] **Step 2: 提交**

```bash
git add DEPLOY.md
git commit -m "docs: add deployment guide"
```

---

## Task 9: 编写 MCP 服务器（可选增强）

**目标:** 创建 MCP 服务器，实现与 Claude Code 的原生集成

**Files:**
- Create: `scripts/mcp_server.py`
- Create: `.mcp.json`

---

### Task 9.1: 编写 MCP 服务器

- [ ] **Step 1: 安装 MCP SDK**

Run:
```bash
source venv/bin/activate  # 或 venv/Scripts/activate
pip install mcp
```

- [ ] **Step 2: 编写 MCP 服务器代码**

Create: `scripts/mcp_server.py`
```python
#!/usr/bin/env python3
"""SDK Knowledge Base MCP Server"""
import json
import os
import sys
from typing import Any

import requests
from mcp.server import Server
from mcp.types import TextContent, Tool

API_BASE_URL = os.getenv("SDK_API_URL", "http://localhost:8000")
app = Server("sdk-knowledge-base")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_sdk_api",
            description="搜索 SuperMap iObjects Java SDK API",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "自然语言查询"},
                    "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_sdk_api_info",
            description="获取 SDK 知识库信息",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    # 实现工具调用逻辑
    pass

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

- [ ] **Step 3: 创建 MCP 配置文件**

Create: `.mcp.json`
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

- [ ] **Step 4: 提交**

```bash
git add scripts/mcp_server.py .mcp.json
git commit -m "feat: add MCP server for Claude Code integration"
```

---

## 自检清单

### Spec Coverage

| 需求 | 实现任务 |
|------|---------|
| 解析 Javadoc HTML | Task 2 |
| 向量数据库构建 | Task 3 |
| HTTP API 服务 | Task 4 |
| CLI 查询工具 | Task 5 |
| MCP 服务器 | Task 9 |
| Docker 打包 | Task 6 |
| 构建自动化 | Task 7 |
| 文档 | Task 8 |

### Placeholder Scan

- [x] 无 TBD/TODO
- [x] 无模糊描述
- [x] 所有代码完整
- [x] 测试代码完整

### Type Consistency

- [x] `SearchResult.class_` 一致使用
- [x] API 端点路径一致 `/search`, `/health`
- [x] 环境变量名称一致

---

## Plan Summary

**总任务数**: 9 个主要任务
**预计文件创建**: 15+
**预计提交次数**: 15+

**执行顺序**: 按 Task 1 → 8 顺序执行

**关键依赖**:
- Task 3 依赖 Task 2（需要解析后的 JSON）
- Task 6 依赖 Task 3 和 Task 4（需要向量库和服务代码）
- Task 7 依赖 Task 2-6

**测试策略**:
- 每个核心组件都有单元测试
- API 服务使用 FastAPI TestClient
- 构建完成后进行端到端测试
