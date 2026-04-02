# 部署指南

本文档详细介绍 SDK 知识库系统的部署流程。

## 环境要求

### 硬件要求

| 配置项 | 最低要求 | 推荐配置 |
|--------|----------|----------|
| CPU | 2 核心 | 4 核心+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘空间 | 2 GB | 5 GB+ |
| 网络 | 内网访问 | 公网访问 |

### 软件要求

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| Docker | 20.10+ | 容器运行时 |
| Docker Compose | 2.0+ (可选) | 多容器编排 |
| Python | 3.9+ | 仅开发环境需要 |
| Bash | 4.0+ | 脚本执行 |

### 操作系统支持

- Linux (Ubuntu 20.04+, CentOS 7+, Debian 10+)
- macOS 11.0+
- Windows 10/11 (使用 WSL2)

## 部署步骤

### 步骤 1: 导入 Docker 镜像

将预构建的镜像文件复制到目标服务器：

```bash
# 复制镜像文件到服务器
scp sdk-kb.tar user@server:/path/to/deploy/

# 在服务器上导入镜像
docker load -i sdk-kb.tar
```

**验证导入**:
```bash
docker images | grep sdk-kb
```

预期输出：
```
sdk-kb    latest    xxxxxxx    xx minutes ago    xxx MB
```

### 步骤 2: 准备数据目录

```bash
# 创建工作目录
mkdir -p /opt/sdk-kb/data
mkdir -p /opt/sdk-kb/models

# 复制数据文件（如果从源码构建）
cp -r data/chroma_db /opt/sdk-kb/data/
cp -r models/* /opt/sdk-kb/models/ 2>/dev/null || true

# 设置权限
chmod -R 755 /opt/sdk-kb
```

### 步骤 3: 启动服务

#### 方式一：使用 Docker 直接启动

```bash
# 启动容器
docker run -d \
    --name sdk-kb \
    --restart unless-stopped \
    -p 8000:8000 \
    -v /opt/sdk-kb/data:/app/data:ro \
    -v /opt/sdk-kb/models:/app/models:ro \
    -e MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2 \
    -e COLLECTION_NAME=sdk_api \
    sdk-kb:latest

# 查看容器状态
docker ps -a | grep sdk-kb

# 查看日志
docker logs -f sdk-kb
```

#### 方式二：使用 Docker Compose

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  sdk-kb:
    image: sdk-kb:latest
    container_name: sdk-kb
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data:ro
      - ./models:/app/models:ro
    environment:
      - MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
      - COLLECTION_NAME=sdk_api
      - CHROMA_PATH=/app/data/chroma_db
      - MODEL_PATH=/app/models
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

启动服务：

```bash
# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 步骤 4: 验证部署

#### 健康检查

```bash
# 方法 1: HTTP 请求
curl http://localhost:8000/health

