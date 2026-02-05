# Bay & Basin Paramedic Roster System

## Project Overview

Automated roster management system for NSW Ambulance Bay & Basin paramedics. Manages complex 9-day rotating shift patterns (DDNNOOOOO) with Award compliance, request tracking, priority-based conflict resolution, and intelligent intern rotation.

## Current Status

**COMPLETED:**
- Core roster assignment logic
- Request tracking & priority system
- Conflict detection & resolution (logic + UI button on manager page)
- Intern rotation with historical mentor tracking
- UI integration (all 6 pages functional)
- Data persistence (JSON storage)
- Excel export
- Priority display on staff request page
- Conflict detection UI on manager page
- Intern assignment UI on manager page
- Priority-based roster generation (ConflictDetector + InternAssignmentSystem integrated)
- Automatic request approval/denial recording after generation
- Line assignment history tracking after generation
- Intern mentor pairing recording after generation
- Generation log with per-staff assignment reasoning

**TODO:**
- Testing with real Bay & Basin data and verifying outcomes
- Bug fixes and edge case handling

## Architecture

### Core Files

**roster_app.py** (~2180 lines)
- Streamlit web interface
- Pages: Staff Management, Current Roster, Staff Request, Manager, Request History, Line Explorer
- Main entry point: `streamlit run roster_app.py`
- Key functions:
  - `auto_save()` (line ~154)
  - `display_shift_calendar()` (line ~168)
  - `current_roster_page()` (line ~246)
  - `staff_management_page()` (line ~398)
  - `staff_request_page()` (line ~714)
  - `manager_roster_page()` (line ~1132) - roster generation with priority/conflict/intern integration
  - `line_explorer_page()` (line ~1810)
  - `request_history_page()` (line ~1890)
  - `main()` (line ~2020)

**request_history.py** (~391 lines)
- `LineAssignment` dataclass: Tracks line assignments with reasons
- `RequestRecord` dataclass: Individual request with status
- `RequestHistory` class: Complete history for one staff member
- `calculate_priority_score()` (line ~127): Core priority logic
- `update_line_assignment()` (line ~224): Records line changes
- `add_mentor_pairing()` (line ~247): Tracks intern-mentor pairings
- `get_total_shifts_with_mentor()` (line ~283): Total shifts with specific mentor

**conflict_detector.py** (~316 lines)
- `RequestConflict` class: Represents a line conflict
- `InternPairingViolation` class: Two interns on same line
- `ConflictDetector` class: Main detection engine
- `detect_line_conflicts()` (line ~59): Finds all conflicts
- `get_winner()` (line ~21): Determines winner by priority
- `suggest_alternatives()` (line ~164): Alternative line suggestions

**intern_assignment.py** (~399 lines)
- `InternAssignmentSystem` class: Intelligent intern placement
- `assign_interns()` (line ~35): Main assignment entry point
- `_find_best_line_for_intern()` (line ~76): Complex scoring logic
  - Calculates shift overlaps with ALL paramedics (not just same line)
  - Avoids mentors worked with in last 2 rosters
  - Avoids paramedics with 14+ day leave
  - Prioritizes multiple mentor exposure
- `record_intern_pairings()` (line ~228): Records actual shift overlaps
- Only considers rotating roster staff (excludes fixed roster)

**roster_assignment.py** (~541 lines)
- `StaffMember` dataclass: Staff member data model
- `CoverageIssue` dataclass: Coverage problem tracking
- `RosterAssignment` class: Core roster generation engine
- `auto_assign_staff_with_defaults()` (line ~166): Current roster generation (lacks priority/intern logic)
- `get_coverage_for_date()` (line ~216): Calculate coverage
- `check_coverage()` (line ~250): Validate minimum coverage

**roster_lines.py** (~306 lines)
- `RosterLine` class: 9-day rotating line (DDNNOOOOO pattern)
- `RosterLineManager`: Manages all 9 lines
- Date-based shift calculation

**roster_boundary_validator.py** (~231 lines)
- `RosterBoundaryValidator`: Award compliance checking
- Validates line transitions (min rest periods, consecutive day limits)

**data_storage.py** (~374 lines)
- JSON persistence for staff, rosters, settings, request histories
- `save_request_history()` / `load_request_history()`: Request tracking persistence
- Save/load functions for all data types
- Storage location: `./roster_data/`

**excel_export.py** (~309 lines)
- Generates Excel roster with formatting
- Separate sheets for rotating and fixed staff

**fixed_roster_helper.py** (~283 lines)
- Helper functions for fixed roster staff (casuals with custom schedules)

### Test/Demo Files

