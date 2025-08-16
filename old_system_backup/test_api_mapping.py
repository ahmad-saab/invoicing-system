#!/usr/bin/env python3
"""Test the mapping via API"""
import requests
import json

# Test with a PDF file
pdf_path = './invoice_system_version_1/test lpos/ATRADEMENA 4710879730.pdf'

# Test with the mapping endpoint
with open(pdf_path, 'rb') as f:
    files = {'file': f}
    data = {'customer_id': 'UPSCALE RESTAURANT L.L.C_55'}
    
    response = requests.post('http://localhost:8001/api/parse/mapped', files=files, data=data)
    
if response.status_code == 200:
    result = response.json()
    print("=== API MAPPING TEST ===")
    print(f"Customer: {result.get('customer_id')}")
    print(f"Items found: {len(result.get('items', []))}")
    print()
    
    for i, item in enumerate(result.get('items', []), 1):
        print(f"Product {i}:")
        print(f"  Description: {item.get('description')}")
        print(f"  Mapped: {item.get('mapped_product', 'NO MAPPING')}")
        print(f"  Quantity: {item.get('quantity')}")
        print(f"  Price: {item.get('unit_price')}")
        print()
else:
    print(f"Error: {response.status_code}")
    print(response.text)