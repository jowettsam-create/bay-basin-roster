"""
Fixed Roster Staff Helper Functions
Utilities for creating and managing staff with fixed schedules
"""

from datetime import datetime, timedelta
from typing import Dict, List
from roster_assignment import StaffMember


def create_fixed_roster_staff(
    name: str,
    role: str,
    schedule_pattern: str,
    roster_start: datetime,
    roster_end: datetime,
    year: str = ""
) -> StaffMember:
    """
    Create a staff member with a fixed roster pattern
    
    Args:
        name: Staff member name
        role: Role (e.g., "Casual", "PT/FTR")
        year: Year level
        schedule_pattern: Pattern like "DDDOOOО" or specific days
        roster_start: Start of roster period
        roster_end: End of roster period
    
    Returns:
        StaffMember with fixed schedule
    """
    # Generate the fixed schedule
    fixed_schedule = {}
    
    # If pattern is provided, repeat it across the roster period
    if schedule_pattern:
        pattern_list = list(schedule_pattern)
        pattern_length = len(pattern_list)
        
        current_date = roster_start
        day_count = 0
        
        while current_date <= roster_end:
            shift_type = pattern_list[day_count % pattern_length]
            fixed_schedule[current_date] = shift_type
            current_date += timedelta(days=1)
            day_count += 1
    
    return StaffMember(
        name=name,
        role=role,
        year=year,
        is_fixed_roster=True,
        fixed_schedule=fixed_schedule
    )


def create_fixed_roster_from_days(
    name: str,
    role: str,
    working_days: List[str],  # e.g., ["Monday", "Tuesday", "Wednesday"]
    shift_type: str,  # 'D' or 'N'
    roster_start: datetime,
    roster_end: datetime,
    year: str = ""
) -> StaffMember:
    """
    Create fixed roster staff who work specific days of the week
    
    Args:
        name: Staff member name
        role: Role
        year: Year level
        working_days: List of day names they work (e.g., ["Monday", "Friday"])
        shift_type: 'D' for day shifts, 'N' for night shifts
        roster_start: Start of roster period
        roster_end: End of roster period
    
    Returns:
        StaffMember with fixed schedule
    """
    # Map day names to numbers
    day_mapping = {
        'Monday': 0,
        'Tuesday': 1,
        'Wednesday': 2,
        'Thursday': 3,
        'Friday': 4,
        'Saturday': 5,
        'Sunday': 6
    }
    
    working_day_numbers = [day_mapping[day] for day in working_days if day in day_mapping]
    
    # Generate schedule
    fixed_schedule = {}
    current_date = roster_start
    
    while current_date <= roster_end:
        if current_date.weekday() in working_day_numbers:
            fixed_schedule[current_date] = shift_type
        else:
            fixed_schedule[current_date] = 'O'
        
        current_date += timedelta(days=1)
    
    return StaffMember(
        name=name,
        role=role,
        year=year,
        is_fixed_roster=True,
        fixed_schedule=fixed_schedule
    )


def create_fixed_roster_from_dates(
    name: str,
    role: str,
    working_dates: Dict[datetime, str],  # {date: shift_type}
    roster_start: datetime,
    roster_end: datetime,
    year: str = ""
) -> StaffMember:
    """
    Create fixed roster staff with specific dates and shift types
    
    Args:
        name: Staff member name
        role: Role
        year: Year level
        working_dates: Dictionary mapping dates to shift types
        roster_start: Start of roster period
        roster_end: End of roster period
    
    Returns:
        StaffMember with fixed schedule
    """
    # Fill in any missing dates with 'O' (off)
    fixed_schedule = {}
    current_date = roster_start
    
    while current_date <= roster_end:
        fixed_schedule[current_date] = working_dates.get(current_date, 'O')
        current_date += timedelta(days=1)
    
    return StaffMember(
        name=name,
        role=role,
        year=year,
        is_fixed_roster=True,
        fixed_schedule=fixed_schedule
    )


