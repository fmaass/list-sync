#!/usr/bin/env python3
import sqlite3
import os
import requests

DB = '/data/list_sync.db'
conn = sqlite3.connect(DB)
cursor = conn.cursor()

# Get movies unique to manual lists that are already_requested
cursor.execute('''
    SELECT DISTINCT si.title, si.overseerr_id
    FROM synced_items si
    INNER JOIN item_lists il ON si.id = il.item_id  
    INNER JOIN lists l ON il.list_type = l.list_type AND il.list_id = l.list_id
    WHERE l.user_id = "2" 
      AND si.status = "already_requested"
      AND si.overseerr_id IS NOT NULL
      AND si.overseerr_id NOT IN (
          SELECT DISTINCT si2.overseerr_id
          FROM synced_items si2
          INNER JOIN item_lists il2 ON si2.id = il2.item_id
          INNER JOIN lists l2 ON il2.list_type = l2.list_type AND il2.list_id = l2.list_id
          WHERE l2.user_id = "1" AND si2.overseerr_id IS NOT NULL
      )
    LIMIT 10
''')
movies = cursor.fetchall()

print(f'Unrequesting {len(movies)} sample movies...\n')

api_key = os.getenv('OVERSEERR_API_KEY')
headers = {'X-Api-Key': api_key}
base_url = 'http://jellyseerr:5055'

for title, tmdb_id in movies:
    # Get media info
    resp = requests.get(f'{base_url}/api/v1/movie/{tmdb_id}', headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        media_info = data.get('mediaInfo', {})
        req_list = media_info.get('requests', [])
        status = media_info.get('status')
        
        print(f'{title} (TMDB:{tmdb_id}):')
        print(f'  Current status: {status}')
        
        if req_list and status in [1, 2]:  # Pending or Approved (not downloaded)
            request_id = req_list[0].get('id')
            del_resp = requests.delete(f'{base_url}/api/v1/request/{request_id}', headers=headers)
            if del_resp.status_code in [200, 204]:
                print(f'  ✓ Unrequested (request ID {request_id})')
            else:
                print(f'  ✗ Failed to unrequest: {del_resp.status_code}')
        elif status in [4, 5]:
            print(f'  → Already downloaded, skipping')
        else:
            print(f'  → Not requested or other status')
    print()

print('✅ Done')