**demo_roster.py** (~169 lines) - Basic roster demonstration
**test_boundary_violations.py** (~136 lines) - Award compliance testing
**populate_bay_basin.py** (~306 lines) - Loads Bay & Basin staff data
**load_bay_basin.py** (~168 lines) - Alternative data loader

## Import Graph

```
roster_app.py
  -> roster_lines (RosterLine, RosterLineManager)
  -> roster_assignment (RosterAssignment, StaffMember)
  -> roster_boundary_validator (RosterBoundaryValidator)
  -> fixed_roster_helper (create_fixed_roster_*)
  -> data_storage
  -> excel_export (export_roster_to_excel)
  -> request_history (RequestHistory, RequestRecord)
  -> conflict_detector (ConflictDetector)
  -> intern_assignment (InternAssignmentSystem)

conflict_detector.py -> roster_assignment, request_history, roster_lines
intern_assignment.py -> roster_assignment, request_history, roster_lines
roster_assignment.py -> roster_lines, roster_boundary_validator
excel_export.py -> roster_assignment
```

## Key Concepts

### Roster Lines

9-day rotating pattern: **DDNNOOOOO** (2 days, 2 nights, 5 off)

Lines 1-9 start on different days to provide continuous coverage:
- Line 1: Starts Day 1
- Line 2: Starts Day 2
- ... and so on

### Priority System

**Regular Paramedics:** Score = 100 + recency_bonus - approval_penalty + tenure_bonus
- Recency bonus: +5 per month since last approval
- Approval penalty: -10 per approval in last 12 months
- Tenure bonus: +50 (first roster), +25 (second roster), 0 (third+)

**Interns:** Score = 10 + minimal_bonuses (only matters vs other interns)

### Intern Rotation Rules

1. **Low priority** (10-20 range) - never bumps paramedics
2. **Mentor tracking** - tracks shift overlaps with ALL paramedics (not just same line)
3. **Historical avoidance** - avoids mentors with 30+ historical shifts together
4. **Leave awareness** - avoids lines with mentors on long leave (14+ days)
5. **Rotating roster only** - fixed roster staff excluded from tracking

### Line Tenure Protection

Staff get priority to stay on current line:
- First roster: +50 bonus (strong protection)
- Second roster: +25 bonus (moderate protection)
- Third+ roster: 0 bonus (fair game for changes)

### Request Types

1. **No change** - Stay on current line
2. **Specific line** - Request particular line number
3. **Specific dates off** - System finds best matching line
4. **Leave periods** - 21-day blocks (Saturday to Friday)

## Data Models

### StaffMember
```python
@dataclass
class StaffMember:
    name: str
    role: str  # "Paramedic", "Intern", "PT/FTR", "Casual"
    year: str  # e.g., "Para Yr6"
    requested_line: Optional[int] = None
    requested_dates_off: List[datetime] = field(default_factory=list)
    assigned_line: Optional[int] = None
    is_fixed_roster: bool = False
    fixed_schedule: Dict[datetime, str] = field(default_factory=dict)
    leave_periods: List[Tuple[datetime, datetime, str]] = field(default_factory=list)
```

### RequestHistory
```python
@dataclass
class RequestHistory:
    staff_name: str
    total_requests_submitted: int = 0
    total_requests_approved: int = 0
    total_requests_denied: int = 0
    current_line: Optional[int] = None
    rosters_on_current_line: int = 0
    line_history: List[LineAssignment] = field(default_factory=list)
    mentors_worked_with: List[Tuple[str, str, int]] = field(default_factory=list)  # (name, period, shifts)
    interns_worked_with: List[Tuple[str, str]] = field(default_factory=list)
    request_log: List[RequestRecord] = field(default_factory=list)
    priority_score: float = 100.0
```

### RequestRecord
```python
@dataclass
class RequestRecord:
    roster_period: str
    request_date: datetime
    request_type: str  # "line_change", "dates_off", "stay_on_line", "line_swap"
    request_details: dict
    swap_partner: Optional[str] = None
    swap_partner_approved: bool = False
    status: str = "pending"  # "pending", "approved", "denied", "modified", "forced_move"
    approved_date: Optional[datetime] = None
    actual_assignment: Optional[dict] = None
    denial_reason: Optional[str] = None
    manager_notes: Optional[str] = None
    was_forced_move: bool = False
    forced_by: Optional[str] = None
```

## Critical Business Rules

### NSW Ambulance Paramedics Award 2023 Compliance

1. **Minimum rest periods:**
   - 10 hours between shifts
   - 54 hours after 2 consecutive night shifts

2. **Maximum consecutive days:**
   - 6 consecutive working days maximum
   - Must have 2 consecutive days off after nights

3. **Leave requirements:**
   - Annual leave: 21 days (Saturday to Friday)
   - No night shift on Friday before Saturday leave start

