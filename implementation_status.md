# Request Tracking System - Implementation Status

## ✅ COMPLETED

### 1. Core Data Structures (`request_history.py`)
- `RequestHistory` class - tracks all requests and line assignments per staff member
- `RequestRecord` class - individual request details  
- `LineAssignment` class - line history with reasons for changes
- **Priority calculation working**:
  - Base score: 100
  - Recency bonus: +5/month since last approval (max 12 months)
  - Approval penalty: -10 per approval in last 12 months
  - **Line tenure bonus: +50 first roster, +25 second roster, 0 after**

### 2. Storage System (`data_storage.py`)
- Added `REQUEST_HISTORY_FILE` path
- `save_request_history()` and `load_request_history()` functions
- Integrated into `clear_all_data()`

### 3. Conflict Detection (`conflict_detector.py`)
- `ConflictDetector` class finds conflicts
- `detect_line_conflicts()` - identifies when multiple staff want same line
- `detect_intern_violations()` - prevents two interns on same line
- `suggest_alternatives()` - recommends other lines
- **Priority-based conflict resolution working**
- Correctly handles "stay on current line" vs "request change"

### 4. Test Results
**Priority calculation test:**
- Jane (1 roster on Line 3, staying): Priority 145 ✅
- Jane (wants to change): Priority 95 ✅  
- Bob (3 rosters, high approvals): Priority 160 ✅

**Conflict resolution test:**
- Bob (current on Line 3, priority 210) beats Jane & Alice (both priority 160) ✅
- System suggests alternatives for losers ✅
- Intern pairing detection works ✅

## 🔨 NEXT STEPS - UI Integration

### Step 3: Update roster_app.py

#### A. Initialize request history system (CRITICAL)
```python
# In main() sidebar, after loading data:
if 'request_histories' not in st.session_state:
    hist_data = data_storage.load_request_history()
    st.session_state.request_histories = {
        name: RequestHistory.from_dict(data) 
        for name, data in hist_data.items()
    }
```

#### B. Staff Request Page - Record requests
When staff submit requests:
```python
# After staff submits request:
history = st.session_state.request_histories.get(staff.name)
if not history:
    history = RequestHistory(staff_name=staff.name)
    st.session_state.request_histories[staff.name] = history

# Create request record
request = RequestRecord(
    roster_period=f"{roster_start.strftime('%b-%Y')}",
    request_date=datetime.now(),
    request_type="line_change" if requested_line else "dates_off",
    request_details={...},
    status="pending"
)
history.add_request(request)

# Save
hist_dict = {name: h.to_dict() for name, h in st.session_state.request_histories.items()}
data_storage.save_request_history(hist_dict)
```

#### C. Manager Page - Conflict Detection & Resolution

Add new section before "Generate Roster":

```python
st.markdown("## ⚠️ Conflict Detection")

if st.button("🔍 Check for Conflicts"):
    detector = ConflictDetector(
        staff_list=st.session_state.staff_list,
        current_roster=st.session_state.current_roster,
        request_histories=st.session_state.request_histories,
        roster_start=st.session_state.roster_start
    )
    
    conflicts = detector.detect_line_conflicts()
    
    if conflicts:
        st.warning(f"Found {len(conflicts)} conflict(s)")
        
        for conflict in conflicts:
            with st.expander(f"⚠️ Line {conflict.line_number} Conflict"):
                # Show requesters with priorities
                st.write("**Requesters:**")
                for staff, priority in conflict.requesters:
                    st.write(f"• {staff.name}: Priority {priority:.1f}")
                
                if conflict.current_occupant:
                    staff, priority = conflict.current_occupant
                    st.write(f"**Current Occupant:**")
                    st.write(f"• {staff.name}: Priority {priority:.1f}")
                
                winner = conflict.get_winner()
                st.success(f"✅ Recommended: {winner.name}")
                
                losers = conflict.get_losers()
                if losers:
                    st.write("**Need alternatives:**")
                    for loser in losers:
                        alts = detector.suggest_alternatives(loser, [conflict.line_number])
                        st.write(f"{loser.name}:")
                        for line_num, reason in alts[:3]:
                            st.write(f"  → Line {line_num}: {reason}")
```

#### D. Manager Page - Approval Workflow

When manager clicks "Generate Roster", after generation:

```python
# After roster.auto_assign_staff_with_defaults():

# Record approvals/denials
for staff in roster.staff:
    if staff.is_fixed_roster:
        continue
    
    history = st.session_state.request_histories.get(staff.name)
    if not history:
        continue
    
    # Find their pending request
    pending = [r for r in history.request_log if r.status == 'pending']
    if not pending:
        continue
    
    latest_request = pending[-1]
    
    # Check if they got what they wanted
    if staff.requested_line and staff.assigned_line == staff.requested_line:
        # Approved!
        history.approve_request(
            len(history.request_log) - 1,
            {'assigned_line': staff.assigned_line}
        )
        history.update_line_assignment(
            new_line=staff.assigned_line,
            roster_period=f"{roster_start.strftime('%b-%Y')}",
            reason="request_approved"
        )
    elif staff.assigned_line != current_roster.get(staff.name, 0):
        # Got moved but didn't request it - forced move
        latest_request.status = 'forced_move'
        latest_request.was_forced_move = True
        history.total_requests_denied += 1
    else:
        # Stayed on current line (either requested or default)
        if staff.requested_line:
            # They requested change but didn't get it
            history.deny_request(
                len(history.request_log) - 1,
                "Higher priority conflict"
            )

# Save updated histories
hist_dict = {name: h.to_dict() for name, h in st.session_state.request_histories.items()}
data_storage.save_request_history(hist_dict)
```

