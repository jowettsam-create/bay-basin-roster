"""
Intern Assignment System
Special logic for assigning interns to maximize learning and rotation
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from roster_assignment import StaffMember
from request_history import RequestHistory
from roster_lines import RosterLineManager


class InternAssignmentSystem:
    """
    Handles special assignment logic for interns:
    - Very low priority (only matters vs other interns)
    - Should work with different mentors each roster
    - Should avoid repeat pairings with other interns
    - Prefer lines where mentor doesn't have 3-week leave block
    """
    
    def __init__(self, staff_list: List[StaffMember], current_roster: Dict[str, int],
                 request_histories: Dict[str, RequestHistory], roster_start: datetime, roster_end: datetime):
        self.staff_list = staff_list
        self.current_roster = current_roster
        self.request_histories = request_histories
        self.roster_start = roster_start
        self.roster_end = roster_end
        self.line_manager = RosterLineManager(roster_start)
        
        # Separate interns and paramedics
        self.interns = [s for s in staff_list if s.role == "Intern" and not s.is_fixed_roster]
        self.paramedics = [s for s in staff_list if s.role == "Paramedic" and not s.is_fixed_roster]
        # Optional: {line_num: shortfall_days} set by caller to nudge interns toward understaffed lines
        self.line_coverage_needs: Dict[int, int] = {}
    
    def assign_interns(self) -> Dict[str, int]:
        """
        Assign all interns to lines using rotation logic
        
        Returns: Dict mapping intern_name -> assigned_line
        """
        assignments = {}
        
        if not self.interns:
            return assignments
        
        # Get available lines (not taken by other interns already assigned)
        used_lines = set()
        
        # Sort interns by their tiny priority scores (to resolve conflicts amongst themselves)
        interns_with_priority = []
        for intern in self.interns:
            history = self.request_histories.get(intern.name, RequestHistory(staff_name=intern.name))
            priority = history.calculate_priority_score(is_requesting_change=True, staff_role="Intern")
            interns_with_priority.append((intern, priority, history))
        
        # Sort by priority (highest first)
        interns_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        # Assign each intern
        for intern, priority, history in interns_with_priority:
            best_line = self._find_best_line_for_intern(intern, history, used_lines)
            
            if best_line:
                assignments[intern.name] = best_line
                used_lines.add(best_line)
            else:
                # Fallback: assign to any available line
                for line_num in range(1, 10):
                    if line_num not in used_lines:
                        assignments[intern.name] = line_num
                        used_lines.add(line_num)
                        break
        
        return assignments
    
    def _find_best_line_for_intern(self, intern: StaffMember, history: RequestHistory, 
                                   unavailable_lines: set) -> Optional[int]:
        """
        Find the best line for this intern considering:
        1. Not already taken by another intern
        2. Maximize exposure to new paramedics (considering shift overlaps, not just same line)
        3. Paramedic doesn't have a 3-week leave block
        4. Respects intern's date requests if any
        """
        # Calculate which paramedics the intern would work with on each line
        # by checking shift overlaps across the entire roster
        
        # Score each available line
        line_scores = []
        
        for line_num in range(1, 10):
            if line_num in unavailable_lines:
                continue
            
            score = 0
            reasons = []
            
            # Check if intern's date requests work with this line
            if intern.requested_dates_off:
                line_obj = self.line_manager.lines[line_num - 1]
                if line_obj.has_days_off(intern.requested_dates_off):
                    score += 50
                    reasons.append("Matches date requests")
                else:
                    conflicts = line_obj.count_working_days(intern.requested_dates_off)
                    score -= conflicts * 10
                    reasons.append(f"{conflicts} date conflict(s)")
            
            # Calculate which paramedics this intern would overlap with on this line
            intern_line_obj = self.line_manager.lines[line_num - 1]
            
            # Generate intern's schedule on this line
            intern_schedule = []
            current_date = self.roster_start
            while current_date <= self.roster_end:
                shift = intern_line_obj.get_shift_type(current_date)
                # Check for intern's leave
                if intern.leave_periods:
                    for leave_start, leave_end, _ in intern.leave_periods:
                        if leave_start <= leave_end:
                            shift = 'LEAVE'
                            break
                intern_schedule.append((current_date, shift))
                current_date += timedelta(days=1)
            
            # Check overlap with ALL paramedics (not just same line)
            mentor_exposure_score = 0
            mentors_found = []
            
            for para in self.paramedics:
                # Get paramedic's current/assigned line
                para_line = self.current_roster.get(para.name, 0)
                if para_line == 0:
                    continue
                
                # Check if para has long leave
                has_long_leave = self._has_long_leave_block(para)
                
                # Generate para's schedule
                para_line_obj = self.line_manager.lines[para_line - 1]
                para_schedule = []
                current_date = self.roster_start
                while current_date <= self.roster_end:
                    shift = para_line_obj.get_shift_type(current_date)
                    # Check for para's leave
                    if para.leave_periods:
                        for leave_start, leave_end, _ in para.leave_periods:
                            if leave_start <= current_date <= leave_end:
                                shift = 'LEAVE'
                                break
                    para_schedule.append((current_date, shift))
                    current_date += timedelta(days=1)
                
                # Count shift overlaps
                shared_shifts = 0
                for i, (date, intern_shift) in enumerate(intern_schedule):
                    if intern_shift in ['D', 'N'] and i < len(para_schedule):
                        para_shift = para_schedule[i][1]
                        if para_shift == intern_shift:  # Same shift type on same day
                            shared_shifts += 1
                
                # If they would work together
                if shared_shifts > 0:
                    mentors_found.append((para.name, shared_shifts))
                    
                    # Check rotation freshness
                    if history.has_worked_with_mentor(para.name, within_rosters=2):
                        # Already worked with this mentor recently
                        score -= 20 * (shared_shifts / 10)  # Penalty based on shift count
                        reasons.append(f"Repeat mentor: {para.name} ({shared_shifts} shifts)")
                    else:
                        # New mentor - good!
                        score += 30 * (shared_shifts / 10)  # Bonus based on shift count
                        reasons.append(f"New mentor: {para.name} ({shared_shifts} shifts)")
                    
                    # Penalize if mentor has long leave
                    if has_long_leave:
                        score -= 15
                        reasons.append(f"{para.name} has long leave")
            
            # Bonus for having multiple mentors (varied exposure)
            if len(mentors_found) > 1:
                score += 20
                reasons.append(f"Multiple mentors ({len(mentors_found)} paramedics)")
            elif len(mentors_found) == 1:
                score += 10
                reasons.append(f"Single mentor")
            else:
                score -= 20
                reasons.append("No paramedic mentors found")

            # Coverage bonus: nudge interns toward understaffed lines
            if self.line_coverage_needs.get(line_num, 0) > 0:
                score += 25
                reasons.append(f"Coverage need ({self.line_coverage_needs[line_num]} shortfall shifts)")
            
            line_scores.append((line_num, score, reasons, mentors_found))
        
        if not line_scores:
            return None
        
        # Sort by score (highest first)
        line_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return the best line
        return line_scores[0][0]
    
    def _has_long_leave_block(self, staff: StaffMember) -> bool:
        """Check if staff has a leave period >= 14 days"""
        if not staff.leave_periods:
            return False
        
        for start, end, leave_type in staff.leave_periods:
            days = (end - start).days + 1
            if days >= 14:  # 2+ weeks
                return True
        
        return False
    
    def get_mentor_for_intern(self, intern_name: str, intern_line: int) -> Optional[str]:
        """
        Find the paramedic mentor for this intern on their assigned line
        
        Returns: Mentor name or None
        """
        for para in self.paramedics:
            para_line = self.current_roster.get(para.name, 0)
            if para_line == intern_line:
                return para.name
        
        return None
    
    def record_intern_pairings(self, assignments: Dict[str, int], roster_period: str):
        """
        Record mentor and intern pairings for rotation tracking.

        Rules:
        - Same-line paramedic = mentor. Count shared working shifts.
        - If no same-line mentor, record split pairings (shared shifts
          from different lines).
        - When a same-line mentor exists, skip incidental overlaps from
          other lines.
        - Clears previous entries for this roster period so re-runs are safe.

        Args:
            assignments: Dict mapping staff_name -> line_number
            roster_period: e.g. "Jan-Mar 2026"
        """
        # Build schedules (respecting leave) for everyone with an assignment
        schedules = {}
        for staff in self.staff_list:
            line = assignments.get(staff.name, self.current_roster.get(staff.name, 0))
            if line > 0:
                line_obj = self.line_manager.lines[line - 1]
                schedule = []
                current_date = self.roster_start
                while current_date <= self.roster_end:
                    shift = line_obj.get_shift_type(current_date)
                    if staff.leave_periods:
                        for leave_start, leave_end, _ in staff.leave_periods:
                            if leave_start <= current_date <= leave_end:
                                shift = 'LEAVE'
                                break
                    schedule.append((current_date, shift))
                    current_date += timedelta(days=1)
                schedules[staff.name] = schedule

        for intern in self.interns:
            intern_line = assignments.get(intern.name, 0)
            intern_schedule = schedules.get(intern.name, [])
            if not intern_schedule:
                continue

            history = self.request_histories.get(intern.name)
            if not history:
                history = RequestHistory(staff_name=intern.name)
                self.request_histories[intern.name] = history

            # Clear previous entries for this period (safe to re-run)
            history.clear_pairings_for_period(roster_period)

            # Find same-line mentor(s)
            same_line_mentors = []
            for para in self.paramedics:
                para_line = assignments.get(para.name, self.current_roster.get(para.name, 0))
                if para_line == intern_line and para_line > 0:
                    para_schedule = schedules.get(para.name, [])
                    shared = self._count_shared_shifts(intern_schedule, para_schedule)
                    if shared > 0:
                        same_line_mentors.append((para.name, shared))

            if same_line_mentors:
                # Record same-line mentor(s) only
                for mentor_name, shifts in same_line_mentors:
                    history.add_mentor_pairing(mentor_name, roster_period, shifts_together=shifts)
            else:
                # No same-line mentor — record split pairings (different line, shared shifts)
                for para in self.paramedics:
                    para_line = assignments.get(para.name, self.current_roster.get(para.name, 0))
                    if para_line == intern_line or para_line == 0:
                        continue
                    para_schedule = schedules.get(para.name, [])
                    shared = self._count_shared_shifts(intern_schedule, para_schedule)
                    if shared > 0:
                        history.add_mentor_pairing(para.name, roster_period, shifts_together=shared)

            # Record other interns in same roster
            for other_intern in self.interns:
                if other_intern.name != intern.name:
                    history.add_intern_pairing(other_intern.name, roster_period)

    @staticmethod
    def _count_shared_shifts(schedule_a, schedule_b) -> int:
        """Count shifts where both schedules have the same working shift type (D or N)."""
        shared = 0
        for i, (date, shift_a) in enumerate(schedule_a):
            if shift_a in ('D', 'N') and i < len(schedule_b):
                if schedule_b[i][1] == shift_a:
                    shared += 1
        return shared


def demo():
    """Demonstrate intern assignment system"""
    from datetime import datetime
    
    print("=" * 80)
    print("INTERN ASSIGNMENT SYSTEM DEMO")
    print("=" * 80)
    
    # Create roster period
    roster_start = datetime(2026, 1, 24)
    roster_end = datetime(2026, 3, 27)
    
    # Create some paramedics
    para1 = StaffMember(name="Senior Para A", role="Paramedic", year="Yr6")
    para2 = StaffMember(name="Senior Para B", role="Paramedic", year="Yr6")
    para3 = StaffMember(name="Para C (On Leave)", role="Paramedic", year="Yr5",
                        leave_periods=[(datetime(2026, 2, 8), datetime(2026, 2, 28), "Annual")])  # 3 weeks
    para4 = StaffMember(name="Senior Para D", role="Paramedic", year="Yr6")
    
    # Create interns
    intern1 = StaffMember(name="Intern Alice", role="Intern", year="Yr1")
    intern2 = StaffMember(name="Intern Bob", role="Intern", year="Yr1")
    
    staff_list = [para1, para2, para3, para4, intern1, intern2]
    
    # Current roster - paramedics on various lines
    current_roster = {
        "Senior Para A": 3,
        "Senior Para B": 5,
        "Para C (On Leave)": 7,
        "Senior Para D": 2,
    }
    
    # Request histories
    hist_intern1 = RequestHistory(staff_name="Intern Alice")
    hist_intern1.mentors_worked_with = [("Senior Para A", "Oct-Dec 2025", 8)]  # Worked 8 shifts with Para A last roster
    
    hist_intern2 = RequestHistory(staff_name="Intern Bob")
    hist_intern2.mentors_worked_with = [("Senior Para D", "Oct-Dec 2025", 10)]  # Worked 10 shifts with Para D last roster
    
    request_histories = {
        "Intern Alice": hist_intern1,
        "Intern Bob": hist_intern2
    }
    
    # Assign interns
    system = InternAssignmentSystem(
        staff_list=staff_list,
        current_roster=current_roster,
        request_histories=request_histories,
        roster_start=roster_start,
        roster_end=roster_end
    )
    
    assignments = system.assign_interns()
    
    print("\n📋 INTERN ASSIGNMENTS:")
    for intern_name, line in assignments.items():
        print(f"\n{intern_name} → Line {line}")
        
        # Find ALL mentors they'll work with (not just same line)
        history = request_histories.get(intern_name)
        if history and history.mentors_worked_with:
            # Get the most recent entries (from this roster)
            recent_mentors = [m for m in history.mentors_worked_with if m[1] == "Jan-Mar 2026"]
            if recent_mentors:
                print(f"  Mentors this roster (Jan-Mar 2026):")
                for mentor, period, shifts in sorted(recent_mentors, key=lambda x: x[2], reverse=True):
                    if shifts >= 20:  # Primary mentor (most shifts)
                        print(f"    🟢 {mentor}: {shifts} shifts (primary mentor)")
                    elif shifts >= 5:
                        print(f"    🟡 {mentor}: {shifts} shifts (regular exposure)")
                    else:
                        print(f"    🟠 {mentor}: {shifts} shifts (occasional)")
    
    print("\n" + "=" * 80)
    print("\nPARAMEDIC PLACEMENTS:")
    for name, line in current_roster.items():
        para = next(s for s in staff_list if s.name == name)
        if para.leave_periods:
            print(f"  Line {line}: {name} (Has long leave - not ideal for intern mentoring)")
        else:
            print(f"  Line {line}: {name}")
    
    print("\n" + "=" * 80)
    
    # Record pairings
    all_assignments = {**current_roster, **assignments}
    system.record_intern_pairings(all_assignments, "Jan-Mar 2026")
    
    print("\nRECORDED PAIRINGS:")
    for intern_name in assignments.keys():
        history = request_histories[intern_name]
        print(f"\n{intern_name}:")
        if history.mentors_worked_with:
            print(f"  Mentors worked with:")
            for mentor, period, shifts in history.mentors_worked_with:
                print(f"    • {mentor} ({period}) - {shifts} shifts together")
        print(f"  Priority score: {history.calculate_priority_score(staff_role='Intern'):.1f} (very low - intern)")


if __name__ == "__main__":
    demo()
