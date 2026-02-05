"""
Request History Tracking System
Tracks staff roster change requests and calculates priority scores
"""

from datetime import datetime
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
import json


@dataclass
class LineAssignment:
    """Track each time someone is assigned to a line"""
    roster_period: str                     # "Jan-Mar 2026"
    line_number: int                       # 1-9
    start_date: datetime
    end_date: Optional[datetime] = None    # None if current assignment
    change_reason: str = "initial"         # "initial", "request_approved", "line_swap", "forced_move"
    
    def to_dict(self):
        return {
            'roster_period': self.roster_period,
            'line_number': self.line_number,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'change_reason': self.change_reason
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            roster_period=data['roster_period'],
            line_number=data['line_number'],
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
            change_reason=data.get('change_reason', 'initial')
        )


@dataclass
class RequestRecord:
    """Record of a single roster change request"""
    roster_period: str
    request_date: datetime
    request_type: str                      # "line_change", "dates_off", "stay_on_line", "line_swap"
    request_details: dict
    
    # For line swaps
    swap_partner: Optional[str] = None
    swap_partner_approved: bool = False
    
    # Outcome
    status: str = "pending"                # "pending", "approved", "denied", "modified", "forced_move"
    approved_date: Optional[datetime] = None
    actual_assignment: Optional[dict] = None
    
    # Notes
    denial_reason: Optional[str] = None
    manager_notes: Optional[str] = None
    
    # Forced moves
    was_forced_move: bool = False
    forced_by: Optional[str] = None
    
    def to_dict(self):
        return {
            'roster_period': self.roster_period,
            'request_date': self.request_date.isoformat(),
            'request_type': self.request_type,
            'request_details': self.request_details,
            'swap_partner': self.swap_partner,
            'swap_partner_approved': self.swap_partner_approved,
            'status': self.status,
            'approved_date': self.approved_date.isoformat() if self.approved_date else None,
            'actual_assignment': self.actual_assignment,
            'denial_reason': self.denial_reason,
            'manager_notes': self.manager_notes,
            'was_forced_move': self.was_forced_move,
            'forced_by': self.forced_by
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            roster_period=data['roster_period'],
            request_date=datetime.fromisoformat(data['request_date']),
            request_type=data['request_type'],
            request_details=data['request_details'],
            swap_partner=data.get('swap_partner'),
            swap_partner_approved=data.get('swap_partner_approved', False),
            status=data.get('status', 'pending'),
            approved_date=datetime.fromisoformat(data['approved_date']) if data.get('approved_date') else None,
            actual_assignment=data.get('actual_assignment'),
            denial_reason=data.get('denial_reason'),
            manager_notes=data.get('manager_notes'),
            was_forced_move=data.get('was_forced_move', False),
            forced_by=data.get('forced_by')
        )


