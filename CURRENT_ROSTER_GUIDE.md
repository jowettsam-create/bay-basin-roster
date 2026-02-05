# Current Roster Feature Guide

## Overview

The app now has a **"Current Roster"** page that lets you:
1. Set what line each staff member is currently on
2. See the current roster coverage
3. When generating a new roster, staff default to staying on their current line

## How It Works

### **Workflow:**

1. **Set Current Roster** → Tell the system what line everyone is on now
2. **Add Staff Requests** → Staff request changes (or nothing if staying on same line)
3. **Generate Projected Roster** → System defaults people to their current line unless they requested a change
4. **Compare Current vs Projected** → See who's changing lines and who's staying

---

## Page 1: 📅 Current Roster

### **Purpose:**
Set what line each staff member is currently working.

### **What You'll See:**

**Previous Roster Period Ended:** (date picker)
- Set when the last roster period ended (default: 20/02/2026)

**Current Line Assignments:**
- Staff grouped by their current line
- Unassigned staff shown at top with ⚠️ warning

### **Assigning Staff to Current Lines:**

**Option 1: Individual Assignment**
```
⚠️ Unassigned (3 staff)
  
  Glenn Chandler (Para Yr6)
  [Assign to line: 1 ▼] [Set]
  
  Samuel Jowett (Para Yr6)
  [Assign to line: 3 ▼] [Set]
```

**Option 2: Bulk Assignment**
Scroll to "Quick Assignment" section:
```
Glenn Chandler (Para Yr6)    [Line 1 ▼]
Samuel Jowett (Para Yr6)     [Line 3 ▼]
Shane Orchard (Para Yr4)     [Line 1 ▼]
Jennifer Richards (Para Yr6) [Line 5 ▼]

[Save All Assignments]
```

**Option 3: Change Existing Assignment**
```
📋 Line 1 (2 staff)
  
  Glenn Chandler (Para Yr6)   [Change Line]
  Shane Orchard (Para Yr4)    [Change Line]
```

Click "Change Line" to unassign them, then reassign.

### **Current Roster Calendar:**

Shows coverage for the last week of the previous roster:
```
Date       | Day Shift | Night Shift
Mon 17/02  |     2     |     2
Tue 18/02  |     2     |     2
Wed 19/02  |     3     |     1
... etc ...
```

---

## Page 2: 👤 Staff Request (No Changes)

Staff still submit requests as before:
- Request specific line
- Request specific days off
- Set as fixed roster

**Key Change:**
- If staff DON'T submit a request, they'll default to their current line

---

## Page 3: 👔 Manager: Create Roster

### **Generate Roster Button:**
Click "🔄 Generate Roster" as before.

### **New: Current vs Projected Comparison**

After generating, you'll see a comparison table:

```
📊 Current vs Projected Line Assignments

Staff                | Current Line | Projected Line | Status
---------------------|--------------|----------------|---------------
Glenn Chandler       | Line 1       | Line 1         | ✅ No Change
Samuel Jowett        | Line 3       | Line 4         | 🔄 Changed
Shane Orchard        | Line 1       | Line 1         | ✅ No Change
Jennifer Richards    | Line 5       | Line 5         | ✅ No Change
Joel Pegram          | Not Set      | Line 7         | 🔄 Changed
```

**What This Shows:**
- ✅ **No Change** = Staff staying on same line
- 🔄 **Changed** = Staff moving to different line (either by request or to accommodate dates off)

### **Assignment Logic:**

**Priority Order:**
1. **Requested specific line?** → Assign to that line
2. **Requested dates off?** → Check if current line gives those days off
   - If yes → Keep on current line
   - If no → Find best matching line
3. **No request?** → Keep on current line

**Example:**
```
Glenn: Currently Line 1, no requests → Stays Line 1
Samuel: Currently Line 3, needs Feb 25-26 off
  - Line 3 doesn't give those days off
  - Line 4 does
  → Moves to Line 4
Jennifer: Currently Line 5, specifically requested Line 5 → Stays Line 5
```

---

## Typical Workflow

### **First Time Setup:**

**Step 1: Add All Staff**
- Go to "Staff Request" page
- Add all your staff (both rotating and fixed)

**Step 2: Set Current Roster**
- Go to "Current Roster" page
- Use "Quick Assignment" to set everyone's current line
- Click "Save All Assignments"

**Step 3: Generate Next Roster**
- Go to "Manager: Create Roster" page
- Set next roster period dates
- Click "Generate Roster"
- Everyone defaults to their current line

### **Subsequent Rosters:**

**Step 1: Staff Submit Requests**
- Staff go to "Staff Request" page
- Only submit if they want to change lines or need specific days off
- Most staff won't need to submit anything

