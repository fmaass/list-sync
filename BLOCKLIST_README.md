# Blocklist Feature - Quick Start Guide

**Status:** ✅ Ready for Testing  
**Branch:** `feature/blocklist-support`  
**Last Updated:** January 1, 2026

---

## 🎯 What This Feature Does

Prevents list-sync from requesting movies/TV shows that are on Seerr's blocklist, eliminating:
- ❌ Repeated requests for blocked movies
- ❌ Wasted download traffic
- ❌ Radarr queue pollution

---

## 📋 Quick Start

### 1. Export Seerr Blocklist (One-Time Setup)

```bash
# Set your Seerr API key
export SEERR_API_KEY=your-api-key-here

# Deploy export service to Saturn
cd seerr-blocklist-export
./deploy-to-saturn.sh
```

This sets up a daily cron job (2:30 AM) to export Seerr's blocklist to `/volume1/docker/listsync/data/blocklist.json`.

### 2. Build & Deploy Custom List-Sync

```bash
# From project root
./scripts/build-and-deploy.sh
```

This will:
1. Clean Docker
2. Build custom image
3. Transfer to Saturn
4. Deploy container
5. Verify deployment

**Time:** ~20-30 minutes

### 3. Verify It's Working

```bash
./scripts/verify-blocklist.sh
```

This checks:
- ✅ Blocklist file exists
- ✅ Valid JSON format
- ✅ Container loaded blocklist
- ✅ API endpoint responding
- ✅ Items being filtered

---

## 🔧 Manual Testing

### Test Locally (Before Deploying)

```bash
# 1. Export blocklist from Seerr
cd seerr-blocklist-export
export SEERR_API_KEY=your-key
export SEERR_URL=https://requests.discomarder.live
./test-local.sh

# 2. Check output
cat test-blocklist.json | jq
```

### Test on Saturn (After Deploying)

```bash
# 1. Check blocklist file
ssh saturn.local "cat /volume1/docker/listsync/data/blocklist.json | jq '{version, total_count, movies: (.movies | length), tv: (.tv | length)}'"

# 2. Check API
ssh saturn.local "curl -s http://localhost:4222/api/blocklist/stats | jq"

# 3. Check logs
ssh saturn.local "sudo /usr/local/bin/docker logs listsync | grep -i blocklist"

# 4. Watch for blocked items
ssh saturn.local "sudo /usr/local/bin/docker logs -f listsync | grep '⛔ BLOCKED'"
```

---

## 📊 Monitoring

### View Blocklist Stats

```bash
# Via API
curl http://listsync:4222/api/blocklist/stats | jq

# Expected output:
{
  "enabled": true,
  "loaded": true,
  "movie_count": 234,
  "tv_count": 45,
  "total_count": 279,
  "age_hours": 2.5
}
```

### Check Sync Results

After a sync completes, the summary will show:
```
Results
─────────────
✅ Requested: 150
☑️ Available: 50
📌 Already Requested: 30
⏭️ Skipped: 20
⛔ Blocked: 25        ← NEW!
```

### View Blocked Items in Logs

```bash
ssh saturn.local "sudo /usr/local/bin/docker logs listsync | grep '⛔ BLOCKED'"
```

---

## 🔄 Maintenance

### Update Blocklist Manually

```bash
# Trigger export
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export && sudo /usr/local/bin/docker-compose run --rm seerr-blocklist-export"

# Reload in list-sync
curl -X POST http://listsync:4222/api/blocklist/reload
```

### View Cron Logs

```bash
ssh saturn.local "tail -f /var/log/seerr-blocklist-export.log"
```

### Disable Blocklist Temporarily

```bash
# Set environment variable in docker-compose.yml
BLOCKLIST_ENABLED=false

# Restart container
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && sudo /usr/local/bin/docker-compose restart listsync"
```

---

## 🚨 Troubleshooting

### Blocklist Not Loading

**Symptom:** Logs show "Blocklist file not found"