@dataclass
class RequestHistory:
    """Complete request history for a staff member"""
    staff_name: str
    
    # Request tracking
    total_requests_submitted: int = 0
    total_requests_approved: int = 0
    total_requests_denied: int = 0
    
    # Line tenure tracking
    current_line: Optional[int] = None
    rosters_on_current_line: int = 0
    line_history: List[LineAssignment] = field(default_factory=list)
    
    # Intern-specific tracking (for rotation and mentorship)
    mentors_worked_with: List[Tuple[str, str, int]] = field(default_factory=list)  # [(mentor_name, roster_period, shifts_together)]
    interns_worked_with: List[Tuple[str, str]] = field(default_factory=list)  # [(intern_name, roster_period)]
    
    # Detailed history
    request_log: List[RequestRecord] = field(default_factory=list)
    
    # Priority score (calculated)
    priority_score: float = 100.0
    
    def calculate_priority_score(self, is_requesting_change: bool = True, staff_role: str = "Paramedic") -> float:
        """
        Calculate priority score for this staff member
        
        Args:
            is_requesting_change: True if requesting a line change, False if requesting to stay
            staff_role: Role of the staff member (affects priority calculation)
        
        Returns:
            Priority score (higher = higher priority)
        """
        # INTERNS: Very low priority, only used for conflicts amongst themselves
        if staff_role == "Intern":
            base_score = 10.0  # Very low base
            
            # Only factor is: have they worked with similar people recently?
            # This is tracked separately in rotation tracking
            recency_bonus = self._get_months_since_last_approval() * 0.5  # Minimal bonus
            approval_penalty = self._get_approvals_last_12_months() * 1  # Minimal penalty
            
            # No tenure protection for interns - they should rotate
            return base_score + recency_bonus - approval_penalty
        
        # REGULAR STAFF: Full priority system
        base_score = 100.0
        
        # Recency bonus: months since last approval
        months_since_approval = self._get_months_since_last_approval()
        recency_bonus = months_since_approval * 5
        
        # Approval penalty: how many approvals in last 12 months
        approvals_last_year = self._get_approvals_last_12_months()
        approval_penalty = approvals_last_year * 10  # Reduced from 50 to be less harsh
        
        # Line tenure bonus: protection for staying on current line
        if not is_requesting_change:
            # They want to STAY on their current line
            if self.rosters_on_current_line < 2:
                line_tenure_bonus = 50  # Strong protection
            elif self.rosters_on_current_line == 2:
                line_tenure_bonus = 25  # Moderate protection
            else:
                line_tenure_bonus = 0   # Fair game
        else:
            # They want to CHANGE lines
            line_tenure_bonus = 0
        
        score = base_score + recency_bonus - approval_penalty + line_tenure_bonus
        
        return max(0, score)  # Never negative
    
    def _get_months_since_last_approval(self) -> int:
        """Get number of months since last approved request"""
        approved_requests = [r for r in self.request_log if r.status == 'approved']
        
        if not approved_requests:
            # Never had approval - give maximum bonus
            return 12
        
        # Find most recent approval
        latest_approval = max(approved_requests, key=lambda r: r.approved_date or r.request_date)
        approval_date = latest_approval.approved_date or latest_approval.request_date
        
        months = (datetime.now() - approval_date).days / 30
        return int(min(months, 12))  # Cap at 12 months
    
    def _get_approvals_last_12_months(self) -> int:
        """Count approved requests in last 12 months"""
        cutoff = datetime.now().replace(year=datetime.now().year - 1)
        
        return sum(1 for r in self.request_log 
                  if r.status == 'approved' 
                  and (r.approved_date or r.request_date) > cutoff)
    
    def add_request(self, request: RequestRecord):
        """Add a new request to the log"""
        self.request_log.append(request)
        self.total_requests_submitted += 1
    
    def approve_request(self, request_index: int, actual_assignment: dict):
        """Mark a request as approved"""
        if 0 <= request_index < len(self.request_log):
            request = self.request_log[request_index]
            request.status = 'approved'
            request.approved_date = datetime.now()
            request.actual_assignment = actual_assignment
            self.total_requests_approved += 1
    
    def deny_request(self, request_index: int, reason: str):
        """Mark a request as denied"""
        if 0 <= request_index < len(self.request_log):
            request = self.request_log[request_index]
            request.status = 'denied'
            request.approved_date = datetime.now()
            request.denial_reason = reason
            self.total_requests_denied += 1
    
    def update_line_assignment(self, new_line: int, roster_period: str, reason: str = "request_approved"):
        """Record a new line assignment"""
        # Close out previous assignment if exists
        if self.line_history and self.line_history[-1].end_date is None:
            self.line_history[-1].end_date = datetime.now()
        
        # Check if staying on same line
        if new_line == self.current_line:
            self.rosters_on_current_line += 1
        else:
            # Moving to new line
            self.rosters_on_current_line = 1
            self.current_line = new_line
        
        # Add new assignment
        assignment = LineAssignment(
            roster_period=roster_period,
            line_number=new_line,
            start_date=datetime.now(),
            change_reason=reason
        )
        self.line_history.append(assignment)
    
    def add_mentor_pairing(self, mentor_name: str, roster_period: str, shifts_together: int = 0):
        """Record that this intern worked with a specific mentor"""
        self.mentors_worked_with.append((mentor_name, roster_period, shifts_together))
    
    def add_intern_pairing(self, intern_name: str, roster_period: str):
        """Record that this intern worked with another intern (on different lines)"""
        self.interns_worked_with.append((intern_name, roster_period))
    
    def has_worked_with_mentor(self, mentor_name: str, within_rosters: int = 2) -> bool:
        """Check if intern worked with this mentor recently"""
        recent_pairings = self.mentors_worked_with[-within_rosters:] if len(self.mentors_worked_with) > within_rosters else self.mentors_worked_with
        return any(name == mentor_name for name, _, _ in recent_pairings)
    
    def has_worked_with_intern(self, intern_name: str, within_rosters: int = 1) -> bool:
        """Check if worked with this intern in recent rosters"""
        recent_pairings = self.interns_worked_with[-within_rosters:] if len(self.interns_worked_with) > within_rosters else self.interns_worked_with
        return any(name == intern_name for name, _ in recent_pairings)
    
    def get_mentor_rotation_score(self, mentor_name: str) -> int:
        """
        Score a potential mentor based on rotation freshness
        Higher score = better choice (haven't worked together recently)
        """
        if not self.mentors_worked_with:
            return 100  # Never worked with anyone, all equally good
        
        # Check how recently they worked together
        for i, (name, period, shifts) in enumerate(reversed(self.mentors_worked_with)):
            if name == mentor_name:
                rosters_ago = i + 1
                # More rosters ago = higher score
                return max(0, 100 - (rosters_ago * 25))
        
        # Never worked together
        return 100
    
    def get_total_shifts_with_mentor(self, mentor_name: str) -> int:
        """Get total number of shifts worked with a specific mentor across all rosters"""
        total = 0
        for name, period, shifts in self.mentors_worked_with:
            if name == mentor_name:
                total += shifts
        return total
    
    def to_dict(self):
        return {
            'staff_name': self.staff_name,
            'total_requests_submitted': self.total_requests_submitted,
            'total_requests_approved': self.total_requests_approved,
            'total_requests_denied': self.total_requests_denied,
            'current_line': self.current_line,
            'rosters_on_current_line': self.rosters_on_current_line,
            'line_history': [a.to_dict() for a in self.line_history],
            'mentors_worked_with': self.mentors_worked_with,
            'interns_worked_with': self.interns_worked_with,
            'request_log': [r.to_dict() for r in self.request_log],
            'priority_score': self.priority_score
        }
    
    @classmethod
    def from_dict(cls, data):
        history = cls(staff_name=data['staff_name'])
        history.total_requests_submitted = data.get('total_requests_submitted', 0)
        history.total_requests_approved = data.get('total_requests_approved', 0)
        history.total_requests_denied = data.get('total_requests_denied', 0)
        history.current_line = data.get('current_line')
        history.rosters_on_current_line = data.get('rosters_on_current_line', 0)
        history.line_history = [LineAssignment.from_dict(a) for a in data.get('line_history', [])]
        history.mentors_worked_with = data.get('mentors_worked_with', [])
        history.interns_worked_with = data.get('interns_worked_with', [])
        history.request_log = [RequestRecord.from_dict(r) for r in data.get('request_log', [])]
        history.priority_score = data.get('priority_score', 100.0)
        return history


