#!/usr/bin/env python3
"""Test the improved mapping system"""
from mapping_parser import MappingParser
import json

# Test with the invoice
parser = MappingParser()
result = parser.parse_with_mappings(
    './invoice_system_version_1/test lpos/ATRADEMENA 4710879730.pdf',
    customer_id='UPSCALE RESTAURANT L.L.C_55'
)

print("=== MAPPING TEST RESULTS ===")
print(f"Customer: {result.get('customer_id')}")
print(f"Total mappings used: {len(result.get('field_mappings_used', {}))}")
print(f"Products found: {len(result.get('items', []))}")
print()

for i, item in enumerate(result.get('items', []), 1):
    print(f"Product {i}:")
    print(f"  Original: {item.get('description')}")
    print(f"  Mapped to: {item.get('mapped_product', 'NO MAPPING')}")
    print(f"  Quantity: {item.get('quantity')}")
    print(f"  Unit Price: {item.get('unit_price')}")
    print()

# Show unmapped text
unmapped = result.get('unmapped_text', [])
if unmapped:
    print(f"\nUnmapped text items: {len(unmapped)}")
    # Show first 5 unmapped items
    for text in unmapped[:5]:
        if len(text) > 100:
            print(f"  - {text[:100]}...")
        else:
            print(f"  - {text}")

print("\n=== TEST COMPLETE ===")