def display_fixed_schedule(staff: StaffMember, num_days: int = 28):
    """Display a fixed roster staff member's schedule"""
    if not staff.is_fixed_roster:
        print(f"{staff.name} is not on a fixed roster")
        return
    
    print(f"\n{staff.name} ({staff.year}) - Fixed Schedule")
    print("=" * 60)
    
    # Get the first date in schedule
    dates = sorted(staff.fixed_schedule.keys())
    if not dates:
        print("No schedule defined")
        return
    
    start_date = dates[0]
    
    # Display schedule
    current_week = []
    for i in range(min(num_days, len(dates))):
        date = start_date + timedelta(days=i)
        shift = staff.fixed_schedule.get(date, 'O')
        
        day_str = date.strftime("%a %d/%m")
        shift_display = {
            'D': '☀️ DAY  ',
            'N': '🌙 NIGHT',
            'O': '   OFF '
        }.get(shift, '   ---  ')
        
        current_week.append(f"{day_str}: {shift_display}")
        
        # Print week rows
        if len(current_week) == 7:
            print(" | ".join(current_week))
            current_week = []
    
    # Print remaining days
    if current_week:
        print(" | ".join(current_week))
    
    print("=" * 60)


def demo():
    """Demonstrate creating fixed roster staff"""
    
    roster_start = datetime(2026, 2, 21)
    roster_end = datetime(2026, 3, 20)
    
    print("=" * 80)
    print("FIXED ROSTER STAFF EXAMPLES")
    print("=" * 80)
    
    # Example 1: Casual who works Mon/Wed/Fri days
    print("\nExample 1: Part-time casual - Mon/Wed/Fri day shifts")
    casual1 = create_fixed_roster_from_days(
        name="Megan Bryant",
        role="PT/FTR",
        year="Para Yr5",
        working_days=["Monday", "Wednesday", "Friday"],
        shift_type='D',
        roster_start=roster_start,
        roster_end=roster_end
    )
    display_fixed_schedule(casual1, 14)
    
    # Example 2: Casual with repeating pattern
    print("\nExample 2: Casual with pattern DDDDOOO (4 on, 3 off)")
    casual2 = create_fixed_roster_staff(
        name="John Smith",
        role="Casual",
        year="Para Yr4",
        schedule_pattern="DDDDOOO",
        roster_start=roster_start,
        roster_end=roster_end
    )
    display_fixed_schedule(casual2, 14)
    
    # Example 3: Weekend warrior (Sat/Sun only)
    print("\nExample 3: Weekend-only casual")
    casual3 = create_fixed_roster_from_days(
        name="Sarah Johnson",
        role="Casual",
        year="Para Yr3",
        working_days=["Saturday", "Sunday"],
        shift_type='D',
        roster_start=roster_start,
        roster_end=roster_end
    )
    display_fixed_schedule(casual3, 14)
    
    # Example 4: Night shift only on specific days
    print("\nExample 4: Night shift specialist - Tue/Thu/Sat")
    casual4 = create_fixed_roster_from_days(
        name="Mike Chen",
        role="Casual",
        year="Para Yr6",
        working_days=["Tuesday", "Thursday", "Saturday"],
        shift_type='N',
        roster_start=roster_start,
        roster_end=roster_end
    )
    display_fixed_schedule(casual4, 14)
    
    # Example 5: Specific dates (e.g., filling known gaps)
    print("\nExample 5: Casual filling specific dates")
    specific_dates = {
        datetime(2026, 2, 24): 'D',
        datetime(2026, 2, 25): 'D',
        datetime(2026, 2, 28): 'N',
        datetime(2026, 3, 1): 'N',
        datetime(2026, 3, 7): 'D',
        datetime(2026, 3, 14): 'D',
    }
    casual5 = create_fixed_roster_from_dates(
        name="Emma Wilson",
        role="Casual",
        year="Para Yr5",
        working_dates=specific_dates,
        roster_start=roster_start,
        roster_end=roster_end
    )
    display_fixed_schedule(casual5, 28)


if __name__ == "__main__":
    demo()
