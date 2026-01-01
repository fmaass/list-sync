# Radarr Exclusions Export Service

Exports Radarr's import exclusions to a JSON file for consumption by list-sync.

## Overview

This service connects to your Radarr instance and exports all import exclusions (blocked movies) to a JSON file. List-sync then loads this file to filter out blocked items before making requests.

**Why Radarr instead of Seerr:**
- Radarr exclusions are the source of truth (~124 items)
- Seerr's blacklist is synced FROM Radarr (may be incomplete)
- Direct from Radarr ensures we get all exclusions

## Deployment

### On Saturn (Production)

**Proper Git Workflow:**

1. **Clone repo on Saturn:**
   ```bash
   ssh saturn.local
   cd /volume1/docker-compose/stacks/kometa-listsync
   git clone git@github.com:fmaass/list-sync.git list-sync-repo
   cd list-sync-repo
   git checkout feature/blocklist-support
   ```

2. **Setup export service:**
   ```bash
   cd radarr-exclusions-export
   cat > .env << 'EOF'
RADARR_URL=http://radarr:7878
RADARR_API_KEY=your-radarr-api-key-here
OUTPUT_FILE=/data/blocklist.json
LOG_LEVEL=INFO
TZ=Europe/Zurich
EOF
   ```

3. **Build and run:**
   ```bash
   sudo /usr/local/bin/docker-compose build
   sudo /usr/local/bin/docker-compose run --rm radarr-exclusions-export
   ```

### Schedule as Cron Job

Add to Saturn's crontab to run daily at 2:30 AM:

```bash
ssh saturn.local "sudo crontab -e"

# Add this line:
30 2 * * * cd /volume1/docker-compose/stacks/kometa-listsync/list-sync-repo/radarr-exclusions-export && /usr/local/bin/docker-compose run --rm radarr-exclusions-export >> /var/log/radarr-exclusions-export.log 2>&1
```

## Configuration

Set via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `RADARR_URL` | Radarr API base URL | `http://radarr:7878` |
| `RADARR_API_KEY` | Radarr API key | *Required* |
| `OUTPUT_FILE` | Output JSON path | `/data/blocklist.json` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Output Format

```json
{
  "version": "1.0",
  "exported_at": "2026-01-01T02:30:00Z",
  "source": "radarr",
  "movies": [12345, 67890, ...],
  "tv": [],
  "total_count": 124
}
```

## Testing Locally

```bash
# Set environment variables
export RADARR_URL=http://localhost:7878
export RADARR_API_KEY=your-api-key-here
export OUTPUT_FILE=./test-blocklist.json

# Run directly
python export_radarr_exclusions.py

# Or via Docker
docker-compose run --rm radarr-exclusions-export

# Check output
cat test-blocklist.json | jq
```

## Troubleshooting

### API Key Not Working
```bash
# Verify API key is correct
curl -H "X-Api-Key: YOUR_KEY" http://localhost:7878/api/v3/system/status

# Check Radarr settings → General → Security → API Key
```

### File Not Created
```bash
# Check directory exists and is writable
ls -la /volume1/docker/listsync/data/

# Check container logs
docker logs radarr-exclusions-export
```

### Empty Exclusions
```bash
# Verify exclusions in Radarr
curl -H "X-Api-Key: YOUR_KEY" http://localhost:7878/api/v3/exclusions | jq

# This is normal if no items are excluded yet
```

## Integration with List-Sync

Once the export runs successfully, list-sync will automatically:
1. Load `/data/blocklist.json` on startup
2. Filter out blocked items before requesting
3. Log blocked items as status="blocked"

See main project documentation for list-sync integration details.

