
================================================================================
SQL TEMPLATES FOR IMPORTING CUSTOMER DATA
================================================================================

-- 1. CUSTOMERS TABLE (Main customer information)
--------------------------------------------------------------------------------
INSERT INTO customers (
    email, 
    unique_alias, 
    customer_name, 
    customer_id_number, 
    trn, 
    billing_address, 
    shipping_address, 
    payment_terms, 
    currency,
    delivery_calendar,
    active
) VALUES (
    'customer@example.com',           -- Email (PRIMARY KEY - unique identifier)
    NULL,                             -- Unique alias (optional, for multiple branches)
    'Company Name Ltd',               -- Customer name
    'CUST-001',                      -- Customer ID number
    '100000000000000',               -- TRN (Tax Registration Number)
    '123 Business St, Dubai, UAE',   -- Billing address
    '456 Warehouse Rd, Dubai, UAE',  -- Shipping address  
    45,                              -- Payment terms in days
    'AED',                           -- Currency (AED/USD/EUR/GBP)
    '{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": false, "sunday": false}',  -- Delivery calendar
    1                                -- Active status (1=active, 0=inactive)
);

-- 2. PRODUCT_MAPPINGS TABLE (Map LPO product names to system names)
--------------------------------------------------------------------------------
INSERT INTO product_mappings (
    customer_email,
    lpo_product_name,
    system_product_name,
    unit_price,
    unit,
    vat_rate,
    active
) VALUES (
    'customer@example.com',           -- Customer email (links to customers table)
    'SUNFLOWER OIL 5L TIN',          -- Product name as it appears in LPO
    'Bunge Sunflower Oil 5L',        -- Your system's product name
    85.00,                           -- Unit price
    'TIN',                           -- Unit (EACH/TIN/CASE/BOX/PKT/CAN)
    5.0,                             -- VAT rate percentage
    1                                -- Active status
);

-- 3. BRANCH_IDENTIFIERS TABLE (For customers with multiple branches)
--------------------------------------------------------------------------------
INSERT INTO branch_identifiers (
    customer_email,
    branch_identifier,
    branch_name,
    delivery_address
) VALUES (
    'customer@example.com',           -- Customer email
    'DIFC',                          -- Text that identifies branch in LPO
    'DIFC Branch',                   -- Branch name
    'Gate Village 3, DIFC, Dubai'    -- Branch-specific delivery address
);

-- 4. BULK IMPORT EXAMPLES
--------------------------------------------------------------------------------

-- Import multiple customers at once:
INSERT INTO customers (email, customer_name, customer_id_number, trn, billing_address, shipping_address, payment_terms, currency, delivery_calendar) VALUES
('customer1@company.com', 'Company One', 'C001', '100000000000001', 'Address 1', 'Delivery 1', 30, 'AED', '{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": false, "sunday": false}'),
('customer2@company.com', 'Company Two', 'C002', '100000000000002', 'Address 2', 'Delivery 2', 45, 'AED', '{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": false, "sunday": false}'),
('customer3@company.com', 'Company Three', 'C003', '100000000000003', 'Address 3', 'Delivery 3', 60, 'USD', '{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": false, "sunday": false}');

-- Import multiple product mappings for a customer:
INSERT INTO product_mappings (customer_email, lpo_product_name, system_product_name, unit_price, unit, vat_rate) VALUES
('customer@example.com', 'CORN OIL 5LTR', 'Mazola Corn Oil 5L', 75.00, 'TIN', 5.0),
('customer@example.com', 'OLIVE OIL 1L', 'Bertolli Olive Oil 1L', 45.00, 'BOTTLE', 5.0),
('customer@example.com', 'VEGETABLE OIL 20L', 'Generic Vegetable Oil 20L', 180.00, 'CAN', 5.0);

-- 5. UPDATE EXISTING DATA
--------------------------------------------------------------------------------

-- Update customer information:
UPDATE customers 
SET 
    customer_name = 'Updated Company Name',
    billing_address = 'New Address',
    payment_terms = 60,
    delivery_calendar = '{"monday": true, "tuesday": false, "wednesday": true, "thursday": true, "friday": true, "saturday": true, "sunday": false}'
WHERE email = 'customer@example.com';

-- Update product mapping:
UPDATE product_mappings 
SET 
    system_product_name = 'New Product Name',
    unit_price = 90.00
WHERE customer_email = 'customer@example.com' 
  AND lpo_product_name = 'SUNFLOWER OIL 5L TIN';

-- 6. DELIVERY CALENDAR OPTIONS
--------------------------------------------------------------------------------

-- Weekdays only (default):
'{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": false, "sunday": false}'

-- Monday, Wednesday, Friday only:
'{"monday": true, "tuesday": false, "wednesday": true, "thursday": false, "friday": true, "saturday": false, "sunday": false}'

-- All days:
'{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": true, "sunday": true}'

-- Weekend only:
'{"monday": false, "tuesday": false, "wednesday": false, "thursday": false, "friday": false, "saturday": true, "sunday": true}'

================================================================================
NOTES:
- Email is the PRIMARY KEY for customers (must be unique)
- All dates are handled automatically by the system
- delivery_calendar determines invoice date calculation
- payment_terms is in days (30, 45, 60, etc.)
- Active fields: 1 = active, 0 = inactive/deleted
================================================================================
