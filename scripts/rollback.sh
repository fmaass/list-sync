#!/bin/bash
# Rollback to official list-sync image

set -e

SATURN_HOST="saturn.local"
SATURN_COMPOSE="/usr/local/bin/docker-compose"
SATURN_STACK_DIR="/volume1/docker-compose/stacks/kometa-listsync"

echo "============================================"
echo "List-Sync Rollback to Official Image"
echo "============================================"
echo ""

echo "⚠️  WARNING: This will revert to the official list-sync image"
echo "   Custom blocklist features will be disabled"
echo ""
read -p "Continue with rollback? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 0
fi

echo "Step 1: Backing up current compose file..."
ssh "$SATURN_HOST" "sudo cp $SATURN_STACK_DIR/docker-compose.yml $SATURN_STACK_DIR/docker-compose.yml.backup"
echo "✓ Backup created"
echo ""

echo "Step 2: Updating compose file..."
ssh "$SATURN_HOST" "sudo sed -i 's/list-sync-custom:production/ghcr.io\/woahai321\/list-sync:latest/' $SATURN_STACK_DIR/docker-compose.yml"
echo "✓ Compose file updated"
echo ""

echo "Step 3: Pulling official image..."
ssh "$SATURN_HOST" "cd $SATURN_STACK_DIR && sudo $SATURN_COMPOSE pull listsync"
echo "✓ Image pulled"
echo ""

echo "Step 4: Recreating container..."
ssh "$SATURN_HOST" "cd $SATURN_STACK_DIR && sudo $SATURN_COMPOSE up -d --force-recreate listsync"
echo "✓ Container recreated"
echo ""

echo "Step 5: Verifying..."
sleep 10
ssh "$SATURN_HOST" "sudo /usr/local/bin/docker ps | grep listsync"
echo ""

echo "============================================"
echo "✅ Rollback Complete"
echo "============================================"
echo ""
echo "Restore custom build:"
echo "  ./scripts/build-and-deploy.sh"
echo ""

