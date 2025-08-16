#!/usr/bin/env python3
"""
Simplified API server using new database structure
- Email as primary customer identifier
- All customer info from database
- Only product name mapping needed from user
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import json
import shutil
from pathlib import Path
import tempfile
from datetime import datetime
import logging
from simple_parser import SimpleParserUnstructured as SimpleParser
from export_manager import ZohoExportManager
from invoice_pipeline import InvoicePipeline
from email_manager import EmailManager

app = FastAPI(title="Invoice Parser API v2")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize managers
export_manager = ZohoExportManager()
pipeline = InvoicePipeline()
email_manager = EmailManager()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path
DB_PATH = "test_customers.db"

# Pydantic models
class Customer(BaseModel):
    email: str
    unique_alias: Optional[str] = None
    customer_name: str
    customer_id_number: str
    trn: str
    billing_address: str
    shipping_address: str
    payment_terms: int = 30
    currency: str = "AED"
    delivery_calendar: Optional[str] = '{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": false, "sunday": false}'

class ProductMapping(BaseModel):
    customer_email: str
    lpo_product_name: str
    system_product_name: str
    unit_price: float
    unit: str = "EACH"
    vat_rate: float = 5.0

class BranchIdentifier(BaseModel):
    customer_email: str
    branch_identifier: str
    branch_name: str
    delivery_address: str

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return {"message": "Invoice Parser API v2", "version": "2.0.0"}

# Customer endpoints
@app.get("/api/customers")
def get_customers():
    """Get all customers with multi-location indicator"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all customers
    cursor.execute("SELECT * FROM customers WHERE active = 1 ORDER BY customer_name")
    customers = [dict(row) for row in cursor.fetchall()]
    
    # Count locations per email
    cursor.execute("""
        SELECT email, COUNT(*) as location_count 
        FROM customers 
        WHERE active = 1 
        GROUP BY email 
        HAVING COUNT(*) > 1
    """)
    multi_location_emails = {row['email']: row['location_count'] for row in cursor.fetchall()}
    
    # Add multi-location indicator to each customer
    for customer in customers:
        if customer['email'] in multi_location_emails:
            customer['is_multi_location'] = True
            customer['total_locations'] = multi_location_emails[customer['email']]
        else:
            customer['is_multi_location'] = False
            customer['total_locations'] = 1
    
    conn.close()
    return {"status": "success", "data": customers}

@app.get("/api/customers/{email}")
def get_customer(email: str):
    """Get customer(s) by email - returns all locations for multi-location customers"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all customers with this email
    cursor.execute("SELECT * FROM customers WHERE email = ? AND active = 1", (email,))
    customers = cursor.fetchall()
    
    if not customers:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check if this is a multi-location customer
    if len(customers) > 1:
        # Get branch identifiers for this multi-location customer
        cursor.execute("SELECT * FROM branch_identifiers WHERE customer_email = ?", (email,))
        branches = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return {
            "status": "success",
            "multi_location": True,
            "locations_count": len(customers),
            "data": [dict(c) for c in customers],
            "branches": branches
        }
    else:
        conn.close()
        return {
            "status": "success",
            "multi_location": False,
            "data": dict(customers[0])
        }

@app.post("/api/customers")
def create_customer(customer: Customer):
    """Create new customer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO customers (email, unique_alias, customer_name, customer_id_number, 
                                  trn, billing_address, shipping_address, payment_terms, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer.email, customer.unique_alias, customer.customer_name, 
              customer.customer_id_number, customer.trn, customer.billing_address,
              customer.shipping_address, customer.payment_terms, customer.currency))
        conn.commit()
        return {"status": "success", "message": "Customer created"}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail="Customer with this email already exists")
    finally:
        conn.close()

