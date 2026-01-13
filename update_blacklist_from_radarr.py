#!/usr/bin/env python3
"""Fetch fresh exclusions from Radarr and update blacklist"""
import requests
import json
import os
from datetime import datetime

RADARR_URL = 'http://radarr:7878'
RADARR_API_KEY = 'b96abe1b76384476b9fbf381ed6941d6'
BLACKLIST_FILE = '/data/blacklist.json'

print('Fetching exclusions from Radarr...')
headers = {'X-Api-Key': RADARR_API_KEY}
resp = requests.get(f'{RADARR_URL}/api/v3/exclusions', headers=headers, timeout=10)

if resp.status_code == 200:
    exclusions = resp.json()
    tmdb_ids = [e['tmdbId'] for e in exclusions if 'tmdbId' in e]
    
    print(f'✅ Found {len(exclusions)} exclusions ({len(tmdb_ids)} with TMDb IDs)')
    
    # Create correct format
    blacklist_data = {
        'version': '1.0',
        'exported_at': datetime.utcnow().isoformat() + 'Z',
        'source': 'radarr',
        'movies': sorted(tmdb_ids),
        'tv': []
    }
    
    with open(BLACKLIST_FILE, 'w') as f:
        json.dump(blacklist_data, f, indent=2)
    
    print(f'✅ Saved {len(tmdb_ids)} IDs to {BLACKLIST_FILE}')
else:
    print(f'❌ Error: HTTP {resp.status_code}')
