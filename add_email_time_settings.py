#!/usr/bin/env python3
"""
Add configurable email time settings to database
"""
import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_email_time_settings(db_path: str = "test_customers.db"):
    """Add time configuration columns to email_config table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add new columns for time configuration
        new_columns = [
            ("last_check_time", "TIMESTAMP"),  # Last time emails were checked
            ("check_lookback_hours", "INTEGER DEFAULT 24"),  # How many hours back to check
            ("server_timezone_offset", "INTEGER DEFAULT 0"),  # Email server timezone offset from local time (in minutes)
            ("auto_detect_timezone", "BOOLEAN DEFAULT 1"),  # Whether to auto-detect timezone difference
            ("force_local_time", "BOOLEAN DEFAULT 1"),  # Use local time instead of server time
        ]
        
        for column_name, column_definition in new_columns:
            try:
                cursor.execute(f'''
                    ALTER TABLE email_config 
                    ADD COLUMN {column_name} {column_definition}
                ''')
                logger.info(f"Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info(f"Column {column_name} already exists")
                else:
                    raise e
        
        # Update existing records with default values
        cursor.execute('''
            UPDATE email_config 
            SET check_lookback_hours = 24,
                server_timezone_offset = 0,
                auto_detect_timezone = 1,
                force_local_time = 1
            WHERE check_lookback_hours IS NULL
        ''')
        
        # Create system settings table for global email settings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                setting_type TEXT DEFAULT 'string',  -- string, integer, boolean, json
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default system settings
        default_settings = [
            ("default_email_lookback_hours", "24", "integer", "Default hours to look back for emails"),
            ("email_timezone_auto_detect", "true", "boolean", "Auto-detect email server timezone"),
            ("email_force_local_time", "true", "boolean", "Force use of local time for email searches"),
            ("last_global_email_check", "", "timestamp", "Last time any email check was performed"),
        ]
        
        for key, value, setting_type, description in default_settings:
            cursor.execute('''
                INSERT OR REPLACE INTO system_settings 
                (setting_key, setting_value, setting_type, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (key, value, setting_type, description, datetime.now()))
        
        conn.commit()
        logger.info("Successfully added email time configuration settings")
        
        # Show current email configs
        cursor.execute('SELECT config_name, email_address, check_lookback_hours, server_timezone_offset FROM email_config')
        configs = cursor.fetchall()
        
        if configs:
            logger.info("Current email configurations:")
            for config in configs:
                logger.info(f"  - {config[0]} ({config[1]}): {config[2]}h lookback, {config[3]}min offset")
        else:
            logger.info("No email configurations found")
            
    except Exception as e:
        logger.error(f"Error adding email time settings: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    add_email_time_settings()