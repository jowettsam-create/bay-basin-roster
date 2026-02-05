"""
Demo Data Loader
Quickly populate the roster system with example staff for testing
"""

from datetime import datetime, timedelta
from roster_assignment import RosterAssignment, StaffMember

def create_demo_roster():
    """Create a demo roster with sample staff"""
    
    # Roster period: 4 weeks starting Feb 21, 2026
    start_date = datetime(2026, 2, 21)
    end_date = datetime(2026, 3, 20)
    
    roster = RosterAssignment(start_date, end_date, min_paramedics_per_shift=2)
    
    # Add sample staff with different request types
    
    # Staff 1: Requests Line 1
    staff1 = StaffMember(
        name="Glenn Chandler",
        role="Paramedic",
        year="Para Yr6",
        requested_line=1
    )
    roster.add_staff(staff1)
    
    # Staff 2: Requests specific dates off
    staff2 = StaffMember(
        name="Samuel Jowett",
        role="Paramedic",
        year="Para Yr6",
        requested_dates_off=[
            datetime(2026, 2, 25),
            datetime(2026, 2, 26),
            datetime(2026, 3, 4),
            datetime(2026, 3, 5),
        ]
    )
    roster.add_staff(staff2)
    
    # Staff 3: Has annual leave
    staff3 = StaffMember(
        name="Shane Orchard",
        role="Paramedic",
        year="Para Yr4",
        leave_periods=[
            (datetime(2026, 3, 10), datetime(2026, 3, 17), "Annual")
        ]
    )
    roster.add_staff(staff3)
    
    # Staff 4: Requests Line 5
    staff4 = StaffMember(
        name="Jennifer Richards",
        role="Paramedic",
        year="Para Yr6",
        requested_line=5
    )
    roster.add_staff(staff4)
    
    # Staff 5: Requests dates off
    staff5 = StaffMember(
        name="Joel Pegram",
        role="Paramedic",
        year="Para Yr6",
        requested_dates_off=[
            datetime(2026, 2, 28),
            datetime(2026, 3, 1),
            datetime(2026, 3, 2),
        ]
    )
    roster.add_staff(staff5)
    
    # Staff 6: No specific requests
    staff6 = StaffMember(
        name="Heulwen Spencer-Goodsir",
        role="Paramedic",
        year="Para Yr2"
    )
    roster.add_staff(staff6)
    
    # Staff 7: Intern with Line 3 request
    staff7 = StaffMember(
        name="Diya Arangassery",
        role="Intern",
        year="Para Intern Yr2",
        requested_line=3
    )
    roster.add_staff(staff7)
    
    # Staff 8: Part-time
    staff8 = StaffMember(
        name="Megan Bryant",
        role="PT/FTR",
        year="Para Yr5"
    )
    roster.add_staff(staff8)
    
    print("=" * 80)
    print("DEMO ROSTER CREATED")
    print("=" * 80)
    print(f"\nRoster Period: {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}")
    print(f"Total Staff: {len(roster.staff)}")
    print("\nStaff Added:")
    
    for staff in roster.staff:
        print(f"\n  • {staff.name} ({staff.year})")
        if staff.requested_line:
            print(f"    Requested: Line {staff.requested_line}")
        elif staff.requested_dates_off:
            print(f"    Requested: {len(staff.requested_dates_off)} specific dates off")
        if staff.leave_periods:
            for start, end, leave_type in staff.leave_periods:
                print(f"    Leave: {leave_type} ({start.strftime('%d/%m')} - {end.strftime('%d/%m')})")
    
    # Auto-assign
    print("\n" + "=" * 80)
    print("AUTO-ASSIGNING STAFF...")
    print("=" * 80)
    roster.auto_assign_staff()
    
    # Show results
    roster.print_assignment_summary()
    roster.print_coverage_report()
    
    return roster


def demo_boundary_validation():
    """Demonstrate boundary validation"""
    from roster_lines import RosterLineManager
    from roster_boundary_validator import RosterBoundaryValidator
    
    print("\n" + "=" * 80)
    print("BOUNDARY VALIDATION DEMO")
    print("=" * 80)
    
    start_date = datetime(2026, 2, 21)
    manager = RosterLineManager(start_date)
    validator = RosterBoundaryValidator()
    
    print("\nTesting line transitions from Line 1:")
    
    line_1 = manager.lines[0]
    results = validator.find_valid_line_transitions(line_1, manager.lines, start_date)
    
    valid = [line for line, is_valid, msg in results if is_valid]
    invalid = [(line, msg) for line, is_valid, msg in results if not is_valid]
    
    print(f"\n✅ Valid transitions: {len(valid)}")
    print(f"❌ Invalid transitions: {len(invalid)}")
    
    if invalid:
        print("\nInvalid transitions:")
        for line, msg in invalid:
            print(f"  {line}: {msg}")


if __name__ == "__main__":
    roster = create_demo_roster()
    demo_boundary_validation()
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nTo run the web interface:")
    print("  streamlit run roster_app.py")
