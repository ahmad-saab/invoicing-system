#!/usr/bin/env python3
"""
Mapping-based Parser - Uses customer field mappings instead of regex patterns
Simply extracts text and looks up what it means in the database
"""

import re
import sqlite3
import pdfplumber
from typing import Dict, List, Any, Optional

class MappingParser:
    """
    Parser that uses customer-defined mappings to understand parsed text
    No complex regex - just simple text matching with database lookups
    """
    
    def __init__(self, db_path: str = "test_customers.db"):
        self.db_path = db_path
    
    def parse_with_mappings(self, file_path: str, customer_id: str = None, use_custom_pricing: bool = True) -> Dict[str, Any]:
        """
        Parse PDF and apply customer mappings to understand the data
        
        Args:
            file_path: Path to PDF file
            customer_id: Customer ID to use for mappings (optional - will try to detect)
            use_custom_pricing: Whether to use customer-specific pricing from database
        """
        
        # Extract raw text from PDF
        raw_text = self._extract_pdf_text(file_path)
        lines = raw_text.split('\n')
        
        # If no customer_id provided, try to detect it
        if not customer_id:
            customer_id = self._detect_customer(raw_text)
        
        # Get customer mappings from database
        mappings = self._get_customer_mappings(customer_id) if customer_id else {}
        
        # Get customer pricing and VAT configuration
        customer_pricing = self._get_customer_pricing(customer_id) if customer_id and use_custom_pricing else {}
        vat_config = self._get_customer_vat_config(customer_id) if customer_id else {
            'vat_rate': 5.0,
            'vat_inclusive': False,
            'default_currency': 'AED'
        }
        
        # Extract additional invoice details
        invoice_details = self._extract_invoice_details(raw_text)
        po_number = self._extract_po_number(raw_text)
        
        # Process each line and apply mappings
        parsed_data = {
            'customer_id': customer_id,
            'products': [],
            'quantities': [],
            'prices': [],
            'units': [],
            'codes': [],
            'other_fields': {},
            'unmapped_text': [],
            'invoice_details': invoice_details,
            'purchase_order_number': po_number
        }
        
        # First, extract product data from TEXT_TABLE rows
        table_products = self._extract_products_from_table_rows(lines)
        if table_products:
            print(f"DEBUG: Extracted {len(table_products)} products from table rows")
            for product in table_products:
                # Try to find mapping for this product
                mapped_product = self._find_product_mapping(product['product_name'], mappings)
                if mapped_product:
                    print(f"DEBUG: Found mapping: '{product['product_name']}' -> '{mapped_product}'")
                    product_name = mapped_product
                else:
                    print(f"DEBUG: No mapping found for '{product['product_name']}', using original")
                    product_name = product['product_name']
                    
                parsed_data['products'].append({
                    'original': product['original_text'],
                    'mapped': product_name,
                    'description': product.get('description', '')
                })
                if product.get('quantity'):
                    parsed_data['quantities'].append({
                        'original': product['original_text'],
                        'value': product['quantity'],
                        'mapped': str(product['quantity'])
                    })
                if product.get('unit'):
                    parsed_data['units'].append({
                        'original': product['original_text'],
                        'mapped': product['unit']
                    })
                if product.get('unit_price'):
                    parsed_data['prices'].append({
                        'original': product['original_text'],
                        'value': product['unit_price'],
                        'mapped': str(product['unit_price'])
                    })
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip TEXT_TABLE lines as they're processed separately
            if line.startswith('TEXT_TABLE:'):
                continue
            
            # Check if this line matches any mapping
            mapped = False
            for parsed_text, mapping_info in mappings.items():
                if parsed_text.lower() in line.lower():
                    field_type = mapping_info['field_type']
                    mapped_value = mapping_info['mapped_value']
                    
                    # Store based on field type
                    if field_type == 'product':
                        parsed_data['products'].append({
                            'original': line,
                            'mapped': mapped_value,
                            'description': mapping_info.get('description', '')
                        })
                    elif field_type == 'quantity':
                        # Extract number from line
                        numbers = re.findall(r'\d+(?:\.\d+)?', line)
                        if numbers:
                            parsed_data['quantities'].append({
                                'original': line,
                                'value': float(numbers[0]),
                                'mapped': mapped_value
                            })
                    elif field_type == 'unit':
                        parsed_data['units'].append({
                            'original': line,
                            'mapped': mapped_value
                        })
                    elif field_type == 'price':
                        # Extract price from line with improved pattern
                        price = self._extract_price(line)
                        if price > 0:
                            parsed_data['prices'].append({
                                'original': line,
                                'value': price,
                                'mapped': mapped_value
                            })
                    elif field_type == 'code':
                        parsed_data['codes'].append({
                            'original': line,
                            'mapped': mapped_value
                        })
                    else:
                        parsed_data['other_fields'][mapped_value] = line
                    
                    mapped = True
                    break
            
            # If not mapped, store as unmapped
            if not mapped and len(line) > 5:  # Ignore very short lines
                # Still try to extract useful data
                if re.search(r'\d+(?:\.\d+)?.*(?:pcs|kg|ltr|case|each|unit)', line, re.IGNORECASE):
                    parsed_data['unmapped_text'].append({
                        'text': line,
                        'type': 'possible_item'
                    })
                elif '@' in line:
                    parsed_data['unmapped_text'].append({
                        'text': line,
                        'type': 'email'
                    })
                else:
                    parsed_data['unmapped_text'].append({
                        'text': line,
                        'type': 'unknown'
                    })
        
        # Create line items from parsed data with customer pricing
        items = self._create_line_items(parsed_data, customer_pricing, vat_config)
        
        # Calculate invoice totals
        subtotal = sum(item.get('subtotal', 0) for item in items)
        total_vat = sum(item.get('vat_amount', 0) for item in items)
        grand_total = sum(item.get('total', 0) for item in items)
        
        return {
            'customer_id': customer_id,
            'items': items,
            'parsed_data': parsed_data,
            'mappings_used': len(mappings),
            'unmapped_count': len(parsed_data['unmapped_text']),
            'purchase_order_number': po_number,
            'invoice_details': invoice_details,
            'vat_config': vat_config,
            'invoice_totals': {
                'subtotal': subtotal,
                'vat_amount': total_vat,
                'grand_total': grand_total,
                'currency': vat_config.get('default_currency', 'AED')
            }
        }
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF using both pdfplumber AND invoice2data for maximum coverage"""
        text = ""
        try:
            # METHOD 1: pdfplumber extraction
            print(f"DEBUG: === PDFPLUMBER EXTRACTION ===")
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract regular text
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        print(f"DEBUG: pdfplumber extracted {len(page_text.split())} words from page {page_num + 1}")
                    
                    # Extract tables with different strategies for borderless tables
                    print(f"DEBUG: Trying multiple table extraction strategies...")
                    
                    # Strategy 1: Default table extraction
                    tables = page.extract_tables()
                    if tables:
                        print(f"DEBUG: Default strategy found {len(tables)} tables")
                        for i, table in enumerate(tables):
                            print(f"DEBUG: Default table {i+1} has {len(table)} rows")
                            for row_num, row in enumerate(table):
                                if row and any(cell for cell in row if cell and str(cell).strip()):
                                    row_text = " | ".join([str(cell).strip() if cell else "" for cell in row])
                                    text += f"DEFAULT_TABLE: {row_text}\n"
                                    print(f"DEBUG: Default table row {row_num+1}: {row_text}")
                    
                    # Strategy 2: Text-based extraction for borderless tables
                    table_settings = {
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "intersection_tolerance": 15,
                        "snap_tolerance": 3,
                        "join_tolerance": 3,
                        "edge_min_length": 3,
                        "min_words_vertical": 1,
                        "min_words_horizontal": 1,
                        "text_tolerance": 3,
                        "text_x_tolerance": 3,
                        "text_y_tolerance": 3
                    }
                    
                    text_tables = page.extract_tables(table_settings)
                    if text_tables:
                        print(f"DEBUG: Text strategy found {len(text_tables)} tables")
                        for i, table in enumerate(text_tables):
                            print(f"DEBUG: Text table {i+1} has {len(table)} rows")
                            for row_num, row in enumerate(table):
                                if row and any(cell for cell in row if cell and str(cell).strip()):
                                    row_text = " | ".join([str(cell).strip() if cell else "" for cell in row])
                                    text += f"TEXT_TABLE: {row_text}\n"
                                    print(f"DEBUG: Text table row {row_num+1}: {row_text}")
                    
                    # Strategy 3: Lines strategy for tables with borders
                    line_settings = {
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "intersection_tolerance": 15,
                        "snap_tolerance": 3
                    }
                    
                    line_tables = page.extract_tables(line_settings)
                    if line_tables:
                        print(f"DEBUG: Lines strategy found {len(line_tables)} tables")
                        for i, table in enumerate(line_tables):
                            print(f"DEBUG: Lines table {i+1} has {len(table)} rows")
                            for row_num, row in enumerate(table):
                                if row and any(cell for cell in row if cell and str(cell).strip()):
                                    row_text = " | ".join([str(cell).strip() if cell else "" for cell in row])
                                    text += f"LINES_TABLE: {row_text}\n"
                                    print(f"DEBUG: Lines table row {row_num+1}: {row_text}")
                    
                    # Strategy 4: Mixed strategy
                    mixed_settings = {
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "text",
                        "intersection_tolerance": 15,
                        "snap_tolerance": 3
                    }
                    
                    mixed_tables = page.extract_tables(mixed_settings)
                    if mixed_tables:
                        print(f"DEBUG: Mixed strategy found {len(mixed_tables)} tables")
                        for i, table in enumerate(mixed_tables):
                            print(f"DEBUG: Mixed table {i+1} has {len(table)} rows")
                            for row_num, row in enumerate(table):
                                if row and any(cell for cell in row if cell and str(cell).strip()):
                                    row_text = " | ".join([str(cell).strip() if cell else "" for cell in row])
                                    text += f"MIXED_TABLE: {row_text}\n"
                                    print(f"DEBUG: Mixed table row {row_num+1}: {row_text}")
                    
                    # Extract character positions for debugging
                    chars = page.chars
                    if chars:
                        print(f"DEBUG: pdfplumber found {len(chars)} character objects")
            
            # METHOD 2: invoice2data extraction
            print(f"DEBUG: === INVOICE2DATA EXTRACTION ===")
            try:
                import invoice2data
                result = invoice2data.extract_data(file_path)
                if result:
                    print(f"DEBUG: invoice2data extracted: {result}")
                    # Add invoice2data results as additional text
                    if isinstance(result, dict):
                        for key, value in result.items():
                            if isinstance(value, list):
                                for item in value:
                                    if isinstance(item, dict):
                                        # This might be line items
                                        item_text = " | ".join([f"{k}:{v}" for k, v in item.items()])
                                        text += f"INVOICE2DATA_ITEM: {item_text}\n"
                                        print(f"DEBUG: invoice2data item: {item_text}")
                                    else:
                                        text += f"INVOICE2DATA_LINE: {item}\n"
                                        print(f"DEBUG: invoice2data line: {item}")
                            else:
                                text += f"INVOICE2DATA_{key.upper()}: {value}\n"
                                print(f"DEBUG: invoice2data {key}: {value}")
                else:
                    print(f"DEBUG: invoice2data returned no results")
            except Exception as e:
                print(f"DEBUG: invoice2data extraction failed: {e}")
            
            # METHOD 3: Alternative pdfplumber extraction with different settings
            print(f"DEBUG: === ALTERNATIVE PDFPLUMBER EXTRACTION ===")
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        # Try extracting text with different parameters
                        alt_text = page.extract_text(x_tolerance=1, y_tolerance=1)
                        if alt_text and alt_text != page.extract_text():
                            lines = alt_text.split('\n')
                            print(f"DEBUG: Alternative extraction found {len(lines)} lines (different from regular)")
                            for line in lines:
                                if line.strip() and line.strip() not in text:
                                    text += f"ALT_EXTRACT: {line}\n"
                                    print(f"DEBUG: Alternative line: {line}")
                        
                        # Try extracting words with positions
                        words = page.extract_words(x_tolerance=1, y_tolerance=1, 
                                                 keep_blank_chars=False,
                                                 use_text_flow=True,
                                                 horizontal_ltr=True,
                                                 vertical_ttb=True)
                        if words:
                            print(f"DEBUG: Found {len(words)} positioned words")
                            # Group words by similar y-coordinates (table rows)
                            word_lines = {}
                            for word in words:
                                y = round(word['top'])
                                if y not in word_lines:
                                    word_lines[y] = []
                                word_lines[y].append(word)
                            
                            # Sort by y-coordinate and reconstruct lines
                            for y in sorted(word_lines.keys()):
                                line_words = sorted(word_lines[y], key=lambda w: w['x0'])
                                line_text = " ".join([w['text'] for w in line_words])
                                if line_text.strip() and line_text.strip() not in text:
                                    text += f"WORD_LINE: {line_text}\n"
                                    print(f"DEBUG: Word-based line: {line_text}")
            except Exception as e:
                print(f"DEBUG: Alternative extraction failed: {e}")
                        
        except Exception as e:
            print(f"Error extracting PDF: {e}")
        
        print(f"DEBUG: Total extracted text length: {len(text)} characters")
        return text
    
    def _extract_products_from_table_rows(self, lines: List[str]) -> List[Dict]:
        """Extract product information from TEXT_TABLE rows"""
        products = []
        
        for line in lines:
            if not line.startswith('TEXT_TABLE:'):
                continue
                
            # Remove TEXT_TABLE prefix
            table_row = line[12:]  # Remove "TEXT_TABLE: "
            cells = [cell.strip() for cell in table_row.split('|')]
            
            # Look for product rows (containing both text and numbers)
            if self._is_product_row(cells):
                product_info = self._parse_product_row(cells)
                if product_info:
                    products.append(product_info)
                    print(f"DEBUG: Parsed product: {product_info}")
        
        return products
    
    def _is_product_row(self, cells: List[str]) -> bool:
        """Check if this table row contains product information"""
        # Product rows typically have:
        # 1. Product name (text)
        # 2. Quantity (number)
        # 3. Unit price (number with decimal)
        # 4. Total (number with decimal)
        
        non_empty_cells = [cell for cell in cells if cell and cell.strip()]
        if len(non_empty_cells) < 4:
            return False
            
        # Look for price patterns (numbers with decimals)
        price_patterns = 0
        has_text = False
        
        for cell in non_empty_cells:
            if re.search(r'\d+\.\d{2}', cell):
                price_patterns += 1
            elif re.search(r'[A-Za-z]{3,}', cell):  # Text with 3+ letters
                has_text = True
        
        # Product row should have text and at least 2 price-like numbers
        return has_text and price_patterns >= 2
    
    def _parse_product_row(self, cells: List[str]) -> Optional[Dict]:
        """Parse a product row from table cells"""
        non_empty_cells = [cell for cell in cells if cell and cell.strip()]
        
        if len(non_empty_cells) < 4:
            return None
            
        try:
            # Reconstruct product name from first several cells
            product_parts = []
            unit_parts = []
            numbers = []
            
            for cell in non_empty_cells:
                # If it's a number, store it
                if re.match(r'^\d+\.?\d*$', cell.replace(',', '')):
                    try:
                        numbers.append(float(cell.replace(',', '')))
                    except:
                        pass
                # If it contains letters, it's part of product name or unit
                elif re.search(r'[A-Za-z]', cell):
                    if re.search(r'(KG|LTR|PCS|PKT|CASE|UNIT|EACH)', cell, re.IGNORECASE):
                        unit_parts.append(cell)
                    else:
                        product_parts.append(cell)
            
            # Reconstruct product name with cleanup
            product_name = ' '.join(product_parts).strip()
            # Clean up fragmented words (e.g., "SUN FLOW E R O IL" -> "SUNFLOWER OIL")
            product_name = self._clean_product_name(product_name)
            unit = ' '.join(unit_parts).strip() if unit_parts else 'PCS'
            
            # Extract quantity and prices from numbers
            # Typically: quantity, unit_price, total
            if len(numbers) >= 3:
                quantity = numbers[0] if numbers[0] < 100 else 1  # Quantities are usually small
                unit_price = numbers[-2]  # Second to last is usually unit price
                total = numbers[-1]  # Last is total
                
                return {
                    'product_name': product_name,
                    'quantity': quantity,
                    'unit': unit,
                    'unit_price': unit_price,
                    'total': total,
                    'original_text': ' | '.join(non_empty_cells)
                }
            elif len(numbers) >= 2:
                # Minimal case: price and total
                quantity = 1
                unit_price = numbers[0]
                total = numbers[1]
                
                return {
                    'product_name': product_name,
                    'quantity': quantity,
                    'unit': unit,
                    'unit_price': unit_price,
                    'total': total,
                    'original_text': ' | '.join(non_empty_cells)
                }
                
        except Exception as e:
            print(f"DEBUG: Error parsing product row: {e}")
            
        return None
    
    def _clean_product_name(self, raw_name: str) -> str:
        """Clean up fragmented product names from table extraction"""
        if not raw_name:
            return ""
            
        # Common word fragments that should be joined
        word_fixes = {
            'SUN FLOW E R': 'SUNFLOWER',
            'O IL': 'OIL',
            'TIN': 'TIN',
            'LTR': 'LTR',
            'PKT': 'PKT',
            'P KT': 'PKT',
        }
        
        cleaned = raw_name
        
        # Fix common fragmented words
        for fragment, fixed in word_fixes.items():
            cleaned = cleaned.replace(fragment, fixed)
        
        # Remove extra spaces
        cleaned = ' '.join(cleaned.split())
        
        # Clean up common patterns
        cleaned = re.sub(r'\b([A-Z])\s+([A-Z])\s+([A-Z])\s+([A-Z])\b', r'\1\2\3\4', cleaned)  # Single letters
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Multiple spaces
        
        print(f"DEBUG: Cleaned product name: '{raw_name}' -> '{cleaned}'")
        return cleaned.strip()
    
    def _find_product_mapping(self, product_name: str, mappings: Dict) -> Optional[str]:
        """Find mapping for a product name in customer field mappings"""
        if not product_name or not mappings:
            print(f"DEBUG: No product name or mappings provided")
            return None
            
        product_lower = product_name.lower()
        print(f"DEBUG: === MAPPING SEARCH START ===")
        print(f"DEBUG: Looking for mapping for: '{product_lower}'")
        print(f"DEBUG: Available mappings: {list(mappings.keys())}")
        
        # Step 1: Direct match
        print(f"DEBUG: Step 1 - Direct match")
        for parsed_text, mapping_info in mappings.items():
            print(f"DEBUG: Checking mapping '{parsed_text}' (type: {mapping_info.get('field_type', 'unknown')})")
            if 'product' in mapping_info['field_type']:
                if parsed_text.lower() == product_lower:
                    print(f"DEBUG: DIRECT MATCH FOUND: '{parsed_text.lower()}' == '{product_lower}'")
                    return mapping_info['mapped_value']
                else:
                    print(f"DEBUG: Direct match failed: '{parsed_text.lower()}' != '{product_lower}'")
        
        # Step 2: Partial match - check if parsed text is contained in product name
        print(f"DEBUG: Step 2 - Partial match (mapping in product)")
        for parsed_text, mapping_info in mappings.items():
            if 'product' in mapping_info['field_type']:
                if parsed_text.lower() in product_lower:
                    print(f"DEBUG: PARTIAL MATCH FOUND: '{parsed_text.lower()}' in '{product_lower}'")
                    return mapping_info['mapped_value']
                else:
                    print(f"DEBUG: Partial match failed: '{parsed_text.lower()}' not in '{product_lower}'")
        
        # Step 3: Reverse partial match - check if product name is contained in parsed text
        print(f"DEBUG: Step 3 - Reverse partial match (product in mapping)")
        for parsed_text, mapping_info in mappings.items():
            if 'product' in mapping_info['field_type']:
                if product_lower in parsed_text.lower():
                    print(f"DEBUG: REVERSE MATCH FOUND: '{product_lower}' in '{parsed_text.lower()}'")
                    return mapping_info['mapped_value']
                else:
                    print(f"DEBUG: Reverse match failed: '{product_lower}' not in '{parsed_text.lower()}'")
        
        # Step 4: Smart word-based matching
        print(f"DEBUG: Step 4 - Smart word-based matching")
        # Extract important words from product name
        product_words = set(re.findall(r'\b[a-z]+\b', product_lower))
        # Remove common words that don't help with matching
        stopwords = {'the', 'of', 'and', 'or', 'with', 'for', 'in', 'on', 'at', 'to', 'a', 'an'}
        product_words = product_words - stopwords
        print(f"DEBUG: Product key words: {product_words}")
        
        best_match = None
        best_score = 0
        
        for parsed_text, mapping_info in mappings.items():
            if 'product' in mapping_info['field_type']:
                mapping_words = set(re.findall(r'\b[a-z]+\b', parsed_text.lower()))
                mapping_words = mapping_words - stopwords
                
                # Calculate word overlap score
                common_words = product_words & mapping_words
                if common_words:
                    # Score based on percentage of words matched
                    score = len(common_words) / min(len(product_words), len(mapping_words))
                    print(f"DEBUG: Comparing with '{parsed_text}': common words={common_words}, score={score:.2f}")
                    
                    # Bonus for important brand/product words
                    important_words = {'bunge', 'procuisine', 'cuisine', 'pro', 'oil', 'sunflower', 'rapeseed', 'frying', 'canola'}
                    important_matches = common_words & important_words
                    if important_matches:
                        score += 0.3 * len(important_matches)
                        print(f"DEBUG: Important word bonus for {important_matches}: new score={score:.2f}")
                    
                    if score > best_score and score >= 0.4:  # At least 40% match
                        best_score = score
                        best_match = mapping_info['mapped_value']
                        print(f"DEBUG: New best match: '{parsed_text}' -> '{best_match}' (score={score:.2f})")
        
        if best_match:
            print(f"DEBUG: SMART MATCH FOUND: '{best_match}' with score {best_score:.2f}")
            return best_match
        
        # Step 5: Fuzzy match - normalize spaces and common variations
        print(f"DEBUG: Step 5 - Fuzzy match (legacy)")
        normalized_product = re.sub(r'\s+', ' ', product_lower)
        normalized_product = normalized_product.replace(' t)', 't)')  # "05L T)" -> "05LT)"
        normalized_product = normalized_product.replace(' pkt', '').strip()  # Remove PKT suffix
        print(f"DEBUG: Normalized product: '{product_lower}' -> '{normalized_product}'")
        
        for parsed_text, mapping_info in mappings.items():
            if 'product' in mapping_info['field_type']:
                normalized_mapping = re.sub(r'\s+', ' ', parsed_text.lower())
                print(f"DEBUG: Comparing fuzzy: '{normalized_product}' vs '{normalized_mapping}'")
                if normalized_mapping in normalized_product or normalized_product in normalized_mapping:
                    print(f"DEBUG: FUZZY MATCH FOUND: '{normalized_product}' ~= '{normalized_mapping}'")
                    return mapping_info['mapped_value']
                else:
                    print(f"DEBUG: Fuzzy match failed: no match between '{normalized_product}' and '{normalized_mapping}'")
        
        print(f"DEBUG: === NO MAPPING FOUND ===")            
        return None
    
    def _detect_customer(self, text: str) -> Optional[str]:
        """Try to detect customer from text with support for shared emails"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all customers
        cursor.execute('SELECT customer_id, email, chain_alias FROM customers WHERE active = 1')
        customers = cursor.fetchall()
        
        # Get customer-specific identifiers (mappings)
        cursor.execute('''
            SELECT customer_id, parsed_text, mapped_value 
            FROM customer_field_mappings 
            WHERE field_type IN ('customer_identifiers', 'branch_identifier', 'delivery_location', 'account_number')
            AND active = 1
        ''')
        identifiers = cursor.fetchall()
        
        best_match = None
        best_score = 0
        email_matches = []  # Track customers with matching emails
        
        text_upper = text.upper()
        
        for customer in customers:
            score = 0
            
            # Check email
            if customer['email'] and customer['email'] in text:
                score += 50  # Reduced from 100 since email might be shared
                email_matches.append(customer['customer_id'])
            
            # Check chain alias
            if customer['chain_alias']:
                alias_upper = customer['chain_alias'].upper()
                if alias_upper in text_upper:
                    score += 50
                # Partial match
                elif any(word in text_upper for word in alias_upper.split() if len(word) > 4):
                    score += 20
            
            # Check customer-specific identifiers (MOST IMPORTANT for shared emails)
            for identifier in identifiers:
                if identifier['customer_id'] == customer['customer_id']:
                    if identifier['parsed_text'].upper() in text_upper:
                        score += 100  # High score for unique identifiers
            
            if score > best_score:
                best_score = score
                best_match = customer['customer_id']
        
        # If multiple customers share the same email, we rely on identifiers
        if len(email_matches) > 1 and best_score < 100:
            print(f"WARNING: Multiple customers share email. Found: {email_matches}")
            print("Add unique identifiers in Customer Mapper to distinguish them.")
        
        conn.close()
        return best_match
    
    def _get_customer_mappings(self, customer_id: str) -> Dict[str, Dict]:
        """Get all mappings for a customer"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT parsed_text, field_type, mapped_value, description
            FROM customer_field_mappings
            WHERE customer_id = ? AND active = 1
        ''', (customer_id,))
        
        mappings = {}
        for row in cursor.fetchall():
            mappings[row['parsed_text']] = {
                'field_type': row['field_type'],
                'mapped_value': row['mapped_value'],
                'description': row['description']
            }
        
        conn.close()
        return mappings
    
    def _get_customer_pricing(self, customer_id: str) -> Dict[str, Dict]:
        """Get customer-specific pricing from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT product_name, unit_price, currency, uom, vat_rate, vat_inclusive
            FROM customer_pricing
            WHERE customer_id = ? AND active = 1
        ''', (customer_id,))
        
        pricing = {}
        for row in cursor.fetchall():
            pricing[row[0].lower()] = {
                'unit_price': row[1],
                'currency': row[2],
                'uom': row[3],
                'vat_rate': row[4],
                'vat_inclusive': row[5]
            }
        
        conn.close()
        return pricing
    
    def _get_customer_vat_config(self, customer_id: str) -> Dict[str, Any]:
        """Get customer VAT configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT vat_rate, vat_inclusive, default_currency
            FROM customers
            WHERE customer_id = ?
        ''', (customer_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'vat_rate': row[0] or 5.0,
                'vat_inclusive': bool(row[1]) if row[1] is not None else False,
                'default_currency': row[2] or 'AED'
            }
        return {
            'vat_rate': 5.0,
            'vat_inclusive': False,
            'default_currency': 'AED'
        }
    
    def _create_line_items(self, parsed_data: Dict, customer_pricing: Dict = None, vat_config: Dict = None) -> List[Dict]:
        """Create line items from parsed data"""
        items = []
        
        # Try to match products with quantities and prices
        for i, product in enumerate(parsed_data['products']):
            item = {
                'product': product['mapped'],
                'description': product.get('description', ''),
                'original_text': product['original']
            }
            
            # Try to find corresponding quantity
            if i < len(parsed_data['quantities']):
                item['quantity'] = parsed_data['quantities'][i]['value']
            else:
                item['quantity'] = 0
            
            # Check if we have custom pricing for this product
            product_key = product['mapped'].lower() if product['mapped'] else ''
            print(f"DEBUG: Looking for product '{product_key}' in customer pricing")
            print(f"DEBUG: Available pricing keys: {list(customer_pricing.keys()) if customer_pricing else 'None'}")
            
            if customer_pricing and product_key in customer_pricing:
                # Use customer-specific pricing
                pricing_info = customer_pricing[product_key]
                item['price'] = pricing_info['unit_price']
                item['currency'] = pricing_info['currency']
                item['unit'] = pricing_info['uom']
                item['vat_rate'] = pricing_info['vat_rate']
                item['vat_inclusive'] = pricing_info['vat_inclusive']
                item['price_source'] = 'customer_pricing'
            else:
                # Use parsed price or default
                if i < len(parsed_data['prices']):
                    item['price'] = parsed_data['prices'][i]['value']
                else:
                    item['price'] = 0
                
                # Use parsed unit or default
                if i < len(parsed_data['units']):
                    item['unit'] = parsed_data['units'][i]['mapped']
                else:
                    item['unit'] = 'PCS'
                
                # Use default VAT config
                if vat_config:
                    item['vat_rate'] = vat_config['vat_rate']
                    item['vat_inclusive'] = vat_config['vat_inclusive']
                    item['currency'] = vat_config['default_currency']
                else:
                    item['vat_rate'] = 5.0
                    item['vat_inclusive'] = False
                    item['currency'] = 'AED'
                
                item['price_source'] = 'parsed'
            
            # Calculate totals with VAT
            subtotal = item['quantity'] * item['price']
            if item.get('vat_inclusive'):
                # VAT is already included in the price
                item['subtotal'] = subtotal
                item['vat_amount'] = subtotal * (item['vat_rate'] / (100 + item['vat_rate']))
                item['total'] = subtotal
            else:
                # VAT needs to be added
                item['subtotal'] = subtotal
                item['vat_amount'] = subtotal * (item['vat_rate'] / 100)
                item['total'] = subtotal + item['vat_amount']
            
            items.append(item)
        
        # If no products mapped, try to create items from unmapped text
        if not items:
            for unmapped in parsed_data['unmapped_text']:
                if unmapped['type'] == 'possible_item':
                    # Extract numbers from the text
                    numbers = re.findall(r'\d+(?:\.\d+)?', unmapped['text'])
                    if numbers:
                        items.append({
                            'product': 'UNMAPPED',
                            'description': unmapped['text'],
                            'original_text': unmapped['text'],
                            'quantity': float(numbers[0]) if numbers else 0,
                            'price': float(numbers[-1]) if len(numbers) > 1 else 0,
                            'unit': 'PCS'
                        })
        
        return items
    
    def _extract_price(self, text: str) -> float:
        """Extract price from text with improved patterns"""
        # Look for price patterns (more comprehensive)
        patterns = [
            r'(?:AED|USD|EUR|GBP)?\s*([0-9,]+\.\d{2})',  # Currency with decimal
            r'([0-9,]+\.\d{2})\s*(?:AED|USD|EUR|GBP)',   # Decimal with currency
            r'(?:price|rate|@)\s*:?\s*([0-9,]+\.?\d*)',   # After price keywords
            r'([0-9]{1,3}(?:,[0-9]{3})*\.\d{2})',        # Formatted numbers
            r'(\d+\.\d+)',                                # Simple decimal
            r'(\d+)\s*(?:AED|USD|EUR|GBP)',              # Whole number with currency
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    # Remove commas and convert to float
                    price_str = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    price_str = price_str.replace(',', '').replace('AED', '').replace('USD', '').strip()
                    price = float(price_str)
                    if price > 0 and price < 1000000:  # Sanity check
                        return price
                except:
                    pass
        return 0
    
    def _extract_po_number(self, text: str) -> str:
        """Extract purchase order number from text"""
        # Look for PO patterns
        patterns = [
            r'(?:P\.?O\.?|Purchase Order|PO)\s*(?:Number|No\.?|#)?\s*:?\s*([A-Z0-9\-/]+)',
            r'(?:Order|Reference)\s*(?:Number|No\.?|#)?\s*:?\s*([A-Z0-9\-/]+)',
            r'PO\s*([A-Z0-9\-/]+)',
            r'P\.O\.\s*([A-Z0-9\-/]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                po_number = match.group(1).strip()
                # Validate it looks like a PO number
                if len(po_number) >= 3 and len(po_number) <= 30:
                    return po_number
        return ''
    
    def _extract_invoice_details(self, text: str) -> Dict[str, Any]:
        """Extract invoice header details"""
        details = {
            'invoice_number': '',  # Always empty - Zoho generates this
            'invoice_date': '',
            'due_date': '',
            'total_amount': 0
        }
        
        # Don't extract invoice number - Zoho will generate it
        # Keep invoice_number empty
        
        # Extract dates
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        dates = re.findall(date_pattern, text)
        if dates:
            details['invoice_date'] = dates[0] if len(dates) > 0 else ''
            details['due_date'] = dates[1] if len(dates) > 1 else ''
        
        # Extract total amount
        total_patterns = [
            r'(?:Total|Grand Total|Amount Due)\s*:?\s*(?:AED)?\s*([0-9,]+\.\d{2})',
            r'([0-9,]+\.\d{2})\s*(?:Total|Due)',
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    details['total_amount'] = float(amount_str)
                    break
                except:
                    pass
        
        return details

def test_mapping_parser():
    """Test the mapping parser"""
    parser = MappingParser()
    
    # Test with a sample PDF
    result = parser.parse_with_mappings('test lpos/GCD.pdf')
    
    print("\n🔍 Mapping Parser Test Results")
    print("=" * 60)
    print(f"Customer Detected: {result['customer_id']}")
    print(f"Mappings Used: {result['mappings_used']}")
    print(f"Unmapped Text Lines: {result['unmapped_count']}")
    
    print(f"\n📦 Items Found: {len(result['items'])}")
    for item in result['items']:
        print(f"  - {item['product']}: {item['quantity']} {item['unit']} @ {item['price']}")
        print(f"    Original: {item['original_text'][:50]}...")
    
    if result['parsed_data']['unmapped_text']:
        print(f"\n⚠️  Unmapped Text (needs customer mapping):")
        for unmapped in result['parsed_data']['unmapped_text'][:5]:
            print(f"  - [{unmapped['type']}] {unmapped['text'][:60]}...")

if __name__ == "__main__":
    test_mapping_parser()