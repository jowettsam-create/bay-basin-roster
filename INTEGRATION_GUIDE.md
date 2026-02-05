# COMPLETE INTEGRATION GUIDE
# All changes needed to integrate request tracking into roster_app.py

## FILES TO COPY TO YOUR PROJECT DIRECTORY:
1. request_history.py
2. conflict_detector.py  
3. intern_assignment.py
4. data_storage.py (updated version)

## CHANGES TO roster_app.py:

### 1. ADD IMPORTS (after line 20):
```python
# Request tracking system
from request_history import RequestHistory, RequestRecord
from conflict_detector import ConflictDetector
from intern_assignment import InternAssignmentSystem
```

### 2. INITIALIZATION (already done above)
- Added request_histories loading
- Updated auto_save function

### 3. UPDATE SIDEBAR (in main() function):

Add after line showing "Current Assignments":
```python
# Show conflicts if any
if st.session_state.request_histories:
    rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
    detector = ConflictDetector(
        staff_list=rotating_staff,
        current_roster=st.session_state.current_roster,
        request_histories=st.session_state.request_histories,
        roster_start=st.session_state.roster_start
    )
    conflicts = detector.detect_line_conflicts()
    if conflicts:
        st.sidebar.markdown(f"**⚠️ Conflicts:** {len(conflicts)}")

# Show intern count
interns = [s for s in st.session_state.staff_list if s.role == "Intern" and not s.is_fixed_roster]
if interns:
    st.sidebar.markdown(f"**👨‍⚕️ Interns:** {len(interns)}")
```

### 4. UPDATE NAVIGATION (in main() function):

Change the page radio to include Request History:
```python
page = st.sidebar.radio(
    "Navigation",
    ["👥 Staff Management", "📅 Current Roster", "🔔 Staff Request", 
     "👔 Manager: Create Roster", "📊 Request History", "🔍 Line Explorer"]
)
```

And in the routing section:
```python
if page == "👥 Staff Management":
    staff_management_page()
elif page == "📅 Current Roster":
    current_roster_page()
elif page == "🔔 Staff Request":
    staff_request_page()
elif page == "👔 Manager: Create Roster":
    manager_roster_page()
elif page == "📊 Request History":
    request_history_page()
else:
    line_explorer_page()
```

### 5. CREATE NEW FUNCTION: request_history_page()

Add this complete function before main():

```python
def request_history_page():
    """Page to view request history and priority scores"""
    st.markdown("<h1 class='main-header'>📊 Request History</h1>", unsafe_allow_html=True)
    
    rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
    
    if not rotating_staff:
        st.info("No rotating roster staff yet")
        return
    
    staff_names = sorted([s.name for s in rotating_staff])
    selected_name = st.selectbox("Select Staff Member", staff_names)
    
    if not selected_name:
        return
    
    selected_staff = next(s for s in rotating_staff if s.name == selected_name)
    history = st.session_state.request_histories.get(selected_name)
    
    if not history:
        history = RequestHistory(staff_name=selected_name)
        st.session_state.request_histories[selected_name] = history
    
    # Update current line if needed
    current_line = st.session_state.current_roster.get(selected_name, 0)
    if history.current_line != current_line and current_line > 0:
        history.current_line = current_line
        if not history.line_history or history.line_history[-1].line_number != current_line:
            history.rosters_on_current_line = 1
    
    # Calculate priorities
    is_intern = selected_staff.role == "Intern"
    priority_stay = history.calculate_priority_score(is_requesting_change=False, staff_role=selected_staff.role)
    priority_change = history.calculate_priority_score(is_requesting_change=True, staff_role=selected_staff.role)
    
    # Show priority scores
    st.markdown("<h2 class='section-header'>Priority Scores</h2>", unsafe_allow_html=True)
    
    if is_intern:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Intern Priority", f"{priority_change:.0f}", help="Interns have low priority - only matters vs other interns")
        with col2:
            success_rate = f"{history.total_requests_approved}/{history.total_requests_submitted}" if history.total_requests_submitted > 0 else "0/0"
            st.metric("Success Rate", success_rate)
        
        st.info("🔵 As an intern, you're assigned based on mentor rotation for maximum learning exposure")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            priority_level = "🟢 High" if priority_stay >= 150 else "🟡 Medium" if priority_stay >= 80 else "🟠 Low"
            st.metric("Priority (Stay)", f"{priority_stay:.0f}", help="Your priority to stay on current line")
            st.caption(priority_level)
        with col2:
            priority_level = "🟢 High" if priority_change >= 150 else "🟡 Medium" if priority_change >= 80 else "🟠 Low"
            st.metric("Priority (Change)", f"{priority_change:.0f}", help="Your priority to change lines")
            st.caption(priority_level)
        with col3:
            success_rate = f"{history.total_requests_approved}/{history.total_requests_submitted}" if history.total_requests_submitted > 0 else "0/0"
            st.metric("Success Rate", success_rate)
        
        if history.rosters_on_current_line < 2:
            st.success(f"✅ Tenure protection active: You've been on Line {current_line} for {history.rosters_on_current_line} roster(s)")
        elif history.rosters_on_current_line == 2:
            st.info(f"ℹ️ Moderate protection: You've been on Line {current_line} for 2 rosters")
        else:
            st.warning(f"⚠️ No tenure protection: You've been on Line {current_line} for {history.rosters_on_current_line}+ rosters")
    
    # Line history
    st.markdown("<h2 class='section-header'>Line Assignment History</h2>", unsafe_allow_html=True)
    
    if history.line_history:
        for assignment in reversed(history.line_history[-5:]):  # Show last 5
            end_str = assignment.end_date.strftime('%d/%m/%Y') if assignment.end_date else "Current"
            st.write(f"**Line {assignment.line_number}** - {assignment.roster_period}")
            st.caption(f"Started: {assignment.start_date.strftime('%d/%m/%Y')} | Ended: {end_str} | Reason: {assignment.change_reason}")
    else:
        st.info("No line history recorded yet")
    
    # Mentor history for interns
    if is_intern and history.mentors_worked_with:
        st.markdown("<h2 class='section-header'>Mentor Rotation History</h2>", unsafe_allow_html=True)
        
        st.write("**Mentors Worked With:**")
        for i, (mentor, period) in enumerate(reversed(history.mentors_worked_with[-5:]), 1):
            if i == 1:
                st.write(f"{i}. {mentor} ({period}) ← Current")
            else:
                st.write(f"{i}. {mentor} ({period})")
    
    # Request log
    st.markdown("<h2 class='section-header'>Request Log</h2>", unsafe_allow_html=True)
    
    if history.request_log:
        for i, request in enumerate(reversed(history.request_log[-10:]), 1):  # Show last 10
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
                
                if request.status == 'approved':
                    st.write(f"**Approved:** {request.approved_date.strftime('%d/%m/%Y') if request.approved_date else 'N/A'}")
                    if request.actual_assignment:
                        st.write(f"**Assigned:** {request.actual_assignment}")
                
                if request.denial_reason:
                    st.write(f"**Denial Reason:** {request.denial_reason}")
                
                if request.was_forced_move:
                    st.write(f"**⚠️ Forced Move** - Moved by: {request.forced_by}")
                
                if request.manager_notes:
                    st.write(f"**Manager Notes:** {request.manager_notes}")
    else:
        st.info("No requests recorded yet")
```

