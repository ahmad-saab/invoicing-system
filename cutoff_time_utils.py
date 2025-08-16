#!/usr/bin/env python3
"""
Daily Cutoff Time Utilities for Email Processing
Handles logic for "last order time" cutoff periods
"""
import sqlite3
from datetime import datetime, time, timedelta, timezone
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

class CutoffTimeManager:
    """Manage daily cutoff time logic for email processing"""
    
    def __init__(self, db_path: str = "test_customers.db"):
        self.db_path = db_path
    
    def parse_time_string(self, time_str: str) -> time:
        """Parse time string in HH:MM format to time object"""
        try:
            # Handle different formats
            if ':' in time_str:
                parts = time_str.split(':')
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            else:
                # Assume just hour
                hour = int(time_str)
                minute = 0
            
            # Handle 24-hour format
            if hour > 23:
                hour = 23
            if minute > 59:
                minute = 59
                
            return time(hour, minute)
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid time format '{time_str}': {e}")
            return time(17, 0)  # Default to 5:00 PM
    
    def get_last_cutoff_time(self, config: Dict[str, Any]) -> datetime:
        """
        Calculate the last cutoff time based on configuration
        
        Logic:
        1. If today is before cutoff time -> use yesterday's cutoff
        2. If today is after cutoff time -> use today's cutoff  
        3. Skip weekends if configured
        """
        try:
            # Parse cutoff time
            cutoff_time_str = config.get('daily_cutoff_time', '17:00')
            cutoff_time = self.parse_time_string(cutoff_time_str)
            
            # Get current time
            now = datetime.now()
            current_time = now.time()
            
            # Calculate today's cutoff datetime
            today_cutoff = datetime.combine(now.date(), cutoff_time)
            
            # Determine which cutoff to use
            if current_time >= cutoff_time:
                # It's after cutoff time today, so last cutoff was today
                last_cutoff = today_cutoff
                logger.info(f"Using today's cutoff: {last_cutoff} (current time {now.time()} is after cutoff {cutoff_time})")
            else:
                # It's before cutoff time today, so last cutoff was yesterday
                yesterday = now.date() - timedelta(days=1)
                last_cutoff = datetime.combine(yesterday, cutoff_time)
                logger.info(f"Using yesterday's cutoff: {last_cutoff} (current time {now.time()} is before cutoff {cutoff_time})")
            
            # Handle weekend skipping
            skip_weekends = config.get('skip_weekends', True)
            if skip_weekends:
                last_cutoff = self.adjust_for_weekends(last_cutoff, cutoff_time, direction='backward')
            
            return last_cutoff
            
        except Exception as e:
            logger.error(f"Error calculating last cutoff time: {e}")
            # Fallback to 24 hours ago
            return datetime.now() - timedelta(hours=24)
    
    def get_next_cutoff_time(self, config: Dict[str, Any]) -> datetime:
        """
        Calculate the next cutoff time
        Used to determine the search window end time
        """
        try:
            # Parse cutoff time
            cutoff_time_str = config.get('daily_cutoff_time', '17:00')
            cutoff_time = self.parse_time_string(cutoff_time_str)
            
            # Get current time
            now = datetime.now()
            current_time = now.time()
            
            # Calculate next cutoff
            if current_time < cutoff_time:
                # Next cutoff is today
                next_cutoff = datetime.combine(now.date(), cutoff_time)
                logger.info(f"Next cutoff is today: {next_cutoff}")
            else:
                # Next cutoff is tomorrow
                tomorrow = now.date() + timedelta(days=1)
                next_cutoff = datetime.combine(tomorrow, cutoff_time)
                logger.info(f"Next cutoff is tomorrow: {next_cutoff}")
            
            # Handle weekend skipping
            skip_weekends = config.get('skip_weekends', True)
            if skip_weekends:
                next_cutoff = self.adjust_for_weekends(next_cutoff, cutoff_time, direction='forward')
            
            return next_cutoff
            
        except Exception as e:
            logger.error(f"Error calculating next cutoff time: {e}")
            # Fallback to now
            return datetime.now()
    
    def adjust_for_weekends(self, dt: datetime, cutoff_time: time, direction: str = 'backward') -> datetime:
        """
        Adjust datetime to skip weekends
        direction: 'backward' = find previous weekday, 'forward' = find next weekday
        """
        # Monday=0, Sunday=6
        while dt.weekday() >= 5:  # Saturday=5, Sunday=6
            if direction == 'backward':
                dt = dt - timedelta(days=1)
                # Ensure we keep the cutoff time
                dt = datetime.combine(dt.date(), cutoff_time)
            else:  # forward
                dt = dt + timedelta(days=1)
                dt = datetime.combine(dt.date(), cutoff_time)
            
            logger.info(f"Adjusted for weekend: {dt} (weekday: {dt.weekday()})")
        
        return dt
    
    def get_email_search_window(self, config: Dict[str, Any]) -> Tuple[datetime, datetime]:
        """
        Get the email search window based on cutoff times
        
        Returns: (start_time, end_time) tuple
        - start_time: Last cutoff time processed OR last stored cutoff check
        - end_time: Current/next cutoff time
        """
        try:
            # Get last cutoff check from database
            last_stored_check = self.get_last_cutoff_check(config.get('config_name', 'default'))
            
            # Calculate last and next cutoff times
            last_cutoff = self.get_last_cutoff_time(config)
            next_cutoff = self.get_next_cutoff_time(config)
            
            # Determine start time
            if last_stored_check:
                # Use the later of: last stored check OR calculated last cutoff
                start_time = max(last_stored_check, last_cutoff)
                logger.info(f"Using max of stored check ({last_stored_check}) and calculated cutoff ({last_cutoff}): {start_time}")
            else:
                # No previous check, use calculated last cutoff
                start_time = last_cutoff
                logger.info(f"No previous check found, using calculated last cutoff: {start_time}")
            
            # End time is always current time (don't wait for next cutoff)
            end_time = datetime.now()
            
            logger.info(f"Email search window: {start_time} to {end_time}")
            return start_time, end_time
            
        except Exception as e:
            logger.error(f"Error calculating search window: {e}")
            # Fallback to last 24 hours
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            return start_time, end_time
    
    def get_last_cutoff_check(self, config_name: str) -> Optional[datetime]:
        """Get the last cutoff check time from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT last_cutoff_check FROM email_config 
                WHERE config_name = ?
            ''', (config_name,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                if isinstance(result[0], str):
                    return datetime.fromisoformat(result[0])
                else:
                    return result[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting last cutoff check: {e}")
            return None
    
    def update_last_cutoff_check(self, config_name: str, cutoff_time: Optional[datetime] = None):
        """Update the last cutoff check time"""
        try:
            if cutoff_time is None:
                cutoff_time = datetime.now()
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE email_config 
                SET last_cutoff_check = ?
                WHERE config_name = ?
            ''', (cutoff_time, config_name))
            conn.commit()
            conn.close()
            
            logger.info(f"Updated last cutoff check for {config_name}: {cutoff_time}")
            
        except Exception as e:
            logger.error(f"Error updating last cutoff check: {e}")
    
    def format_imap_date(self, dt: datetime) -> str:
        """Format datetime for IMAP search"""
        return dt.strftime("%d-%b-%Y")
    
    def is_within_business_hours(self, dt: datetime, config: Dict[str, Any]) -> bool:
        """Check if a datetime is within business hours"""
        try:
            cutoff_time_str = config.get('daily_cutoff_time', '17:00')
            cutoff_time = self.parse_time_string(cutoff_time_str)
            
            # Check if it's a weekend and we skip weekends
            skip_weekends = config.get('skip_weekends', True)
            if skip_weekends and dt.weekday() >= 5:
                return False
            
            # Check if time is before cutoff
            return dt.time() <= cutoff_time
            
        except Exception as e:
            logger.error(f"Error checking business hours: {e}")
            return True  # Default to allowing

# Test function
if __name__ == "__main__":
    manager = CutoffTimeManager()
    
    # Test configuration
    test_config = {
        'config_name': 'default',
        'daily_cutoff_time': '17:00',
        'skip_weekends': True,
        'cutoff_timezone': 'local'
    }
    
    print("=== Cutoff Time Analysis ===")
    print(f"Current time: {datetime.now()}")
    
    last_cutoff = manager.get_last_cutoff_time(test_config)
    next_cutoff = manager.get_next_cutoff_time(test_config)
    
    print(f"Last cutoff: {last_cutoff}")
    print(f"Next cutoff: {next_cutoff}")
    
    start_time, end_time = manager.get_email_search_window(test_config)
    print(f"Search window: {start_time} to {end_time}")
    
    print(f"IMAP format - Start: {manager.format_imap_date(start_time)}")
    print(f"IMAP format - End: {manager.format_imap_date(end_time)}")