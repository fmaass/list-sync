#!/usr/bin/env python3
"""Check what's ACTUALLY in the database and why it shows 100%"""
import sqlite3

db = '/usr/src/app/data/list_sync.db'
conn = sqlite3.connect(db)
cursor = conn.cursor()

print("=" * 70)
print("INVESTIGATING: Why does report show 100% in library?")
print("=" * 70)
print()

# Status breakdown
cursor.execute('SELECT status, COUNT(*) FROM synced_items GROUP BY status')
print('Database Status Counts:')
for row in cursor.fetchall():
    print(f'  {row[0]:25s}: {row[1]:6d}')

print()

# Check if "skipped" means "in library" or something else
cursor.execute('''
    SELECT title, year, status, overseerr_id
    FROM synced_items 
    WHERE status = 'skipped'
    LIMIT 10
''')

print('Sample "skipped" items:')
print('(These are counted as "in library" in the report)')
print('-' * 70)
for row in cursor.fetchall():
    print(f'{row[0][:40]:40s} ({row[1]}) - overseerr_id: {row[3]}')

print()
print('Analysis:')
print('  - Status "skipped" = already in Radarr (SKIP_EXISTING=true)')
print('  - Report counts "skipped" as "in library"')
print('  - This is CORRECT - these movies ARE available!')
print()
print('Expected behavior:')
print('  - Some items should be "already_requested" (pending download)')
print('  - Some items should be "blocked" (on exclusion list)')
print('  - But if SKIP_EXISTING=true, they never get requested')
print('  - So they show as "skipped" instead')

conn.close()

