"""
Paramedic Roster Management System
Streamlit Web Interface
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd

from roster_lines import RosterLine, RosterLineManager
from roster_assignment import RosterAssignment, StaffMember, CoverageAnalyzer
from roster_boundary_validator import RosterBoundaryValidator
from fixed_roster_helper import (
    create_fixed_roster_from_days,
    create_fixed_roster_staff,
    create_fixed_roster_from_dates
)
import google_sheets_storage as data_storage
from excel_export import export_roster_to_excel

# Request tracking system
from request_history import RequestHistory, RequestRecord, LineAssignment
from conflict_detector import ConflictDetector
from intern_assignment import InternAssignmentSystem


def rebuild_line_histories_from_roster_history(request_histories: Dict[str, RequestHistory],
                                                roster_history: List[dict]) -> Dict[str, RequestHistory]:
    """
    Rebuild line_history for all staff based on historical roster data.
    This ensures new staff members have proper tenure tracking even if they
    were added via the Roster History page.

    Args:
        request_histories: Current request histories dict
        roster_history: List of approved roster entries from storage

    Returns:
        Updated request_histories dict with populated line histories
    """
    if not roster_history:
        return request_histories

    # Sort roster history by start date (oldest first)
    sorted_history = sorted(
        roster_history,
        key=lambda x: x.get('start_date', '9999-99-99')
    )

    # Track each staff member's line history
    # Structure: {staff_name: [(period, line_number, start_date), ...]}
    staff_line_history: Dict[str, List[tuple]] = {}

    for entry in sorted_history:
        period = entry.get('period', '')
        start_date_str = entry.get('start_date', '')
        assignments = entry.get('assignments', {})

        for staff_name, line_number in assignments.items():
            if line_number == 0:  # Skip unassigned
                continue

            if staff_name not in staff_line_history:
                staff_line_history[staff_name] = []

            staff_line_history[staff_name].append((period, line_number, start_date_str))

    # Now update request histories based on this data
    for staff_name, history_entries in staff_line_history.items():
        # Get or create request history
        if staff_name not in request_histories:
            request_histories[staff_name] = RequestHistory(staff_name=staff_name)

        history = request_histories[staff_name]

        # Clear existing line_history if we have roster history data
        # (roster history is the source of truth)
        if history_entries:
            # Rebuild line_history from roster history
            history.line_history = []

            previous_line = None
            rosters_on_line = 0

            for period, line_number, start_date_str in history_entries:
                # Parse start date
                try:
                    start_date = datetime.fromisoformat(start_date_str)
                except:
                    start_date = datetime.now()

                # Add to line history
                assignment = LineAssignment(
                    roster_period=period,
                    line_number=line_number,
                    start_date=start_date,
                    change_reason="approved_roster"
                )
                history.line_history.append(assignment)

                # Track tenure on current line
                if line_number == previous_line:
                    rosters_on_line += 1
                else:
                    rosters_on_line = 1
                    previous_line = line_number

            # Set current line info based on most recent entry
            if history_entries:
                latest_period, latest_line, _ = history_entries[-1]
                history.current_line = latest_line
                history.rosters_on_current_line = rosters_on_line

    return request_histories

# Page config
st.set_page_config(
    page_title="Bay & Basin Roster System",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    .shift-day {
        background-color: rgba(255, 193, 7, 0.25);
        border: 2px solid #ffc107;
        padding: 5px;
        border-radius: 3px;
        display: inline-block;
        margin: 2px;
        font-weight: bold;
    }
    .shift-night {
        background-color: rgba(13, 110, 253, 0.25);
        border: 2px solid #0d6efd;
        padding: 5px;
        border-radius: 3px;
        display: inline-block;
        margin: 2px;
        font-weight: bold;
    }
    .shift-off {
        background-color: rgba(25, 135, 84, 0.25);
        border: 2px solid #198754;
        padding: 5px;
        border-radius: 3px;
        display: inline-block;
        margin: 2px;
        font-weight: bold;
    }
    .shift-leave {
        background-color: rgba(155, 89, 182, 0.25);
        border: 2px solid #9b59b6;
        padding: 5px;
        border-radius: 3px;
        display: inline-block;
        margin: 2px;
        font-weight: bold;
    }
    .violation-box {
        background-color: rgba(220, 53, 69, 0.15);
        border-left: 4px solid #dc3545;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
        color: inherit;
    }
    .success-box {
        background-color: rgba(40, 167, 69, 0.15);
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
        color: inherit;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state with auto-load
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    
    # Try to load saved data
    if data_storage.data_exists():
        staff_list, current_roster, roster_start, roster_end, prev_end = data_storage.load_all()
        st.session_state.staff_list = staff_list
        st.session_state.current_roster = current_roster
        st.session_state.roster_start = roster_start
        st.session_state.roster_end = roster_end
        st.session_state.previous_roster_end = prev_end
    else:
        # Defaults - 9-week rosters (63 days)
        st.session_state.staff_list = []
        st.session_state.current_roster = {}
        # Current roster: 24 Jan - 27 Mar 2026 (9 weeks = 63 days)
        st.session_state.roster_start = datetime(2026, 1, 24)  # Saturday Jan 24
        st.session_state.roster_end = datetime(2026, 3, 27)    # Friday Mar 27
        st.session_state.previous_roster_end = datetime(2026, 1, 23)  # Previous ended Fri Jan 23

    # Calculate projected roster dates (next 9-week period after current)
    st.session_state.projected_roster_start = st.session_state.roster_end + timedelta(days=1)
    st.session_state.projected_roster_end = st.session_state.projected_roster_start + timedelta(days=62)  # 63 days total
    
    # Load roster history first
    try:
        st.session_state.roster_history = data_storage.load_roster_history()
    except Exception:
        st.session_state.roster_history = []

    # Load request histories
    hist_data = data_storage.load_request_history()
    st.session_state.request_histories = {
        name: RequestHistory.from_dict(data)
        for name, data in hist_data.items()
    }

    # Rebuild line histories from roster history to ensure proper tenure tracking
    # This ensures new staff members have their line_history populated correctly
    st.session_state.request_histories = rebuild_line_histories_from_roster_history(
        st.session_state.request_histories,
        st.session_state.roster_history
    )

    st.session_state.roster = None

# Ensure all required keys exist
if 'roster' not in st.session_state:
    st.session_state.roster = None
if 'staff_list' not in st.session_state:
    st.session_state.staff_list = []
if 'roster_start' not in st.session_state:
    st.session_state.roster_start = datetime(2026, 1, 24)
if 'roster_end' not in st.session_state:
    st.session_state.roster_end = datetime(2026, 3, 27)
if 'current_roster' not in st.session_state:
    st.session_state.current_roster = {}
if 'previous_roster_end' not in st.session_state:
    st.session_state.previous_roster_end = datetime(2026, 1, 23)
if 'request_histories' not in st.session_state:
    st.session_state.request_histories = {}
if 'roster_history' not in st.session_state:
    try:
        st.session_state.roster_history = data_storage.load_roster_history()
        # Also rebuild line histories when roster_history is loaded
        st.session_state.request_histories = rebuild_line_histories_from_roster_history(
            st.session_state.request_histories,
            st.session_state.roster_history
        )
    except Exception:
        st.session_state.roster_history = []

# Calculate projected roster dates if not already set
if 'projected_roster_start' not in st.session_state or 'projected_roster_end' not in st.session_state:
    st.session_state.projected_roster_start = st.session_state.roster_end + timedelta(days=1)
    st.session_state.projected_roster_end = st.session_state.projected_roster_start + timedelta(days=62)


def auto_save():
    """Auto-save data after changes"""
    data_storage.save_all(
        st.session_state.staff_list,
        st.session_state.current_roster,
        st.session_state.roster_start,
        st.session_state.roster_end,
        st.session_state.previous_roster_end
    )

    # Save request histories
    hist_dict = {name: h.to_dict() for name, h in st.session_state.request_histories.items()}
    data_storage.save_request_history(hist_dict)

def display_shift_calendar(schedule: List[tuple], title: str):
    """Display a visual calendar of shifts"""
    st.markdown(f"**{title}**")
    
    # Calculate summary stats
    total_days = len(schedule)
    day_shifts = sum(1 for _, shift in schedule if shift == 'D')
    night_shifts = sum(1 for _, shift in schedule if shift == 'N')
    leave_days = sum(1 for _, shift in schedule if shift == 'LEAVE')
    off_days = sum(1 for _, shift in schedule if shift == 'O')
    
    # Show summary
    if leave_days > 0:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Days", total_days)
        with col2:
            st.metric("☀️ Day Shifts", day_shifts)
        with col3:
            st.metric("🌙 Night Shifts", night_shifts)
        with col4:
            st.metric("🏖️ Leave Days", leave_days)
        with col5:
            st.metric("⭕ Days Off", off_days)
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Days", total_days)
        with col2:
            st.metric("☀️ Day Shifts", day_shifts)
        with col3:
            st.metric("🌙 Night Shifts", night_shifts)
        with col4:
            st.metric("⭕ Days Off", off_days)
    
    st.markdown("---")
    
    # Group by weeks
    weeks = []
    current_week = []
    
    for i, (date, shift) in enumerate(schedule):
        if date.weekday() == 5 and current_week:  # Saturday - start new week
            weeks.append(current_week)
            current_week = []
        current_week.append((date, shift))
    
    if current_week:
        weeks.append(current_week)
    
    # Display weeks with week numbers
    for week_num, week in enumerate(weeks, 1):
        st.markdown(f"**Week {week_num}**")
        cols = st.columns(7)
        for i, (date, shift) in enumerate(week):
            with cols[i]:
                shift_class = {
                    'D': 'shift-day',
                    'N': 'shift-night',
                    'O': 'shift-off',
                    'LEAVE': 'shift-leave'
                }.get(shift, 'shift-off')
                
                shift_label = {
                    'D': '☀️ Day',
                    'N': '🌙 Night',
                    'O': '⭕ Off',
                    'LEAVE': '🏖️ Leave'
                }.get(shift, shift)
                
                st.markdown(
                    f"<div style='text-align: center;'>"
                    f"<small>{date.strftime('%a %d')}</small><br>"
                    f"<span class='{shift_class}'>{shift_label}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

def current_roster_page():
    """Page to view and set the current roster (what lines people are currently on)"""
    st.markdown("<h1 class='main-header'>📅 Current Roster</h1>", unsafe_allow_html=True)
    
    st.info("These are the line assignments for the **current active roster**. When generating the projected roster, staff will default to staying on their current line unless they request a change.")

    # Show current roster period
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Current Roster Start:** {st.session_state.roster_start.strftime('%d/%m/%Y')}")
    with col2:
        st.write(f"**Current Roster End:** {st.session_state.roster_end.strftime('%d/%m/%Y')}")
    with col3:
        st.write(f"**Projected Roster:** {st.session_state.projected_roster_start.strftime('%d/%m/%Y')} - {st.session_state.projected_roster_end.strftime('%d/%m/%Y')}")
    
    st.markdown("<h2 class='section-header'>Current Line Assignments</h2>", unsafe_allow_html=True)
    
    # Get all rotating roster staff (not fixed)
    rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
    
    if not rotating_staff:
        st.warning("No rotating roster staff added yet. Add staff on the 'Staff Request' page first.")
        return
    
    # Group by current line
    current_assignments = {}
    for i in range(10):  # 0 = unassigned, 1-9 = lines
        current_assignments[i] = []
    
    for staff in rotating_staff:
        current_line = st.session_state.current_roster.get(staff.name, 0)
        current_assignments[current_line].append(staff)
    
    # Sort each group alphabetically
    for line_num in current_assignments:
        current_assignments[line_num] = sorted(current_assignments[line_num], key=lambda s: s.name)
    
    # Display current assignments
    st.markdown("### Current Assignments by Line")
    
    # Unassigned staff
    if current_assignments[0]:
        with st.expander(f"⚠️ Unassigned ({len(current_assignments[0])} staff)", expanded=True):
            st.warning("These staff need to be assigned to a line")
            for staff in current_assignments[0]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{staff.name}** ")
                with col2:
                    new_line = st.selectbox(
                        "Assign to line",
                        options=[1, 2, 3, 4, 5, 6, 7, 8, 9],
                        key=f"assign_{staff.name}"
                    )
                    if st.button("Set", key=f"set_{staff.name}"):
                        st.session_state.current_roster[staff.name] = new_line
                        st.rerun()
    
    # Assigned staff by line
    for line_num in range(1, 10):
        if current_assignments[line_num]:
            with st.expander(f"📋 Line {line_num} ({len(current_assignments[line_num])} staff)"):
                for staff in current_assignments[line_num]:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{staff.name}** ")
                    with col2:
                        if st.button("Change Line", key=f"change_{staff.name}"):
                            st.session_state.current_roster[staff.name] = 0  # Unassign
                            st.rerun()
    
    # Bulk assignment section
    st.markdown("<h2 class='section-header'>Quick Assignment</h2>", unsafe_allow_html=True)
    
    with st.form("bulk_assign_form"):
        st.write("Assign multiple staff to lines at once:")
        
        assignments = {}
        # Sort staff alphabetically for bulk assignment
        sorted_rotating_staff = sorted(rotating_staff, key=lambda s: s.name)
        
        for staff in sorted_rotating_staff:
            current_line = st.session_state.current_roster.get(staff.name, 0)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"{staff.name} ")
            with col2:
                assignments[staff.name] = st.selectbox(
                    "Line",
                    options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                    index=current_line,
                    format_func=lambda x: "Unassigned" if x == 0 else f"Line {x}",
                    key=f"bulk_{staff.name}"
                )
        
        if st.form_submit_button("Save All Assignments", type="primary"):
            for name, line in assignments.items():
                st.session_state.current_roster[name] = line
            
            # Auto-save
            auto_save()
            
            st.success("✅ All assignments saved!")
            st.rerun()
    
    # Show visual calendar of current roster
    if st.session_state.current_roster:
        st.markdown("<h2 class='section-header'>Current Roster Calendar</h2>", unsafe_allow_html=True)
        
        # Create a roster assignment to show the current state
        temp_roster = RosterAssignment(
            st.session_state.previous_roster_end - timedelta(days=27),
            st.session_state.previous_roster_end,
            min_paramedics_per_shift=2
        )
        
        # Add staff with their current lines
        for staff in rotating_staff:
            current_line = st.session_state.current_roster.get(staff.name, 0)
            if current_line > 0:
                temp_staff = StaffMember(
                    name=staff.name,
                    role=staff.role,
                    year=staff.year,
                    assigned_line=current_line
                )
                temp_roster.add_staff(temp_staff)
        
        # Show coverage for the last week of previous roster
        st.write("**Coverage for last week of previous roster:**")
        
        last_week_start = st.session_state.previous_roster_end - timedelta(days=6)
        coverage_data = []
        
        for i in range(7):
            date = last_week_start + timedelta(days=i)
            coverage = temp_roster.get_coverage_for_date(date)
            coverage_data.append({
                'Date': date.strftime('%a %d/%m'),
                'Day Shift': coverage['D'],
                'Night Shift': coverage['N']
            })
        
        df = pd.DataFrame(coverage_data)
        st.dataframe(df, width="stretch", hide_index=True)


def staff_management_page():
    """Page to manage all staff - add, edit, remove"""
    st.markdown("<h1 class='main-header'>👥 Staff Management</h1>", unsafe_allow_html=True)
    
    st.info("Manage all staff at Bay & Basin station. Add new staff, edit details, or remove staff who have left.")
    
    # Summary stats
    col1, col2, col3 = st.columns(3)
    
    total_staff = len(st.session_state.staff_list)
    rotating = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
    fixed = [s for s in st.session_state.staff_list if s.is_fixed_roster]
    
    with col1:
        st.metric("Total Staff", total_staff)
    with col2:
        st.metric("Rotating Roster", len(rotating))
    with col3:
        st.metric("Fixed/Casual", len(fixed))
    
    # Tabs for different views
    tab1, tab2 = st.tabs(["📋 All Staff", "➕ Add New Staff"])
    
    with tab1:
        # View and edit all staff
        st.markdown("### All Staff Members")
        
        if not st.session_state.staff_list:
            st.warning("No staff added yet. Use the 'Add New Staff' tab to add staff members.")
        else:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                filter_type = st.selectbox(
                    "Filter by type",
                    ["All", "Rotating Roster Only", "Fixed/Casual Only"]
                )
            with col2:
                filter_role = st.selectbox(
                    "Filter by role",
                    ["All", "Paramedic", "Intern", "PT/FTR", "Casual"]
                )
            
            # Filter staff list
            filtered_staff = st.session_state.staff_list
            if filter_type == "Rotating Roster Only":
                filtered_staff = [s for s in filtered_staff if not s.is_fixed_roster]
            elif filter_type == "Fixed/Casual Only":
                filtered_staff = [s for s in filtered_staff if s.is_fixed_roster]
            
            if filter_role != "All":
                filtered_staff = [s for s in filtered_staff if s.role == filter_role]
            
            # Sort alphabetically by name
            filtered_staff = sorted(filtered_staff, key=lambda s: s.name)
            
            # Display staff in a table-like format
            for i, staff in enumerate(filtered_staff):
                with st.expander(f"{'📌' if staff.is_fixed_roster else '🔄'} {staff.name} ", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Role:** {staff.role}")
                        st.write(f"")
                        st.write(f"**Type:** {'Fixed Roster' if staff.is_fixed_roster else 'Rotating Roster'}")
                        
                        if not staff.is_fixed_roster:
                            current_line = st.session_state.current_roster.get(staff.name, 0)
                            if current_line > 0:
                                st.write(f"**Current Line:** Line {current_line}")
                            else:
                                st.write("**Current Line:** Not assigned")
                    
                    with col2:
                        if staff.leave_periods:
                            st.write("**Leave:**")
                            for start, end, leave_type in staff.leave_periods:
                                st.write(f"  • {leave_type}: {start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}")
                        
                        if staff.is_fixed_roster and staff.fixed_schedule:
                            # Show first week pattern
                            dates = sorted([d for d in staff.fixed_schedule.keys() if d >= st.session_state.roster_start])[:7]
                            if dates:
                                st.write("**Fixed Schedule (first week):**")
                                pattern = []
                                for date in dates:
                                    shift = staff.fixed_schedule.get(date, 'O')
                                    pattern.append(f"{date.strftime('%a')}: {shift}")
                                st.write(", ".join(pattern))
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"✏️ Edit", key=f"edit_{i}"):
                            st.session_state.editing_staff = staff.name
                            st.rerun()
                    
                    with col2:
                        if not staff.is_fixed_roster:
                            if st.button(f"🔄 Change Line", key=f"change_line_{i}"):
                                st.session_state.changing_line_for = staff.name
                                st.rerun()
                    
                    with col3:
                        if st.button(f"🗑️ Remove", key=f"remove_{i}"):
                            # Confirm removal
                            st.session_state.confirm_remove = staff.name
                            st.rerun()
                    
                    # Inline editing
                    if st.session_state.get('editing_staff') == staff.name:
                        st.markdown("---")
                        st.markdown("**Edit Staff Details:**")
                        
                        with st.form(f"edit_form_{i}"):
                            new_name = st.text_input("Name", value=staff.name)
                            new_role = st.selectbox("Role", ["Paramedic", "Intern", "PT/FTR", "Casual"], 
                                                   index=["Paramedic", "Intern", "PT/FTR", "Casual"].index(staff.role))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Save Changes"):
                                    # Update staff
                                    old_name = staff.name
                                    staff.name = new_name
                                    staff.role = new_role
                                    
                                    # Update current roster if name changed
                                    if old_name != new_name and old_name in st.session_state.current_roster:
                                        st.session_state.current_roster[new_name] = st.session_state.current_roster.pop(old_name)
                                    
                                    # Auto-save
                                    auto_save()
                                    
                                    st.session_state.editing_staff = None
                                    st.success(f"✅ Updated {new_name}")
                                    st.rerun()
                            
                            with col2:
                                if st.form_submit_button("❌ Cancel"):
                                    st.session_state.editing_staff = None
                                    st.rerun()
                    
                    # Inline line changing
                    if st.session_state.get('changing_line_for') == staff.name:
                        st.markdown("---")
                        st.markdown("**Change Current Line:**")
                        
                        current_line = st.session_state.current_roster.get(staff.name, 0)
                        new_line = st.selectbox(
                            "Select new line",
                            options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                            index=current_line,
                            format_func=lambda x: "Unassigned" if x == 0 else f"Line {x}",
                            key=f"new_line_{i}"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 Update Line", key=f"save_line_{i}"):
                                st.session_state.current_roster[staff.name] = new_line
                                
                                # Auto-save
                                auto_save()
                                
                                st.session_state.changing_line_for = None
                                st.success(f"✅ {staff.name} assigned to {'Line ' + str(new_line) if new_line > 0 else 'Unassigned'}")
                                st.rerun()
                        
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_line_{i}"):
                                st.session_state.changing_line_for = None
                                st.rerun()
                    
                    # Confirm removal
                    if st.session_state.get('confirm_remove') == staff.name:
                        st.markdown("---")
                        st.warning(f"⚠️ Are you sure you want to remove **{staff.name}**?")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Remove", key=f"confirm_yes_{i}", type="primary"):
                                # Remove from staff list
                                st.session_state.staff_list.remove(staff)
                                # Remove from current roster
                                if staff.name in st.session_state.current_roster:
                                    del st.session_state.current_roster[staff.name]
                                
                                # Auto-save
                                auto_save()
                                
                                st.session_state.confirm_remove = None
                                st.success(f"✅ Removed {staff.name}")
                                st.rerun()
                        
                        with col2:
                            if st.button("❌ Cancel", key=f"confirm_no_{i}"):
                                st.session_state.confirm_remove = None
                                st.rerun()
    
    with tab2:
        # Add new staff
        st.markdown("### Add New Staff Member")

        st.markdown("**Basic Information:**")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", placeholder="e.g., John Smith", key="add_staff_name")
        with col2:
            role = st.selectbox("Role", ["Paramedic", "Intern", "PT/FTR", "Casual"], key="add_staff_role")

        # Fixed roster option - OUTSIDE form so it triggers immediate rerun
        is_fixed = st.checkbox("Fixed/Casual roster (works specific days)", key="add_staff_is_fixed")

        fixed_params = None
        current_line = 0

        if is_fixed:
            st.markdown("**Fixed Roster Pattern:**")

            fixed_type = st.radio(
                "Schedule type",
                ["Specific days of week", "Repeating pattern"],
                key="add_staff_fixed_type"
            )

            if fixed_type == "Specific days of week":
                col1, col2, col3 = st.columns(3)
                working_days = []

                with col1:
                    if st.checkbox("Monday", key="add_mon"): working_days.append("Monday")
                    if st.checkbox("Tuesday", key="add_tue"): working_days.append("Tuesday")
                    if st.checkbox("Wednesday", key="add_wed"): working_days.append("Wednesday")

                with col2:
                    if st.checkbox("Thursday", key="add_thu"): working_days.append("Thursday")
                    if st.checkbox("Friday", key="add_fri"): working_days.append("Friday")

                with col3:
                    if st.checkbox("Saturday", key="add_sat"): working_days.append("Saturday")
                    if st.checkbox("Sunday", key="add_sun"): working_days.append("Sunday")

                shift_type = st.radio("Shift type", ["Day shifts", "Night shifts"], key="add_shift")
                shift_code = 'D' if shift_type == "Day shifts" else 'N'

                fixed_params = {'type': 'days', 'working_days': working_days, 'shift_type': shift_code}

            else:  # Repeating pattern
                pattern = st.text_input(
                    "Pattern (D=Day, N=Night, O=Off)",
                    placeholder="e.g., DDDDOOO",
                    key="add_pattern"
                )
                fixed_params = {'type': 'pattern', 'pattern': pattern.upper() if pattern else ''}

        else:
            # Current line assignment (for rotating staff)
            st.markdown("**Current Line Assignment:**")
            current_line = st.selectbox(
                "Assign to line",
                options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                format_func=lambda x: "Unassigned" if x == 0 else f"Line {x}",
                key="add_staff_line"
            )

        # Submit button
        if st.button("➕ Add Staff Member", type="primary", use_container_width=True):
            if not name:
                st.error("❌ Please enter a name")
            elif is_fixed and fixed_params and fixed_params['type'] == 'days' and not fixed_params['working_days']:
                st.error("❌ Please select at least one working day")
            elif is_fixed and fixed_params and fixed_params['type'] == 'pattern' and not fixed_params.get('pattern'):
                st.error("❌ Please enter a pattern")
            else:
                # Create staff member
                if is_fixed and fixed_params:
                    if fixed_params['type'] == 'days':
                        new_staff = create_fixed_roster_from_days(
                            name=name,
                            role=role,
                            working_days=fixed_params['working_days'],
                            shift_type=fixed_params['shift_type'],
                            roster_start=st.session_state.roster_start,
                            roster_end=st.session_state.roster_end
                        )
                    else:
                        new_staff = create_fixed_roster_staff(
                            name=name,
                            role=role,
                            schedule_pattern=fixed_params['pattern'],
                            roster_start=st.session_state.roster_start,
                            roster_end=st.session_state.roster_end
                        )
                else:
                    new_staff = StaffMember(
                        name=name,
                        role=role
                    )

                # Add to list
                st.session_state.staff_list.append(new_staff)

                # Set current line for rotating staff
                if not is_fixed:
                    st.session_state.current_roster[name] = current_line

                # Auto-save
                auto_save()

                st.success(f"✅ Added {name}!")
                st.rerun()


def staff_request_page():
    """Page for staff to submit roster requests"""
    st.markdown("<h1 class='main-header'>🚑 Staff Roster Request</h1>", unsafe_allow_html=True)

    # Display projected roster period
    st.info(f"""
    **Making request for Projected Roster Period:**
    {st.session_state.projected_roster_start.strftime('%d %b %Y')} - {st.session_state.projected_roster_end.strftime('%d %b %Y')}
    _(Current roster: {st.session_state.roster_start.strftime('%d %b %Y')} - {st.session_state.roster_end.strftime('%d %b %Y')})_
    """)

    if not st.session_state.staff_list:
        st.warning("⚠️ No staff in the system yet. Please add staff in the 'Staff Management' page first.")
        return
    
    # Get rotating roster staff only (fixed roster can't request lines)
    rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
    
    if not rotating_staff:
        st.warning("⚠️ No rotating roster staff in the system. Add staff in the 'Staff Management' page.")
        return
    
    # Staff selection and request type OUTSIDE form for immediate updates
    st.markdown("<h2 class='section-header'>Select Staff Member</h2>", unsafe_allow_html=True)
    
    # Dropdown to select staff - sorted alphabetically
    staff_names = sorted([s.name for s in rotating_staff])
    selected_name = st.selectbox(
        "Who is submitting this request?",
        options=staff_names,
        help="Select your name from the list",
        key="staff_selector"
    )
    
    # Get the selected staff member
    selected_staff = next(s for s in rotating_staff if s.name == selected_name)
    
    # Show their current details
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Role:** {selected_staff.role}")
    with col2:
        current_line = st.session_state.current_roster.get(selected_name, 0)
        if current_line > 0:
            st.info(f"**Current Line:** Line {current_line}")
        else:
            st.warning("**Current Line:** Not assigned")
    
    # Get or create request history
    history = st.session_state.request_histories.get(selected_name)
    if not history:
        history = RequestHistory(staff_name=selected_name)
        st.session_state.request_histories[selected_name] = history

    # Update current line info in history
    if history.current_line != current_line and current_line > 0:
        history.current_line = current_line
        if not history.line_history or history.line_history[-1].line_number != current_line:
            history.rosters_on_current_line = 1

    # Calculate and show priority
    is_intern = selected_staff.role == "Intern"
    priority_stay = history.calculate_priority_score(is_requesting_change=False, staff_role=selected_staff.role)
    priority_change = history.calculate_priority_score(is_requesting_change=True, staff_role=selected_staff.role)

    # Show priority box
    st.markdown("<h2 class='section-header'>Your Priority Status</h2>", unsafe_allow_html=True)

    if is_intern:
        st.info(f"""
