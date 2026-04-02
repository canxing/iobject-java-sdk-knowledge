# 多阶段 Dockerfile for SDK 知识库系统
# Stage 1: builder - 构建依赖和下载模型
# Stage 2: runner - 运行服务

# ==================== Stage 1: Builder ====================
FROM python:3.9-slim AS builder

# 使用清华镜像源加速 apt
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖到虚拟环境（便于复制到 runner）
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 设置环境变量（加速模型下载）
ENV PATH="/opt/venv/bin:$PATH" \
    HF_ENDPOINT=https://hf-mirror.com \
    TRANSFORMERS_OFFLINE=0

# 安装依赖（使用清华镜像加速）
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 使用本地预下载的模型（不重新下载）
ENV HF_HUB_OFFLINE=1

# 复制本地模型
COPY models_cache/hub/models--sentence-transformers--all-MiniLM-L6-v2/ /root/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/

# 复制模型到应用目录
RUN mkdir -p /app/models && \
    python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); model.save('/app/models/all-MiniLM-L6-v2')" && \
    ls -la /app/models/

# ==================== Stage 2: Runner ====================
FROM python:3.9-slim AS runner

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    CHROMA_PATH=/app/data/chroma_db \
    MODEL_PATH=/app/models \
    COLLECTION_NAME=sdk_api \
    MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2 \
    PATH="/opt/venv/bin:$PATH"

# 创建非 root 用户（安全最佳实践）
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# 复制虚拟环境（包含所有 Python 包）
COPY --from=builder /opt/venv /opt/venv

# 复制模型
COPY --from=builder /app/models /app/models

# 复制应用代码
COPY scripts/ /app/scripts/

# 复制预构建的向量数据库
COPY data/chroma_db/ /app/data/chroma_db/

# 设置目录权限
RUN chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令
CMD ["uvicorn", "scripts.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
