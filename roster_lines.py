"""
Paramedic Roster Line Calculator
9-day rotating roster: DDNNOOOO (2 days, 2 nights, 5 off)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple

class RosterLine:
    """Represents a single roster line in the 9-day rotation"""
    
    # Shift pattern: D=Day, N=Night, O=Off
    PATTERN = ['D', 'D', 'N', 'N', 'O', 'O', 'O', 'O', 'O']
    CYCLE_LENGTH = 9
    
    # Award constraints (Operational Ambulance Managers Award)
    MIN_DAYS_OFF_PER_WEEK = 2
    MIN_DAYS_OFF_PER_FORTNIGHT = 4
    MIN_BREAK_BETWEEN_SHIFTS_HOURS = 10
    AVG_HOURS_PER_WEEK = 38
    
    # Shift timing assumptions (can be configured per station)
    DAY_SHIFT_START = "06:45"
    DAY_SHIFT_END = "19:00"
    NIGHT_SHIFT_START = "18:45"
    NIGHT_SHIFT_END = "07:00"
    
    def __init__(self, line_number: int, start_date: datetime):
        """
        Initialize a roster line
        
        Args:
            line_number: Line number (1-9)
            start_date: The reference start date for Line 1
        """
        self.line_number = line_number
        self.start_date = start_date
        # Offset BACKWARDS by 2*(line_number - 1) days for pairing
        # Line 1 starts at DDNNOOOOO which is position 0 in the pattern
        # Each subsequent line is offset backwards by 2 days
        line_offset = ((line_number - 1) * 2)
        self.offset = (0 - line_offset) % self.CYCLE_LENGTH
    
    def get_shift_type(self, date: datetime) -> str:
        """
        Get the shift type for a given date
        
        Returns: 'D' (Day), 'N' (Night), or 'O' (Off)
        """
        days_since_start = (date - self.start_date).days
        # Apply the line offset
        adjusted_days = (days_since_start + self.offset) % self.CYCLE_LENGTH
        return self.PATTERN[adjusted_days]
    
    def get_schedule(self, start_date: datetime, num_days: int) -> List[Tuple[datetime, str]]:
        """
        Get the schedule for this line over a date range
        
        Returns: List of (date, shift_type) tuples
        """
        schedule = []
        for i in range(num_days):
            current_date = start_date + timedelta(days=i)
            shift_type = self.get_shift_type(current_date)
            schedule.append((current_date, shift_type))
        return schedule
    
    def has_days_off(self, requested_dates: List[datetime]) -> bool:
        """
        Check if all requested dates fall on OFF days for this line
        
        Args:
            requested_dates: List of dates that need to be off
            
        Returns: True if all dates are OFF days
        """
        for date in requested_dates:
            if self.get_shift_type(date) != 'O':
                return False
        return True
    
    def count_working_days(self, requested_dates: List[datetime]) -> int:
        """
        Count how many of the requested dates are working days
        
        Returns: Number of requested dates that are NOT off days
        """
        return sum(1 for date in requested_dates if self.get_shift_type(date) != 'O')
    
    def get_consecutive_working_days(self, start_date: datetime, num_days: int) -> int:
        """
        Find the maximum number of consecutive working days in a given period
        
        Returns: Maximum consecutive working days
        """
        schedule = self.get_schedule(start_date, num_days)
        max_consecutive = 0
        current_consecutive = 0
        
        for date, shift in schedule:
            if shift in ['D', 'N']:  # Working day
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:  # Off day
                current_consecutive = 0
        
        return max_consecutive
    
    def validate_award_compliance(self, start_date: datetime, num_days: int = 28) -> List[str]:
        """
        Check if this roster line complies with Award requirements
        
        Returns: List of violation messages (empty if compliant)
        """
        violations = []
        schedule = self.get_schedule(start_date, num_days)
        
        # Check 7-day rolling windows for minimum 2 days off per week
        for i in range(len(schedule) - 6):
            week_window = schedule[i:i+7]
            days_off = sum(1 for date, shift in week_window if shift == 'O')
            
            if days_off < self.MIN_DAYS_OFF_PER_WEEK:
                week_start = week_window[0][0].strftime('%d/%m')
                week_end = week_window[-1][0].strftime('%d/%m')
                violations.append(
                    f"Week {week_start}-{week_end}: Only {days_off} days off (minimum 2 required)"
                )
        
        # Check 14-day rolling windows for minimum 4 days off per fortnight
        for i in range(len(schedule) - 13):
            fortnight_window = schedule[i:i+14]
            days_off = sum(1 for date, shift in fortnight_window if shift == 'O')
            
            if days_off < self.MIN_DAYS_OFF_PER_FORTNIGHT:
                fortnight_start = fortnight_window[0][0].strftime('%d/%m')
                fortnight_end = fortnight_window[-1][0].strftime('%d/%m')
                violations.append(
                    f"Fortnight {fortnight_start}-{fortnight_end}: Only {days_off} days off (minimum 4 required)"
                )
        
        return violations
    
    def __repr__(self):
        return f"Line {self.line_number}"


class RosterLineManager:
    """Manages all 9 roster lines and helps with line selection"""
    
    def __init__(self, roster_start_date: datetime):
        """
        Initialize all 9 roster lines
        
        Args:
            roster_start_date: The start date of the roster period
        """
        self.roster_start_date = roster_start_date
        self.lines = [RosterLine(i, roster_start_date) for i in range(1, 10)]
    
    def find_matching_lines(self, requested_dates: List[datetime]) -> List[RosterLine]:
        """
        Find all lines where the requested dates fall on OFF days
        
        Args:
            requested_dates: List of dates that need to be off
            
        Returns: List of RosterLine objects that match
        """
        matching_lines = []
        for line in self.lines:
            if line.has_days_off(requested_dates):
                matching_lines.append(line)
        return matching_lines
    
    def rank_lines_by_fit(self, requested_dates: List[datetime]) -> List[Tuple[RosterLine, int]]:
        """
        Rank all lines by how well they fit the requested dates
        
        Returns: List of (RosterLine, working_days_count) tuples, sorted by best fit
        """
        line_scores = []
        for line in self.lines:
            working_days = line.count_working_days(requested_dates)
            line_scores.append((line, working_days))
        
        # Sort by working days (fewer working days = better fit)
        line_scores.sort(key=lambda x: x[1])
        return line_scores
    
    def display_line_schedule(self, line: RosterLine, start_date: datetime, num_days: int = 28):
        """
        Display a line's schedule in a readable format
        """
        schedule = line.get_schedule(start_date, num_days)
        
        print(f"\n{line} Schedule:")
        print("=" * 60)
        
        current_week = []
        for date, shift in schedule:
            day_str = date.strftime("%a %d/%m")
            shift_display = {
                'D': '☀️ DAY  ',
                'N': '🌙 NIGHT',
                'O': '   OFF '
            }[shift]
            
            current_week.append(f"{day_str}: {shift_display}")
            
            # Print week rows (7 days per row)
            if len(current_week) == 7:
                print(" | ".join(current_week))
                current_week = []
        
        # Print remaining days
        if current_week:
            print(" | ".join(current_week))
        
        print("=" * 60)


def demo():
    """Demonstration of the roster line system"""
    
    # Example: Roster starts on Jan 24, 2026 (from your PDF)
    roster_start = datetime(2026, 1, 24)
    
    manager = RosterLineManager(roster_start)
    
    print("=" * 80)
    print("PARAMEDIC ROSTER LINE CALCULATOR")
    print("=" * 80)
    
    # Show what each line looks like for the first 2 weeks
    print("\n📋 First 18 days of each roster line:")
    print("-" * 80)
    
    for line in manager.lines:
        schedule = line.get_schedule(roster_start, 18)
        line_display = f"Line {line.line_number}: "
        for date, shift in schedule:
            line_display += f"{shift} "
        print(line_display)
    
    # Example 1: Staff member wants specific dates off
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Finding lines for specific days off")
    print("=" * 80)
    
    requested_off_dates = [
        datetime(2026, 1, 27),  # Mon
        datetime(2026, 1, 28),  # Tue
        datetime(2026, 2, 3),   # Tue
        datetime(2026, 2, 4),   # Wed
    ]
    
    print("\n🗓️  Staff member needs these dates OFF:")
    for date in requested_off_dates:
        print(f"  - {date.strftime('%A, %B %d, %Y')}")
    
    matching_lines = manager.find_matching_lines(requested_off_dates)
    
    print(f"\n✅ Lines where ALL requested dates are OFF: {len(matching_lines)}")
    for line in matching_lines:
        print(f"  - {line}")
    
    # Show ranking of all lines
    print("\n📊 All lines ranked by fit (0 = perfect fit):")
    ranked_lines = manager.rank_lines_by_fit(requested_off_dates)
    for line, working_days in ranked_lines:
        fit_status = "✅ PERFECT FIT" if working_days == 0 else f"❌ {working_days} conflict(s)"
        print(f"  {line}: {fit_status}")
    
    # Example 2: Show a specific line's schedule
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Viewing a specific line's schedule")
    print("=" * 80)
    
    manager.display_line_schedule(manager.lines[0], roster_start, 28)
    
    # Example 3: Different date request
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Another staff member's request")
    print("=" * 80)
    
    requested_off_dates_2 = [
        datetime(2026, 2, 6),   # Fri
        datetime(2026, 2, 7),   # Sat
        datetime(2026, 2, 8),   # Sun
    ]
    
    print("\n🗓️  Staff member needs these dates OFF:")
    for date in requested_off_dates_2:
        print(f"  - {date.strftime('%A, %B %d, %Y')}")
    
    matching_lines_2 = manager.find_matching_lines(requested_off_dates_2)
    
    print(f"\n✅ Lines where ALL requested dates are OFF: {len(matching_lines_2)}")
    for line in matching_lines_2:
        print(f"  - {line}")
        manager.display_line_schedule(line, roster_start, 21)


if __name__ == "__main__":
    demo()
