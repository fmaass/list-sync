#!/bin/bash
# Wrapper script to run the cleanup inside Docker container on saturn

set -e

REMOTE_HOST="saturn.local"
DOCKER_CMD="/usr/local/bin/docker"  # Full path on saturn

# Check if container is running on saturn
echo "Checking container on $REMOTE_HOST..."
if ! ssh "$REMOTE_HOST" "sudo $DOCKER_CMD ps | grep -q listsync"; then
    echo "❌ ListSync container is not running on $REMOTE_HOST!"
    echo "Please start the container first with: ssh $REMOTE_HOST 'cd ~/list-sync && sudo $DOCKER_CMD compose up -d'"
    exit 1
fi

# Run cleanup inside container on saturn
echo "📋 Running cleanup script on $REMOTE_HOST..."
ssh "$REMOTE_HOST" "sudo $DOCKER_CMD exec listsync-full python3 /usr/src/app/cleanup_manual_approval_lists.py $@"
