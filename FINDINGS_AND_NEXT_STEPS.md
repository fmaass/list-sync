# 🔍 Email Reports - Findings & Next Steps

**Date:** January 7, 2026  
**Status:** Feature complete, but data issue discovered

---

## 🐛 BUG DISCOVERED: Status Overwriting

### The Problem

**Symptom:** Reports show 100% in library (all items "skipped")  
**Root Cause:** `should_sync_item()` check overwrites correct statuses

### What's Happening:

```
Sync 1 (10:20):
  ✓ Items processed with correct statuses
  ✓ Database shows: already_available, already_requested, blocked, etc.

Sync 2 (10:50):
  ✗ Items marked as "recently synced"
  ✗ Status overwritten to "skipped" WITHOUT checking actual status
  ✗ Database now shows: ALL items = "skipped"
```

**Code Location:** `list_sync/main.py` lines 678-683

```python
if not should_sync_item(overseerr_id):
    logging.info(f"⏭️  SKIP: Recently synced (within skip window)")
    save_sync_result(..., "skipped", ...)  # ← BUG: Overwrites real status!
    return {"title": title, "status": "skipped", ...}
```

### The Fix Needed

**Option 1: Don't overwrite status when skipping**
```python
if not should_sync_item(overseerr_id):
    # Don't save or update - just skip processing
    # Keep existing status in database
    return {"title": title, "status": "recently_synced", ...}
```

**Option 2: Check status but don't re-request**
```python
if not should_sync_item(overseerr_id):
    # Still check current status from Overseerr
    is_available, is_requested, _ = overseerr_client.get_media_status(...)
    
    # Determine actual status
    if is_available:
        status = "already_available"
    elif is_requested:
        status = "already_requested"
    else:
        status = "unknown"
    
    # Save with REAL status, not "skipped"
    save_sync_result(..., status, ...)
```

**Recommendation:** Option 2 (check status but don't re-request)

---

## ✅ What's Working

1. **Email delivery:** SMTP working perfectly
2. **Daily scheduling:** 3am reports configured
3. **Enhanced HTML:** Movie titles showing correctly
4. **PDF generation:** 35KB PDFs with complete data
5. **Beautiful design:** Tautulli-style formatting

---

## ❌ What's Not Working

1. **Status accuracy:** Items incorrectly marked as "skipped"
2. **Data persistence:** Database location inconsistency (`/data` vs `/usr/src/app/data`)

---

## 🎯 Immediate Actions Needed

### 1. Fix Status Overwriting Bug

**File:** `list_sync/main.py`  
**Lines:** 678-683

**Change:**
```python
# BEFORE (Current - buggy):
if not should_sync_item(overseerr_id):
    save_sync_result(title, media_type, imdb_id, overseerr_id, "skipped", ...)
    return {"title": title, "status": "skipped", ...}

# AFTER (Fixed):
if not should_sync_item(overseerr_id):
    # Check actual status without re-requesting
    is_available, is_requested, _ = overseerr_client.get_media_status(overseerr_id, media_type)
    
    if is_available:
        status = "already_available"
    elif is_requested:
        status = "already_requested"  
    else:
        status = "not_requested"  # Rare edge case
    
    # Save with REAL status
    for source_list in source_lists:
        save_sync_result(title, media_type, imdb_id, overseerr_id, status, ...)
    
    return {"title": title, "status": status, ...}
```

### 2. Test with Sample Data (Dev Iteration)

For faster development, use the sample data scripts I created:
- `create_sample_data.sh`
- `test_report_with_sample.sh`

This allows < 1 second testing vs 20+ minute syncs.

---

## 📊 Expected Real Data (After Fix)

Based on the 10:20 sync logs (before bug overwrote statuses):

```
Total: 1788 items

Already Available:  ~1150 (64%)  ← In Plex
Already Requested:  ~495 (28%)   ← Pending in Overseerr  
Blocked:            ~90 (5%)     ← On Radarr blocklist
Not Found:          ~48 (3%)     ← Couldn't match
Errors:             ~5 (<1%)     ← Processing errors
```

---

## 🎬 What Enhanced Reports Will Show (After Fix)

```
📋 List 66765 - Top Action
  45/57 in library (79%)
  
  Missing Items (12):
  
  🔄 Pending Download (8 movies):
    • The Matrix Resurrections (2021)
    • Dune: Part Two (2024)
    • Blade Runner 2099 (2025)
    • The Northman (2022)
    • Mad Max Prequel (2025)
    ... and 3 more pending
  
  ⛔ Blocked (2 movies):
    • Bad Sequel 7 (2020)
    • Cash Grab Reboot (2021)
  
  ❌ Not Found (2 movies):
    • Obscure Film (2023)
    • Foreign Title (2022)

+ PDF Attachment with ALL movie titles!
```

---

## 🚀 Recommended Next Steps

### Immediate (Now):
1. **Fix the status bug** in `process_media_item()` 
2. **Run one clean sync** to get correct data
3. **Generate report** with accurate statuses
4. **Verify** you receive diverse data (not 100%)

### Short-term (This Week):
1. Create development testing framework
2. Document the bug and fix
3. Consider PR to upstream list-sync

### Long-term (Future):
1. Database path consolidation (`/data` vs `/usr/src/app/data`)
2. Add database health checks
3. Monitor status accuracy over time

---

## 💬 My Recommendation

**Let me fix the status bug right now**, then trigger one final sync and send you a report with REAL, accurate data showing actual movie titles for pending/blocked/not found items.

This will take:
- 15 minutes to fix the bug
- 20 minutes for sync to complete
- 1 minute to generate and send report

**Total:** ~35 minutes to give you accurate, actionable email reports

**Proceed with the fix?**

---

**Created:** January 7, 2026  
**Priority:** High (blocks accurate reporting)  
**Impact:** All email reports currently inaccurate

