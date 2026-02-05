# Paramedic Roster System - Summary

## System Overview

This Python-based roster system manages the DDNNOOOO (9-day) rotating roster pattern for Bay & Basin paramedics, with Award compliance and coverage checking.

## Award Requirements (Operational Ambulance Managers Award)

### HARD CONSTRAINTS - Must Never Violate

1. **Hours of Work**
   - 38 hours/week average over roster cycle
   - Maximum 19 shifts per 28 days (for 8-hour rosters)
   - Maximum shift length: 12h15m (modified) or 12h (standard)

2. **Days Off Requirements**
   - Minimum 2 full days off per week
   - OR minimum 4 full days per fortnight
   - "Working Week" = Saturday to Friday
   - **This prevents working 8+ consecutive days across roster boundaries**

3. **Breaks Between Shifts**
   - Minimum 10 hours between shifts (hard rule)
   - Exception: 8 hours if overtime causes the gap reduction

4. **Days Off Definition**
   - Modified roster: 24 hours clear
   - Non-modified roster: 24 hours + minimum 6 hours buffer

5. **ADO Accrual** (For Non-Modified Rosters)
   - Accrues at 0.4 hours per 8-hour shift
   - Must receive at least 1 ADO per 28 days
   - ADO must be shown on roster
   - Where practicable, ADO should be consecutive with other days off

### OPERATIONAL REQUIREMENTS

6. **Minimize Single Paramedic Rostering**
   - Core rosters should not produce single responders at construction stage
   - This is the PRIMARY operational objective

7. **Hours Balance When Changing Lines**
   - When changing roster lines across periods, must validate:
     - No 7-day window has fewer than 2 days off
     - No 14-day window has fewer than 4 days off
     - Hours still balance to 38/week average

8. **One-Hour Pairing Rule**
   - Formation of dual paramedic response should occur within 1 hour of shift start
   - If pairing takes >1 hour, single officer restricted from deployment

## Roster Pattern: DDNNOOOO

The 9-day rotating cycle:
- **DD**: 2 day shifts (typically 06:45-19:00)
- **NN**: 2 night shifts (typically 18:45-07:00)
- **OOOOO**: 5 days off

### Why 9 Lines?

With a 9-day cycle, there are 9 possible roster lines, each offset by 1 day:

- **Line 1**: DDNNOOOOO (starts Day on Day 1)
- **Line 2**: ODDNNOOOO (starts Day on Day 2)
- **Line 3**: OODDNNOOO (starts Day on Day 3)
- etc.

This ensures continuous coverage with different staff working different parts of the cycle.

## Current System Features

### 1. Roster Line Calculator (`roster_lines.py`)
- Defines 9 rotating roster lines
- Calculates what shift type (D/N/O) falls on any given date
- Finds lines that match requested days off
- Validates Award compliance within a roster period

### 2. Staff Assignment System (`roster_assignment.py`)
- Manages staff assignments to roster lines
- Handles two types of requests:
  - Direct line requests ("I want Line 3")
  - Date requests ("I need these days off") → auto-finds matching lines
- Tracks leave periods (Annual, MCPD, etc.)
- Checks coverage requirements (minimum 2 per shift)
- Generates individual staff schedules

### 3. Roster Boundary Validator (`roster_boundary_validator.py`)
- **CRITICAL FOR AWARD COMPLIANCE**
- Validates that changing roster lines doesn't violate consecutive day rules
- Checks 7-day and 14-day rolling windows across roster boundaries
- Prevents scenarios like working 8 consecutive days across two roster periods

## Potential Violations

### Example 1: Working Too Many Consecutive Days

**INVALID:**
```
Period 1 (Days 25-28): DDDD (work 4 days straight)
Period 2 (Days 1-4):   DDDD (work 4 days straight)
Result: 8 consecutive working days
```

**Award Violation:** Week spanning Days 25-31 has 0 days off (needs minimum 2)

### Example 2: Overtime Creating Violations

**Scenario:** Staff on Line 1 picks up overtime shifts at end of period

```
Normal roster:  DDNNOOOOO
With overtime:  DDNN-DDN- (worked 2 extra day shifts)
Result: 6 consecutive working days (4 roster + 2 overtime)
```