@app.put("/api/customers/{email}")
def update_customer(email: str, customer: Customer):
    """Update customer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE customers 
        SET customer_name = ?, customer_id_number = ?, trn = ?, 
            billing_address = ?, shipping_address = ?, payment_terms = ?, 
            currency = ?, unique_alias = ?, updated_at = CURRENT_TIMESTAMP
        WHERE email = ?
    ''', (customer.customer_name, customer.customer_id_number, customer.trn,
          customer.billing_address, customer.shipping_address, customer.payment_terms,
          customer.currency, customer.unique_alias, email))
    
    conn.commit()
    conn.close()
    
    if cursor.rowcount > 0:
        return {"status": "success", "message": "Customer updated"}
    else:
        raise HTTPException(status_code=404, detail="Customer not found")

# Product mapping endpoints
@app.get("/api/customers/{email}/mappings")
def get_customer_mappings(email: str):
    """Get all product mappings for a customer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM product_mappings 
        WHERE customer_email = ? AND active = 1
        ORDER BY lpo_product_name
    ''', (email,))
    mappings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"status": "success", "data": mappings}

@app.post("/api/customers/{email}/mappings")
def create_product_mapping(email: str, mapping: ProductMapping):
    """Create product mapping for customer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO product_mappings 
            (customer_email, lpo_product_name, system_product_name, unit_price, unit, vat_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (email, mapping.lpo_product_name, mapping.system_product_name,
              mapping.unit_price, mapping.unit, mapping.vat_rate))
        conn.commit()
        return {"status": "success", "message": "Mapping created", "id": cursor.lastrowid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/mappings/{mapping_id}")
def delete_mapping(mapping_id: int):
    """Delete a product mapping"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE product_mappings SET active = 0 WHERE id = ?", (mapping_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Mapping deleted"}

# Branch endpoints
@app.get("/api/customers/{email}/branches")
def get_customer_branches(email: str):
    """Get all branches for a customer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM branch_identifiers 
        WHERE customer_email = ?
        ORDER BY branch_name
    ''', (email,))
    branches = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"status": "success", "data": branches}

@app.post("/api/customers/{email}/branches")
def create_branch(email: str, branch: BranchIdentifier):
    """Create branch identifier for customer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO branch_identifiers 
            (customer_email, branch_identifier, branch_name, delivery_address)
            VALUES (?, ?, ?, ?)
        ''', (email, branch.branch_identifier, branch.branch_name, branch.delivery_address))
        conn.commit()
        return {"status": "success", "message": "Branch created", "id": cursor.lastrowid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

# Parsing endpoint
@app.post("/api/parse")
async def parse_lpo(
    file: UploadFile = File(...),
    customer_email: str = Form(...),
    add_to_queue: bool = Form(False)
):
    """Parse LPO with known customer email (from SMTP sender)"""
    
    # Save uploaded file temporarily
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        # Parse the LPO
        parser = SimpleParser()
        
        # For demo: Override the email detection with provided email
        result = parser.parse_lpo(str(file_path))
        
        # If no customer found by extraction, use provided email
        if not result['customer'] and customer_email:
            # Read the file to get text for branch detection
            with open(file_path, 'rb') as f:
                from unstructured.partition.pdf import partition_pdf
                elements = partition_pdf(file=f)
                full_text = '\n'.join([str(el) for el in elements])
            
            customer = parser._get_customer_by_email(customer_email, full_text)
            if customer:
                result['customer'] = customer
                # Re-parse with known customer
                result = parser.parse_lpo(str(file_path), customer_email)
                # The result already has customer, items and totals
        
        # Save parsing history with enhanced error tracking
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Determine if there were parsing issues
        has_unmapped = any(item.get('needs_mapping') for item in result.get('items', []))
        no_items = len(result.get('items', [])) == 0
        
        # Update status based on results
        if result['status'] == 'error':
            status = 'error'
        elif no_items:
            status = 'error'
            result['errors'].append('No products extracted from document')
        elif has_unmapped:
            status = 'partial'
        else:
            status = result['status']
        
        # Save to parsing_history
        cursor.execute('''
            INSERT INTO parsing_history 
            (filename, customer_email, status, extracted_data, invoice_data, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (file.filename, customer_email, status, 
              json.dumps(result.get('items', [])), 
              json.dumps(result),
              json.dumps(result.get('errors', []))))
        
        # If there were failures, save detailed info to parsing_failures
        if status in ['error', 'partial']:
            unmapped = [item['lpo_product_name'] for item in result.get('items', []) 
                       if item.get('needs_mapping')]
            
            cursor.execute('''
                INSERT INTO parsing_failures 
                (filename, customer_email, error_type, error_message, debug_info, 
                 extracted_text, unmapped_products)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                file.filename,
                customer_email,
                'no_extraction' if no_items else 'unmapped_products' if has_unmapped else 'parse_error',
                result.get('errors', ['Unknown error'])[0] if result.get('errors') else 'Some products could not be mapped',
                json.dumps(result.get('debug_info', {})),
                result.get('debug_info', {}).get('complete_text_preview', ''),
                json.dumps(unmapped) if unmapped else None
            ))
        
        conn.commit()
        
        # Add to processing queue if requested
        queue_id = None
        if add_to_queue and result.get('status') == 'success':
            cursor.execute('''
                INSERT INTO invoice_queue 
                (source, source_id, filename, file_path, customer_email, status, parse_result, export_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('manual', f'manual_{datetime.now().strftime("%Y%m%d_%H%M%S")}', 
                  file.filename, str(file_path), customer_email, 'completed',
                  json.dumps(result), 'pending'))
            queue_id = cursor.lastrowid
            conn.commit()
            result['queue_id'] = queue_id
            result['added_to_queue'] = True
        
        conn.close()
        
        return result
        
    finally:
        # Clean up temp file only if not added to queue
        if file_path.exists() and not add_to_queue:
            file_path.unlink()

# Parsing failures endpoints
@app.get("/api/parsing-failures")
def get_parsing_failures():
    """Get all parsing failures with details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            pf.*,
            c.customer_name
        FROM parsing_failures pf
        LEFT JOIN customers c ON pf.customer_email = c.email
        WHERE pf.resolved = 0
        ORDER BY pf.created_at DESC
        LIMIT 50
    ''')
    
    failures = []
    for row in cursor.fetchall():
        failure = dict(row)
        # Parse JSON fields
        if failure.get('debug_info'):
            try:
                failure['debug_info'] = json.loads(failure['debug_info'])
            except:
                pass
        if failure.get('unmapped_products'):
            try:
                failure['unmapped_products'] = json.loads(failure['unmapped_products'])
            except:
                pass
        failures.append(failure)
    
    conn.close()
    return {"status": "success", "data": failures}

@app.post("/api/parsing-failures/{failure_id}/resolve")
def resolve_parsing_failure(failure_id: int, resolution_notes: str = ""):
    """Mark a parsing failure as resolved"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE parsing_failures
        SET resolved = 1,
            resolved_at = CURRENT_TIMESTAMP,
            resolution_notes = ?
        WHERE id = ?
    ''', (resolution_notes, failure_id))
    
    conn.commit()
    conn.close()
    
    if cursor.rowcount > 0:
        return {"status": "success", "message": "Failure marked as resolved"}
    else:
        raise HTTPException(status_code=404, detail="Failure not found")

