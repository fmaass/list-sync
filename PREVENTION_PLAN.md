# 🛡️ PREVENTION PLAN - Never Let This Happen Again

## 🚨 **What Went Wrong:**

### **Double Failure:**
1. **List-Sync:** Blocklist not loaded (bug)
2. **Seerr:** Blacklist incomplete (only 3/153 items)

**Result:** Movies got through both defenses and were downloaded.

---

## ✅ **IMMEDIATE FIXES (Done):**

### **1. List-Sync Bug Fixed**
- ✅ Added blocklist reload after setup completes
- ✅ Committed to main (1660205)
- ✅ Pushed to GitHub
- ✅ Deployed to Saturn
- ⏳ Needs: Web UI setup to activate

### **2. Using Radarr Directly**
- ✅ Bypasses Seerr's incomplete sync
- ✅ Gets all 124 exclusions from source
- ✅ First line of defense

---

## 🚨 **CRITICAL NEXT STEPS:**

### **Step 1: IMMEDIATE CLEANUP (NOW)**

Run the cleanup script to remove blocked movies from Radarr:

```bash
# Transfer cleanup script
scp cleanup_blocked_movies.py saturn.local:/tmp/

# Run from Saturn
ssh saturn.local "cd /tmp && sudo /usr/local/bin/docker run --rm --network arr -v /tmp:/scripts python:3.11-alpine sh -c 'pip install requests && python3 /scripts/cleanup_blocked_movies.py'"
```

This will:
- Find all movies in Radarr that are on exclusion list
- Delete them including downloaded files
- Free up disk space

### **Step 2: Complete List-Sync Setup (NOW)**

Go to: `http://saturn.local:3222`
- Complete setup wizard
- Verify blocklist loads: `curl http://saturn.local:4222/api/blocklist/stats`
- Should show: `loaded=true, movie_count=124`

### **Step 3: Verify Seerr Blocklist Sync (URGENT)**

Check why Seerr only has 3-5 items when Radarr has 153:

```bash
# Check Seerr blacklist
curl -H "X-Api-Key: ..." "http://jellyseerr:5055/api/v1/blacklist?take=200"

# Should have 153 items, not 3
# If not, Seerr's sync is broken
```

### **Step 4: Schedule Export Service (TODAY)**

Ensure daily export from Radarr:

```bash
# Add to cron
ssh saturn.local "sudo crontab -e"

# Add:
30 2 * * * cd /path && docker run --rm radarr-exclusions-export
```

---

## 🛡️ **LONG-TERM PREVENTION:**

### **Priority 1: Auto-Setup from Env Vars** (CRITICAL)

Implement auto-migration to skip setup wizard:
- Prevents blocklist loading issues
- True infrastructure-as-code
- No manual intervention needed

**Code change needed in main.py:**
```python
if not config_manager.is_setup_complete():
    if config_manager.has_env_config():
        # Auto-migrate and continue
        config_manager.migrate_env_to_database()
        load_env_lists()
        config_manager.mark_setup_complete()
        load_blocklist()  # ← Ensure loaded!
```

### **Priority 2: Health Check** (HIGH)

Add startup health check that FAILS if blocklist not loaded:

```python
if BLOCKLIST_ENABLED and not blocklist_loaded:
    logger.error("CRITICAL: Blocklist enabled but not loaded!")
    sys.exit(1)  # Fail fast, don't sync
```

### **Priority 3: Monitoring** (MEDIUM)

Add alerts:
- API endpoint returns loaded=false → Alert
- Sync summary shows blocked=0 when it should have blocks → Alert
- Daily check via Discord webhook

### **Priority 4: Fix Seerr Sync** (MEDIUM)

Investigate why Seerr only has 3-5 items when it claims to sync 153:
- Check Seerr database directly
- Verify sync job is actually writing to database
- May be a bug in your custom Seerr build

---

## 📋 **IMMEDIATE CHECKLIST:**

Today (URGENT):
- [ ] Run cleanup script to remove blocked movies from Radarr
- [ ] Complete list-sync web UI setup
- [ ] Verify blocklist loaded (API shows 124 movies)
- [ ] Test: Trigger manual sync, watch for "⛔ BLOCKED" messages

This Week:
- [ ] Implement auto-setup from env vars (prevent wizard issues)
- [ ] Add blocklist health check (fail fast if not loaded)
- [ ] Schedule export service in cron
- [ ] Investigate Seerr sync issue (why only 3-5 items?)

This Month:
- [ ] Add monitoring/alerts for blocklist status
- [ ] Document recovery procedures
- [ ] Consider making blocklist REQUIRED (not optional)

---

## 🎯 **SUMMARY:**

**Problem:** Both defenses failed (list-sync + Seerr)  
**Cause:** List-sync bug + Seerr incomplete sync  
**Fix:** List-sync fixed, using Radarr directly  
**Cleanup:** Script created to remove blocked movies  
**Prevention:** Multiple layers (auto-setup, health check, monitoring)

**This will never happen again with these safeguards!** 🛡️
