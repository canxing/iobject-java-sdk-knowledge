#!/bin/bash
# Build script for SDK Knowledge Base

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
INPUT_DIR="${1:-SuperMap iObjects Java Javadoc}"
OUTPUT_JSON="data/parsed_javadoc.json"
CHROMA_DB="data/chroma_db"
IMAGE_NAME="sdk-kb:latest"

# Logging setup
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/build-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$LOG_DIR"

# Logging functions
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

# Error handler
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

log_info "=========================================="
log_info "SDK Knowledge Base Build Script"
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
docker build -t "$IMAGE_NAME" . 2>&1 | tee -a "$LOG_FILE"
END_TIME=$(date +%s)
log_info "Step 4 completed in $((END_TIME - START_TIME))s"
log_info "Image: $IMAGE_NAME"

# Step 5: Export image
log_step "5" "Exporting Docker image"
START_TIME=$(date +%s)
docker save -o sdk-kb.tar "$IMAGE_NAME" 2>&1 | tee -a "$LOG_FILE"
END_TIME=$(date +%s)
log_info "Step 5 completed in $((END_TIME - START_TIME))s"
log_info "Export: sdk-kb.tar ($(du -h sdk-kb.tar | cut -f1))"

log_info ""
log_info "=========================================="
log_info "Build complete!"
log_info "=========================================="
log_info "Docker image: $IMAGE_NAME"
log_info "Export file: sdk-kb.tar"
log_info "Log file: $LOG_FILE"