# Dashboard endpoints
@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    """Get dashboard statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Overall statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'partial' THEN 1 ELSE 0 END) as partial
        FROM parsing_history
    ''')
    row = cursor.fetchone()
    if row:
        total = row['total'] or 0
        success = row['success'] or 0
        failed = row['failed'] or 0
        partial = row['partial'] or 0
        
        stats['overall_stats'] = {
            'total': total,
            'success': success,
            'failed': failed,
            'partial': partial,
            'success_rate': (success / total * 100) if total > 0 else 0,
            'total_revenue': 0,  # Calculate from invoice_data
            'avg_processing_time': 2000  # Placeholder
        }
    
    # Daily statistics for last 7 days
    cursor.execute('''
        SELECT 
            DATE(parse_date) as date,
            COUNT(*) as count,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count
        FROM parsing_history
        WHERE parse_date >= date('now', '-7 days')
        GROUP BY DATE(parse_date)
        ORDER BY date DESC
    ''')
    stats['daily_stats'] = [dict(row) for row in cursor.fetchall()]
    
    # Status breakdown
    cursor.execute('''
        SELECT 
            status,
            COUNT(*) as count
        FROM parsing_history
        GROUP BY status
    ''')
    stats['status_breakdown'] = [dict(row) for row in cursor.fetchall()]
    
    # Top customers by volume
    cursor.execute('''
        SELECT 
            c.customer_name,
            c.email as customer_id,
            COUNT(p.id) as invoice_count,
            0 as total_amount
        FROM parsing_history p
        JOIN customers c ON p.customer_email = c.email
        WHERE p.status = 'success'
        GROUP BY p.customer_email
        ORDER BY invoice_count DESC
        LIMIT 5
    ''')
    stats['top_customers'] = [dict(row) for row in cursor.fetchall()]
    
    # Recent failed invoices
    cursor.execute('''
        SELECT 
            filename,
            customer_email,
            status,
            parse_date as parsed_at,
            CASE 
                WHEN status = 'error' THEN 'Failed to parse document'
                WHEN status = 'partial' THEN 'Some items could not be mapped'
                ELSE 'Unknown error'
            END as error_message,
            0 as unmapped_count
        FROM parsing_history
        WHERE status IN ('error', 'partial')
        ORDER BY parse_date DESC
        LIMIT 10
    ''')
    stats['failed_invoices'] = [dict(row) for row in cursor.fetchall()]
    
    # Customer and mapping counts
    cursor.execute('SELECT COUNT(*) as count FROM customers WHERE active = 1')
    stats['customer_count'] = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM product_mappings WHERE active = 1')
    stats['mapping_count'] = cursor.fetchone()['count']
    
    conn.close()
    
    return {"status": "success", "data": stats}

# Export endpoints
@app.post("/api/export/zoho")
async def export_to_zoho(invoice_data: Dict[str, Any]):
    """Export parsed data to Zoho Books compatible CSV"""
    try:
        # Validate before export
        validation = export_manager.validate_export(invoice_data)
        
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid invoice data: Missing {', '.join(validation['missing_required'])}"
            )
        
        # Export to CSV
        filepath = export_manager.export_to_zoho_csv(invoice_data)
        
        # Return file
        return FileResponse(
            filepath,
            media_type="text/csv",
            filename=Path(filepath).name,
            headers={
                "Content-Disposition": f"attachment; filename={Path(filepath).name}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export/zoho/batch")
async def export_batch_to_zoho(invoices: List[Dict[str, Any]]):
    """Export multiple invoices to single Zoho CSV file"""
    try:
        if not invoices:
            raise HTTPException(status_code=400, detail="No invoices provided")
        
        # Validate all invoices
        invalid_invoices = []
        for i, invoice in enumerate(invoices):
            validation = export_manager.validate_export(invoice)
            if not validation['valid']:
                invalid_invoices.append(f"Invoice {i+1}: {', '.join(validation['missing_required'])}")
        
        if invalid_invoices:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid invoices: {'; '.join(invalid_invoices)}"
            )
        
        # Export batch
        filepath = export_manager.export_batch(invoices)
        
        return FileResponse(
            filepath,
            media_type="text/csv",
            filename=Path(filepath).name,
            headers={
                "Content-Disposition": f"attachment; filename={Path(filepath).name}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/validate")
async def validate_invoice_for_export(invoice_data: Dict[str, Any]):
    """Validate invoice data before export"""
    validation = export_manager.validate_export(invoice_data)
    return {
        "status": "success" if validation['valid'] else "error",
        "validation": validation
    }

# Pipeline endpoints
@app.get("/api/pipeline/stats")
def get_pipeline_statistics():
    """Get pipeline processing statistics"""
    stats = pipeline.get_queue_statistics()
    return {"status": "success", "data": stats}

@app.get("/api/pipeline/queue")
def get_queue_items(status: Optional[str] = None, limit: int = 50):
    """Get items from processing queue"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute('''
            SELECT * FROM invoice_queue 
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (status, limit))
    else:
        cursor.execute('''
            SELECT * FROM invoice_queue 
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
    
    items = []
    for row in cursor.fetchall():
        item = dict(row)
        # Parse JSON fields if present
        if item.get('parse_result'):
            try:
                item['parse_result'] = json.loads(item['parse_result'])
            except:
                pass
        items.append(item)
    
    conn.close()
    return {"status": "success", "data": items}

@app.post("/api/pipeline/process")
async def run_pipeline(fetch_emails: bool = False, auto_export: bool = True):
    """Run the invoice processing pipeline"""
    try:
        results = pipeline.process_pipeline(fetch_emails=fetch_emails, auto_export=auto_export)
        return {
            "status": "success",
            "data": results,
            "message": f"Processed {results['total_processed']} invoices, exported {results['total_exported']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipeline/fetch-emails")
async def fetch_emails():
    """Fetch emails and add to processing queue"""
    try:
        results = pipeline.fetch_emails_to_queue()
        return {
            "status": "success",
            "data": results,
            "message": f"Fetched {results['emails_fetched']} emails, queued {results['attachments_queued']} attachments"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipeline/export-batch")
async def export_batch_from_queue(request_data: Optional[Dict[str, Any]] = None):
    """Export completed invoices from queue"""
    try:
        invoice_ids = None
        if request_data and 'invoice_ids' in request_data:
            invoice_ids = request_data['invoice_ids']
        
        results = pipeline.export_invoices_batch(invoice_ids)
        return {
            "status": "success",
            "data": results,
            "message": f"Exported {results['exported_count']} invoices"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email configuration endpoints
@app.get("/api/email-config")
def get_email_configs():
    """Get all email configurations"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, config_name, email_address, server, port, use_ssl, use_tls,
               check_interval, folders, search_subjects, unseen_only, active,
               created_at, updated_at
        FROM email_config
        ORDER BY config_name
    ''')
    
    configs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"status": "success", "data": configs}

