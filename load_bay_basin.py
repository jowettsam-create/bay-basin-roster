"""
QUICK LOADER - Bay & Basin Staff
Copy and paste this into a Python cell or run as a script
"""

import sys
sys.path.append('C:\\Users\\Sam\\Downloads\\python\\Roster')  # Adjust if needed

from datetime import datetime
from roster_assignment import StaffMember
from fixed_roster_helper import create_fixed_roster_from_days

def load_bay_basin_data():
    """
    Returns: (staff_list, current_roster, roster_dates)
    Ready to load into Streamlit session state
    """
    
    staff_list = []
    current_roster = {}
    
    # Dates - 9-week rosters (63 days each)
    # Current roster: 24 Jan - 27 Mar 2026 (9 weeks)
    CURRENT_START = datetime(2026, 1, 24)  # Saturday
    CURRENT_END = datetime(2026, 3, 27)    # Friday (63 days later)
    PREV_END = datetime(2026, 1, 23)       # Previous roster ended Friday Jan 23
    
    # ========== FULL-TIME ROTATING STAFF ==========
    
    # Line 1
    staff_list.append(StaffMember(
        name="Shane Orchard",
        role="Paramedic",
    ))
    current_roster["Shane Orchard"] = 1
    
    # Line 2
    staff_list.append(StaffMember(
        name="Heulwen Spencer-Goodsir",
        role="Paramedic",
    ))
    current_roster["Heulwen Spencer-Goodsir"] = 2
    
    # Line 3
    staff_list.append(StaffMember(
        name="David McColl",
        role="Paramedic",
    ))
    current_roster["David McColl"] = 3
    
    staff_list.append(StaffMember(
        name="Claire Doyle",
        role="Intern",
    ))
    current_roster["Claire Doyle"] = 3
    
    # Line 4
    staff_list.append(StaffMember(
        name="Jennifer Richards",
        role="Paramedic",
    ))
    current_roster["Jennifer Richards"] = 4
    
    # Line 5
    staff_list.append(StaffMember(
        name="Minling Wu",
        role="Paramedic",
    ))
    current_roster["Minling Wu"] = 5
    
    # Line 6
    staff_list.append(StaffMember(
        name="Briana Car",
        role="Paramedic",
        leave_periods=[
            (datetime(2026, 1, 24), datetime(2026, 2, 18), "Annual")
        ]
    ))
    current_roster["Briana Car"] = 6
    
    staff_list.append(StaffMember(
        name="Joel Pegram",
        role="Paramedic",
    ))
    current_roster["Joel Pegram"] = 6
    
    # Line 7
    staff_list.append(StaffMember(
        name="Glenn Chandler",
        role="Paramedic",
        leave_periods=[
            (datetime(2026, 2, 9), datetime(2026, 2, 10), "MCPD Leave")
        ]
    ))
    current_roster["Glenn Chandler"] = 7
    
    # Line 8
    staff_list.append(StaffMember(
        name="Samuel Jowett",
        role="Paramedic",
        leave_periods=[
            (datetime(2026, 1, 24), datetime(2026, 2, 19), "Annual")
        ]
    ))
    current_roster["Samuel Jowett"] = 8
    
    # Line 9
    staff_list.append(StaffMember(
        name="Diya Arangassery",
        role="Intern",
    ))
    current_roster["Diya Arangassery"] = 9
    
    # On maternity leave (not assigned to line)
    staff_list.append(StaffMember(
        name="Marissa Leso",
        role="Paramedic",
        leave_periods=[
            (datetime(2026, 1, 24), datetime(2026, 6, 30), "Maternity")
        ]
    ))
    current_roster["Marissa Leso"] = 0  # Not working
    
    # ========== FIXED ROSTER STAFF (Part-time/Casual) ==========
    
    # Megan Bryant - PT working Mon/Wed/Fri
    staff_list.append(create_fixed_roster_from_days(
        name="Megan Bryant",
        role="PT/FTR",
        working_days=["Monday", "Wednesday", "Friday"],
        shift_type='D',
        roster_start=CURRENT_START,
        roster_end=CURRENT_END
    ))
    
    return staff_list, current_roster, (CURRENT_START, CURRENT_END, PREV_END)


# ========== PRINT SUMMARY ==========
if __name__ == "__main__":
    staff_list, current_roster, dates = load_bay_basin_data()
    
    print("✅ LOADED BAY & BASIN ROSTER DATA")
    print("=" * 60)
    print(f"Total Staff: {len(staff_list)}")
    print(f"Assigned to Lines: {sum(1 for v in current_roster.values() if v > 0)}")
    print(f"Fixed Roster: {sum(1 for s in staff_list if s.is_fixed_roster)}")
    print()
    print("Next Roster: {} to {}".format(
        dates[0].strftime('%d/%m/%Y'),
        dates[1].strftime('%d/%m/%Y')
    ))
    print()
    print("Line Distribution:")
    for line in range(1, 10):
        count = sum(1 for v in current_roster.values() if v == line)
        if count > 0:
            names = [k for k, v in current_roster.items() if v == line]
            print(f"  Line {line}: {count} staff - {', '.join(names)}")
    print()
    print("=" * 60)
    print("\nTo load into Streamlit:")
    print("  staff_list, current_roster, dates = load_bay_basin_data()")
    print("  st.session_state.staff_list = staff_list")
    print("  st.session_state.current_roster = current_roster")
    print("  st.session_state.roster_start = dates[0]")
    print("  st.session_state.roster_end = dates[1]")
    print("  st.session_state.previous_roster_end = dates[2]")
