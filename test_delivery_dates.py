#!/usr/bin/env python3
"""
Test the delivery calendar date calculations for different scenarios
"""
from datetime import datetime
from delivery_calendar import DeliveryCalendar
import json

def test_scenario(scenario_name, calendar_config, test_date=None):
    """Test a specific scenario"""
    print(f"\n{scenario_name}")
    print("=" * 60)
    
    dc = DeliveryCalendar(calendar_config)
    
    # Show configuration
    config = json.loads(calendar_config) if isinstance(calendar_config, str) else calendar_config
    allowed_days = [day for day, allowed in config.items() if allowed]
    print(f"Allowed delivery days: {', '.join(allowed_days)}")
    
    # Test from specific date or today
    if test_date:
        from_date = datetime.strptime(test_date, '%Y-%m-%d')
        print(f"LPO received on: {from_date.strftime('%A, %B %d, %Y')}")
    else:
        from_date = datetime.now()
        print(f"LPO received today: {from_date.strftime('%A, %B %d, %Y')}")
    
    # Calculate dates
    dates = dc.process_invoice_dates(payment_terms_days=45)
    
    print(f"\nCalculated dates:")
    print(f"  Invoice Date: {dates['invoice_date'].strftime('%A, %B %d, %Y')}")
    print(f"  Due Date: {dates['due_date'].strftime('%A, %B %d, %Y')}")
    print(f"  Days until due: {(dates['due_date'] - dates['invoice_date']).days} days")
    
    return dates

# Test scenarios
print("DELIVERY CALENDAR DATE CALCULATION TESTS")
print("=" * 60)

# Scenario 1: Default (weekdays only)
default_calendar = json.dumps({
    "monday": True,
    "tuesday": True,
    "wednesday": True,
    "thursday": True,
    "friday": True,
    "saturday": False,
    "sunday": False
})

test_scenario(
    "Scenario 1: Default Calendar (Weekdays Only)",
    default_calendar
)

# Scenario 2: Monday and Thursday only
limited_calendar = json.dumps({
    "monday": True,
    "tuesday": False,
    "wednesday": False,
    "thursday": True,
    "friday": False,
    "saturday": False,
    "sunday": False
})

test_scenario(
    "Scenario 2: Limited Days (Monday & Thursday Only)",
    limited_calendar
)

# Scenario 3: Weekend delivery only (unusual case)
weekend_calendar = json.dumps({
    "monday": False,
    "tuesday": False,
    "wednesday": False,
    "thursday": False,
    "friday": False,
    "saturday": True,
    "sunday": True
})

test_scenario(
    "Scenario 3: Weekend Only Delivery",
    weekend_calendar
)

# Scenario 4: Test specific date - Saturday
saturday_date = "2025-08-16"  # This is a Saturday
test_scenario(
    "Scenario 4: LPO Received on Saturday (Weekdays Only)",
    default_calendar,
    saturday_date
)

# Scenario 5: Test specific date - Sunday with Monday disabled
no_monday_calendar = json.dumps({
    "monday": False,
    "tuesday": True,
    "wednesday": True,
    "thursday": True,
    "friday": True,
    "saturday": False,
    "sunday": False
})

sunday_date = "2025-08-17"  # This is a Sunday
test_scenario(
    "Scenario 5: LPO on Sunday, Monday Disabled (Should use Tuesday)",
    no_monday_calendar,
    sunday_date
)

print("\n" + "=" * 60)
print("KEY OBSERVATIONS:")
print("- Invoice dates always use the nearest allowed delivery day")
print("- Due dates are calculated as end of month + payment terms")
print("- System ignores the LPO date and uses current date for calculations")
print("- Each customer can have their own delivery calendar settings")