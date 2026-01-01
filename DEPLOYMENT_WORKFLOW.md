# Seerr Deployment Workflow - Production Guide

**Last Updated:** January 1, 2026  
**Status:** ✅ Mandatory for all deployments

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
- Removed volumes: ~2-5GB

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
cd /Users/fabian/projects/seerr

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
git checkout feature/my-feature
```

### Step 3: Build Docker Image (10 minutes)
```bash
# Build for Saturn (AMD64 platform)
docker build \
  --platform linux/amd64 \
  --build-arg COMMIT_TAG="$(git rev-parse --short HEAD)-$(date +%s)" \
  -t seerr-radarr-blocklist:deploy \
  -f Dockerfile \
  .

# Check build succeeded
echo "Build status: $?"
```

### Step 4: Transfer to Saturn (5 minutes)
```bash
# Compress and transfer
docker save seerr-radarr-blocklist:deploy | gzip | \
  ssh saturn.local "cat > /volume1/docker/seerr-deploy.tar.gz"

# Load on Saturn
ssh saturn.local "sudo /usr/local/bin/docker load < /volume1/docker/seerr-deploy.tar.gz && \
  rm /volume1/docker/seerr-deploy.tar.gz && \
  sudo /usr/local/bin/docker tag seerr-radarr-blocklist:deploy seerr-radarr-blocklist:test"
```

### Step 5: Deploy on Saturn (1 minute)
```bash
# Recreate container with new image
ssh saturn.local "cd /volume1/docker-compose/stacks/sonarr-radarr && \
  sudo /usr/local/bin/docker-compose up -d --force-recreate jellyseerr"

# Wait for startup
sleep 20
```

### Step 6: Verify Deployment (2 minutes)
```bash
# Check version
curl -s https://requests.discomarder.live/api/v1/status | jq '{version, commitTag}'

# Check logs for errors
ssh saturn.local "sudo /usr/local/bin/docker logs jellyseerr --tail 50 | grep -i error"

# Verify server ready
ssh saturn.local "sudo /usr/local/bin/docker logs jellyseerr --tail 20 | grep 'Server ready'"
```

---

## One-Line Deployment Command

```bash
cd /Users/fabian/projects/seerr && \
docker system prune -a -f --volumes && docker builder prune -f && \
docker build --platform linux/amd64 --build-arg COMMIT_TAG="$(git rev-parse --short HEAD)-$(date +%s)" -t seerr-radarr-blocklist:deploy -f Dockerfile . && \
docker save seerr-radarr-blocklist:deploy | gzip | ssh saturn.local "cat > /volume1/docker/seerr-deploy.tar.gz" && \
ssh saturn.local "sudo /usr/local/bin/docker load < /volume1/docker/seerr-deploy.tar.gz && rm /volume1/docker/seerr-deploy.tar.gz && sudo /usr/local/bin/docker tag seerr-radarr-blocklist:deploy seerr-radarr-blocklist:test" && \
ssh saturn.local "cd /volume1/docker-compose/stacks/sonarr-radarr && sudo /usr/local/bin/docker-compose up -d --force-recreate jellyseerr" && \
echo "✅ Deployed! Check: https://requests.discomarder.live/api/v1/status"
```

---

## Troubleshooting

### "No Space Left on Device"
```bash
# This is why we clean FIRST!
docker system prune -a -f --volumes
docker builder prune -f

# Check disk space
df -h /var/lib/docker
docker system df
```

### Build Fails with I/O Error
```bash
# Clean and retry
docker system prune -a -f --volumes
docker builder prune -f

# Rebuild
docker build --no-cache --platform linux/amd64 ...
```

### Container Won't Start
```bash
# Check logs
ssh saturn.local "sudo /usr/local/bin/docker logs jellyseerr --tail 100"

# Common issues:
# - Missing environment variables
# - Database migration errors
# - Port conflicts
```

### Settings Not Loading
```bash
# Restart to reload settings.json
ssh saturn.local "cd /volume1/docker-compose/stacks/sonarr-radarr && \
  sudo /usr/local/bin/docker-compose restart jellyseerr"