4. **Intern rules:**
   - No two interns on same line
   - Interns should work with different mentors each roster
   - Only rotating roster paramedics are mentors (fixed roster excluded)

## Current Staff

13 staff members loaded from `roster_data/staff.json`:
- **Paramedics (9):** Sam Jowett, Shane Orchard, Jenny Richards, Min Wu, Hez Goodsir-Spencer, Joel Pegram, Glenn Chandler, Dave McColl, Briana Car
- **Interns (3):** Oliver Pritchard, Matt Pitt, Diya Arangassery
- **Fixed Roster (1):** Megan Bryant (Thu/Fri pattern)

## Current Workflow

### Staff Request Submission
1. Staff selects their name (`staff_request_page()`)
2. System shows priority scores (stay vs change)
3. Staff sees visual line availability grid (green/red)
4. Staff submits request
5. Request recorded in history with "pending" status

### Manager Roster Generation
1. Manager clicks "Check for Conflicts" (implemented, line ~1165)
2. System shows all conflicts with priorities
3. Manager clicks "Generate Roster" (line ~1474)
4. **[TODO]** System should:
   - Use ConflictDetector to resolve conflicts
   - Use InternAssignmentSystem for interns
   - Record approvals/denials in request histories
   - Update line assignments with reasons

### Roster Generation Flow (Implemented)
**File:** `roster_app.py`, lines ~1474-1694

The "Generate Roster" button runs a 7-step process:

1. **Conflict detection** - `ConflictDetector` finds line conflicts among non-intern rotating staff
2. **Conflict resolution** - Winners get their line by priority; losers get alternative lines via `suggest_alternatives()`
3. **Non-conflict assignment** - Staff with no conflicts get their requested line, best-fit line for date requests, or stay on current line
4. **Intern rotation** - `InternAssignmentSystem.assign_interns()` places interns for mentor diversity; `record_intern_pairings()` tracks shifts
5. **Apply to RosterAssignment** - All final assignments applied via `assign_staff_to_line()`
6. **Record outcomes** - Each staff's pending `RequestRecord` is approved or denied with reason; `update_line_assignment()` tracks line history
7. **Update & save** - `current_roster` updated, `auto_save()` persists everything including request histories

## Running

**Run app:**
```bash
streamlit run roster_app.py
```

**Test individual components:**
```bash
python request_history.py
python conflict_detector.py
python intern_assignment.py
```

**Load Bay & Basin data:**
```bash
python populate_bay_basin.py
```

## Data Storage

**Location:** `./roster_data/` (created automatically)

**Files:**
- `staff.json` - Staff members (currently 13 staff)
- `current_roster.json` - Current line assignments
- `settings.json` - Roster dates (currently Jan 24 - Mar 27, 2026)
- `request_history.json` - Request tracking data (not yet created)

## Common Issues

1. **Imports failing:** All Python files must be in the same directory
2. **Data not persisting:** Check `roster_data/` directory exists and is writable
3. **Interns not rotating:** Ensure `is_fixed_roster=False` for rotating staff
4. **Priorities not showing:** Check request_histories loaded in session_state
5. **Mentor tracking wrong:** Only rotating roster staff should be tracked
6. **Multiple staff on one line:** Lines 8 and 9 currently have two people each - check assignments

## Next Steps

### Priority 1: Testing
- Generate test rosters with real Bay & Basin data
- Verify priorities resolve conflicts correctly
- Check intern rotation produces mentor diversity
- Validate Award compliance (rest periods, consecutive day limits)
- Verify request histories are saved/loaded correctly across sessions

### Priority 2: Edge Cases
- Handle staff with no requests and no current line
- Handle all interns wanting same line
- Handle conflicts with >3 people wanting same line
- Handle interns with leave periods
- Boundary validation for line transitions during generation

## Documentation Files

- `IMPLEMENTATION_COMPLETE.md` - Overall status
- `INTEGRATION_GUIDE.md` - Step-by-step UI integration
- `CURRENT_ROSTER_GUIDE.md` - Current roster page guide
- `SHIFT_TRACKING_UPDATE.md` - Shift overlap tracking
- `INTERN_MENTOR_DISPLAY.md` - UI display rules
- `implementation_status.md` - Implementation status
- `intern_system_summary.md` - Intern system summary
- `request_tracking_proposal.md` - Request tracking proposal
- `ROSTER_SYSTEM_SUMMARY.md` - System summary
- `STREAMLIT_QUICKSTART.md` - Streamlit quickstart

## Context

This system is for NSW Ambulance Bay & Basin region. The user (Sam) works in the NSW Ambulance system and is actively developing this for real-world use. The roster must comply with NSW Ambulance Paramedics Award 2023 requirements.
