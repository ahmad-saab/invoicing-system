#!/usr/bin/env python3
"""
Show structure of both databases
"""
import sqlite3
import os

def show_database_structure(db_path):
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    if not tables:
        print(f"No tables in {db_path}")
        return
    
    for table in tables:
        table_name = table[0]
        print(f"\n📋 Table: {table_name}")
        print("-" * 60)
        
        # Get columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"{'Column Name':<25} {'Type':<15} {'Null':<8} {'Default':<15}")
        print("-" * 60)
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            col_null = "NULL" if not col[3] else "NOT NULL"
            col_default = col[4] if col[4] else ""
            print(f"{col_name:<25} {col_type:<15} {col_null:<8} {col_default:<15}")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\nRows in table: {count}")
    
    conn.close()

print("=" * 70)
print("DATABASE STRUCTURE COMPARISON")
print("=" * 70)

print("\n🔴 OLD DATABASE: invoice_parser.db")
print("=" * 70)
show_database_structure("invoice_parser.db")

print("\n\n🟢 CURRENT DATABASE: test_customers.db")
print("=" * 70)
show_database_structure("test_customers.db")

print("\n" + "=" * 70)
print("SUMMARY:")
print("- invoice_parser.db is EMPTY (not used)")
print("- test_customers.db is the ACTIVE database with all data")
print("=" * 70)