#!/usr/bin/env python3
"""
Test multi-location customer functionality
"""
import sqlite3
from simple_parser import SimpleParserUnstructured

def test_multi_location():
    """Test parsing with multi-location customer"""
    
    # Sample LPO text that includes branch identifier
    sample_lpo_text_dubai_mall = """
    PURCHASE ORDER
    
    To: A Trade MENA Trading LLC
    From: Fine Dining Restaurant
    Delivery To: Dubai Mall, Service Corridor S3
    
    Order No: DM-2025-001
    Date: 13/08/2025
    
    Items:
    SUNFLOWER OIL 5L TIN - Quantity: 20
    CORN OIL 1L BOTTLE - Quantity: 15
    """
    
    sample_lpo_text_moe = """
    PURCHASE ORDER
    
    To: A Trade MENA Trading LLC
    From: Fine Dining Restaurant
    Delivery To: Mall of Emirates, Loading Bay 10
    
    Order No: MOE-2025-002
    Date: 13/08/2025
    
    Items:
    SUNFLOWER OIL 5L TIN - Quantity: 30
    OLIVE OIL 1L BOTTLE - Quantity: 10
    """
    
    # Initialize parser
    parser = SimpleParserUnstructured()
    
    print("=" * 80)
    print("TESTING MULTI-LOCATION CUSTOMER DETECTION")
    print("=" * 80)
    
    # Test 1: Check Dubai Golf (existing multi-location customer)
    print("\n1. Testing Dubai Golf (existing multi-location customer)")
    print("-" * 40)
    
    email = "a.krishnan@dubaigolf.com"
    
    # Simulate LPO with Emirates Golf Club
    lpo_text_emirates = "Order from Emirates Golf Club for delivery"
    customer = parser._get_customer_by_email(email, lpo_text_emirates)
    if customer:
        print(f"✓ Detected: {customer['customer_name']}")
        print(f"  Shipping: {customer['shipping_address']}")
    
    # Simulate LPO with Dubai Creek
    lpo_text_creek = "Order from Dubai Creek Golf & Yacht Club"
    customer = parser._get_customer_by_email(email, lpo_text_creek)
    if customer:
        print(f"✓ Detected: {customer['customer_name']}")
        print(f"  Shipping: {customer['shipping_address']}")
    
    # Test 2: Check Cipriani (another multi-location customer)
    print("\n2. Testing Cipriani (multi-location customer)")
    print("-" * 40)
    
    email = "dubaipurch@cipriani.ae"
    
    # Check if multiple locations exist
    conn = sqlite3.connect('test_customers.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE email = ?", (email,))
    customers = cursor.fetchall()
    
    print(f"Found {len(customers)} location(s) for {email}")
    
    cursor.execute("SELECT * FROM branch_identifiers WHERE customer_email = ?", (email,))
    branches = cursor.fetchall()
    print(f"Branch identifiers:")
    for branch in branches:
        print(f"  - {branch[2]}: '{branch[3]}'")  # branch_identifier: branch_name
    
    conn.close()
    
    # Test 3: Check how the system selects the right location
    print("\n3. Testing branch selection logic")
    print("-" * 40)
    
    # Test with text containing "Dolci"
    lpo_text = "Delivery to Cipriani Dolci at Dubai Mall"
    customer = parser._get_customer_by_email(email, lpo_text)
    if customer:
        print(f"LPO mentions 'Dolci' → Selected: {customer['customer_name']}")
        print(f"  Shipping: {customer.get('shipping_address', 'N/A')}")
    
    # Test with no specific branch mentioned
    lpo_text = "Order from Cipriani"
    customer = parser._get_customer_by_email(email, lpo_text)
    if customer:
        print(f"No specific branch → Default: {customer['customer_name']}")
        print(f"  Shipping: {customer.get('shipping_address', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("KEY FEATURES:")
    print("- System detects branch from LPO content")
    print("- Each branch can have different shipping addresses")
    print("- Each branch can have different delivery calendars")
    print("- Falls back to default if branch not identified")
    print("=" * 80)

if __name__ == "__main__":
    test_multi_location()