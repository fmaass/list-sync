# List-Sync Blocklist Feature - Executive Summary

**Date:** January 1, 2026  
**Status:** Ready for Review & Approval

---

## 🎯 The Problem

You're running a sophisticated *arr stack where:
- **List-sync** polls public lists nightly (IMDb, Letterboxd, MDBList)
- **Seerr** manages all media requests to Radarr/Sonarr
- **Radarr** has exclusion lists and Seerr has blocklists
- **BUT**: List-sync doesn't check blocklists before requesting

**Result:** Hundreds of blocked movies get re-requested repeatedly, causing:
- ❌ Enormous download traffic
- ❌ Wasted Radarr/Sonarr resources
- ❌ Movies re-added despite being excluded

---

## ✅ The Solution

Add blocklist support to list-sync following a proven 3-step workflow:

```
┌─────────────────────────────────────────────────────────┐
│  NIGHTLY AUTOMATED WORKFLOW                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [02:00] Seerr Blocklist Sync (existing)               │
│          Radarr exclusions → Seerr blacklist            │
│                     ↓                                    │
│  [02:30] NEW: Blocklist Export Service                 │
│          Seerr blacklist → JSON file                    │
│                     ↓                                    │
│  [03:10] List-Sync (ENHANCED)                          │
│          Load blocklist → Filter blocked → Request      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Phases

### **Phase 1: Seerr Blocklist Export** (2-3 hours)
Create standalone service to export Seerr's blocklist:
- Python script to fetch from Seerr API
- Docker container running as cron job
- Exports to `/volume1/docker/listsync/data/blocklist.json`
- Simple JSON format: `{"movies": [12345, 67890, ...], "tv": [...]}`

### **Phase 2: List-Sync Integration** (4-6 hours)
Add blocklist checking to list-sync:
- Create `list_sync/blocklist.py` - Manager class
- Modify `list_sync/main.py` - Add filtering logic
- Update `list_sync/database.py` - Track blocked items
- Add configuration options

**Key Change:**
```python
# Before requesting, check if blocked:
if blocklist_manager.is_blocked(tmdb_id, media_type):
    logging.info(f"⛔ BLOCKED: '{title}' - on blocklist")
    return {"status": "blocked"}
```

### **Phase 3: Docker Deployment** (1-2 hours)
Build and deploy custom image (same as Seerr):
- Build locally: `docker build --platform linux/amd64 ...`
- Transfer to Saturn: `docker save | gzip | ssh ...`
- Deploy: Update compose to use custom image
- Verify: Check logs and test

### **Phase 4: Monitoring** (2-3 hours)
Add visibility and metrics:
- API endpoint: `/api/blocklist/stats`
- Sync summary shows blocked count
- Logs clearly show filtered items
- Database tracks blocked items

### **Phase 5: Testing** (3-4 hours)
Comprehensive validation:
- Unit tests for blocklist manager
- Integration tests with list-sync
- End-to-end test: Export → Filter → Verify
- Regression tests for edge cases

**Total Estimate: 12-18 hours** (can be done in phases over several days)

---

## 🏗️ Architecture Decisions

### ✅ **Design Choices Made:**

1. **Standalone Export Service**
   - ✅ Clean separation of concerns
   - ✅ Easy to test independently
   - ✅ Can run on different schedule
   - ✅ No changes to Seerr needed

2. **JSON File Format**
   - ✅ Simple and human-readable
   - ✅ Easy to debug
   - ✅ Low overhead
   - ✅ Can be manually edited if needed

3. **Filter Before Request**
   - ✅ Prevents network calls to Overseerr
   - ✅ Saves API rate limits
   - ✅ Reduces logs noise
   - ✅ Clear "blocked" status in database

4. **Follow Seerr Deployment Pattern**
   - ✅ Proven workflow you already use
   - ✅ Local source control
   - ✅ Custom Docker builds
   - ✅ Easy rollback

### 💡 **Configuration Options:**

```bash
# Enable/disable blocklist
BLOCKLIST_ENABLED=true

# Blocklist file path
BLOCKLIST_FILE=/data/blocklist.json

# Reload frequency
BLOCKLIST_RELOAD_HOURS=24

# Seerr connection (for export service)
SEERR_URL=http://jellyseerr:5055
SEERR_API_KEY=your-key-here
```

---

## 📊 Expected Results

### **Before Blocklist:**
- 🔴 1000+ movies from lists
- 🔴 200+ blocked movies re-requested
- 🔴 Massive download traffic
- 🔴 Radarr/Sonarr processing wasted items

### **After Blocklist:**
- ✅ 1000+ movies from lists
- ✅ 200+ blocked movies FILTERED OUT
- ✅ Only 800 valid requests made
- ✅ Zero traffic on blocked items
- ✅ Clean Radarr queue

---

## 🔄 Deployment Workflow

Following your proven Seerr process:

```bash
# 1. Clean Docker
docker system prune -a -f --volumes

# 2. Build custom image
cd /Users/fabian/projects/list-sync
docker build --platform linux/amd64 \
  -t list-sync-custom:deploy .

