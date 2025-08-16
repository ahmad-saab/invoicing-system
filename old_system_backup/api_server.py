"""
Simple API Server for Invoice Parser with Customer Mappings
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
import os
import sqlite3
from datetime import datetime, timedelta
import time

# Import our parsers
from simple_extractor import SimpleDataExtractor
from mapping_parser import MappingParser
try:
    from unstructured_mapping_parser import UnstructuredMappingParser
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    print("Warning: Unstructured parser not available. Install unstructured[pdf] to enable.")
    UNSTRUCTURED_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="Simple Invoice Parser API",
    description="Parse invoices and map data using customer-defined mappings",
    version="2.0.0"
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize parsers
simple_parser = SimpleDataExtractor()
mapping_parser = MappingParser()
if UNSTRUCTURED_AVAILABLE:
    unstructured_parser = UnstructuredMappingParser()
else:
    unstructured_parser = None

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Simple Invoice Parser API",
        "version": "2.1.0",
        "endpoints": {
            "customers": "/api/customers",
            "parse": "/api/parse",
            "parse_with_mappings": "/api/parse/mapped",
            "parse_with_unstructured": "/api/parse/unstructured" if UNSTRUCTURED_AVAILABLE else None
        },
        "features": {
            "unstructured_parser": UNSTRUCTURED_AVAILABLE
        }
    }

# Customer Management Endpoints
@app.get("/api/customers")
async def get_customers(search: str = None):
    """Get all customers with optional search"""
    try:
        conn = sqlite3.connect('test_customers.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if search:
            query = '''
                SELECT * FROM customers 
                WHERE active = 1 
                AND (
                    LOWER(customer_id) LIKE LOWER(?) OR 
                    LOWER(email) LIKE LOWER(?) OR 
                    LOWER(chain_alias) LIKE LOWER(?)
                )
                ORDER BY customer_id
            '''
            search_pattern = f'%{search}%'
            cursor.execute(query, (search_pattern, search_pattern, search_pattern))
        else:
            cursor.execute('SELECT * FROM customers WHERE active = 1 ORDER BY customer_id')
        
        customers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"status": "success", "data": customers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Get a single customer by ID"""
    try:
        conn = sqlite3.connect('test_customers.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM customers 
            WHERE customer_id = ? AND active = 1
        ''', (customer_id,))
        
        customer = cursor.fetchone()
        conn.close()
        
        if customer:
            return {"status": "success", "data": dict(customer)}
        else:
            raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/customers")
async def add_customer(customer: Dict[str, Any]):
    """Add a new customer"""
    try:
        conn = sqlite3.connect('test_customers.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO customers (customer_id, email, chain_alias, place_of_supply, payment_term, active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (
            customer.get('customer_id'),
            customer.get('email'),
            customer.get('chain_alias', ''),
            customer.get('place_of_supply', 'Dubai'),
            customer.get('payment_term', '30 days')
        ))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Customer added successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Customer ID already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/customers/{customer_id}")
async def update_customer(customer_id: str, customer: Dict[str, Any]):
    """Update customer details including customer_id if changed"""
    try:
        conn = sqlite3.connect('test_customers.db')
        cursor = conn.cursor()
        
        new_customer_id = customer.get('customer_id', customer_id)
        
        # If customer_id is being changed, check if new ID already exists
        if new_customer_id != customer_id:
            cursor.execute('SELECT COUNT(*) FROM customers WHERE customer_id = ?', (new_customer_id,))
            if cursor.fetchone()[0] > 0:
                conn.close()
                raise HTTPException(status_code=400, detail=f"Customer ID '{new_customer_id}' already exists")
        
        # Update all fields including customer_id
        cursor.execute('''
            UPDATE customers 
            SET customer_id = ?, email = ?, chain_alias = ?, place_of_supply = ?, 
                payment_term = ?, trn = ?, currency = ?, vat_rate = ?, vat_inclusive = ?, default_currency = ?
            WHERE customer_id = ?
        ''', (
            new_customer_id,
            customer.get('email', ''),
            customer.get('chain_alias', ''),
            customer.get('place_of_supply', ''),
            customer.get('payment_term', '30 days'),
            customer.get('trn', ''),
            customer.get('currency', 'AED'),
            customer.get('vat_rate', 5.0),
            customer.get('vat_inclusive', 0),
            customer.get('default_currency', 'AED'),
            customer_id  # Original customer_id in WHERE clause
        ))
        
        # Check if the update was successful
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found")
        
        # If customer_id changed, update related tables
        if new_customer_id != customer_id:
            # Update field mappings
            cursor.execute('''
                UPDATE customer_field_mappings 
                SET customer_id = ? 
                WHERE customer_id = ?
            ''', (new_customer_id, customer_id))
            
            # Update customer pricing
            cursor.execute('''
                UPDATE customer_pricing 
                SET customer_id = ? 
                WHERE customer_id = ?
            ''', (new_customer_id, customer_id))
            
            # Update pricing history
            cursor.execute('''
                UPDATE pricing_history 
                SET customer_id = ? 
                WHERE customer_id = ?
            ''', (new_customer_id, customer_id))
            
            # Update parsing history
            cursor.execute('''
                UPDATE parsing_history 
                SET customer_id = ? 
                WHERE customer_id = ?
            ''', (new_customer_id, customer_id))
        
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Customer updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/customers/{customer_id}/mappings")
async def get_customer_mappings(customer_id: str):
    """Get field mappings for a specific customer"""
    try:
        conn = sqlite3.connect('test_customers.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM customer_field_mappings 
            WHERE customer_id = ? AND active = 1
            ORDER BY field_type, parsed_text
        ''', (customer_id,))
        mappings = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"status": "success", "data": mappings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/customers/{customer_id}/mappings")
