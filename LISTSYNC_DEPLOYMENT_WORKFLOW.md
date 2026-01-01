# List-Sync Custom Build - Deployment Workflow

**Last Updated:** January 1, 2026  
**Status:** ✅ Ready to Use  
**Based On:** Seerr deployment workflow (proven and tested)

---

## Overview

This workflow allows you to:
1. Build list-sync with custom features (like blocklist support)
2. Deploy to Saturn using the same proven process as Seerr
3. Maintain version control and rollback capability
4. Test features locally before production deployment

---

## Pre-Deployment: Docker Cleanup (MANDATORY)

**Always run before building** to prevent "no space left on device" errors:

```bash
# Clean Docker system
docker system prune -a -f --volumes

# Clean builder cache
docker builder prune -f

# Verify space freed
docker system df
```

**Expected results:**
- Removed unused images: ~20-40GB
- Removed build cache: ~10-20GB
- Freed space for new build

**Why this matters:**
- Docker builds cache layers
- Failed builds leave orphaned data
- macOS Docker Desktop has limited space
- Build failures waste time

**Frequency:** Before EVERY build

---

## Standard Deployment Process

### Step 1: Clean Docker (5 minutes)
```bash
cd /Users/fabian/projects/list-sync

# Clean everything
docker system prune -a -f --volumes
docker builder prune -f

# Verify
docker system df
```

### Step 2: Ensure Clean Working Directory
```bash
# Check status
git status

# Stash if needed
git stash push -m "WIP: describe work"

# Switch to feature branch
git checkout feature/blocklist-support
```

### Step 3: Build Docker Image (10-15 minutes)
```bash
# Build for Saturn (AMD64 platform)
docker build \
  --platform linux/amd64 \
  --build-arg COMMIT_TAG="$(git rev-parse --short HEAD)-$(date +%s)" \
  -t list-sync-custom:deploy \
  -f Dockerfile \
  .

# Check build succeeded
echo "Build status: $?"
```

**Note:** List-sync build is multi-stage (Python + Node.js), so it takes longer than Seerr.

### Step 4: Transfer to Saturn (5-10 minutes)
```bash
# Compress and transfer
docker save list-sync-custom:deploy | gzip | \
  ssh saturn.local "cat > /volume1/docker/list-sync-deploy.tar.gz"

# Load on Saturn
ssh saturn.local "sudo /usr/local/bin/docker load < /volume1/docker/list-sync-deploy.tar.gz && \
  rm /volume1/docker/list-sync-deploy.tar.gz && \
  sudo /usr/local/bin/docker tag list-sync-custom:deploy list-sync-custom:production"
```

### Step 5: Update Docker Compose (Saturn)

**First time only:** Edit `/volume1/docker-compose/stacks/kometa-listsync/docker-compose.yml`

```yaml
services:
  listsync:
    image: list-sync-custom:production  # ← CHANGED from ghcr.io/woahai321/list-sync:latest
    container_name: listsync
    # ... rest of config unchanged ...
    volumes:
      - /volume1/docker/listsync/data:/data
      - /volume1/docker/listsync/blocklist.json:/data/blocklist.json:ro  # ← NEW (optional, for blocklist feature)
    labels:
      - com.centurylinklabs.watchtower.enable=false  # ← CHANGED (prevent auto-update)
```

### Step 6: Deploy on Saturn (1 minute)
```bash
# Recreate container with new image
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && \
  sudo /usr/local/bin/docker-compose up -d --force-recreate listsync"

# Wait for startup
sleep 30
```

### Step 7: Verify Deployment (2 minutes)
```bash
# Check container is running
ssh saturn.local "sudo /usr/local/bin/docker ps | grep listsync"

# Check logs for errors
ssh saturn.local "sudo /usr/local/bin/docker logs listsync --tail 100 | grep -i error"

# Verify API is responding
curl -s http://listsync.yourdomain.com/api/system/health | jq

# Check version
ssh saturn.local "sudo /usr/local/bin/docker exec listsync python -m list_sync --version"
```

---

## One-Line Deployment Command

```bash
cd /Users/fabian/projects/list-sync && \
docker system prune -a -f --volumes && docker builder prune -f && \
docker build --platform linux/amd64 --build-arg COMMIT_TAG="$(git rev-parse --short HEAD)-$(date +%s)" -t list-sync-custom:deploy -f Dockerfile . && \
docker save list-sync-custom:deploy | gzip | ssh saturn.local "cat > /volume1/docker/list-sync-deploy.tar.gz" && \
ssh saturn.local "sudo /usr/local/bin/docker load < /volume1/docker/list-sync-deploy.tar.gz && rm /volume1/docker/list-sync-deploy.tar.gz && sudo /usr/local/bin/docker tag list-sync-custom:deploy list-sync-custom:production" && \
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && sudo /usr/local/bin/docker-compose up -d --force-recreate listsync" && \
echo "✅ Deployed! Check logs: ssh saturn.local 'sudo /usr/local/bin/docker logs -f listsync'"
```