@app.get("/api/email-config/{config_name}")
def get_email_config(config_name: str):
    """Get specific email configuration"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, config_name, email_address, server, port, use_ssl, use_tls,
               check_interval, folders, search_subjects, unseen_only, active
        FROM email_config
        WHERE config_name = ?
    ''', (config_name,))
    
    config = cursor.fetchone()
    conn.close()
    
    if config:
        return {"status": "success", "data": dict(config)}
    else:
        raise HTTPException(status_code=404, detail="Configuration not found")

@app.post("/api/email-config")
async def save_email_config(config_data: Dict[str, Any]):
    """Save or update email configuration"""
    logger.info(f"Saving email config: {config_data}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if config exists
        config_name = config_data.get('config_name', 'default')
        cursor.execute('SELECT id FROM email_config WHERE config_name = ?', (config_name,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing
            cursor.execute('''
                UPDATE email_config
                SET email_address = ?, password = ?, server = ?, port = ?,
                    use_ssl = ?, use_tls = ?, check_interval = ?,
                    folders = ?, search_subjects = ?, unseen_only = ?,
                    active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE config_name = ?
            ''', (
                config_data.get('email_address'),
                config_data.get('password', ''),
                config_data.get('server', 'imap.gmail.com'),
                config_data.get('port', 993),
                config_data.get('use_ssl', True),
                config_data.get('use_tls', False),
                config_data.get('check_interval', 300),
                config_data.get('folders', 'INBOX'),
                config_data.get('search_subjects', ''),
                config_data.get('unseen_only', True),
                config_data.get('active', True),
                config_name
            ))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO email_config (
                    config_name, email_address, password, server, port,
                    use_ssl, use_tls, check_interval, folders,
                    search_subjects, unseen_only, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config_name,
                config_data.get('email_address'),
                config_data.get('password', ''),
                config_data.get('server', 'imap.gmail.com'),
                config_data.get('port', 993),
                config_data.get('use_ssl', True),
                config_data.get('use_tls', False),
                config_data.get('check_interval', 300),
                config_data.get('folders', 'INBOX'),
                config_data.get('search_subjects', ''),
                config_data.get('unseen_only', True),
                config_data.get('active', True)
            ))
        
        conn.commit()
        
        # Log what was actually saved
        cursor.execute('SELECT email_address, server, port FROM email_config WHERE config_name = ?', (config_name,))
        saved_config = cursor.fetchone()
        logger.info(f"Saved config result: {saved_config}")
        
        return {"status": "success", "message": "Configuration saved"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.post("/api/email-config/test")
async def test_email_connection(config_data: Dict[str, Any]):
    """Test email connection with provided configuration"""
    try:
        # Test connection
        test_config = {
            'email_address': config_data.get('email_address'),
            'password': config_data.get('password'),
            'server': config_data.get('server', 'imap.gmail.com'),
            'port': config_data.get('port', 993),
            'use_ssl': config_data.get('use_ssl', True)
        }
        
        # Validate required fields
        if not test_config['email_address'] or test_config['email_address'] == 'placeholder@example.com':
            return {"status": "error", "message": "Please enter a valid email address"}
            
        if not test_config['password']:
            return {"status": "error", "message": "Please enter your email password or App Password"}
            
        if not test_config['server'] or test_config['server'] == 'mail.example.com':
            return {"status": "error", "message": "Please enter a valid IMAP server (e.g., imap.gmail.com)"}
        
        success = email_manager.connect_to_email(test_config)
        
        if success:
            email_manager.disconnect()
            return {"status": "success", "message": "✅ Connection successful! Email configuration is working."}
        else:
            # If full email failed, try with just username part for own mail servers
            if '@' in test_config['email_address'] and not success:
                username_only = test_config['email_address'].split('@')[0]
                test_config_alt = test_config.copy()
                test_config_alt['email_address'] = username_only
                
                logger.info(f"Trying alternative username format: {username_only}")
                success_alt = email_manager.connect_to_email(test_config_alt)
                
                if success_alt:
                    email_manager.disconnect()
                    return {
                        "status": "success", 
                        "message": f"✅ Connection successful using username '{username_only}' (without domain)!"
                    }
            
            return {"status": "error", "message": "❌ Authentication failed. Check server logs for details. Try: 1) Username only vs full email, 2) Verify IMAP enabled, 3) Check IP restrictions"}
            
    except Exception as e:
        return {"status": "error", "message": f"Connection error: {str(e)}"}

# Export file management endpoints
@app.get("/api/exports")
def list_exported_files():
    """List all exported CSV files"""
    export_dir = Path("exports")
    files = []
    
    if export_dir.exists():
        for file_path in export_dir.glob("*.csv"):
            files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                "path": str(file_path)
            })
    
    # Sort by creation date, newest first
    files.sort(key=lambda x: x['created'], reverse=True)
    
    return {"status": "success", "data": files}

@app.get("/api/exports/{filename}")
async def download_export(filename: str):
    """Download a specific exported CSV file"""
    file_path = Path("exports") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="text/csv",
        filename=filename,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)