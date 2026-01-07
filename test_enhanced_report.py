#!/usr/bin/env python3
"""Test enhanced report with movie titles and PDF attachment"""
import sys
sys.path.insert(0, '/usr/src/app')
import os
from datetime import datetime

os.environ['EMAIL_REPORT_ENABLED'] = 'true'
os.environ['MAIL_TO'] = 'fabianmaass@me.com'

print("=" * 70)
print("TESTING ENHANCED REPORT")
print("  ✓ Movie titles in email (5 per category)")
print("  ✓ Complete PDF attachment (all items)")
print("=" * 70)
print()

try:
    from list_sync.database import load_list_ids, get_sync_stats
    from list_sync.reports.report_generator import generate_html_report, generate_pdf_report
    from list_sync.reports.email_sender import send_email
    from pathlib import Path
    from list_sync.utils.logger import DATA_DIR
    
    # Remove schedule lock for testing
    last_sent_file = Path(DATA_DIR) / "reports" / ".last_report_sent"
    if last_sent_file.exists():
        last_sent_file.unlink()
    
    # Get real data
    lists = load_list_ids()
    stats = get_sync_stats()
    
    print(f"✓ Loaded {len(lists)} lists")
    print(f"✓ Database stats: {stats}")
    print()
    
    # Create results
    class Results:
        def __init__(self):
            self.total_items = stats.get('total_items', 1788)
            self.start_time = 1380
            self.results = {
                'already_available': stats.get('already_available', 0),
                'already_requested': stats.get('already_requested', 0),
                'requested': stats.get('requested', 0),
                'skipped': stats.get('skipped', 0),
                'blocked': stats.get('blocked', 0),
                'not_found': stats.get('not_found', 0),
                'error': stats.get('error', 0)
            }
    
    results = Results()
    synced_lists = [{'type': lst['type'], 'id': lst['id']} for lst in lists]
    
    print(f"Generating reports:")
    print(f"  - Email HTML (5 items per category)")
    print(f"  - PDF attachment (ALL items)")
    print()
    
    # Generate email HTML
    html = generate_html_report(results, synced_lists, max_items_per_category=5)
    print(f"✓ Email HTML: {len(html)} bytes")
    
    # Generate PDF
    pdf_data = generate_pdf_report(results, synced_lists)
    if pdf_data:
        print(f"✓ PDF generated: {len(pdf_data)} bytes")
    else:
        print("✗ PDF generation failed")
    
    # Send email with PDF attachment
    subject = f"List-Sync Enhanced Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    pdf_filename = f"ListSync_Complete_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    result = send_email(subject, html, html=True, pdf_attachment=pdf_data, pdf_filename=pdf_filename)
    
    print()
    print("=" * 70)
    print(f"✅ EMAIL SENT: {result}")
    print("=" * 70)
    print()
    print("Check fabianmaass@me.com for:")
    print("  ✓ Email with movie titles (up to 5 per category)")
    print("  ✓ PDF attachment with COMPLETE list")
    print()
    if pdf_data:
        print(f"PDF size: {len(pdf_data) / 1024:.1f} KB")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

