#!/usr/bin/env python3
"""
Delivery Calendar Utility Module
Handles date calculations based on customer's allowed delivery days
"""
from datetime import datetime, timedelta
import json
import calendar

class DeliveryCalendar:
    """Calculate invoice and due dates based on customer's delivery calendar"""
    
    WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    def __init__(self, delivery_calendar_json=None):
        """
        Initialize with delivery calendar configuration
        
        Args:
            delivery_calendar_json: JSON string with day configurations
                                   e.g., {"monday": true, "tuesday": false, ...}
        """
        if delivery_calendar_json:
            if isinstance(delivery_calendar_json, str):
                self.calendar = json.loads(delivery_calendar_json)
            else:
                self.calendar = delivery_calendar_json
        else:
            # Default: weekdays only
            self.calendar = {
                "monday": True,
                "tuesday": True,
                "wednesday": True,
                "thursday": True,
                "friday": True,
                "saturday": False,
                "sunday": False
            }
    
    def get_nearest_delivery_date(self, from_date=None):
        """
        Get the nearest allowed delivery date from a given date
        
        Args:
            from_date: Starting date (datetime object or string). 
                      If None, uses today.
        
        Returns:
            datetime object of the nearest allowed delivery date
        """
        if from_date is None:
            check_date = datetime.now()
        elif isinstance(from_date, str):
            # Try multiple date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']:
                try:
                    check_date = datetime.strptime(from_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                # If no format matches, use today
                check_date = datetime.now()
        else:
            check_date = from_date
        
        # Check up to 7 days ahead to find an allowed delivery day
        for days_ahead in range(8):  # 0 to 7 days
            test_date = check_date + timedelta(days=days_ahead)
            weekday_name = self.WEEKDAYS[test_date.weekday()]
            
            if self.calendar.get(weekday_name, False):
                return test_date
        
        # Fallback: if no days are allowed (shouldn't happen), return original date
        return check_date
    
    def get_end_of_month_date(self, from_date=None):
        """
        Get the last day of the month for a given date
        
        Args:
            from_date: Reference date. If None, uses today.
        
        Returns:
            datetime object of the last day of the month
        """
        if from_date is None:
            ref_date = datetime.now()
        elif isinstance(from_date, str):
            # Try to parse the date
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']:
                try:
                    ref_date = datetime.strptime(from_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                ref_date = datetime.now()
        else:
            ref_date = from_date
        
        # Get the last day of the month
        last_day = calendar.monthrange(ref_date.year, ref_date.month)[1]
        return datetime(ref_date.year, ref_date.month, last_day)
    
    def calculate_due_date(self, invoice_date, payment_terms_days=30):
        """
        Calculate due date as end of month + payment terms
        
        Args:
            invoice_date: The invoice date (datetime object or string)
            payment_terms_days: Number of days for payment terms (default 30)
        
        Returns:
            datetime object of the due date
        """
        if isinstance(invoice_date, str):
            # Try to parse the date
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']:
                try:
                    inv_date = datetime.strptime(invoice_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                inv_date = datetime.now()
        else:
            inv_date = invoice_date
        
        # Get end of month for the invoice date
        end_of_month = self.get_end_of_month_date(inv_date)
        
        # Add payment terms
        due_date = end_of_month + timedelta(days=payment_terms_days)
        
        return due_date
    
    def process_invoice_dates(self, lpo_date=None, payment_terms_days=30):
        """
        Process both invoice date and due date based on delivery calendar
        
        Args:
            lpo_date: Original LPO date (will be ignored, using delivery calendar)
            payment_terms_days: Payment terms in days
        
        Returns:
            dict with 'invoice_date' and 'due_date' as datetime objects
        """
        # Get nearest allowed delivery date (ignoring LPO date, using today)
        invoice_date = self.get_nearest_delivery_date(from_date=datetime.now())
        
        # Calculate due date as end of month + payment terms
        due_date = self.calculate_due_date(invoice_date, payment_terms_days)
        
        return {
            'invoice_date': invoice_date,
            'due_date': due_date,
            'invoice_date_str': invoice_date.strftime('%Y-%m-%d'),
            'due_date_str': due_date.strftime('%Y-%m-%d')
        }


# Test the module
if __name__ == "__main__":
    # Test with default calendar (weekdays only)
    dc = DeliveryCalendar()
    
    print("Testing Delivery Calendar Module")
    print("-" * 40)
    
    # Test 1: Today is Saturday, should give Monday
    saturday = datetime(2025, 8, 16)  # This is a Saturday
    result = dc.get_nearest_delivery_date(saturday)
    print(f"From Saturday (Aug 16): {result.strftime('%A, %Y-%m-%d')}")
    
    # Test 2: Today is Tuesday, should give same day
    tuesday = datetime(2025, 8, 12)  # This is a Tuesday
    result = dc.get_nearest_delivery_date(tuesday)
    print(f"From Tuesday (Aug 12): {result.strftime('%A, %Y-%m-%d')}")
    
    # Test 3: Calculate full invoice dates
    print("\nFull Invoice Date Calculation:")
    dates = dc.process_invoice_dates(payment_terms_days=45)
    print(f"Invoice Date: {dates['invoice_date_str']}")
    print(f"Due Date: {dates['due_date_str']}")
    
    # Test 4: Custom calendar (only Monday and Thursday)
    custom_cal = DeliveryCalendar('{"monday": true, "tuesday": false, "wednesday": false, "thursday": true, "friday": false, "saturday": false, "sunday": false}')
    print("\nCustom Calendar (Monday & Thursday only):")
    wednesday = datetime(2025, 8, 13)  # Wednesday
    result = custom_cal.get_nearest_delivery_date(wednesday)
    print(f"From Wednesday (Aug 13): {result.strftime('%A, %Y-%m-%d')}")