### 6. UPDATE staff_request_page() - Add Priority Display

At the beginning of staff_request_page(), after getting selected_staff, add:

```python
# Get or create request history
history = st.session_state.request_histories.get(selected_name)
if not history:
    history = RequestHistory(staff_name=selected_name)
    st.session_state.request_histories[selected_name] = history

# Update current line info
if history.current_line != current_line and current_line > 0:
    history.current_line = current_line
    history.rosters_on_current_line = 1

# Calculate and show priority
is_intern = selected_staff.role == "Intern"
priority_stay = history.calculate_priority_score(is_requesting_change=False, staff_role=selected_staff.role)
priority_change = history.calculate_priority_score(is_requesting_change=True, staff_role=selected_staff.role)

# Show priority box
if is_intern:
    st.info(f"""
    **Role:** {selected_staff.role}  
    **Current Line:** {'Line ' + str(current_line) if current_line > 0 else 'Not assigned'}  
    **Your Priority:** 🔵 {priority_change:.0f} (Intern - rotation based)
    
    ℹ️ As an intern, you're in a rotation program. The system will assign you to work with different paramedics each roster for learning.
    """)
    
    # Show mentor history
    if history.mentors_worked_with:
        st.write("**Previous Mentors:**")
        for mentor, period in history.mentors_worked_with[-3:]:
            st.write(f"• {mentor} ({period})")
else:
    st.info(f"""
    **Role:** {selected_staff.role}  
    **Current Line:** {'Line ' + str(current_line) if current_line > 0 else 'Not assigned'}
    
    **Your Priority Scores:**
    • To STAY on Line {current_line}: {'🟢' if priority_stay >= 150 else '🟡'} {priority_stay:.0f} {'(High - tenure protection)' if history.rosters_on_current_line < 2 else '(Medium)' if history.rosters_on_current_line == 2 else ''}
    • To CHANGE lines: {'🟢' if priority_change >= 150 else '🟡' if priority_change >= 80 else '🟠'} {priority_change:.0f}
    
    **Last approval:** {history._get_months_since_last_approval()} months ago  
    **Success rate:** {history.total_requests_approved}/{history.total_requests_submitted}
    """)
```

### 7. UPDATE staff_request_page() - Record Requests

In the form submission section, after updating staff member's request, add:

