# List-Sync Blocklist Feature - Complete Implementation Plan

**Date:** January 1, 2026  
**Status:** Planning & Architecture Phase  
**Goal:** Add blocklist support to list-sync to prevent re-requesting blocked movies

---

## Executive Summary

This document outlines the complete plan to add blocklist functionality to list-sync, preventing movies on Seerr's blocklist from being repeatedly requested. The implementation will follow the same proven deployment workflow as your custom Seerr build, using local source code, Docker builds, and remote deployment to Saturn.

---

## Current Infrastructure Analysis

### 1. **Your *arr Stack** (`/volume1/docker-compose/stacks/sonarr-radarr`)
- **Jellyseerr (Custom Seerr Build)**: Handles all media requests
  - Image: `seerr-radarr-blocklist:test` (custom build)
  - Has built-in blocklist sync from Radarr exclusions
  - Stores blacklist in SQLite database (Blacklist entity)
  - API exposes blacklist at `/api/v1/settings/radarr` endpoint
- **Radarr**: Movie management with exclusion lists
- **Sonarr (2 instances)**: TV show management
- All connected via `arr` Docker network

### 2. **Your List-Sync Stack** (`/volume1/docker-compose/stacks/kometa-listsync`)
- **ListSync**: Currently uses `ghcr.io/woahai321/list-sync:latest`
  - Syncs public lists (IMDb, Letterboxd, MDBList, etc.)
  - Makes requests directly to Jellyseerr/Overseerr
  - **NO blocklist checking currently implemented**
  - Runs nightly syncs via SYNC_INTERVAL
- **Kometa**: Media collection management
- **Radarr-Sync**: Queue cleaner for stuck downloads

### 3. **The Problem**
Seerr has blocklists, but list-sync doesn't consult them before requesting. This leads to:
- Hundreds of blocked movies being re-requested repeatedly
- Massive download traffic
- Wasted resources on Radarr/Sonarr
- Movies getting re-added despite being on exclusion lists

### 4. **The Solution Architecture**

