#!/usr/bin/env python3
"""
Unstructured.io PDF Extractor - Command Line Version
Simple self-sufficient tool to extract data from PDFs using unstructured.io library
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.staging.base import convert_to_dict
    print("✅ Unstructured library loaded successfully")
except ImportError as e:
    print(f"❌ Error: unstructured library not found! {e}")
    print("Please run: pip install unstructured[pdf]")
    sys.exit(1)


class UnstructuredExtractorCLI:
    def __init__(self, output_dir="extracted_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_data(self, file_path, extract_images=False, extract_tables=True, chunk_by_title=True):
        """Extract data from PDF using unstructured.io"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        file_path = Path(file_path)
        file_name = file_path.stem
        
        print(f"🔍 Starting extraction of: {file_path.name}")
        print(f"📚 Using unstructured.io library...")
        
        # Configure extraction parameters
        extract_params = {
            "filename": str(file_path),
            "extract_images_in_pdf": extract_images,
            "infer_table_structure": extract_tables,
            "chunking_strategy": "by_title" if chunk_by_title else None,
            "include_page_breaks": True,
            "strategy": "hi_res"  # High resolution strategy for better extraction
        }
        
        print(f"⚙️  Extraction settings:")
        print(f"   - Strategy: hi_res")
        print(f"   - Extract images: {extract_images}")
        print(f"   - Extract tables: {extract_tables}")
        print(f"   - Chunk by title: {chunk_by_title}")
        
        # Extract using unstructured
        print("🔧 Partitioning PDF document...")
        try:
            elements = partition_pdf(**extract_params)
            print(f"✅ Extracted {len(elements)} elements from PDF")
        except Exception as e:
            print(f"❌ Error during PDF partitioning: {e}")
            raise
        
        # Convert to dictionary format
        print("🔄 Converting elements to structured data...")
        elements_dict = []
        for elem in elements:
            elem_data = {
                "type": str(type(elem).__name__),
                "text": str(elem),
                "metadata": {}
            }
            
            # Handle metadata safely
            try:
                metadata = getattr(elem, 'metadata', {})
                if metadata:
                    # Convert metadata to JSON-serializable format
                    elem_data["metadata"] = self._serialize_metadata(metadata)
            except Exception as e:
                print(f"Warning: Could not serialize metadata for element: {e}")
                
            elements_dict.append(elem_data)
        
        # Organize extracted data
        extracted_data = {
            "file_info": {
                "filename": file_path.name,
                "filepath": str(file_path),
                "extraction_timestamp": datetime.now().isoformat(),
                "total_elements": len(elements),
                "extraction_library": "unstructured.io",
                "extraction_strategy": "hi_res"
            },
            "extraction_options": {
                "extract_images": extract_images,
                "extract_tables": extract_tables,
                "chunk_by_title": chunk_by_title
            },
            "elements": elements_dict,
            "structured_data": self._structure_data(elements)
        }
        
        # Save to JSON file
        output_file = self.output_dir / f"{file_name}_unstructured_extraction.json"
        print(f"💾 Saving data to: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
        # Generate summary
        summary = self._generate_summary(extracted_data)
        summary_file = self.output_dir / f"{file_name}_extraction_summary.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
            
        print(f"📄 Summary saved to: {summary_file}")
        print("🎉 Extraction completed successfully!")
        
        return output_file, summary_file, extracted_data
    
    def _serialize_metadata(self, metadata):
        """Convert metadata to JSON-serializable format"""
        if isinstance(metadata, dict):
            result = {}
            for key, value in metadata.items():
                try:
                    # Test if value is JSON serializable
                    json.dumps(value)
                    result[key] = value
                except (TypeError, ValueError):
                    # Convert non-serializable objects to string
                    result[key] = str(value)
            return result
        else:
            return str(metadata)
        
    def _structure_data(self, elements):
        """Structure the extracted elements by type"""
        structured = {
            "text_blocks": [],
            "tables": [],
            "titles": [],
            "headers": [],
            "footers": [],
            "images": [],
            "metadata": [],
            "raw_text": ""
        }
        
        for element in elements:
            element_type = str(type(element).__name__)
            element_text = str(element)
            
            # Add to raw text
            structured["raw_text"] += element_text + "\n"
            
            # Get serializable metadata
            try:
                metadata = getattr(element, 'metadata', {})
                safe_metadata = self._serialize_metadata(metadata)
            except Exception:
                safe_metadata = {}
            
            # Categorize by element type
            if "Title" in element_type:
                structured["titles"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": safe_metadata
                })
            elif "Header" in element_type:
                structured["headers"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": safe_metadata
                })
            elif "Footer" in element_type:
                structured["footers"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": safe_metadata
                })
            elif "Table" in element_type:
                structured["tables"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": safe_metadata
                })
            elif "Image" in element_type:
                structured["images"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": safe_metadata
                })
            else:
                structured["text_blocks"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": safe_metadata
                })
                
        return structured
        
    def _generate_summary(self, data):
        """Generate a human-readable summary of the extraction"""
        structured = data["structured_data"]
        file_info = data["file_info"]
        
        summary = f"""
UNSTRUCTURED.IO PDF EXTRACTION SUMMARY
======================================

File: {file_info['filename']}
Extraction Time: {file_info['extraction_timestamp']}
Library: {file_info['extraction_library']}
Strategy: {file_info['extraction_strategy']}
Total Elements: {file_info['total_elements']}

ELEMENT BREAKDOWN:
- Text Blocks: {len(structured['text_blocks'])}
- Tables: {len(structured['tables'])}
- Titles: {len(structured['titles'])}
- Headers: {len(structured['headers'])}
- Footers: {len(structured['footers'])}
- Images: {len(structured['images'])}

EXTRACTED TITLES:
"""
        for i, title in enumerate(structured['titles'][:10], 1):
            summary += f"{i}. {title['text'][:100]}...\n"
            
        summary += f"""
EXTRACTED TABLES:
"""
        for i, table in enumerate(structured['tables'][:5], 1):
            summary += f"{i}. {table['text'][:200]}...\n"
            
        summary += f"""
RAW TEXT SAMPLE (first 500 chars):
{structured['raw_text'][:500]}...

RAW TEXT LENGTH: {len(structured['raw_text'])} characters

EXTRACTION OPTIONS USED:
- Extract Images: {data['extraction_options']['extract_images']}
- Extract Tables: {data['extraction_options']['extract_tables']}
- Chunk by Title: {data['extraction_options']['chunk_by_title']}
"""
        
        return summary


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Extract data from PDF using unstructured.io")
    parser.add_argument("pdf_file", help="Path to PDF file to extract")
    parser.add_argument("-o", "--output", default="extracted_data", 
                       help="Output directory (default: extracted_data)")
    parser.add_argument("--extract-images", action="store_true", 
                       help="Extract images from PDF")
    parser.add_argument("--no-tables", action="store_true", 
                       help="Skip table extraction")
    parser.add_argument("--no-chunking", action="store_true", 
                       help="Don't chunk by title")
    
    args = parser.parse_args()
    
    print("🚀 Starting Unstructured.io PDF Extractor (CLI Version)")
    print(f"📁 Output directory: {args.output}")
    
    # Check if we're in the right environment
    try:
        import unstructured
        print(f"✅ Unstructured library version: {unstructured.__version__}")
    except ImportError:
        print("❌ Unstructured library not found!")
        print("Please activate the virtual environment and install: pip install unstructured[pdf]")
        return 1
        
    # Create extractor and run
    try:
        extractor = UnstructuredExtractorCLI(output_dir=args.output)
        
        output_file, summary_file, data = extractor.extract_data(
            file_path=args.pdf_file,
            extract_images=args.extract_images,
            extract_tables=not args.no_tables,
            chunk_by_title=not args.no_chunking
        )
        
        print(f"\n📋 QUICK SUMMARY:")
        print(f"   📄 File: {data['file_info']['filename']}")
        print(f"   🔢 Elements: {data['file_info']['total_elements']}")
        print(f"   📝 Text blocks: {len(data['structured_data']['text_blocks'])}")
        print(f"   📊 Tables: {len(data['structured_data']['tables'])}")
        print(f"   📖 Titles: {len(data['structured_data']['titles'])}")
        print(f"   📏 Raw text: {len(data['structured_data']['raw_text'])} chars")
        print(f"\n💾 Files created:")
        print(f"   📋 JSON: {output_file}")
        print(f"   📄 Summary: {summary_file}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())