---

## Troubleshooting

### "No Space Left on Device"
```bash
# This is why we clean FIRST!
docker system prune -a -f --volumes
docker builder prune -f

# Check disk space
df -h ~/.docker
docker system df
```

### Build Fails with I/O Error
```bash
# Clean and retry
docker system prune -a -f --volumes
docker builder prune -f

# Rebuild with no cache
docker build --no-cache --platform linux/amd64 \
  -t list-sync-custom:deploy -f Dockerfile .
```

### Container Won't Start
```bash
# Check logs
ssh saturn.local "sudo /usr/local/bin/docker logs listsync --tail 200"

# Common issues:
# - Missing environment variables (check docker-compose.yml)
# - Database migration errors (check data volume permissions)
# - Port conflicts (check if 3222/4222 are in use)
# - Missing volumes (check /volume1/docker/listsync/data exists)
```

### Frontend Not Loading
```bash
# Check if frontend service is running
ssh saturn.local "sudo /usr/local/bin/docker exec listsync ps aux | grep node"

# Check frontend logs (supervisor manages it)
ssh saturn.local "sudo /usr/local/bin/docker exec listsync cat /var/log/supervisor/frontend.log | tail -50"

# Restart just the frontend service
ssh saturn.local "sudo /usr/local/bin/docker exec listsync supervisorctl restart listsync-frontend"
```

### API Not Responding
```bash
# Check if API service is running
ssh saturn.local "sudo /usr/local/bin/docker exec listsync ps aux | grep python"

# Check API logs
ssh saturn.local "sudo /usr/local/bin/docker exec listsync cat /var/log/supervisor/api.log | tail -50"

# Restart just the API service
ssh saturn.local "sudo /usr/local/bin/docker exec listsync supervisorctl restart listsync-api"
```

### Blocklist Not Loading (if blocklist feature enabled)
```bash
# Check if blocklist file exists
ssh saturn.local "ls -lh /volume1/docker/listsync/data/blocklist.json"

# Check if file is mounted in container
ssh saturn.local "sudo /usr/local/bin/docker exec listsync ls -lh /data/blocklist.json"

# Check blocklist stats via API
curl -s http://listsync.yourdomain.com/api/blocklist/stats | jq
```

---

## Git Workflow (NO SSH File Copying!)

### ✅ APPROVED Process
```
1. Create feature branch
2. Make changes locally
3. Test locally (optional: docker-compose.local.yml)
4. Commit atomically
5. Build Docker image
6. Deploy via Docker image transfer
7. Verify functionality
8. Merge to main after testing
```

### ❌ FORBIDDEN Process
```
# NEVER DO THIS (except emergencies):
cat file.py | ssh saturn.local "cat > /volume1/docker/listsync/file.py"
```

**Why forbidden:**
- No Git tracking
- No rollback capability
- No audit trail
- Causes issues during cleanup
- Hard to debug

**Emergency exception:**
- Document the incident
- Commit immediately after
- Note in Git message: "emergency: deployed via SSH"

---

## Deployment Checklist

**Before deployment:**
- [ ] Docker cleaned (`docker system prune -a -f`)
- [ ] Feature branch checked out
- [ ] Code committed (or stashed)
- [ ] No uncommitted changes to critical files
- [ ] Build successful
- [ ] Image transferred to Saturn

**After deployment:**
- [ ] Container running (`docker ps`)
- [ ] All services started (check supervisor)
- [ ] Frontend accessible (port 3222)
- [ ] API responding (port 4222)
- [ ] No errors in logs
- [ ] Features tested
- [ ] Database migrations completed

---

## Scheduled Maintenance

### Weekly (Sunday)
```bash
# Clean Docker on Mac
cd /Users/fabian/projects/list-sync
docker system prune -a -f --volumes
docker builder prune -f

# Clean Docker on Saturn (if needed)
ssh saturn.local "sudo /usr/local/bin/docker system prune -f"
```

### Monthly
```bash
# Verify list-sync stats
curl -s http://listsync.yourdomain.com/api/system/status | jq

# Check disk space
ssh saturn.local "df -h /volume1/docker/listsync"

# Review logs
ssh saturn.local "sudo /usr/local/bin/docker logs listsync --tail 500 | grep ERROR"
```

