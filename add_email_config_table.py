#!/usr/bin/env python3
"""
Add email configuration table to database
"""
import sqlite3

def add_email_config_table():
    conn = sqlite3.connect('test_customers.db')
    cursor = conn.cursor()
    
    # Create email_config table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_name TEXT UNIQUE NOT NULL,
            email_address TEXT NOT NULL,
            password TEXT,
            server TEXT NOT NULL,
            port INTEGER NOT NULL,
            use_ssl BOOLEAN DEFAULT 1,
            use_tls BOOLEAN DEFAULT 0,
            check_interval INTEGER DEFAULT 300,
            folders TEXT DEFAULT 'INBOX',
            search_subjects TEXT,
            search_senders TEXT,
            unseen_only BOOLEAN DEFAULT 1,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create invoice_queue table for processing pipeline
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL, -- 'email' or 'manual'
            source_id TEXT, -- email message id or upload id
            filename TEXT NOT NULL,
            file_path TEXT,
            customer_email TEXT,
            status TEXT DEFAULT 'pending', -- pending, processing, completed, failed, exported
            parse_result TEXT, -- JSON result from parsing
            export_status TEXT, -- pending, exported, failed
            export_path TEXT,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            exported_at TIMESTAMP
        )
    ''')
    
    # Add default email configuration
    cursor.execute('''
        INSERT OR IGNORE INTO email_config (
            config_name, email_address, password, server, port, use_ssl, 
            check_interval, folders, search_subjects, unseen_only
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'default',
        'orders@atrade.ae',
        '', # Password will be set via UI
        'imap.gmail.com',
        993,
        1,
        300,
        'INBOX',
        'LPO,Purchase Order,PO,Local Purchase Order',
        1
    ))
    
    conn.commit()
    
    # Show the structure
    cursor.execute("PRAGMA table_info(email_config)")
    columns = cursor.fetchall()
    
    print("Email Config Table Structure:")
    print("-" * 60)
    for col in columns:
        print(f"{col[1]:<20} {col[2]:<15}")
    
    cursor.execute("PRAGMA table_info(invoice_queue)")
    columns = cursor.fetchall()
    
    print("\nInvoice Queue Table Structure:")
    print("-" * 60)
    for col in columns:
        print(f"{col[1]:<20} {col[2]:<15}")
    
    conn.close()
    print("\n✓ Email configuration tables created successfully!")

if __name__ == "__main__":
    add_email_config_table()