def demo():
    """Demonstrate the request history system"""
    
    print("=" * 80)
    print("REQUEST HISTORY SYSTEM DEMO")
    print("=" * 80)
    
    # Create some example staff histories
    staff_a = RequestHistory(staff_name="Jane Smith")
    staff_a.current_line = 3
    staff_a.rosters_on_current_line = 1  # Just started on this line
    
    # Add some historical requests
    staff_a.add_request(RequestRecord(
        roster_period="Oct-Dec 2025",
        request_date=datetime(2025, 10, 1),
        request_type="line_change",
        request_details={"requested_line": 5},
        status="denied",
        denial_reason="Conflict with another staff member"
    ))
    staff_a.total_requests_denied += 1
    
    staff_a.add_request(RequestRecord(
        roster_period="Jan-Mar 2026",
        request_date=datetime(2026, 1, 1),
        request_type="line_change",
        request_details={"requested_line": 3},
        status="approved",
        approved_date=datetime(2026, 1, 5)
    ))
    staff_a.total_requests_approved += 1
    
    # Calculate priority for wanting to STAY on Line 3
    priority_stay = staff_a.calculate_priority_score(is_requesting_change=False)
    print(f"\n{staff_a.staff_name}:")
    print(f"  Current Line: {staff_a.current_line}")
    print(f"  Rosters on line: {staff_a.rosters_on_current_line}")
    print(f"  Requests: {staff_a.total_requests_submitted} submitted, {staff_a.total_requests_approved} approved")
    print(f"  Priority to STAY on line: {priority_stay:.1f} (has tenure protection +50)")
    
    # Calculate priority for wanting to CHANGE
    priority_change = staff_a.calculate_priority_score(is_requesting_change=True)
    print(f"  Priority to CHANGE lines: {priority_change:.1f} (no tenure protection)")
    
    print("\n" + "=" * 80)
    
    # Staff B - been on line for 3 rosters
    staff_b = RequestHistory(staff_name="Bob Jones")
    staff_b.current_line = 5
    staff_b.rosters_on_current_line = 3
    staff_b.total_requests_submitted = 3
    staff_b.total_requests_approved = 3
    
    priority_stay_b = staff_b.calculate_priority_score(is_requesting_change=False)
    print(f"\n{staff_b.staff_name}:")
    print(f"  Current Line: {staff_b.current_line}")
    print(f"  Rosters on line: {staff_b.rosters_on_current_line}")
    print(f"  Requests: {staff_b.total_requests_submitted} submitted, {staff_b.total_requests_approved} approved")
    print(f"  Priority to STAY on line: {priority_stay_b:.1f} (no tenure protection - been there 3+ rosters)")
    
    print("\n" + "=" * 80)
    print(f"\nCONFLICT RESOLUTION:")
    print(f"If Jane requests Line 5 (priority: {priority_change:.1f})")
    print(f"And Bob wants to stay on Line 5 (priority: {priority_stay_b:.1f})")
    print(f"Winner: {'Jane' if priority_change > priority_stay_b else 'Bob'}")


if __name__ == "__main__":
    demo()
