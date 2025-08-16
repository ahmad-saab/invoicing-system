#!/usr/bin/env python3
"""
Unstructured.io PDF Extractor with GUI
Simple self-sufficient tool to extract data from PDFs using unstructured.io library
"""

import os
import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from pathlib import Path

try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.staging.base import convert_to_dict
except ImportError:
    print("Error: unstructured library not found!")
    print("Please run: pip install unstructured[pdf]")
    sys.exit(1)


class UnstructuredExtractorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Unstructured.io PDF Extractor")
        self.root.geometry("800x600")
        
        # Variables
        self.selected_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "extracted_data"))
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Unstructured.io PDF Data Extractor", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # File selection
        ttk.Label(main_frame, text="Select PDF File:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.file_entry = ttk.Entry(file_frame, textvariable=self.selected_file, width=60)
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        browse_button.grid(row=0, column=1)
        
        file_frame.columnconfigure(0, weight=1)
        
        # Output directory
        ttk.Label(main_frame, text="Output Directory:").grid(row=3, column=0, sticky=tk.W, pady=(20, 5))
        
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_dir, width=60)
        self.output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        output_browse_button = ttk.Button(output_frame, text="Browse", command=self.browse_output_dir)
        output_browse_button.grid(row=0, column=1)
        
        output_frame.columnconfigure(0, weight=1)
        
        # Extraction options
        options_frame = ttk.LabelFrame(main_frame, text="Extraction Options", padding="10")
        options_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=20)
        
        self.extract_images = tk.BooleanVar(value=False)
        self.extract_tables = tk.BooleanVar(value=True)
        self.chunk_by_title = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(options_frame, text="Extract Images", 
                       variable=self.extract_images).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Extract Tables", 
                       variable=self.extract_tables).grid(row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Chunk by Title", 
                       variable=self.chunk_by_title).grid(row=0, column=2, sticky=tk.W)
        
        # Extract button
        self.extract_button = ttk.Button(main_frame, text="Extract Data", 
                                        command=self.extract_data, style="Accent.TButton")
        self.extract_button.grid(row=6, column=0, columnspan=3, pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Status text
        self.status_text = tk.Text(main_frame, height=15, width=80)
        self.status_text.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Scrollbar for status text
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.status_text.yview)
        scrollbar.grid(row=8, column=3, sticky=(tk.N, tk.S))
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(8, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def browse_file(self):
        """Open file dialog to select PDF file"""
        file_path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.selected_file.set(file_path)
            
    def browse_output_dir(self):
        """Open directory dialog to select output directory"""
        dir_path = filedialog.askdirectory(title="Select output directory")
        if dir_path:
            self.output_dir.set(dir_path)
            
    def log_message(self, message):
        """Add message to status text with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.root.update()
        
    def extract_data(self):
        """Extract data from selected PDF using unstructured.io"""
        if not self.selected_file.get():
            messagebox.showerror("Error", "Please select a PDF file")
            return
            
        if not os.path.exists(self.selected_file.get()):
            messagebox.showerror("Error", "Selected file does not exist")
            return
            
        # Create output directory
        output_dir = Path(self.output_dir.get())
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Start extraction
        self.extract_button.config(state="disabled")
        self.progress.start(10)
        self.status_text.delete(1.0, tk.END)
        
        try:
            file_path = self.selected_file.get()
            file_name = Path(file_path).stem
            
            self.log_message(f"Starting extraction of: {Path(file_path).name}")
            self.log_message(f"Using unstructured.io library...")
            
            # Extract using unstructured
            self.log_message("Partitioning PDF document...")
            
            # Configure extraction parameters
            extract_params = {
                "filename": file_path,
                "extract_images_in_pdf": self.extract_images.get(),
                "infer_table_structure": self.extract_tables.get(),
                "chunking_strategy": "by_title" if self.chunk_by_title.get() else None,
                "include_page_breaks": True,
                "strategy": "hi_res"  # High resolution strategy for better extraction
            }
            
            elements = partition_pdf(**extract_params)
            self.log_message(f"Extracted {len(elements)} elements from PDF")
            
            # Convert to dictionary format
            self.log_message("Converting elements to structured data...")
            elements_dict = convert_to_dict(elements)
            
            # Organize extracted data
            extracted_data = {
                "file_info": {
                    "filename": Path(file_path).name,
                    "filepath": file_path,
                    "extraction_timestamp": datetime.now().isoformat(),
                    "total_elements": len(elements),
                    "extraction_library": "unstructured.io",
                    "extraction_strategy": "hi_res"
                },
                "extraction_options": {
                    "extract_images": self.extract_images.get(),
                    "extract_tables": self.extract_tables.get(),
                    "chunk_by_title": self.chunk_by_title.get()
                },
                "elements": elements_dict,
                "structured_data": self._structure_data(elements)
            }
            
            # Save to JSON file
            output_file = output_dir / f"{file_name}_unstructured_extraction.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                
            self.log_message(f"Data saved to: {output_file}")
            
            # Generate summary
            summary = self._generate_summary(extracted_data)
            summary_file = output_dir / f"{file_name}_extraction_summary.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
                
            self.log_message(f"Summary saved to: {summary_file}")
            self.log_message("✅ Extraction completed successfully!")
            
            # Show success message
            messagebox.showinfo("Success", 
                              f"Extraction completed!\n\n"
                              f"JSON data: {output_file}\n"
                              f"Summary: {summary_file}")
            
        except Exception as e:
            self.log_message(f"❌ Error during extraction: {str(e)}")
            messagebox.showerror("Extraction Error", f"Failed to extract data:\n{str(e)}")
            
        finally:
            self.progress.stop()
            self.extract_button.config(state="normal")
            
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
            
            # Categorize by element type
            if "Title" in element_type:
                structured["titles"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": getattr(element, 'metadata', {})
                })
            elif "Header" in element_type:
                structured["headers"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": getattr(element, 'metadata', {})
                })
            elif "Footer" in element_type:
                structured["footers"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": getattr(element, 'metadata', {})
                })
            elif "Table" in element_type:
                structured["tables"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": getattr(element, 'metadata', {})
                })
            elif "Image" in element_type:
                structured["images"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": getattr(element, 'metadata', {})
                })
            else:
                structured["text_blocks"].append({
                    "text": element_text,
                    "type": element_type,
                    "metadata": getattr(element, 'metadata', {})
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
RAW TEXT LENGTH: {len(structured['raw_text'])} characters

EXTRACTION OPTIONS USED:
- Extract Images: {data['extraction_options']['extract_images']}
- Extract Tables: {data['extraction_options']['extract_tables']}
- Chunk by Title: {data['extraction_options']['chunk_by_title']}
"""
        
        return summary
        
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    print("Starting Unstructured.io PDF Extractor...")
    
    # Check if we're in the right environment
    try:
        import unstructured
        print(f"✅ Unstructured library version: {unstructured.__version__}")
    except ImportError:
        print("❌ Unstructured library not found!")
        print("Please activate the virtual environment and install: pip install unstructured[pdf]")
        return
        
    # Start GUI
    app = UnstructuredExtractorGUI()
    app.run()


if __name__ == "__main__":
    main()