**Role:** {selected_staff.role}
**Current Line:** {'Line ' + str(current_line) if current_line > 0 else 'Not assigned'}
**Your Priority:** 🔵 {priority_change:.0f} (Intern - rotation based)

ℹ️ As an intern, you're in a rotation program. The system will assign you to work with different paramedics each roster for learning exposure.
        """)

        # Show mentor history
        if history.mentors_worked_with:
            st.write("**Previous Mentors:**")
            for mentor, period, shifts in history.mentors_worked_with[-3:]:
                current_marker = " ← Current" if (mentor, period, shifts) == history.mentors_worked_with[-1] else ""
                st.write(f"• {mentor} ({period}) - {shifts} shifts{current_marker}")
    else:
        # Create priority display
        months_since = history._get_months_since_last_approval()
        success_rate = f"{history.total_requests_approved}/{history.total_requests_submitted}" if history.total_requests_submitted > 0 else "0/0"

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
            st.metric("Success Rate", success_rate)
            st.caption(f"Last approval: {months_since} months ago")

        # Tenure protection message - check for new staff (no line_history)
        if not history.line_history:
            st.success(f"✅ New staff - maximum tenure protection (first roster)")
        elif history.rosters_on_current_line <= 1:
            st.success(f"✅ Tenure protection active: First/second roster on Line {current_line}")
        elif history.rosters_on_current_line == 2:
            st.info(f"ℹ️ Moderate protection: You've been on Line {current_line} for 2 rosters")
        else:
            st.warning(f"⚠️ No tenure protection: You've been on Line {current_line} for {history.rosters_on_current_line}+ rosters")

    st.markdown("<h2 class='section-header'>Leave Period</h2>", unsafe_allow_html=True)
    
    # Check leave BEFORE request type so we can use it in line validation
    has_leave = st.checkbox("I have approved leave during this roster period", key="has_leave_check")
    
    temp_leave_periods = []
    if has_leave:
        st.info("📅 Annual leave should be a 3-week block starting on Saturday and ending on Friday")
        st.warning("⚠️ Lines with a night shift on the Friday before your leave starts will be marked as unavailable")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            leave_start = st.date_input("Leave Start Date (should be Saturday)", key="leave_start_preview")
        with col2:
            leave_end = st.date_input("Leave End Date (should be Friday)", key="leave_end_preview")
        with col3:
            leave_type = st.selectbox("Leave Type", ["Annual", "MCPD Leave", "Sick Leave", "Other"], key="leave_type_preview")
        
        # Validate leave dates
        leave_start_dt = datetime.combine(leave_start, datetime.min.time())
        leave_end_dt = datetime.combine(leave_end, datetime.min.time())
        
        # Check if it's a Saturday start
        if leave_start_dt.weekday() != 5:
            st.warning(f"⚠️ Leave starts on {leave_start_dt.strftime('%A')} - annual leave typically starts on Saturday")
        
        # Check if it's a Friday end
        if leave_end_dt.weekday() != 4:
            st.warning(f"⚠️ Leave ends on {leave_end_dt.strftime('%A')} - annual leave typically ends on Friday")
        
        # Check if it's 3 weeks (21 days)
        leave_duration = (leave_end_dt - leave_start_dt).days + 1
        if leave_duration != 21:
            st.warning(f"⚠️ Leave duration is {leave_duration} days - annual leave is typically 21 days (3 weeks)")
        
        temp_leave_periods = [(leave_start_dt, leave_end_dt, leave_type)]
    
    st.markdown("<h2 class='section-header'>Request Type</h2>", unsafe_allow_html=True)
    
    request_type = st.radio(
        "What would you like to request?",
        ["No change (stay on current line)", "Specific Roster Line", "Specific Days Off"],
        help="Select 'No change' if you're happy staying on your current line",
        key="request_type_selector"
    )
    
    # Line selection (outside form so buttons work)
    requested_line = None
    requested_dates = []

    if request_type == "Specific Roster Line":
        # Check line validity based on constraints
        current_line = st.session_state.current_roster.get(selected_name, 0)

        # Get validation info for each line
        line_validation_info = {}

        if current_line > 0:
            try:
                from roster_boundary_validator import RosterBoundaryValidator
                validator = RosterBoundaryValidator()
                manager = RosterLineManager(st.session_state.roster_start)
                current_line_obj = manager.lines[current_line - 1]

                for new_line_num in range(1, 10):
                    if new_line_num == current_line:
                        line_validation_info[new_line_num] = {"valid": True, "reason": "Current line"}
                    else:
                        new_line_obj = manager.lines[new_line_num - 1]
                        is_valid, message = validator.validate_line_transition(
                            current_line_obj,
                            new_line_obj,
                            st.session_state.roster_start
                        )
                        line_validation_info[new_line_num] = {"valid": is_valid, "reason": message}
            except ImportError:
                for line_num in range(1, 10):
                    line_validation_info[line_num] = {"valid": True, "reason": ""}
        else:
            for line_num in range(1, 10):
                line_validation_info[line_num] = {"valid": True, "reason": ""}

        # Check for intern-to-intern conflicts
        if selected_staff.role == "Intern":
            intern_count_by_line = {i: 0 for i in range(1, 10)}
            for other_staff in st.session_state.staff_list:
                if other_staff.role == "Intern" and other_staff.name != selected_name:
                    other_current_line = st.session_state.current_roster.get(other_staff.name, 0)
                    if other_current_line > 0:
                        intern_count_by_line[other_current_line] += 1

            for line_num, intern_count in intern_count_by_line.items():
                if intern_count > 0 and line_validation_info[line_num]["valid"]:
                    line_validation_info[line_num] = {
                        "valid": False,
                        "reason": f"Another intern is already on this line"
                    }

        # Check for night shift on Friday before Saturday leave
        if temp_leave_periods:
            manager = RosterLineManager(st.session_state.roster_start)

            for leave_start, leave_end, leave_type in temp_leave_periods:
                if leave_start.weekday() == 5:
                    friday_before = leave_start - timedelta(days=1)

                    for line_num in range(1, 10):
                        if not line_validation_info[line_num]["valid"]:
                            continue

                        line = manager.lines[line_num - 1]
                        shift_on_friday = line.get_shift_type(friday_before)

                        if shift_on_friday == 'N':
                            line_validation_info[line_num] = {
                                "valid": False,
                                "reason": f"Night shift on {friday_before.strftime('%d/%m')} before leave starts"
                            }

        # Initialize selected line in session state
        if 'selected_request_line' not in st.session_state:
            st.session_state.selected_request_line = None

        # Display clickable line buttons
        st.markdown("**Select a Roster Line:**")

        valid_lines = [ln for ln, info in line_validation_info.items() if info["valid"]]

        if not valid_lines:
            st.error("No lines are available. This may be due to Award constraints or intern pairing rules.")
        else:
            cols = st.columns(3)
            for i, line_num in enumerate(range(1, 10)):
                with cols[i % 3]:
                    validation = line_validation_info[line_num]
                    is_selected = (st.session_state.selected_request_line == line_num)

                    if validation["valid"]:
                        # Build button label with reason
                        if is_selected:
                            label = f"✅ Line {line_num} — Selected"
                        elif validation["reason"]:
                            label = f"🟢 Line {line_num} — {validation['reason']}"
                        else:
                            label = f"🟢 Line {line_num}"

                        if st.button(
                            label,
                            key=f"select_line_{line_num}",
                            use_container_width=True,
                            type="primary" if is_selected else "secondary"
                        ):
                            st.session_state.selected_request_line = line_num
                            st.rerun()
                    else:
                        # Unavailable — disabled button with reason
                        reason = validation['reason'] if validation['reason'] else "Unavailable"
                        st.button(
                            f"🔴 Line {line_num} — {reason}",
                            key=f"select_line_{line_num}",
                            use_container_width=True,
                            disabled=True
                        )

            requested_line = st.session_state.selected_request_line

            if requested_line and requested_line not in valid_lines:
                st.session_state.selected_request_line = None
                requested_line = None

    # Form for submit button (and date inputs for days-off requests)
    with st.form("staff_request_form"):

        if request_type == "Specific Days Off":
            st.info("Select the dates you need off. The system will find which roster lines give you those days.")

            num_dates = st.number_input("How many dates do you need off?", min_value=1, max_value=10, value=2)

            cols = st.columns(min(num_dates, 3))
            for i in range(num_dates):
                with cols[i % 3]:
                    date = st.date_input(
                        f"Date {i+1}",
                        value=st.session_state.roster_start + timedelta(days=i),
                        key=f"date_{i}"
                    )
                    requested_dates.append(datetime.combine(date, datetime.min.time()))

        submitted = st.form_submit_button("Submit Request", type="primary", use_container_width=True)

        if submitted:
            # Validate line selection
            if request_type == "Specific Roster Line" and not requested_line:
                st.error("Please select a line above before submitting.")
                st.stop()

            # Clear the line selection from session state after submit
            if request_type == "Specific Roster Line":
                st.session_state.pop('selected_request_line', None)

            # Update the existing staff member's request
            selected_staff.requested_line = requested_line if request_type == "Specific Roster Line" else None
            selected_staff.requested_dates_off = requested_dates if request_type == "Specific Days Off" else []
            
            # Update leave periods from the checkbox above
            if temp_leave_periods:
                selected_staff.leave_periods = temp_leave_periods
            
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
            
            # Auto-save
            auto_save()
            
            if request_type == "No change (stay on current line)":
                st.success(f"✅ Request recorded for {selected_name}: Stay on current line (Line {current_line})")
            elif request_type == "Specific Roster Line":
                st.success(f"✅ Request submitted for {selected_name}: Line {requested_line}")
            else:
                st.success(f"✅ Request submitted for {selected_name}!")
                
                # Show what lines match their request
                if requested_dates:
                    st.markdown("<h3 class='section-header'>Lines That Match Your Request</h3>", unsafe_allow_html=True)
                    
                    manager = RosterLineManager(st.session_state.roster_start)
                    matching_lines = manager.find_matching_lines(requested_dates)
                    ranked_lines = manager.rank_lines_by_fit(requested_dates)
                    
                    if matching_lines:
                        st.success(f"✅ {len(matching_lines)} roster line(s) give you ALL requested days off:")
                        for line in matching_lines:
                            st.write(f"• Line {line.line_number}")
                    else:
                        st.warning("⚠️ No single line gives you all requested days off. Here are the best options:")
                        
                        for line, conflicts in ranked_lines[:3]:
                            if conflicts == 0:
                                st.write(f"✅ Line {line.line_number}: Perfect match")
                            else:
                                st.write(f"⚠️ Line {line.line_number}: {conflicts} conflict(s)")


def manager_roster_page():
    """Page for managers to create and approve rosters"""
    st.markdown("<h1 class='main-header'>📋 Manager: Create Roster</h1>", unsafe_allow_html=True)

    # Display roster periods
    st.info(f"""
    **Generating roster for Projected Period:**
    {st.session_state.projected_roster_start.strftime('%d %b %Y')} - {st.session_state.projected_roster_end.strftime('%d %b %Y')}
    _(Current roster: {st.session_state.roster_start.strftime('%d %b %Y')} - {st.session_state.roster_end.strftime('%d %b %Y')} - cannot be changed)_
    """)

    # Roster period settings
    with st.expander("⚙️ Current Roster Period (Read-Only)", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.text_input("Current Roster Start", value=st.session_state.roster_start.strftime('%d %b %Y'), disabled=True)

        with col2:
            st.text_input("Current Roster End", value=st.session_state.roster_end.strftime('%d %b %Y'), disabled=True)

    # Coverage settings
    cov_col1, cov_col2 = st.columns(2)
    with cov_col1:
        min_coverage = st.number_input(
            "Minimum Paramedics per Shift",
            min_value=1,
            max_value=10,
            value=2
        )
    with cov_col2:
        max_coverage = st.number_input(
            "Maximum Paramedics per Shift",
            min_value=1,
            max_value=10,
            value=4
        )
    
    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 1: HARD RULES (Must never be violated)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<h2 class='section-header'>🚫 Hard Rule Violations</h2>", unsafe_allow_html=True)
    st.caption("These rules cannot be broken - the system will block generation if violated")

    if st.button("🔍 Check Hard Rules", key="check_hard_rules"):
        hard_violations = []
        rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
        interns = [s for s in rotating_staff if s.role == "Intern"]

        # Check 1: Two interns on same line
        intern_lines = {}
        for intern in interns:
            line = st.session_state.current_roster.get(intern.name, 0)
            if line > 0:
                if line not in intern_lines:
                    intern_lines[line] = []
                intern_lines[line].append(intern.name)

        for line_num, intern_names in intern_lines.items():
            if len(intern_names) > 1:
                hard_violations.append({
                    'type': 'intern_pairing',
                    'line': line_num,
                    'details': f"Line {line_num}: Multiple interns ({', '.join(intern_names)}) - interns cannot work together"
                })

        # Check 2: Friday night shift before Saturday leave
        from roster_lines import RosterLineManager as RLM
        line_manager = RLM(st.session_state.projected_roster_start)
        for staff in rotating_staff:
            if staff.leave_periods:
                staff_line = st.session_state.current_roster.get(staff.name, 0)
                if staff_line > 0:
                    line_obj = line_manager.lines[staff_line - 1]
                    for leave_start, leave_end, leave_type in staff.leave_periods:
                        # Check if leave starts on Saturday
                        if leave_start.weekday() == 5:  # Saturday
                            friday_before = leave_start - timedelta(days=1)
                            shift_on_friday = line_obj.get_shift_type(friday_before)
                            if shift_on_friday == 'N':
                                hard_violations.append({
                                    'type': 'friday_night_leave',
                                    'staff': staff.name,
                                    'line': staff_line,
                                    'details': f"{staff.name} (Line {staff_line}): Night shift on {friday_before.strftime('%d/%m')} before leave starts {leave_start.strftime('%d/%m')}"
                                })

        # Display results
        if hard_violations:
            st.error(f"🚫 Found {len(hard_violations)} hard rule violation(s) - MUST be fixed before generating roster")
            for violation in hard_violations:
                if violation['type'] == 'intern_pairing':
                    st.warning(f"👥 **Intern Pairing:** {violation['details']}")
                elif violation['type'] == 'friday_night_leave':
                    st.warning(f"🌙 **Award Violation:** {violation['details']}")
        else:
            st.success("✅ No hard rule violations - roster can be generated")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 2: REQUEST CONFLICTS (Resolved by priority)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<h2 class='section-header'>⚠️ Request Conflicts (Priority-Based)</h2>", unsafe_allow_html=True)
    st.caption("When multiple people request the same line, priority determines who gets it")

    if st.button("🔍 Check Request Conflicts", key="check_request_conflicts"):
        rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
        non_intern_staff = [s for s in rotating_staff if s.role != "Intern"]

        if non_intern_staff:
            detector = ConflictDetector(
                staff_list=non_intern_staff,
                current_roster=st.session_state.current_roster,
                request_histories=st.session_state.request_histories,
                roster_start=st.session_state.roster_start
            )

            conflicts = detector.detect_line_conflicts()

            if conflicts:
                st.warning(f"⚠️ Found {len(conflicts)} request conflict(s) - will be resolved by priority")

                for conflict in conflicts:
                    with st.expander(f"⚠️ Line {conflict.line_number} - Multiple Requests"):
                        st.write("**Requesting to move here:**")
                        if conflict.requesters:
                            for staff, priority in conflict.requesters:
                                priority_level = "🟢 High" if priority >= 150 else "🟡 Medium" if priority >= 80 else "🟠 Low"
                                st.write(f"• {staff.name}: Priority {priority:.0f} {priority_level}")
                        else:
                            st.write("• (none)")

                        if conflict.current_occupant:
                            staff, priority = conflict.current_occupant
                            priority_level = "🟢 High" if priority >= 150 else "🟡 Medium" if priority >= 80 else "🟠 Low"
                            st.write("**Currently on this line (wants to stay):**")
                            st.write(f"• {staff.name}: Priority {priority:.0f} {priority_level}")

                        winner = conflict.get_winner()
                        st.success(f"✅ Winner: {winner.name}")

                        losers = conflict.get_losers()
                        if losers:
                            st.write("**Will be assigned alternatives:**")
                            for loser in losers:
                                alts = detector.suggest_alternatives(loser, [conflict.line_number])
                                if alts:
                                    st.write(f"• {loser.name} → Line {alts[0][0]} ({alts[0][1]})")
                                else:
                                    st.write(f"• {loser.name} → (will find available line)")
            else:
                st.success("✅ No request conflicts - all line requests are compatible")
        else:
            st.info("No rotating roster staff (excluding interns) to check")
    
    st.markdown("---")
    
    # Intern Assignment Section
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
                    # Find ALL mentors this intern works with (not just same line)
                    from roster_lines import RosterLineManager
                    line_manager = RosterLineManager(st.session_state.roster_start)
                    
                    # Generate intern's schedule
                    intern_line_obj = line_manager.lines[current_line - 1]
                    intern_schedule = []
                    current_date = st.session_state.roster_start
                    while current_date <= st.session_state.roster_end:
                        shift = intern_line_obj.get_shift_type(current_date)
                        # Check for intern's leave
                        if intern.leave_periods:
                            for leave_start, leave_end, _ in intern.leave_periods:
                                if leave_start <= current_date <= leave_end:
                                    shift = 'LEAVE'
                                    break
                        intern_schedule.append((current_date, shift))
                        current_date += timedelta(days=1)
                    
                    # Check overlap with ALL paramedics
                    mentors_with_shifts = []
                    paramedics = [s for s in st.session_state.staff_list if s.role == "Paramedic" and not s.is_fixed_roster]
                    
                    for para in paramedics:
                        para_line = st.session_state.current_roster.get(para.name, 0)
                        if para_line == 0:
                            continue
                        
                        # Generate para's schedule
                        para_line_obj = line_manager.lines[para_line - 1]
                        para_schedule = []
                        current_date = st.session_state.roster_start
                        while current_date <= st.session_state.roster_end:
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
                                if para_shift == intern_shift:
                                    shared_shifts += 1
                        
                        if shared_shifts > 0:
                            mentors_with_shifts.append((para.name, para_line, shared_shifts))
                    
                    # Display mentors
                    if mentors_with_shifts:
                        # Sort by shift count (most shifts first)
                        mentors_with_shifts.sort(key=lambda x: x[2], reverse=True)
                        
                        # Check if they share a line with anyone (teaming rule)
                        same_line_mentors = [m for m in mentors_with_shifts if m[1] == current_line]
                        other_line_mentors = [m for m in mentors_with_shifts if m[1] != current_line]
                        
                        if same_line_mentors:
                            # On same line = teaming
                            st.write(f"**Teamed Mentor(s) (Line {current_line}):**")
                            for mentor_name, mentor_line, shifts in same_line_mentors:
                                if history.has_worked_with_mentor(mentor_name, within_rosters=1):
                                    st.write(f"• {mentor_name}: {shifts} shifts ⚠️ Repeat from last roster")
                                else:
                                    st.write(f"• {mentor_name}: {shifts} shifts ✅ New pairing")
                        
                        if other_line_mentors:
                            # Different lines = cross-exposure
                            st.write(f"**Cross-Line Exposure:**")
                            for mentor_name, mentor_line, shifts in other_line_mentors:
                                st.write(f"• {mentor_name} (Line {mentor_line}): {shifts} shifts")
                        
                        # Overall assessment
                        total_mentors = len(mentors_with_shifts)
                        if total_mentors >= 2:
                            st.success(f"✅ Working with {total_mentors} paramedics (varied exposure)")
                        elif total_mentors == 1:
                            st.info(f"ℹ️ Working with 1 paramedic")
                    else:
                        st.warning("⚠️ No paramedic mentors found for this assignment")
                
                if history.mentors_worked_with:
                    st.write("**Rotation History:**")
                    for mentor, period, shifts in history.mentors_worked_with[-3:]:
                        st.write(f"• {mentor} ({period}) - {shifts} shifts")
    else:
        st.info("No interns in current roster")
    
    st.markdown("---")
    
    # Show current requests
    st.markdown("<h2 class='section-header'>Current Staff Requests</h2>", unsafe_allow_html=True)
    
    if st.session_state.staff_list:
        # Separate fixed and rotating roster staff
        fixed_staff = [s for s in st.session_state.staff_list if s.is_fixed_roster]
        rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
        
        if fixed_staff:
            st.markdown("#### 📌 Fixed Roster Staff")
            for i, staff in enumerate(fixed_staff):
                with st.expander(f"{staff.name}  - Fixed Schedule"):
                    st.write(f"**Role:** {staff.role}")
                    
                    # Show their schedule pattern
                    if staff.fixed_schedule:
                        # Sample first 7 days
                        dates = sorted(staff.fixed_schedule.keys())[:7]
                        schedule_preview = []
                        for date in dates:
                            shift = staff.fixed_schedule[date]
                            shift_label = {'D': 'Day', 'N': 'Night', 'O': 'Off'}.get(shift, '-')
                            schedule_preview.append(f"{date.strftime('%a')}: {shift_label}")
                        
                        st.write("**First week:**")
                        st.write(", ".join(schedule_preview))
                    
                    # Show leave if any with individual delete buttons
                    if staff.leave_periods:
                        st.write("**Leave Periods:**")
                        for leave_idx, (start, end, leave_type) in enumerate(staff.leave_periods):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"• {leave_type}: {start.strftime('%d/%m')} - {end.strftime('%d/%m')}")
                            with col2:
                                if st.button("🗑️", key=f"clear_leave_fixed_{i}_{leave_idx}", help="Delete this leave period"):
                                    staff.leave_periods.pop(leave_idx)
                                    auto_save()
                                    st.success(f"✅ Cleared leave period")
                                    st.rerun()
                    
                    st.markdown("---")
                    
                    # Remove button with confirmation
                    if st.button(f"❌ Remove {staff.name} from Roster", key=f"remove_fixed_{i}"):
                        st.session_state[f'confirm_remove_fixed_{i}'] = True
                        st.rerun()
                    
                    # Confirmation
                    if st.session_state.get(f'confirm_remove_fixed_{i}', False):
                        st.warning(f"⚠️ Really remove **{staff.name}** from the roster?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Remove", key=f"confirm_yes_fixed_{i}"):
                                st.session_state.staff_list.remove(staff)
                                st.session_state[f'confirm_remove_fixed_{i}'] = False
                                auto_save()
                                st.success(f"✅ Removed {staff.name}")
                                st.rerun()
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_remove_fixed_{i}"):
                                st.session_state[f'confirm_remove_fixed_{i}'] = False
                                st.rerun()
        
        if rotating_staff:
            st.markdown("#### 🔄 Rotating Roster Staff")
            for i, staff in enumerate(rotating_staff):
                with st.expander(f"{staff.name} "):
                    # Basic info
                    st.write(f"**Role:** {staff.role}")
                    current_line = st.session_state.current_roster.get(staff.name, 0)
                    if current_line > 0:
                        st.write(f"**Current Line:** Line {current_line}")
                    else:
                        st.write(f"**Current Line:** Not assigned")
                    
                    st.markdown("---")
                    
                    # Line change request
                    if staff.requested_line:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Line Change Request:** Line {staff.requested_line}")
                        with col2:
                            if st.button("🗑️", key=f"clear_line_req_{i}", help="Delete line change request"):
                                staff.requested_line = None
                                auto_save()
                                st.success(f"✅ Cleared line request")
                                st.rerun()
                    
                    # Dates off request
                    if staff.requested_dates_off:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Dates Off Request:**")
                            for date in staff.requested_dates_off:
                                st.write(f"• {date.strftime('%a %d/%m/%Y')}")
                        with col2:
                            st.write("")  # Spacing
                            if st.button("🗑️", key=f"clear_dates_req_{i}", help="Delete dates off request"):
                                staff.requested_dates_off = []
                                auto_save()
                                st.success(f"✅ Cleared dates request")
                                st.rerun()
                    
                    # Leave periods
                    if staff.leave_periods:
                        st.write(f"**Leave Periods:**")
                        for leave_idx, (start, end, leave_type) in enumerate(staff.leave_periods):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"• {leave_type}: {start.strftime('%d/%m')} - {end.strftime('%d/%m')}")
                            with col2:
                                if st.button("🗑️", key=f"clear_leave_{i}_{leave_idx}", help="Delete this leave period"):
                                    staff.leave_periods.pop(leave_idx)
                                    auto_save()
                                    st.success(f"✅ Cleared leave period")
                                    st.rerun()
                    
                    # Show message if no requests
                    if not staff.requested_line and not staff.requested_dates_off and not staff.leave_periods:
                        st.info("ℹ️ No requests or leave scheduled")
                    
                    st.markdown("---")
                    
                    # Remove staff member button - with confirmation
                    if st.button(f"❌ Remove {staff.name} from Roster", key=f"remove_rotating_{i}", help="Remove this staff member entirely"):
                        st.session_state[f'confirm_remove_staff_{i}'] = True
                        st.rerun()
                    
                    # Confirmation for staff removal
                    if st.session_state.get(f'confirm_remove_staff_{i}', False):
                        st.warning(f"⚠️ Really remove **{staff.name}** from the roster entirely?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Remove", key=f"confirm_yes_{i}"):
                                st.session_state.staff_list.remove(staff)
                                if staff.name in st.session_state.current_roster:
                                    del st.session_state.current_roster[staff.name]
                                st.session_state[f'confirm_remove_staff_{i}'] = False
                                auto_save()
                                st.success(f"✅ Removed {staff.name}")
                                st.rerun()
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_remove_{i}"):
                                st.session_state[f'confirm_remove_staff_{i}'] = False
                                st.rerun()
    else:
        st.info("No staff requests yet. Use the 'Staff Request' page to add requests.")
    
    # Generate roster button
    if st.button("🔄 Generate Roster", type="primary", width="stretch"):
        if not st.session_state.staff_list:
            st.error("❌ No staff to roster! Add some staff requests first.")
        else:
            with st.spinner("Generating roster with priority-based assignment..."):
                # Create roster object for PROJECTED period
                roster = RosterAssignment(
                    st.session_state.projected_roster_start,
                    st.session_state.projected_roster_end,
                    min_paramedics_per_shift=min_coverage,
                    max_paramedics_per_shift=max_coverage
                )

                # Add all staff
                for staff in st.session_state.staff_list:
                    roster.add_staff(staff)

                # Separate staff categories
                rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
                interns = [s for s in rotating_staff if s.role == "Intern"]
                non_intern_rotating = [s for s in rotating_staff if s.role != "Intern"]

                roster_period = f"{st.session_state.projected_roster_start.strftime('%b')}-{st.session_state.projected_roster_end.strftime('%b %Y')}"

                # Track final assignments: staff_name -> line_number
                final_assignments = {}
                # Track generation notes for display
                generation_log = []
                # Track requests denied specifically for coverage
                coverage_denials = 0

                # ── Step 0: Build baseline coverage ──
                # Everyone starts on their current line as a baseline
                baseline_assignments = {}
                for staff in rotating_staff:
                    cur = st.session_state.current_roster.get(staff.name, 0)
                    if cur > 0:
                        baseline_assignments[staff.name] = cur

                cov_line_manager = RosterLineManager(st.session_state.projected_roster_start)
                coverage_analyzer = CoverageAnalyzer(
                    staff_list=st.session_state.staff_list,
                    line_manager=cov_line_manager,
                    roster_start=st.session_state.projected_roster_start,
                    roster_end=st.session_state.projected_roster_end,
                    min_coverage=min_coverage,
                    max_coverage=max_coverage
                )
                # Working assignments built up incrementally
                working_assignments = dict(baseline_assignments)

                # ── Step 1: Detect conflicts among non-intern rotating staff ──
                detector = ConflictDetector(
                    staff_list=non_intern_rotating,
                    current_roster=st.session_state.current_roster,
                    request_histories=st.session_state.request_histories,
                    roster_start=st.session_state.projected_roster_start
                )
                conflicts = detector.detect_line_conflicts()

                # Build sets of staff handled by conflict resolution
                conflict_handled = set()
                conflicted_lines = set()

                for conflict in conflicts:
                    conflicted_lines.add(conflict.line_number)
                    winner = conflict.get_winner()
                    losers = conflict.get_losers()

                    # Assign the winner (priority earned; coverage issues addressed via loser placement)
                    working_assignments[winner.name] = conflict.line_number
                    final_assignments[winner.name] = conflict.line_number
                    conflict_handled.add(winner.name)
                    generation_log.append(f"Line {conflict.line_number}: {winner.name} wins (priority)")

                    # Handle losers - find coverage-safe alternatives
                    for loser in losers:
                        conflict_handled.add(loser.name)
                        current_line = st.session_state.current_roster.get(loser.name, 0)
                        unavailable = [conflict.line_number] + [l for l in final_assignments.values()]
                        alternatives = detector.suggest_alternatives(loser, unavailable)

                        best_alt = None
                        best_delta = float('inf')

                        # Try each suggested alternative, prefer coverage-safe ones
                        for alt_line, reason in alternatives:
                            from_line = current_line if current_line > 0 else 0
                            result = coverage_analyzer.evaluate_move(working_assignments, loser.name, from_line, alt_line)
                            if result['delta'] <= 0:
                                best_alt = alt_line
                                best_delta = 0
                                break
                            elif result['delta'] < best_delta:
                                best_delta = result['delta']
                                best_alt = alt_line

                        # Staying on current line might be safest for coverage
                        if current_line > 0 and best_delta > 0:
                            best_alt = current_line
                            generation_log.append(f"Line {current_line}: {loser.name} (kept for coverage, lost conflict on Line {conflict.line_number})")
                            coverage_denials += 1
                        elif best_alt:
                            generation_log.append(f"Line {best_alt}: {loser.name} (moved from conflict on Line {conflict.line_number})")
                        else:
                            # Fallback: use coverage-ranked lines
                            ranked = coverage_analyzer.rank_lines_by_coverage_need(working_assignments)
                            for ln, benefit in ranked:
                                if ln != conflict.line_number:
                                    best_alt = ln
                                    generation_log.append(f"Line {ln}: {loser.name} (fallback, coverage-ranked)")
                                    break

                        if best_alt:
                            working_assignments[loser.name] = best_alt
                            final_assignments[loser.name] = best_alt

                # ── Step 2: Assign non-intern staff not involved in conflicts ──
                for staff in non_intern_rotating:
                    if staff.name in conflict_handled:
                        continue

                    current_line = st.session_state.current_roster.get(staff.name, 0)

                    if staff.requested_line:
                        # Direct line request — check coverage before allowing
                        from_line = current_line if current_line > 0 else 0
                        if from_line and from_line != staff.requested_line and not coverage_analyzer.is_move_safe(working_assignments, staff.name, from_line, staff.requested_line):
                            # Request denied for coverage — keep on current line
                            working_assignments[staff.name] = current_line
                            final_assignments[staff.name] = current_line
                            generation_log.append(f"Line {current_line}: {staff.name} (request for Line {staff.requested_line} denied - coverage)")
                            coverage_denials += 1
                        else:
                            working_assignments[staff.name] = staff.requested_line
                            final_assignments[staff.name] = staff.requested_line
                            generation_log.append(f"Line {staff.requested_line}: {staff.name} (requested)")
                    elif staff.requested_dates_off:
                        # Find best line for their date requests
                        line_manager = RosterLineManager(st.session_state.projected_roster_start)

                        # Check if current line works
                        if current_line > 0:
                            current_line_obj = line_manager.lines[current_line - 1]
                            if current_line_obj.has_days_off(staff.requested_dates_off):
                                working_assignments[staff.name] = current_line
                                final_assignments[staff.name] = current_line
                                generation_log.append(f"Line {current_line}: {staff.name} (current line fits dates)")
                                continue

                        # Find best fitting line with coverage check
                        ranked = line_manager.rank_lines_by_fit(staff.requested_dates_off)
                        placed = False
                        for line_obj, date_conflicts in ranked:
                            candidate = line_obj.line_number
                            from_line = current_line if current_line > 0 else 0
                            if from_line and from_line != candidate and not coverage_analyzer.is_move_safe(working_assignments, staff.name, from_line, candidate):
                                continue  # Skip this option, would hurt coverage
                            if date_conflicts == 0 or candidate not in set(final_assignments.values()):
                                working_assignments[staff.name] = candidate
                                final_assignments[staff.name] = candidate
                                generation_log.append(f"Line {candidate}: {staff.name} (best date fit, {date_conflicts} conflict(s))")
                                placed = True
                                break
                        if not placed and current_line > 0:
                            working_assignments[staff.name] = current_line
                            final_assignments[staff.name] = current_line
                            generation_log.append(f"Line {current_line}: {staff.name} (kept on current - coverage/date constraints)")
                            coverage_denials += 1
                    elif current_line > 0:
                        # No request - stay on current line
                        working_assignments[staff.name] = current_line
                        final_assignments[staff.name] = current_line
                        generation_log.append(f"Line {current_line}: {staff.name} (no change)")
                    else:
                        # No current line and no request - assign to line with most coverage need
                        ranked = coverage_analyzer.rank_lines_by_coverage_need(working_assignments)
                        for ln, benefit in ranked:
                            working_assignments[staff.name] = ln
                            final_assignments[staff.name] = ln
                            generation_log.append(f"Line {ln}: {staff.name} (auto-assigned, coverage-ranked)")
                            break

                # ── Step 3: Assign interns using rotation system ──
                if interns:
                    # Build coverage need data for intern scoring bonus
                    cov_map = coverage_analyzer.build_coverage_map(working_assignments)
                    line_coverage_needs = {}
                    for ln in range(1, 10):
                        line_obj = cov_line_manager.lines[ln - 1]
                        shortfall_days = 0
                        d = st.session_state.projected_roster_start
                        while d <= st.session_state.projected_roster_end:
                            shift = line_obj.get_shift_type(d)
                            if shift in ('D', 'N') and cov_map[d][shift] < min_coverage:
                                shortfall_days += 1
                            d += timedelta(days=1)
                        line_coverage_needs[ln] = shortfall_days

                    intern_system = InternAssignmentSystem(
                        staff_list=st.session_state.staff_list,
                        current_roster=working_assignments,
                        request_histories=st.session_state.request_histories,
                        roster_start=st.session_state.projected_roster_start,
                        roster_end=st.session_state.projected_roster_end
                    )
                    intern_system.line_coverage_needs = line_coverage_needs
                    intern_assignments = intern_system.assign_interns()

                    for intern_name, line_num in intern_assignments.items():
                        working_assignments[intern_name] = line_num
                        final_assignments[intern_name] = line_num
                        generation_log.append(f"Line {line_num}: {intern_name} (intern rotation)")

                    # Record intern pairings (mentor tracking) and persist to Google Sheets
                    all_assignments_for_pairings = dict(final_assignments)
                    intern_system.record_intern_pairings(all_assignments_for_pairings, roster_period)

                    # Save request histories so mentor pairings persist across sessions
                    hist_dict = {name: h.to_dict() for name, h in st.session_state.request_histories.items()}
                    data_storage.save_request_history(hist_dict)

                # ── Step 3.5: Coverage repair after intern moves ──
                # Intern rotation may have created shortfalls by moving interns off
                # their old lines. Try swapping flexible paramedics to compensate.
                post_intern_map = coverage_analyzer.build_coverage_map(working_assignments)
                post_intern_shortfalls = coverage_analyzer.count_shortfalls(post_intern_map)

                if post_intern_shortfalls > 0:
                    # Identify flexible paramedics: non-intern, no specific request,
                    # just stayed on their current line ("no change" in log)
                    flexible_staff = []
                    for staff in non_intern_rotating:
                        if staff.name in conflict_handled:
                            continue
                        if staff.requested_line or staff.requested_dates_off:
                            continue
                        current_line = st.session_state.current_roster.get(staff.name, 0)
                        assigned = final_assignments.get(staff.name, 0)
                        if current_line > 0 and assigned == current_line:
                            flexible_staff.append(staff)

                    # Try moving each flexible paramedic to a line that needs coverage
                    # Keep going until no improvement is possible
                    improved = True
                    while improved and post_intern_shortfalls > 0:
                        improved = False
                        best_swap = None
                        best_improvement = 0

                        for staff in flexible_staff:
                            from_line = working_assignments.get(staff.name, 0)
                            if from_line == 0:
                                continue

                            # Try every other line
                            for to_line in range(1, 10):
                                if to_line == from_line:
                                    continue
                                result = coverage_analyzer.evaluate_move(
                                    working_assignments, staff.name, from_line, to_line
                                )
                                # Only accept moves that strictly reduce shortfalls
                                if result['delta'] < best_improvement:
                                    best_improvement = result['delta']
                                    best_swap = (staff, from_line, to_line, result['after'])

                        if best_swap:
                            staff, from_line, to_line, new_shortfalls = best_swap
                            working_assignments[staff.name] = to_line
                            final_assignments[staff.name] = to_line
                            generation_log.append(
                                f"Line {to_line}: {staff.name} (moved from Line {from_line} for coverage)"
                            )
                            post_intern_shortfalls = new_shortfalls
                            # Remove from flexible list so we don't move them again
                            flexible_staff = [s for s in flexible_staff if s.name != staff.name]
                            improved = True

                # ── Step 4: Apply assignments to the RosterAssignment object ──
                for staff in roster.staff:
                    if staff.is_fixed_roster:
                        continue
                    line = final_assignments.get(staff.name)
                    if line:
                        roster.assign_staff_to_line(staff, line)

                # ── Step 5: Store projected assignments (don't touch current_roster) ──
                # Request outcomes and line history are recorded only when the
                # roster is approved (uploaded via Roster History or manually set
                # in Staff Management). This lets generation be re-run freely.
                st.session_state.projected_assignments = dict(final_assignments)
                st.session_state.projected_generation_log = list(generation_log)
                st.session_state.projected_coverage_denials = coverage_denials

                # Store the roster object for display/export (does NOT change current_roster)
                st.session_state.roster = roster

                # ── Step 7: Show generation summary ──
                st.success(f"✅ Roster generated with priority-based assignment!")

                if conflicts:
                    st.info(f"Resolved {len(conflicts)} conflict(s) using priority scores")

                if interns:
                    st.info(f"Assigned {len(interns)} intern(s) using mentor rotation")

                if coverage_denials > 0:
                    st.warning(f"⚠️ {coverage_denials} request(s) denied to maintain minimum coverage")

                # Show final coverage check
                final_cov_map = coverage_analyzer.build_coverage_map(final_assignments)
                final_shortfalls = coverage_analyzer.count_shortfalls(final_cov_map)
                if final_shortfalls > 0:
                    st.warning(f"⚠️ {final_shortfalls} coverage issue(s) remain (under/overstaffed periods may be unavoidable)")
                else:
                    st.success(f"All shifts within coverage range ({min_coverage}-{max_coverage} per shift)")

                with st.expander("Generation Log"):
                    for entry in generation_log:
                        st.write(f"• {entry}")

                # Generate Excel file
                try:
                    excel_filename = export_roster_to_excel(roster)
                    st.session_state.excel_file = excel_filename
                    st.success(f"Excel file created: {excel_filename}")
                except Exception as e:
                    st.error(f"⚠️ Roster generated but Excel export failed: {e}")
                    st.session_state.excel_file = None
    
    # Display roster if generated
    if st.session_state.roster:
        st.markdown("<h2 class='section-header'>Projected Roster</h2>", unsafe_allow_html=True)
        
        roster = st.session_state.roster
        
        # Show comparison: Current vs Projected
        st.markdown("### 📊 Current vs Projected Line Assignments")

        projected = st.session_state.get('projected_assignments', {})

        comparison_data = []
        for staff in roster.staff:
            if not staff.is_fixed_roster and staff.assigned_line:
                cur_line = st.session_state.current_roster.get(staff.name, 0)
                if isinstance(cur_line, int) and cur_line == 0:
                    current_line_str = "Not Set"
                elif isinstance(cur_line, int):
                    current_line_str = f"Line {cur_line}"
                else:
                    current_line_str = str(cur_line)

                proj_line = projected.get(staff.name, staff.assigned_line)
                projected_line = f"Line {proj_line}"

                status = "✅ No Change" if current_line_str == projected_line else "🔄 Changed"

                comparison_data.append({
                    'Staff': staff.name,
                    'Current Line': current_line_str,
                    'Projected Line': projected_line,
                    'Status': status
                })
        
        if comparison_data:
            # Sort alphabetically by staff name
            comparison_data = sorted(comparison_data, key=lambda x: x['Staff'])
            df_comparison = pd.DataFrame(comparison_data)
            st.dataframe(df_comparison, width="stretch", hide_index=True)
        
        # Download Excel button
        if st.session_state.get('excel_file'):
            st.markdown("---")
            with open(st.session_state.excel_file, 'rb') as f:
                st.download_button(
                    label="📥 Download Roster (Excel)",
                    data=f,
                    file_name=st.session_state.excel_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
            st.markdown("---")
        
        # Line assignments
        st.markdown("### Projected Line Assignments")
        
        for line_num in range(1, 10):
            staff_on_line = roster.line_assignments[line_num]
            if staff_on_line:
                with st.expander(f"📋 Line {line_num} ({len(staff_on_line)} staff)"):
                    for staff in staff_on_line:
                        st.write(f"• {staff.name} ")
        
        # Coverage report
        st.markdown("### Coverage Analysis")
        
        issues = roster.check_coverage()
        
        if not issues:
            st.success(f"✅ All shifts have adequate coverage! (Minimum {roster.min_paramedics_per_shift} paramedics per shift)")
        else:
            st.error(f"⚠️ Found {len(issues)} coverage issue(s)")
            
            for issue in issues[:10]:  # Show first 10
                st.warning(f"❌ {issue}")
        
        # Coverage statistics
        col1, col2, col3 = st.columns(3)
        
        total_days = (roster.roster_end_date - roster.roster_start_date).days + 1
        day_coverages = []
        night_coverages = []
        
        current_date = roster.roster_start_date
        while current_date <= roster.roster_end_date:
            coverage = roster.get_coverage_for_date(current_date)
            day_coverages.append(coverage['D'])
            night_coverages.append(coverage['N'])
            current_date += timedelta(days=1)
        
        with col1:
            st.metric("Day Shift - Average", f"{sum(day_coverages)/len(day_coverages):.1f}")
            st.caption(f"Min: {min(day_coverages)} | Max: {max(day_coverages)}")
        
        with col2:
            st.metric("Night Shift - Average", f"{sum(night_coverages)/len(night_coverages):.1f}")
            st.caption(f"Min: {min(night_coverages)} | Max: {max(night_coverages)}")
        
        with col3:
            total_coverage = sum(day_coverages) + sum(night_coverages)
            st.metric("Total Staff-Shifts", total_coverage)
        
        # Individual schedules
        st.markdown("### Individual Schedules")
        
        staff_names = sorted([s.name for s in roster.staff if s.assigned_line])
        selected_staff_name = st.selectbox("Select Staff Member", staff_names)
        
        if selected_staff_name:
            selected_staff = next(s for s in roster.staff if s.name == selected_staff_name)
            
            if selected_staff.assigned_line:
                st.write(f"**{selected_staff.name}** - Line {selected_staff.assigned_line}")
                
                schedule = roster.get_staff_schedule(selected_staff, 28)
                display_shift_calendar(schedule, "28-Day Schedule")

def line_explorer_page():
    """Page to explore roster lines and check transitions"""
    st.markdown("<h1 class='main-header'>🔍 Roster Line Explorer</h1>", unsafe_allow_html=True)

    # Display projected roster period
    st.info(f"""
    **Viewing Projected Roster Period**
    {st.session_state.projected_roster_start.strftime('%d %b %Y')} - {st.session_state.projected_roster_end.strftime('%d %b %Y')}
    _(Current roster: {st.session_state.roster_start.strftime('%d %b %Y')} - {st.session_state.roster_end.strftime('%d %b %Y')})_
    """)

    manager = RosterLineManager(st.session_state.projected_roster_start)

    st.markdown("<h2 class='section-header'>View Roster Lines</h2>", unsafe_allow_html=True)

    st.info("Each line follows the DDNNOOOOO pattern (2 days, 2 nights, 5 off) but starts on different days")
    
    # Show all lines
    line_num = st.selectbox("Select Line to View", list(range(1, 10)))

    line = manager.lines[line_num - 1]

    # Calculate roster length in days (using projected roster)
    roster_days = (st.session_state.projected_roster_end - st.session_state.projected_roster_start).days + 1

    # Options for how many days to view
    col1, col2 = st.columns([2, 1])
    with col1:
        view_options = {
            "1 Week (7 days)": 7,
            "2 Weeks (14 days)": 14,
            "4 Weeks (28 days)": 28,
            "6 Weeks (42 days)": 42,
            f"Full Roster ({roster_days} days)": roster_days
        }
        selected_view = st.selectbox("View Period", list(view_options.keys()), index=2)
        days_to_show = view_options[selected_view]

    with col2:
        st.metric("Roster Length", f"{roster_days} days")

    schedule = line.get_schedule(st.session_state.projected_roster_start, days_to_show)
    display_shift_calendar(schedule, f"Line {line_num} - {selected_view}")

    # Award compliance check
    st.markdown("<h2 class='section-header'>Award Compliance Check</h2>", unsafe_allow_html=True)

    violations = line.validate_award_compliance(st.session_state.projected_roster_start, days_to_show)
    
    if violations:
        st.error("❌ Award Violations Detected")
        for v in violations:
            st.error(v)
    else:
        st.success(f"✅ This line complies with all Award requirements over {days_to_show} days")
    
    # Boundary validation
    st.markdown("<h2 class='section-header'>Check Line Transitions</h2>", unsafe_allow_html=True)
    
    st.write("Check if changing from one line to another violates Award requirements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        current_line_num = st.selectbox("Current Line", list(range(1, 10)), key="current")
    with col2:
        new_line_num = st.selectbox("New Line", list(range(1, 10)), key="new")
    
    if st.button("Check Transition"):
        validator = RosterBoundaryValidator()
        current_line = manager.lines[current_line_num - 1]
        new_line = manager.lines[new_line_num - 1]

        is_valid, message = validator.validate_line_transition(
            current_line,
            new_line,
            st.session_state.projected_roster_start
        )
        
        if is_valid:
            st.success(f"✅ Transitioning from Line {current_line_num} to Line {new_line_num} is valid")
        else:
            st.error(f"❌ Transitioning from Line {current_line_num} to Line {new_line_num} violates Award requirements")
            st.error(f"**Reason:** {message}")


def roster_history_page():
    """Page to record and view approved roster history"""
    st.markdown("<h1 class='main-header'>📜 Roster History</h1>", unsafe_allow_html=True)

    st.info("""
    **Purpose:** Record the actual approved roster assignments (after management approval).
    This affects priority calculations - staff only lose priority when their request is
    actually approved in the final roster, not just in the draft.
    """)

    # Load existing history
    if 'roster_history' not in st.session_state:
        st.session_state.roster_history = data_storage.load_roster_history()

    # ══════════════════════════════════════════════════════════════════════════
    # Section 1: Record Approved Roster
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("## 📝 Record Approved Roster")
    st.caption("Enter the final approved line assignments after management review")

    with st.expander("➕ Add Approved Roster Period", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            approved_start = st.date_input(
                "Roster Start Date",
                value=st.session_state.projected_roster_start,
                key="approved_start"
            )
        with col2:
            approved_end = st.date_input(
                "Roster End Date",
                value=st.session_state.projected_roster_end,
                key="approved_end"
            )

        period_name = f"{approved_start.strftime('%b')}-{approved_end.strftime('%b %Y')}"
        st.write(f"**Period:** {period_name}")

        st.markdown("### Line Assignments")
        st.caption("Enter the line each staff member was assigned in the approved roster")

        # Get rotating staff
        rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]

        if rotating_staff:
            approved_assignments = {}

            # Create columns for better layout
            col1, col2 = st.columns(2)

            # Pre-fill from projected_assignments (generated roster) if available
            projected = st.session_state.get('projected_assignments', {})

            for i, staff in enumerate(sorted(rotating_staff, key=lambda s: s.name)):
                # Default to projected assignment, then current roster
                default_line = projected.get(staff.name,
                               st.session_state.current_roster.get(staff.name, 0))

                with col1 if i % 2 == 0 else col2:
                    line = st.selectbox(
                        f"{staff.name}",
                        options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                        index=default_line,
                        format_func=lambda x: "Unassigned" if x == 0 else f"Line {x}",
                        key=f"approved_line_{staff.name}"
                    )
                    approved_assignments[staff.name] = line

            st.markdown("---")

            approved_date = st.date_input("Date Approved", value=datetime.now(), key="approval_date")

            if st.button("💾 Save Approved Roster", type="primary", use_container_width=True):
                # Create roster entry
                roster_entry = {
                    'period': period_name,
                    'start_date': approved_start.isoformat(),
                    'end_date': approved_end.isoformat(),
                    'assignments': approved_assignments,
                    'approved_date': approved_date.isoformat(),
                    'status': 'approved'
                }

                # Check if this period already exists
                existing_idx = None
                for idx, entry in enumerate(st.session_state.roster_history):
                    if entry['period'] == period_name:
                        existing_idx = idx
                        break

                if existing_idx is not None:
                    st.session_state.roster_history[existing_idx] = roster_entry
                    st.success(f"✅ Updated approved roster for {period_name}")
                else:
                    st.session_state.roster_history.append(roster_entry)
                    st.success(f"✅ Saved approved roster for {period_name}")

                # Update request histories with approved outcomes
                for staff_name, assigned_line in approved_assignments.items():
                    if assigned_line == 0:
                        continue

                    history = st.session_state.request_histories.get(staff_name)
                    if not history:
                        history = RequestHistory(staff_name=staff_name)
                        st.session_state.request_histories[staff_name] = history

                    # Update line assignment (this affects tenure tracking)
                    history.update_line_assignment(
                        assigned_line,
                        period_name,
                        reason="approved_roster"
                    )

                    # Find and approve/deny pending requests for this period
                    for idx, req in enumerate(history.request_log):
                        if req.status == 'pending' and req.roster_period == period_name:
                            got_requested = False
                            if req.request_type == 'line_change':
                                got_requested = (req.request_details.get('requested_line') == assigned_line)
                            elif req.request_type == 'stay_on_line':
                                got_requested = (req.request_details.get('stay_on_line') == assigned_line)
                            elif req.request_type == 'dates_off':
                                got_requested = True  # Best effort for date requests

                            if got_requested:
                                history.approve_request(idx, {'assigned_line': assigned_line})
                            else:
                                history.deny_request(idx, f"Approved roster assigned Line {assigned_line}")

                # Rebuild line histories from the complete roster history
                # This ensures tenure tracking is calculated correctly across ALL rosters
                st.session_state.request_histories = rebuild_line_histories_from_roster_history(
                    st.session_state.request_histories,
                    st.session_state.roster_history
                )

                # Apply approved assignments to current_roster
                for staff_name, assigned_line in approved_assignments.items():
                    if assigned_line > 0:
                        st.session_state.current_roster[staff_name] = assigned_line

                # Clear staff request fields (requests are now resolved)
                for staff in st.session_state.staff_list:
                    if not staff.is_fixed_roster:
                        staff.requested_line = None
                        staff.requested_dates_off = []

                # Clear projected generation state
                st.session_state.pop('projected_assignments', None)
                st.session_state.pop('projected_generation_log', None)
                st.session_state.pop('projected_coverage_denials', None)
                st.session_state.roster = None

                # Save everything
                data_storage.save_roster_history(st.session_state.roster_history)
                hist_dict = {name: h.to_dict() for name, h in st.session_state.request_histories.items()}
                data_storage.save_request_history(hist_dict)
                auto_save()

                st.rerun()
        else:
            st.warning("No rotating roster staff found")

    # ══════════════════════════════════════════════════════════════════════════
    # Section 2: View History
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## 📋 Previous Approved Rosters")

    if st.session_state.roster_history:
        # Sort by start date (most recent first)
        sorted_history = sorted(
            st.session_state.roster_history,
            key=lambda x: x.get('start_date', ''),
            reverse=True
        )

        for entry in sorted_history:
            with st.expander(f"📅 {entry['period']} ({entry.get('status', 'approved').title()})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Start:** {entry.get('start_date', 'N/A')}")
                    st.write(f"**End:** {entry.get('end_date', 'N/A')}")
                with col2:
                    st.write(f"**Approved:** {entry.get('approved_date', 'N/A')}")
                    st.write(f"**Status:** {entry.get('status', 'approved').title()}")

                st.markdown("**Assignments:**")
                assignments = entry.get('assignments', {})
                if assignments:
                    # Group by line
                    by_line = {}
                    for name, line in assignments.items():
                        if line > 0:
                            if line not in by_line:
                                by_line[line] = []
                            by_line[line].append(name)

                    for line_num in sorted(by_line.keys()):
                        names = by_line[line_num]
                        st.write(f"**Line {line_num}:** {', '.join(sorted(names))}")

                # Delete button
                if st.button(f"🗑️ Delete this record", key=f"delete_{entry['period']}"):
                    st.session_state.roster_history = [
                        e for e in st.session_state.roster_history
                        if e['period'] != entry['period']
                    ]
                    data_storage.save_roster_history(st.session_state.roster_history)
                    st.success(f"Deleted {entry['period']}")
                    st.rerun()
    else:
        st.info("No approved rosters recorded yet. Use the form above to record approved roster assignments.")

    # ══════════════════════════════════════════════════════════════════════════
    # Section 3: Import from Current
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## 🔄 Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 Copy Current Roster to Approved", use_container_width=True):
            # Quick way to record current roster as approved
            period_name = f"{st.session_state.roster_start.strftime('%b')}-{st.session_state.roster_end.strftime('%b %Y')}"

            roster_entry = {
                'period': period_name,
                'start_date': st.session_state.roster_start.isoformat(),
                'end_date': st.session_state.roster_end.isoformat(),
                'assignments': dict(st.session_state.current_roster),
                'approved_date': datetime.now().isoformat(),
                'status': 'approved'
            }

            # Check if exists
            existing_idx = None
            for idx, entry in enumerate(st.session_state.roster_history):
                if entry['period'] == period_name:
                    existing_idx = idx
                    break

            if existing_idx is not None:
                st.session_state.roster_history[existing_idx] = roster_entry
            else:
                st.session_state.roster_history.append(roster_entry)

            data_storage.save_roster_history(st.session_state.roster_history)
            st.success(f"✅ Current roster saved as approved for {period_name}")
            st.rerun()

    with col2:
        if st.button("🔄 Refresh from Storage", use_container_width=True):
            st.session_state.roster_history = data_storage.load_roster_history()
            st.success("✅ Reloaded roster history from storage")
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # Section 4: Advance to Next Roster Period
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## ⏭️ Advance to Next Roster Period")

    st.caption(
        "Once the projected roster has been approved and is ready to become the active roster, "
        "use this to advance the dates forward. The projected roster becomes the current roster, "
        "and new projected dates are calculated."
    )

    # Show what will happen
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Current State:**")
        st.write(f"Current: {st.session_state.roster_start.strftime('%d %b %Y')} - {st.session_state.roster_end.strftime('%d %b %Y')}")
        st.write(f"Projected: {st.session_state.projected_roster_start.strftime('%d %b %Y')} - {st.session_state.projected_roster_end.strftime('%d %b %Y')}")

    new_projected_start = st.session_state.projected_roster_end + timedelta(days=1)
    new_projected_end = new_projected_start + timedelta(days=62)

    with col2:
        st.markdown("**After Advance:**")
        st.write(f"Current: {st.session_state.projected_roster_start.strftime('%d %b %Y')} - {st.session_state.projected_roster_end.strftime('%d %b %Y')}")
        st.write(f"Projected: {new_projected_start.strftime('%d %b %Y')} - {new_projected_end.strftime('%d %b %Y')}")

    # Find the approved roster entry that matches the projected period
    projected_period_name = f"{st.session_state.projected_roster_start.strftime('%b')}-{st.session_state.projected_roster_end.strftime('%b %Y')}"
    approved_entry = None
    for entry in st.session_state.roster_history:
        if entry.get('status') == 'approved' and entry.get('period') == projected_period_name:
            approved_entry = entry
            break

    if approved_entry:
        st.success(f"Found approved roster for **{projected_period_name}** - assignments will be applied.")
    else:
        st.warning(f"No approved roster found for **{projected_period_name}**. Current line assignments will be kept.")

    # Confirmation with checkbox
    confirm_advance = st.checkbox("I confirm I want to advance the roster period", key="confirm_advance")

    if st.button("⏭️ Advance Roster Period", type="primary", use_container_width=True, disabled=not confirm_advance):
        # 1. Store old current end as new previous_roster_end
        st.session_state.previous_roster_end = st.session_state.roster_end

        # 2. Move projected dates to current
        st.session_state.roster_start = st.session_state.projected_roster_start
        st.session_state.roster_end = st.session_state.projected_roster_end

        # 3. Calculate new projected dates
        st.session_state.projected_roster_start = st.session_state.roster_end + timedelta(days=1)
        st.session_state.projected_roster_end = st.session_state.projected_roster_start + timedelta(days=62)

        # 4. Apply approved roster assignments if available
        if approved_entry:
            assignments = approved_entry.get('assignments', {})
            for staff_name, line_num in assignments.items():
                if line_num > 0:
                    st.session_state.current_roster[staff_name] = line_num

        # 5. Clear staff request fields and projected generation state
        for staff in st.session_state.staff_list:
            if not staff.is_fixed_roster:
                staff.requested_line = None
                staff.requested_dates_off = []

        st.session_state.pop('projected_assignments', None)
        st.session_state.pop('projected_generation_log', None)
        st.session_state.pop('projected_coverage_denials', None)
        st.session_state.roster = None

        # 6. Save everything (auto_save handles staff, roster, settings, and request histories)
        auto_save()

        st.success(
            f"✅ Roster period advanced!\n\n"
            f"**Current:** {st.session_state.roster_start.strftime('%d %b %Y')} - {st.session_state.roster_end.strftime('%d %b %Y')}\n\n"
            f"**Projected:** {st.session_state.projected_roster_start.strftime('%d %b %Y')} - {st.session_state.projected_roster_end.strftime('%d %b %Y')}"
        )
        st.rerun()


# Main app
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
        
        # Tenure protection message - check for new staff (no line_history)
        if not history.line_history:
            st.success(f"✅ New staff - maximum tenure protection (first roster)")
        elif history.rosters_on_current_line <= 1:
            st.success(f"✅ Tenure protection active: First/second roster on Line {current_line}")
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
                st.write(f"{i}. {mentor} ({period}) - {shifts} shifts ← Current")
            else:
                st.write(f"{i}. {mentor} ({period}) - {shifts} shifts")
    
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


def main():
    st.sidebar.title("🚑 Bay & Basin Roster")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Navigation",
        ["👥 Staff Management", "📅 Current Roster", "🔔 Staff Request", "👔 Manager: Create Roster", "📜 Roster History", "📊 Request History", "🔍 Line Explorer"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Current Roster Period")
    st.sidebar.write(f"**Start:** {st.session_state.roster_start.strftime('%d/%m/%Y')}")
    st.sidebar.write(f"**End:** {st.session_state.roster_end.strftime('%d/%m/%Y')}")
    
    # Calculate days
    current_days = (st.session_state.roster_end - st.session_state.roster_start).days + 1
    current_weeks = current_days / 7
    st.sidebar.caption(f"{current_days} days ({current_weeks:.1f} weeks)")
    
    st.sidebar.markdown("### Projected Roster Period")
    st.sidebar.write(f"**Start:** {st.session_state.projected_roster_start.strftime('%d/%m/%Y')}")
    st.sidebar.write(f"**End:** {st.session_state.projected_roster_end.strftime('%d/%m/%Y')}")
    projected_days = (st.session_state.projected_roster_end - st.session_state.projected_roster_start).days + 1
    projected_weeks = projected_days / 7
    st.sidebar.caption(f"{projected_days} days ({projected_weeks:.1f} weeks)")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Staff Requests:** {len(st.session_state.staff_list)}")
    
    # Show current roster stats
    rotating_staff = [s for s in st.session_state.staff_list if not s.is_fixed_roster]
    assigned_count = sum(1 for name in st.session_state.current_roster.values() if name > 0)
    st.sidebar.markdown(f"**Current Assignments:** {assigned_count}/{len(rotating_staff)}")
    
    # Show conflicts if any
    if st.session_state.request_histories and rotating_staff:
        detector = ConflictDetector(
            staff_list=rotating_staff,
            current_roster=st.session_state.current_roster,
            request_histories=st.session_state.request_histories,
            roster_start=st.session_state.projected_roster_start
        )
        conflicts = detector.detect_line_conflicts()
        if conflicts:
            st.sidebar.markdown(f"**⚠️ Conflicts:** {len(conflicts)}")
    
    # Show intern count
    interns = [s for s in st.session_state.staff_list if s.role == "Intern" and not s.is_fixed_roster]
    if interns:
        st.sidebar.markdown(f"**👨‍⚕️ Interns:** {len(interns)}")
    
    st.sidebar.markdown("---")
    
    # Save/Clear controls
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("💾 Save Now", width="stretch"):
            if data_storage.save_all(
                st.session_state.staff_list,
                st.session_state.current_roster,
                st.session_state.roster_start,
                st.session_state.roster_end,
                st.session_state.previous_roster_end
            ):
                st.sidebar.success("✅ Saved!")
            else:
                st.sidebar.error("❌ Save failed")
    
    with col2:
        if st.button("🗑️ Clear", width="stretch"):
            st.session_state.confirm_clear_all = True
    
    # Confirmation dialog for clear - MUCH SAFER
    if st.session_state.get('confirm_clear_all', False):
        st.sidebar.markdown("---")
        st.sidebar.error("⚠️ **DANGER: Delete All Data?**")
        st.sidebar.warning(
            "This will permanently delete:\n\n"
            f"• All {len(st.session_state.staff_list)} staff members\n"
            f"• All current roster assignments\n"
            "• All saved data files\n\n"
            "**This CANNOT be undone!**"
        )
        
        # Suggest backup first
        if data_storage.data_exists():
            st.sidebar.info("💡 Consider saving a backup first using the 💾 Save Now button")
        
        # Type to confirm
        st.sidebar.markdown("**Type `DELETE` to confirm:**")
        confirm_text = st.sidebar.text_input(
            "Confirmation",
            key="clear_confirm_text",
            label_visibility="collapsed"
        )
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            # Only enable if they typed DELETE
            if confirm_text == "DELETE":
                if st.button("✅ Yes, Delete", key="confirm_yes", type="primary"):
                    st.session_state.staff_list = []
                    st.session_state.current_roster = {}
                    st.session_state.roster = None
                    data_storage.clear_all_data()
                    st.session_state.confirm_clear_all = False
                    st.sidebar.success("✅ All data cleared!")
                    st.rerun()
            else:
                st.button("✅ Yes, Delete", key="confirm_yes_disabled", disabled=True)
                if confirm_text:
                    st.sidebar.caption("❌ Must type DELETE exactly")
        
        with col2:
            if st.button("❌ Cancel", key="confirm_no"):
                st.session_state.confirm_clear_all = False
                st.session_state.clear_confirm_text = ""
                st.rerun()
        
        st.sidebar.markdown("---")
    
    # Show auto-save status
    if data_storage.data_exists():
        st.sidebar.caption("💾 Auto-saves on changes")
    
    st.sidebar.markdown("---")
    
    # Load Sample Data button
    if st.sidebar.button("📥 Load Bay & Basin Data"):
        try:
            from load_bay_basin import load_bay_basin_data
            staff_list, current_roster, dates = load_bay_basin_data()
            
            st.session_state.staff_list = staff_list
            st.session_state.current_roster = current_roster
            st.session_state.roster_start = dates[0]
            st.session_state.roster_end = dates[1]
            st.session_state.previous_roster_end = dates[2]
            
            st.sidebar.success("✅ Data loaded!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error loading data: {e}")
    
    # Route to correct page
    if page == "👥 Staff Management":
        staff_management_page()
    elif page == "📅 Current Roster":
        current_roster_page()
    elif page == "🔔 Staff Request":
        staff_request_page()
    elif page == "👔 Manager: Create Roster":
        manager_roster_page()
    elif page == "📜 Roster History":
        roster_history_page()
    elif page == "📊 Request History":
        request_history_page()
    else:
        line_explorer_page()

if __name__ == "__main__":
    main()
