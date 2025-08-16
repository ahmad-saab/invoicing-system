#!/usr/bin/env python3
"""
Create a new, clean database structure based on user requirements
"""
import sqlite3
import os
from datetime import datetime

# Backup existing database
if os.path.exists('test_customers.db'):
    backup_name = f'test_customers_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    os.rename('test_customers.db', backup_name)
    print(f"Backed up existing database to {backup_name}")

# Create new database
conn = sqlite3.connect('test_customers.db')
cursor = conn.cursor()

# Create customers table
# Email is the primary identifier
cursor.execute('''
CREATE TABLE customers (
    email TEXT PRIMARY KEY,
    unique_alias TEXT,  -- For emails that send to multiple branches
    customer_name TEXT NOT NULL,
    customer_id_number TEXT UNIQUE,  -- Internal customer ID
    trn TEXT,  -- Tax Registration Number
    billing_address TEXT,
    shipping_address TEXT,
    payment_terms INTEGER DEFAULT 30,  -- Days after SOA
    currency TEXT DEFAULT 'AED',
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create product mappings table
# Maps customer's LPO product names to system product names with pricing
cursor.execute('''
CREATE TABLE product_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_email TEXT NOT NULL,
    lpo_product_name TEXT NOT NULL,  -- How it appears in customer's LPO
    system_product_name TEXT NOT NULL,  -- Our system's product name
    unit_price REAL NOT NULL,
    unit TEXT DEFAULT 'EACH',  -- EACH, CASE, BOX, etc.
    vat_rate REAL DEFAULT 5.0,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_email) REFERENCES customers (email),
    UNIQUE(customer_email, lpo_product_name)
)
''')

# Create branch identifiers table for customers with multiple branches
cursor.execute('''
CREATE TABLE branch_identifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_email TEXT NOT NULL,
    branch_identifier TEXT NOT NULL,  -- Text in LPO that identifies this branch
    branch_name TEXT NOT NULL,
    delivery_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_email) REFERENCES customers (email)
)
''')

# Create parsing history table for tracking
cursor.execute('''
CREATE TABLE parsing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    customer_email TEXT,
    parse_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    extracted_data TEXT,  -- JSON
    invoice_data TEXT,  -- JSON
    error_message TEXT
)
''')

# Insert sample data
sample_customers = [
    # Email, Alias, Name, ID Number, TRN, Billing Address, Shipping Address
    ('asaab@atrade.ae', None, 'A Trade MENA Trading LLC', 'ATRADE_001', '100123456789000', 
     'Dubai Business Bay', 'Same as billing', 30),
    ('dubaipurch@cipriani.ae', 'CIPRIANI_MAIN', 'Cipriani Dubai', 'CIP_001', '100548028800003',
     'DIFC Gate Village', 'DIFC Gate Village Building 3', 45),
    ('a.krishnan@dubaigolf.com', 'GOLF_EMIRATES', 'Dubai Golf LLC', 'GOLF_001', '100572588000003',
     'Emirates Hills', 'Emirates Golf Club', 60),
    ('purchasing@mythos.ae', 'MYTHOS_CW', 'Mythos Urban Greek Eatery', 'MYTHOS_001', '100548028800003',
     'City Walk', 'The Square City Walk, B08-00-02', 30),
]

for customer in sample_customers:
    cursor.execute('''
        INSERT INTO customers (email, unique_alias, customer_name, customer_id_number, 
                              trn, billing_address, shipping_address, payment_terms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', customer)

print(f"Added {len(sample_customers)} sample customers")

# Insert sample product mappings
sample_mappings = [
    # Customer Email, LPO Product Name, System Product Name, Price, Unit
    ('a.krishnan@dubaigolf.com', 'Oil Cuisine Bunge Pro 10L', 'Bunge ProCuisine F1 10L', 85.00, 'CAN'),
    ('a.krishnan@dubaigolf.com', 'FRYING OIL BUNGE PRO F10', 'Bunge ProCuisine F1 10L', 85.00, 'CAN'),
    ('a.krishnan@dubaigolf.com', 'Sunflower Oil 5L', 'Sunflower Oil 5L', 45.00, 'BOTTLE'),
    
    ('dubaipurch@cipriani.ae', 'SUNFLOWER OIL TIN 05LT', 'Sunflower Oil 5L', 48.00, 'TIN'),
    ('dubaipurch@cipriani.ae', 'OLIVE OIL POMACE', 'Olive Oil Pomace 5L', 120.00, 'TIN'),
    ('dubaipurch@cipriani.ae', 'CANOLA OIL', 'Canola Oil 20L', 95.00, 'CAN'),
    
    ('purchasing@mythos.ae', 'FRYING OIL BUNGE PRO F10 1x10LTR', 'Bunge ProCuisine F1 10L', 85.00, 'CASE'),
    ('purchasing@mythos.ae', 'RAPESEED OIL BUNGE PRO CUISINE 1x10LTR', 'Rapeseed Oil 10L', 80.00, 'CASE'),
]

for mapping in sample_mappings:
    cursor.execute('''
        INSERT INTO product_mappings (customer_email, lpo_product_name, system_product_name, 
                                     unit_price, unit)
        VALUES (?, ?, ?, ?, ?)
    ''', mapping)

print(f"Added {len(sample_mappings)} sample product mappings")

# Insert sample branch identifiers for customers with multiple locations
sample_branches = [
    ('a.krishnan@dubaigolf.com', 'Emirates Golf Club', 'Emirates Golf Club', 'Emirates Hills, Dubai'),
    ('a.krishnan@dubaigolf.com', 'Dubai Creek Golf', 'Dubai Creek Golf & Yacht Club', 'Deira, Dubai'),
    ('dubaipurch@cipriani.ae', 'Cipriani Dolci', 'Cipriani Dolci', 'Dubai Mall'),
    ('dubaipurch@cipriani.ae', 'Cipriani DIFC', 'Cipriani DIFC', 'DIFC Gate Village'),
]

for branch in sample_branches:
    cursor.execute('''
        INSERT INTO branch_identifiers (customer_email, branch_identifier, branch_name, delivery_address)
        VALUES (?, ?, ?, ?)
    ''', branch)

print(f"Added {len(sample_branches)} sample branch identifiers")

# Create indexes for better performance
cursor.execute('CREATE INDEX idx_customer_email ON customers(email)')
cursor.execute('CREATE INDEX idx_product_customer ON product_mappings(customer_email)')
cursor.execute('CREATE INDEX idx_branch_customer ON branch_identifiers(customer_email)')

conn.commit()

# Show summary
print("\n=== Database Structure Created ===")
print("\nTables:")
print("1. customers - Primary customer information (email as key)")
print("2. product_mappings - Maps LPO product names to system names with pricing")
print("3. branch_identifiers - For customers with multiple delivery locations")
print("4. parsing_history - Tracks all parsing attempts")

print("\n=== Sample Data ===")
cursor.execute("SELECT COUNT(*) FROM customers")
print(f"Customers: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM product_mappings")
print(f"Product Mappings: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM branch_identifiers")
print(f"Branch Identifiers: {cursor.fetchone()[0]}")

conn.close()
print("\nDatabase created successfully!")