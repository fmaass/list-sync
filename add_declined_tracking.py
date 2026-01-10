#!/usr/bin/env python3
"""
Add declined_requests tracking to prevent re-requesting declined movies.
Run this once to add the table to your database.
"""
import sqlite3
import os

DB_FILE = "/data/list_sync.db" if os.path.exists("/data/list_sync.db") else '/usr/src/app/data/list_sync.db'

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

print(f'Using database: {DB_FILE}\n')

# Create declined_requests table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS declined_requests (
        tmdb_id TEXT NOT NULL,
        media_type TEXT NOT NULL,
        title TEXT,
        year INTEGER,
        declined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        declined_by_user_id TEXT,
        reason TEXT,
        PRIMARY KEY (tmdb_id, media_type)
    )
''')

# Create index for faster lookups
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_declined_requests_tmdb 
    ON declined_requests(tmdb_id, media_type)
''')

conn.commit()
print('✅ Created declined_requests table')

# Show current count
cursor.execute('SELECT COUNT(*) FROM declined_requests')
count = cursor.fetchone()[0]
print(f'Current declined requests: {count}')

conn.close()
print('\n✅ Database migration complete')
