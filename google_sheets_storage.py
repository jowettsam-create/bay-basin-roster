"""
Google Sheets storage backend for roster data
Replaces JSON file storage with Google Sheets
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import pandas as pd

# Import existing data structures
from roster_assignment import StaffMember
from request_history import RequestHistory


class GoogleSheetsStorage:
    """Handles all data storage using Google Sheets"""
    
    def __init__(self):
        """Initialize Google Sheets connection"""
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Get credentials from Streamlit secrets
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open("Bay Basin Roster Data")
    
    def save_staff(self, staff_list: List[StaffMember]) -> bool:
        """Save staff list to Google Sheets"""
        try:
            sheet = self.spreadsheet.worksheet("Staff")
            
            # Convert staff to rows
            rows = [["name", "role", "year", "requested_line", "requested_dates_off", 
                     "assigned_line", "is_fixed_roster", "fixed_schedule", "leave_periods"]]
            
            for staff in staff_list:
                rows.append([
                    staff.name,
                    staff.role,
                    staff.year,
                    staff.requested_line or "",
                    json.dumps([d.isoformat() for d in staff.requested_dates_off]),
                    staff.assigned_line or "",
                    staff.is_fixed_roster,
                    json.dumps({k.isoformat(): v for k, v in staff.fixed_schedule.items()}),
                    json.dumps([(start.isoformat(), end.isoformat(), type_) 
                               for start, end, type_ in staff.leave_periods])
                ])
            
            # Clear and update
            sheet.clear()
            sheet.update('A1', rows)
            return True
        except Exception as e:
            st.error(f"Error saving staff: {e}")
            return False
    
    def load_staff(self) -> List[StaffMember]:
        """Load staff list from Google Sheets"""
        try:
            sheet = self.spreadsheet.worksheet("Staff")
            rows = sheet.get_all_values()
            
            if len(rows) <= 1:
                return []
            
            staff_list = []
            for row in rows[1:]:  # Skip header
                if not row[0]:  # Skip empty rows
                    continue
                
                staff = StaffMember(
                    name=row[0],
                    role=row[1],
                    year=row[2],
                    requested_line=int(row[3]) if row[3] else None,
                    requested_dates_off=[datetime.fromisoformat(d) for d in json.loads(row[4])] if row[4] else [],
                    assigned_line=int(row[5]) if row[5] else None,
                    is_fixed_roster=row[6].lower() == 'true',
                    fixed_schedule={datetime.fromisoformat(k): v for k, v in json.loads(row[7]).items()} if row[7] else {},
                    leave_periods=[(datetime.fromisoformat(s), datetime.fromisoformat(e), t) 
                                  for s, e, t in json.loads(row[8])] if row[8] else []
                )
                staff_list.append(staff)
            
            return staff_list
        except Exception as e:
            st.error(f"Error loading staff: {e}")
            return []
    
    def save_current_roster(self, current_roster: Dict[str, int]) -> bool:
        """Save current roster assignments to Google Sheets"""
        try:
            sheet = self.spreadsheet.worksheet("Current_Roster")
            
            rows = [["staff_name", "line_number"]]
            for name, line in current_roster.items():
                rows.append([name, line])
            
            sheet.clear()
            sheet.update('A1', rows)
            return True
        except Exception as e:
            st.error(f"Error saving roster: {e}")
            return False
    
    def load_current_roster(self) -> Dict[str, int]:
        """Load current roster assignments from Google Sheets"""
        try:
            sheet = self.spreadsheet.worksheet("Current_Roster")
            rows = sheet.get_all_values()
            
            if len(rows) <= 1:
                return {}
            
            roster = {}
            for row in rows[1:]:
                if row[0]:
                    roster[row[0]] = int(row[1])
            
            return roster
        except Exception as e:
            st.error(f"Error loading roster: {e}")
            return {}
    
    def save_settings(self, roster_start: datetime, roster_end: datetime, 
                     previous_roster_end: datetime) -> bool:
        """Save roster settings to Google Sheets"""
        try:
            sheet = self.spreadsheet.worksheet("Settings")
            
            rows = [
                ["setting", "value"],
                ["roster_start", roster_start.isoformat()],
                ["roster_end", roster_end.isoformat()],
                ["previous_roster_end", previous_roster_end.isoformat()]
            ]
            
            sheet.clear()
            sheet.update('A1', rows)
            return True
        except Exception as e:
            st.error(f"Error saving settings: {e}")
            return False
    
    def load_settings(self) -> Tuple[datetime, datetime, datetime]:
        """Load roster settings from Google Sheets"""
        try:
            sheet = self.spreadsheet.worksheet("Settings")
            rows = sheet.get_all_values()
            
            if len(rows) <= 1:
                # Default values
                return (
                    datetime(2026, 1, 24),
                    datetime(2026, 3, 27),
                    datetime(2026, 1, 23)
                )
            
            settings = {row[0]: row[1] for row in rows[1:]}
            
            return (
                datetime.fromisoformat(settings.get("roster_start", "2026-01-24T00:00:00")),
                datetime.fromisoformat(settings.get("roster_end", "2026-03-27T00:00:00")),
                datetime.fromisoformat(settings.get("previous_roster_end", "2026-01-23T00:00:00"))
            )
        except Exception as e:
            st.error(f"Error loading settings: {e}")
            return (
                datetime(2026, 1, 24),
                datetime(2026, 3, 27),
                datetime(2026, 1, 23)
            )
    
    def save_request_history(self, history_dict: Dict[str, dict]) -> bool:
        """Save request histories to Google Sheets"""
        try:
            sheet = self.spreadsheet.worksheet("Request_History")
            
            # Convert to JSON for storage
            rows = [["staff_name", "history_json"]]
            for name, history_data in history_dict.items():
                rows.append([name, json.dumps(history_data)])
            
            sheet.clear()
            sheet.update('A1', rows)
            return True
        except Exception as e:
            st.error(f"Error saving request history: {e}")
            return False
    
    def load_request_history(self) -> Dict[str, dict]:
        """Load request histories from Google Sheets"""
        try:
            sheet = self.spreadsheet.worksheet("Request_History")
            rows = sheet.get_all_values()
            
            if len(rows) <= 1:
                return {}
            
            histories = {}
            for row in rows[1:]:
                if row[0]:
                    histories[row[0]] = json.loads(row[1])
            
            return histories
        except Exception as e:
            st.error(f"Error loading request history: {e}")
            return {}
    
    def save_all(self, staff_list: List[StaffMember], current_roster: Dict[str, int],
                roster_start: datetime, roster_end: datetime, 
                previous_roster_end: datetime) -> bool:
        """Save all data to Google Sheets"""
        success = True
        success &= self.save_staff(staff_list)
        success &= self.save_current_roster(current_roster)
        success &= self.save_settings(roster_start, roster_end, previous_roster_end)
        return success
    
    def data_exists(self) -> bool:
        """Check if any data exists in sheets"""
        try:
            sheet = self.spreadsheet.worksheet("Staff")
            rows = sheet.get_all_values()
            return len(rows) > 1  # More than just header
        except:
            return False
    
    def clear_all_data(self) -> bool:
        """Clear all data from all sheets"""
        try:
            for sheet_name in ["Staff", "Current_Roster", "Request_History", "Settings"]:
                sheet = self.spreadsheet.worksheet(sheet_name)
                sheet.clear()
            return True
        except Exception as e:
            st.error(f"Error clearing data: {e}")
            return False

    def save_roster_history(self, roster_history: List[dict]) -> bool:
        """
        Save approved roster history to Google Sheets

        Each entry: {
            'period': 'Jan-Mar 2026',
            'start_date': '2026-01-24',
            'end_date': '2026-03-27',
            'assignments': {'Staff Name': line_number, ...},
            'approved_date': '2026-01-20',
            'status': 'approved'  # or 'draft'
        }
        """
        try:
            # Try to get or create the sheet
            try:
                sheet = self.spreadsheet.worksheet("Roster_History")
            except:
                sheet = self.spreadsheet.add_worksheet(title="Roster_History", rows=100, cols=10)

            rows = [["period", "start_date", "end_date", "assignments_json", "approved_date", "status"]]
            for entry in roster_history:
                rows.append([
                    entry.get('period', ''),
                    entry.get('start_date', ''),
                    entry.get('end_date', ''),
                    json.dumps(entry.get('assignments', {})),
                    entry.get('approved_date', ''),
                    entry.get('status', 'draft')
                ])

            sheet.clear()
            sheet.update('A1', rows)
            return True
        except Exception as e:
            st.error(f"Error saving roster history: {e}")
            return False

    def load_roster_history(self) -> List[dict]:
        """Load approved roster history from Google Sheets"""
        try:
            sheet = self.spreadsheet.worksheet("Roster_History")
            rows = sheet.get_all_values()

            if len(rows) <= 1:
                return []

            history = []
            for row in rows[1:]:
                if row[0]:  # Has period
                    history.append({
                        'period': row[0],
                        'start_date': row[1],
                        'end_date': row[2],
                        'assignments': json.loads(row[3]) if row[3] else {},
                        'approved_date': row[4] if len(row) > 4 else '',
                        'status': row[5] if len(row) > 5 else 'approved'
                    })

            return history
        except Exception as e:
            # Sheet might not exist yet
            return []

# Create a singleton instance
_storage = None

def get_storage():
    """Get or create storage instance"""
    global _storage
    if _storage is None:
        _storage = GoogleSheetsStorage()
    return _storage

# Wrapper functions to match old data_storage.py interface
def save_all(staff_list, current_roster, roster_start, roster_end, previous_roster_end):
    """Save all data - matches old interface"""
    storage = get_storage()
    return storage.save_all(staff_list, current_roster, roster_start, roster_end, previous_roster_end)

def load_all():
    """Load all data - matches old interface"""
    storage = get_storage()
    staff_list = storage.load_staff()
    current_roster = storage.load_current_roster()
    roster_start, roster_end, previous_roster_end = storage.load_settings()
    return staff_list, current_roster, roster_start, roster_end, previous_roster_end

def data_exists():
    """Check if data exists - matches old interface"""
    storage = get_storage()
    return storage.data_exists()

def clear_all_data():
    """Clear all data - matches old interface"""
    storage = get_storage()
    return storage.clear_all_data()

def save_request_history(history_dict):
    """Save request histories"""
    storage = get_storage()
    return storage.save_request_history(history_dict)

def load_request_history():
    """Load request histories"""
    storage = get_storage()
    return storage.load_request_history()

def save_roster_history(roster_history):
    """Save approved roster history"""
    storage = get_storage()
    return storage.save_roster_history(roster_history)

def load_roster_history():
    """Load approved roster history"""
    try:
        storage = get_storage()
        return storage.load_roster_history()
    except Exception:
        return []