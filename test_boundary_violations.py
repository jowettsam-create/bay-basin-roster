"""
Test problematic roster boundary scenarios
"""

from datetime import datetime, timedelta
from roster_boundary_validator import RosterBoundaryValidator


def test_problematic_transitions():
    """Test scenarios that could violate Award requirements"""
    
    print("=" * 80)
    print("TESTING PROBLEMATIC ROSTER BOUNDARIES")
    print("=" * 80)
    
    # Scenario: Someone working extra shifts at end of period
    print("\nScenario: Staff member works overtime at end of Period 1")
    print("This simulates working 6 days straight across roster boundary")
    
    # Simulate end of Period 1: DD (normal) + DD (overtime)
    # Then start of Period 2: DD (normal start of their new line)
    
    transition_date = datetime(2026, 2, 21)
    
    # Manually create a problematic schedule
    period_1_end = [
        (datetime(2026, 2, 17), 'D'),  # Mon - Day
        (datetime(2026, 2, 18), 'D'),  # Tue - Day
        (datetime(2026, 2, 19), 'D'),  # Wed - Day (overtime)
        (datetime(2026, 2, 20), 'D'),  # Thu - Day (overtime)
    ]
    
    period_2_start = [
        (datetime(2026, 2, 21), 'D'),  # Fri - Day
        (datetime(2026, 2, 22), 'D'),  # Sat - Day
        (datetime(2026, 2, 23), 'N'),  # Sun - Night
        (datetime(2026, 2, 24), 'N'),  # Mon - Night
    ]
    
    combined = period_1_end + period_2_start
    
    print("\nCombined schedule across boundary:")
    for date, shift in combined:
        print(f"  {date.strftime('%a %d/%m')}: {shift}")
    
    # Check 7-day windows
    print("\nChecking Award compliance:")
    
    shifts = [shift for date, shift in combined]
    
    # Check if any 7-day window violates minimum days off
    total_days = len(shifts)
    violation_found = False
    
    for start_idx in range(max(0, total_days - 6)):
        if start_idx + 7 > total_days:
            break
            
        week_window = shifts[start_idx:start_idx + 7]
        days_off = sum(1 for shift in week_window if shift == 'O')
        
        if days_off < 2:
            violation_start = combined[start_idx][0]
            violation_end = combined[start_idx + 6][0]
            print(f"\n❌ AWARD VIOLATION DETECTED!")
            print(f"   Week: {violation_start.strftime('%a %d/%m')} to {violation_end.strftime('%a %d/%m')}")
            print(f"   Days off: {days_off} (minimum 2 required)")
            print(f"   Shifts: {week_window}")
            
            # Count consecutive working days
            consecutive = 0
            max_consecutive = 0
            for shift in shifts:
                if shift in ['D', 'N']:
                    consecutive += 1
                    max_consecutive = max(max_consecutive, consecutive)
                else:
                    consecutive = 0
            
            print(f"   Maximum consecutive working days: {max_consecutive}")
            violation_found = True
    
    if not violation_found:
        print("\n✅ No violations detected in this 8-day window")
        print("   (Award allows this as long as full week requirements met)")


def test_realistic_overtime_scenario():
    """Test what happens with realistic overtime patterns"""
    
    print("\n" + "=" * 80)
    print("REALISTIC OVERTIME SCENARIO")
    print("=" * 80)
    
    print("\nStaff member on Line 1 (DDNNOOOOO)")
    print("Works their normal roster, then picks up one extra day shift")
    
    # Normal Line 1 end
    normal_schedule = [
        (datetime(2026, 2, 15), 'O'),  # Sat - Off
        (datetime(2026, 2, 16), 'O'),  # Sun - Off  
        (datetime(2026, 2, 17), 'D'),  # Mon - Day
        (datetime(2026, 2, 18), 'D'),  # Tue - Day
        (datetime(2026, 2, 19), 'N'),  # Wed - Night
        (datetime(2026, 2, 20), 'N'),  # Thu - Night
        # Now should be off, but picks up overtime
        (datetime(2026, 2, 21), 'D'),  # Fri - Day (OVERTIME)
    ]
    
    print("\nSchedule with overtime:")
    for date, shift in normal_schedule:
        ot_marker = " (OVERTIME)" if date.day == 21 else ""
        print(f"  {date.strftime('%a %d/%m')}: {shift}{ot_marker}")
    
    # Check consecutive days
    shifts = [shift for date, shift in normal_schedule]
    consecutive = RosterBoundaryValidator.get_max_consecutive_working_days(shifts)
    
    print(f"\nMaximum consecutive working days: {consecutive}")
    
    if consecutive > 6:
        print("⚠️  Warning: Working more than 6 consecutive days may violate fatigue management")
    
    # Check days off in the week
    days_off = sum(1 for shift in shifts if shift == 'O')
    print(f"Days off in this 7-day period: {days_off}")
    
    if days_off < 2:
        print("❌ AWARD VIOLATION: Less than 2 days off per week")
    else:
        print("✅ Minimum days off requirement met")


if __name__ == "__main__":
    test_problematic_transitions()
    test_realistic_overtime_scenario()
