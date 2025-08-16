#!/usr/bin/env python3
"""
Add daily cutoff time configuration to database
"""
import sqlite3
import logging
from datetime import datetime, time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_cutoff_time_settings(db_path: str = "test_customers.db"):
    """Add daily cutoff time configuration to email_config table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add new columns for daily cutoff time
        new_columns = [
            ("daily_cutoff_time", "TEXT DEFAULT '17:00'"),  # Daily order cutoff time (HH:MM format)
            ("last_cutoff_check", "TIMESTAMP"),  # Last cutoff time processed
            ("skip_weekends", "BOOLEAN DEFAULT 1"),  # Skip Saturday/Sunday
            ("cutoff_timezone", "TEXT DEFAULT 'local'"),  # Timezone for cutoff time
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
            SET daily_cutoff_time = '17:00',
                skip_weekends = 1,
                cutoff_timezone = 'local'
            WHERE daily_cutoff_time IS NULL
        ''')
        
        # Add cutoff time system settings
        cutoff_settings = [
            ("default_daily_cutoff_time", "17:00", "time", "Default daily order cutoff time (HH:MM)"),
            ("cutoff_skip_weekends", "true", "boolean", "Skip weekends for cutoff calculations"),
            ("cutoff_timezone_mode", "local", "string", "Timezone mode for cutoff time (local/server)"),
            ("last_global_cutoff_check", "", "timestamp", "Last time cutoff check was performed globally"),
        ]
        
        for key, value, setting_type, description in cutoff_settings:
            cursor.execute('''
                INSERT OR REPLACE INTO system_settings 
                (setting_key, setting_value, setting_type, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (key, value, setting_type, description, datetime.now()))
        
        conn.commit()
        logger.info("Successfully added daily cutoff time configuration settings")
        
        # Show current email configs with cutoff times
        cursor.execute('''
            SELECT config_name, email_address, daily_cutoff_time, skip_weekends, last_cutoff_check 
            FROM email_config
        ''')
        configs = cursor.fetchall()
        
        if configs:
            logger.info("Current email configurations with cutoff times:")
            for config in configs:
                last_check = config[4] if config[4] else "Never"
                logger.info(f"  - {config[0]} ({config[1]}): Cutoff {config[2]}, Skip weekends: {bool(config[3])}, Last check: {last_check}")
        else:
            logger.info("No email configurations found")
            
    except Exception as e:
        logger.error(f"Error adding cutoff time settings: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    add_cutoff_time_settings()