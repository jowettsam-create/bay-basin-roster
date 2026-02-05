"""
Roster Conflict Detection and Resolution
Identifies conflicts in roster requests and resolves them using priority scores
"""

from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from roster_assignment import StaffMember
from request_history import RequestHistory
from roster_lines import RosterLineManager


@dataclass
class RequestConflict:
    """Represents a conflict where multiple staff want the same line"""
    line_number: int
    requesters: List[Tuple[StaffMember, float]]  # (staff, priority_score)
    current_occupant: Optional[Tuple[StaffMember, float]] = None  # Who's currently on this line
    
    def get_winner(self) -> StaffMember:
        """Determine who should get this line based on priority"""
        all_candidates = list(self.requesters)
        if self.current_occupant:
            all_candidates.append(self.current_occupant)
        
        # Sort by priority score (highest first)
        all_candidates.sort(key=lambda x: x[1], reverse=True)
        return all_candidates[0][0]
    
    def get_losers(self) -> List[StaffMember]:
        """Get staff who don't win this line"""
        winner = self.get_winner()
        all_candidates = [s for s, _ in self.requesters]
        if self.current_occupant:
            all_candidates.append(self.current_occupant[0])
        
        return [s for s in all_candidates if s.name != winner.name]


@dataclass
class InternPairingViolation:
    """Represents a violation where two interns would be on the same line"""
    line_number: int
    interns: List[StaffMember]


