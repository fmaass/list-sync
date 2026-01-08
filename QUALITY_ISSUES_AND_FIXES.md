# Quality Issues Found & Fixes

## Issues Identified

### 1. Template Literals Not Interpolated
**Problem:** `{len(pending_requests)}` and `{len(list_breakdown)}` showing as literal text
**Location:** Lines 735, 831 in report_generator.py
**Fix:** Use f-string formatting

### 2. Blocked Count Showing 0
**Problem:** Overview shows 0 blocked items despite items being blocked
**Cause:** Not calculating blocked count from database correctly
**Fix:** Add blocked status to statistics calculation

### 3. Pending vs Open Requests Confusion
**Problem:** "Pending Download: 494" but "Open Requests: 0"
**Explanation:**
- "Pending Download" = already_requested (approved, waiting for Radarr)
- "Open Requests" = status=1 in Overseerr (awaiting approval)
- These are different statuses!
**Fix:** Better labeling and explanations

### 4. Misclassified Items
**Problem:** "I'm Your Man" showing as request_failed but actually blocked
**Cause:** Status in database might be incorrect
**Fix:** Verify blocklist is being checked and status recorded correctly

### 5. Template Variable Calculation
**Problem:** Overview stats calculated from SyncResults object, not database
**Cause:** SyncResults only has data from latest sync, not cumulative
**Fix:** Calculate all overview stats from database for accurate totals

## Fixes to Implement

1. Fix template literals (f-strings)
2. Calculate overview stats from database
3. Rename "Pending Download" to "Already Requested" for clarity
4. Verify blocklist status recording
5. Add explanatory text to clarify what each section means

## After Fixes - Strategic Review Needed

User requested high-level perspective on:
- What are we trying to achieve?
- What features don't make sense yet?
- What features are missing?
- What does the consumer want to see?
