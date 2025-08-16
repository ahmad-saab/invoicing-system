-- Database Schema for Invoice System
-- Generated from test_customers.db

CREATE TABLE branch_identifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_email TEXT NOT NULL,
    branch_identifier TEXT NOT NULL,  -- Text in LPO that identifies this branch
    branch_name TEXT NOT NULL,
    delivery_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_email) REFERENCES customers (email)
);

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
, delivery_calendar TEXT DEFAULT '{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": false, "sunday": false}');

CREATE TABLE email_config (
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
        );

CREATE TABLE invoice_queue (
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
        );

CREATE TABLE parsing_failures (
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
        );

CREATE TABLE parsing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    customer_email TEXT,
    parse_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    extracted_data TEXT,  -- JSON
    invoice_data TEXT,  -- JSON
    error_message TEXT
, error_details TEXT, debug_extraction TEXT);

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
);

CREATE TABLE sqlite_sequence(name,seq);