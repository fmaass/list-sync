# 🔄 LLM HANDOVER PROMPT - List-Sync Email Reports Feature

**Date:** January 6, 2026  
**Context:** Continuing work on email reports feature  
**Previous Session:** Implemented blocklist feature + started email reports

---

## 📋 **TASK: Complete Email Reports Feature**

You are continuing development on the List-Sync project. A previous session implemented a blocklist feature (now complete and working in production) and started implementing an email reports feature that needs to be finished.

---

## ✅ **WHAT'S ALREADY COMPLETE:**

### **Blocklist Feature (Main Branch - DONE):**
- ✅ Fully implemented and working in production on Saturn
- ✅ 181 movies from Radarr loaded and filtering
- ✅ Auto-setup from environment variables (no web UI needed)
- ✅ Critical bug fixed (blocklist reload after setup)
- ✅ 5 commits on `main` branch, all pushed to GitHub
- ✅ PR-ready (no secrets committed)

**This feature is 100% complete. Do not modify unless asked.**

### **Email Reports Feature (Feature Branch - 90% DONE):**
- ✅ Reports module created (`list_sync/reports/`)
- ✅ Email sender using proc-watchdog pattern
- ✅ HTML report generator (Tautulli-style design)
- ✅ Integration point added to main.py
- ✅ Committed to `feature/email-reports` branch
- ✅ Pushed to GitHub
- ✅ Deployed to Saturn
- ⚠️ **NOT GENERATING REPORTS** - this is what you need to fix

---

## 🎯 **YOUR TASK:**

**Debug and fix the email report generation.**

### **The Problem:**
- Email reports are integrated into the sync flow
- Code is deployed to Saturn
- `EMAIL_REPORT_ENABLED=true` is set
- But no reports are being generated
- No error messages in logs (silent failure)

