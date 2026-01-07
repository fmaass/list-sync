# 🚀 Fast Development Testing for Email Reports

**Problem:** Waiting 20+ minutes for full sync to test report changes is too slow  
**Solution:** Use sample/mock data for instant testing

---

## 📊 Option 1: Create Sample Database (Recommended)

### Create Test Data Script

```python
# create_test_data.py
import sqlite3
import random

# Connect to test database
conn = sqlite3.connect('/usr/src/app/data/list_sync_test.db')
cursor = conn.cursor()

# Create tables (copy from init_database())
cursor.execute('''
    CREATE TABLE IF NOT EXISTS synced_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        media_type TEXT DEFAULT 'movie',
        year INTEGER,
        imdb_id TEXT,
        tmdb_id TEXT,
        overseerr_id INTEGER,
        status TEXT,
        last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Insert realistic test data
statuses_with_weights = [
    ('already_available', 100),  # 100 items in library
    ('already_requested', 30),    # 30 pending
    ('blocked', 10),              # 10 blocked
    ('not_found', 5),             # 5 not found
    ('error', 3),                 # 3 errors
]

sample_movies = [
    ('The Matrix Resurrections', 2021),
    ('Dune: Part Two', 2024),
    ('Blade Runner 2099', 2025),
    ('The Northman', 2022),
    # ... add more
]

for status, count in statuses_with_weights:
    for i in range(count):
        title = f"Test Movie {i} ({status})"
        year = 2020 + random.randint(0, 5)
        cursor.execute('''
            INSERT INTO synced_items (title, year, status)
            VALUES (?, ?, ?)
        ''', (title, year, status))

conn.commit()
conn.close()
print("Test database created!")
```

### Use Test Database

```python
# Override DB_FILE temporarily for testing
import os
os.environ['DB_FILE'] = '/usr/src/app/data/list_sync_test.db'

# Now generate report - uses test data!
from list_sync.reports.report_generator import send_sync_report
# ... generate report ...
```

---

## 📊 Option 2: Mock Data Generator (Fastest)

```python
# instant_test_report.py
"""Generate report with mock data - NO DATABASE NEEDED!"""

# Create realistic mock data
class MockResults:
    def __init__(self):
        self.total_items = 200
        self.start_time = 600
        self.results = {
            'already_available': 120,  # 60% in library
            'already_requested': 50,    # 25% pending
            'requested': 5,
            'skipped': 0,
            'blocked': 15,              # 7.5% blocked
            'not_found': 8,             # 4% not found
            'error': 2
        }

mock_missing_items = {
    'pending': [
        {'title': 'The Matrix Resurrections', 'year': 2021},
        {'title': 'Dune: Part Two', 'year': 2024},
        {'title': 'Blade Runner 2099', 'year': 2025},
        # ... add realistic titles
    ],
    'blocked': [
        {'title': 'Bad Movie A', 'year': 2020},
        {'title': 'Bad Movie B', 'year': 2019},
        # ...
    ],
    'not_found': [
        {'title': 'Obscure Foreign Film', 'year': 2023},
        # ...
    ],
    'errors': []
}

# Generate report instantly!
html = _generate_html(MockResults(), mock_list_breakdown)
# Test, iterate, repeat - all in seconds!
```

---

## 🎯 Recommended Workflow

### For Development (Iterating on Report Design):

```bash
# 1. Create mock data once
python create_test_data.py

# 2. Test report generation (instant!)
python instant_test_report.py

# 3. Iterate on HTML/CSS/layout
#    Edit report_generator.py
#    Run instant_test_report.py again
#    Check email
#    Repeat until perfect

# Takes: ~30 seconds per iteration instead of 20+ minutes!
```

### For Production Testing:

```bash
# Only when ready to test with real data
curl -X POST http://localhost:4222/api/sync/trigger
# Wait 20 minutes
# Generate real report
```

---

## 💡 Better Approach: Use Existing Database

Since the sync just completed, I can generate a report using the REAL database at `/usr/src/app/data/list_sync.db` right now!

Let me do that immediately...

