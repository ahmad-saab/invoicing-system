#!/usr/bin/env python3
"""
Simplified parser using unstructured.io for better extraction
Uses email as primary identifier and gets all customer info from database
"""
import re
import sqlite3
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

# Import unstructured library
try:
    from unstructured.partition.auto import partition
    from unstructured.partition.pdf import partition_pdf
    from unstructured.partition.html import partition_html
    from unstructured.partition.xlsx import partition_xlsx
    from unstructured.partition.image import partition_image
    from unstructured.partition.text import partition_text
    from unstructured.documents.elements import Table, Title, NarrativeText
except ImportError:
    print("Error: unstructured library not found!")
    print("Please install: pip install 'unstructured[all-docs]'")
    raise

class SimpleParserUnstructured:
    """
    Simple parser using unstructured.io that:
    1. Uses email to identify customer (from SMTP in production)
    2. Gets all customer info from database
    3. Extracts product table using unstructured.io
    4. Maps product names using database mappings
    5. Uses database pricing (not PDF pricing)
    """
    
    def __init__(self, db_path: str = "test_customers.db"):
        self.db_path = db_path
    
    def parse_lpo(self, file_path: str, customer_email: str = None) -> Dict[str, Any]:
        """Main parsing function"""
        result = {
            'status': 'success',
            'customer': None,
            'items': [],
            'totals': {},
            'errors': [],
            'debug_info': {}
        }
        
        try:
            # Step 1: Extract elements using unstructured.io (auto-detects format)
            print(f"Extracting from {file_path} using unstructured.io...")
            
            # Get file extension to determine format
            file_ext = Path(file_path).suffix.lower()
            
            # Use appropriate partition function based on file type
            if file_ext == '.pdf':
                elements = partition_pdf(
                    filename=file_path,
                    strategy="hi_res",
                    infer_table_structure=True
                )
            elif file_ext in ['.html', '.htm']:
                elements = partition_html(filename=file_path)
            elif file_ext in ['.xlsx', '.xls']:
                elements = partition_xlsx(filename=file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
                elements = partition_image(
                    filename=file_path,
                    strategy="hi_res",
                    infer_table_structure=True
                )
            elif file_ext in ['.txt']:
                elements = partition_text(filename=file_path)
            else:
                # Use auto-detection for unknown formats or email bodies
                elements = partition(
                    filename=file_path,
                    strategy="hi_res",
                    infer_table_structure=True
                )
            
            result['debug_info']['total_elements'] = len(elements)
            result['debug_info']['element_types'] = {}
            
            # Categorize elements
            tables = []
            text_content = []
            all_text_including_tables = []  # Include everything for product search
            
            for element in elements:
                element_type = type(element).__name__
                result['debug_info']['element_types'][element_type] = result['debug_info']['element_types'].get(element_type, 0) + 1
                
                all_text_including_tables.append(str(element))
                
                if isinstance(element, Table):
                    tables.append(element)
                else:
                    text_content.append(str(element))
            
            full_text = '\n'.join(text_content)
            complete_text = '\n'.join(all_text_including_tables)  # All content including tables
            
            print(f"Found {len(tables)} table elements")
            result['debug_info']['tables_found'] = len(tables)
            
            # Step 2: Find customer by email (if not provided, try to extract)
            if not customer_email:
                customer_email = self._extract_email(full_text)
            
            if not customer_email:
                result['errors'].append("No customer email provided or found")
                return result
            
            # Step 3: Get customer from database (pass full text for branch detection)
            customer = self._get_customer_by_email(customer_email, full_text)
            if not customer:
                result['errors'].append(f"Customer not found for email: {customer_email}")
                return result
            
            result['customer'] = customer
            
            # Step 4: Add branch info if detected
            branch = self._identify_branch(full_text, customer_email)
            if branch:
                result['customer']['branch'] = branch
                result['customer']['detected_location'] = branch['branch_name']
                # Update shipping address if branch has specific delivery address
                if branch.get('delivery_address'):
                    result['customer']['shipping_address'] = branch['delivery_address']
            
            # Step 5: Extract PO number
            po_number = self._extract_po_number(full_text)
            result['po_number'] = po_number
            
            # Step 6: Extract product items from tables and complete text
            # Also pass debug info to see what's in the document
            result['debug_info']['complete_text_preview'] = complete_text[:1000]  # First 1000 chars
            items = self._extract_items_from_tables(tables, complete_text, customer_email)
            result['debug_info']['items_extracted'] = len(items)
            
            # Step 7: Map products and get pricing from database
            mapped_items = self._map_products(items, customer_email)
            result['items'] = mapped_items
            
            # Step 8: Calculate totals
            result['totals'] = self._calculate_totals(mapped_items, customer.get('vat_rate', 5.0))
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
            print(f"Error: {e}")
        
        return result
    
    def _extract_items_from_tables(self, tables: List, complete_text: str, customer_email: str) -> List[Dict]:
        """Search for customer's mapped products in the extracted text"""
        items = []
        
        print(f"\n=== Searching for customer's products in extracted text ===")
        
        # Get customer's product mappings from database
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT lpo_product_name FROM product_mappings 
            WHERE customer_email = ? AND active = 1
        ''', (customer_email,))
        customer_mappings = cursor.fetchall()
        conn.close()
        
        print(f"Customer has {len(customer_mappings)} product mappings to search for")
        
        # Convert complete text to uppercase for case-insensitive search
        complete_upper = complete_text.upper()
        
        # For each product in customer's mappings, search if it exists in the PDF
        for mapping in customer_mappings:
            product_name = mapping['lpo_product_name']
            product_upper = product_name.upper()
            
            print(f"\nSearching for: {product_name}")
            
            # Check if this product appears in the extracted text
            if product_upper in complete_upper:
                print(f"  ✓ Found '{product_name}' in document")
                
                # Find the position of the product in the text
                position = complete_upper.find(product_upper)
                
                # Look for a quantity near this product (before or after)
                # Get surrounding text (100 chars before and after)
                start = max(0, position - 100)
                end = min(len(complete_text), position + len(product_upper) + 100)
                context = complete_text[start:end]
                
                print(f"  Context: ...{context}...")
                
                # Look for numbers that could be quantities in the context
                numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', context)
                
                # Find the most likely quantity (usually a small number)
                quantity = None
                for num_str in numbers:
                    try:
                        num = float(num_str)
                        # Quantities are typically 1-1000, prices are larger
                        if 0 < num <= 1000 and num != int(product_upper.count('X')):  # Avoid matching package size
                            quantity = num
                            print(f"  Found quantity: {quantity}")
                            break
                    except:
                        continue
                
                if quantity is None:
                    quantity = 1.0  # Default to 1 if no quantity found
                    print(f"  No quantity found, defaulting to 1")
                
                items.append({
                    'lpo_product_name': product_name,  # Use exact mapping name
                    'quantity': quantity,
                    'raw_text': context.strip(),
                    'extraction_method': 'reverse_lookup'
                })
            else:
                print(f"  ✗ '{product_name}' not found in document")
        
        # Fallback: if no products found via reverse lookup, try generic extraction
        if not items:
            print("\n=== No products found via reverse lookup, trying generic extraction ===")
            
            for table_idx, table in enumerate(tables):
                print(f"\n=== Processing Table {table_idx + 1} ===")
                table_text = str(table)
                print(f"Table content: {table_text[:500]}...")
                
                # Check if this is a product table - added more variations
                table_lower = table_text.lower()
                if not any(indicator in table_lower for indicator in ['article', 'item', 'product', 'qty', 'quantity', 'unit', 'service', 'uom']):
                    print(f"Table {table_idx + 1} doesn't appear to be a product table")
                    continue
                    
                print(f"Table {table_idx + 1} is a product table")
                
                # Extract what's actually in the table
                # Remove header portion to get to the data
                data_part = table_text
                for marker in ['Price Total', 'Unit Price', 'Price', 'Qty Unit']:
                    if marker in table_text:
                        parts = table_text.split(marker, 1)
                        if len(parts) > 1:
                            data_part = parts[1]
                            break
                
                print(f"Data part to analyze: {data_part[:400]}...")
                
                # Extract all numbers from the text for quantity detection
                all_numbers = re.findall(r'\d+\.?\d*', data_part)
                print(f"All numbers found: {all_numbers[:10]}")  # Show first 10 numbers
                
                # Look for patterns: text followed by unit (CAN/TIN/PKT) followed by quantity
                # This should work for most LPO formats
                # Example: "Oil Cuisine Bunge Pro 10L Emirates Golf Club CAN 20 85.00"
                
                # Pattern: capture text before common units or size patterns (1x10LTR), then quantity
                # Handle both "Product CAN 20" and "Product 1x10LTR 4.00" formats
                generic_patterns = [
                    r'([A-Za-z0-9\s]+?)\s+(CAN|TIN|PKT|BOX|CTN|BOTTLE|PCS|EACH)\s+(\d+(?:\.\d+)?)\s',  # Unit pattern
                    r'([A-Za-z0-9\s]+?)\s+(\d+x\d+(?:LTR|L|KG|ML))\s+(\d+(?:\.\d+)?)\s',  # Size pattern like 1x10LTR
                ]
                
                for generic_pattern in generic_patterns:
                    matches = re.finditer(generic_pattern, data_part, re.IGNORECASE)
                    for match in matches:
                        # Get the text before the unit - this should contain the product name
                        text_before = match.group(1).strip()
                        unit = match.group(2)
                        quantity = float(match.group(3))
                        
                        # Clean up the text - remove delivery location, item codes etc
                        # Look for product-like patterns (contains numbers with L/ML/KG or contains Oil/Bunge etc)
                        words = text_before.split()
                        product_name = ""
                        
                        # Build product name by looking for relevant words
                        for i, word in enumerate(words):
                            # Start collecting from where product names typically start
                            if any(indicator in word.upper() for indicator in ['OIL', 'BUNGE', 'CUISINE']) or re.match(r'\d+L|\d+ML|\d+KG', word, re.IGNORECASE):
                                # Found start of product, collect from here
                                product_name = ' '.join(words[i:])
                                break
                        
                        # If no specific product pattern found, take the last few words before unit
                        if not product_name and len(words) > 0:
                            # Take last 3-4 words as product name (skip location names)
                            product_name = ' '.join(words[-4:]) if len(words) > 4 else ' '.join(words)
                        
                        if product_name and quantity:
                            print(f"  Found: Product='{product_name}', Unit={unit}, Quantity={quantity}")
                            items.append({
                                'lpo_product_name': product_name,
                                'quantity': quantity,
                                'raw_text': match.group(0),
                                'extraction_method': 'generic_pattern'
                            })
        
        print(f"\n=== Total items extracted: {len(items)} ===")
        return items
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        for email in emails:
            # Skip common sender emails
            if not any(skip in email.lower() for skip in ['noreply', 'donotreply', 'system']):
                return email.lower()
        
        return None
    
    def _get_customer_by_email(self, email: str, lpo_text: str = None) -> Optional[Dict]:
        """Get customer details from database, handling multi-location customers"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # First, get all customers with this email
        cursor.execute('''
            SELECT * FROM customers WHERE email = ? AND active = 1
        ''', (email,))
        
        customers = cursor.fetchall()
        
        if not customers:
            conn.close()
            return None
        
        # If only one customer, return it
        if len(customers) == 1:
            conn.close()
            return dict(customers[0])
        
        # Multiple customers with same email - need to identify which branch
        print(f"\nMultiple locations found for {email}, detecting branch...")
        
        if lpo_text:
            # Get branch identifiers for this email
            cursor.execute('''
                SELECT * FROM branch_identifiers WHERE customer_email = ?
            ''', (email,))
            
            branches = cursor.fetchall()
            text_upper = lpo_text.upper()
            
            # Try to match branch identifier in LPO text
            for branch in branches:
                identifier_upper = branch['branch_identifier'].upper()
                if identifier_upper in text_upper:
                    print(f"  ✓ Branch identified: {branch['branch_name']} (matched '{branch['branch_identifier']}')")
                    
                    # Find the customer with matching unique_alias or delivery address
                    for customer in customers:
                        customer_dict = dict(customer)
                        # Check if shipping address matches or if customer name contains branch name
                        if (branch['delivery_address'] and 
                            branch['delivery_address'] in customer_dict.get('shipping_address', '')) or \
                           (branch['branch_name'] in customer_dict.get('customer_name', '')):
                            print(f"  → Selected: {customer_dict['customer_name']}")
                            conn.close()
                            return customer_dict
        
        # If no branch identified, return the first customer as fallback
        print(f"  ⚠ Could not identify specific branch, using default")
        conn.close()
        return dict(customers[0])
    
    def _identify_branch(self, text: str, customer_email: str) -> Optional[Dict]:
        """Identify branch if customer has multiple locations"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM branch_identifiers WHERE customer_email = ?
        ''', (customer_email,))
        
        branches = cursor.fetchall()
        conn.close()
        
        if branches:
            text_lower = text.lower()
            for branch in branches:
                if branch['branch_identifier'].lower() in text_lower:
                    return dict(branch)
        
        return None
    
    def _extract_po_number(self, text: str) -> Optional[str]:
        """Extract PO/Order number from text"""
        patterns = [
            r'Order\s*No[:\.]?\s*([A-Z0-9\-]+)',
            r'Order\s*Number[:\.]?\s*([A-Z0-9\-]+)',
            r'PO\s*No[:\.]?\s*([A-Z0-9\-]+)',
            r'PO\s*Number[:\.]?\s*([A-Z0-9\-]+)',
            r'P\.O\.\s*([A-Z0-9\-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _map_products(self, items: List[Dict], customer_email: str) -> List[Dict]:
        """Map extracted items to database products using intelligent matching"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get ALL mappings for this customer first
        cursor.execute('''
            SELECT * FROM product_mappings 
            WHERE customer_email = ? AND active = 1
        ''', (customer_email,))
        all_mappings = cursor.fetchall()
        
        print(f"\nCustomer has {len(all_mappings)} product mappings")
        for mapping in all_mappings:
            print(f"  - {mapping['lpo_product_name']} -> {mapping['system_product_name']}")
        
        mapped_items = []
        
        for item in items:
            print(f"\nTrying to map: '{item['lpo_product_name']}'")
            
            # First try exact match
            mapping = None
            for map_row in all_mappings:
                if map_row['lpo_product_name'].upper() == item['lpo_product_name'].upper():
                    mapping = map_row
                    print(f"  Exact match found!")
                    break
            
            # If no exact match, try intelligent matching
            if not mapping:
                item_upper = item['lpo_product_name'].upper()
                best_match = None
                best_score = 0
                
                for map_row in all_mappings:
                    map_name_upper = map_row['lpo_product_name'].upper()
                    score = 0
                    
                    # Special case: if we extracted just a unit spec like "TIN 10 LITER"
                    # and the mapping contains a similar unit spec, that's likely a match
                    if all(unit in item_upper for unit in ['TIN', 'LITER']) or all(unit in item_upper for unit in ['PKT', 'LTR']):
                        # This is a unit specification, check if mapping has similar unit
                        if 'TIN' in item_upper and 'TIN' in map_name_upper:
                            # Both have TIN, likely the same product
                            score = 0.8
                            print(f"  Unit-based match: Both have TIN container")
                        elif 'PKT' in item_upper and 'PKT' in map_name_upper:
                            # Both have PKT, likely the same product  
                            score = 0.8
                            print(f"  Unit-based match: Both have PKT container")
                    
                    # Check if the extracted item is contained in the mapping name
                    elif item_upper in map_name_upper:
                        score = len(item_upper) / len(map_name_upper)
                        print(f"  '{item_upper}' is contained in '{map_name_upper}' (score: {score:.2f})")
                    
                    # Check if the mapping name contains the extracted item
                    elif map_name_upper in item_upper:
                        score = len(map_name_upper) / len(item_upper)
                        print(f"  '{map_name_upper}' is contained in '{item_upper}' (score: {score:.2f})")
                    
                    # Check for common important tokens
                    else:
                        item_tokens = set(item_upper.split())
                        map_tokens = set(map_name_upper.split())
                        common_tokens = item_tokens & map_tokens
                        
                        if common_tokens:
                            # Regular word matching
                            score = len(common_tokens) / max(len(item_tokens), len(map_tokens))
                            if common_tokens:
                                print(f"  Common tokens: {common_tokens} (score: {score:.2f})")
                    
                    if score > best_score:
                        best_score = score
                        best_match = map_row
                
                # Use best match if score is reasonable
                if best_match and best_score >= 0.3:  # Lower threshold for better matching
                    mapping = best_match
                    print(f"  Best match: '{mapping['lpo_product_name']}' (score: {best_score:.2f})")
            
            if mapping:
                mapped_items.append({
                    'lpo_product_name': mapping['lpo_product_name'],  # Use the mapping name, not extracted text!
                    'system_product_name': mapping['system_product_name'],
                    'quantity': item['quantity'],
                    'unit': mapping['unit'],
                    'unit_price': mapping['unit_price'],
                    'total': item['quantity'] * mapping['unit_price']
                })
            else:
                # No mapping found - add as unmapped
                mapped_items.append({
                    'lpo_product_name': item['lpo_product_name'],
                    'system_product_name': 'UNMAPPED: ' + item['lpo_product_name'],
                    'quantity': item['quantity'],
                    'unit': 'EACH',
                    'unit_price': 0,
                    'total': 0,
                    'needs_mapping': True
                })
        
        conn.close()
        return mapped_items
    
    def _calculate_totals(self, items: List[Dict], vat_rate: float = 5.0) -> Dict:
        """Calculate invoice totals"""
        subtotal = sum(item['total'] for item in items)
        vat = subtotal * (vat_rate / 100)
        total = subtotal + vat
        
        return {
            'subtotal': round(subtotal, 2),
            'vat_rate': vat_rate,
            'vat_amount': round(vat, 2),
            'total': round(total, 2)
        }


# Test the parser
if __name__ == "__main__":
    parser = SimpleParserUnstructured()
    
    # Test with a sample PDF
    test_file = './invoice_system_version_1/test lpos/2508501751 102180 A T R A D E MENA TRADING L.L.C.PDF'
    
    if Path(test_file).exists():
        print(f"\n=== Testing: {test_file} ===")
        # Simulate email from SMTP
        result = parser.parse_lpo(test_file, customer_email='a.krishnan@dubaigolf.com')
        
        if result['customer']:
            print(f"\nCustomer: {result['customer']['customer_name']}")
            print(f"Email: {result['customer']['email']}")
            print(f"TRN: {result['customer']['trn']}")
            
            if result['items']:
                print(f"\nItems found: {len(result['items'])}")
                for item in result['items']:
                    print(f"  - {item['lpo_product_name']} -> {item['system_product_name']}")
                    print(f"    Quantity: {item['quantity']} {item['unit']}")
                    print(f"    Price: {item['unit_price']} = Total: {item['total']}")
            
            if result['totals']:
                print(f"\nTotals:")
                print(f"  Subtotal: {result['totals']['subtotal']}")
                print(f"  VAT ({result['totals']['vat_rate']}%): {result['totals']['vat_amount']}")
                print(f"  Total: {result['totals']['total']}")
        else:
            print(f"Errors: {result['errors']}")