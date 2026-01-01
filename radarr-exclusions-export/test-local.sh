#!/bin/bash
# Local testing script for Radarr exclusions export
# Tests the export service before deploying to Saturn

set -e

echo "============================================"
echo "Radarr Exclusions Export - Local Test"
echo "============================================"
echo ""

# Check if RADARR_API_KEY is set
if [ -z "$RADARR_API_KEY" ]; then
    echo "❌ ERROR: RADARR_API_KEY environment variable not set"
    echo ""
    echo "Please set it:"
    echo "  export RADARR_API_KEY=your-api-key-here"
    echo ""
    echo "Get your API key from Radarr:"
    echo "  Settings → General → Security → API Key"
    exit 1
fi

# Configuration
RADARR_URL="${RADARR_URL:-https://radarr.discomarder.live}"
OUTPUT_FILE="./test-blocklist.json"

echo "Configuration:"
echo "  RADARR_URL: $RADARR_URL"
echo "  OUTPUT_FILE: $OUTPUT_FILE"
echo "  API_KEY: ${RADARR_API_KEY:0:10}..." # Show only first 10 chars
echo ""

# Test 1: Verify Radarr is accessible
echo "Test 1: Verifying Radarr connection..."
if curl -s -f -H "X-Api-Key: $RADARR_API_KEY" "$RADARR_URL/api/v3/system/status" > /dev/null 2>&1; then
    echo "  ✅ Radarr is accessible"
else
    echo "  ❌ Cannot connect to Radarr"
    echo "  Check URL and API key"
    exit 1
fi
echo ""

# Test 2: Fetch exclusions
echo "Test 2: Fetching exclusions from Radarr..."
EXCLUSION_COUNT=$(curl -s -H "X-Api-Key: $RADARR_API_KEY" "$RADARR_URL/api/v3/exclusions" | jq '. | length' 2>/dev/null || echo "0")
echo "  Found $EXCLUSION_COUNT exclusions in Radarr"
echo ""

# Test 3: Run Python export script
echo "Test 3: Running export script..."
if [ ! -f "export_radarr_exclusions.py" ]; then
    echo "  ❌ export_radarr_exclusions.py not found"
    echo "  Run this script from radarr-exclusions-export directory"
    exit 1
fi

# Install dependencies if needed
if ! python3 -c "import requests" 2>/dev/null; then
    echo "  Installing dependencies..."
    pip3 install -r requirements.txt --quiet
fi

# Run export
export RADARR_URL="$RADARR_URL"
export OUTPUT_FILE="$OUTPUT_FILE"
export LOG_LEVEL="INFO"

if python3 export_radarr_exclusions.py; then
    echo "  ✅ Export completed successfully"
else
    echo "  ❌ Export failed"
    exit 1
fi
echo ""

# Test 4: Verify output file
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
echo "  2. Push to GitHub: git push"
echo "  3. Clone on Saturn and build from Git repo"
echo "  4. Verify: ssh saturn.local 'cat /volume1/docker/listsync/data/blocklist.json'"
echo ""