#### E. New Page - Request History

Add new page to view history:

```python
def request_history_page():
    st.markdown("<h1 class='main-header'>📊 Request History</h1>", unsafe_allow_html=True)
    
    # Select staff
    staff_names = sorted([s.name for s in st.session_state.staff_list if not s.is_fixed_roster])
    selected_name = st.selectbox("Select Staff Member", staff_names)
    
    history = st.session_state.request_histories.get(selected_name)
    if not history:
        st.info("No request history for this staff member")
        return
    
    # Show priority score
    current_line = st.session_state.current_roster.get(selected_name, 0)
    priority_stay = history.calculate_priority_score(is_requesting_change=False)
    priority_change = history.calculate_priority_score(is_requesting_change=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Priority (Stay)", f"{priority_stay:.0f}")
    with col2:
        st.metric("Priority (Change)", f"{priority_change:.0f}")
    with col3:
        st.metric("Approval Rate", f"{history.total_requests_approved}/{history.total_requests_submitted}")
    
    # Show line history
    st.markdown("### Line History")
    for assignment in reversed(history.line_history):
        st.write(f"**Line {assignment.line_number}** - {assignment.roster_period}")
        st.caption(f"Reason: {assignment.change_reason}")
    
    # Show request log
    st.markdown("### Request Log")
    for i, request in enumerate(reversed(history.request_log)):
        status_emoji = {
            'approved': '✅',
            'denied': '❌',
            'pending': '⏳',
            'forced_move': '⚠️'
        }.get(request.status, '❓')
        
        with st.expander(f"{status_emoji} {request.roster_period} - {request.request_type}"):
            st.write(f"**Requested:** {request.request_date.strftime('%d/%m/%Y')}")
            st.write(f"**Details:** {request.request_details}")
            st.write(f"**Status:** {request.status}")
            if request.denial_reason:
                st.write(f"**Reason:** {request.denial_reason}")
```

### Step 4: Update roster_assignment.py

Add intern validation and conflict resolution:

```python
def auto_assign_staff_with_conflicts(
    self, 
    current_roster: Dict[str, int],
    request_histories: Dict[str, RequestHistory]
):
    """
    Assign staff using priority-based conflict resolution
    """
    from conflict_detector import ConflictDetector
    
    # Detect conflicts first
    detector = ConflictDetector(
        staff_list=self.staff,
        current_roster=current_roster,
        request_histories=request_histories,
        roster_start=self.roster_start_date
    )
    
    conflicts = detector.detect_line_conflicts()
    
    # Resolve conflicts
    assigned_staff = set()
    
    for conflict in conflicts:
        winner = conflict.get_winner()
        self.assign_staff_to_line(winner, conflict.line_number)
        assigned_staff.add(winner.name)
        
        # Assign losers to alternatives
        losers = conflict.get_losers()
        for loser in losers:
            alternatives = detector.suggest_alternatives(loser, [conflict.line_number])
            if alternatives:
                self.assign_staff_to_line(loser, alternatives[0][0])
                assigned_staff.add(loser.name)
    
    # Assign remaining staff (no conflicts)
    for staff in self.staff:
        if staff.is_fixed_roster or staff.name in assigned_staff:
            continue
        
        if staff.requested_line:
            self.assign_staff_to_line(staff, staff.requested_line)
        else:
            current_line = current_roster.get(staff.name, 0)
            if current_line > 0:
                self.assign_staff_to_line(staff, current_line)
    
    # Check for intern violations
    proposed = {s.name: s.assigned_line for s in self.staff if s.assigned_line}
    violations = detector.detect_intern_violations(proposed)
    
    if violations:
        # Handle intern violations - move one intern
        for violation in violations:
            # Keep first intern, move second
            intern_to_move = violation.interns[1]
            alternatives = detector.suggest_alternatives(intern_to_move, [violation.line_number])
            if alternatives:
                self.assign_staff_to_line(intern_to_move, alternatives[0][0])
```

## 📋 TESTING CHECKLIST

- [ ] Request history saves and loads correctly
- [ ] Priority scores calculate correctly
- [ ] Line tenure protection works
- [ ] Conflict detection finds all conflicts
- [ ] Priority-based resolution works
- [ ] Intern pairing prevention works
- [ ] Alternatives suggested correctly
- [ ] Request approval/denial tracked
- [ ] Line assignment history tracked
- [ ] UI shows conflicts clearly
- [ ] Manager can review priorities
- [ ] Staff can see their priority
- [ ] History page shows all data

## 🚀 FUTURE ENHANCEMENTS

### Line Swap System
- UI for staff to initiate swaps
- Notification system for swap requests
- Mutual consent workflow
- Manager approval of swaps

### Analytics
- Fairness reports (who hasn't had approval in X months)
- Line popularity metrics
- Success rate by staff member
- Historical trends

### Advanced Features
- Batch roster generation (multiple periods at once)
- What-if scenario testing
- Automatic fairness balancing
- Export request history to Excel
