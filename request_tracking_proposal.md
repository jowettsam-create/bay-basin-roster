# Request Tracking & Priority System Proposal

## Overview
Track staff roster change requests over time and use this data to prioritize future requests fairly.

## Data to Track (per staff member)

```python
class RequestHistory:
    # Request tracking
    total_requests_submitted: int = 0      # How many times they've asked
    total_requests_approved: int = 0       # How many were granted
    total_requests_denied: int = 0         # How many were rejected
    
    # Line tenure tracking
    current_line: Optional[int] = None     # What line they're on now
    rosters_on_current_line: int = 0       # Consecutive rosters on this line
    line_history: List[LineAssignment] = [] # History of line assignments
    
    # Detailed history
    request_log: List[RequestRecord] = []
    
    # Priority score (calculated)
    priority_score: float = 0.0

class LineAssignment:
    """Track each time someone is assigned to a line"""
    roster_period: str                     # "Jan-Mar 2026"
    line_number: int                       # 1-9
    start_date: datetime                   # When they started on this line
    end_date: Optional[datetime]           # When they moved off (None if current)
    change_reason: str                     # "initial", "request_approved", "line_swap", "forced_move"
```

## Request Record Structure

```python
class RequestRecord:
    roster_period: str                     # "Jan-Mar 2026"
    request_date: datetime                 # When they submitted
    request_type: str                      # "line_change", "dates_off", "stay_on_line", "line_swap"
    request_details: dict                  # What they asked for
    
    # For line swaps
    swap_partner: Optional[str]            # Name of person swapping with
    swap_partner_approved: bool = False    # Did partner agree?
    
    # Outcome
    status: str                            # "pending", "approved", "denied", "modified", "forced_move"
    approved_date: Optional[datetime]      # When manager approved/denied
    actual_assignment: Optional[dict]      # What they actually got
    
    # Notes
    denial_reason: Optional[str]           # Why it was denied
    manager_notes: Optional[str]           # Any manager comments
    
    # Forced moves (when bumped by higher priority)
    was_forced_move: bool = False          # Were they moved against their will?
    forced_by: Optional[str]               # Who caused the forced move
```

## Priority Score Calculation

### Formula:
```
priority_score = base_score + recency_bonus - approval_penalty + line_tenure_bonus

Where:
- base_score = 100 (everyone starts equal)
- recency_bonus = months_since_last_approval * 5
- approval_penalty = (requests_approved_last_year / total_staff_requests) * 50
- line_tenure_bonus = line_tenure_protection_score (see below)
```

### Line Tenure Protection System

**Purpose:** Protect staff who are settled on a line from being moved due to others' requests

**Tenure Score Calculation:**
```
If requesting to STAY on current line:
  rosters_on_current_line = count of consecutive rosters on this line
  
  if rosters_on_current_line < 2:
    line_tenure_bonus = 50  (strong protection)
  elif rosters_on_current_line == 2:
    line_tenure_bonus = 25  (moderate protection)  
  else:
    line_tenure_bonus = 0   (fair game for changes)

If requesting to CHANGE lines:
  line_tenure_bonus = 0  (no protection when you want to move)
```

**Key Rules:**
- Staff get **strong protection** (bonus +50) for their first 2 rosters on a line
- After 2 rosters, protection drops to moderate (bonus +25)
- After 3+ rosters, no tenure protection (bonus 0)
- Requesting a change forfeits your tenure protection

### Line Swap System

**Purpose:** Allow two staff to swap lines with mutual consent, bypassing normal priority

**Requirements:**
```
1. Both staff must consent to the swap
2. Both must be on rotating roster (not fixed)
3. Award compliance must be validated for both:
   - Check line transition rules
   - Check any leave periods
   - Check intern pairing if applicable
4. Manager must approve the swap
```

**Process:**
```
1. Staff A initiates swap request with Staff B
2. Staff B receives notification and must accept
3. System validates Award compliance for both
4. Manager reviews and approves
5. Swap is recorded as "approved" for both (counts toward their history)
6. Both staff reset to 1 roster on their new line (tenure protection restarts)
```

**Priority Calculation:** Line swaps are treated as approved requests for both parties

### Example Scenarios:

**Staff A - Frequent Requester:** 
- Last 12 months: 3 requests, 3 approved (100% success)
- On current line for 1 roster (wants to stay)
- Priority score: 100 + 0 - 30 + 50 = **120** (tenure protection keeps them competitive)

**Staff B - Rarely Approved:**
- Last 12 months: 3 requests, 0 approved (0% success)  
- On current line for 4 rosters (requesting change)
- Priority score: 100 + 15 - 0 + 0 = **115** (high from poor history, but no tenure)

**Staff C - Long Time Since Approval:**
- Last 12 months: 1 request, 1 approved (100% success)
- But it was 6 months ago, on Line 3 for 1 roster (wants to stay)
- Priority score: 100 + 30 - 10 + 50 = **170** (highest - combines recency, low requests, and tenure)

**Staff D - New to Line, Wants to Stay:**
- Last 12 months: 2 requests, 1 approved (50% success)
- Just moved to Line 5 this roster (first roster on it)
- Priority score: 100 + 10 - 17 + 50 = **143** (strong tenure protection for newcomers)

