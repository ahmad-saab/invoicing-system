#!/usr/bin/env python3
"""
Simple runner for the Unstructured.io PDF Extractor
Self-sufficient tool with its own virtual environment
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    venv_dir = script_dir / "venv"
    
    # Check if virtual environment exists
    if not venv_dir.exists():
        print("❌ Virtual environment not found!")
        print(f"Expected location: {venv_dir}")
        print("\nTo set up the environment:")
        print("1. cd unstructured")
        print("2. python3 -m venv venv")
        print("3. source venv/bin/activate")
        print("4. pip install unstructured[pdf]")
        return 1
        
    # Get python executable from venv
    python_exe = venv_dir / "bin" / "python"
    if not python_exe.exists():
        print("❌ Python executable not found in virtual environment!")
        print(f"Expected: {python_exe}")
        return 1
        
    # Get the extractor script
    extractor_script = script_dir / "unstructured_extractor.py"
    if not extractor_script.exists():
        print("❌ Extractor script not found!")
        print(f"Expected: {extractor_script}")
        return 1
        
    print("🚀 Starting Unstructured.io PDF Extractor...")
    print(f"📁 Working directory: {script_dir}")
    print(f"🐍 Using Python: {python_exe}")
    print(f"📄 Running script: {extractor_script}")
    print()
    
    # Run the extractor with the venv python
    try:
        subprocess.run([str(python_exe), str(extractor_script)], 
                      cwd=str(script_dir), check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running extractor: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n👋 Extractor stopped by user")
        return 0
        
    return 0

if __name__ == "__main__":
    sys.exit(main())