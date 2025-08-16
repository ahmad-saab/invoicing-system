#!/usr/bin/env python3
"""
Add smart product mappings to handle variations in product names
"""
import sqlite3

def add_product_mappings():
    conn = sqlite3.connect('test_customers.db')
    cursor = conn.cursor()
    
    # Product mappings for common variations
    # These will match using our smart word-based algorithm
    product_mappings = [
        # Bunge ProCuisine variations
        ('Oil Cuisine Bunge Pro 10L', 'product', 'Bunge ProCuisine Oil 10L', 
         'Maps various Bunge ProCuisine oil references'),
        ('FRYING OIL BUNGE PRO F10', 'product', 'Bunge ProCuisine Frying Oil F10 10L',
         'Bunge frying oil F10 product'),
        ('RAPESEED OIL BUNGE PRO CUISINE', 'product', 'Bunge ProCuisine Rapeseed Oil 10L',
         'Bunge rapeseed oil product'),
        ('Bunge Pro Cuisine', 'product', 'Bunge ProCuisine Oil',
         'Generic Bunge ProCuisine reference'),
        
        # Sunflower oil variations
        ('SUNFLOWER OIL TIN', 'product', 'Sunflower Oil',
         'Sunflower oil in tin packaging'),
        ('SUNFLOWER OIL 5L', 'product', 'Sunflower Oil 5 Liters',
         'Sunflower oil 5L size'),
        
        # Canola oil variations
        ('CANOLA OIL', 'product', 'Canola Oil',
         'Standard canola oil product'),
        ('Canola Oil 10L', 'product', 'Canola Oil 10 Liters',
         'Canola oil 10L size'),
        
        # Generic oil products
        ('Vegetable Oil', 'product', 'Vegetable Oil',
         'Generic vegetable oil'),
        ('Cooking Oil', 'product', 'Cooking Oil',
         'Generic cooking oil'),
    ]
    
    # Add mappings for UPSCALE RESTAURANT specifically
    customer_id = 'UPSCALE RESTAURANT L.L.C_55'
    
    for parsed_text, field_type, mapped_value, description in product_mappings:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO customer_field_mappings 
                (customer_id, parsed_text, field_type, mapped_value, description, active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, datetime('now'))
            ''', (customer_id, parsed_text, field_type, mapped_value, description))
            print(f"Added mapping: '{parsed_text}' -> '{mapped_value}'")
        except Exception as e:
            print(f"Error adding mapping: {e}")
    
    # Also add some generic mappings that apply to all customers
    cursor.execute('''
        INSERT OR REPLACE INTO customer_field_mappings 
        (customer_id, parsed_text, field_type, mapped_value, description, active, created_at)
        VALUES 
        ('ALL', 'Bunge', 'product_brand', 'Bunge', 'Bunge brand identifier', 1, datetime('now')),
        ('ALL', 'ProCuisine', 'product_brand', 'ProCuisine', 'ProCuisine product line', 1, datetime('now')),
        ('ALL', 'F10', 'product_code', 'F10', 'Product code F10', 1, datetime('now'))
    ''')
    
    conn.commit()
    
    # Show current mappings
    cursor.execute('''
        SELECT customer_id, parsed_text, field_type, mapped_value 
        FROM customer_field_mappings 
        WHERE field_type LIKE '%product%' 
        ORDER BY customer_id, parsed_text
        LIMIT 20
    ''')
    
    print("\nCurrent product mappings:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: '{row[1]}' ({row[2]}) -> '{row[3]}'")
    
    conn.close()
    print("\nMappings added successfully!")

if __name__ == '__main__':
    add_product_mappings()