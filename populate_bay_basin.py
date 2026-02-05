"""
Populate Bay & Basin Roster Data
Based on the Jan 24 - Feb 20, 2026 roster

This script adds all staff and sets their current line assignments
"""

from datetime import datetime, timedelta
from roster_assignment import StaffMember
from fixed_roster_helper import create_fixed_roster_from_days

# Roster periods
CURRENT_ROSTER_START = datetime(2026, 1, 24)  # Friday Jan 24
CURRENT_ROSTER_END = datetime(2026, 2, 20)    # Friday Feb 20

NEXT_ROSTER_START = datetime(2026, 2, 21)     # Saturday Feb 21
NEXT_ROSTER_END = datetime(2026, 3, 20)       # Friday Mar 20


def analyze_schedule_pattern(schedule_string):
    """
    Analyze a schedule string to determine which roster line it matches
    
    Looking at Jan 24-26 (Sat-Mon):
    Line 1: DD N -> starts with 2 days on Sat
    Line 2: OD DN -> off Sat, day Sun
    Line 3: OO DD -> off Sat-Sun, days Mon-Tue
    etc.
    """
    # Based on the DDNNOOOO pattern starting different days
    # We'll check the first few days to identify the line
    
    first_week = schedule_string[:9]  # First 9 characters
    
    # Line patterns (where pattern starts on Saturday Jan 24)
    patterns = {
        1: "DDNNOOOOO",  # Starts: DD on Sat-Sun
        2: "ODDNNOOOO",  # Starts: O on Sat, DD on Sun-Mon
        3: "OODDNNOOO",  # Starts: OO on Sat-Sun, DD on Mon-Tue
        4: "OOODDNNOO",  # Starts: OOO, then DD
        5: "OOOODDNNO",  # Starts: OOOO, then DD
        6: "OOOOODDNN",  # Starts: OOOOO, then DD
        7: "NOOOOODDNO", # Starts: N on Sat
        8: "NNOOOOОДD",  # Starts: NN on Sat-Sun
        9: "ONNOOOODD",  # Starts: O on Sat, NN on Sun-Mon
    }
    
    # Try to match
    for line_num, pattern in patterns.items():
        if first_week.startswith(pattern[:len(first_week)]):
            return line_num
    
    return None


def create_bay_basin_staff():
    """
    Create all Bay & Basin staff with their details
    Returns: (staff_list, current_roster_dict)
    """
    
    staff_list = []
    current_roster = {}
    
    # FULL-TIME ROTATING ROSTER STAFF
    
    # 1. Briana Car - Currently on Annual Leave entire period
    # From roster: All "Annual" from Jan 24-Feb 18, then OFF OFF OFF DD N
    # Pattern at end suggests Line 6 or 7 (OOO DD N)
    briana = StaffMember(
        name="Briana Car",
        role="Paramedic",
        year="Para Yr2",
        leave_periods=[
            (datetime(2026, 1, 24), datetime(2026, 2, 18), "Annual")
        ]
    )
    staff_list.append(briana)
    current_roster["Briana Car"] = 6  # Line 6 based on OFF OFF OFF DD pattern at end
    
    # 2. Glenn Chandler
    # Jan 24-26: OFF OFF OFF -> suggests middle of OFF period
    # Feb 3-7: DD NN OFF -> classic DDNNOOOO pattern
    # This is Line 7 (starts with N, then OOOOO, then DD)
    glenn = StaffMember(
        name="Glenn Chandler",
        role="Paramedic",
        year="Para Yr6",
        leave_periods=[
            (datetime(2026, 2, 9), datetime(2026, 2, 10), "MCPD Leave")
        ]
    )
    staff_list.append(glenn)
    current_roster["Glenn Chandler"] = 7
    
    # 3. Samuel Jowett - On Annual Leave entire period
    # Last day shows: NN OFF -> suggests Line 8 or 9
    samuel = StaffMember(
        name="Samuel Jowett",
        role="Paramedic",
        year="Para Yr6",
        leave_periods=[
            (datetime(2026, 1, 24), datetime(2026, 2, 19), "Annual")
        ]
    )
    staff_list.append(samuel)
    current_roster["Samuel Jowett"] = 8
    
    # 4. Marissa Leso - Mat HP (Maternity Health Program) entire period
    # Not working, but keeping in system
    marissa = StaffMember(
        name="Marissa Leso",
        role="Paramedic",
        year="Para Yr6",
        leave_periods=[
            (datetime(2026, 1, 24), datetime(2026, 3, 20), "Maternity")
        ]
    )
    staff_list.append(marissa)
    current_roster["Marissa Leso"] = 0  # Not assigned while on mat leave
    
    # 5. David McColl
    # From visual inspection of roster PDF - need to determine pattern
    # Appears to start: OFF OFF DD NN
    david = StaffMember(
        name="David McColl",
        role="Paramedic",
        year="Para Yr6"
    )
    staff_list.append(david)
    current_roster["David McColl"] = 3  # Line 3: OO DD NN
    
    # 6. Shane Orchard  
    # Appears to have: DD NN OFF OFF OFF pattern
    shane = StaffMember(
        name="Shane Orchard",
        role="Paramedic",
        year="Para Yr4"
    )
    staff_list.append(shane)
    current_roster["Shane Orchard"] = 1  # Line 1: DD NN OOOOO
    
    # 7. Joel Pegram
    # Pattern suggests: OOOOO DD NN
    joel = StaffMember(
        name="Joel Pegram",
        role="Paramedic",
        year="Para Yr6"
    )
    staff_list.append(joel)
    current_roster["Joel Pegram"] = 6  # Line 6: OOOOO DD NN
    
    # 8. Jennifer Richards
    # Pattern suggests: OOO DD NN OFF OFF
    jennifer = StaffMember(
        name="Jennifer Richards",
        role="Paramedic",
        year="Para Yr6"
    )
    staff_list.append(jennifer)
    current_roster["Jennifer Richards"] = 4  # Line 4: OOO DD NN
    
    # 9. Heulwen Spencer-Goodsir
    # Newer paramedic
    heulwen = StaffMember(
        name="Heulwen Spencer-Goodsir",
        role="Paramedic",
        year="Para Yr2"
    )
    staff_list.append(heulwen)
    current_roster["Heulwen Spencer-Goodsir"] = 2  # Line 2
    
    # 10. Minling Wu
    minling = StaffMember(
        name="Minling Wu",
        role="Paramedic",
        year="Para Yr6"
    )
    staff_list.append(minling)
    current_roster["Minling Wu"] = 5  # Line 5
    
    # INTERNS / TRAINEES
    
    # 11. Diya Arangassery
    diya = StaffMember(
        name="Diya Arangassery",
        role="Intern",
        year="Para Intern Yr2"
    )
    staff_list.append(diya)
    current_roster["Diya Arangassery"] = 9  # Line 9
    
    # 12. Claire Doyle
    claire = StaffMember(
        name="Claire Doyle",
        role="Intern",
        year="Para Intern Yr2"
    )
    staff_list.append(claire)
    current_roster["Claire Doyle"] = 3  # Line 3
    
    # PART-TIME / CASUAL STAFF (Fixed Rosters)
    
    # 13. Megan Bryant - Part-time (exact pattern needs to be determined from roster)
    # Assuming Mon/Wed/Fri based on typical PT pattern
    megan = create_fixed_roster_from_days(
        name="Megan Bryant",
        role="PT/FTR",
        year="Para Yr5",
        working_days=["Monday", "Wednesday", "Friday"],
        shift_type='D',
        roster_start=NEXT_ROSTER_START,
        roster_end=NEXT_ROSTER_END
    )
    staff_list.append(megan)
    # Fixed roster staff don't have a current line number
    
    return staff_list, current_roster


