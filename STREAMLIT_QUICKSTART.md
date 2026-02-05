# Bay & Basin Paramedic Roster System
## Streamlit Web Interface - Quick Start Guide

## Installation

1. Make sure you have Python 3.9+ installed
2. Install Streamlit:
   ```bash
   pip install streamlit
   ```

## Running the App

From the directory containing all the roster files, run:

```bash
streamlit run roster_app.py
```

The app will automatically open in your web browser at `http://localhost:8501`

## App Features

### 1. 👤 Staff Request Page
**For Paramedics to submit roster requests**

- Enter your name, role, and year
- Choose request type:
  - **Specific Roster Line**: Request a specific line number (1-9)
  - **Specific Days Off**: Enter dates you need off, and the system shows which lines match
- Add leave periods if applicable
- Submit your request

The system will:
- Show which roster lines give you your requested days off
- Rank lines by best fit if no perfect match exists
- Store your request for the manager to process

### 2. 👔 Manager: Create Roster Page
**For managers to generate and approve rosters**

- Set roster period (start and end dates)
- Set minimum coverage requirements (default: 2 per shift)
- View all submitted staff requests
- Click "Generate Roster" to auto-assign staff to lines
- Review:
  - Line assignments (who's on which line)
  - Coverage analysis (gaps and shortfalls)
  - Coverage statistics (min/max/average per shift)
  - Individual staff schedules

**Coverage Checking:**
- Green box = All shifts adequately covered
- Red box = Coverage issues detected (lists specific dates/shifts)

**Individual Schedules:**
- Select a staff member from dropdown
- View their 28-day calendar with color-coded shifts:
  - ☀️ Yellow = Day shift
  - 🌙 Blue = Night shift
  - ⭕ Green = Off
  - 🏖️ Green = Leave

### 3. 🔍 Line Explorer Page
**For exploring roster lines and checking Award compliance**

- View any of the 9 roster lines in calendar format
- Check if a line complies with Award requirements
- Test line transitions:
  - Select current line and new line
  - Click "Check Transition"
  - See if changing lines violates consecutive day rules

**Award Compliance:**
- Checks minimum 2 days off per week
- Checks minimum 4 days off per fortnight
- Validates consecutive working days

## Understanding the 9 Roster Lines

The DDNNOOOO pattern (2 days, 2 nights, 5 off) creates 9 possible lines:

- **Line 1**: DDNNOOOOO (starts Day on Day 1)
- **Line 2**: ODDNNOOOO (starts Day on Day 2)  
- **Line 3**: OODDNNOOO (starts Day on Day 3)
- **Line 4**: OOODDNNOO (starts Day on Day 4)
- **Line 5**: OOOODDNNO (starts Day on Day 5)
- **Line 6**: OOOOODDNN (starts Day on Day 6)
- **Line 7**: NOOOOODDН (starts Night on Day 1, then Days on Day 7)
- **Line 8**: NNOOOOОDD (starts Night on Days 1-2)
- **Line 9**: ONNOOOODD (starts Off on Day 1)

## Color Coding

Throughout the app:
- 🟨 **Yellow** = Day shift (06:45-19:00)
- 🟦 **Blue** = Night shift (18:45-07:00)
- 🟩 **Green** = Off day / Leave
- 🟥 **Red** = Award violation / Coverage issue

## Tips for Use

### For Staff:
1. Submit your request early in the roster period
2. If requesting specific days off, be flexible (more dates = fewer matching lines)
3. Check the "Line Explorer" to see what each line looks like
4. Remember: Annual leave takes priority over roster requests

### For Managers:
1. Set the roster period first
2. Collect all staff requests before generating
3. Check coverage report for gaps
4. Use individual schedules to verify assignments
5. If coverage issues exist:
   - Add more staff
   - Adjust requested lines
   - Consider overtime for specific shifts

### Award Compliance:
- System automatically checks Award requirements
- Won't allow 8+ consecutive working days across roster boundaries
- Ensures minimum 2 days off per week (or 4 per fortnight)
- Validates 10-hour breaks between shifts

## Common Issues

**"No staff to roster!"**
- Add staff requests on the Staff Request page first

**Coverage shortfalls showing**
- Not enough staff for the roster period
- Some staff on leave
- Need to add more staff or adjust assignments

**Line transition violations**
- Changing from one line to another would create too many consecutive days
- Try a different line combination
- Check the Line Explorer to test transitions

## Data Management

**Session State:**
- All data stored in browser session
- Closing browser = data lost
- Use "Clear All Data" button to reset

**Future Enhancement:**
- Data persistence (save to file/database)
- Export to Excel
- Import from existing rosters

## Files Required

Make sure these files are in the same directory:
```
roster_app.py                  (this app)
roster_lines.py               (roster line logic)
roster_assignment.py          (staff assignment)
roster_boundary_validator.py  (Award compliance)
```

## Support

For questions or issues:
1. Check the Award requirements in ROSTER_SYSTEM_SUMMARY.md
2. Test line transitions in the Line Explorer
3. Review coverage requirements (minimum 2 per shift)

## Next Steps

Future enhancements planned:
- Excel export in your current roster format
- Import existing staff lists
- Email notifications for roster changes
- Mobile-friendly view
- Overtime tracking
- Shift swap requests
