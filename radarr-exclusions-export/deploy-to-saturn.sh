#!/bin/bash
# Deploy Radarr Exclusions Export via Proper Git Workflow
# Run this after pushing changes to GitHub

set -e

echo "============================================"
echo "Deploying Radarr Exclusions Export (Git)"
echo "============================================"
echo ""

echo "This script uses PROPER GIT WORKFLOW:"
echo "  1. Clone repo on Saturn"
echo "  2. Checkout feature branch"
echo "  3. Build from Git repo"
echo "  4. Deploy from built image"
echo ""

REPO_DIR="/volume1/docker-compose/stacks/kometa-listsync/list-sync-repo"
DATA_DIR="/volume1/docker/listsync/data"

echo "Step 1: Checking if repo exists on Saturn..."
if ssh saturn.local "test -d $REPO_DIR"; then
    echo "  ✅ Repo exists, pulling latest..."
    ssh saturn.local "cd $REPO_DIR && git fetch origin && git checkout feature/blocklist-support && git pull origin feature/blocklist-support"
else
    echo "  📥 Cloning repo..."
    ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync && git clone git@github.com:fmaass/list-sync.git list-sync-repo && cd list-sync-repo && git checkout feature/blocklist-support"
fi
echo ""

echo "Step 2: Creating .env file (secrets not in Git)..."
ssh saturn.local "cd $REPO_DIR/radarr-exclusions-export && cat > .env << 'EOF'
RADARR_URL=http://radarr:7878
RADARR_API_KEY=b96abe1b76384476b9fbf381ed6941d6
OUTPUT_FILE=/data/blocklist.json
LOG_LEVEL=INFO
TZ=Europe/Zurich
EOF
chmod 600 .env"
echo "  ✅ Environment configured"
echo ""

echo "Step 3: Building Docker image from Git repo..."
ssh saturn.local "cd $REPO_DIR/radarr-exclusions-export && sudo /usr/local/bin/docker-compose build"
echo "  ✅ Image built"
echo ""

echo "Step 4: Running initial export..."
ssh saturn.local "cd $REPO_DIR/radarr-exclusions-export && sudo /usr/local/bin/docker-compose run --rm radarr-exclusions-export"
echo "  ✅ Export completed"
echo ""

echo "Step 5: Verifying output..."
ssh saturn.local "cat $DATA_DIR/blocklist.json | jq '{version, source, total_count, movies: (.movies | length)}'"
echo ""

echo "Step 6: Setting up cron job..."
CRON_CMD="30 2 * * * cd $REPO_DIR/radarr-exclusions-export && /usr/local/bin/docker-compose run --rm radarr-exclusions-export >> /var/log/radarr-exclusions-export.log 2>&1"
ssh saturn.local "sudo bash -c '(crontab -l 2>/dev/null | grep -v radarr-exclusions-export | grep -v seerr-blocklist-export; echo \"$CRON_CMD\") | crontab -'"
echo "  ✅ Cron job added (runs daily at 2:30 AM)"
echo ""

echo "============================================"
echo "✅ Deployment complete (via Git)!"
echo "============================================"
echo ""
echo "Blocklist location: $DATA_DIR/blocklist.json"
echo "Git repo location: $REPO_DIR"
echo "Service location: $REPO_DIR/radarr-exclusions-export"
echo "Cron schedule: Daily at 2:30 AM"
echo ""
echo "Future updates:"
echo "  1. Commit & push changes to GitHub"
echo "  2. Run: ./deploy-to-saturn.sh"
echo "  3. Script will git pull and rebuild"
echo ""