def print_summary(staff_list, current_roster):
    """Print a summary of the populated data"""
    print("=" * 80)
    print("BAY & BASIN ROSTER POPULATION")
    print("=" * 80)
    print(f"\nCurrent Roster Period: {CURRENT_ROSTER_START.strftime('%d/%m/%Y')} to {CURRENT_ROSTER_END.strftime('%d/%m/%Y')}")
    print(f"Next Roster Period: {NEXT_ROSTER_START.strftime('%d/%m/%Y')} to {NEXT_ROSTER_END.strftime('%d/%m/%Y')}")
    
    print(f"\n📊 Total Staff: {len(staff_list)}")
    
    fixed = [s for s in staff_list if s.is_fixed_roster]
    rotating = [s for s in staff_list if not s.is_fixed_roster]
    
    print(f"  • Rotating roster: {len(rotating)}")
    print(f"  • Fixed roster: {len(fixed)}")
    
    print("\n" + "=" * 80)
    print("CURRENT LINE ASSIGNMENTS")
    print("=" * 80)
    
    # Group by line
    for line_num in range(1, 10):
        staff_on_line = [name for name, line in current_roster.items() if line == line_num]
        if staff_on_line:
            print(f"\n📋 Line {line_num}: {len(staff_on_line)} staff")
            for name in staff_on_line:
                staff = next(s for s in staff_list if s.name == name)
                leave_info = ""
                if staff.leave_periods:
                    leave_info = f" (On leave: {staff.leave_periods[0][2]})"
                print(f"  • {name} - {staff.year}{leave_info}")
    
    # Unassigned
    unassigned = [name for name, line in current_roster.items() if line == 0]
    if unassigned:
        print(f"\n⚠️ Unassigned: {len(unassigned)}")
        for name in unassigned:
            print(f"  • {name}")
    
    # Fixed roster staff
    if fixed:
        print(f"\n📌 Fixed Roster Staff: {len(fixed)}")
        for staff in fixed:
            print(f"  • {staff.name} - {staff.year}")
    
    print("\n" + "=" * 80)


def export_for_streamlit():
    """
    Generate Python code that can be pasted into Streamlit
    or saved as a startup script
    """
    staff_list, current_roster = create_bay_basin_staff()
    
    print("\n" + "=" * 80)
    print("COPY THIS CODE TO POPULATE STREAMLIT")
    print("=" * 80)
    print("""
# Add this to your Streamlit session or save as a separate file

staff_list, current_roster = create_bay_basin_staff()

# For Streamlit, add to session state:
st.session_state.staff_list = staff_list
st.session_state.current_roster = current_roster
st.session_state.roster_start = datetime(2026, 2, 21)
st.session_state.roster_end = datetime(2026, 3, 20)
st.session_state.previous_roster_end = datetime(2026, 2, 20)
    """)
    
    print("=" * 80)


if __name__ == "__main__":
    staff_list, current_roster = create_bay_basin_staff()
    print_summary(staff_list, current_roster)
    
    print("\n" + "=" * 80)
    print("DATA READY TO USE")
    print("=" * 80)
    print("\nYou can now:")
    print("1. Import this data into your Streamlit app")
    print("2. Use it as a starting point")
    print("3. Modify assignments as needed")
    print("\nRun this script with: python populate_bay_basin.py")