# 3. Transfer to Saturn
docker save list-sync-custom:deploy | gzip | \
  ssh saturn.local "cat > /volume1/docker/list-sync-deploy.tar.gz"

# 4. Load and deploy
ssh saturn.local "
  sudo docker load < /volume1/docker/list-sync-deploy.tar.gz && \
  sudo docker tag list-sync-custom:deploy list-sync-custom:production && \
  cd /volume1/docker-compose/stacks/kometa-listsync && \
  sudo docker-compose up -d --force-recreate listsync
"

# 5. Verify
ssh saturn.local "sudo docker logs -f listsync"
```

---

## 🛡️ Safety & Rollback

### **Safety Measures:**
- ✅ Each phase tested independently
- ✅ Blocklist can be disabled via config
- ✅ Missing blocklist = graceful fallback (warning only)
- ✅ Git version control for all changes
- ✅ Database tracks all filtered items

### **Rollback Plan:**
```bash
# Revert to official image (30 seconds)
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && \
  sudo sed -i 's/list-sync-custom:production/ghcr.io\/woahai321\/list-sync:latest/' docker-compose.yml && \
  sudo docker-compose up -d --force-recreate listsync"
```

---

## 📁 Files to Create/Modify

### **New Files:**
```
list_sync/
├── blocklist.py (NEW - 150 lines)
└── LISTSYNC_DEPLOYMENT_WORKFLOW.md (NEW - documentation)

scripts/
├── build-and-deploy.sh (NEW - deployment automation)
└── verify_blocklist.py (NEW - validation tool)

tests/
├── test_blocklist.py (NEW - unit tests)
└── test_blocklist_integration.py (NEW - integration tests)

Saturn: /volume1/docker-compose/stacks/kometa-listsync/
└── seerr-export/ (NEW directory)
    ├── Dockerfile
    ├── export_seerr_blocklist.py
    └── requirements.txt
```

### **Modified Files:**
```
list_sync/
├── main.py (MODIFY - add blocklist integration, ~20 lines)
├── config.py (MODIFY - add blocklist config, ~10 lines)
├── database.py (MODIFY - add blocked status, ~5 lines)
└── api_server.py (MODIFY - add stats endpoint, ~20 lines)

Saturn: /volume1/docker-compose/stacks/kometa-listsync/
└── docker-compose.yml (MODIFY - use custom image, ~5 lines)
```

**Total new code: ~400 lines**  
**Total modifications: ~60 lines**

---

## 🎓 What You'll Learn

This project demonstrates:
- ✅ Building custom Docker images for production
- ✅ Multi-container orchestration
- ✅ API integration between services
- ✅ Database-driven filtering logic
- ✅ Automated deployment workflows
- ✅ Production monitoring and metrics

---

## 🚀 Next Steps

### **Decision Points:**

1. **Approve Architecture?**
   - ✅ Standalone export service
   - ✅ JSON file format
   - ✅ Filter in list-sync
   - ✅ Custom Docker image

2. **Approve Phases?**
   - Phase 1: Seerr export (2-3h)
   - Phase 2: List-sync integration (4-6h)
   - Phase 3: Deployment (1-2h)
   - Phase 4: Monitoring (2-3h)
   - Phase 5: Testing (3-4h)

3. **Approve Timeline?**
   - Can be done in phases over multiple days
   - Each phase independently testable
   - Total: 12-18 hours work

### **Questions to Resolve:**

1. ✅ **Export Format**: JSON file with TMDB IDs (simple & effective)
2. ✅ **Filter Scope**: Movies and TV shows (configurable)
3. ✅ **Missing Blocklist**: Warning only, continue sync
4. ✅ **Reload Frequency**: 24 hours (configurable)
5. ❓ **Force Override**: Do we need manual override capability?
6. ❓ **Web UI**: Do we need blocklist management UI?

### **Ready to Start?**

Once you approve this plan, we can:
1. ✅ Start Phase 1: Create Seerr export service
2. ✅ Test export locally
3. ✅ Deploy to Saturn
4. ✅ Move to Phase 2: List-sync integration

---

## 📚 Documentation

**Full Details:** See `BLOCKLIST_FEATURE_PLAN.md` (comprehensive 400+ line spec)

**This Summary:** High-level overview for decision making

**Deployment Guide:** Will create `LISTSYNC_DEPLOYMENT_WORKFLOW.md` (modeled after Seerr)

---

## 💡 Why This Approach Works

1. **Proven Pattern**: Same workflow as your Seerr build
2. **Incremental**: Each phase is independently testable
3. **Safe**: Easy rollback, no breaking changes
4. **Maintainable**: Clean code, well-documented
5. **Scalable**: Can extend to support more sources

---

**Status: ⏸️ Awaiting Your Review & Approval**

Please review:
- ✅ Architecture makes sense?
- ✅ Phases are clear and achievable?
- ✅ Timeline is reasonable?
- ✅ Ready to proceed with Phase 1?

Once approved, we can start implementation immediately! 🚀