```python
# Record the request in history
roster_period = f"{st.session_state.roster_start.strftime('%b-%Y')}"

request_details = {}
if request_type == "Specific Roster Line":
    request_details = {'requested_line': requested_line}
    req_type = 'line_change'
elif request_type == "Specific Days Off":
    request_details = {'requested_dates': [d.strftime('%d/%m/%Y') for d in requested_dates]}
    req_type = 'dates_off'
else:
    request_details = {'stay_on_line': current_line}
    req_type = 'stay_on_line'

request_record = RequestRecord(
    roster_period=roster_period,
    request_date=datetime.now(),
    request_type=req_type,
    request_details=request_details,
    status='pending'
)

history.add_request(request_record)
st.session_state.request_histories[selected_name] = history
```

### 8. ADD CONFLICT DETECTION TO manager_roster_page()

Add this section BEFORE the "Generate Roster" button:

```python
st.markdown("<h2 class='section-header'>⚠️ Conflict Detection & Resolution</h2>", unsafe_allow_html=True)

if st.button("🔍 Check for Conflicts"):
    rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
    
    if rotating_staff:
        detector = ConflictDetector(
            staff_list=rotating_staff,
            current_roster=st.session_state.current_roster,
            request_histories=st.session_state.request_histories,
            roster_start=st.session_state.roster_start
        )
        
        conflicts = detector.detect_line_conflicts()
        
        if conflicts:
            st.warning(f"⚠️ Found {len(conflicts)} conflict(s)")
            
            for conflict in conflicts:
                with st.expander(f"⚠️ Line {conflict.line_number} Conflict"):
                    st.write("**Requesters:**")
                    for staff, priority in conflict.requesters:
                        priority_level = "🟢 High" if priority >= 150 else "🟡 Medium" if priority >= 80 else "🟠 Low"
                        st.write(f"• {staff.name}: Priority {priority:.0f} {priority_level}")
                    
                    if conflict.current_occupant:
                        staff, priority = conflict.current_occupant
                        priority_level = "🟢 High" if priority >= 150 else "🟡 Medium"
                        st.write("**Current Occupant:**")
                        st.write(f"• {staff.name}: Priority {priority:.0f} {priority_level}")
                    
                    winner = conflict.get_winner()
                    st.success(f"✅ Recommended: {winner.name}")
                    
                    losers = conflict.get_losers()
                    if losers:
                        st.write("**Alternative assignments needed:**")
                        for loser in losers:
                            alts = detector.suggest_alternatives(loser, [conflict.line_number])
                            st.write(f"{loser.name}:")
                            for line_num, reason in alts[:3]:
                                st.write(f"  → Line {line_num}: {reason}")
        else:
            st.success("✅ No conflicts detected - all requests are compatible")
    else:
        st.info("No rotating roster staff to check")

st.markdown("---")
```

### 9. ADD INTERN SECTION TO manager_roster_page()

Add after the conflict detection section:

```python
st.markdown("<h2 class='section-header'>👨‍⚕️ Intern Assignments (Rotation System)</h2>", unsafe_allow_html=True)

interns = [s for s in st.session_state.staff_list if s.role == "Intern" and not s.is_fixed_roster]

if interns:
    st.info("ℹ️ Interns are assigned using mentor rotation logic for maximum learning exposure")
    
    # Show current intern placements if available
    for intern in interns:
        current_line = st.session_state.current_roster.get(intern.name, 0)
        history = st.session_state.request_histories.get(intern.name, RequestHistory(staff_name=intern.name))
        
        with st.expander(f"{intern.name} - {'Line ' + str(current_line) if current_line > 0 else 'Not assigned'}"):
            if current_line > 0:
                # Find mentor
                mentor = None
                for para in st.session_state.staff_list:
                    if para.role == "Paramedic" and not para.is_fixed_roster:
                        para_line = st.session_state.current_roster.get(para.name, 0)
                        if para_line == current_line:
                            mentor = para.name
                            break
                
                if mentor:
                    st.write(f"**Current Mentor:** {mentor}")
                    if history.has_worked_with_mentor(mentor, within_rosters=1):
                        st.warning("⚠️ Same mentor as last roster")
                    else:
                        st.success("✅ New mentor pairing")
                else:
                    st.warning("⚠️ No paramedic mentor on this line")
            
            if history.mentors_worked_with:
                st.write("**Rotation History:**")
                for mentor, period in history.mentors_worked_with[-3:]:
                    st.write(f"• {mentor} ({period})")
else:
    st.info("No interns in current roster")

st.markdown("---")
```

### 10. UPDATE ROSTER GENERATION

IMPORTANT: This goes in the "Generate Roster" button section.  
This is the most complex change - see separate file "roster_generation_update.py" for complete code.

## TESTING CHECKLIST:
- [ ] App loads without errors
- [ ] Request histories load from file
- [ ] Priority scores calculate correctly
- [ ] Conflict detection shows conflicts
- [ ] Request history page displays data
- [ ] Requests get recorded when submitted
- [ ] Auto-save includes request histories
- [ ] Intern rotation tracking works
- [ ] Sidebar shows conflict count
- [ ] All pages accessible from navigation

## FILES DELIVERED:
- request_history.py
- conflict_detector.py
- intern_assignment.py
- data_storage.py (updated)
- roster_app.py (partially updated - needs manual completion)
- This integration guide