class ConflictDetector:
    """Detects conflicts in roster assignments"""
    
    def __init__(self, staff_list: List[StaffMember], current_roster: Dict[str, int],
                 request_histories: Dict[str, RequestHistory], roster_start: datetime):
        self.staff_list = staff_list
        self.current_roster = current_roster
        self.request_histories = request_histories
        self.roster_start = roster_start
        self.line_manager = RosterLineManager(roster_start)
    
    def detect_line_conflicts(self) -> List[RequestConflict]:
        """
        Detect when multiple staff request the same line
        
        Returns: List of conflicts
        """
        conflicts = []
        
        # Group requests by line number
        line_requests: Dict[int, List[Tuple[StaffMember, bool]]] = {}  # line -> [(staff, is_change_request)]
        
        for staff in self.staff_list:
            if staff.is_fixed_roster:
                continue
            
            current_line = self.current_roster.get(staff.name, 0)
            
            # Staff requesting a specific line
            if staff.requested_line:
                if staff.requested_line not in line_requests:
                    line_requests[staff.requested_line] = []
                is_change = (staff.requested_line != current_line)
                line_requests[staff.requested_line].append((staff, is_change))
            
            # Staff with no request (wants to stay on current line)
            elif current_line > 0:
                if current_line not in line_requests:
                    line_requests[current_line] = []
                line_requests[current_line].append((staff, False))  # Not a change, staying put
        
        # Check each line for conflicts
        for line_num, requests in line_requests.items():
            if len(requests) > 1:
                # Multiple people want this line - conflict!
                requesters_with_priority = []
                current_occupant = None
                
                for staff, is_change_request in requests:
                    current_line = self.current_roster.get(staff.name, 0)
                    
                    # Get or create request history
                    history = self.request_histories.get(staff.name, RequestHistory(staff_name=staff.name))
                    
                    # Update current line info if not set
                    if history.current_line is None and current_line > 0:
                        history.current_line = current_line
                        history.rosters_on_current_line = 1
                    
                    # Calculate priority
                    priority = history.calculate_priority_score(is_requesting_change=is_change_request)
                    
                    if current_line == line_num:
                        # This person is currently on this line
                        current_occupant = (staff, priority)
                    else:
                        # This person is requesting to move here
                        requesters_with_priority.append((staff, priority))
                
                # Only a conflict if someone is actively requesting to move to this line
                # (not just multiple people already on the line with no change requests)
                if len(requesters_with_priority) > 0:
                    conflict = RequestConflict(
                        line_number=line_num,
                        requesters=requesters_with_priority,
                        current_occupant=current_occupant
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def detect_intern_violations(self, proposed_assignments: Dict[str, int]) -> List[InternPairingViolation]:
        """
        Detect if two interns would be assigned to the same line
        
        Args:
            proposed_assignments: Dict mapping staff_name -> line_number
        
        Returns: List of intern pairing violations
        """
        violations = []
        
        # Group by line
        line_assignments: Dict[int, List[StaffMember]] = {}
        
        for staff in self.staff_list:
            if staff.is_fixed_roster:
                continue
            
            assigned_line = proposed_assignments.get(staff.name, 0)
            if assigned_line > 0:
                if assigned_line not in line_assignments:
                    line_assignments[assigned_line] = []
                line_assignments[assigned_line].append(staff)
        
        # Check each line for intern pairing
        for line_num, staff_on_line in line_assignments.items():
            interns = [s for s in staff_on_line if s.role == "Intern"]
            
            if len(interns) > 1:
                violations.append(InternPairingViolation(
                    line_number=line_num,
                    interns=interns
                ))
        
        return violations
    
    def suggest_alternatives(self, staff: StaffMember, unavailable_lines: List[int]) -> List[Tuple[int, str]]:
        """
        Suggest alternative lines for a staff member
        
        Args:
            staff: Staff member who needs an alternative
            unavailable_lines: Lines they can't have
        
        Returns: List of (line_number, reason) tuples
        """
        suggestions = []
        
        # If they have date requests, find lines that work
        if staff.requested_dates_off:
            suitable_lines = self.line_manager.rank_lines_by_fit(staff.requested_dates_off)
            
            for line, conflicts in suitable_lines:
                if line.line_number not in unavailable_lines:
                    if conflicts == 0:
                        suggestions.append((line.line_number, "Perfect fit for your dates"))
                    else:
                        suggestions.append((line.line_number, f"{conflicts} date conflict(s)"))
                    
                    if len(suggestions) >= 3:
                        break
        else:
            # No date preferences, suggest any available line
            for line_num in range(1, 10):
                if line_num not in unavailable_lines:
                    suggestions.append((line_num, "Available"))
                    if len(suggestions) >= 3:
                        break
        
        return suggestions


def demo():
    """Demonstrate conflict detection"""
    from roster_assignment import StaffMember
    from datetime import datetime
    
    print("=" * 80)
    print("CONFLICT DETECTION DEMO")
    print("=" * 80)
    
    # Create some staff with conflicting requests
    staff1 = StaffMember(name="Jane Smith", role="Paramedic", year="Yr6", requested_line=3)
    staff2 = StaffMember(name="Bob Jones", role="Paramedic", year="Yr5", requested_line=3)
    staff3 = StaffMember(name="Alice Wong", role="Paramedic", year="Yr4", requested_line=3)
    
    # Create request histories
    hist1 = RequestHistory(staff_name="Jane Smith")
    hist1.current_line = 5
    hist1.rosters_on_current_line = 1
    hist1.total_requests_approved = 0  # Never had approval - high priority
    
    hist2 = RequestHistory(staff_name="Bob Jones")
    hist2.current_line = 3  # Currently on Line 3
    hist2.rosters_on_current_line = 1  # Just got here
    hist2.total_requests_approved = 1
    
    hist3 = RequestHistory(staff_name="Alice Wong")
    hist3.current_line = 7
    hist3.rosters_on_current_line = 2
    hist3.total_requests_approved = 3  # Lots of approvals - lower priority
    
    histories = {
        "Jane Smith": hist1,
        "Bob Jones": hist2,
        "Alice Wong": hist3
    }
    
    current_roster = {
        "Jane Smith": 5,
        "Bob Jones": 3,
        "Alice Wong": 7
    }
    
    # Detect conflicts
    detector = ConflictDetector(
        staff_list=[staff1, staff2, staff3],
        current_roster=current_roster,
        request_histories=histories,
        roster_start=datetime(2026, 1, 24)
    )
    
    conflicts = detector.detect_line_conflicts()
    
    print(f"\n📋 Found {len(conflicts)} conflict(s)")
    
    for conflict in conflicts:
        print(f"\n⚠️  CONFLICT: Line {conflict.line_number}")
        print(f"   Requesters:")
        for staff, priority in conflict.requesters:
            print(f"     • {staff.name}: Priority {priority:.1f}")
        
        if conflict.current_occupant:
            staff, priority = conflict.current_occupant
            print(f"   Current occupant:")
            print(f"     • {staff.name}: Priority {priority:.1f} (wants to stay)")
        
        winner = conflict.get_winner()
        print(f"\n   ✅ WINNER: {winner.name}")
        
        losers = conflict.get_losers()
        print(f"   ❌ Need alternatives: {', '.join(s.name for s in losers)}")
        
        # Suggest alternatives
        for loser in losers:
            alternatives = detector.suggest_alternatives(loser, [conflict.line_number])
            print(f"\n   Alternatives for {loser.name}:")
            for line_num, reason in alternatives[:3]:
                print(f"     → Line {line_num}: {reason}")
    
    print("\n" + "=" * 80)
    
    # Test intern pairing detection
    print("\n" + "=" * 80)
    print("INTERN PAIRING VIOLATION DEMO")
    print("=" * 80)
    
    intern1 = StaffMember(name="Intern A", role="Intern", year="Yr1")
    intern2 = StaffMember(name="Intern B", role="Intern", year="Yr1")
    para1 = StaffMember(name="Para C", role="Paramedic", year="Yr5")
    
    detector2 = ConflictDetector(
        staff_list=[intern1, intern2, para1],
        current_roster={},
        request_histories={},
        roster_start=datetime(2026, 1, 24)
    )
    
    # Proposed assignments with intern violation
    proposed = {
        "Intern A": 5,
        "Intern B": 5,  # Both interns on Line 5!
        "Para C": 3
    }
    
    violations = detector2.detect_intern_violations(proposed)
    
    if violations:
        print(f"\n⚠️  Found {len(violations)} intern pairing violation(s)")
        for v in violations:
            print(f"\n   Line {v.line_number} has multiple interns:")
            for intern in v.interns:
                print(f"     • {intern.name}")
    else:
        print("\n✅ No intern pairing violations")


if __name__ == "__main__":
    demo()
