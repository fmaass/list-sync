# 🚀 Manual Deployment Guide - Blocklist Feature

**What I've Done:**
- ✅ Pushed `feature/blocklist-support` branch to GitHub
- ✅ Created secrets directory on Saturn
- ✅ Stored API key: `/volume1/docker-compose/stacks/kometa-listsync/secrets/seerr_api_key`
- ✅ Created .env file on Saturn
- ✅ All code verified locally (47 tests passed)

**What Needs Sudo (You):**
- Docker operations (build, deploy, compose)
- Some file operations

---

## 🎯 Deployment Steps

### **Step 1: Copy Export Service Files to Saturn** (5 min)

Since SCP had issues, use this method:

```bash
cd /Users/fabian/projects/list-sync

# Copy files individually via SSH with cat
ssh saturn.local "cat > /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export/export_seerr_blocklist.py" < seerr-blocklist-export/export_seerr_blocklist.py

ssh saturn.local "cat > /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export/Dockerfile" < seerr-blocklist-export/Dockerfile

ssh saturn.local "cat > /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export/docker-compose.yml" < seerr-blocklist-export/docker-compose.yml

ssh saturn.local "cat > /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export/requirements.txt" < seerr-blocklist-export/requirements.txt

# Make executable
ssh saturn.local "chmod +x /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export/export_seerr_blocklist.py"
```

**Or use rsync:**
```bash
rsync -avz seerr-blocklist-export/ saturn.local:/volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export/
```

---

### **Step 2: Build Export Service** (2 min)

```bash
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export && sudo /usr/local/bin/docker-compose build"
```

Expected: Build successful

---

### **Step 3: Run Initial Export** (1 min)

```bash
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export && sudo /usr/local/bin/docker-compose run --rm seerr-blocklist-export"
```

Expected: Creates `/volume1/docker/listsync/data/blocklist.json`

Verify:
```bash
ssh saturn.local "cat /volume1/docker/listsync/data/blocklist.json | jq '{version, total_count, movies: (.movies | length), tv: (.tv | length)}'"
```

---

### **Step 4: Schedule Cron Job** (1 min)

```bash
ssh saturn.local "sudo crontab -e"

# Add this line:
30 2 * * * cd /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export && /usr/local/bin/docker-compose run --rm seerr-blocklist-export >> /var/log/seerr-blocklist-export.log 2>&1
```

Or add to crontab programmatically:
```bash
ssh saturn.local 'sudo bash -c '"'"'(crontab -l 2>/dev/null | grep -v seerr-blocklist-export; echo "30 2 * * * cd /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export && /usr/local/bin/docker-compose run --rm seerr-blocklist-export >> /var/log/seerr-blocklist-export.log 2>&1") | crontab -'"'"''
```

---

### **Step 5: Build Custom List-Sync Image** (15 min)

On your Mac:

```bash
cd /Users/fabian/projects/list-sync

# Clean Docker (IMPORTANT!)
docker system prune -a -f --volumes
docker builder prune -f

# Build image
docker build \
  --platform linux/amd64 \
  --build-arg COMMIT_TAG="$(git rev-parse --short HEAD)-$(date +%s)" \
  -t list-sync-custom:deploy \
  -f Dockerfile \
  .
```

---

### **Step 6: Transfer to Saturn** (10 min)

```bash
docker save list-sync-custom:deploy | gzip | \
  ssh saturn.local "cat > /volume1/docker/list-sync-deploy.tar.gz"

ssh saturn.local "sudo /usr/local/bin/docker load < /volume1/docker/list-sync-deploy.tar.gz && \
  rm /volume1/docker/list-sync-deploy.tar.gz && \
  sudo /usr/local/bin/docker tag list-sync-custom:deploy list-sync-custom:production"
```

---

### **Step 7: Update docker-compose.yml** (2 min)

```bash
ssh saturn.local

# Backup current compose
sudo cp /volume1/docker-compose/stacks/kometa-listsync/docker-compose.yml \
        /volume1/docker-compose/stacks/kometa-listsync/docker-compose.yml.backup

# Edit the file
sudo vi /volume1/docker-compose/stacks/kometa-listsync/docker-compose.yml
```

**Change line 6:**
```yaml
# FROM:
image: ghcr.io/woahai321/list-sync:latest

# TO:
image: list-sync-custom:production
```

**Change line 31:**
```yaml
# FROM:
- com.centurylinklabs.watchtower.enable=true

# TO:
- com.centurylinklabs.watchtower.enable=false
```

**Or use sed:**
```bash
ssh saturn.local "
cd /volume1/docker-compose/stacks/kometa-listsync && \
sudo sed -i.backup 's|ghcr.io/woahai321/list-sync:latest|list-sync-custom:production|' docker-compose.yml && \
sudo sed -i 's|com.centurylinklabs.watchtower.enable=true|com.centurylinklabs.watchtower.enable=false|' docker-compose.yml
"
```

---

### **Step 8: Deploy Container** (2 min)

```bash
ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && \
  sudo /usr/local/bin/docker-compose up -d --force-recreate listsync"
```

Wait 30 seconds for startup.

---

### **Step 9: Verify Deployment** (5 min)

```bash
# Check container is running
ssh saturn.local "sudo /usr/local/bin/docker ps | grep listsync"

# Check logs for blocklist loading
ssh saturn.local "sudo /usr/local/bin/docker logs listsync --tail 200 | grep -i blocklist"

# Expected to see:
# "✅ Loaded blocklist from data/blocklist.json"
# "   Movies: XXX, TV: XXX, Total: XXX"

# Check for errors
ssh saturn.local "sudo /usr/local/bin/docker logs listsync --tail 100 | grep -i error"

# Check API endpoint
ssh saturn.local "curl -s http://localhost:4222/api/blocklist/stats | jq"
```

---

### **Step 10: Monitor Next Sync** (ongoing)

```bash
# Watch for blocked items
ssh saturn.local "sudo /usr/local/bin/docker logs -f listsync | grep -E '(⛔|BLOCKED)'"

# Expected to see:
# "⛔ BLOCKED: 'Movie Title' (TMDB: 12345) - on blocklist, skipping"
```

---

## 🔧 Alternative: Use Automated Script

I already created the script, just run:

```bash
cd /Users/fabian/projects/list-sync
./scripts/build-and-deploy.sh
```

It will handle everything except the initial export service deployment.

---

## ✅ Verification Checklist

After deployment:

- [ ] Export service built
- [ ] Initial export ran successfully
- [ ] blocklist.json exists on Saturn
- [ ] Cron job scheduled
- [ ] Custom list-sync image built
- [ ] Image transferred to Saturn
- [ ] docker-compose.yml updated
- [ ] Container recreated
- [ ] Blocklist loaded in logs
- [ ] API stats endpoint works
- [ ] Next sync shows blocked items

---

## 🎯 What I Managed to Do

✅ **Completed:**
- Pushed branch to GitHub
- Created secrets directory
- Stored API key securely
- Created .env file on Saturn

❌ **Blocked by Permissions:**
- SCP file transfer (subsystem issue)
- Docker build (needs sudo)
- Docker deploy (needs sudo)

---

## 💡 Recommended Next Steps

1. **Use the automated script:**
   ```bash
   ./scripts/build-and-deploy.sh
   ```

2. **Or follow manual steps above**

3. **Then verify:**
   ```bash
   ./scripts/verify-blocklist.sh
   ```

---

**Everything is ready, just needs your sudo access!** 🚀

