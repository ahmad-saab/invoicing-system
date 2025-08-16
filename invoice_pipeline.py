#!/usr/bin/env python3
"""
Unified Invoice Processing Pipeline
Connects email fetching, parsing, and export to Zoho
"""
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

from email_manager import EmailManager
from simple_parser import SimpleParserUnstructured
from export_manager import ZohoExportManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InvoicePipeline:
    """Unified pipeline for processing invoices from various sources"""
    
    def __init__(self, db_path: str = "test_customers.db"):
        """Initialize pipeline components"""
        self.db_path = db_path
        self.email_manager = EmailManager(db_path)
        self.parser = SimpleParserUnstructured()
        self.export_manager = ZohoExportManager()
        
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def fetch_emails_to_queue(self, config_name: str = "default") -> Dict[str, Any]:
        """Fetch emails and add to processing queue"""
        logger.info("Fetching emails...")
        results = self.email_manager.fetch_and_queue_emails(config_name)
        logger.info(f"Fetched {results['emails_fetched']} emails, queued {results['attachments_queued']} attachments")
        return results
    
    def get_pending_invoices(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending invoices from queue"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM invoice_queue 
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
        ''', (limit,))
        
        invoices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return invoices
    
    def process_invoice(self, queue_item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single invoice from queue"""
        result = {
            'success': False,
            'queue_id': queue_item['id'],
            'filename': queue_item['filename'],
            'parse_result': None,
            'error': None
        }
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Update status to processing
            cursor.execute('''
                UPDATE invoice_queue 
                SET status = 'processing', processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (queue_item['id'],))
            conn.commit()
            
            # Parse the invoice
            logger.info(f"Processing {queue_item['filename']}...")
            parse_result = self.parser.parse_lpo(
                queue_item['file_path'],
                queue_item.get('customer_email')
            )
            
            # Store parse result
            result['parse_result'] = parse_result
            
            # Update queue with results - check for critical errors that prevent export
            critical_errors = [
                'Customer not found',
                'No customer email',
                'Invalid customer data'
            ]
            
            has_critical_error = any(
                any(critical in str(error) for critical in critical_errors)
                for error in parse_result.get('errors', [])
            )
            
            # Only mark as completed if no critical errors AND customer found AND items exist
            customer_found = parse_result.get('customer') is not None
            has_items = len(parse_result.get('items', [])) > 0
            
            if (parse_result.get('status') == 'success' and 
                not has_critical_error and 
                customer_found and 
                has_items):
                cursor.execute('''
                    UPDATE invoice_queue 
                    SET status = 'completed',
                        parse_result = ?,
                        export_status = 'pending'
                    WHERE id = ?
                ''', (json.dumps(parse_result), queue_item['id']))
                result['success'] = True
                logger.info(f"Successfully parsed {queue_item['filename']} - ready for export")
            else:
                # Determine error message
                if has_critical_error:
                    error_msg = next((error for error in parse_result.get('errors', []) 
                                    if any(critical in str(error) for critical in critical_errors)), 
                                   'Critical parsing error')
                elif not customer_found:
                    error_msg = 'Customer not found - cannot export'
                elif not has_items:
                    error_msg = 'No items extracted - cannot export'
                else:
                    error_msg = parse_result.get('errors', ['Unknown error'])[0]
                
                cursor.execute('''
                    UPDATE invoice_queue 
                    SET status = 'failed',
                        parse_result = ?,
                        error_message = ?
                    WHERE id = ?
                ''', (json.dumps(parse_result), error_msg, queue_item['id']))
                
                # Also record in parsing_failures table for user visibility
                self._record_parsing_failure(cursor, queue_item, parse_result, error_msg)
                
                result['error'] = error_msg
                logger.error(f"Failed to parse {queue_item['filename']}: {error_msg}")
            
            conn.commit()
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = str(e)
            cursor.execute('''
                UPDATE invoice_queue 
                SET status = 'failed',
                    error_message = ?
                WHERE id = ?
            ''', (error_msg, queue_item['id']))
            conn.commit()
            result['error'] = error_msg
            logger.error(f"Error processing {queue_item['filename']}: {e}")
        
        finally:
            conn.close()
        
        return result
    
    def _record_parsing_failure(self, cursor, queue_item: Dict[str, Any], parse_result: Dict[str, Any], error_msg: str):
        """Record parsing failure in parsing_failures table for user visibility"""
        try:
            # Determine error type
            if 'Customer not found' in error_msg:
                error_type = 'customer_not_found'
            elif 'No items extracted' in error_msg:
                error_type = 'no_items_extracted'
            elif 'cannot export' in error_msg:
                error_type = 'export_validation_failed'
            else:
                error_type = 'parsing_error'
            
            # Get debug info and text preview
            debug_info = parse_result.get('debug_info', {})
            extracted_text = debug_info.get('complete_text_preview', '')
            
            # Get unmapped products if any
            items = parse_result.get('items', [])
            unmapped_products = [item['lpo_product_name'] for item in items if item.get('needs_mapping')]
            
            cursor.execute('''
                INSERT INTO parsing_failures 
                (filename, customer_email, error_type, error_message, debug_info, 
                 extracted_text, unmapped_products)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                queue_item['filename'],
                queue_item.get('customer_email', 'unknown'),
                error_type,
                error_msg,
                json.dumps(debug_info),
                extracted_text[:1000] if extracted_text else '',  # Limit text preview
                json.dumps(unmapped_products) if unmapped_products else None
            ))
            
            logger.info(f"Recorded parsing failure for {queue_item['filename']} - {error_type}")
            
        except Exception as e:
            logger.warning(f"Failed to record parsing failure: {e}")
    
    def get_invoices_for_export(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get successfully parsed invoices ready for export"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM invoice_queue 
            WHERE status = 'completed' 
            AND export_status = 'pending'
            ORDER BY processed_at ASC
            LIMIT ?
        ''', (limit,))
        
        invoices = []
        for row in cursor.fetchall():
            invoice_data = dict(row)
            # Parse the JSON result
            if invoice_data.get('parse_result'):
                invoice_data['parse_result'] = json.loads(invoice_data['parse_result'])
            invoices.append(invoice_data)
        
        conn.close()
        return invoices
    
    def export_invoices_batch(self, invoice_ids: List[int] = None) -> Dict[str, Any]:
        """Export a batch of invoices to Zoho CSV"""
        result = {
            'success': False,
            'exported_count': 0,
            'export_path': None,
            'errors': []
        }
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get invoices to export
            if invoice_ids:
                placeholders = ','.join('?' * len(invoice_ids))
                cursor.execute(f'''
                    SELECT * FROM invoice_queue 
                    WHERE id IN ({placeholders})
                    AND status = 'completed'
                ''', invoice_ids)
            else:
                cursor.execute('''
                    SELECT * FROM invoice_queue 
                    WHERE status = 'completed' 
                    AND export_status = 'pending'
                    LIMIT 100
                ''')
            
            invoices_to_export = []
            queue_ids = []
            
            for row in cursor.fetchall():
                queue_item = dict(row)
                queue_ids.append(queue_item['id'])
                
                # Parse the stored result
                if queue_item.get('parse_result'):
                    parse_result = json.loads(queue_item['parse_result'])
                    invoices_to_export.append(parse_result)
            
            if not invoices_to_export:
                result['errors'].append("No invoices to export")
                return result
            
            # Export to CSV
            logger.info(f"Exporting {len(invoices_to_export)} invoices...")
            export_path = self.export_manager.export_batch(invoices_to_export)
            
            # Update export status
            for queue_id in queue_ids:
                cursor.execute('''
                    UPDATE invoice_queue 
                    SET export_status = 'exported',
                        export_path = ?,
                        exported_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (export_path, queue_id))
            
            conn.commit()
            
            result['success'] = True
            result['exported_count'] = len(invoices_to_export)
            result['export_path'] = export_path
            logger.info(f"Exported {len(invoices_to_export)} invoices to {export_path}")
            
        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Export failed: {e}")
            conn.rollback()
        
        finally:
            conn.close()
        
        return result
    
    def process_pipeline(self, fetch_emails: bool = True, auto_export: bool = True) -> Dict[str, Any]:
        """Run the complete pipeline"""
        results = {
            'fetch_results': None,
            'processed': [],
            'export_results': None,
            'total_processed': 0,
            'total_exported': 0
        }
        
        # Step 1: Fetch emails if enabled
        if fetch_emails:
            results['fetch_results'] = self.fetch_emails_to_queue()
        
        # Step 2: Process pending invoices
        pending = self.get_pending_invoices(limit=20)
        logger.info(f"Found {len(pending)} pending invoices to process")
        
        for invoice in pending:
            process_result = self.process_invoice(invoice)
            results['processed'].append(process_result)
            if process_result['success']:
                results['total_processed'] += 1
        
        # Step 3: Export if enabled
        if auto_export:
            ready_for_export = self.get_invoices_for_export()
            if ready_for_export:
                logger.info(f"Found {len(ready_for_export)} invoices ready for export")
                export_result = self.export_invoices_batch()
                results['export_results'] = export_result
                results['total_exported'] = export_result.get('exported_count', 0)
        
        return results
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """Get statistics about the processing queue"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                status,
                COUNT(*) as count
            FROM invoice_queue
            GROUP BY status
        ''')
        
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT 
                export_status,
                COUNT(*) as count
            FROM invoice_queue
            WHERE status = 'completed'
            GROUP BY export_status
        ''')
        
        export_counts = {row['export_status']: row['count'] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT COUNT(*) as total FROM invoice_queue
        ''')
        total = cursor.fetchone()['total']
        
        conn.close()
        
        return {
            'total': total,
            'by_status': status_counts,
            'by_export_status': export_counts,
            'pending': status_counts.get('pending', 0),
            'completed': status_counts.get('completed', 0),
            'failed': status_counts.get('failed', 0),
            'ready_for_export': export_counts.get('pending', 0),
            'exported': export_counts.get('exported', 0)
        }
    
    def run_continuous(self, interval: int = 300):
        """Run pipeline continuously"""
        logger.info(f"Starting continuous pipeline (checking every {interval} seconds)")
        
        while True:
            try:
                logger.info("Running pipeline cycle...")
                results = self.process_pipeline(fetch_emails=True, auto_export=True)
                
                # Log results
                if results['total_processed'] > 0:
                    logger.info(f"Processed {results['total_processed']} invoices")
                if results['total_exported'] > 0:
                    logger.info(f"Exported {results['total_exported']} invoices")
                
                # Get statistics
                stats = self.get_queue_statistics()
                logger.info(f"Queue stats - Pending: {stats['pending']}, Completed: {stats['completed']}, Failed: {stats['failed']}")
                
                # Wait for next cycle
                logger.info(f"Waiting {interval} seconds for next cycle...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Pipeline stopped by user")
                break
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                time.sleep(60)  # Wait a minute before retrying


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    pipeline = InvoicePipeline()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "fetch":
            # Fetch emails only
            results = pipeline.fetch_emails_to_queue()
            print(json.dumps(results, indent=2))
            
        elif command == "process":
            # Process pending invoices
            results = pipeline.process_pipeline(fetch_emails=False, auto_export=False)
            print(f"Processed {results['total_processed']} invoices")
            
        elif command == "export":
            # Export completed invoices
            results = pipeline.export_invoices_batch()
            print(json.dumps(results, indent=2))
            
        elif command == "stats":
            # Show queue statistics
            stats = pipeline.get_queue_statistics()
            print("\nQueue Statistics:")
            print("-" * 40)
            print(f"Total invoices: {stats['total']}")
            print(f"Pending: {stats['pending']}")
            print(f"Completed: {stats['completed']}")
            print(f"Failed: {stats['failed']}")
            print(f"Ready for export: {stats['ready_for_export']}")
            print(f"Exported: {stats['exported']}")
            
        elif command == "run":
            # Run complete pipeline once
            results = pipeline.process_pipeline()
            print(f"Processed: {results['total_processed']}")
            print(f"Exported: {results['total_exported']}")
            
        elif command == "continuous":
            # Run continuously
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
            pipeline.run_continuous(interval)
            
        else:
            print("Usage: python invoice_pipeline.py [fetch|process|export|stats|run|continuous [interval]]")
    else:
        # Show help
        print("Invoice Processing Pipeline")
        print("-" * 40)
        print("Commands:")
        print("  fetch      - Fetch emails and add to queue")
        print("  process    - Process pending invoices")
        print("  export     - Export completed invoices")
        print("  stats      - Show queue statistics")
        print("  run        - Run complete pipeline once")
        print("  continuous - Run continuously (default 300s interval)")
        print()
        print("Example: python invoice_pipeline.py run")