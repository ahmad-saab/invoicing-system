#!/usr/bin/env python3
"""
Export Manager for Zoho Books
Converts parsed invoice data to Zoho-compatible CSV format
"""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from delivery_calendar import DeliveryCalendar

class ZohoExportManager:
    """Export parsed invoices to Zoho Books CSV format"""
    
    # Zoho Books required fields
    REQUIRED_FIELDS = [
        'Invoice Number',
        'Invoice Date', 
        'Customer Name',
        'Item Name',
        'Item Quantity',
        'Item Rate'
    ]
    
    # Complete Zoho Books field mapping
    FIELD_MAPPING = {
        # Invoice Header Fields
        'Invoice Number': 'invoice_number',
        'Invoice Date': 'invoice_date',
        'Due Date': 'due_date',
        'Customer Name': 'customer_name',
        'Customer ID': 'customer_id',
        'TRN': 'trn',
        'Order Number': 'order_number',
        'Terms': 'payment_terms',
        'Salesperson': 'salesperson',
        
        # Address Fields
        'Billing Address': 'billing_address',
        'Billing City': 'billing_city',
        'Billing State': 'billing_state',
        'Billing Country': 'billing_country',
        'Billing Zip': 'billing_zip',
        'Shipping Address': 'shipping_address',
        'Shipping City': 'shipping_city',
        'Shipping State': 'shipping_state',
        'Shipping Country': 'shipping_country',
        'Shipping Zip': 'shipping_zip',
        
        # Item Fields
        'Item Name': 'item_name',
        'Item Description': 'item_description',
        'Item Quantity': 'quantity',
        'Item Rate': 'unit_price',
        'Item Unit': 'unit',
        'Item Tax': 'vat_rate',
        'Item Total': 'item_total',
        
        # Summary Fields
        'SubTotal': 'subtotal',
        'Tax Amount': 'tax_amount',
        'Total': 'total',
        'Currency Code': 'currency',
        'Notes': 'notes'
    }
    
    def __init__(self, export_dir: str = "exports"):
        """Initialize export manager"""
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
        
    def generate_invoice_number(self, prefix: str = "") -> str:
        """Leave invoice number empty for Zoho to auto-generate"""
        return ""  # Zoho will auto-generate the invoice number
    
    def calculate_due_date(self, invoice_date: datetime, payment_terms: int = 30) -> str:
        """Calculate due date as end of month + payment terms"""
        # Use DeliveryCalendar to calculate proper due date
        dc = DeliveryCalendar()
        due_date = dc.calculate_due_date(invoice_date, payment_terms)
        return due_date.strftime("%Y-%m-%d")
    
    def export_to_zoho_csv(self, invoice_data: Dict[str, Any], filename: str = None) -> str:
        """
        Export invoice data to Zoho Books CSV format
        
        Args:
            invoice_data: Parsed invoice data from the system
            filename: Optional custom filename
            
        Returns:
            Path to exported CSV file
        """
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"zoho_invoice_{timestamp}.csv"
        
        filepath = self.export_dir / filename
        
        # Extract data from invoice
        customer = invoice_data.get('customer', {})
        items = invoice_data.get('items', [])
        totals = invoice_data.get('totals', {})
        
        # Leave invoice number empty for Zoho to generate
        invoice_number = ""  # Zoho will auto-generate
        
        # Get or generate dates using delivery calendar
        delivery_calendar_json = customer.get('delivery_calendar')
        dc = DeliveryCalendar(delivery_calendar_json)
        
        # Get nearest allowed delivery date (ignoring LPO date)
        dates = dc.process_invoice_dates(payment_terms_days=customer.get('payment_terms', 30))
        invoice_date = dates['invoice_date_str']
        due_date = dates['due_date_str']
        
        # Prepare rows for CSV
        rows = []
        
        # Create a row for each item
        for item in items:
            row = {
                # Invoice Header (same for all items)
                'Invoice Number': invoice_number,
                'Invoice Date': invoice_date,
                'Due Date': due_date,
                'Customer Name': customer.get('customer_name', ''),
                'Customer ID': customer.get('customer_id_number', ''),
                'TRN': customer.get('trn', ''),
                'Order Number': invoice_data.get('po_number', ''),
                'Terms': f"Net {customer.get('payment_terms', 30)}",
                
                # Billing Address
                'Billing Address': customer.get('billing_address', ''),
                
                # Shipping Address
                'Shipping Address': customer.get('shipping_address', ''),
                
                # Item Details
                'Item Name': item.get('system_product_name', item.get('lpo_product_name', '')),
                'Item Description': item.get('description', ''),
                'Item Quantity': item.get('quantity', 0),
                'Item Rate': item.get('unit_price', 0),
                'Item Unit': item.get('unit', 'EACH'),
                'Item Tax': item.get('vat_rate', 5),
                'Item Total': item.get('total', 0),
                
                # Currency
                'Currency Code': customer.get('currency', 'AED'),
                
                # Notes
                'Notes': f"PO: {invoice_data.get('po_number', '')} | Email: {customer.get('email', '')}"
            }
            rows.append(row)
        
        # Write to CSV
        if rows:
            fieldnames = list(rows[0].keys())
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        
        return str(filepath)
    
    def export_batch(self, invoices: List[Dict[str, Any]], batch_name: str = None) -> str:
        """
        Export multiple invoices in a single CSV file
        
        Args:
            invoices: List of parsed invoice data
            batch_name: Optional batch name for the file
            
        Returns:
            Path to exported CSV file
        """
        if not batch_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_name = f"zoho_batch_{timestamp}.csv"
        
        filepath = self.export_dir / batch_name
        
        all_rows = []
        
        for invoice_data in invoices:
            customer = invoice_data.get('customer', {})
            items = invoice_data.get('items', [])
            
            invoice_number = ""  # Leave empty for Zoho to generate
            
            # Use delivery calendar for dates
            delivery_calendar_json = customer.get('delivery_calendar')
            dc = DeliveryCalendar(delivery_calendar_json)
            dates = dc.process_invoice_dates(payment_terms_days=customer.get('payment_terms', 30))
            invoice_date = dates['invoice_date_str']
            due_date = dates['due_date_str']
            
            for item in items:
                row = {
                    'Invoice Number': invoice_number,
                    'Invoice Date': invoice_date,
                    'Due Date': due_date,
                    'Customer Name': customer.get('customer_name', ''),
                    'Customer ID': customer.get('customer_id_number', ''),
                    'TRN': customer.get('trn', ''),
                    'Order Number': invoice_data.get('po_number', ''),
                    'Terms': f"Net {customer.get('payment_terms', 30)}",
                    'Billing Address': customer.get('billing_address', ''),
                    'Shipping Address': customer.get('shipping_address', ''),
                    'Item Name': item.get('system_product_name', item.get('lpo_product_name', '')),
                    'Item Quantity': item.get('quantity', 0),
                    'Item Rate': item.get('unit_price', 0),
                    'Item Unit': item.get('unit', 'EACH'),
                    'Item Tax': item.get('vat_rate', 5),
                    'Currency Code': customer.get('currency', 'AED')
                }
                all_rows.append(row)
        
        # Write all rows to CSV
        if all_rows:
            fieldnames = list(all_rows[0].keys())
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)
        
        return str(filepath)
    
    def validate_export(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate invoice data before export
        
        Returns:
            Validation result with missing fields
        """
        validation = {
            'valid': True,
            'missing_required': [],
            'warnings': []
        }
        
        customer = invoice_data.get('customer', {})
        items = invoice_data.get('items', [])
        
        # Check customer name
        if not customer.get('customer_name'):
            validation['missing_required'].append('Customer Name')
            validation['valid'] = False
        
        # Check items
        if not items:
            validation['missing_required'].append('Items')
            validation['valid'] = False
        else:
            for i, item in enumerate(items):
                if not item.get('system_product_name') and not item.get('lpo_product_name'):
                    validation['warnings'].append(f'Item {i+1}: Missing product name')
                if not item.get('quantity'):
                    validation['warnings'].append(f'Item {i+1}: Missing quantity')
                if not item.get('unit_price'):
                    validation['warnings'].append(f'Item {i+1}: Missing price')
        
        return validation
    
    def get_export_summary(self, filepath: str) -> Dict[str, Any]:
        """Get summary of exported file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                # Get unique invoices
                invoices = {}
                for row in rows:
                    inv_num = row.get('Invoice Number', '')
                    if inv_num not in invoices:
                        invoices[inv_num] = {
                            'customer': row.get('Customer Name', ''),
                            'date': row.get('Invoice Date', ''),
                            'items': 0,
                            'total': 0
                        }
                    invoices[inv_num]['items'] += 1
                
                return {
                    'file': filepath,
                    'total_rows': len(rows),
                    'invoices': len(invoices),
                    'invoice_details': invoices
                }
        except Exception as e:
            return {'error': str(e)}


if __name__ == "__main__":
    # Test export manager
    manager = ZohoExportManager()
    
    # Sample invoice data (Note: invoice_number left empty for Zoho to generate)
    test_invoice = {
        'po_number': 'PO-2025-001',
        'customer': {
            'customer_name': 'Test Company LLC',
            'customer_id_number': 'CUST001',
            'email': 'test@company.com',
            'trn': '100000000000003',
            'billing_address': '123 Business St, Dubai',
            'shipping_address': '456 Warehouse Rd, Dubai',
            'payment_terms': 30,
            'currency': 'AED'
        },
        'items': [
            {
                'lpo_product_name': 'SUNFLOWER OIL TIN 5L',
                'system_product_name': 'Sunflower Oil 5L Tin',
                'quantity': 10,
                'unit': 'TIN',
                'unit_price': 85.00,
                'vat_rate': 5,
                'total': 850.00
            },
            {
                'lpo_product_name': 'CORN OIL BOTTLE 1L',
                'system_product_name': 'Corn Oil 1L Bottle',
                'quantity': 20,
                'unit': 'BOTTLE',
                'unit_price': 25.00,
                'vat_rate': 5,
                'total': 500.00
            }
        ],
        'totals': {
            'subtotal': 1350.00,
            'vat_amount': 67.50,
            'total': 1417.50
        }
    }
    
    # Validate
    validation = manager.validate_export(test_invoice)
    print("Validation Result:", json.dumps(validation, indent=2))
    
    # Export
    if validation['valid']:
        filepath = manager.export_to_zoho_csv(test_invoice)
        print(f"\nExported to: {filepath}")
        
        # Get summary
        summary = manager.get_export_summary(filepath)
        print("\nExport Summary:", json.dumps(summary, indent=2))