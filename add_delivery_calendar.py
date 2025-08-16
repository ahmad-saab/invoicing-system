#!/usr/bin/env python3
"""
Add delivery_calendar column to customers table for specifying allowed delivery days
"""
import sqlite3

def add_delivery_calendar():
    conn = sqlite3.connect('test_customers.db')
    cursor = conn.cursor()
    
    try:
        # Add delivery_calendar column to customers table
        # Format: JSON string with days like {"monday": true, "tuesday": false, ...}
        cursor.execute('''
            ALTER TABLE customers 
            ADD COLUMN delivery_calendar TEXT DEFAULT '{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": false, "sunday": false}'
        ''')
        print("Added delivery_calendar column to customers table")
        
        # Update existing customers with default calendar (weekdays only)
        default_calendar = '{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": false, "sunday": false}'
        cursor.execute('''
            UPDATE customers 
            SET delivery_calendar = ?
            WHERE delivery_calendar IS NULL
        ''', (default_calendar,))
        
        conn.commit()
        print("Updated existing customers with default delivery calendar (weekdays only)")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("delivery_calendar column already exists")
        else:
            raise e
    finally:
        conn.close()

if __name__ == "__main__":
    add_delivery_calendar()
    print("Database update completed!")