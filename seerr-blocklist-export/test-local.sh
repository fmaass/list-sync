#!/bin/bash
# Local testing script for Seerr blocklist export
# Tests the export service before deploying to Saturn

set -e

echo "============================================"
echo "Seerr Blocklist Export - Local Test"
echo "============================================"
echo ""

# Check if SEERR_API_KEY is set
if [ -z "$SEERR_API_KEY" ]; then
    echo "❌ ERROR: SEERR_API_KEY environment variable not set"
    echo ""
    echo "Please set it:"
    echo "  export SEERR_API_KEY=your-api-key-here"
    echo ""
    echo "Get your API key from Seerr:"
    echo "  Settings → General → API Key"
    exit 1
fi

# Configuration
SEERR_URL="${SEERR_URL:-https://requests.discomarder.live}"
OUTPUT_FILE="./test-blocklist.json"

echo "Configuration:"
echo "  SEERR_URL: $SEERR_URL"
echo "  OUTPUT_FILE: $OUTPUT_FILE"
echo "  API_KEY: ${SEERR_API_KEY:0:10}..." # Show only first 10 chars
echo ""

# Test 1: Verify Seerr is accessible
echo "Test 1: Verifying Seerr connection..."
if curl -s -f -H "X-Api-Key: $SEERR_API_KEY" "$SEERR_URL/api/v1/status" > /dev/null 2>&1; then
    echo "  ✅ Seerr is accessible"
else
    echo "  ❌ Cannot connect to Seerr"
    echo "  Check URL and API key"
    exit 1
fi
echo ""

# Test 2: Fetch movie blacklist
echo "Test 2: Fetching movie blacklist..."
MOVIE_COUNT=$(curl -s -H "X-Api-Key: $SEERR_API_KEY" "$SEERR_URL/api/v1/blacklist?mediaType=movie" | jq '. | length' 2>/dev/null || echo "0")
echo "  Found $MOVIE_COUNT movies in blacklist"
echo ""

# Test 3: Fetch TV blacklist
echo "Test 3: Fetching TV blacklist..."
TV_COUNT=$(curl -s -H "X-Api-Key: $SEERR_API_KEY" "$SEERR_URL/api/v1/blacklist?mediaType=tv" | jq '. | length' 2>/dev/null || echo "0")
echo "  Found $TV_COUNT TV shows in blacklist"
echo ""

# Test 4: Run Python export script
echo "Test 4: Running export script..."
if [ ! -f "export_seerr_blocklist.py" ]; then
    echo "  ❌ export_seerr_blocklist.py not found"
    echo "  Run this script from seerr-blocklist-export directory"
    exit 1
fi

# Install dependencies if needed
if ! python3 -c "import requests" 2>/dev/null; then
    echo "  Installing dependencies..."
    pip3 install -r requirements.txt --quiet
fi

# Run export
export SEERR_URL="$SEERR_URL"
export OUTPUT_FILE="$OUTPUT_FILE"
export LOG_LEVEL="INFO"

if python3 export_seerr_blocklist.py; then
    echo "  ✅ Export completed successfully"
else
    echo "  ❌ Export failed"
    exit 1
fi
echo ""

# Test 5: Verify output file
echo "Test 5: Verifying output file..."
if [ -f "$OUTPUT_FILE" ]; then
    echo "  ✅ File created: $OUTPUT_FILE"
    
    # Check if it's valid JSON
    if jq empty "$OUTPUT_FILE" 2>/dev/null; then
        echo "  ✅ Valid JSON format"
    else
        echo "  ❌ Invalid JSON format"
        exit 1
    fi
    
    # Display summary
    echo ""
    echo "Output summary:"
    jq '{version, exported_at, total_count, movies: (.movies | length), tv: (.tv | length)}' "$OUTPUT_FILE"
    
    # Show first few IDs
    echo ""
    echo "Sample movie IDs:"
    jq '.movies[:5]' "$OUTPUT_FILE"
    
    echo ""
    echo "Sample TV IDs:"
    jq '.tv[:5]' "$OUTPUT_FILE"
else
    echo "  ❌ Output file not created"
    exit 1
fi

echo ""
echo "============================================"
echo "✅ All tests passed!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Review test-blocklist.json"
echo "  2. Deploy to Saturn: ./deploy-to-saturn.sh"
echo "  3. Test on Saturn: ssh saturn.local 'cat /volume1/docker/listsync/data/blocklist.json'"
echo ""