If this crosses into next period where they start with DD again:
- Could result in 8 consecutive days
- Week would have 0 days off = Award violation

### Example 3: Valid Overtime

**Scenario:** Staff on Line 1 picks up ONE overtime shift

```
Normal roster:  DDNNOOOOO
With overtime:  DDNND-OOO (worked 1 extra day shift)
Result: 5 consecutive working days
Days off in week: Still 2 or more = ✅ Compliant
```

## What the System Can Do

### For Staff:
1. Request specific roster lines
2. Request specific days off and see which lines work
3. View their complete schedule including leave
4. See if their requests create any conflicts

### For Managers:
1. Auto-assign staff to lines based on preferences
2. Check if minimum coverage is met (2 per shift)
3. Identify coverage gaps and shortfalls
4. Validate Award compliance before publishing roster
5. Track leave balances and ADO requirements
6. Generate reports on roster performance

### For Organization:
1. Ensure Award compliance across roster boundaries
2. Balance workload across staff fairly
3. Track coverage statistics (min/max/average per shift)
4. Maintain audit trail of roster assignments
5. Export rosters in required format

## Still To Build

### Next Phase:
1. **Streamlit web interface** - Let staff submit requests online
2. **Excel export** - Generate rosters in your current PDF format
3. **Better assignment algorithm** - Optimize coverage when assigning
4. **Conflict resolution** - Handle competing requests
5. **Leave balance tracking** - Integration with leave management

### Future Enhancements:
1. Shift swap functionality
2. Overtime tracking and approval
3. Skills matrix and training tracking
4. Integration with payroll systems
5. Mobile app for roster viewing
6. Notification system for roster changes

## Key Files

```
roster_lines.py                  - Core roster line logic
roster_assignment.py            - Staff assignment & coverage
roster_boundary_validator.py    - Award compliance checking
test_boundary_violations.py     - Test cases for violations
```

## Usage Example

```python
from datetime import datetime
from roster_assignment import RosterAssignment, StaffMember

# Create 4-week roster period
start = datetime(2026, 1, 24)
end = datetime(2026, 2, 20)

roster = RosterAssignment(start, end, min_paramedics_per_shift=2)

# Add staff with requests
staff1 = StaffMember(
    name="Glenn Chandler",
    role="Paramedic",
    year="Para Yr6",
    requested_line=3  # Wants Line 3
)
roster.add_staff(staff1)

staff2 = StaffMember(
    name="Samuel Jowett",
    role="Paramedic",
    year="Para Yr6",
    requested_dates_off=[
        datetime(2026, 1, 27),
        datetime(2026, 1, 28)
    ]  # Needs these days off
)
roster.add_staff(staff2)

# Auto-assign everyone
roster.auto_assign_staff()

# Check coverage
issues = roster.check_coverage()

# Print summary
roster.print_assignment_summary()
roster.print_coverage_report()
```

## Award Compliance Validation

```python
from roster_boundary_validator import RosterBoundaryValidator
from roster_lines import RosterLineManager

manager = RosterLineManager(datetime(2026, 2, 21))
validator = RosterBoundaryValidator()

# Check if transitioning from Line 1 to Line 5 is valid
line_1 = manager.lines[0]
line_5 = manager.lines[4]

is_valid, message = validator.validate_line_transition(
    line_1, 
    line_5, 
    datetime(2026, 2, 21)
)

if not is_valid:
    print(f"❌ Award violation: {message}")
```

## Questions to Resolve

1. **Shift times**: Are B&B1 and B&B2 times always the same, or do they vary?
2. **Part-time staff**: How do we handle staff like Megan Bryant who only work day shifts?
3. **Interns**: Do they count toward the minimum 2 paramedics, or do you need 2 full paramedics?
4. **Leave priorities**: Which takes precedence - Annual leave vs MCPD leave vs roster requests?
5. **Overtime approval**: What's the process for approving overtime that might create boundary issues?

## Next Steps

Let me know which feature you'd like to build next:
1. **Streamlit web interface** for staff requests
2. **Excel export** matching your current roster format
3. **Better assignment algorithm** that optimizes coverage
4. **Command-line tool** for quick roster generation
