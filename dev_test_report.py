#!/usr/bin/env python3
"""
DEVELOPMENT TEST SCRIPT
Generate report using existing database data - NO SYNC NEEDED!
This allows fast iteration during development.
"""
import sys
import sqlite3
import os
from datetime import datetime

sys.path.insert(0, '/usr/src/app')
os.environ['EMAIL_REPORT_ENABLED'] = 'true'
os.environ['MAIL_TO'] = 'fabianmaass@me.com'

print("=" * 70)
print("DEVELOPMENT TEST - Using Existing Database")
print("(No sync required - instant report generation!)")
print("=" * 70)
print()

# Check both database locations
db_new = '/usr/src/app/data/list_sync.db'
db_old = '/data/list_sync.db'

print("Checking databases:")
import os.path
if os.path.exists(db_new):
    size = os.path.getsize(db_new) / 1024
    print(f"  ✓ {db_new}: {size:.1f} KB")
if os.path.exists(db_old):
    size = os.path.getsize(db_old) / 1024
    print(f"  ✓ {db_old}: {size:.1f} KB")
print()

# Use the NEW database with actual data
conn = sqlite3.connect(db_new)
cursor = conn.cursor()

# Get status breakdown
cursor.execute('SELECT status, COUNT(*) FROM synced_items GROUP BY status')
status_counts = {}
total_items = 0
print('Database status breakdown:')
print('=' * 70)
for row in cursor.fetchall():
    status_counts[row[0]] = row[1]
    total_items += row[1]
    print(f'{row[0]:25s}: {row[1]:6d} items')

print(f'\n{"TOTAL":25s}: {total_items:6d} items')
print('=' * 70)
print()

# Get sample of different statuses
print('Sample items from each category:')
print('=' * 70)

for status in ['already_available', 'already_requested', 'blocked', 'not_found', 'error', 'skipped']:
    cursor.execute(f'''
        SELECT title, year FROM synced_items 
        WHERE status = ? 
        LIMIT 3
    ''', (status,))
    
    results = cursor.fetchall()
    if results:
        print(f'\n{status.upper()}:')
        for row in results:
            year = f' ({row[1]})' if row[1] else ''
            print(f'  • {row[0]}{year}')

conn.close()

print()
print('=' * 70)
print('Now generating report with this REAL data...')
print('=' * 70)
print()

# NOW generate the actual report
try:
    from pathlib import Path
    from list_sync.utils.logger import DATA_DIR
    from list_sync.database import load_list_ids
    from list_sync.reports.report_generator import generate_html_report, generate_pdf_report
    from list_sync.reports.email_sender import send_email
    
    # Remove schedule lock
    last_sent_file = Path(DATA_DIR) / "reports" / ".last_report_sent"
    if last_sent_file.exists():
        last_sent_file.unlink()
    
    # Load lists
    lists = load_list_ids()
    
    # Create results from database
    class Results:
        def __init__(self):
            self.total_items = total_items
            self.start_time = 1050
            self.results = {
                'already_available': status_counts.get('already_available', 0),
                'already_requested': status_counts.get('already_requested', 0),
                'requested': status_counts.get('requested', 0),
                'skipped': status_counts.get('skipped', 0),
                'blocked': status_counts.get('blocked', 0),
                'not_found': status_counts.get('not_found', 0),
                'error': status_counts.get('error', 0) + status_counts.get('request_failed', 0)
            }
    
    results = Results()
    synced_lists = [{'type': lst['type'], 'id': lst['id']} for lst in lists]
    
    print(f"Generating report:")
    print(f"  Total items: {results.total_items}")
    print(f"  In library: {results.results['already_available'] + results.results['skipped']}")
    print(f"  Pending: {results.results['already_requested']}")
    print(f"  Blocked: {results.results['blocked']}")
    print(f"  Lists: {len(synced_lists)}")
    print()
    
    # Generate reports
    html = generate_html_report(results, synced_lists, max_items_per_category=5)
    pdf_data = generate_pdf_report(results, synced_lists)
    
    print(f"✓ Email HTML: {len(html)} bytes")
    if pdf_data:
        print(f"✓ PDF: {len(pdf_data)} bytes ({len(pdf_data)/1024:.1f} KB)")
    
    # Send
    subject = f"List-Sync Report (Dev Test - Real Data) - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    pdf_filename = f"ListSync_Report_DevTest_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    
    result = send_email(subject, html, html=True, pdf_attachment=pdf_data, pdf_filename=pdf_filename)
    
    print()
    print("=" * 70)
    print(f"✅ SENT: {result}")
    print("=" * 70)
    print("\nCheck fabianmaass@me.com!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

