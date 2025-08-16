#!/usr/bin/env python3
"""
Fix dashboard database issues - add missing columns
"""
import sqlite3

def fix_database():
    conn = sqlite3.connect('test_customers.db')
    cursor = conn.cursor()
    
    # Add created_at column to parsing_history if not exists
    try:
        cursor.execute('''
            ALTER TABLE parsing_history 
            ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ''')
        print("Added created_at column to parsing_history")
        conn.commit()
        
        # Update any existing records
        cursor.execute('''
            UPDATE parsing_history 
            SET created_at = CURRENT_TIMESTAMP 
            WHERE created_at IS NULL
        ''')
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"Column may already exist or other error: {e}")
    
    conn.commit()
    
    # Show the current structure
    cursor.execute("PRAGMA table_info(parsing_history)")
    columns = cursor.fetchall()
    
    print("\nParsing History Table Structure:")
    print("-" * 50)
    for col in columns:
        print(f"{col[1]:<20} {col[2]:<15} {'NOT NULL' if col[3] else 'NULL':<10} {f'DEFAULT {col[4]}' if col[4] else ''}")
    
    conn.close()
    print("\n✓ Database fixed successfully!")
    
if __name__ == "__main__":
    fix_database()