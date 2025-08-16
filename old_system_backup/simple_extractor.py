#!/usr/bin/env python3
"""
Simple data extractor - extracts raw data without complex patterns
Then uses database matching to identify customers and items
"""

import re
import sqlite3
import sys
from typing import Dict, List, Any
from difflib import SequenceMatcher
import pdfplumber

sys.path.insert(0, '.')

class SimpleDataExtractor:
    """
    Simple extractor that pulls raw data and uses database matching
    """
    
    def __init__(self, db_path: str = "invoice_parser.db"):
        self.db_path = db_path
    
    def extract_file(self, file_path: str) -> Dict[str, Any]:
        """Extract raw data from file and match with database"""
        
        # Extract raw text
        text = self._extract_pdf_text(file_path)
        
        # Extract basic raw data
        raw_data = self._extract_raw_data(text)
        
        # Match with database
        customer_match = self._match_customer(raw_data, text)
        item_matches = self._match_items(raw_data, text)
        
        return {
            'file_path': file_path,
            'raw_text': text,
            'raw_data': raw_data,
            'customer_match': customer_match,
            'item_matches': item_matches,
            'confidence_score': self._calculate_confidence(customer_match, item_matches)
        }
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Simple PDF text extraction"""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error extracting PDF: {e}")
        return text
    
    def _extract_raw_data(self, text: str) -> Dict[str, Any]:
        """Extract basic raw data without complex patterns"""
        
        raw_data = {
            'emails': [],
            'phone_numbers': [],
            'amounts': [],
            'dates': [],
            'order_numbers': [],
            'company_names': [],
            'item_descriptions': [],
            'quantities': [],
            'addresses': []
        }
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Extract emails
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line)
            raw_data['emails'].extend(emails)
            
            # Extract phone numbers
            phones = re.findall(r'[\+]?[1-9]?[0-9]{7,15}', line)
            raw_data['phone_numbers'].extend(phones)
            
            # Extract amounts (AED, USD, etc)
            amounts = re.findall(r'(?:AED|USD)?\s*([0-9,]+\.?\d*)', line)
            raw_data['amounts'].extend(amounts)
            
            # Extract dates
            dates = re.findall(r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}', line)
            raw_data['dates'].extend(dates)
            
            # Extract order numbers (alphanumeric codes)
            orders = re.findall(r'\b[A-Z0-9\-]{5,20}\b', line)
            raw_data['order_numbers'].extend(orders)
            
            # Extract company names (words in CAPS)
            companies = re.findall(r'\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b', line)
            raw_data['company_names'].extend(companies)
            
            # Extract potential item descriptions (lines with product-like text)
            # Look for lines that contain product names and numbers (quantities/prices)
            line_upper = line.upper()
            if (re.search(r'[A-Za-z].{10,}.*\d+', line) and 
                not any(word in line_upper for word in ['NET TOTAL', 'GRAND TOTAL', 'VAT TOTAL', 'SUBTOTAL', 'ORDER NO', 'ORDER DATE', 'DELIVERY', 'GENERAL DELIVERY', 'REQUEST NO']) and
                not line.strip().startswith('Tel:') and
                not line.strip().startswith('Fax:') and
                not line.strip().startswith('Page:') and
                not re.match(r'^\d+\.', line.strip()) and  # Skip numbered instructions
                # Look for patterns typical of item lines: product name + unit + quantity + prices
                (re.search(r'[A-Za-z].*(TIN|LTR?|KG|CASE|PKG|BOTTLE|EACH|UNIT).*\d+\.\d{2}', line) or
                 # Or lines with multiple decimal numbers (prices)
                 len(re.findall(r'\d+\.\d{2}', line)) >= 2)):
                raw_data['item_descriptions'].append(line.strip())
            
            # Extract quantities
            qtys = re.findall(r'\b\d+(?:\.\d+)?\s*(?:PCS|KG|LTR|CASE|EACH|UNIT|PKG|TIN|BOTTLE)\b', line, re.IGNORECASE)
            raw_data['quantities'].extend(qtys)
        
        # Clean and deduplicate
        for key in raw_data:
            if isinstance(raw_data[key], list):
                raw_data[key] = list(set(raw_data[key]))  # Remove duplicates
                
        return raw_data
    
    def _match_customer(self, raw_data: Dict, text: str) -> Dict[str, Any]:
        """Match customer using email and company name matching"""
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all customers from database
        cursor.execute('SELECT * FROM customers')
        customers = cursor.fetchall()
        
        best_match = None
        best_score = 0.0
        
        for customer in customers:
            score = 0.0
            match_reasons = []
            
            # Email matching (highest priority)
            customer_email = (customer['email'] or '').lower()
            if customer_email:
                for extracted_email in raw_data['emails']:
                    if customer_email in extracted_email.lower() or extracted_email.lower() in customer_email:
                        score += 50.0  # High score for email match
                        match_reasons.append(f"Email match: {extracted_email}")
            
            # Company name matching (use customer_id as the name)
            customer_name = (customer['customer_id'] or '').upper()
            if customer_name:
                for company in raw_data['company_names']:
                    similarity = SequenceMatcher(None, customer_name, company).ratio()
                    if similarity > 0.6:  # 60% similarity threshold
                        score += similarity * 30.0
                        match_reasons.append(f"Name similarity: {company} ({similarity:.1%})")
            
            # Address/location matching (use place_of_supply as address)
            customer_address = (customer['place_of_supply'] or '').upper()
            if customer_address:
                text_upper = text.upper()
                for addr_part in customer_address.split():
                    if len(addr_part) > 3 and addr_part in text_upper:
                        score += 5.0
                        match_reasons.append(f"Address part: {addr_part}")
            
            if score > best_score:
                best_score = score
                best_match = {
                    'customer_id': customer['id'],
                    'customer_name': customer['customer_id'],  # Use customer_id as name
                    'score': score,
                    'match_reasons': match_reasons
                }
        
        conn.close()
        return best_match or {'score': 0.0}
    
    def _match_items(self, raw_data: Dict, text: str) -> List[Dict[str, Any]]:
        """Match items using description similarity"""
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all items from database
        cursor.execute('SELECT * FROM items')
        db_items = cursor.fetchall()
        
        matched_items = []
        
        for description in raw_data['item_descriptions']:
            best_item_match = None
            best_item_score = 0.0
            
            for db_item in db_items:
                item_name = (db_item['name'] or '').upper()
                item_description = (db_item['description'] or '').upper()
                
                # Calculate similarity with item name and description
                desc_upper = description.upper()
                
                # Try different matching approaches
                name_similarity = SequenceMatcher(None, desc_upper, item_name).ratio()
                desc_similarity = SequenceMatcher(None, desc_upper, item_description).ratio()
                
                # Also try substring matching for common words
                common_words = ['OIL', 'SUNFLOWER', 'OLIVE', 'FRYING', 'COOKING', 'VEGETABLE', 'CANOLA']
                word_bonus = 0.0
                for word in common_words:
                    if word in desc_upper and word in item_name:
                        word_bonus = 0.3  # 30% bonus for matching key words
                        break
                
                max_similarity = max(name_similarity, desc_similarity) + word_bonus
                
                if max_similarity > 0.4:  # Lower threshold with word matching
                    score = max_similarity * 100
                    
                    if score > best_item_score:
                        best_item_score = score
                        best_item_match = {
                            'item_id': db_item['id'],
                            'item_name': db_item['name'],
                            'parsed_description': description,
                            'score': score,
                            'similarity_type': 'name' if name_similarity > desc_similarity else 'description'
                        }
            
            if best_item_match:
                matched_items.append(best_item_match)
        
        conn.close()
        return matched_items
    
    def _calculate_confidence(self, customer_match: Dict, item_matches: List) -> float:
        """Calculate overall confidence score"""
        
        customer_score = customer_match.get('score', 0.0) / 100.0  # Normalize to 0-1
        items_score = 0.0
        
        if item_matches:
            avg_item_score = sum(item.get('score', 0.0) for item in item_matches) / len(item_matches)
            items_score = avg_item_score / 100.0  # Normalize to 0-1
        
        # Weighted combination: 70% customer, 30% items
        return (customer_score * 0.7) + (items_score * 0.3)


def test_simple_extractor():
    """Test the simple extractor"""
    
    extractor = SimpleDataExtractor()
    
    test_files = [
        'test lpos/F5.pdf',
        'test lpos/Atrade.pdf', 
        'test lpos/B202507-15118.pdf'
    ]
    
    for file_path in test_files:
        print(f"\n🔍 Testing {file_path}")
        try:
            result = extractor.extract_file(file_path)
            
            print(f"📧 Emails found: {result['raw_data']['emails']}")
            print(f"🏢 Companies: {result['raw_data']['company_names'][:5]}")  # First 5
            print(f"💰 Amounts: {result['raw_data']['amounts'][:5]}")  # First 5
            
            customer_match = result['customer_match']
            if customer_match.get('customer_name'):
                print(f"✅ Customer: {customer_match['customer_name']} ({customer_match['score']:.1f})")
            else:
                print("❌ No customer match")
            
            item_matches = result['item_matches']
            print(f"📦 Items matched: {len(item_matches)}")
            for item in item_matches[:3]:  # First 3
                print(f"   - {item['item_name']} ({item['score']:.1f}%)")
            
            print(f"🎯 Overall confidence: {result['confidence_score']:.1%}")
            
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_simple_extractor()