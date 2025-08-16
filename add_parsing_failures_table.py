#!/usr/bin/env python3
"""
Add parsing failures tracking table to the database
"""
import sqlite3
from datetime import datetime

def add_parsing_failures_table():
    conn = sqlite3.connect('test_customers.db')
    cursor = conn.cursor()
    
    # Create parsing_failures table for detailed error tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parsing_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            customer_email TEXT,
            error_type TEXT NOT NULL,
            error_message TEXT,
            debug_info TEXT,
            extracted_text TEXT,
            unmapped_products TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved BOOLEAN DEFAULT 0,
            resolved_at TIMESTAMP,
            resolution_notes TEXT,
            FOREIGN KEY (customer_email) REFERENCES customers(email)
        )
    ''')
    
    # Create index for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_parsing_failures_email 
        ON parsing_failures(customer_email)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_parsing_failures_resolved 
        ON parsing_failures(resolved)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_parsing_failures_created 
        ON parsing_failures(created_at)
    ''')
    
    # Add error_details column to parsing_history if not exists
    try:
        cursor.execute('''
            ALTER TABLE parsing_history 
            ADD COLUMN error_details TEXT
        ''')
        print("Added error_details column to parsing_history")
    except sqlite3.OperationalError:
        print("error_details column already exists in parsing_history")
    
    # Add debug_extraction column to parsing_history if not exists
    try:
        cursor.execute('''
            ALTER TABLE parsing_history 
            ADD COLUMN debug_extraction TEXT
        ''')
        print("Added debug_extraction column to parsing_history")
    except sqlite3.OperationalError:
        print("debug_extraction column already exists in parsing_history")
    
    conn.commit()
    
    # Show the new table structure
    cursor.execute("PRAGMA table_info(parsing_failures)")
    columns = cursor.fetchall()
    
    print("\nParsing Failures Table Structure:")
    print("-" * 50)
    for col in columns:
        print(f"{col[1]:<20} {col[2]:<15} {'NOT NULL' if col[3] else 'NULL':<10} {f'DEFAULT {col[4]}' if col[4] else ''}")
    
    conn.close()
    print("\n✓ Parsing failures table created successfully!")
    
if __name__ == "__main__":
    add_parsing_failures_table()