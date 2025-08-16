#!/usr/bin/env python3
"""Check and fix database structure"""
import sqlite3
import json

conn = sqlite3.connect('test_customers.db')
cursor = conn.cursor()

# Check customer table structure
cursor.execute("PRAGMA table_info(customers)")
columns = cursor.fetchall()
print("Customer table columns:")
for col in columns:
    print(f"  {col[1]}: {col[2]}")

# Check sample data
cursor.execute("SELECT customer_id, customer_name, email, trn, address FROM customers LIMIT 3")
print("\nSample customer data:")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}")
    print(f"  Name: {row[1]}")
    print(f"  Email: {row[2]}")
    print(f"  TRN: {row[3]}")
    print(f"  Address: {row[4]}")
    print("  ---")

# Check if we have pricing table
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customer_pricing'")
if cursor.fetchone():
    cursor.execute("PRAGMA table_info(customer_pricing)")
    columns = cursor.fetchall()
    print("\nCustomer pricing table columns:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")

conn.close()