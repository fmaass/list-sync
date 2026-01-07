import sys
import sqlite3
sys.path.insert(0, '/usr/src/app')

conn = sqlite3.connect('/data/list_sync.db')
cursor = conn.cursor()

# Get status breakdown
cursor.execute('SELECT status, COUNT(*) FROM synced_items GROUP BY status')
print('Status breakdown in database:')
print('=' * 50)
for row in cursor.fetchall():
    print(f'{row[0]:20s}: {row[1]:5d} items')

print()
print('Sample items from each status:')
print('=' * 50)

cursor.execute('''
    SELECT status, title, year 
    FROM synced_items 
    WHERE status IN ('already_requested', 'blocked', 'not_found', 'error')
    LIMIT 20
''')

for row in cursor.fetchall():
    print(f'{row[0]:20s}: {row[1]} ({row[2]})')

conn.close()

