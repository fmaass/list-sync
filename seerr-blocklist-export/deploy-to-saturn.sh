#!/bin/bash
# Deploy Seerr blocklist export service to Saturn
# Run this after testing locally with test-local.sh

set -e

echo "============================================"
echo "Deploying Seerr Blocklist Export to Saturn"
echo "============================================"
echo ""

# Check if SEERR_API_KEY is set
if [ -z "$SEERR_API_KEY" ]; then
    echo "❌ ERROR: SEERR_API_KEY environment variable not set"
    echo ""
    echo "Please set it:"
    echo "  export SEERR_API_KEY=your-api-key-here"
    exit 1
fi

TARGET_DIR="/volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export"
DATA_DIR="/volume1/docker/listsync/data"

echo "Step 1: Creating directories on Saturn..."
ssh saturn.local "sudo mkdir -p $TARGET_DIR $DATA_DIR && sudo chmod 755 $DATA_DIR"
echo "  ✅ Directories created"
echo ""

echo "Step 2: Copying files to Saturn..."
scp -r ./* saturn.local:$TARGET_DIR/
echo "  ✅ Files copied"
echo ""

echo "Step 3: Setting up environment variables..."
ssh saturn.local "sudo bash -c 'cat > $TARGET_DIR/.env << EOF
SEERR_URL=http://jellyseerr:5055
SEERR_API_KEY=$SEERR_API_KEY
OUTPUT_FILE=/data/blocklist.json
LOG_LEVEL=INFO
TZ=Europe/Zurich
EOF'"
echo "  ✅ Environment variables set"
echo ""

echo "Step 4: Building Docker image on Saturn..."
ssh saturn.local "cd $TARGET_DIR && sudo /usr/local/bin/docker-compose build"
echo "  ✅ Image built"
echo ""

echo "Step 5: Running initial export..."
ssh saturn.local "cd $TARGET_DIR && sudo /usr/local/bin/docker-compose run --rm seerr-blocklist-export"
echo "  ✅ Export completed"
echo ""

echo "Step 6: Verifying output..."
ssh saturn.local "test -f $DATA_DIR/blocklist.json && echo 'File exists' || echo 'File missing'"
ssh saturn.local "cat $DATA_DIR/blocklist.json | jq '{version, total_count, movies: (.movies | length), tv: (.tv | length)}'"
echo ""

echo "Step 7: Setting up cron job..."
CRON_CMD="30 2 * * * cd $TARGET_DIR && /usr/local/bin/docker-compose run --rm seerr-blocklist-export >> /var/log/seerr-blocklist-export.log 2>&1"
echo "  Adding cron job: $CRON_CMD"
ssh saturn.local "sudo bash -c '(crontab -l 2>/dev/null | grep -v seerr-blocklist-export; echo \"$CRON_CMD\") | crontab -'"
echo "  ✅ Cron job added (runs daily at 2:30 AM)"
echo ""

echo "============================================"
echo "✅ Deployment complete!"
echo "============================================"
echo ""
echo "Blocklist location: $DATA_DIR/blocklist.json"
echo "Service location: $TARGET_DIR"
echo "Cron schedule: Daily at 2:30 AM"
echo ""
echo "Manual run command:"
echo "  ssh saturn.local 'cd $TARGET_DIR && sudo /usr/local/bin/docker-compose run --rm seerr-blocklist-export'"
echo ""
echo "View blocklist:"
echo "  ssh saturn.local 'cat $DATA_DIR/blocklist.json | jq'"
echo ""
echo "View cron logs:"
echo "  ssh saturn.local 'tail -f /var/log/seerr-blocklist-export.log'"
echo ""