**Step 2: Update Current Roster (Optional)**
- If roster periods have rolled over, update "Current Roster" page
- Usually you can just use the projected roster from last time

**Step 3: Generate New Roster**
- Go to "Manager: Create Roster"
- Click "Generate Roster"
- Review comparison table
- Check coverage

---

## Example Scenarios

### **Scenario 1: Normal Roll-Over (No Changes)**

**Current Roster:**
- Glenn: Line 1
- Samuel: Line 3
- Shane: Line 1
- Jennifer: Line 5

**Staff Requests:** None (everyone happy with current line)

**Projected Roster:**
- Glenn: Line 1 ✅ No Change
- Samuel: Line 3 ✅ No Change
- Shane: Line 1 ✅ No Change
- Jennifer: Line 5 ✅ No Change

**Result:** Everyone stays on their line!

---

### **Scenario 2: One Staff Needs Days Off**

**Current Roster:**
- Glenn: Line 1
- Samuel: Line 3
- Shane: Line 1
- Jennifer: Line 5

**Staff Requests:**
- Samuel requests Feb 25-26 off

**System Checks:**
- Does Line 3 give Feb 25-26 off? No
- Which lines give those days off? Lines 4, 5, 6

**Projected Roster:**
- Glenn: Line 1 ✅ No Change
- Samuel: Line 4 🔄 Changed (to get requested days)
- Shane: Line 1 ✅ No Change
- Jennifer: Line 5 ✅ No Change

---

### **Scenario 3: Staff Requests Line Change**

**Current Roster:**
- Glenn: Line 1
- Samuel: Line 3

**Staff Requests:**
- Glenn requests Line 7

**Projected Roster:**
- Glenn: Line 7 🔄 Changed (explicit request)
- Samuel: Line 3 ✅ No Change

---

### **Scenario 4: New Staff Member**

**Current Roster:**
- Glenn: Line 1
- Samuel: Line 3

**Staff Requests:**
- New hire Alex (no current line set)

**Projected Roster:**
- Glenn: Line 1 ✅ No Change
- Samuel: Line 3 ✅ No Change
- Alex: Line 2 (assigned based on coverage needs)

---

## Benefits

### **For Staff:**
✅ **Stability** - Stay on your current line unless you want to change  
✅ **Predictable** - Know what to expect  
✅ **Less Admin** - Only submit request if you need something different  

### **For Managers:**
✅ **Continuity** - Staff keep familiar patterns  
✅ **Clear Changes** - Comparison table shows who's moving  
✅ **Better Planning** - See current state before projecting next roster  
✅ **Audit Trail** - Track line changes over time  

### **For Rostering:**
✅ **Award Compliance** - Validates line transitions  
✅ **Coverage Optimization** - Changes only when needed  
✅ **Request Priority** - Explicit requests override defaults  

---

## Tips

### **Setting Up Current Roster:**

**Tip 1: Use Bulk Assignment**
Instead of assigning one-by-one, use "Quick Assignment" to set everyone at once.

**Tip 2: Copy from Last Projected**
After generating a roster, those assignments become your new "current" for next time.

**Tip 3: Check Coverage First**
Before generating new roster, verify current roster has good coverage using the calendar view.

### **Managing Requests:**

**Tip 4: "No Request" is Valid**
If staff don't submit anything, they stay on current line - that's intentional!

**Tip 5: Specific Line > Dates Off**
If someone requests both a line AND dates off, the line request takes priority.

**Tip 6: Review Comparison Table**
Always check the "Current vs Projected" table to catch unexpected changes.

---

## Sidebar Stats

The sidebar now shows:
```
Current Roster Period
Start: 21/02/2026
End: 20/03/2026

Staff Requests: 10
Current Assignments: 7/10
```

**Current Assignments:** How many staff have been assigned to lines in the "Current Roster" page.

---

## Data Persistence Note

**Currently:** Data resets when you close the browser.

**Future Enhancement:** Will save current roster and staff list to file so it persists between sessions.

**Workaround:** Take a screenshot of your "Current Roster" assignments or export the comparison table before closing.

---

## Troubleshooting

**Q: "Current Assignments" shows 0/10**
A: Go to "Current Roster" page and assign staff to lines.

**Q: Everyone showing as "Changed" in comparison**
A: Current roster wasn't set properly. Check "Current Roster" page.

**Q: Staff staying on same line even though they requested dates off**
A: Their current line already gives them those days off! System is optimizing to minimize changes.

**Q: New staff member not showing in Current Roster**
A: They need to be added via "Staff Request" page first.

---

Ready to use it? The workflow is:

1. **📅 Current Roster** - Set current lines
2. **👤 Staff Request** - Add any change requests
3. **👔 Create Roster** - Generate and compare
4. **📊 Review** - Check the comparison table
5. **✅ Approve** - Coverage looks good? Done!
