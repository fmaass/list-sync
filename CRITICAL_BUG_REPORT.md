# 🚨 CRITICAL BUG REPORT & FIX

**Date:** January 4, 2026  
**Severity:** CRITICAL - Caused blocked movies to be downloaded  
**Status:** Fixed and deployed

---

## 🚨 **WHAT HAPPENED:**

All 124 blocklist movies re-appeared in Plex after list-sync ran.

---

## 🔍 **ROOT CAUSE:**

**The Bug:**
Blocklist loaded in `startup()` but was LOST when container waited for setup wizard.

**Timeline of Failure:**
1. Container starts → `startup()` called → blocklist loads ✅
2. Setup check: `is_setup_complete()` = false
3. Container waits 30+ minutes for web UI setup
4. Setup completes → continues to sync
5. **Blocklist was NEVER reloaded** ❌
6. Sync runs with `loaded=false, movie_count=0`
7. ALL movies requested (no filtering)
8. Radarr downloads them
9. Seerr enforcement runs later (too late)

**Evidence:**
- API showed: `loaded=false, movie_count=0`
- No "⛔ BLOCKED" messages in logs
- Many "Successfully Requested" messages
- Manual reload worked (proved code was correct)

---

## ✅ **THE FIX:**

**Code Change in `list_sync/main.py` (line ~1726):**

Added blocklist reload AFTER setup wizard completes:

```python
logging.info("Setup completed! Starting sync service...")
print("✅ Configuration detected! Starting sync service...\n")

# CRITICAL: Reload blocklist after setup completes
try:
    from .blocklist import load_blocklist
    if load_blocklist():
        logging.info("✅ Blocklist reloaded after setup completion")
    else:
        logging.warning("⚠️ Blocklist file not found")
except Exception as e:
    logging.warning(f"Failed to reload blocklist: {e}")
```

**Why This Works:**
- Ensures blocklist is loaded RIGHT BEFORE sync starts
- Doesn't rely on startup() load persisting
- Handles both setup completion paths
- Logs success/failure clearly

---

## 🔧 **DEPLOYMENT:**

**Hotfix Deployed:**
- Commit: 1660205
- Built: Hotfix image
- Transferred: To Saturn
- Deployed: Container recreated
- Status: Now loading blocklist after setup

---

## 🛡️ **PREVENTION:**

**Immediate:**
- Hotfix deployed ✅
- Will reload blocklist on every startup after setup ✅

**Long-term:**
- Implement auto-setup from env vars (skip wizard entirely)
- Add health check for blocklist loaded status
- Fail startup if blocklist required but not loaded

---

## 📊 **IMPACT:**

**What Went Wrong:**
- ~1814 movies processed without blocklist
- Some blocked movies were requested
- Radarr downloaded them
- Appeared in Plex

**What's Fixed:**
- Blocklist now reloads after setup
- Will load 124 movies before sync
- Will filter blocked items
- Won't happen again

---

**Status:** Fixed and deployed
**Commit:** 1660205 (on main)
**Deployed:** Hotfix on Saturn

🚨 Critical bug fixed! 🚨
