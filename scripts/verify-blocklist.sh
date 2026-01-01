#!/bin/bash
# Verify Blocklist Integration
# Tests that blocklist is working correctly on Saturn

set -e

SATURN_HOST="saturn.local"
SATURN_DOCKER="/usr/local/bin/docker"
API_URL="http://localhost:4222"

echo "============================================"
echo "Blocklist Integration Verification"
echo "============================================"
echo ""

# Test 1: Check blocklist file exists
echo "Test 1: Checking blocklist file..."
if ssh "$SATURN_HOST" "test -f /volume1/docker/listsync/data/blocklist.json"; then
    echo "  ✅ Blocklist file exists"
    FILE_SIZE=$(ssh "$SATURN_HOST" "stat -f%z /volume1/docker/listsync/data/blocklist.json")
    echo "  File size: $FILE_SIZE bytes"
else
    echo "  ❌ Blocklist file not found"
    echo "  Run: cd /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export && sudo docker-compose run --rm seerr-blocklist-export"
    exit 1
fi
echo ""

# Test 2: Check file is valid JSON
echo "Test 2: Validating JSON format..."
if ssh "$SATURN_HOST" "cat /volume1/docker/listsync/data/blocklist.json | jq empty 2>/dev/null"; then
    echo "  ✅ Valid JSON format"
else
    echo "  ❌ Invalid JSON format"
    exit 1
fi
echo ""

# Test 3: Check blocklist content
echo "Test 3: Checking blocklist content..."
MOVIE_COUNT=$(ssh "$SATURN_HOST" "cat /volume1/docker/listsync/data/blocklist.json | jq '.movies | length'")
TV_COUNT=$(ssh "$SATURN_HOST" "cat /volume1/docker/listsync/data/blocklist.json | jq '.tv | length'")
TOTAL_COUNT=$(ssh "$SATURN_HOST" "cat /volume1/docker/listsync/data/blocklist.json | jq '.total_count'")

echo "  Movies: $MOVIE_COUNT"
echo "  TV Shows: $TV_COUNT"
echo "  Total: $TOTAL_COUNT"

if [ "$TOTAL_COUNT" -gt "0" ]; then
    echo "  ✅ Blocklist has items"
else
    echo "  ⚠️  Blocklist is empty (this is OK if no items are blocked)"
fi
echo ""

# Test 4: Check container logs for blocklist loading
echo "Test 4: Checking container logs..."
LOAD_LOG=$(ssh "$SATURN_HOST" "sudo $SATURN_DOCKER logs listsync --tail 500 | grep -i 'Loaded blocklist' | tail -1")

if [ -n "$LOAD_LOG" ]; then
    echo "  ✅ Blocklist loaded"
    echo "  Log: $LOAD_LOG"
else
    echo "  ❌ Blocklist not loaded"
    echo "  Check logs: ssh $SATURN_HOST 'sudo $SATURN_DOCKER logs listsync | grep blocklist'"
    exit 1
fi
echo ""

# Test 5: Check API endpoint
echo "Test 5: Testing API endpoint..."
API_RESPONSE=$(ssh "$SATURN_HOST" "curl -s $API_URL/api/blocklist/stats")

if [ -n "$API_RESPONSE" ]; then
    echo "  ✅ API endpoint responding"
    echo ""
    echo "  Blocklist Stats:"
    echo "$API_RESPONSE" | ssh "$SATURN_HOST" "jq '{enabled, loaded, movie_count, tv_count, total_count, age_hours}'"
else
    echo "  ❌ API endpoint not responding"
    exit 1
fi
echo ""

# Test 6: Check for blocked items in recent sync
echo "Test 6: Checking for blocked items in sync logs..."
BLOCKED_COUNT=$(ssh "$SATURN_HOST" "sudo $SATURN_DOCKER logs listsync --tail 1000 | grep -c '⛔ BLOCKED' || echo 0")

echo "  Blocked items in recent logs: $BLOCKED_COUNT"
if [ "$BLOCKED_COUNT" -gt "0" ]; then
    echo "  ✅ Blocklist is actively filtering items"
    echo ""
    echo "  Recent blocked items:"
    ssh "$SATURN_HOST" "sudo $SATURN_DOCKER logs listsync --tail 1000 | grep '⛔ BLOCKED' | tail -5"
else
    echo "  ⚠️  No blocked items found (this is OK if no blocked items were in lists)"
fi
echo ""

# Test 7: Verify no blocked items were requested
echo "Test 7: Verifying no blocked items were requested..."
# This would require checking Overseerr API, skipping for now
echo "  ℹ️  Manual verification needed:"
echo "  - Check Overseerr request history"
echo "  - Verify no movies from blocklist were requested"
echo ""

echo "============================================"
echo "✅ Verification Complete"
echo "============================================"
echo ""
echo "Summary:"
echo "  - Blocklist file: ✅"
echo "  - JSON format: ✅"
echo "  - Container loaded: ✅"
echo "  - API endpoint: ✅"
echo "  - Filtering active: $([ "$BLOCKED_COUNT" -gt "0" ] && echo "✅" || echo "⚠️")"
echo ""
echo "Next steps:"
echo "  1. Monitor next sync for blocked items"
echo "  2. Check sync summary shows blocked count"
echo "  3. Verify no blocked items in Overseerr"
echo ""