### **What Needs to Work:**
After each sync completes, generate an HTML email report showing:
1. **Overview:** Total items, in library, pending, blocked
2. **Per-list breakdown:** For each of 17 MDBList lists
   - Total movies
   - In Plex (count + %)
   - Missing (count), broken down by:
     - 🔄 Pending download
     - ⛔ Blocked by blocklist
     - ❌ Not found (couldn't match)
     - ❗ Processing errors
3. **Format:** Beautiful HTML (Tautulli newsletter style)
4. **Delivery:** Save to outbox (SMTP not configured yet)

---

## 📁 **PROJECT STRUCTURE:**

```
/Users/fabian/projects/list-sync/
├── list_sync/
│   ├── blocklist.py (COMPLETE - do not modify)
│   ├── main.py (has email integration at line ~1468)
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── email_sender.py (proc-watchdog pattern)
│   │   └── report_generator.py (HTML generation)
│   └── ...
├── radarr-exclusions-export/ (COMPLETE - do not modify)
└── ...

Saturn (Production):
  /volume1/docker-compose/stacks/kometa-listsync/
  └── docker-compose.yml (configured with EMAIL_REPORT_ENABLED=true)
```

---

## 🔍 **DEBUGGING STEPS:**

### **Step 1: Check if report function is being called**

```bash
ssh saturn.local "sudo /usr/local/bin/docker logs listsync 2>&1 | grep -i 'email report\\|send_sync_report\\|Attempting to generate'"
```

Expected: Should see "Attempting to generate email report..." after sync completes  
If not: Integration point isn't being reached

### **Step 2: Check for errors**

```bash
ssh saturn.local "sudo /usr/local/bin/docker logs listsync 2>&1 | grep -i 'failed to send email report'"
```

Expected: Error message with traceback  
Actual: Might be getting swallowed

### **Step 3: Test manually in container**

```bash
ssh saturn.local "sudo /usr/local/bin/docker exec listsync python3 << 'PY'
import sys
sys.path.insert(0, '/usr/src/app')
from list_sync.reports.report_generator import send_sync_report

# Create mock data
class MockResults:
    def __init__(self):
        self.total_items = 100
        self.start_time = 600
        self.results = {
            'already_available': 60,
            'already_requested': 30,
            'requested': 5,
            'skipped': 0,
            'blocked': 3,
            'not_found': 2,
            'error': 0
        }

mock_lists = [{'type': 'mdblist', 'id': 'test'}]
send_sync_report(MockResults(), mock_lists)
print('Report generation completed')
PY
"
```

Expected: Report saved to `/data/reports/outbox/`  
Check: `ssh saturn.local "sudo /usr/local/bin/docker exec listsync ls -la /data/reports/outbox/"`

### **Step 4: Check environment variables**

```bash
ssh saturn.local "sudo /usr/local/bin/docker exec listsync env | grep -E '(EMAIL|MAIL)'"
```

Expected:
- `EMAIL_REPORT_ENABLED=true`
- `MAIL_TO=fabian.maass@gmail.com`

### **Step 5: Check file generation**

If code runs but no file appears:
```bash
ssh saturn.local "sudo /usr/local/bin/docker exec listsync python3 -c 'from pathlib import Path; Path(\"/data/reports/outbox\").mkdir(parents=True, exist_ok=True); print(\"Directory created\")'"
```

Then retry report generation.

---

## 🔧 **LIKELY ISSUES & FIXES:**

### **Issue 1: Function not being called**

**Symptom:** No log messages about email reports  
**Cause:** dry_run flag or integration point not reached  
**Fix:** Check if `dry_run=False` in the run_sync() call

### **Issue 2: Silent exception in get_list_items()**

**Symptom:** HTML generates but with warnings about database  
**Cause:** Database query failing  
**Fix:** Wrap database queries in try/except, continue with empty stats

### **Issue 3: Permissions creating outbox directory**

**Symptom:** Error creating /data/reports/outbox/  
**Cause:** Permission denied  
**Fix:** Create directory in Dockerfile or use /tmp/

### **Issue 4: Missing import**

**Symptom:** ImportError or NameError  
**Cause:** Missing import statement  
**Fix:** Add proper imports to report_generator.py

---

## 🛠️ **HOW TO DEPLOY FIXES:**

### **1. Make changes locally:**
```bash
cd /Users/fabian/projects/list-sync
git checkout feature/email-reports
# Edit files
git add .
git commit -m "Fix: <description>"
git push
```

### **2. Build and deploy:**
```bash
# Clean Docker first
docker system prune -a -f --volumes
docker builder prune -f

# Build
docker build --platform linux/amd64 -t list-sync-custom:deploy -f Dockerfile .

# Transfer
docker save list-sync-custom:deploy | gzip | ssh saturn.local "cat > /volume1/docker/list-sync-deploy.tar.gz"

# Load
ssh saturn.local "sudo /usr/local/bin/docker load < /volume1/docker/list-sync-deploy.tar.gz && rm /volume1/docker/list-sync-deploy.tar.gz && sudo /usr/local/bin/docker tag list-sync-custom:deploy list-sync-custom:production"

# Deploy
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && sudo /usr/local/bin/docker-compose up -d --force-recreate listsync"
```

### **3. Trigger test sync:**
```bash
ssh saturn.local "curl -X POST http://localhost:4222/api/sync/trigger"
```

### **4. Monitor logs:**
```bash
ssh saturn.local "sudo /usr/local/bin/docker logs -f listsync | grep -E '(email|report|Attempting)'"
```

### **5. Check for report file:**
```bash
ssh saturn.local "ls -lth /volume1/docker/listsync/data/reports/outbox/"
```

---

## 📊 **CURRENT CONFIGURATION:**

### **Environment Variables (in docker-compose.yml):**
```yaml
environment:
  - EMAIL_REPORT_ENABLED=true
  - MAIL_TO=${MAIL_TO}  # Set in .env file
  - BLOCKLIST_ENABLED=true
  - BLOCKLIST_FILE=/data/blocklist.json
  # ... all other vars
```

### **.env file location:**
`/volume1/docker-compose/stacks/kometa-listsync/.env`

Contains:
- `MAIL_TO=fabian.maass@gmail.com`
- (No SMTP configured, so reports save to outbox)

---

## 🎯 **SUCCESS CRITERIA:**

When fixed, you should see:

1. **In logs after sync:**
   ```
   Attempting to generate email report...
   Email report module imported successfully
   send_sync_report() called
   EMAIL_REPORT_ENABLED: True
   Generating HTML report...
   HTML generated: XXXX bytes
   Sending email: List-Sync Report - 2026-01-06
   ✅ Sync report sent/saved: /data/reports/outbox/YYYYMMDD-HHMMSS-List-Sync_Report.eml
   ```

2. **Report file exists:**
   ```bash
   ssh saturn.local "ls /volume1/docker/listsync/data/reports/outbox/"
   ```
   Should show .eml file(s)

3. **Report content:**
   - Download: `scp saturn.local:/volume1/docker/listsync/data/reports/outbox/*.eml ~/Downloads/`
   - Open in email client or browser
   - Should show beautiful HTML with per-list breakdown

---

## 📖 **REFERENCE DOCUMENTS:**

**On your Mac:**
- `LIST_REPORT_DESIGN.md` - Complete design specification (21KB)
- `BLOCKLIST_IMPLEMENTATION_GUIDE.txt` - Blocklist implementation (31KB)
- `PREVENTION_PLAN.md` - Prevention strategies

**Code Reference:**
- `/Users/fabian/projects/proc-watchdog/sendmail.py` - Email pattern to follow
- `list_sync/reports/email_sender.py` - Already implements this pattern
- `list_sync/reports/report_generator.py` - HTML generation

---

## 🔑 **IMPORTANT CONTEXT:**

### **Why Email Reports Were Started:**

User wants to see which movies from their lists are missing from Plex, broken down by:
- Which list they came from
- Why they're missing (pending, blocked, not found, etc.)

Currently this info exists in the database but isn't easily viewable. The email report makes it accessible.

### **Design Inspiration:**

Based on:
- Tautulli newsletters (HTML email style)
- Plex Wrapped (big stats, visual design)
- Proc-watchdog reports (email delivery pattern)

### **Current Blocklist Context:**

- Radarr has 181 exclusions (movies not to download)
- Export service fetches these from Radarr API
- List-sync loads blocklist and filters before requesting
- This prevents bandwidth waste and repeated downloads
- **This is working correctly in production**

---

## 🚀 **QUICK START FOR NEW SESSION:**

```bash
# 1. Check out the feature branch
cd /Users/fabian/projects/list-sync
git checkout feature/email-reports
git pull origin feature/email-reports

# 2. Review the code
cat list_sync/reports/report_generator.py
cat list_sync/reports/email_sender.py

# 3. Check current deployment status
ssh saturn.local "sudo /usr/local/bin/docker ps | grep listsync"
ssh saturn.local "sudo /usr/local/bin/docker logs listsync --tail 100"

# 4. Test report generation manually (see Step 3 above)

# 5. Fix issues, commit, and deploy (see "How to Deploy" above)
```

---

## 🎓 **TIPS FOR DEBUGGING:**

1. **Add more logging:** The code already has debug logging added, check for those messages

2. **Test in isolation:** Run `send_sync_report()` manually with mock data first

3. **Check permissions:** Ensure `/data/reports/outbox/` can be created

4. **Verify integration point:** Make sure the code path actually reaches the email report section

5. **Check for silent exceptions:** The try/except might be swallowing errors - check logs carefully

---

## 🎨 **WHAT THE FINAL REPORT SHOULD LOOK LIKE:**

```
╔════════════════════════════════════════════════════════════════╗
║              LIST-SYNC REPORT - January 6, 2026                ║
╚════════════════════════════════════════════════════════════════╝

OVERVIEW:
  ✅ In Library:    1180 movies (65%)  
  🔄 Pending:        504 movies (28%)  
  ⛔ Blocked:        181 movies (10%)  

LIST BREAKDOWN (17 lists, sorted by coverage):

  📋 List 66765
     57 total | 45 in Plex (79%) | Missing: 12
     ▓▓▓▓▓▓▓▓░░ 79%
     Missing: 8 pending, 2 blocked, 2 not found

  📋 List 66767
     184 total | 120 in Plex (65%) | Missing: 64
     ▓▓▓▓▓▓░░░░ 65%
     Missing: 50 pending, 10 blocked, 4 not found

  ... (15 more lists)
```

---

## 📚 **USEFUL COMMANDS:**

### **Check Saturn Environment:**
```bash
ssh saturn.local "sudo /usr/local/bin/docker ps | grep listsync"
ssh saturn.local "sudo /usr/local/bin/docker logs listsync --tail 200"
ssh saturn.local "curl -s http://localhost:4222/api/blocklist/stats"
```

### **Check Database:**
```bash
ssh saturn.local "sudo /usr/local/bin/docker exec listsync python3 << 'PY'
import sqlite3
conn = sqlite3.connect('/data/list_sync.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM lists')
print(f'Lists: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM synced_items')
print(f'Items: {cursor.fetchone()[0]}')
PY
"
```

### **Force Sync (for testing):**
```bash
ssh saturn.local "curl -X POST http://localhost:4222/api/sync/trigger"
```

### **Check Email Config:**
```bash
ssh saturn.local "cat /volume1/docker-compose/stacks/kometa-listsync/.env | grep MAIL"
ssh saturn.local "sudo /usr/local/bin/docker exec listsync env | grep EMAIL"
```

---

## 🔐 **CREDENTIALS & SECRETS:**

**DO NOT COMMIT THESE:**
- Radarr API Key: `b96abe1b76384476b9fbf381ed6941d6`
- Seerr API Key: `MTc2MDA4NTk4OTYzMDI2MTA0ZDIzLTYyODQtNDdmMy1iYTUzLTcwOGRiZjllZTQ0Ng==`
- User email: `fabian.maass@gmail.com`

**Always use:** `${VARIABLE}` placeholders in code  
**Store in:** `.env` files on Saturn (not in Git)

---

## 📈 **EXPECTED BEHAVIOR:**

### **When Working Correctly:**

1. **Sync completes**
2. **Logs show:**
   ```
   Attempting to generate email report...
   Email report module imported successfully
   send_sync_report() called
   EMAIL_REPORT_ENABLED: True
   Generating HTML report...
   HTML generated: 5808 bytes
   ✅ Sync report sent/saved: /data/reports/outbox/20260106-152322-List-Sync_Report.eml
   ```

3. **File created:**
   `/volume1/docker/listsync/data/reports/outbox/20260106-HHMMSS-List-Sync_Report.eml`

4. **File contains:**
   - Valid .eml format
   - HTML content
   - Per-list breakdown
   - Beautiful styling

---

## 🐛 **KNOWN ISSUES TO CHECK:**

### **Issue 1: get_list_items() might fail**

**Location:** `list_sync/reports/report_generator.py` line ~35  
**Symptom:** "unable to open database file" in test  
**Fix:** May need to handle database not being accessible or query failing

### **Issue 2: Integration point might not be reached**

**Location:** `list_sync/main.py` line ~1468  
**Check:** Is this in the right place? After display_summary()?  
**Note:** There are multiple sync paths (full sync, single list sync)

### **Issue 3: Silent exception**

**Location:** Try/except block swallowing errors  
**Fix:** Already added better logging, check if it appears

### **Issue 4: Directory permissions**

**Symptom:** Can't create `/data/reports/outbox/`  
**Fix:** Ensure directory creation doesn't fail

---

## 🎯 **MINIMUM VIABLE FIX:**

If you can't get full HTML working quickly, implement this simple version:

```python
def send_sync_report(sync_results, synced_lists):
    """Simple text-based report"""
    import os
    from pathlib import Path
    
    if os.getenv('EMAIL_REPORT_ENABLED') != 'true':
        return
    
    # Create simple text report
    report = f"""
List-Sync Report - {datetime.now()}

Total Items: {sync_results.total_items}
In Library: {sync_results.results['already_available']}
Pending: {sync_results.results['already_requested']}
Blocked: {sync_results.results['blocked']}

Lists Processed: {len(synced_lists)}
"""
    
    # Save to file
    outbox = Path("/data/reports/outbox")
    outbox.mkdir(parents=True, exist_ok=True)
    
    filename = outbox / f"{time.strftime('%Y%m%d-%H%M%S')}-report.txt"
    with open(filename, 'w') as f:
        f.write(report)
    
    logger.info(f"Simple report saved: {filename}")
```

This proves the integration works, then enhance to HTML later.

---

## 📊 **VERIFICATION:**

### **After Fix, Verify:**

1. ✅ Report file created in outbox
2. ✅ Logs show report generation messages
3. ✅ HTML is valid and viewable
4. ✅ Per-list breakdown shows correctly
5. ✅ Missing items grouped by reason

### **Then:**

1. Commit fix to `feature/email-reports`
2. Push to GitHub
3. Merge to main (or keep as feature)
4. Document in README

---

## 💡 **HELPFUL CONTEXT:**

### **User's System:**
- **Saturn:** Synology NAS at `saturn.local`
- **List-Sync:** Custom build with blocklist feature
- **Radarr:** Movie management with 181 exclusions
- **Seerr:** Request management (custom build)
- **Plex:** Media server
- **Lists:** 17 MDBList curated movie lists

### **User's Goal:**
- Prevent blocked movies from being re-requested (DONE ✅)
- See per-list breakdown of what's missing (IN PROGRESS 90%)

### **User's Workflow:**
- All code via Git (no direct file copying)
- Docker image transfer for deployment
- Secrets in .env files (not committed)
- Professional commit messages (may PR upstream)

---

## ✅ **CHECKLIST FOR COMPLETION:**

- [ ] Debug why reports aren't generating
- [ ] Fix the issue
- [ ] Test report generation
- [ ] Verify report file created
- [ ] Verify HTML renders correctly
- [ ] Verify per-list breakdown works
- [ ] Commit and push to GitHub
- [ ] Merge to main (or document as beta feature)
- [ ] Update README with email report docs

---

## 🎉 **SUCCESS LOOKS LIKE:**

After each sync, user receives (or finds in outbox) a beautiful HTML email showing:
- Overview stats (in library, pending, blocked)
- Breakdown for each of their 17 lists
- Coverage % for each list
- Why movies are missing from each list
- Tautulli newsletter styling

---

## 📞 **IF YOU GET STUCK:**

1. **Check similar code:** `proc-watchdog/health_report.py` (complete working example)
2. **Simplify:** Start with text report, then add HTML
3. **Test manually:** Don't rely on sync triggering it
4. **Check logs verbosely:** Use `exc_info=True` in logging
5. **Ask user:** They've been very helpful and responsive

---

## 🎓 **FINAL NOTES:**

**The blocklist feature is the priority and it's DONE.**  
The email reports are a "nice to have" bonus feature.

If you can't fix it quickly, document what you tried and the user can finish it later. The critical work is complete!

**Estimated time to fix:** 1-2 hours if straightforward, up to 4 hours if complex

**Good luck!** 🚀

---

**Branch:** `feature/email-reports`  
**Status:** 90% complete, needs debugging  
**Priority:** Medium (blocklist is high priority and done)

