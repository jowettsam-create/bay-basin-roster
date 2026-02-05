# Intern Mentor Display - Teaming vs Cross-Exposure

## The Rule

When displaying intern mentors in the Manager page:

1. **Same Line = Teaming** - These paramedics are "teamed" with the intern (primary mentors)
2. **Different Lines = Cross-Exposure** - These paramedics work overlapping shifts but aren't on the same line

## Example Display

### Oliver Pritchard - Line 6

**Before (Incorrect):**
```
⚠️ No paramedic mentor on this line
```

**After (Correct):**
```
Cross-Line Exposure:
• Glenn Chandler (Line 3): 12 shifts
• Joel Pegram (Line 5): 8 shifts

✅ Working with 2 paramedics (varied exposure)
```

### Matt Pitt - Line 9

**Before:**
```
Current Mentor: Briana Car
✅ New mentor pairing
```

**After:**
```
Teamed Mentor(s) (Line 9):
• Briana Car: 28 shifts ✅ New pairing

✅ Working with 1 paramedic
```

### Diya Arangassery - Line 8

**Before:**
```
Current Mentor: Dave McColl
✅ New mentor pairing
```

**After:**
```
Teamed Mentor(s) (Line 8):
• Dave McColl: 28 shifts ✅ New pairing

Cross-Line Exposure:
• Jennifer Richards (Line 2): 5 shifts

✅ Working with 2 paramedics (varied exposure)
```

## How It Works

For each intern, the system:

1. **Generates their schedule** based on their assigned line
2. **For EVERY paramedic:**
   - Generates their schedule based on their assigned line
   - Compares day-by-day to find matching shifts (D-D or N-N)
   - Counts total overlapping shifts
3. **Categorizes mentors:**
   - Same line → "Teamed Mentor(s)"
   - Different line → "Cross-Line Exposure"
4. **Shows totals:**
   - 2+ paramedics → "varied exposure" ✅
   - 1 paramedic → "single mentor" ℹ️
   - 0 paramedics → "no mentors found" ⚠️

## Benefits

✅ **Accurate picture** - Shows ALL paramedics intern works with
✅ **Teaming clarity** - Distinguishes primary vs secondary mentors
✅ **Cross-line learning** - Recognizes exposure to multiple teaching styles
✅ **Shift-accurate** - Counts actual overlapping shifts, not just line assignments

## Code Location

File: `roster_app.py`
Function: `manager_roster_page()`
Section: "👨‍⚕️ Intern Assignments (Rotation System)"
Lines: ~1220-1290

The logic:
1. Generates intern schedule from their line
2. Loops through all paramedics
3. Generates each para schedule from their line
4. Counts matching shifts
5. Categorizes by same/different line
6. Displays with appropriate labels
