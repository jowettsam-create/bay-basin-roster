"""
Data Storage Module
Saves and loads roster data to/from JSON files
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from roster_assignment import StaffMember

# Storage directory
STORAGE_DIR = Path("roster_data")
STORAGE_DIR.mkdir(exist_ok=True)

# File paths
STAFF_FILE = STORAGE_DIR / "staff.json"
CURRENT_ROSTER_FILE = STORAGE_DIR / "current_roster.json"
SETTINGS_FILE = STORAGE_DIR / "settings.json"
REQUEST_HISTORY_FILE = STORAGE_DIR / "request_history.json"


def serialize_date(dt: datetime) -> str:
    """Convert datetime to string"""
    return dt.isoformat() if dt else None


def deserialize_date(date_str: str) -> datetime:
    """Convert string to datetime"""
    return datetime.fromisoformat(date_str) if date_str else None


def serialize_staff(staff: StaffMember) -> dict:
    """Convert StaffMember to JSON-serializable dict"""
    data = {
        'name': staff.name,
        'role': staff.role,
        'year': staff.year,
        'is_fixed_roster': staff.is_fixed_roster,
        'requested_line': staff.requested_line,
        'assigned_line': staff.assigned_line,
    }
    
    # Requested dates off
    if staff.requested_dates_off:
        data['requested_dates_off'] = [serialize_date(d) for d in staff.requested_dates_off]
    
    # Leave periods
    if staff.leave_periods:
        data['leave_periods'] = [
            (serialize_date(start), serialize_date(end), leave_type)
            for start, end, leave_type in staff.leave_periods
        ]
    
    # Fixed schedule
    if staff.is_fixed_roster and staff.fixed_schedule:
        data['fixed_schedule'] = {
            serialize_date(date): shift_type
            for date, shift_type in staff.fixed_schedule.items()
        }
    
    return data


def deserialize_staff(data: dict) -> StaffMember:
    """Convert dict to StaffMember"""
    # Basic fields
    staff = StaffMember(
        name=data['name'],
        role=data['role'],
        year=data['year'],
        is_fixed_roster=data.get('is_fixed_roster', False),
        requested_line=data.get('requested_line'),
        assigned_line=data.get('assigned_line')
    )
    
    # Requested dates off
    if 'requested_dates_off' in data:
        staff.requested_dates_off = [
            deserialize_date(d) for d in data['requested_dates_off']
        ]
    
    # Leave periods
    if 'leave_periods' in data:
        staff.leave_periods = [
            (deserialize_date(start), deserialize_date(end), leave_type)
            for start, end, leave_type in data['leave_periods']
        ]
    
    # Fixed schedule
    if 'fixed_schedule' in data:
        staff.fixed_schedule = {
            deserialize_date(date_str): shift_type
            for date_str, shift_type in data['fixed_schedule'].items()
        }
    
    return staff


def save_staff_list(staff_list: List[StaffMember]) -> bool:
    """Save staff list to file"""
    try:
        data = [serialize_staff(staff) for staff in staff_list]
        
        with open(STAFF_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving staff list: {e}")
        return False


def load_staff_list() -> List[StaffMember]:
    """Load staff list from file"""
    if not STAFF_FILE.exists():
        return []
    
    try:
        with open(STAFF_FILE, 'r') as f:
            data = json.load(f)
        
        return [deserialize_staff(staff_data) for staff_data in data]
    except Exception as e:
        print(f"Error loading staff list: {e}")
        return []


def save_current_roster(current_roster: Dict[str, int]) -> bool:
    """Save current roster assignments to file"""
    try:
        with open(CURRENT_ROSTER_FILE, 'w') as f:
            json.dump(current_roster, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving current roster: {e}")
        return False


def load_current_roster() -> Dict[str, int]:
    """Load current roster assignments from file"""
    if not CURRENT_ROSTER_FILE.exists():
        return {}
    
    try:
        with open(CURRENT_ROSTER_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading current roster: {e}")
        return {}


def save_settings(roster_start: datetime, roster_end: datetime, previous_roster_end: datetime) -> bool:
    """Save roster period settings"""
    try:
        data = {
            'roster_start': serialize_date(roster_start),
            'roster_end': serialize_date(roster_end),
            'previous_roster_end': serialize_date(previous_roster_end)
        }
        
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


def load_settings() -> Tuple[datetime, datetime, datetime]:
    """Load roster period settings"""
    # Defaults - 9-week rosters (63 days)
    # Current roster: 24 Jan - 27 Mar 2026
    default_start = datetime(2026, 1, 24)
    default_end = datetime(2026, 3, 27)
    default_prev_end = datetime(2026, 1, 23)
    
    if not SETTINGS_FILE.exists():
        return default_start, default_end, default_prev_end
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            data = json.load(f)
        
        return (
            deserialize_date(data.get('roster_start')) or default_start,
            deserialize_date(data.get('roster_end')) or default_end,
            deserialize_date(data.get('previous_roster_end')) or default_prev_end
        )
    except Exception as e:
        print(f"Error loading settings: {e}")
        return default_start, default_end, default_prev_end


def save_all(staff_list: List[StaffMember], current_roster: Dict[str, int], 
             roster_start: datetime, roster_end: datetime, previous_roster_end: datetime) -> bool:
    """Save everything at once"""
    success = True
    success &= save_staff_list(staff_list)
    success &= save_current_roster(current_roster)
    success &= save_settings(roster_start, roster_end, previous_roster_end)
    return success


def load_all() -> Tuple[List[StaffMember], Dict[str, int], datetime, datetime, datetime]:
    """Load everything at once"""
    staff_list = load_staff_list()
    current_roster = load_current_roster()
    roster_start, roster_end, prev_end = load_settings()
    
    return staff_list, current_roster, roster_start, roster_end, prev_end


def data_exists() -> bool:
    """Check if any saved data exists"""
    return STAFF_FILE.exists() or CURRENT_ROSTER_FILE.exists() or SETTINGS_FILE.exists()


def clear_all_data() -> bool:
    """Delete all saved data"""
    try:
        if STAFF_FILE.exists():
            STAFF_FILE.unlink()
        if CURRENT_ROSTER_FILE.exists():
            CURRENT_ROSTER_FILE.unlink()
        if SETTINGS_FILE.exists():
            SETTINGS_FILE.unlink()
        if REQUEST_HISTORY_FILE.exists():
            REQUEST_HISTORY_FILE.unlink()
        return True
    except Exception as e:
        print(f"Error clearing data: {e}")
        return False


def export_backup(filename: str = None) -> str:
    """
    Export all data to a single backup file
    
    Returns: Path to backup file
    """
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"roster_backup_{timestamp}.json"
    
    backup_path = STORAGE_DIR / filename
    
    try:
        staff_list = load_staff_list()
        current_roster = load_current_roster()
        roster_start, roster_end, prev_end = load_settings()
        
        backup_data = {
            'version': '1.0',
            'exported_at': serialize_date(datetime.now()),
            'staff': [serialize_staff(s) for s in staff_list],
            'current_roster': current_roster,
            'settings': {
                'roster_start': serialize_date(roster_start),
                'roster_end': serialize_date(roster_end),
                'previous_roster_end': serialize_date(prev_end)
            }
        }
        
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        return str(backup_path)
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None


def import_backup(filepath: str) -> bool:
    """
    Import data from a backup file
    
    Returns: True if successful
    """
    try:
        with open(filepath, 'r') as f:
            backup_data = json.load(f)
        
        # Extract data
        staff_list = [deserialize_staff(s) for s in backup_data.get('staff', [])]
        current_roster = backup_data.get('current_roster', {})
        settings = backup_data.get('settings', {})
        
        roster_start = deserialize_date(settings.get('roster_start')) or datetime(2026, 2, 21)
        roster_end = deserialize_date(settings.get('roster_end')) or datetime(2026, 3, 20)
        prev_end = deserialize_date(settings.get('previous_roster_end')) or datetime(2026, 2, 20)
        
        # Save imported data
        return save_all(staff_list, current_roster, roster_start, roster_end, prev_end)
    except Exception as e:
        print(f"Error importing backup: {e}")
        return False


def save_request_history(history_dict: Dict) -> bool:
    """
    Save request history to file
    
    Args:
        history_dict: Dict mapping staff_name -> RequestHistory dict
    
    Returns: True if successful
    """
    try:
        with open(REQUEST_HISTORY_FILE, 'w') as f:
            json.dump(history_dict, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving request history: {e}")
        return False


def load_request_history() -> Dict:
    """
    Load request history from file
    
    Returns: Dict mapping staff_name -> RequestHistory dict
    """
    if not REQUEST_HISTORY_FILE.exists():
        return {}
    
    try:
        with open(REQUEST_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading request history: {e}")
        return {}


def clear_request_history() -> bool:
    """Delete request history file"""
    try:
        if REQUEST_HISTORY_FILE.exists():
            REQUEST_HISTORY_FILE.unlink()
        return True
    except Exception as e:
        print(f"Error clearing request history: {e}")
        return False


# Demo/test
if __name__ == "__main__":
    print("=" * 60)
    print("ROSTER DATA STORAGE TEST")
    print("=" * 60)
    
    # Check if data exists
    if data_exists():
        print("\n✅ Saved data found!")
        
        staff_list, current_roster, start, end, prev = load_all()
        
        print(f"\nStaff: {len(staff_list)}")
        print(f"Current roster assignments: {len(current_roster)}")
        print(f"Roster period: {start.strftime('%d/%m/%Y')} to {end.strftime('%d/%m/%Y')}")
        
        if staff_list:
            print("\nStaff members:")
            for staff in staff_list[:5]:  # Show first 5
                print(f"  • {staff.name} ({staff.year})")
            if len(staff_list) > 5:
                print(f"  ... and {len(staff_list) - 5} more")
    else:
        print("\n⚠️ No saved data found")
        print("Data will be saved in: roster_data/")
    
    print("\n" + "=" * 60)
