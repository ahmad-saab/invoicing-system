#!/usr/bin/env python3
"""
Enhanced Mapping Parser using Unstructured.io library
Replaces pdfplumber with unstructured for better extraction quality
Maintains compatibility with existing mapping database
"""

import re
import sqlite3
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

# Import unstructured library components
try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.staging.base import convert_to_dict
except ImportError:
    print("Error: unstructured library not found!")
    print("Please install: pip install unstructured[pdf]")
    raise

class UnstructuredMappingParser:
    """
    Enhanced parser using unstructured.io for extraction
    and customer-defined mappings for understanding the data
    """
    
    def __init__(self, db_path: str = "test_customers.db"):
        self.db_path = db_path
        self.extraction_cache = {}
    
    def parse_with_mappings(self, file_path: str, customer_id: str = None, use_custom_pricing: bool = True) -> Dict[str, Any]:
        """
        Parse PDF using unstructured.io and apply customer mappings
        
        Args:
            file_path: Path to PDF file
            customer_id: Customer ID to use for mappings (optional - will try to detect)
            use_custom_pricing: Whether to use customer-specific pricing from database
        """
        
        # Extract structured data from PDF using unstructured
        extracted_data = self._extract_with_unstructured(file_path)
        
        # Get raw text from extracted elements
        raw_text = extracted_data.get('raw_text', '')
        elements = extracted_data.get('elements', [])
        
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
        
        # Extract invoice details from structured data
        invoice_details = self._extract_invoice_details_from_elements(elements, raw_text)
        po_number = self._extract_po_number(raw_text)
        
        # Process structured elements and apply mappings
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
            'purchase_order_number': po_number,
            'extraction_metadata': extracted_data.get('metadata', {})
        }
        
        # Process table elements first (they often contain product listings)
        table_products = self._extract_products_from_table_elements(elements)
        if table_products:
            print(f"DEBUG: Extracted {len(table_products)} products from table elements")
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
                    'original': product.get('original_text', ''),
                    'mapped': product_name,
                    'description': product.get('description', ''),
                    'element_type': product.get('element_type', 'table'),
                    'confidence': product.get('confidence', 1.0)
                })
                
                if product.get('quantity'):
                    parsed_data['quantities'].append({
                        'original': product.get('original_text', ''),
                        'value': product['quantity'],
                        'mapped': str(product['quantity'])
                    })
                    
                if product.get('unit'):
                    parsed_data['units'].append({
                        'original': product.get('original_text', ''),
                        'mapped': product['unit']
                    })
                    
                if product.get('unit_price'):
                    parsed_data['prices'].append({
                        'original': product.get('original_text', ''),
                        'value': product['unit_price'],
                        'mapped': str(product['unit_price'])
                    })
        
        # Process text elements for additional data
        for element in elements:
            element_text = element.get('text', '').strip()
            if not element_text:
                continue
            
            element_type = element.get('type', '')
            
            # Skip table elements as they're processed separately
            if 'Table' in element_type:
                continue
            
            # Check if this element matches any mapping
            mapped = False
            for parsed_text, mapping_info in mappings.items():
                if parsed_text.lower() in element_text.lower():
                    field_type = mapping_info['field_type']
                    mapped_value = mapping_info['mapped_value']
                    
                    # Store based on field type
                    if field_type == 'product' and not self._is_duplicate_product(mapped_value, parsed_data['products']):
                        parsed_data['products'].append({
                            'original': element_text,
                            'mapped': mapped_value,
                            'description': mapping_info.get('description', ''),
                            'element_type': element_type,
                            'confidence': 0.9
                        })
                        mapped = True
                        
                    elif field_type == 'quantity':
                        numbers = re.findall(r'\d+(?:\.\d+)?', element_text)
                        if numbers:
                            parsed_data['quantities'].append({
                                'original': element_text,
                                'value': float(numbers[0]),
                                'mapped': mapped_value
                            })
                            mapped = True
                            
                    elif field_type == 'unit':
                        parsed_data['units'].append({
                            'original': element_text,
                            'mapped': mapped_value
                        })
                        mapped = True
                        
                    elif field_type == 'price':
                        price = self._extract_price(element_text)
                        if price > 0:
                            parsed_data['prices'].append({
                                'original': element_text,
                                'value': price,
                                'mapped': mapped_value
                            })
                            mapped = True
                            
                    elif field_type == 'code':
                        parsed_data['codes'].append({
                            'original': element_text,
                            'mapped': mapped_value
                        })
                        mapped = True
                        
                    else:
                        # Store in other_fields
                        if field_type not in parsed_data['other_fields']:
                            parsed_data['other_fields'][field_type] = []
                        parsed_data['other_fields'][field_type].append({
                            'original': element_text,
                            'mapped': mapped_value
                        })
                        mapped = True
            
            # If not mapped, add to unmapped text with element metadata
            if not mapped and len(element_text) > 3:
                parsed_data['unmapped_text'].append({
                    'text': element_text,
                    'element_type': element_type,
                    'metadata': element.get('metadata', {})
                })
        
        # Build final items list with customer pricing
        items = self._build_items_list(parsed_data, customer_pricing, vat_config)
        
        return {
            'customer_id': customer_id,
            'mappings_used': len(mappings),
            'parsed_data': parsed_data,
            'items': items,
            'invoice_details': invoice_details,
            'purchase_order_number': po_number,
            'extraction_quality': self._assess_extraction_quality(parsed_data),
            'unstructured_metadata': extracted_data.get('file_info', {})
        }
    
    def _extract_with_unstructured(self, file_path: str) -> Dict[str, Any]:
        """Extract structured data from PDF using unstructured.io"""
        
        # Check cache first
        cache_key = str(Path(file_path).resolve())
        if cache_key in self.extraction_cache:
            print(f"DEBUG: Using cached extraction for {file_path}")
            return self.extraction_cache[cache_key]
        
        print(f"DEBUG: Extracting data from {file_path} using unstructured.io")
        
        try:
            # Configure extraction parameters for optimal results
            extract_params = {
                "filename": file_path,
                "extract_images_in_pdf": False,  # Disable for faster processing
                "infer_table_structure": True,   # Enable table extraction
                "chunking_strategy": None,       # No chunking for invoice parsing
                "include_page_breaks": True,
                "strategy": "hi_res",            # High resolution for better accuracy
                "languages": ["eng", "ara"]      # Support English and Arabic
            }
            
            # Extract elements from PDF
            elements = partition_pdf(**extract_params)
            
            # Convert to dictionary format
            elements_dict = convert_to_dict(elements)
            
            # Build structured data
            structured_data = {
                "text_blocks": [],
                "tables": [],
                "titles": [],
                "headers": [],
                "footers": [],
                "raw_text": "",
                "elements": []
            }
            
            # Process each element
            for element in elements:
                element_type = str(type(element).__name__)
                element_text = str(element)
                element_metadata = getattr(element, 'metadata', {})
                
                # Add to raw text
                structured_data["raw_text"] += element_text + "\n"
                
                # Create element entry with all available metadata
                element_entry = {
                    "text": element_text,
                    "type": element_type,
                    "metadata": {
                        "page_number": getattr(element_metadata, 'page_number', None),
                        "coordinates": getattr(element_metadata, 'coordinates', None),
                        "detection_class_prob": getattr(element_metadata, 'detection_class_prob', None)
                    }
                }
                
                structured_data["elements"].append(element_entry)
                
                # Categorize by element type
                if "Title" in element_type:
                    structured_data["titles"].append(element_entry)
                elif "Header" in element_type:
                    structured_data["headers"].append(element_entry)
                elif "Footer" in element_type:
                    structured_data["footers"].append(element_entry)
                elif "Table" in element_type:
                    structured_data["tables"].append(element_entry)
                else:
                    structured_data["text_blocks"].append(element_entry)
            
            # Create extraction result
            result = {
                "file_info": {
                    "filename": Path(file_path).name,
                    "filepath": file_path,
                    "extraction_timestamp": datetime.now().isoformat(),
                    "total_elements": len(elements),
                    "extraction_library": "unstructured.io"
                },
                "raw_text": structured_data["raw_text"],
                "elements": structured_data["elements"],
                "tables": structured_data["tables"],
                "titles": structured_data["titles"],
                "text_blocks": structured_data["text_blocks"],
                "metadata": {
                    "table_count": len(structured_data["tables"]),
                    "title_count": len(structured_data["titles"]),
                    "text_block_count": len(structured_data["text_blocks"])
                }
            }
            
            # Cache the result
            self.extraction_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            print(f"Error extracting with unstructured: {e}")
            # Return minimal structure on error
            return {
                "raw_text": "",
                "elements": [],
                "tables": [],
                "file_info": {"error": str(e)}
            }
    
    def _extract_products_from_table_elements(self, elements: List[Dict]) -> List[Dict]:
        """Extract product information from table elements"""
        products = []
        
        for element in elements:
            if 'Table' not in element.get('type', ''):
                continue
                
            text = element.get('text', '')
            if not text:
                continue
            
            # Check if this table contains product data (look for keywords)
            product_keywords = ['FRYING', 'OIL', 'RAPESEED', 'BUNGE', 'LTR', 'Article', 'Unit Price', 'Total']
            is_product_table = any(keyword in text for keyword in product_keywords)
            
            if is_product_table:
                # Extract product lines specifically for the format:
                # FRYING OIL BUNGE PRO F10 1x10LTR 5.00 0.00 85.00 425.00
                # RAPESEED OIL BUNGE PRO CUISINE 1x10LTR 1.00 0.00 80.00 80.00
                
                # First try to split by newlines
                lines = text.split('\n')
                
                # If the entire table is in one line (common with unstructured output),
                # try to extract individual product entries
                if len(lines) == 1 and 'FRYING' in text:
                    # Extract FRYING OIL entry - simplified pattern
                    frying_match = re.search(r'(FRYING OIL.*?)(?:RAPESEED|TOTAL)', text)
                    if frying_match:
                        lines.append(frying_match.group(1).strip())
                    
                    # Extract RAPESEED OIL entry - simplified pattern
                    rapeseed_match = re.search(r'(RAPESEED OIL.*?)(?:TOTAL)', text)
                    if rapeseed_match:
                        lines.append(rapeseed_match.group(1).strip())
                
                for line in lines:
                    # Look for lines containing oil products
                    if 'OIL' in line.upper() and not any(skip in line.upper() for skip in ['ARTICLE', 'TOTAL NET', 'TOTAL VAT', 'TOTAL GROSS']):
                        # Parse the product line
                        # Pattern: PRODUCT_NAME PACKAGE QTY DISCOUNT UNIT_PRICE TOTAL
                        parts = line.split()
                        
                        if len(parts) >= 6:
                            # Find where the numeric values start
                            numeric_start_idx = -1
                            for i, part in enumerate(parts):
                                if re.match(r'^\d+\.?\d*$', part):
                                    numeric_start_idx = i
                                    break
                            
                            if numeric_start_idx > 0:
                                # Product name is everything before the first number
                                product_name = ' '.join(parts[:numeric_start_idx])
                                
                                # Extract numeric values
                                numbers = []
                                for part in parts[numeric_start_idx:]:
                                    try:
                                        numbers.append(float(part))
                                    except:
                                        # Check if it's a package format like "1x10LTR"
                                        if 'x' in part.lower() and any(c.isdigit() for c in part):
                                            # This is the package format, add it to product name
                                            product_name += ' ' + part
                                
                                # Typical format: QTY, DISCOUNT, UNIT_PRICE, TOTAL
                                product_info = {
                                    'product_name': product_name.strip(),
                                    'element_type': 'table',
                                    'original_text': line
                                }
                                
                                if len(numbers) >= 1:
                                    product_info['quantity'] = numbers[0]
                                if len(numbers) >= 3:
                                    product_info['unit_price'] = numbers[2]
                                if len(numbers) >= 4:
                                    product_info['total_price'] = numbers[3]
                                
                                products.append(product_info)
                        
                        # Alternative simpler parsing for common patterns
                        elif 'FRYING OIL' in line or 'RAPESEED OIL' in line:
                            # Extract basic info even if full parsing fails
                            product_info = self._parse_product_line(line)
                            if not product_info:
                                # Create basic entry
                                product_info = {
                                    'product_name': line.strip(),
                                    'element_type': 'table',
                                    'original_text': line
                                }
                            else:
                                product_info['element_type'] = 'table'
                                product_info['original_text'] = line
                            products.append(product_info)
                
            else:
                # For non-product tables, use the original parsing
                lines = text.split('\n')
                for line in lines:
                    # Skip header-like lines
                    if any(header in line.lower() for header in ['article', 'description', 'item', 'product', 'qty', 'price']):
                        continue
                        
                    # Try to extract product info from line
                    product_info = self._parse_product_line(line)
                    if product_info:
                        product_info['element_type'] = 'table'
                        product_info['original_text'] = line
                        products.append(product_info)
        
        return products
    
    def _parse_product_line(self, line: str) -> Optional[Dict]:
        """Parse a single line to extract product information"""
        
        # Skip lines that are clearly headers or non-product lines
        skip_patterns = [
            r'^ATRADE MENA',
            r'^Order No:',
            r'^THIS ORDER',
            r'^DELIVERY',
            r'^PAYMENT',
            r'^CONDITIONS',
            r'^Page\d+',
            r'^TRN Number',
            r'^Tel :',
            r'^Fax:',
            r'^Request'
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return None
        
        # Common patterns for product lines in invoices
        # Pattern 1: Product Name | Quantity | Unit | Price
        pattern1 = r'^(.+?)\s+(\d+(?:\.\d+)?)\s*([A-Za-z]+)?\s+(\d+(?:\.\d+)?)\s*$'
        
        # Pattern 2: Product with code (e.g., "PRODUCT NAME 1x10LTR")
        pattern2 = r'^(.+?)\s+(\d+)x(\d+[A-Za-z]+)\s*'
        
        # Pattern 3: Simple product with quantity
        pattern3 = r'^(.+?)\s+(\d+(?:\.\d+)?)\s*$'
        
        # Try patterns in order
        match = re.match(pattern1, line.strip())
        if match:
            return {
                'product_name': match.group(1).strip(),
                'quantity': float(match.group(2)),
                'unit': match.group(3) if match.group(3) else None,
                'unit_price': float(match.group(4))
            }
        
        match = re.match(pattern2, line.strip())
        if match:
            return {
                'product_name': match.group(1).strip(),
                'quantity': float(match.group(2)),
                'unit': match.group(3),
                'description': f"{match.group(2)}x{match.group(3)}"
            }
        
        match = re.match(pattern3, line.strip())
        if match and not re.match(r'^\d', match.group(1)):  # Ensure it doesn't start with a number
            return {
                'product_name': match.group(1).strip(),
                'quantity': float(match.group(2))
            }
        
        # If no pattern matches but line contains product-like text
        if len(line.strip()) > 5 and not line.strip()[0].isdigit():
            # Extract any numbers as potential quantity/price
            numbers = re.findall(r'\d+(?:\.\d+)?', line)
            
            # Remove numbers from product name
            product_name = re.sub(r'\d+(?:\.\d+)?', '', line).strip()
            product_name = re.sub(r'\s+', ' ', product_name)  # Normalize spaces
            
            if product_name:
                result = {'product_name': product_name}
                if numbers:
                    result['quantity'] = float(numbers[0])
                    if len(numbers) > 1:
                        result['unit_price'] = float(numbers[-1])
                return result
        
        return None
    
    def _extract_invoice_details_from_elements(self, elements: List[Dict], raw_text: str) -> Dict[str, Any]:
        """Extract invoice details from structured elements"""
        details = {
            'invoice_number': None,
            'invoice_date': None,
            'delivery_date': None,
            'customer_name': None,
            'supplier_name': None,
            'total_amount': None,
            'vat_amount': None
        }
        
        for element in elements:
            text = element.get('text', '').strip()
            element_type = element.get('type', '')
            
            # Look for invoice number
            if not details['invoice_number']:
                invoice_match = re.search(r'(?:Invoice|Order|PO)[\s#:]*([A-Z0-9\-]+)', text, re.I)
                if invoice_match:
                    details['invoice_number'] = invoice_match.group(1)
            
            # Look for dates
            date_pattern = r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}'
            dates = re.findall(date_pattern, text)
            if dates:
                if 'invoice' in text.lower() and not details['invoice_date']:
                    details['invoice_date'] = dates[0]
                elif 'delivery' in text.lower() and not details['delivery_date']:
                    details['delivery_date'] = dates[0]
                elif not details['invoice_date']:
                    details['invoice_date'] = dates[0]
            
            # Look for amounts (especially totals)
            if 'total' in text.lower() or 'gross' in text.lower():
                amounts = re.findall(r'[\d,]+\.?\d*', text)
                if amounts:
                    # Take the largest amount as total
                    amount_values = [float(a.replace(',', '')) for a in amounts]
                    if amount_values:
                        details['total_amount'] = max(amount_values)
            
            # Look for VAT
            if 'vat' in text.lower() or 'tax' in text.lower():
                vat_amounts = re.findall(r'[\d,]+\.?\d*', text)
                if vat_amounts:
                    details['vat_amount'] = float(vat_amounts[0].replace(',', ''))
            
            # Extract company names from title elements
            if 'Title' in element_type and not details['supplier_name']:
                # First title often contains supplier name
                if len(text) > 3 and text.isupper():
                    details['supplier_name'] = text
        
        return details
    
    def _find_product_mapping(self, product_text: str, mappings: Dict) -> Optional[str]:
        """Find mapping for a product text using intelligent word-based matching"""
        if not product_text or not mappings:
            return None
            
        product_lower = product_text.lower()
        
        # Step 1: Direct match
        for parsed_text, mapping_info in mappings.items():
            if 'product' in str(mapping_info.get('field_type', '')):
                if parsed_text.lower() == product_lower:
                    return mapping_info.get('mapped_value')
        
        # Step 2: Partial match
        for parsed_text, mapping_info in mappings.items():
            if 'product' in str(mapping_info.get('field_type', '')):
                if parsed_text.lower() in product_lower or product_lower in parsed_text.lower():
                    return mapping_info.get('mapped_value')
        
        # Step 3: Smart word-based matching
        # Extract important words from product name
        product_words = set(re.findall(r'\b[a-z]+\b', product_lower))
        # Remove common words that don't help with matching
        stopwords = {'the', 'of', 'and', 'or', 'with', 'for', 'in', 'on', 'at', 'to', 'a', 'an', 'x'}
        product_words = product_words - stopwords
        
        best_match = None
        best_score = 0
        
        for parsed_text, mapping_info in mappings.items():
            if 'product' in str(mapping_info.get('field_type', '')):
                mapping_words = set(re.findall(r'\b[a-z]+\b', parsed_text.lower()))
                mapping_words = mapping_words - stopwords
                
                # Calculate word overlap score
                common_words = product_words & mapping_words
                if common_words:
                    # Score based on percentage of words matched
                    score = len(common_words) / min(len(product_words), len(mapping_words)) if min(len(product_words), len(mapping_words)) > 0 else 0
                    
                    # Bonus for important brand/product words
                    important_words = {'bunge', 'procuisine', 'cuisine', 'pro', 'oil', 'sunflower', 'rapeseed', 'frying', 'canola', 'vegetable'}
                    important_matches = common_words & important_words
                    if important_matches:
                        score += 0.3 * len(important_matches)
                    
                    if score > best_score and score >= 0.4:  # At least 40% match
                        best_score = score
                        best_match = mapping_info.get('mapped_value')
        
        return best_match
    
    def _is_duplicate_product(self, product_name: str, existing_products: List[Dict]) -> bool:
        """Check if product already exists in the list"""
        for product in existing_products:
            if product.get('mapped', '').lower() == product_name.lower():
                return True
        return False
    
    def _assess_extraction_quality(self, parsed_data: Dict) -> Dict[str, Any]:
        """Assess the quality of extraction"""
        quality = {
            'has_products': len(parsed_data.get('products', [])) > 0,
            'has_quantities': len(parsed_data.get('quantities', [])) > 0,
            'has_prices': len(parsed_data.get('prices', [])) > 0,
            'unmapped_ratio': 0.0,
            'overall_score': 0.0
        }
        
        total_elements = (
            len(parsed_data.get('products', [])) +
            len(parsed_data.get('quantities', [])) +
            len(parsed_data.get('prices', [])) +
            len(parsed_data.get('unmapped_text', []))
        )
        
        if total_elements > 0:
            quality['unmapped_ratio'] = len(parsed_data.get('unmapped_text', [])) / total_elements
            
        # Calculate overall score
        score = 0
        if quality['has_products']:
            score += 40
        if quality['has_quantities']:
            score += 30
        if quality['has_prices']:
            score += 30
        
        # Penalize for high unmapped ratio
        score *= (1 - quality['unmapped_ratio'] * 0.5)
        
        quality['overall_score'] = round(score, 2)
        
        return quality
    
    # Database access methods (same as original MappingParser)
    def _get_customer_mappings(self, customer_id: str) -> Dict[str, Any]:
        """Get customer field mappings from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT parsed_text, field_type, mapped_value, description
                FROM customer_field_mappings
                WHERE customer_id = ?
            ''', (customer_id,))
            
            mappings = {}
            for row in cursor.fetchall():
                mappings[row[0]] = {
                    'field_type': row[1],
                    'mapped_value': row[2],
                    'description': row[3]
                }
            
            conn.close()
            return mappings
        except Exception as e:
            print(f"Error getting customer mappings: {e}")
            return {}
    
    def _get_customer_pricing(self, customer_id: str) -> Dict[str, float]:
        """Get customer-specific pricing from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT product_name, custom_price
                FROM customer_pricing
                WHERE customer_id = ?
            ''', (customer_id,))
            
            pricing = {}
            for row in cursor.fetchall():
                pricing[row[0]] = row[1]
            
            conn.close()
            return pricing
        except Exception as e:
            print(f"Error getting customer pricing: {e}")
            return {}
    
    def _get_customer_vat_config(self, customer_id: str) -> Dict[str, Any]:
        """Get customer VAT configuration"""
        try:
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
                    'vat_rate': row[0] if row[0] is not None else 5.0,
                    'vat_inclusive': bool(row[1]) if row[1] is not None else False,
                    'default_currency': row[2] if row[2] else 'AED'
                }
            
            return {
                'vat_rate': 5.0,
                'vat_inclusive': False,
                'default_currency': 'AED'
            }
        except Exception as e:
            print(f"Error getting VAT config: {e}")
            return {
                'vat_rate': 5.0,
                'vat_inclusive': False,
                'default_currency': 'AED'
            }
    
    def _detect_customer(self, text: str) -> Optional[str]:
        """Try to detect customer from text"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT customer_id, email, chain_alias FROM customers WHERE active = 1')
            customers = cursor.fetchall()
            conn.close()
            
            text_lower = text.lower()
            
            for customer_id, email, chain_alias in customers:
                # Check if email appears in text
                if email and email.lower() in text_lower:
                    return customer_id
                
                # Check if chain alias appears
                if chain_alias and chain_alias.lower() in text_lower:
                    return customer_id
                
                # Check if customer ID appears
                if customer_id.lower() in text_lower:
                    return customer_id
            
            return None
        except Exception as e:
            print(f"Error detecting customer: {e}")
            return None
    
    def _extract_price(self, text: str) -> float:
        """Extract price from text with improved pattern matching"""
        # Remove commas and normalize
        text = text.replace(',', '')
        
        # Try different price patterns
        patterns = [
            r'(?:AED|USD|EUR|GBP)?\s*(\d+(?:\.\d{1,2})?)',  # With currency
            r'(\d+\.\d{2})\b',  # Decimal with exactly 2 digits
            r'(\d+(?:\.\d+)?)\s*(?:AED|USD|EUR|GBP)',  # Number before currency
            r'(\d+(?:\.\d+)?)'  # Any number
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    # Return the largest value found (likely the price)
                    values = [float(m) for m in matches if float(m) > 0]
                    if values:
                        return max(values)
                except:
                    continue
        
        return 0.0
    
    def _extract_po_number(self, text: str) -> Optional[str]:
        """Extract purchase order number from text"""
        # Common PO number patterns
        patterns = [
            r'(?:PO|P\.O\.|Purchase Order|Order No)[:\s#]*([A-Z0-9\-]+)',
            r'Order\s+(?:Number|No|#)[:\s]*([A-Z0-9\-]+)',
            r'\b([A-Z]{1,3}\d{6,}[\-\d]*)\b'  # Generic alphanumeric pattern
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _build_items_list(self, parsed_data: Dict, customer_pricing: Dict, vat_config: Dict) -> List[Dict]:
        """Build final items list with pricing"""
        items = []
        
        # Match products with quantities and prices
        products = parsed_data.get('products', [])
        quantities = parsed_data.get('quantities', [])
        prices = parsed_data.get('prices', [])
        
        for i, product in enumerate(products):
            item = {
                'product': product.get('mapped', product.get('original', '')),
                'original_text': product.get('original', ''),
                'quantity': 1.0,
                'unit_price': 0.0,
                'total_price': 0.0,
                'vat_amount': 0.0,
                'price_source': 'not_found',
                'confidence': product.get('confidence', 0.5)
            }
            
            # Try to find matching quantity
            if i < len(quantities):
                item['quantity'] = quantities[i].get('value', 1.0)
            
            # Try to find price - first check customer pricing
            product_name = item['product']
            if product_name in customer_pricing:
                item['unit_price'] = customer_pricing[product_name]
                item['price_source'] = 'customer_pricing'
            elif i < len(prices):
                item['unit_price'] = prices[i].get('value', 0.0)
                item['price_source'] = 'extracted'
            
            # Calculate totals
            item['total_price'] = item['quantity'] * item['unit_price']
            
            # Calculate VAT
            if vat_config['vat_inclusive']:
                # Price includes VAT
                item['vat_amount'] = item['total_price'] * (vat_config['vat_rate'] / (100 + vat_config['vat_rate']))
            else:
                # VAT to be added
                item['vat_amount'] = item['total_price'] * (vat_config['vat_rate'] / 100)
            
            items.append(item)
        
        return items


if __name__ == "__main__":
    # Test the parser
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python unstructured_mapping_parser.py <pdf_file> [customer_id]")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    customer_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    parser = UnstructuredMappingParser()
    result = parser.parse_with_mappings(pdf_file, customer_id)
    
    print(json.dumps(result, indent=2, default=str))