```
┌────────────────────────────────────────────────────────────┐
│  NIGHTLY SYNC WORKFLOW                                      │
├────────────────────────────────────────────────────────────┤
│                                                              │
│  1. [02:00] Seerr Blocklist Sync Job (existing)            │
│      ├─ Radarr exclusions → Seerr blacklist                │
│      └─ Seerr stores: {tmdbId, title, mediaType, tags}     │
│                                                              │
│  2. [03:00] **NEW** Blocklist Export Job                   │
│      ├─ Export Seerr blacklist via API                     │
│      ├─ Save to: /volume1/docker/listsync/blocklist.json   │
│      └─ Format: {"movies": [tmdbId1, tmdbId2, ...]}        │
│                                                              │
│  3. [03:10] List-Sync Job (ENHANCED)                       │
│      ├─ Load blocklist.json                                 │
│      ├─ Fetch items from configured lists                   │
│      ├─ **Filter out blocked items** (NEW)                 │
│      └─ Request remaining items to Overseerr               │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

---

## Deployment Strategy

### **Local Development → Remote Deployment**
Following your proven Seerr workflow:

1. **Local Source**: `/Users/fabian/projects/list-sync` (this repo)
2. **Build Locally**: Docker build on your Mac (AMD64 platform)
3. **Transfer**: Compressed image → Saturn via SSH
4. **Deploy**: Load image & recreate container on Saturn
5. **Verify**: Check logs and test blocklist filtering

### **Custom Image Strategy**
- Base: `list-sync-custom:deploy` (similar to `seerr-radarr-blocklist:deploy`)
- Tag for Saturn: `list-sync-custom:production`
- Update compose to use custom image instead of ghcr.io

---

## Implementation Phases

### **PHASE 1: Seerr Blocklist Export Service** ✅ Ready to Start
**Goal:** Create a standalone service to export Seerr's blocklist to JSON

**Components:**
1. **Python Script**: `export_seerr_blocklist.py`
   - Location: `/volume1/docker-compose/stacks/kometa-listsync/seerr-export/`
   - Fetch blocklist from Seerr API
   - Export to shared volume JSON file
   - Handle movies and TV shows separately

2. **Docker Container**: `seerr-blocklist-exporter`
   - Runs as cron job (daily at 02:30)
   - Lightweight Python container
   - Mounted volume: `/volume1/docker/listsync/data`

3. **API Integration**:
   ```python
   # Seerr API endpoint
   GET /api/v1/blacklist?mediaType=movie
   Response: [
     {
       "id": 1,
       "tmdbId": 12345,
       "mediaType": "movie",
       "title": "Example Movie",
       "blacklistedTags": "radarr-sync-1-456"
     }
   ]
   ```

4. **Output Format** (`blocklist.json`):
   ```json
   {
     "version": "1.0",
     "exported_at": "2026-01-01T02:30:00Z",
     "source": "seerr",
     "movies": [12345, 67890, ...],
     "tv": [11111, 22222, ...],
     "total_count": 1234
   }
   ```

**Success Criteria:**
- [ ] Blocklist exports successfully to JSON
- [ ] File is accessible from list-sync container
- [ ] Runs daily without manual intervention
- [ ] Logs show export statistics

---

### **PHASE 2: List-Sync Blocklist Integration** ✅ Core Feature
**Goal:** Add blocklist loading and filtering to list-sync

**Files to Modify:**
1. `list_sync/main.py`
   - Add `load_blocklist()` function
   - Add `is_blocked()` check in `process_media_item()`
   - Filter items before requesting

2. `list_sync/database.py`
   - Add blocklist cache table
   - Track blocked items that were filtered

3. `list_sync/config.py`
   - Add `BLOCKLIST_FILE` path configuration
   - Add `BLOCKLIST_ENABLED` flag

**Implementation Details:**

```python
# list_sync/blocklist.py (NEW FILE)
import json
import logging
from pathlib import Path
from typing import Set, Optional
from datetime import datetime, timedelta

class BlocklistManager:
    """Manages blocklist loading and checking"""
    
    def __init__(self, blocklist_path: str = "data/blocklist.json"):
        self.blocklist_path = Path(blocklist_path)
        self.movie_blocklist: Set[int] = set()
        self.tv_blocklist: Set[int] = set()
        self.loaded_at: Optional[datetime] = None
        self.enabled = True
        
    def load(self) -> bool:
        """Load blocklist from JSON file"""
        try:
            if not self.blocklist_path.exists():
                logging.warning(f"Blocklist file not found: {self.blocklist_path}")
                return False
                
            with open(self.blocklist_path, 'r') as f:
                data = json.load(f)
                
            self.movie_blocklist = set(data.get('movies', []))
            self.tv_blocklist = set(data.get('tv', []))
            self.loaded_at = datetime.now()
            
            logging.info(f"Loaded blocklist: {len(self.movie_blocklist)} movies, "
                        f"{len(self.tv_blocklist)} TV shows")
            return True
            
        except Exception as e:
            logging.error(f"Failed to load blocklist: {e}")
            return False
    
    def is_blocked(self, tmdb_id: int, media_type: str) -> bool:
        """Check if item is blocked"""
        if not self.enabled:
            return False
            
        if media_type == 'movie':
            return tmdb_id in self.movie_blocklist
        elif media_type == 'tv':
            return tmdb_id in self.tv_blocklist
        return False
    
    def should_reload(self, max_age_hours: int = 24) -> bool:
        """Check if blocklist should be reloaded"""
        if not self.loaded_at:
            return True
        age = datetime.now() - self.loaded_at
        return age > timedelta(hours=max_age_hours)
