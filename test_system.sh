#!/bin/bash

echo "=========================================="
echo "Testing Simple Invoice Parser System"
echo "=========================================="

# Activate virtual environment
source venv/bin/activate

echo ""
echo "1. Testing API Server..."
python3 -c "
import requests
try:
    r = requests.get('http://localhost:8000/')
    if r.status_code == 200:
        print('✓ API server is running')
        status = requests.get('http://localhost:8000/api/status').json()
        print(f'  - Customers: {status[\"data\"][\"customers\"]}')
        print(f'  - Mappings: {status[\"data\"][\"mappings\"]}')
    else:
        print('✗ API server not responding')
except:
    print('✗ API server not running - start with: ./start_app.sh')
"

echo ""
echo "2. Testing Simple Parser..."
python3 -c "
from simple_extractor import SimpleDataExtractor
import os

parser = SimpleDataExtractor()
test_file = 'test lpos/GCD.pdf'

if os.path.exists(test_file):
    result = parser.extract_file(test_file)
    customer = result.get('customer_match', {})
    
    print('✓ Simple parser working')
    if customer.get('customer_name'):
        print(f'  - Customer matched: {customer[\"customer_name\"]}')
        print(f'  - Confidence: {result[\"confidence_score\"]:.1%}')
    else:
        print('  - No customer match (add mappings in frontend)')
else:
    print('✗ Test file not found')
"

echo ""
echo "3. Testing Mapping Parser..."
python3 -c "
from mapping_parser import MappingParser

parser = MappingParser()
test_file = 'test lpos/GCD.pdf'

result = parser.parse_with_mappings(test_file)
print('✓ Mapping parser working')
print(f'  - Customer detected: {result[\"customer_id\"]}')
print(f'  - Items found: {len(result[\"items\"])}')
print(f'  - Mappings used: {result[\"mappings_used\"]}')

if result['unmapped_count'] > 0:
    print(f'  - Unmapped text: {result[\"unmapped_count\"]} lines')
    print('    (Define mappings in frontend to map this text)')
"

echo ""
echo "=========================================="
echo "System Test Complete!"
echo ""
echo "To start the full system:"
echo "  ./start_app.sh"
echo ""
echo "Then visit:"
echo "  Frontend: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
echo "=========================================="