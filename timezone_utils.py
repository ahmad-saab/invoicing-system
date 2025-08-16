#!/usr/bin/env python3
"""
Timezone utilities for email time conversion
Handles conversion between email server time and local system time
"""
import imaplib
import email
from datetime import datetime, timedelta
import time
import logging
from typing import Optional, Tuple
import re
import sqlite3

logger = logging.getLogger(__name__)

class TimezoneConverter:
    """Handle timezone conversions between email server and local time"""
    
    def __init__(self, db_path: str = "test_customers.db"):
        self.db_path = db_path
        self._cached_offset = None
        self._last_detection = None
        
    def get_system_setting(self, key: str, default_value: str = "") -> str:
        """Get system setting from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT setting_value FROM system_settings WHERE setting_key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else default_value
        except Exception as e:
            logger.error(f"Error getting system setting {key}: {e}")
            return default_value
    
    def set_system_setting(self, key: str, value: str):
        """Set system setting in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO system_settings 
                (setting_key, setting_value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error setting system setting {key}: {e}")
    
    def detect_server_timezone_offset(self, imap_connection) -> int:
        """
        Detect timezone offset between email server and local system
        Returns offset in minutes (server_time - local_time)
        """
        try:
            # Check cache (valid for 1 hour)
            if (self._cached_offset is not None and 
                self._last_detection and 
                (datetime.now() - self._last_detection).seconds < 3600):
                return self._cached_offset
            
            # Get a recent email to compare timestamps
            imap_connection.select('INBOX')
            
            # Search for recent emails
            search_criteria = 'ALL'
            _, message_ids = imap_connection.search(None, search_criteria)
            
            if not message_ids[0]:
                logger.warning("No emails found for timezone detection")
                return 0
            
            # Get the most recent email
            latest_id = message_ids[0].split()[-1]
            _, msg_data = imap_connection.fetch(latest_id, '(RFC822)')
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    email_date_str = msg['Date']
                    
                    if email_date_str:
                        # Parse email date
                        server_time = self.parse_email_date(email_date_str)
                        if server_time:
                            # Get current local time
                            local_time = datetime.now()
                            
                            # Calculate offset (in minutes)
                            # Note: This is a rough estimation based on the assumption
                            # that the email was sent recently
                            time_diff = server_time - local_time
                            offset_minutes = int(time_diff.total_seconds() / 60)
                            
                            # Cache the result
                            self._cached_offset = offset_minutes
                            self._last_detection = datetime.now()
                            
                            # Store in database
                            self.set_system_setting("detected_server_timezone_offset", str(offset_minutes))
                            
                            logger.info(f"Detected server timezone offset: {offset_minutes} minutes")
                            return offset_minutes
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to detect server timezone: {e}")
            return 0
    
    def parse_email_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date string to datetime object"""
        try:
            # Remove day name if present (e.g., "Mon, 01 Jan 2024...")
            date_str = re.sub(r'^[A-Za-z]{3},?\s*', '', date_str.strip())
            
            # Common email date formats
            formats = [
                "%d %b %Y %H:%M:%S %z",      # 01 Jan 2024 12:00:00 +0400
                "%d %b %Y %H:%M:%S",         # 01 Jan 2024 12:00:00
                "%Y-%m-%d %H:%M:%S %z",      # 2024-01-01 12:00:00 +0400
                "%Y-%m-%d %H:%M:%S",         # 2024-01-01 12:00:00
                "%a, %d %b %Y %H:%M:%S %z",  # Mon, 01 Jan 2024 12:00:00 +0400
                "%a, %d %b %Y %H:%M:%S"      # Mon, 01 Jan 2024 12:00:00
            ]
            
            for fmt in formats:
                try:
                    if '%z' in fmt:
                        # Handle timezone-aware parsing
                        dt = datetime.strptime(date_str, fmt)
                        # Convert to local timezone
                        return dt.replace(tzinfo=None)
                    else:
                        # Timezone-naive parsing
                        return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Fallback: try email.utils
            import email.utils
            timestamp = email.utils.parsedate_tz(date_str)
            if timestamp:
                dt = datetime.fromtimestamp(email.utils.mktime_tz(timestamp))
                return dt
                
        except Exception as e:
            logger.debug(f"Failed to parse email date '{date_str}': {e}")
        
        return None
    
    def get_configured_lookback_time(self, config: dict) -> datetime:
        """
        Get the configured lookback time considering timezone settings
        """
        try:
            # Get lookback hours from config or default
            lookback_hours = config.get('check_lookback_hours', 24)
            if lookback_hours is None:
                lookback_hours = int(self.get_system_setting("default_email_lookback_hours", "24"))
            
            # Get timezone handling settings
            auto_detect = config.get('auto_detect_timezone', True)
            force_local = config.get('force_local_time', True)
            manual_offset = config.get('server_timezone_offset', 0) or 0
            
            # Calculate base time (local time minus lookback hours)
            base_time = datetime.now() - timedelta(hours=lookback_hours)
            
            if force_local:
                # Use local time directly
                logger.info(f"Using local time for email search: {base_time} (lookback: {lookback_hours}h)")
                return base_time
            
            # Handle timezone conversion for server time
            if auto_detect:
                # This would require an active IMAP connection
                # For now, use manual offset or stored detected offset
                stored_offset = int(self.get_system_setting("detected_server_timezone_offset", "0"))
                offset_minutes = stored_offset
            else:
                offset_minutes = manual_offset
            
            # Apply timezone offset
            adjusted_time = base_time - timedelta(minutes=offset_minutes)
            
            logger.info(f"Adjusted time for server timezone (offset: {offset_minutes}min): {adjusted_time}")
            return adjusted_time
            
        except Exception as e:
            logger.error(f"Error calculating lookback time: {e}")
            # Fallback to 24 hours ago
            return datetime.now() - timedelta(hours=24)
    
    def convert_local_to_server_time(self, local_time: datetime, config: dict) -> datetime:
        """Convert local time to server time for IMAP search"""
        try:
            force_local = config.get('force_local_time', True)
            if force_local:
                return local_time
            
            auto_detect = config.get('auto_detect_timezone', True)
            
            if auto_detect:
                stored_offset = int(self.get_system_setting("detected_server_timezone_offset", "0"))
                offset_minutes = stored_offset
            else:
                offset_minutes = config.get('server_timezone_offset', 0) or 0
            
            # Convert local time to server time
            server_time = local_time + timedelta(minutes=offset_minutes)
            return server_time
            
        except Exception as e:
            logger.error(f"Error converting time: {e}")
            return local_time
    
    def format_imap_date(self, dt: datetime) -> str:
        """Format datetime for IMAP search"""
        return dt.strftime("%d-%b-%Y")
    
    def update_last_check_time(self, config_name: str):
        """Update the last check time for an email configuration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE email_config 
                SET last_check_time = ?
                WHERE config_name = ?
            ''', (datetime.now(), config_name))
            conn.commit()
            conn.close()
            
            # Also update global last check time
            self.set_system_setting("last_global_email_check", datetime.now().isoformat())
            
        except Exception as e:
            logger.error(f"Error updating last check time: {e}")
    
    def get_last_check_time(self, config_name: str) -> Optional[datetime]:
        """Get the last check time for an email configuration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT last_check_time FROM email_config 
                WHERE config_name = ?
            ''', (config_name,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                # Handle different possible formats
                if isinstance(result[0], str):
                    return datetime.fromisoformat(result[0])
                else:
                    return result[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting last check time: {e}")
            return None


# Test function
if __name__ == "__main__":
    converter = TimezoneConverter()
    
    # Test configuration
    test_config = {
        'check_lookback_hours': 12,
        'auto_detect_timezone': True,
        'force_local_time': True,
        'server_timezone_offset': 0
    }
    
    lookback_time = converter.get_configured_lookback_time(test_config)
    print(f"Configured lookback time: {lookback_time}")
    print(f"IMAP formatted: {converter.format_imap_date(lookback_time)}")