```

**Integration into main.py:**

```python
# In process_media_item() function
def process_media_item(item, overseerr_client, dry_run, is_4k=False, 
                       list_type=None, list_id=None, blocklist_manager=None):
    """Process media item with blocklist check"""
    
    title = item.get('title', 'Unknown Title').strip()
    media_type = item.get('media_type', 'unknown')
    tmdb_id = item.get('tmdb_id')
    
    # NEW: Blocklist check
    if blocklist_manager and tmdb_id:
        if blocklist_manager.is_blocked(tmdb_id, media_type):
            logging.info(f"⛔ BLOCKED: '{title}' (TMDB: {tmdb_id}) - on blocklist")
            # Save to database as "blocked"
            for source_list in get_source_lists_from_item(item, list_type, list_id):
                save_sync_result(title, media_type, item.get('imdb_id'), None, 
                               "blocked", item.get('year'), tmdb_id, 
                               source_list['type'], source_list['id'])
            return {"title": title, "status": "blocked", "year": item.get('year'), 
                   "media_type": media_type}
    
    # Continue with normal processing...
    [existing code]
```

**Success Criteria:**
- [ ] Blocklist loads on startup
- [ ] Blocked items are filtered out before requests
- [ ] Logs show "BLOCKED" messages for filtered items
- [ ] Database tracks blocked items with status="blocked"
- [ ] Sync summary shows blocked count

---

### **PHASE 3: Docker Build & Deployment** ✅ Production Ready
**Goal:** Create custom Docker image and deploy to Saturn

**Files to Create:**

1. **Deployment Workflow** (`LISTSYNC_DEPLOYMENT_WORKFLOW.md`):
   ```markdown
   # List-Sync Deployment Workflow
   
   ## Pre-Deployment: Docker Cleanup
   ```bash
   docker system prune -a -f --volumes
   docker builder prune -f
   ```
   
   ## Build Custom Image
   ```bash
   cd /Users/fabian/projects/list-sync
   
   docker build \
     --platform linux/amd64 \
     --build-arg COMMIT_TAG="$(git rev-parse --short HEAD)-$(date +%s)" \
     -t list-sync-custom:deploy \
     -f Dockerfile \
     .
   ```
   
   ## Transfer to Saturn
   ```bash
   docker save list-sync-custom:deploy | gzip | \
     ssh saturn.local "cat > /volume1/docker/list-sync-deploy.tar.gz"
   
   ssh saturn.local "sudo /usr/local/bin/docker load < /volume1/docker/list-sync-deploy.tar.gz && \
     rm /volume1/docker/list-sync-deploy.tar.gz && \
     sudo /usr/local/bin/docker tag list-sync-custom:deploy list-sync-custom:production"
   ```
   
   ## Deploy on Saturn
   ```bash
   ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && \
     sudo /usr/local/bin/docker-compose up -d --force-recreate listsync"
   ```
   
   ## Verify
   ```bash
   ssh saturn.local "sudo /usr/local/bin/docker logs listsync --tail 100"
   ```
   ```

2. **Updated docker-compose.yml** (on Saturn):
   ```yaml
   services:
     listsync:
       image: list-sync-custom:production  # ← CHANGED from ghcr.io
       container_name: listsync
       # ... rest unchanged ...
       volumes:
         - /volume1/docker/listsync/data:/data  # ← Ensure this exists
         - /volume1/docker/listsync/blocklist.json:/data/blocklist.json:ro  # ← NEW
       labels:
         - com.centurylinklabs.watchtower.enable=false  # ← CHANGED
   ```

3. **Build Script** (`scripts/build-and-deploy.sh`):
   ```bash
   #!/bin/bash
   set -e
   
   echo "🧹 Cleaning Docker..."
   docker system prune -a -f --volumes
   docker builder prune -f
   
   echo "🔨 Building list-sync custom image..."
   docker build --platform linux/amd64 \
     --build-arg COMMIT_TAG="$(git rev-parse --short HEAD)-$(date +%s)" \
     -t list-sync-custom:deploy \
     -f Dockerfile .
   
   echo "📦 Transferring to Saturn..."
   docker save list-sync-custom:deploy | gzip | \
     ssh saturn.local "cat > /volume1/docker/list-sync-deploy.tar.gz"
   
   echo "🚀 Deploying on Saturn..."
   ssh saturn.local "
     sudo /usr/local/bin/docker load < /volume1/docker/list-sync-deploy.tar.gz && \
     rm /volume1/docker/list-sync-deploy.tar.gz && \
     sudo /usr/local/bin/docker tag list-sync-custom:deploy list-sync-custom:production && \
     cd /volume1/docker-compose/stacks/kometa-listsync && \
     sudo /usr/local/bin/docker-compose up -d --force-recreate listsync
   "
   
   echo "✅ Deployment complete!"
   echo "📋 View logs: ssh saturn.local 'sudo /usr/local/bin/docker logs -f listsync'"
   ```

**Success Criteria:**
- [ ] Docker image builds successfully
- [ ] Image transfers to Saturn
- [ ] Container recreates with new image
- [ ] Blocklist file is accessible
- [ ] Logs show blocklist loaded

---

### **PHASE 4: Monitoring & Validation** ✅ Production Monitoring
**Goal:** Add metrics and verification tools

**Components:**

1. **Blocklist Stats API Endpoint** (add to `api_server.py`):
   ```python
   @app.get("/api/blocklist/stats")
   async def get_blocklist_stats():
       """Get blocklist statistics"""
       try:
           manager = get_blocklist_manager()
           return {
               "enabled": manager.enabled,
               "loaded_at": manager.loaded_at.isoformat() if manager.loaded_at else None,
               "movie_count": len(manager.movie_blocklist),
               "tv_count": len(manager.tv_blocklist),
               "total_count": len(manager.movie_blocklist) + len(manager.tv_blocklist),
               "file_path": str(manager.blocklist_path),
               "file_exists": manager.blocklist_path.exists()
           }
       except Exception as e:
           raise HTTPException(status_code=500, detail=str(e))
   ```

2. **Sync Summary Enhancement**:
   ```python
   # In display.py - add to SyncResults
   class SyncResults:
       # ... existing fields ...
       blocked_count: int = 0  # NEW
       blocked_items: List[Dict] = field(default_factory=list)  # NEW
   ```

3. **Verification Script** (`scripts/verify_blocklist.py`):
   ```python
   #!/usr/bin/env python3
   """Verify blocklist integration"""
   import requests
   import json
   
   # Check if blocklist file exists
   # Check API endpoint
   # Sample some blocked movies
   # Verify they're not in request history
   ```

**Success Criteria:**
- [ ] API endpoint shows blocklist stats
- [ ] Sync summary includes blocked count
- [ ] Logs clearly show filtered items
- [ ] No blocked items in request history

---

### **PHASE 5: Testing & Validation** ✅ Quality Assurance
**Goal:** Comprehensive testing before production

**Test Scenarios:**

1. **Unit Tests**:
   - [ ] Blocklist loads valid JSON
   - [ ] Blocklist handles missing file gracefully
   - [ ] `is_blocked()` returns correct results
   - [ ] Empty blocklist doesn't filter anything

2. **Integration Tests**:
   - [ ] Sync runs with blocklist enabled
   - [ ] Blocked items are filtered
   - [ ] Non-blocked items are requested
   - [ ] Database records blocked status

3. **End-to-End Tests**:
   - [ ] Export blocklist from Seerr
   - [ ] Run list-sync with blocklist
   - [ ] Verify no blocked movies requested
   - [ ] Check Radarr for violations

4. **Regression Tests**:
   - [ ] Sync works with blocklist disabled
   - [ ] Sync works with missing blocklist file
   - [ ] Sync works with empty blocklist
   - [ ] Sync works with corrupted blocklist

**Test Data:**
```json
{
  "movies": [550, 551, 552],  // Known blocked TMDBs
  "tv": [1399, 1400]
}
```

**Success Criteria:**
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] E2E test shows 0 blocked requests
- [ ] Regression tests pass

---

## File Structure

```
/Users/fabian/projects/list-sync/
├── BLOCKLIST_FEATURE_PLAN.md (this file)
├── LISTSYNC_DEPLOYMENT_WORKFLOW.md (to create)
├── list_sync/
│   ├── blocklist.py (NEW)
│   ├── main.py (MODIFY - add blocklist integration)
│   ├── config.py (MODIFY - add blocklist config)
│   └── database.py (MODIFY - add blocked status)
├── api_server.py (MODIFY - add blocklist stats endpoint)
├── scripts/
│   ├── build-and-deploy.sh (NEW)
│   └── verify_blocklist.py (NEW)
└── tests/
    ├── test_blocklist.py (NEW)
    └── test_blocklist_integration.py (NEW)

