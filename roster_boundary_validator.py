"""
Roster Boundary Validation
Validates that roster line changes comply with Award requirements
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from roster_lines import RosterLine


class RosterBoundaryValidator:
    """Validates roster boundaries when staff change lines between roster periods"""
    
    MIN_DAYS_OFF_PER_WEEK = 2
    MIN_DAYS_OFF_PER_FORTNIGHT = 4
    
    @staticmethod
    def validate_line_transition(
        line_1: RosterLine,
        line_2: RosterLine,
        transition_date: datetime,
        lookback_days: int = 4,
        lookahead_days: int = 4
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates that transitioning from line_1 to line_2 complies with Award
        
        Args:
            line_1: Current roster line
            line_2: New roster line
            transition_date: Date when the roster period changes
            lookback_days: Days to check before transition
            lookahead_days: Days to check after transition
            
        Returns:
            (is_valid, violation_message)
        """
        # Get schedules around the boundary
        period_1_start = transition_date - timedelta(days=lookback_days)
        period_1_schedule = line_1.get_schedule(period_1_start, lookback_days)
        
        period_2_schedule = line_2.get_schedule(transition_date, lookahead_days)
        
        # Combine for boundary analysis
        boundary_schedule = period_1_schedule + period_2_schedule
        
        # Extract just the shift types
        shifts = [shift for date, shift in boundary_schedule]
        
        # Check every 7-day rolling window
        total_days = len(shifts)
        for start_idx in range(max(0, total_days - 6)):
            if start_idx + 7 > total_days:
                break
                
            week_window = shifts[start_idx:start_idx + 7]
            days_off = sum(1 for shift in week_window if shift == 'O')
            
            if days_off < RosterBoundaryValidator.MIN_DAYS_OFF_PER_WEEK:
                # Calculate which dates this violation spans
                violation_start = boundary_schedule[start_idx][0]
                violation_end = boundary_schedule[start_idx + 6][0]
                
                return False, (
                    f"Award violation: Week spanning {violation_start.strftime('%d/%m')} to "
                    f"{violation_end.strftime('%d/%m')} has only {days_off} days off "
                    f"(minimum {RosterBoundaryValidator.MIN_DAYS_OFF_PER_WEEK} required)"
                )
        
        # Check 14-day window if we have enough data
        if total_days >= 14:
            fortnight_window = shifts[:14]
            days_off = sum(1 for shift in fortnight_window if shift == 'O')
            
            if days_off < RosterBoundaryValidator.MIN_DAYS_OFF_PER_FORTNIGHT:
                fortnight_start = boundary_schedule[0][0]
                fortnight_end = boundary_schedule[13][0]
                
                return False, (
                    f"Award violation: Fortnight spanning {fortnight_start.strftime('%d/%m')} to "
                    f"{fortnight_end.strftime('%d/%m')} has only {days_off} days off "
                    f"(minimum {RosterBoundaryValidator.MIN_DAYS_OFF_PER_FORTNIGHT} required)"
                )
        
        return True, None
    
    @staticmethod
    def find_valid_line_transitions(
        current_line: RosterLine,
        all_lines: List[RosterLine],
        transition_date: datetime
    ) -> List[Tuple[RosterLine, bool, Optional[str]]]:
        """
        Check all possible line transitions from current line
        
        Returns:
            List of (line, is_valid, violation_message) tuples
        """
        results = []
        
        for new_line in all_lines:
            is_valid, message = RosterBoundaryValidator.validate_line_transition(
                current_line, new_line, transition_date
            )
            results.append((new_line, is_valid, message))
        
        return results
    
    @staticmethod
    def get_max_consecutive_working_days(shifts: List[str]) -> int:
        """
        Calculate maximum consecutive working days in a shift sequence
        
        Args:
            shifts: List of shift types ('D', 'N', 'O')
            
        Returns:
            Maximum number of consecutive working days
        """
        max_consecutive = 0
        current_consecutive = 0
        
        for shift in shifts:
            if shift in ['D', 'N']:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive


def demo():
    """Demonstrate roster boundary validation"""
    from roster_lines import RosterLineManager
    
    roster_start = datetime(2026, 2, 21)  # Start of a new roster period
    
    manager = RosterLineManager(roster_start)
    validator = RosterBoundaryValidator()
    
    print("=" * 80)
    print("ROSTER BOUNDARY VALIDATION DEMO")
    print("=" * 80)
    print(f"\nRoster transition date: {roster_start.strftime('%d %B %Y')}")
    
    # Example 1: Valid transition
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Valid Line Transition")
    print("=" * 80)
    
    line_3 = manager.lines[2]  # Line 3
    line_5 = manager.lines[4]  # Line 5
    
    # Show the schedules
    print(f"\nCurrent Line: {line_3}")
    prev_period_start = roster_start - timedelta(days=4)
    prev_schedule = line_3.get_schedule(prev_period_start, 4)
    print("Last 4 days of previous period:")
    for date, shift in prev_schedule:
        print(f"  {date.strftime('%a %d/%m')}: {shift}")
    
    print(f"\nNew Line: {line_5}")
    next_schedule = line_5.get_schedule(roster_start, 4)
    print("First 4 days of new period:")
    for date, shift in next_schedule:
        print(f"  {date.strftime('%a %d/%m')}: {shift}")
    
    is_valid, message = validator.validate_line_transition(line_3, line_5, roster_start)
    
    if is_valid:
        print("\n✅ VALID TRANSITION")
    else:
        print(f"\n❌ INVALID TRANSITION")
        print(f"Reason: {message}")
    
    # Example 2: Invalid transition (too many consecutive days)
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Invalid Line Transition (Consecutive Days Violation)")
    print("=" * 80)
    
    line_1 = manager.lines[0]  # Line 1
    line_2 = manager.lines[1]  # Line 2
    
    print(f"\nCurrent Line: {line_1}")
    prev_schedule = line_1.get_schedule(prev_period_start, 4)
    print("Last 4 days of previous period:")
    for date, shift in prev_schedule:
        print(f"  {date.strftime('%a %d/%m')}: {shift}")
    
    print(f"\nNew Line: {line_2}")
    next_schedule = line_2.get_schedule(roster_start, 4)
    print("First 4 days of new period:")
    for date, shift in next_schedule:
        print(f"  {date.strftime('%a %d/%m')}: {shift}")
    
    is_valid, message = validator.validate_line_transition(line_1, line_2, roster_start)
    
    if is_valid:
        print("\n✅ VALID TRANSITION")
    else:
        print(f"\n❌ INVALID TRANSITION")
        print(f"Reason: {message}")
    
    # Example 3: Check all possible transitions from Line 1
    print("\n" + "=" * 80)
    print("EXAMPLE 3: All Valid Transitions from Line 1")
    print("=" * 80)
    
    results = validator.find_valid_line_transitions(line_1, manager.lines, roster_start)
    
    valid_transitions = []
    invalid_transitions = []
    
    for line, is_valid, message in results:
        if is_valid:
            valid_transitions.append(line)
        else:
            invalid_transitions.append((line, message))
    
    print(f"\n✅ Valid transitions from {line_1} ({len(valid_transitions)} options):")
    for line in valid_transitions:
        print(f"  → {line}")
    
    print(f"\n❌ Invalid transitions from {line_1} ({len(invalid_transitions)} violations):")
    for line, message in invalid_transitions:
        print(f"  → {line}: {message}")


if __name__ == "__main__":
    demo()
