# Unstructured.io PDF Extractor

A self-sufficient PDF data extraction tool using the unstructured.io library with a GUI interface.

## Features

- **GUI Interface**: Simple tkinter-based file picker
- **Unstructured.io Library**: Advanced PDF parsing with AI-powered extraction
- **JSON Output**: Structured data export in JSON format
- **Multiple Strategies**: High-resolution extraction with table detection
- **Self-Contained**: Own virtual environment with all dependencies

## Installation & Setup

The tool is already set up with its own virtual environment and dependencies.

### Directory Structure:
```
unstructured/
├── venv/                    # Virtual environment with unstructured[pdf]
├── unstructured_extractor.py  # Main GUI application
├── run_extractor.py         # Simple runner script
├── README.md               # This file
└── extracted_data/         # Output directory (created automatically)
```

## Usage

### Method 1: Using the Runner Script
```bash
cd unstructured
python3 run_extractor.py
```

### Method 2: Direct Execution
```bash
cd unstructured
source venv/bin/activate
python unstructured_extractor.py
```

## How It Works

1. **File Selection**: Use the GUI to browse and select a PDF file
2. **Output Directory**: Choose where to save extracted data
3. **Extraction Options**: 
   - Extract Images: Include images from PDF
   - Extract Tables: Detect and extract table structures
   - Chunk by Title: Organize content by document sections
4. **Extract Data**: Click to start the extraction process
5. **Results**: Get JSON file with structured data + summary text file

## Output Files

For each PDF processed, you get:
- `filename_unstructured_extraction.json` - Complete structured data
- `filename_extraction_summary.txt` - Human-readable summary

## JSON Structure

```json
{
  "file_info": {
    "filename": "document.pdf",
    "extraction_timestamp": "2025-08-13T10:45:00",
    "total_elements": 156,
    "extraction_library": "unstructured.io"
  },
  "extraction_options": {
    "extract_images": false,
    "extract_tables": true,
    "chunk_by_title": true
  },
  "elements": [...],  // Raw unstructured elements
  "structured_data": {
    "text_blocks": [...],
    "tables": [...],
    "titles": [...],
    "headers": [...],
    "footers": [...],
    "images": [...],
    "raw_text": "..."
  }
}
```

## Comparison with Other Libraries

**Unstructured.io Advantages:**
- AI-powered element detection (titles, tables, headers)
- Better handling of complex layouts
- Table structure recognition
- Document chunking strategies
- Multi-modal extraction (text, images, tables)

**vs pdfplumber:**
- More intelligent element classification
- Better table extraction
- Handles scanned documents better

**vs PyPDF2:**
- Much more advanced parsing
- Layout-aware extraction
- Better handling of complex PDFs

## Testing Results

✅ **Successfully tested with 3 different PDF formats:**

### F5.pdf (Foodics Format)
- **Elements**: 2 extracted
- **Content**: Purchase order with restaurant details
- **Key Data**: Customer name, PO number, items, quantities, prices
- **Raw Text**: 850 characters extracted

### Atrade.pdf (ATRADE Format) 
- **Elements**: 5 extracted
- **Content**: Detailed purchase order with VAT information
- **Key Data**: Customer details, supplier info, item descriptions
- **Raw Text**: 2025 characters extracted

### B202507-15118.pdf (Alternative Format)
- **Elements**: 3 extracted  
- **Content**: Different layout PDF structure
- **Raw Text**: 1206 characters extracted

**Total Success Rate**: 3/3 PDFs processed successfully!

## Dependencies

Pre-installed in the virtual environment:
- unstructured[pdf] - Core extraction library
- tkinter - GUI interface (usually included with Python)
- All required ML dependencies for document processing

## Self-Sufficient Design

This tool is completely isolated from the main invoice system:
- Own virtual environment
- Own dependencies
- Independent operation
- No conflicts with main system

Perfect for testing unstructured.io extraction quality against the current pdfplumber approach!