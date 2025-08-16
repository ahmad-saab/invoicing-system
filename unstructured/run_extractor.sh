#!/bin/bash
# Simple bash runner for Unstructured.io PDF Extractor
# Usage: ./run_extractor.sh [pdf_file]

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_EXE="$VENV_DIR/bin/python"
EXTRACTOR_SCRIPT="$SCRIPT_DIR/unstructured_cli.py"

echo "🚀 Unstructured.io PDF Extractor"
echo "=================================="

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found!"
    echo "Expected location: $VENV_DIR"
    echo ""
    echo "To set up the environment:"
    echo "1. cd unstructured"
    echo "2. python3 -m venv venv"
    echo "3. source venv/bin/activate"
    echo "4. pip install unstructured[pdf]"
    exit 1
fi

# Check if Python executable exists
if [ ! -f "$PYTHON_EXE" ]; then
    echo "❌ Python executable not found in virtual environment!"
    echo "Expected: $PYTHON_EXE"
    exit 1
fi

# Check if extractor script exists
if [ ! -f "$EXTRACTOR_SCRIPT" ]; then
    echo "❌ Extractor script not found!"
    echo "Expected: $EXTRACTOR_SCRIPT"
    exit 1
fi

echo "📁 Working directory: $SCRIPT_DIR"
echo "🐍 Using Python: $PYTHON_EXE"
echo "📄 Running script: $EXTRACTOR_SCRIPT"
echo ""

# If no argument provided, show usage and available test files
if [ $# -eq 0 ]; then
    echo "Usage: $0 <pdf_file>"
    echo ""
    echo "Available test files:"
    if [ -d "../test lpos" ]; then
        ls -la "../test lpos"/*.pdf 2>/dev/null | head -10
    fi
    echo ""
    echo "Example:"
    echo "  $0 \"../test lpos/F5.pdf\""
    echo "  $0 \"../test lpos/Atrade.pdf\""
    exit 1
fi

PDF_FILE="$1"

# Check if PDF file exists
if [ ! -f "$PDF_FILE" ]; then
    echo "❌ PDF file not found: $PDF_FILE"
    exit 1
fi

echo "🔍 Processing: $(basename "$PDF_FILE")"
echo ""

# Run the extractor
cd "$SCRIPT_DIR"
"$PYTHON_EXE" "$EXTRACTOR_SCRIPT" "$PDF_FILE"

echo ""
echo "✅ Done! Check the extracted_data/ directory for results."