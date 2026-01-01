# Seerr Blocklist Export Service

Exports Seerr's blacklist to a JSON file for consumption by list-sync.

## Overview

This service connects to your Seerr instance (Jellyseerr/Overseerr) and exports all blacklisted items (movies and TV shows) to a JSON file. List-sync then loads this file to filter out blocked items before making requests.

## Deployment

### On Saturn (Production)

1. **Copy files to Saturn:**
   ```bash
   scp -r seerr-blocklist-export/ saturn.local:/volume1/docker-compose/stacks/kometa-listsync/
   ```

2. **Set API key:**
   ```bash
   ssh saturn.local "echo 'SEERR_API_KEY=your-api-key-here' >> /volume1/docker-compose/stacks/kometa-listsync/.env"
   ```

3. **Build and run:**
   ```bash
   ssh saturn.local "cd /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export && \
     sudo /usr/local/bin/docker-compose build && \
     sudo /usr/local/bin/docker-compose run --rm seerr-blocklist-export"
   ```

### Schedule as Cron Job

Add to Saturn's crontab to run daily at 2:30 AM:

```bash
ssh saturn.local "sudo crontab -e"

# Add this line:
30 2 * * * cd /volume1/docker-compose/stacks/kometa-listsync/seerr-blocklist-export && /usr/local/bin/docker-compose run --rm seerr-blocklist-export >> /var/log/seerr-blocklist-export.log 2>&1
```

## Configuration

Set via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SEERR_URL` | Seerr API base URL | `http://jellyseerr:5055` |
| `SEERR_API_KEY` | Seerr API key | *Required* |
| `OUTPUT_FILE` | Output JSON path | `/data/blocklist.json` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Output Format

```json
{
  "version": "1.0",
  "exported_at": "2026-01-01T02:30:00Z",
  "source": "seerr",
  "movies": [12345, 67890, ...],
  "tv": [11111, 22222, ...],
  "total_count": 1234
}
```

## Testing Locally

```bash
# Set environment variables
export SEERR_URL=http://localhost:5055
export SEERR_API_KEY=your-api-key-here
export OUTPUT_FILE=./test-blocklist.json

# Run directly
python export_seerr_blocklist.py

# Or via Docker
docker-compose run --rm seerr-blocklist-export

# Check output
cat test-blocklist.json | jq
```

## Troubleshooting

### API Key Not Working
```bash
# Verify API key is correct
curl -H "X-Api-Key: YOUR_KEY" http://localhost:5055/api/v1/status

# Check Seerr settings → General → API Key
```

### File Not Created
```bash
# Check directory exists and is writable
ls -la /volume1/docker/listsync/data/

# Check container logs
docker logs seerr-blocklist-export
```

### Empty Blacklist
```bash
# Verify blacklist in Seerr
curl -H "X-Api-Key: YOUR_KEY" http://localhost:5055/api/v1/blacklist?mediaType=movie | jq

# This is normal if no items are blacklisted yet
```

## Integration with List-Sync

Once the export runs successfully, list-sync will automatically:
1. Load `/data/blocklist.json` on startup
2. Filter out blocked items before requesting
3. Log blocked items as status="blocked"

See main project documentation for list-sync integration details.