### After Issues
```bash
# Check sync history
curl -s http://listsync.yourdomain.com/api/sync/history | jq '.[0]'

# Trigger manual sync
curl -X POST http://listsync.yourdomain.com/api/sync/trigger \
  -H 'Authorization: Bearer YOUR_TOKEN'

# Check blocklist stats (if enabled)
curl -s http://listsync.yourdomain.com/api/blocklist/stats | jq
```

---

## Common Commands

```bash
# View logs (all services)
ssh saturn.local "sudo /usr/local/bin/docker logs listsync -f"

# View specific service logs
ssh saturn.local "sudo /usr/local/bin/docker exec listsync tail -f /var/log/supervisor/listsync-core.log"
ssh saturn.local "sudo /usr/local/bin/docker exec listsync tail -f /var/log/supervisor/api.log"
ssh saturn.local "sudo /usr/local/bin/docker exec listsync tail -f /var/log/supervisor/frontend.log"

# Check service status
ssh saturn.local "sudo /usr/local/bin/docker exec listsync supervisorctl status"

# Restart a service
ssh saturn.local "sudo /usr/local/bin/docker exec listsync supervisorctl restart listsync-core"

# Restart entire container
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && \
  sudo /usr/local/bin/docker-compose restart listsync"

# Check disk space (Mac)
docker system df

# Check disk space (Saturn)
ssh saturn.local "df -h /volume1"

# List recent images
docker images list-sync-custom --format "{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"

# Remove old images
docker image prune -a -f
```

---

## Emergency Rollback

### Option 1: Revert to Official Image (Fastest)
```bash
# On Saturn: Edit docker-compose.yml
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && \
  sudo sed -i.bak 's/list-sync-custom:production/ghcr.io\/woahai321\/list-sync:latest/' docker-compose.yml && \
  sudo /usr/local/bin/docker-compose pull listsync && \
  sudo /usr/local/bin/docker-compose up -d --force-recreate listsync"
```

### Option 2: Use Previous Custom Build
```bash
# On Saturn: Find previous image
ssh saturn.local "sudo /usr/local/bin/docker images list-sync-custom"

# Tag and use previous version
ssh saturn.local "sudo /usr/local/bin/docker tag <IMAGE_ID> list-sync-custom:production && \
  cd /volume1/docker-compose/stacks/kometa-listsync && \
  sudo /usr/local/bin/docker-compose up -d --force-recreate listsync"
```

---

## Performance Tips

### Speed Up Builds
```bash
# Use Docker BuildKit (enabled by default in newer Docker)
export DOCKER_BUILDKIT=1

# Use build cache (don't use --no-cache unless necessary)
docker build --platform linux/amd64 -t list-sync-custom:deploy .
```

### Reduce Image Size
Already optimized in Dockerfile:
- Multi-stage build (Python builder + Node builder + runtime)
- .dockerignore file
- Production dependencies only
- Prune node_modules/.cache

### Faster Transfer
```bash
# Already using gzip compression
# Could use: ssh -C for additional compression
docker save list-sync-custom:deploy | gzip --fast | ssh -C saturn.local "cat > ..."
```

---

## Critical Settings (Never Change)

**In Docker Compose:**
```yaml
labels:
  - com.centurylinklabs.watchtower.enable=false  # ← MUST stay false for custom builds
```

**Volumes:**
```yaml
volumes:
  - /volume1/docker/listsync/data:/data  # ← Data persistence
```

**Ports:**
```yaml
ports:
  - "3222:3222"  # Frontend
  - "4222:4222"  # API
```

---

## Comparison with Seerr Workflow

| Aspect | Seerr | List-Sync |
|--------|-------|-----------|
| Build Time | ~5 min | ~10-15 min (multi-stage) |
| Image Size | ~800MB | ~1.2GB (includes Node.js) |
| Services | 1 (Node.js) | 4 (Python + API + Frontend + Xvfb) |
| Ports | 5055 | 3222, 4222 |
| Database | SQLite | SQLite |
| Supervisor | No | Yes (manages 4 services) |

---

## References

- List-Sync Source: `/Users/fabian/projects/list-sync/`
- Saturn Compose: `/volume1/docker-compose/stacks/kometa-listsync/`
- Seerr Workflow: `/Users/fabian/projects/seerr/DEPLOYMENT_WORKFLOW.md`
- Blocklist Plan: `/Users/fabian/projects/list-sync/BLOCKLIST_FEATURE_PLAN.md`

---

**Remember: Clean Docker FIRST, then build!** 🧹

**Questions?** Check the Troubleshooting section above or review logs.

---

**Status:** ✅ Ready for use with blocklist feature

