"""
Paramedic Roster Assignment System
Assigns staff to roster lines and checks coverage requirements
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from roster_lines import RosterLine, RosterLineManager


@dataclass
class StaffMember:
    """Represents a staff member"""
    name: str
    role: str  # e.g., "Paramedic", "Intern", "PT/FTR", "Casual"
    year: str = ""  # Optional - e.g., "Para Yr6"
    
    # Request types
    requested_line: Optional[int] = None  # Direct line request (1-9)
    requested_dates_off: List[datetime] = None  # Specific dates needed off
    
    # Assignment
    assigned_line: Optional[int] = None
    
    # Fixed roster (for casuals, part-timers)
    is_fixed_roster: bool = False  # True if staff can't change lines
    fixed_schedule: Dict[datetime, str] = None  # Specific dates -> shift types (D/N/O)
    
    # Leave/Unavailability
    leave_periods: List[Tuple[datetime, datetime, str]] = None  # (start, end, type)
    
    def __post_init__(self):
        if self.requested_dates_off is None:
            self.requested_dates_off = []
        if self.leave_periods is None:
            self.leave_periods = []
        if self.fixed_schedule is None:
            self.fixed_schedule = {}
    
    def is_on_leave(self, date: datetime) -> bool:
        """Check if staff member is on leave for a given date"""
        for start, end, leave_type in self.leave_periods:
            if start <= date <= end:
                return True
        return False
    
    def get_fixed_shift(self, date: datetime) -> Optional[str]:
        """Get the fixed shift type for a specific date (if fixed roster)"""
        if not self.is_fixed_roster:
            return None
        return self.fixed_schedule.get(date, None)
    
    def __repr__(self):
        return f"{self.name} ({self.year})"


@dataclass
class CoverageIssue:
    """Represents a coverage problem on a specific date/shift"""
    date: datetime
    shift_type: str  # 'D' or 'N'
    required: int
    assigned: int
    shortfall: int
    
    def __repr__(self):
        return (f"{self.date.strftime('%a %d/%m/%Y')} {self.shift_type}-shift: "
                f"Need {self.required}, Have {self.assigned} (Short {self.shortfall})")


class RosterAssignment:
    """Manages staff assignments and coverage checking"""
    
    def __init__(self, roster_start_date: datetime, roster_end_date: datetime,
                 min_paramedics_per_shift: int = 2):
        """
        Initialize the roster assignment system
        
        Args:
            roster_start_date: Start date of roster period
            roster_end_date: End date of roster period
            min_paramedics_per_shift: Minimum paramedics required per shift
        """
        self.roster_start_date = roster_start_date
        self.roster_end_date = roster_end_date
        self.min_paramedics_per_shift = min_paramedics_per_shift
        
        self.line_manager = RosterLineManager(roster_start_date)
        self.staff: List[StaffMember] = []
        
        # Track assignments
        self.line_assignments: Dict[int, List[StaffMember]] = {i: [] for i in range(1, 10)}
        
        # Import boundary validator
        try:
            from roster_boundary_validator import RosterBoundaryValidator
            self.boundary_validator = RosterBoundaryValidator()
        except ImportError:
            self.boundary_validator = None
    
    def add_staff(self, staff: StaffMember):
        """Add a staff member to the roster"""
        self.staff.append(staff)
    
    def find_suitable_lines_for_staff(self, staff: StaffMember) -> List[Tuple[RosterLine, int]]:
        """
        Find suitable lines for a staff member based on their requests
        
        Returns: List of (RosterLine, conflicts) tuples, sorted by best fit
        """
        if staff.requested_dates_off:
            return self.line_manager.rank_lines_by_fit(staff.requested_dates_off)
        else:
            # No specific dates, return all lines as equally suitable
            return [(line, 0) for line in self.line_manager.lines]
    
    def assign_staff_to_line(self, staff: StaffMember, line_number: int) -> bool:
        """
        Assign a staff member to a specific line
        
        Returns: True if successful, False if line is invalid
        """
        if line_number < 1 or line_number > 9:
            return False
        
        staff.assigned_line = line_number
        self.line_assignments[line_number].append(staff)
        return True
    
    def auto_assign_staff(self):
        """
        Automatically assign all staff to lines based on their requests
        Tries to optimize for coverage and staff preferences
        Fixed roster staff are skipped (already have their schedules)
        """
        # First pass: Assign staff who requested specific lines (excluding fixed roster)
        for staff in self.staff:
            if staff.is_fixed_roster:
                continue  # Skip fixed roster staff
            
            if staff.requested_line:
                self.assign_staff_to_line(staff, staff.requested_line)
        
        # Second pass: Assign staff with date requests
        unassigned = [s for s in self.staff if not s.assigned_line and not s.is_fixed_roster]
        
        for staff in unassigned:
            suitable_lines = self.find_suitable_lines_for_staff(staff)
            
            # Try to find the best line that also helps with coverage
            assigned = False
            for line, conflicts in suitable_lines:
                if conflicts == 0:  # Perfect fit
                    # Assign to the line with least current assignments
                    line_num = line.line_number
                    if self.assign_staff_to_line(staff, line_num):
                        assigned = True
                        break
            
            # If no perfect fit, assign to best available
            if not assigned and suitable_lines:
                best_line = suitable_lines[0][0]
                self.assign_staff_to_line(staff, best_line.line_number)
    
    def auto_assign_staff_with_defaults(self, current_roster: Dict[str, int]):
        """
        Automatically assign staff, defaulting to their current line where possible
        
        Args:
            current_roster: Dict mapping staff name -> current line number
        """
        # First pass: Staff who requested specific lines
        for staff in self.staff:
            if staff.is_fixed_roster:
                continue
            
            if staff.requested_line:
                self.assign_staff_to_line(staff, staff.requested_line)
        
        # Second pass: Staff with date requests
        unassigned = [s for s in self.staff if not s.assigned_line and not s.is_fixed_roster]
        
        for staff in unassigned:
            # Check if they have a current line
            current_line = current_roster.get(staff.name, 0)
            
            # If they have date requests, check if their current line works
            if staff.requested_dates_off and current_line > 0:
                current_line_obj = self.line_manager.lines[current_line - 1]
                if current_line_obj.has_days_off(staff.requested_dates_off):
                    # Current line works! Keep them on it
                    self.assign_staff_to_line(staff, current_line)
                    continue
            
            # If no date requests, try to keep them on current line
            if not staff.requested_dates_off and current_line > 0:
                self.assign_staff_to_line(staff, current_line)
                continue
            
            # Otherwise find suitable lines
            suitable_lines = self.find_suitable_lines_for_staff(staff)
            
            assigned = False
            for line, conflicts in suitable_lines:
                if conflicts == 0:
                    line_num = line.line_number
                    if self.assign_staff_to_line(staff, line_num):
                        assigned = True
                        break
            
            if not assigned and suitable_lines:
                best_line = suitable_lines[0][0]
                self.assign_staff_to_line(staff, best_line.line_number)
    
    def get_coverage_for_date(self, date: datetime) -> Dict[str, int]:
        """
        Calculate coverage for a specific date
        
        Returns: Dict with 'D' (day) and 'N' (night) shift counts
        """
        coverage = {'D': 0, 'N': 0}
        
        # Count all staff by getting their actual schedules
        for staff in self.staff:
            # Skip if on leave
            if staff.is_on_leave(date):
                continue
            
            # Get shift type for this staff on this date
            if staff.is_fixed_roster:
                # Fixed roster staff
                shift_type = staff.get_fixed_shift(date)
            else:
                # Rotating roster staff
                if staff.assigned_line:
                    line = self.line_manager.lines[staff.assigned_line - 1]
                    shift_type = line.get_shift_type(date)
                else:
                    continue  # Not assigned
            
            # Count the shift
            if shift_type == 'D':
                coverage['D'] += 1
            elif shift_type == 'N':
                coverage['N'] += 1
        
        return coverage
    
    def check_coverage(self) -> List[CoverageIssue]:
        """
        Check coverage for entire roster period
        
        Returns: List of coverage issues (days with insufficient staff)
        """
        issues = []
        current_date = self.roster_start_date
        
        while current_date <= self.roster_end_date:
            coverage = self.get_coverage_for_date(current_date)
            
            # Check day shift
            if coverage['D'] < self.min_paramedics_per_shift:
                issues.append(CoverageIssue(
                    date=current_date,
                    shift_type='DAY',
                    required=self.min_paramedics_per_shift,
                    assigned=coverage['D'],
                    shortfall=self.min_paramedics_per_shift - coverage['D']
                ))
            
            # Check night shift
            if coverage['N'] < self.min_paramedics_per_shift:
                issues.append(CoverageIssue(
                    date=current_date,
                    shift_type='NIGHT',
                    required=self.min_paramedics_per_shift,
                    assigned=coverage['N'],
                    shortfall=self.min_paramedics_per_shift - coverage['N']
                ))
            
            current_date += timedelta(days=1)
        
        return issues
    
    def get_staff_schedule(self, staff: StaffMember, num_days: int = None) -> List[Tuple[datetime, str]]:
        """
        Get a staff member's schedule
        
        Returns: List of (date, shift_type) tuples
        """
        if num_days is None:
            num_days = (self.roster_end_date - self.roster_start_date).days + 1
        
        schedule = []
        
        # Handle fixed roster staff
        if staff.is_fixed_roster:
            current_date = self.roster_start_date
            for i in range(num_days):
                date = current_date + timedelta(days=i)
                
                if staff.is_on_leave(date):
                    schedule.append((date, 'LEAVE'))
                else:
                    shift_type = staff.get_fixed_shift(date)
                    if shift_type:
                        schedule.append((date, shift_type))
                    else:
                        schedule.append((date, 'O'))  # Default to off if not specified
            
            return schedule
        
        # Handle line-based staff
        if not staff.assigned_line:
            return []
        
        line = self.line_manager.lines[staff.assigned_line - 1]
        schedule = line.get_schedule(self.roster_start_date, num_days)
        
        # Mark leave days
        modified_schedule = []
        for date, shift_type in schedule:
            if staff.is_on_leave(date):
                modified_schedule.append((date, 'LEAVE'))
            else:
                modified_schedule.append((date, shift_type))
        
        return modified_schedule
    
    def print_assignment_summary(self):
        """Print a summary of line assignments"""
        print("\n" + "=" * 80)
        print("ROSTER LINE ASSIGNMENTS")
        print("=" * 80)
        
        # Show fixed roster staff separately
        fixed_staff = [s for s in self.staff if s.is_fixed_roster]
        if fixed_staff:
            print(f"\n📌 Fixed Roster Staff: {len(fixed_staff)}")
            for staff in fixed_staff:
                print(f"  • {staff.name} - {staff.year} (Fixed schedule)")
        
        # Show line assignments
        for line_num in range(1, 10):
            staff_on_line = self.line_assignments[line_num]
            print(f"\n📋 Line {line_num}: {len(staff_on_line)} staff")
            for staff in staff_on_line:
                request_info = ""
                if staff.requested_line == line_num:
                    request_info = " ✅ (Requested this line)"
                elif staff.requested_dates_off:
                    request_info = f" (Had {len(staff.requested_dates_off)} date request(s))"
                print(f"  • {staff.name} - {staff.year}{request_info}")
        
        unassigned = [s for s in self.staff if not s.assigned_line and not s.is_fixed_roster]
        if unassigned:
            print(f"\n⚠️  Unassigned: {len(unassigned)} staff")
            for staff in unassigned:
                print(f"  • {staff}")
    
    def print_coverage_report(self):
        """Print a coverage report for the roster period"""
        issues = self.check_coverage()
        
        print("\n" + "=" * 80)
        print("COVERAGE REPORT")
        print("=" * 80)
        
        if not issues:
            print("\n✅ All shifts have adequate coverage!")
            print(f"   (Minimum {self.min_paramedics_per_shift} paramedics per shift)")
        else:
            print(f"\n⚠️  Found {len(issues)} coverage issue(s):\n")
            for issue in issues:
                print(f"  ❌ {issue}")
        
        # Show coverage statistics
        print("\n📊 Coverage Statistics:")
        total_days = (self.roster_end_date - self.roster_start_date).days + 1
        day_coverages = []
        night_coverages = []
        
        current_date = self.roster_start_date
        while current_date <= self.roster_end_date:
            coverage = self.get_coverage_for_date(current_date)
            day_coverages.append(coverage['D'])
            night_coverages.append(coverage['N'])
            current_date += timedelta(days=1)
        
        print(f"  Day shifts   - Min: {min(day_coverages)}, Max: {max(day_coverages)}, "
              f"Avg: {sum(day_coverages)/len(day_coverages):.1f}")
        print(f"  Night shifts - Min: {min(night_coverages)}, Max: {max(night_coverages)}, "
              f"Avg: {sum(night_coverages)/len(night_coverages):.1f}")


def demo():
    """Demonstration of the roster assignment system"""
    
    # Create roster for 4-week period
    start_date = datetime(2026, 1, 24)
    end_date = datetime(2026, 2, 20)
    
    roster = RosterAssignment(start_date, end_date, min_paramedics_per_shift=2)
    
    # Add some example staff with different request types
    
    # Staff 1: Requests a specific line
    staff1 = StaffMember(
        name="Glenn Chandler",
        role="Paramedic",
        year="Para Yr6",
        requested_line=3
    )
    roster.add_staff(staff1)
    
    # Staff 2: Requests specific dates off
    staff2 = StaffMember(
        name="Samuel Jowett",
        role="Paramedic",
        year="Para Yr6",
        requested_dates_off=[
            datetime(2026, 1, 27),
            datetime(2026, 1, 28),
            datetime(2026, 2, 3),
            datetime(2026, 2, 4),
        ]
    )
    roster.add_staff(staff2)
    
    # Staff 3: Has annual leave
    staff3 = StaffMember(
        name="David McColl",
        role="Paramedic",
        year="Para Yr6",
        leave_periods=[
            (datetime(2026, 2, 11), datetime(2026, 2, 20), "Annual")
        ]
    )
    roster.add_staff(staff3)
    
    # Staff 4: No specific requests
    staff4 = StaffMember(
        name="Shane Orchard",
        role="Paramedic",
        year="Para Yr4"
    )
    roster.add_staff(staff4)
    
    # Staff 5: Requests specific dates
    staff5 = StaffMember(
        name="Jennifer Richards",
        role="Paramedic",
        year="Para Yr6",
        requested_dates_off=[
            datetime(2026, 2, 6),
            datetime(2026, 2, 7),
            datetime(2026, 2, 8),
        ]
    )
    roster.add_staff(staff5)
    
    # Staff 6: Requests line 5
    staff6 = StaffMember(
        name="Joel Pegram",
        role="Paramedic",
        year="Para Yr6",
        requested_line=5
    )
    roster.add_staff(staff6)
    
    print("=" * 80)
    print("PARAMEDIC ROSTER ASSIGNMENT DEMO")
    print("=" * 80)
    print(f"\nRoster Period: {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}")
    print(f"Staff Count: {len(roster.staff)}")
    print(f"Minimum Coverage: {roster.min_paramedics_per_shift} paramedics per shift")
    
    # Show staff requests
    print("\n" + "=" * 80)
    print("STAFF REQUESTS")
    print("=" * 80)
    for staff in roster.staff:
        print(f"\n{staff.name} ({staff.year}):")
        if staff.requested_line:
            print(f"  ✋ Requested Line {staff.requested_line}")
        elif staff.requested_dates_off:
            print(f"  📅 Requested {len(staff.requested_dates_off)} specific dates off:")
            for date in staff.requested_dates_off:
                print(f"     - {date.strftime('%a %d/%m/%Y')}")
        else:
            print(f"  ➡️  No specific requests")
        
        if staff.leave_periods:
            for start, end, leave_type in staff.leave_periods:
                print(f"  🏖️  {leave_type} leave: {start.strftime('%d/%m')} - {end.strftime('%d/%m')}")
    
    # Auto-assign staff
    print("\n" + "=" * 80)
    print("AUTO-ASSIGNING STAFF...")
    print("=" * 80)
    roster.auto_assign_staff()
    
    # Show assignments
    roster.print_assignment_summary()
    
    # Check coverage
    roster.print_coverage_report()
    
    # Show individual schedules
    print("\n" + "=" * 80)
    print("INDIVIDUAL SCHEDULES (First 14 days)")
    print("=" * 80)
    
    for staff in roster.staff:
        if staff.assigned_line:
            print(f"\n{staff.name} - Line {staff.assigned_line}:")
            schedule = roster.get_staff_schedule(staff, 14)
            
            week = []
            for date, shift in schedule:
                day_str = date.strftime("%a %d/%m")
                shift_display = {
                    'D': '☀️ DAY  ',
                    'N': '🌙 NIGHT',
                    'O': '   OFF ',
                    'LEAVE': '🏖️ LEAVE'
                }[shift]
                
                week.append(f"{day_str}: {shift_display}")
                
                if len(week) == 7:
                    print("  " + " | ".join(week))
                    week = []
            
            if week:
                print("  " + " | ".join(week))


if __name__ == "__main__":
    demo()