```

---

## Git Workflow (NO SSH File Copying!)

### ✅ APPROVED Process
```
1. Create feature branch
2. Make changes
3. Commit atomically
4. Build Docker image
5. Deploy via Docker image transfer
6. Verify functionality
```

### ❌ FORBIDDEN Process
```
# NEVER DO THIS (except emergencies):
cat file.ts | ssh saturn.local "cat > /volume1/docker/seerr-custom/file.ts"
```

**Why forbidden:**
- No Git tracking
- No rollback capability
- No audit trail
- Causes issues during cleanup

**Emergency exception:**
- Document the incident
- Commit immediately after
- Note in Git message: "emergency: deployed via SSH"

---

## Deployment Checklist

Before deployment:
- [ ] Docker cleaned (`docker system prune -a -f`)
- [ ] Feature branch checked out
- [ ] Code committed
- [ ] No uncommitted changes
- [ ] Build successful
- [ ] Image transferred to Saturn

After deployment:
- [ ] Container running
- [ ] Server ready (logs)
- [ ] API responding
- [ ] Version correct
- [ ] No errors in logs
- [ ] Features tested

---

## Scheduled Maintenance

### Weekly (Sunday)
```bash
# Clean Docker on Mac
cd /Users/fabian/projects/seerr
docker system prune -a -f --volumes
docker builder prune -f

# Clean Docker on Saturn (if needed)
ssh saturn.local "sudo /usr/local/bin/docker system prune -f"
```

### Monthly
```bash
# Verify settings
curl -s 'https://requests.discomarder.live/api/v1/settings/radarr' | \
  jq '.[0] | {enforceBlocklist: .blocklistEnforceEnabled, syncEnabled}'

# Should show:
# {
#   "enforceBlocklist": true,  ← Must be true!
#   "syncEnabled": true
# }
```

### After Issues
```bash
# Check violations
curl -s 'https://requests.discomarder.live/api/v1/settings/blocklist/violations' \
  -H 'X-Api-Key: YOUR_KEY' | jq 'length'

# Trigger manual cleanup if needed
curl -X POST 'https://requests.discomarder.live/api/v1/settings/jobs/blocklist-sync/run' \
  -H 'X-Api-Key: YOUR_KEY'
```

---

## Common Commands

```bash
# View logs
ssh saturn.local "sudo /usr/local/bin/docker logs jellyseerr -f"

# Check version
curl -s https://requests.discomarder.live/api/v1/status | jq '.commitTag'

# Restart container
ssh saturn.local "cd /volume1/docker-compose/stacks/sonarr-radarr && \
  sudo /usr/local/bin/docker-compose restart jellyseerr"

# Check disk space (Mac)
docker system df

# Check disk space (Saturn)
ssh saturn.local "df -h /volume2"

# List recent images
docker images seerr-radarr-blocklist --format "{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"

# Remove old images
docker image prune -a -f
```

---

## Emergency Rollback

```bash
# On Saturn: Find previous image
ssh saturn.local "sudo /usr/local/bin/docker images seerr-radarr-blocklist"

# Tag and use previous version
ssh saturn.local "sudo /usr/local/bin/docker tag IMAGE_ID seerr-radarr-blocklist:test && \
  cd /volume1/docker-compose/stacks/sonarr-radarr && \
  sudo /usr/local/bin/docker-compose up -d --force-recreate jellyseerr"
```

---

## Performance Tips

### Speed Up Builds
```bash
# Use Docker BuildKit
export DOCKER_BUILDKIT=1

# Parallel layer building
docker build --platform linux/amd64 ...
```

### Reduce Image Size
```bash
# Already done in Dockerfile:
# - Multi-stage build
# - .dockerignore file
# - Prune .next/cache
```

### Faster Transfer
```bash
# Already using gzip compression
# Could use: ssh -C for additional compression
```

---

## Critical Settings (Never Change)

**In Seerr:**
- `blocklistEnforceEnabled: true` ← MUST stay true
- `blocklistSyncInterval: 60` (or 30 for faster)
- `syncEnabled: true`

**In Docker Compose:**
- Watchtower disabled (custom build)
- Volume mounts correct
- Port 5055 exposed

---

**Remember: Clean Docker FIRST, then build!** 🧹