**Staff E - Settled, Someone Wants Their Line:**
- Last 12 months: 0 requests (never asks for changes)
- On Line 7 for 3 rosters, not requesting change
- Priority score: 100 + 60 - 0 + 0 = **160** (very high but no tenure protection)
- **Vulnerable:** Staff D above could potentially displace them

## Integration with Roster Generation

### New Assignment Logic:

```
1. Validate all requests against rules (interns, Award compliance, leave)
   → Mark as "valid" or "invalid with reason"

2. Detect conflicts (multiple people want same line)
   → Group conflicting requests

3. Resolve conflicts using priority scores:
   - Sort conflicting staff by priority_score (highest first)
   - Award to highest priority
   - Offer alternatives to others based on their needs

4. Track outcomes:
   - Record "approved" for those who got their request
   - Record "denied" for those who didn't
   - Save denial reasons
```

## UI Changes Needed

### Manager Tab - New Features:

**1. Request Review Section:**
```
┌─────────────────────────────────────────┐
│ Pending Requests (Sorted by Priority)  │
├─────────────────────────────────────────┤
│                                         │
│ 🔴 HIGH PRIORITY (Score: 120)          │
│ Jane Smith - Line 3 Request             │
│ Priority: No approvals in 6 months      │
│ [✓ Approve] [✗ Deny] [📝 Modify]       │
│                                         │
│ 🟡 MEDIUM PRIORITY (Score: 95)         │
│ John Doe - Dates Off: 15-17 Feb        │
│ Priority: 1 approval this year          │
│ [✓ Approve] [✗ Deny] [📝 Modify]       │
│                                         │
│ 🟢 LOW PRIORITY (Score: 70)            │
│ Bob Jones - Line 5 Request              │
│ Priority: 3 approvals this year         │
│ Conflict: Jane also wants Line 5       │
│ [✓ Approve] [✗ Deny] [📝 Modify]       │
└─────────────────────────────────────────┘
```

**2. Conflict Resolution Helper:**
```
⚠️ CONFLICT DETECTED

Line 3 requested by:
1. Jane Smith (Priority: 120) - Recommended ✓
2. Bob Jones (Priority: 70)

Alternative lines for Bob that meet his needs:
• Line 5 - No conflicts
• Line 7 - No conflicts

[Auto-resolve using priorities] [Manual resolution]
```

**3. Staff Request History:**
```
┌─────────────────────────────────────────┐
│ Jane Smith - Request History            │
├─────────────────────────────────────────┤
│ Priority Score: 120 (High)              │
│                                         │
│ Last 12 months:                         │
│ • Jan 2026: Line 5 → Denied (conflict)  │
│ • Oct 2025: Dates off → Approved        │
│ • Jul 2025: Line 3 → Denied (intern)    │
│                                         │
│ Success rate: 33% (1/3 approved)        │
│ Time since last approval: 4 months      │
└─────────────────────────────────────────┘
```

### Staff Request Page - Show Priority:

```
Your Current Priority: 🟡 MEDIUM (Score: 95)

Based on: 1 approval in the last 12 months

Note: Staff with fewer recent approvals get higher 
priority when conflicts arise.
```

## Storage

Add to `data_storage.py`:

```python
REQUEST_HISTORY_FILE = STORAGE_DIR / "request_history.json"

def save_request_history(history: Dict[str, RequestHistory])
def load_request_history() -> Dict[str, RequestHistory]
```

## Validation Rules to Implement

Currently missing - need to add:

1. **Intern Pairing Check:**
   - Before assigning, check if line already has an intern
   - Block assignment if conflict exists

2. **Line Capacity Check:**
   - Optional: Set max staff per line
   - Prevent overloading popular lines

3. **Award Compliance Check:**
   - Use RosterBoundaryValidator for transitions
   - Already implemented in UI, needs backend enforcement

## Phased Implementation

### Phase 1: Basic Conflict Detection
- Detect when multiple people request same line
- Show warnings in manager UI
- Manual resolution only

### Phase 2: Request Tracking
- Track all requests and outcomes
- Store history
- Calculate priority scores

### Phase 3: Automated Priority Resolution
- Sort requests by priority
- Auto-resolve simple conflicts
- Suggest alternatives for denied requests

### Phase 4: Analytics & Reporting
- Show fairness metrics
- Alert if someone hasn't had approval in X months
- Historical reports

## Benefits

✅ **Fair rotation:** People who get their requests regularly will have lower priority
✅ **Transparency:** Everyone can see why decisions were made
✅ **Reduced manager workload:** Auto-resolution of conflicts
✅ **Better morale:** Staff know they'll get a turn
✅ **Audit trail:** Complete history of all decisions
✅ **Conflict prevention:** Interns won't end up on same line

## Design Decisions (CONFIRMED)

1. **Priority rolls continuously** - No annual reset
2. **No emergency overrides** - Other leave types handle emergencies; this is for projected rosters
3. **All request types weighted equally** - Date requests are really just helping find the best line
4. **No seniority factor** - Fairness based purely on request history
5. **Rare requesters get high priority when they do request** - This is working as intended
6. **LINE TENURE PROTECTION** - Staff have priority to stay on their current line
7. **Line swaps allowed** - Staff can swap lines with mutual consent, bypassing normal priority