**Fix:**
```bash
# 1. Check file exists
ssh saturn.local "ls -lh /volume1/docker/listsync/data/blocklist.json"

# 2. If missing, run export
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export && sudo /usr/local/bin/docker-compose run --rm seerr-blocklist-export"

# 3. Restart list-sync
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && sudo /usr/local/bin/docker-compose restart listsync"
```

### Empty Blocklist

**Symptom:** `total_count: 0`

**This is normal if:**
- No items are blocked in Seerr
- Radarr exclusion list is empty
- Blocklist sync hasn't run yet in Seerr

**To verify:**
```bash
# Check Seerr directly
curl -H "X-Api-Key: YOUR_KEY" https://requests.discomarder.live/api/v1/blacklist?mediaType=movie | jq 'length'
```

### Items Still Being Requested

**Symptom:** Blocked movies still appear in Overseerr

**Debug steps:**
```bash
# 1. Check if item is in blocklist
ssh saturn.local "cat /volume1/docker/listsync/data/blocklist.json | jq '.movies[] | select(. == 12345)'"

# 2. Check if blocklist is loaded
curl http://listsync:4222/api/blocklist/stats | jq '.loaded'

# 3. Check logs for that specific movie
ssh saturn.local "sudo /usr/local/bin/docker logs listsync | grep 'TMDB: 12345'"
```

---

## 🔙 Rollback

If something goes wrong:

```bash
# Quick rollback to official image
./scripts/rollback.sh
```

This reverts to `ghcr.io/woahai321/list-sync:latest` (without blocklist feature).

---

## 📁 File Locations

### On Your Mac
- Source code: `/Users/fabian/projects/list-sync/`
- Branch: `feature/blocklist-support`
- Scripts: `./scripts/`
- Export service: `./seerr-blocklist-export/`

### On Saturn
- Blocklist file: `/volume1/docker/listsync/data/blocklist.json`
- Export service: `/volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export/`
- List-sync stack: `/volume1/docker-compose/stacks/kometa-listsync/`
- Cron log: `/var/log/seerr-blocklist-export.log`

---

## 🎓 How It Works

```
┌─────────────────────────────────────────────────────────┐
│  NIGHTLY WORKFLOW                                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [02:00] Seerr syncs Radarr exclusions                  │
│          └─> Updates Seerr blacklist                    │
│                                                          │
│  [02:30] Export service runs (cron)                     │
│          └─> Exports to blocklist.json                  │
│                                                          │
│  [03:10] List-sync runs                                 │
│          ├─> Loads blocklist.json                       │
│          ├─> Fetches items from lists                   │
│          ├─> Filters blocked items (⛔)                 │
│          └─> Requests remaining items                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📚 Documentation

- **Feature Plan:** `BLOCKLIST_FEATURE_PLAN.md` (detailed spec)
- **Summary:** `BLOCKLIST_SUMMARY.md` (executive overview)
- **Deployment:** `LISTSYNC_DEPLOYMENT_WORKFLOW.md` (deployment guide)
- **This File:** Quick reference for daily use

---

## ✅ Testing Checklist

Before deploying to production:

- [ ] Export service runs successfully
- [ ] Blocklist JSON file is valid
- [ ] Custom image builds without errors
- [ ] Container starts successfully
- [ ] Blocklist loads on startup
- [ ] API endpoints respond
- [ ] Blocked items are filtered
- [ ] Sync summary shows blocked count
- [ ] No blocked items in Overseerr

---

## 🚀 Next Steps

1. **Test locally:** Run `./seerr-blocklist-export/test-local.sh`
2. **Deploy export:** Run `./seerr-blocklist-export/deploy-to-saturn.sh`
3. **Build & deploy:** Run `./scripts/build-and-deploy.sh`
4. **Verify:** Run `./scripts/verify-blocklist.sh`
5. **Monitor:** Watch next sync for blocked items
6. **Merge:** Once confident, merge to main branch

---

**Questions?** Check the detailed docs or review the code in `list_sync/blocklist.py`