Saturn: /volume1/docker-compose/stacks/kometa-listsync/
├── docker-compose.yml (MODIFY - use custom image)
├── seerr-export/ (NEW)
│   ├── Dockerfile
│   ├── export_seerr_blocklist.py
│   └── requirements.txt
└── blocklist.json (GENERATED by seerr-export)
```

---

## Configuration Options

Add to `.env` or Docker compose:

```bash
# Blocklist Feature
BLOCKLIST_ENABLED=true
BLOCKLIST_FILE=/data/blocklist.json
BLOCKLIST_RELOAD_HOURS=24

# Seerr Export (for exporter container)
SEERR_URL=http://jellyseerr:5055
SEERR_API_KEY=your-api-key-here
EXPORT_PATH=/data/blocklist.json
EXPORT_SCHEDULE="0 2 * * *"  # 2 AM daily
```

---

## Rollback Plan

If something goes wrong:

```bash
# Revert to official image
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && \
  sudo sed -i 's/list-sync-custom:production/ghcr.io\/woahai321\/list-sync:latest/' docker-compose.yml && \
  sudo /usr/local/bin/docker-compose up -d --force-recreate listsync"
```

---

## Timeline Estimate

| Phase | Estimated Time | Dependencies |
|-------|---------------|--------------|
| Phase 1: Seerr Export | 2-3 hours | Access to Seerr API |
| Phase 2: List-Sync Integration | 4-6 hours | Phase 1 complete |
| Phase 3: Docker Deployment | 1-2 hours | Phase 2 complete |
| Phase 4: Monitoring | 2-3 hours | Phase 3 complete |
| Phase 5: Testing | 3-4 hours | All phases |
| **Total** | **12-18 hours** | Phased approach |

---

## Success Metrics

1. **Functional Metrics**:
   - Zero blocked movies requested
   - 100% blocklist load success rate
   - < 1 second blocklist check overhead

2. **Operational Metrics**:
   - Daily blocklist export success
   - Sync completion without errors
   - Clean deployment process

3. **Business Metrics**:
   - Reduced download traffic
   - No re-requesting of excluded movies
   - Radarr queue stays clean

---

## Next Steps

1. **Review this plan** - Ensure architecture meets your needs
2. **Approve phases** - Confirm implementation approach
3. **Begin Phase 1** - Start with Seerr export service
4. **Iterate** - Test each phase independently
5. **Deploy** - Roll out to production with monitoring

---

## Questions to Answer Before Starting

1. ✅ Should we filter movies only, or also TV shows?
2. ✅ Should blocklist be cached in database or reloaded each sync?
3. ✅ What should happen if blocklist file is missing?
4. ✅ Should we add a "force request" override for specific items?
5. ✅ Do we need a web UI to view/manage the blocklist?

---

## References

- Seerr Deployment Workflow: `/Users/fabian/projects/seerr/DEPLOYMENT_WORKFLOW.md`
- List-Sync Source: `/Users/fabian/projects/list-sync/`
- Saturn Compose: `/volume1/docker-compose/stacks/kometa-listsync/`
- Seerr Blocklist Code: `/Users/fabian/projects/seerr/server/lib/blocklistSync.ts`

---

**Ready to proceed?** Review this plan and we can start with Phase 1! 🚀