# 方法 2: 使用 query-sdk 脚本
./query-sdk --check
```

预期响应：
```json
{
  "status": "healthy",
  "collection": "sdk_api",
  "document_count": 1234,
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

#### 功能测试

```bash
# 测试搜索 API
curl -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -d '{"query": "如何创建数据源", "top_k": 3}'

# 使用 query-sdk 测试
./query-sdk "如何创建数据源"
```

#### Web 界面

浏览器访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## CLI 配置

### 1. 配置 query-sdk 脚本

```bash
# 复制脚本到系统 PATH
cp query-sdk /usr/local/bin/
chmod +x /usr/local/bin/query-sdk

# 现在可以在任何位置使用
query-sdk "如何创建数据源"
```

### 2. 环境变量配置

编辑 `~/.bashrc` 或 `~/.zshrc`：

```bash
# SDK 知识库配置
export SDK_API_URL=http://localhost:8000
export SDK_KB_CONTAINER_NAME=sdk-kb

# 可选：配置日志级别
export SDK_LOG_LEVEL=INFO
```

加载配置：

```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

### 3. 别名配置

添加常用别名：

```bash
# 添加到 ~/.bashrc
alias kb-check='query-sdk --check'
alias kb-restart='query-sdk --restart'
alias kb-stop='query-sdk --stop'
alias kb-logs='docker logs -f sdk-kb'
```

## 常用命令

### 容器管理

```bash
# 查看容器状态
docker ps -a | grep sdk-kb

# 查看日志
docker logs sdk-kb
docker logs -f sdk-kb  # 实时跟踪

# 重启容器
docker restart sdk-kb

# 停止容器
docker stop sdk-kb

# 删除容器
docker rm sdk-kb

# 进入容器（调试）
docker exec -it sdk-kb /bin/bash
```

### 服务管理

```bash
# 使用 query-sdk 管理
query-sdk --check      # 健康检查
query-sdk --restart    # 重启服务
query-sdk --stop       # 停止服务

# 使用 systemctl（如果配置了服务）
systemctl status sdk-kb
systemctl restart sdk-kb
systemctl stop sdk-kb
```

### 数据备份

```bash
# 备份数据目录
tar -czf sdk-kb-backup-$(date +%Y%m%d).tar.gz /opt/sdk-kb/data/

# 备份 Docker 镜像
docker save sdk-kb:latest | gzip > sdk-kb-image-$(date +%Y%m%d).tar.gz
```

### 数据恢复

```bash
# 恢复数据
tar -xzf sdk-kb-backup-YYYYMMDD.tar.gz -C /

# 恢复镜像
gunzip -c sdk-kb-image-YYYYMMDD.tar.gz | docker load
```

## 故障排查

### 常见问题

#### 问题 1: 容器无法启动

**症状**:
```
Error: docker: Error response from daemon...
```

**排查步骤**:
```bash
# 查看详细日志
docker logs sdk-kb

# 检查端口冲突
netstat -tlnp | grep 8000

# 检查数据目录权限
ls -la /opt/sdk-kb/data/

# 检查镜像完整性
docker inspect sdk-kb:latest
```

**解决方案**:
```bash
# 如果端口被占用，更换端口
docker run -d --name sdk-kb -p 8001:8000 sdk-kb:latest

# 修复权限
chmod -R 755 /opt/sdk-kb/data
chown -R $USER:$USER /opt/sdk-kb
```

#### 问题 2: 健康检查失败

**症状**:
```
服务不可用 (http://localhost:8000)
```

**排查步骤**:
```bash
# 检查容器状态
docker ps -a | grep sdk-kb

# 查看容器日志
docker logs sdk-kb --tail 50

# 测试 HTTP 连通性
curl -v http://localhost:8000/health

# 检查容器内部
docker exec sdk-kb python -c "import chromadb; print('OK')"
```

**可能原因**:
- 数据目录未正确挂载
- 向量数据库文件损坏
- 内存不足导致服务启动失败

**解决方案**:
```bash
# 重新检查数据挂载
docker inspect sdk-kb | grep -A 5 Mounts

# 重建容器
docker rm -f sdk-kb
docker run -d --name sdk-kb \
    -p 8000:8000 \
    -v /opt/sdk-kb/data:/app/data:ro \
    sdk-kb:latest
```

#### 问题 3: 搜索结果不准确

**排查**:
```bash
# 检查文档数量
curl http://localhost:8000/health | jq '.document_count'

# 查看向量数据库状态
docker exec sdk-kb python -c "
import chromadb
client = chromadb.PersistentClient('/app/data/chroma_db')
coll = client.get_collection('sdk_api')
print(f'文档数: {coll.count()}')
"
```

**解决方案**:
- 重新构建向量数据库
- 检查模型是否正确加载
- 验证原始数据完整性

#### 问题 4: 性能问题

**症状**: 查询响应慢

**排查**:
```bash
# 检查资源使用
docker stats sdk-kb

# 查看系统负载
top
free -h

# 测试查询时间
time curl -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -d '{"query": "test", "top_k": 5}'
```

**优化建议**:
- 增加内存分配
- 使用 SSD 存储数据
- 考虑使用 GPU 加速（需修改配置）

### 日志分析

**查看特定级别日志**:
```bash
# 查看错误日志
docker logs sdk-kb 2>&1 | grep -i error

# 查看启动日志
docker logs sdk-kb 2>&1 | head -50
```

**导出日志**:
```bash
# 导出到文件
docker logs sdk-kb > sdk-kb-$(date +%Y%m%d).log 2>&1

# 导出最近 1000 行
docker logs --tail 1000 sdk-kb > recent.log 2>&1
```

## 更新 SDK 方法

### 场景 1: 新增 SDK 版本

```bash
# 1. 准备新的 Javadoc 文件
mkdir -p "SuperMap iObjects Java Javadoc-new"
cp -r new-javadoc/* "SuperMap iObjects Java Javadoc-new/"

# 2. 重新解析
python scripts/parse_javadoc.py \
    "SuperMap iObjects Java Javadoc-new" \
    data/sdk_knowledge_new.json

# 3. 重建向量数据库
python scripts/build_vector_db.py \
    data/sdk_knowledge_new.json \
    data/chroma_db_new

# 4. 备份旧数据
mv /opt/sdk-kb/data/chroma_db /opt/sdk-kb/data/chroma_db_backup

# 5. 部署新数据
cp -r data/chroma_db_new /opt/sdk-kb/data/chroma_db

# 6. 重启服务
docker restart sdk-kb
```

### 场景 2: 增量更新

```bash
# 1. 解析新的 Javadoc（只包含变更）
python scripts/parse_javadoc.py \
    "javadoc-updates" \
    data/updates.json

# 2. 合并到现有数据
python -c "
import json
with open('data/sdk_knowledge.json') as f:
    existing = json.load(f)
with open('data/updates.json') as f:
    updates = json.load(f)

# 合并逻辑（去重）
existing_ids = {(c['class'], m['name']) for c in existing for m in c['methods']}
for cls in updates:
    for method in cls['methods']:
        if (cls['class'], method['name']) not in existing_ids:
            # 添加新方法
            pass

# 保存合并结果
with open('data/merged.json', 'w') as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)
"

# 3. 重建向量数据库
python scripts/build_vector_db.py data/merged.json data/chroma_db

# 4. 重启服务
docker restart sdk-kb
```

### 场景 3: 更新向量模型

```bash
# 1. 修改 Dockerfile 中的模型名称
# FROM: sentence-transformers/all-MiniLM-L6-v2
# TO: sentence-transformers/all-MiniLM-L12-v2

# 2. 重新构建镜像
docker build -t sdk-kb:v2 .

# 3. 导出镜像
docker save -o sdk-kb-v2.tar sdk-kb:v2

# 4. 在生产环境部署
docker load -i sdk-kb-v2.tar
docker stop sdk-kb
docker rm sdk-kb
docker run -d --name sdk-kb -p 8000:8000 sdk-kb:v2
```

### 自动化更新脚本

创建 `update-sdk.sh`：

```bash
#!/bin/bash
set -e

JAVADOC_DIR="${1:-SuperMap iObjects Java Javadoc}"
BACKUP_DIR="/opt/sdk-kb/backup/$(date +%Y%m%d_%H%M%S)"

echo "=== SDK 知识库更新脚本 ==="

# 备份现有数据
echo "备份现有数据..."
mkdir -p "$BACKUP_DIR"
cp -r /opt/sdk-kb/data/chroma_db "$BACKUP_DIR/"

# 解析新数据
echo "解析 Javadoc..."
python scripts/parse_javadoc.py "$JAVADOC_DIR" data/sdk_knowledge.json

# 构建新向量数据库
echo "构建向量数据库..."
python scripts/build_vector_db.py data/sdk_knowledge.json data/chroma_db

# 复制到部署目录
echo "更新部署数据..."
rm -rf /opt/sdk-kb/data/chroma_db
cp -r data/chroma_db /opt/sdk-kb/data/

# 重启服务
echo "重启服务..."
docker restart sdk-kb

# 验证
echo "验证更新..."
sleep 5
if query-sdk --check; then
    echo "更新成功！"
else
    echo "更新失败，正在恢复..."
    rm -rf /opt/sdk-kb/data/chroma_db
    cp -r "$BACKUP_DIR/chroma_db" /opt/sdk-kb/data/
    docker restart sdk-kb
    exit 1
fi
```

使用：

```bash
chmod +x update-sdk.sh
./update-sdk.sh "SuperMap iObjects Java Javadoc"
```

## 生产环境建议

### 高可用部署

```yaml
# docker-compose.ha.yml
version: '3.8'

services:
  sdk-kb-1:
    image: sdk-kb:latest
    container_name: sdk-kb-1
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data:ro
    environment:
      - COLLECTION_NAME=sdk_api

  sdk-kb-2:
    image: sdk-kb:latest
    container_name: sdk-kb-2
    restart: unless-stopped
    ports:
      - "8001:8000"
    volumes:
      - ./data:/app/data:ro
    environment:
      - COLLECTION_NAME=sdk_api

  nginx:
    image: nginx:alpine
    container_name: sdk-kb-lb
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - sdk-kb-1
      - sdk-kb-2
```

### 监控建议

```bash
# 使用 Prometheus + Grafana 监控
# 或使用简单的脚本检查

# 创建监控脚本
#!/bin/bash
while true; do
    status=$(curl -s http://localhost:8000/health | jq -r '.status')
    if [ "$status" != "healthy" ]; then
        echo "$(date): 服务异常，发送告警..."
        # 发送告警（邮件/钉钉/企业微信等）
    fi
    sleep 60
done
```

### 安全建议

1. **限制访问**: 使用防火墙限制 API 端口访问
2. **HTTPS**: 使用 Nginx 反向代理配置 HTTPS
3. **定期备份**: 设置定时任务备份数据
4. **日志审计**: 定期审查访问日志

---

如有问题，请参考 README.md 或提交 Issue。
