#!/bin/bash
# Build and Deploy List-Sync Custom Image to Saturn
# Based on proven Seerr deployment workflow

set -e

echo "============================================"
echo "List-Sync Custom Build - Deployment"
echo "============================================"
echo ""

# Configuration
PROJECT_DIR="/Users/fabian/projects/list-sync"
IMAGE_NAME="list-sync-custom"
DEPLOY_TAG="deploy"
PRODUCTION_TAG="production"
SATURN_HOST="saturn.local"
SATURN_DOCKER="/usr/local/bin/docker"
SATURN_COMPOSE="/usr/local/bin/docker-compose"
SATURN_STACK_DIR="/volume1/docker-compose/stacks/kometa-listsync"
SATURN_TRANSFER_PATH="/volume1/docker/list-sync-deploy.tar.gz"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Step 0: Check we're in the right directory
if [ ! -f "$PROJECT_DIR/pyproject.toml" ]; then
    log_error "Not in list-sync project directory"
    exit 1
fi

cd "$PROJECT_DIR"

# Step 1: Docker Cleanup (MANDATORY)
echo "Step 1: Cleaning Docker..."
log_warn "This will remove unused images and free space"
docker system prune -a -f --volumes
docker builder prune -f
log_info "Docker cleaned"
echo ""

# Step 2: Check Git Status
echo "Step 2: Checking Git status..."
if [ -n "$(git status --porcelain)" ]; then
    log_warn "You have uncommitted changes"
    git status --short
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Deployment cancelled"
        exit 1
    fi
fi
CURRENT_BRANCH=$(git branch --show-current)
COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_TAG="${COMMIT_HASH}-$(date +%s)"
log_info "Branch: $CURRENT_BRANCH"
log_info "Commit: $COMMIT_HASH"
log_info "Tag: $COMMIT_TAG"
echo ""

# Step 3: Build Docker Image
echo "Step 3: Building Docker image..."
log_info "Platform: linux/amd64 (for Saturn)"
log_info "This will take 10-15 minutes..."
echo ""

docker build \
  --platform linux/amd64 \
  --build-arg COMMIT_TAG="$COMMIT_TAG" \
  -t "${IMAGE_NAME}:${DEPLOY_TAG}" \
  -f Dockerfile \
  .

if [ $? -eq 0 ]; then
    log_info "Build completed successfully"
else
    log_error "Build failed"
    exit 1
fi
echo ""

# Step 4: Transfer to Saturn
echo "Step 4: Transferring image to Saturn..."
log_info "Compressing and transferring (this may take 5-10 minutes)..."

docker save "${IMAGE_NAME}:${DEPLOY_TAG}" | gzip | \
  ssh "$SATURN_HOST" "cat > $SATURN_TRANSFER_PATH"

if [ $? -eq 0 ]; then
    log_info "Transfer completed"
else
    log_error "Transfer failed"
    exit 1
fi
echo ""

# Step 5: Load on Saturn
echo "Step 5: Loading image on Saturn..."
ssh "$SATURN_HOST" "sudo $SATURN_DOCKER load < $SATURN_TRANSFER_PATH && \
  rm $SATURN_TRANSFER_PATH && \
  sudo $SATURN_DOCKER tag ${IMAGE_NAME}:${DEPLOY_TAG} ${IMAGE_NAME}:${PRODUCTION_TAG}"

if [ $? -eq 0 ]; then
    log_info "Image loaded and tagged"
else
    log_error "Failed to load image"
    exit 1
fi
echo ""

# Step 6: Update docker-compose.yml (if needed)
echo "Step 6: Checking docker-compose configuration..."
COMPOSE_IMAGE=$(ssh "$SATURN_HOST" "grep 'image:' $SATURN_STACK_DIR/docker-compose.yml | grep listsync | head -1")

if echo "$COMPOSE_IMAGE" | grep -q "list-sync-custom:production"; then
    log_info "Compose already configured for custom image"
else
    log_warn "Compose file needs update to use custom image"
    echo ""
    echo "Please update $SATURN_STACK_DIR/docker-compose.yml:"
    echo "  Change: image: ghcr.io/woahai321/list-sync:latest"
    echo "  To:     image: list-sync-custom:production"
    echo ""
    read -p "Have you updated the compose file? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Please update compose file and run again"
        exit 1
    fi
fi
echo ""

# Step 7: Deploy on Saturn
echo "Step 7: Deploying container..."
ssh "$SATURN_HOST" "cd $SATURN_STACK_DIR && \
  sudo $SATURN_COMPOSE up -d --force-recreate listsync"

if [ $? -eq 0 ]; then
    log_info "Container recreated"
else
    log_error "Deployment failed"
    exit 1
fi
echo ""

# Step 8: Wait for startup
echo "Step 8: Waiting for container startup..."
sleep 30
log_info "Startup wait complete"
echo ""

# Step 9: Verify Deployment
echo "Step 9: Verifying deployment..."

# Check container is running
CONTAINER_STATUS=$(ssh "$SATURN_HOST" "sudo $SATURN_DOCKER ps | grep listsync | wc -l")
if [ "$CONTAINER_STATUS" -gt "0" ]; then
    log_info "Container is running"
else
    log_error "Container is not running"
    exit 1
fi

# Check for errors in logs
ERROR_COUNT=$(ssh "$SATURN_HOST" "sudo $SATURN_DOCKER logs listsync --tail 100 | grep -i error | wc -l")
if [ "$ERROR_COUNT" -gt "5" ]; then
    log_warn "Found $ERROR_COUNT errors in logs (check manually)"
else
    log_info "No critical errors in logs"
fi

# Check blocklist loaded
BLOCKLIST_LOADED=$(ssh "$SATURN_HOST" "sudo $SATURN_DOCKER logs listsync --tail 200 | grep -i 'Loaded blocklist' | wc -l")
if [ "$BLOCKLIST_LOADED" -gt "0" ]; then
    log_info "Blocklist loaded successfully"
else
    log_warn "Blocklist not loaded (check if file exists)"
fi

echo ""
echo "============================================"
echo "✅ Deployment Complete!"
echo "============================================"
echo ""
echo "Deployment Details:"
echo "  Image: ${IMAGE_NAME}:${PRODUCTION_TAG}"
echo "  Commit: $COMMIT_TAG"
echo "  Branch: $CURRENT_BRANCH"
echo ""
echo "Verification Commands:"
echo "  View logs:      ssh $SATURN_HOST 'sudo $SATURN_DOCKER logs -f listsync'"
echo "  Check status:   ssh $SATURN_HOST 'sudo $SATURN_DOCKER ps | grep listsync'"
echo "  Blocklist stats: curl http://listsync:4222/api/blocklist/stats | jq"
echo ""
echo "Rollback Command (if needed):"
echo "  ./scripts/rollback.sh"
echo ""

