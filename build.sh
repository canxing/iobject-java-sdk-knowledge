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
