#!/usr/bin/env python3
"""
Simplified parser that uses email as primary identifier
and gets all customer info from database
"""
import re
import sqlite3
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import pdfplumber
from datetime import datetime

class SimpleParser:
    """
    Simple parser that:
    1. Extracts email from PDF to identify customer
    2. Gets all customer info from database
    3. Extracts product table from PDF
    4. Maps product names using database mappings
    5. Uses database pricing (not PDF pricing)
    """
    
    def __init__(self, db_path: str = "test_customers.db"):
        self.db_path = db_path
    
    def parse_lpo(self, pdf_path: str) -> Dict[str, Any]:
        """Main parsing function"""
        result = {
            'status': 'success',
            'customer': None,
            'items': [],
            'totals': {},
            'errors': []
        }
        
        try:
            # Step 1: Extract text and tables from PDF
            pdf_data = self._extract_pdf_data(pdf_path)
            
            # Step 2: Find customer by email
            customer_email = self._extract_email(pdf_data['text'])
            if not customer_email:
                result['errors'].append("No email found in PDF")
                return result
            
            # Step 3: Get customer from database
            customer = self._get_customer_by_email(customer_email)
            if not customer:
                result['errors'].append(f"Customer not found for email: {customer_email}")
                return result
            
            result['customer'] = customer
            
            # Step 4: Check for branch identifier if customer has multiple branches
            branch = self._identify_branch(pdf_data['text'], customer_email)
            if branch:
                result['customer']['branch'] = branch
            
            # Step 5: Extract PO number
            po_number = self._extract_po_number(pdf_data['text'])
            result['po_number'] = po_number
            
            # Step 6: Extract product items from tables
            items = self._extract_items(pdf_data['tables'], pdf_data['text'])
            
            # Step 7: Map products and get pricing from database
            mapped_items = self._map_products(items, customer_email)
            result['items'] = mapped_items
            
            # Step 8: Calculate totals
            result['totals'] = self._calculate_totals(mapped_items, customer['vat_rate'])
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
        
        return result
    
    def _extract_pdf_data(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text and tables from PDF"""
        data = {'text': '', 'tables': []}
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract text
                data['text'] += page.extract_text() or ''
                
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    data['tables'].extend(tables)
        
        return data
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Return first valid email (usually the customer's email)
        for email in emails:
            # Skip common sender emails
            if not any(skip in email.lower() for skip in ['noreply', 'donotreply', 'system']):
                return email.lower()
        
        return None
    
    def _get_customer_by_email(self, email: str) -> Optional[Dict]:
        """Get customer details from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM customers WHERE email = ? AND active = 1
        ''', (email,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
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
    
    def _extract_items(self, tables: List, text: str) -> List[Dict]:
        """Extract product items from tables with improved column detection"""
        items = []
        
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:
                continue
            
            print(f"\n=== Analyzing Table {table_idx + 1} ===")
            print(f"Table has {len(table)} rows and {len(table[0]) if table else 0} columns")
            
            # Try to identify product table by headers
            headers = [str(cell).lower() if cell else '' for cell in table[0]]
            print(f"Headers: {headers}")
            
            # Look for product-related headers with more variations
            product_indicators = ['item', 'product', 'description', 'article', 'service', 'text', 'name', 'material']
            qty_indicators = ['qty', 'quantity', 'quan', 'qt', 'pieces', 'units', 'amount']
            unit_indicators = ['uom', 'unit', 'um', 'measure']
            
            product_col = -1
            qty_col = -1
            unit_col = -1
            
            # Find column indices
            for i, header in enumerate(headers):
                header_clean = header.strip().lower()
                
                # Check for product column
                if product_col == -1:
                    if any(ind in header_clean for ind in product_indicators):
                        product_col = i
                        print(f"Found product column at index {i}: '{header}'")
                
                # Check for quantity column
                if qty_col == -1:
                    if any(ind in header_clean for ind in qty_indicators):
                        qty_col = i
                        print(f"Found quantity column at index {i}: '{header}'")
                
                # Check for unit column
                if unit_col == -1:
                    if any(ind in header_clean for ind in unit_indicators):
                        unit_col = i
                        print(f"Found unit column at index {i}: '{header}'")
            
            # If we didn't find headers, try to detect by content patterns
            if product_col == -1 and len(table) > 1:
                print("No product header found, analyzing content...")
                for col_idx in range(len(table[0])):
                    # Check if this column has text that looks like products
                    sample_values = []
                    for row_idx in range(1, min(4, len(table))):
                        if col_idx < len(table[row_idx]):
                            val = str(table[row_idx][col_idx]).strip()
                            if val and not val.replace('.', '').replace(',', '').isdigit():
                                sample_values.append(val)
                    
                    # If we have non-numeric values, might be product column
                    if len(sample_values) >= 1:
                        # Check if it contains product-like words
                        combined = ' '.join(sample_values).lower()
                        if any(word in combined for word in ['oil', 'bunge', 'product', 'item']):
                            product_col = col_idx
                            print(f"Detected product column at index {col_idx} by content")
                            break
            
            # If we found product column, extract items
            if product_col >= 0:
                print(f"Extracting items from table...")
                for row_idx, row in enumerate(table[1:], 1):  # Skip header row
                    if len(row) > product_col:
                        product_name = str(row[product_col]).strip() if row[product_col] else ''
                        
                        # Skip empty rows or totals
                        if product_name and not any(skip in product_name.lower() 
                                                   for skip in ['total', 'subtotal', 'vat', 'tax', 'gross', 'net']):
                            
                            # Extract quantity
                            quantity = 1.0
                            if qty_col >= 0 and qty_col < len(row):
                                qty_str = str(row[qty_col]).strip()
                                # Clean quantity string
                                qty_str = qty_str.replace(',', '').replace(' ', '')
                                try:
                                    quantity = float(qty_str)
                                    print(f"  Row {row_idx}: Product='{product_name[:30]}...', Quantity={quantity}")
                                except:
                                    print(f"  Row {row_idx}: Product='{product_name[:30]}...', Quantity=1.0 (failed to parse '{qty_str}')")
                                    quantity = 1.0
                            else:
                                print(f"  Row {row_idx}: Product='{product_name[:30]}...', Quantity=1.0 (no qty column)")
                            
                            # Extract unit if available
                            unit = 'EACH'
                            if unit_col >= 0 and unit_col < len(row):
                                unit = str(row[unit_col]).strip() or 'EACH'
                            
                            items.append({
                                'lpo_product_name': product_name,
                                'quantity': quantity,
                                'unit': unit,
                                'raw_row': row,
                                'table_index': table_idx,
                                'row_index': row_idx
                            })
            else:
                print(f"No product column found in this table")
        
        print(f"\n=== Total items extracted: {len(items)} ===")
        return items
    
    def _map_products(self, items: List[Dict], customer_email: str) -> List[Dict]:
        """Map LPO product names to system products and get pricing from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        mapped_items = []
        
        for item in items:
            # Look for exact mapping first
            cursor.execute('''
                SELECT * FROM product_mappings 
                WHERE customer_email = ? AND lpo_product_name = ? AND active = 1
            ''', (customer_email, item['lpo_product_name']))
            
            mapping = cursor.fetchone()
            
            if not mapping:
                # Try fuzzy matching - find mappings containing key words
                product_words = item['lpo_product_name'].lower().split()
                
                cursor.execute('''
                    SELECT * FROM product_mappings 
                    WHERE customer_email = ? AND active = 1
                ''', (customer_email,))
                
                all_mappings = cursor.fetchall()
                best_match = None
                best_score = 0
                
                for map_row in all_mappings:
                    lpo_name = map_row['lpo_product_name'].lower()
                    # Count matching words
                    score = sum(1 for word in product_words if word in lpo_name)
                    if score > best_score:
                        best_score = score
                        best_match = map_row
                
                if best_match and best_score >= 2:  # At least 2 words match
                    mapping = best_match
            
            if mapping:
                mapped_items.append({
                    'lpo_product_name': item['lpo_product_name'],
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
    
    def add_product_mapping(self, customer_email: str, lpo_name: str, 
                           system_name: str, price: float, unit: str = 'EACH'):
        """Add a new product mapping to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO product_mappings 
                (customer_email, lpo_product_name, system_product_name, unit_price, unit)
                VALUES (?, ?, ?, ?, ?)
            ''', (customer_email, lpo_name, system_name, price, unit))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding mapping: {e}")
            return False
        finally:
            conn.close()


# Test the parser
if __name__ == "__main__":
    parser = SimpleParser()
    
    # Test with a sample PDF
    test_files = [
        './invoice_system_version_1/test lpos/ATRADEMENA 4710879730.pdf',
        './invoice_system_version_1/test lpos/Purchase Order Report - 2025-07-26T170234.923.pdf'
    ]
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\n=== Testing: {test_file} ===")
            result = parser.parse_lpo(test_file)
            
            if result['customer']:
                print(f"Customer: {result['customer']['customer_name']}")
                print(f"Email: {result['customer']['email']}")
                print(f"TRN: {result['customer']['trn']}")
                
                if result['items']:
                    print(f"\nItems found: {len(result['items'])}")
                    for item in result['items']:
                        print(f"  - {item['system_product_name']}: {item['quantity']} x {item['unit_price']} = {item['total']}")
                
                if result['totals']:
                    print(f"\nTotals:")
                    print(f"  Subtotal: {result['totals']['subtotal']}")
                    print(f"  VAT ({result['totals']['vat_rate']}%): {result['totals']['vat_amount']}")
                    print(f"  Total: {result['totals']['total']}")
            else:
                print(f"Errors: {result['errors']}")
            
            break