async def add_customer_mapping(customer_id: str, mapping: Dict[str, Any]):
    """Add a new field mapping for a customer"""
    try:
        print(f"DEBUG: Adding mapping for customer {customer_id}")
        print(f"DEBUG: Mapping data: {mapping}")
        
        conn = sqlite3.connect('test_customers.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO customer_field_mappings 
            (customer_id, parsed_text, field_type, mapped_value, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            customer_id,
            mapping.get('parsed_text'),
            mapping.get('field_type', 'product'),
            mapping.get('mapped_value'),
            mapping.get('description', '')
        ))
        
        print(f"DEBUG: Mapping saved successfully, row ID: {cursor.lastrowid}")
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Mapping added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/customers/mappings/{mapping_id}")
async def delete_customer_mapping(mapping_id: int):
    """Delete a customer field mapping"""
    try:
        conn = sqlite3.connect('test_customers.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE customer_field_mappings SET active = 0 WHERE id = ?', (mapping_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Mapping deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Parsing Endpoints
@app.post("/api/parse")
async def parse_file(file: UploadFile = File(...)):
    """Parse uploaded file using simple extractor"""
    try:
        # Save uploaded file temporarily
        temp_path = f"temp/{file.filename}"
        os.makedirs("temp", exist_ok=True)
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Parse with simple extractor
        result = simple_parser.extract_file(temp_path)
        
        # Clean up
        os.remove(temp_path)
        
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/parse/mapped")
async def parse_with_mappings(file: UploadFile = File(...), customer_id: str = Form(None)):
    """Parse file and apply customer mappings"""
    start_time = time.time()
    try:
        # Save uploaded file temporarily
        temp_path = f"temp/{file.filename}"
        os.makedirs("temp", exist_ok=True)
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Parse with mapping parser
        print(f"DEBUG: Parsing file with customer_id: {customer_id}")
        result = mapping_parser.parse_with_mappings(temp_path, customer_id)
        
        # Show complete PDF text extraction for debugging
        try:
            import pdfplumber
            print(f"DEBUG: === COMPLETE PDF TEXT EXTRACTION ===")
            with pdfplumber.open(temp_path) as pdf:
                print(f"DEBUG: PDF has {len(pdf.pages)} pages")
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        lines = page_text.split('\n')
                        print(f"DEBUG: Page {page_num + 1} has {len(lines)} lines")
                        print(f"DEBUG: Page {page_num + 1} first 5 lines:")
                        for i, line in enumerate(lines[:5]):
                            print(f"  {i+1}. '{line.strip()}'")
                        print(f"DEBUG: Page {page_num + 1} last 5 lines:")
                        for i, line in enumerate(lines[-5:]):
                            print(f"  {len(lines)-4+i}. '{line.strip()}'")
                    else:
                        print(f"DEBUG: Page {page_num + 1} - No text extracted")
        except Exception as e:
            print(f"DEBUG: Error in complete PDF extraction: {e}")
        
        # Show what text was actually extracted from PDF
        if result.get('parsed_data', {}).get('products'):
            print(f"DEBUG: Extracted products from PDF:")
            for i, prod in enumerate(result['parsed_data']['products']):
                print(f"  Product {i+1}: original_text='{prod.get('original', 'N/A')}', mapped_to='{prod.get('mapped', 'N/A')}'")
        
        if result.get('parsed_data', {}).get('unmapped_text'):
            print(f"DEBUG: Unmapped text from PDF (ALL {len(result['parsed_data']['unmapped_text'])} lines):")
            for i, unmapped in enumerate(result['parsed_data']['unmapped_text'][:1000]):  # Show up to 1000 lines
                print(f"  Line {i+1}: '{unmapped.get('text', 'N/A')}'")
        
        print(f"DEBUG: Parser result customer_id: {result.get('customer_id')}")
        print(f"DEBUG: Mappings used: {result.get('mappings_used', 0)}")
        print(f"DEBUG: Items found: {len(result.get('items', []))}")
        
        # Show detailed item information
        for i, item in enumerate(result.get('items', [])):
            print(f"DEBUG: Item {i+1}: product='{item.get('product', 'N/A')}', price_source='{item.get('price_source', 'N/A')}', price={item.get('price', 0)}")
        
        # Check if we have custom pricing applied
        items_with_custom_pricing = [item for item in result.get('items', []) if item.get('price_source') == 'customer_pricing']
        print(f"DEBUG: Items with custom pricing: {len(items_with_custom_pricing)}")
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Save to parsing history
        conn = sqlite3.connect('test_customers.db')
        cursor = conn.cursor()
        
        # Determine status
        status = 'failed'
        if result.get('customer_id'):
            if result.get('unmapped_count', 0) > 5:
                status = 'partial'
            else:
                status = 'success'
        
        # Get customer name
        customer_name = None
        if result.get('customer_id'):
            cursor.execute('SELECT chain_alias, customer_id FROM customers WHERE customer_id = ?', 
                         (result['customer_id'],))
            cust = cursor.fetchone()
            if cust:
                customer_name = cust[0] or cust[1]
        
        # Calculate total amount from items
        total_amount = 0
        if result.get('items'):
            for item in result['items']:
                qty = float(item.get('quantity', 0))
                price = float(item.get('price', 0))
                total_amount += qty * price
        
        # Insert into history
        cursor.execute('''
            INSERT INTO parsing_history 
            (filename, customer_id, customer_name, status, items_found, total_amount,
             error_message, unmapped_count, confidence_score, invoice_date, po_number, processing_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file.filename,
            result.get('customer_id'),
            customer_name,
            status,
            len(result.get('items', [])),
            total_amount,
            None if status == 'success' else 'Check mappings',
            result.get('unmapped_count', 0),
            85.0 if status == 'success' else 50.0,
            result.get('invoice_details', {}).get('invoice_date'),
            result.get('purchase_order_number'),
            processing_time
        ))
        
        conn.commit()
        conn.close()
        
        # Clean up
        os.remove(temp_path)
        
        return {"status": "success", "data": result}
    except Exception as e:
        # Log failed parsing
        try:
            conn = sqlite3.connect('test_customers.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO parsing_history 
                (filename, status, error_message, processing_time_ms)
                VALUES (?, 'failed', ?, ?)
            ''', (file.filename, str(e), int((time.time() - start_time) * 1000)))
            conn.commit()
            conn.close()
        except:
            pass
        return {"status": "error", "message": str(e)}

@app.post("/api/parse/unstructured")
async def parse_with_unstructured(file: UploadFile = File(...), customer_id: str = Form(None), use_legacy: bool = Form(False)):
    """Parse file using unstructured.io library with customer mappings"""
    if not UNSTRUCTURED_AVAILABLE and not use_legacy:
        return {"status": "error", "message": "Unstructured parser not available. Install unstructured[pdf] to enable."}
    
    start_time = time.time()
    try:
        # Save uploaded file temporarily
        temp_path = f"temp/{file.filename}"
        os.makedirs("temp", exist_ok=True)
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Choose parser based on availability and preference
        if UNSTRUCTURED_AVAILABLE and not use_legacy:
            print(f"DEBUG: Using unstructured parser for {file.filename}")
            result = unstructured_parser.parse_with_mappings(temp_path, customer_id)
        else:
            print(f"DEBUG: Falling back to legacy parser for {file.filename}")
            result = mapping_parser.parse_with_mappings(temp_path, customer_id)
        
        # Add extraction method to result
        result['extraction_method'] = 'unstructured' if (UNSTRUCTURED_AVAILABLE and not use_legacy) else 'pdfplumber'
        
        # Enhanced debugging output for unstructured results
        if result.get('extraction_method') == 'unstructured':
            print(f"DEBUG: === UNSTRUCTURED EXTRACTION RESULTS ===")
            print(f"DEBUG: Extraction quality score: {result.get('extraction_quality', {}).get('overall_score', 0)}")
            print(f"DEBUG: Elements extracted: {result.get('unstructured_metadata', {}).get('total_elements', 0)}")
            
            if result.get('parsed_data', {}).get('products'):
                print(f"DEBUG: Products found: {len(result['parsed_data']['products'])}")
                for i, prod in enumerate(result['parsed_data']['products'][:10]):
                    print(f"  {i+1}. {prod.get('mapped', 'N/A')} (confidence: {prod.get('confidence', 0)})")
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Save to parsing history with extraction method
        conn = sqlite3.connect('test_customers.db')
        cursor = conn.cursor()
        
        # Determine status based on extraction quality
        status = 'failed'
        confidence_score = 50.0
        if result.get('customer_id'):
            quality = result.get('extraction_quality', {})
            if quality.get('overall_score', 0) > 70:
                status = 'success'
                confidence_score = quality.get('overall_score', 85)
            elif quality.get('overall_score', 0) > 40:
                status = 'partial'
                confidence_score = quality.get('overall_score', 60)
        
        # Get customer name
        customer_name = None
        if result.get('customer_id'):
            cursor.execute('SELECT chain_alias, customer_id FROM customers WHERE customer_id = ?', 
                         (result['customer_id'],))
            cust = cursor.fetchone()
            if cust:
                customer_name = cust[0] or cust[1]
        
        # Calculate total amount from items
        total_amount = sum(item.get('total_price', 0) for item in result.get('items', []))
        
        cursor.execute('''
            INSERT INTO parsing_history 
            (filename, customer_id, customer_name, status, items_found, total_amount,
             error_message, unmapped_count, confidence_score, invoice_date, po_number, 
             processing_time_ms, extraction_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file.filename,
            result.get('customer_id'),
            customer_name,
            status,
            len(result.get('items', [])),
            total_amount,
            None if status == 'success' else 'Check mappings',
            len(result.get('parsed_data', {}).get('unmapped_text', [])),
            confidence_score,
            result.get('invoice_details', {}).get('invoice_date'),
            result.get('purchase_order_number'),
            processing_time,
            result.get('extraction_method', 'unknown')
        ))
        
        conn.commit()
        conn.close()
        
        # Clean up
        os.remove(temp_path)
        
        return {"status": "success", "data": result, "processing_time_ms": processing_time}
        
    except Exception as e:
        # Log failed parsing
        try:
            conn = sqlite3.connect('test_customers.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO parsing_history 
                (filename, status, error_message, processing_time_ms)
                VALUES (?, 'failed', ?, ?)
            ''', (file.filename, str(e), int((time.time() - start_time) * 1000)))
            conn.commit()
            conn.close()
        except:
            pass
        return {"status": "error", "message": str(e)}

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        conn = sqlite3.connect('test_customers.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Overall statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'partial' THEN 1 ELSE 0 END) as partial,
                AVG(processing_time_ms) as avg_processing_time,
                SUM(total_amount) as total_revenue
            FROM parsing_history
        ''')
        stats = dict(cursor.fetchone())
        
        # Calculate success rate
        stats['success_rate'] = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        # Get daily parsing counts for last 7 days
        cursor.execute('''
            SELECT 
                DATE(parsed_at) as date,
                COUNT(*) as count,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count
            FROM parsing_history
            WHERE parsed_at >= date('now', '-7 days')
            GROUP BY DATE(parsed_at)
            ORDER BY date
        ''')
        daily_stats = [dict(row) for row in cursor.fetchall()]
        
        # Get top customers by invoice count
        cursor.execute('''
            SELECT 
                customer_name,
                customer_id,
                COUNT(*) as invoice_count,
                SUM(total_amount) as total_amount
            FROM parsing_history
            WHERE customer_id IS NOT NULL
            GROUP BY customer_id
            ORDER BY invoice_count DESC
            LIMIT 5
        ''')
        top_customers = [dict(row) for row in cursor.fetchall()]
        
        # Get recent failed invoices
        cursor.execute('''
            SELECT 
                filename,
                error_message,
                parsed_at,
                unmapped_count
            FROM parsing_history
            WHERE status = 'failed'
            ORDER BY parsed_at DESC
            LIMIT 10
        ''')
        failed_invoices = [dict(row) for row in cursor.fetchall()]
        
        # Get parsing by status
        cursor.execute('''
            SELECT 
                status,
                COUNT(*) as count
            FROM parsing_history
            GROUP BY status
        ''')
        status_breakdown = [dict(row) for row in cursor.fetchall()]
        
        # Get customer and mapping counts
        cursor.execute('SELECT COUNT(*) FROM customers WHERE active = 1')
        customer_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM customer_field_mappings WHERE active = 1')
        mapping_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "status": "success",
            "data": {
                "overall_stats": stats,
                "daily_stats": daily_stats,
                "top_customers": top_customers,
                "failed_invoices": failed_invoices,
                "status_breakdown": status_breakdown,
                "customer_count": customer_count,
                "mapping_count": mapping_count,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/dashboard/failed")
async def get_failed_invoices(limit: int = 50):
    """Get detailed list of failed invoices"""
    try:
        conn = sqlite3.connect('test_customers.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                filename,
                error_message,
                unmapped_count,
                parsed_at,
                processing_time_ms
            FROM parsing_history
            WHERE status IN ('failed', 'partial')
            ORDER BY parsed_at DESC
            LIMIT ?
        ''', (limit,))
        
        failed = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"status": "success", "data": failed}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Customer Pricing Endpoints
@app.get("/api/customers/{customer_id}/pricing")
async def get_customer_pricing(customer_id: str):
    """Get all pricing for a specific customer"""
    try:
        conn = sqlite3.connect('test_customers.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get customer info including VAT settings
        cursor.execute('''
            SELECT customer_id, chain_alias, vat_rate, vat_inclusive, default_currency
            FROM customers
            WHERE customer_id = ? AND active = 1
        ''', (customer_id,))
        customer = cursor.fetchone()
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get all pricing for this customer
        cursor.execute('''
            SELECT * FROM customer_pricing
            WHERE customer_id = ? AND active = 1
            ORDER BY product_name
        ''', (customer_id,))
        
        pricing = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "status": "success",
            "customer": dict(customer),
            "pricing": pricing
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/customers/{customer_id}/pricing")
async def add_customer_pricing(customer_id: str, pricing_data: Dict[str, Any]):
    """Add or update pricing for a customer"""
    try:
        print(f"DEBUG: Adding pricing for customer {customer_id}")
        print(f"DEBUG: Pricing data: {pricing_data}")
        
        conn = sqlite3.connect('test_customers.db')
        cursor = conn.cursor()
        
        # Check if customer exists
        cursor.execute('SELECT customer_id FROM customers WHERE customer_id = ?', (customer_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Insert or update pricing
        cursor.execute('''
            INSERT OR REPLACE INTO customer_pricing
            (customer_id, product_id, product_name, product_description, 
             unit_price, currency, uom, vat_rate, vat_inclusive)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            customer_id,
            pricing_data.get('product_id', ''),
            pricing_data.get('product_name'),
            pricing_data.get('product_description', ''),
            pricing_data.get('unit_price'),
            pricing_data.get('currency', 'AED'),
            pricing_data.get('uom', 'EACH'),
            pricing_data.get('vat_rate', 5.0),
            pricing_data.get('vat_inclusive', False)
        ))
        
        # Log price change in history
        cursor.execute('''
            INSERT INTO pricing_history
            (customer_id, product_name, new_price, changed_by, change_reason)
            VALUES (?, ?, ?, 'API', 'Updated via API')
        ''', (
            customer_id,
            pricing_data.get('product_name'),
            pricing_data.get('unit_price')
        ))
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Pricing updated successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/customers/{customer_id}/pricing/{product_name}")
async def delete_customer_pricing(customer_id: str, product_name: str):
    """Delete specific pricing for a customer"""
    try:
        conn = sqlite3.connect('test_customers.db')
        cursor = conn.cursor()
        
        # Soft delete - set active to 0
        cursor.execute('''
            UPDATE customer_pricing
            SET active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE customer_id = ? AND product_name = ?
        ''', (customer_id, product_name))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pricing not found")
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Pricing deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.put("/api/customers/{customer_id}/vat")
async def update_customer_vat(customer_id: str, vat_config: Dict[str, Any]):
    """Update customer VAT configuration"""
    try:
        conn = sqlite3.connect('test_customers.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE customers
            SET vat_rate = ?, vat_inclusive = ?, default_currency = ?
            WHERE customer_id = ?
        ''', (
            vat_config.get('vat_rate', 5.0),
            vat_config.get('vat_inclusive', False),
            vat_config.get('default_currency', 'AED'),
            customer_id
        ))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "VAT configuration updated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/pricing/search")
async def search_pricing(customer_id: str, product_name: str):
    """Search for specific product pricing for a customer"""
    try:
        conn = sqlite3.connect('test_customers.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Try exact match first
        cursor.execute('''
            SELECT * FROM customer_pricing
            WHERE customer_id = ? 
            AND LOWER(product_name) = LOWER(?)
            AND active = 1
        ''', (customer_id, product_name))
        
        result = cursor.fetchone()
        
        # If no exact match, try partial match
        if not result:
            cursor.execute('''
                SELECT * FROM customer_pricing
                WHERE customer_id = ?
                AND LOWER(product_name) LIKE LOWER(?)
                AND active = 1
                LIMIT 1
            ''', (customer_id, f'%{product_name}%'))
            result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return {"status": "success", "data": dict(result)}
        else:
            return {"status": "not_found", "message": "No pricing found for this product"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)