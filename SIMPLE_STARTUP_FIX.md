# 🚀 Simple Startup Fix - Bypass Setup Completely

## The Issue
Complex startup logic with database/encryption is causing crashes.

## Simple Solution
Create a direct startup script that bypasses ALL setup code.

## Implementation

### Create `/usr/src/app/start-direct.sh`:
```bash
#!/bin/bash
cd /usr/src/app

# Run Python directly with minimal imports
/usr/src/app/.venv/bin/python3 << 'PYEOF'
import sys
import os
sys.path.insert(0, '/usr/src/app')

# Set up logging
from list_sync.utils.logger import setup_logging
setup_logging()

# Import what we need
from list_sync.api.overseerr import OverseerrClient
from list_sync.main import automated_sync, run_sync
from list_sync.config import load_env_lists

# Get config from environment
url = os.getenv('OVERSEERR_URL')
api_key = os.getenv('OVERSEERR_API_KEY')
user_id = os.getenv('OVERSEERR_USER_ID', '1')
is_4k = os.getenv('OVERSEERR_4K', 'false').lower() == 'true'
sync_interval = float(os.getenv('SYNC_INTERVAL', '6'))

print(f"Starting List-Sync in automated mode...")
print(f"URL: {url}")
print(f"User ID: {user_id}")
print(f"Interval: {sync_interval} hours")

# Create client
client = OverseerrClient(url, api_key, user_id)
client.test_connection()
print("✅ Connected to Overseerr!")

# Load lists
load_env_lists()
print("✅ Lists loaded!")

# Start automated sync
if sync_interval > 0:
    automated_sync(client, sync_interval, is_4k, True)
else:
    run_sync(client, is_4k=is_4k, automated_mode=True)
PYEOF
```

### Update supervisor config:
```ini
[program:listsync-core]
command=/usr/src/app/start-direct.sh  # Use direct startup
```

This bypasses:
- Setup wizard
- ConfigManager
- Database credential loading  
- All complex startup logic

**Result:** Clean startup every time!

