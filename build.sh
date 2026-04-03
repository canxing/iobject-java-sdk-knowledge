#!/bin/bash
# Build script for SDK Knowledge Base
# 支持分层镜像构建：基础镜像（依赖）和最终镜像（应用）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ==================== 配置 ====================
REGISTRY="registry.cn-chengdu.aliyuncs.com/liuxin-registry"
IMAGE_NAME="iobject-java-sdk-knowledge"
BASE_TAG="1.0"

INPUT_DIR="${1:-SuperMap iObjects Java Javadoc}"
OUTPUT_JSON="data/parsed_javadoc.json"
CHROMA_DB="data/chroma_db"

# ==================== 日志配置 ====================
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/build-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$LOG_DIR"

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE" >&2
}

log_step() {
    echo "" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "STEP $1: $2" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
}

error_handler() {
    local line=$1
    log_error "Build failed at line $line"
    log_error "Check log file: $LOG_FILE"
    exit 1
}
trap 'error_handler $LINENO' ERR

# Python interpreter (use venv if exists)
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif [ -f "venv/Scripts/python.exe" ]; then
    PYTHON="venv/Scripts/python.exe"
else
    PYTHON="python3"
fi

# ==================== 构建函数 ====================

# 构建基础镜像（包含依赖和模型）
build_base() {
    log_info "=========================================="
    log_info "Building base image with dependencies"
    log_info "=========================================="
    log_info "Registry: $REGISTRY"
    log_info "Base tag: $BASE_TAG"

    START_TIME=$(date +%s)
    docker build -f Dockerfile.base \
        -t "${IMAGE_NAME}-base:${BASE_TAG}" \
        . 2>&1 | tee -a "$LOG_FILE"

    # 推送到镜像仓库
    docker tag "${IMAGE_NAME}-base:${BASE_TAG}" \
        "${REGISTRY}/${IMAGE_NAME}-base:${BASE_TAG}"
    docker push "${REGISTRY}/${IMAGE_NAME}-base:${BASE_TAG}" 2>&1 | tee -a "$LOG_FILE"

    END_TIME=$(date +%s)
    log_info "Base image build completed in $((END_TIME - START_TIME))s"
}

# 构建最终镜像（基于基础镜像，只添加应用代码和数据）
build_final() {
    log_info "=========================================="
    log_info "Building final image"
    log_info "=========================================="
    log_info "Registry: $REGISTRY"
    log_info "Image: ${IMAGE_NAME}:latest"

    # 拉取基础镜像（如果本地不存在）
    docker pull "${REGISTRY}/${IMAGE_NAME}-base:${BASE_TAG}" 2>/dev/null || {
        log_info "Base image not found in registry, building locally..."
        docker build -f Dockerfile.base -t "${IMAGE_NAME}-base:${BASE_TAG}" . 2>&1 | tee -a "$LOG_FILE"
    }

    START_TIME=$(date +%s)
    docker build -f Dockerfile.final \
        --build-arg BASE_IMAGE="${REGISTRY}/${IMAGE_NAME}-base:${BASE_TAG}" \
        -t "${IMAGE_NAME}:latest" \
        . 2>&1 | tee -a "$LOG_FILE"
    END_TIME=$(date +%s)
    log_info "Final image build completed in $((END_TIME - START_TIME))s"
}

# 完整构建（先构建基础镜像，再构建最终镜像）
build_all() {
    build_base
    build_final
}

# 本地完整构建（不推送，用于本地测试）
build_local() {
    log_info "=========================================="
    log_info "SDK Knowledge Base Local Build"
    log_info "=========================================="
    log_info "Python: $PYTHON"
    log_info "Input directory: $INPUT_DIR"
    log_info "Log file: $LOG_FILE"
    log_info ""

    # Step 1: Check Python dependencies
    log_step "1" "Checking Python dependencies"
    START_TIME=$(date +%s)
    $PYTHON -c "import bs4, chromadb, sentence_transformers" 2>/dev/null || {
        log_info "Installing Python dependencies..."
        $PYTHON -m pip install -r requirements.txt 2>&1 | tee -a "$LOG_FILE"
    }
    END_TIME=$(date +%s)
    log_info "Step 1 completed in $((END_TIME - START_TIME))s"

    # Step 2: Parse HTML
    log_step "2" "Parsing Javadoc HTML"
    START_TIME=$(date +%s)
    $PYTHON scripts/parse_javadoc.py "$INPUT_DIR" "$OUTPUT_JSON" 2>&1 | tee -a "$LOG_FILE"
    END_TIME=$(date +%s)
    log_info "Step 2 completed in $((END_TIME - START_TIME))s"
    log_info "Generated: $OUTPUT_JSON"

    # Step 3: Build vector database
    log_step "3" "Building vector database"
    START_TIME=$(date +%s)
    $PYTHON scripts/build_vector_db.py --input "$OUTPUT_JSON" --output "$CHROMA_DB" 2>&1 | tee -a "$LOG_FILE"
    END_TIME=$(date +%s)
    log_info "Step 3 completed in $((END_TIME - START_TIME))s"
    log_info "Generated: $CHROMA_DB"

    # Step 4: Build Docker image
    log_step "4" "Building Docker image"
    START_TIME=$(date +%s)
    docker build -t "${IMAGE_NAME}:latest" . 2>&1 | tee -a "$LOG_FILE"
    END_TIME=$(date +%s)
    log_info "Step 4 completed in $((END_TIME - START_TIME))s"
    log_info "Image: ${IMAGE_NAME}:latest"

    log_info ""
    log_info "=========================================="
    log_info "Build complete!"
    log_info "=========================================="
    log_info "Docker image: ${IMAGE_NAME}:latest"
    log_info "Log file: $LOG_FILE"
}

# ==================== 主流程 ====================

case "${1:-}" in
    --base)
        build_base
        ;;
    --final)
        build_final
        ;;
    --all)
        build_all
        ;;
    --help|-h)
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  --base    Build only the base image (dependencies + model)"
        echo "  --final   Build only the final image (application + data)"
        echo "  --all     Build base image then final image (default for initial setup)"
        echo "  --local   Build everything locally (without registry)"
        echo "  --help    Show this help message"
        echo ""
        echo "Without options, builds everything locally for testing."
        exit 0
        ;;
    *)
        log_info "No option specified, running local build for testing..."
        log_info "For CI/CD, use: --base, --final, or --all"
        echo ""
        echo "Available options:"
        echo "  --base    Build only the base image (dependencies + model)"
        echo "  --final   Build only the final image (application + data)"
        echo "  --all     Build base image then final image"
        echo "  --local   Build everything locally (default)"
        echo "  --help    Show help"
        echo ""
        read -p "Continue with local build? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            build_local
        else
            exit 0
        fi
        ;;
esac
