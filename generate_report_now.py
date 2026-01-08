#!/usr/bin/env python3
"""
Generate and send a full email report right now (bypassing schedule)
Same as what would be sent at 3 AM
"""

import os
import sys
sys.path.insert(0, '/usr/src/app')

from datetime import datetime
from list_sync.reports.report_generator import generate_html_report, generate_full_html_report
from list_sync.reports.email_sender import send_email
from list_sync.database import load_list_ids, get_list_items
from list_sync.ui.display import SyncResults
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sync_results_from_db():
    """Get sync results from database"""
    from list_sync.database import DB_FILE
    import sqlite3
    
    sync_results = SyncResults()
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Get total items
        cursor.execute('SELECT COUNT(*) FROM synced_items')
        sync_results.total_items = cursor.fetchone()[0]
        
        # Get status counts
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM synced_items 
            GROUP BY status
        ''')
        
        for status, count in cursor.fetchall():
            if status in sync_results.results:
                sync_results.results[status] = count
        
        # Calculate totals
        sync_results.results['already_available'] = sync_results.results.get('already_available', 0)
        sync_results.results['already_requested'] = sync_results.results.get('already_requested', 0)
        sync_results.results['pending'] = sync_results.results.get('already_requested', 0) + sync_results.results.get('requested', 0)
        sync_results.results['blocked'] = sync_results.results.get('blocked', 0)
        sync_results.results['not_found'] = sync_results.results.get('not_found', 0)
        sync_results.results['error'] = sync_results.results.get('error', 0)
        sync_results.results['request_failed'] = sync_results.results.get('request_failed', 0)
    
    return sync_results

def get_synced_lists():
    """Get list of synced lists"""
    lists = load_list_ids()
    synced_lists = []
    
    for list_info in lists:
        synced_lists.append({
            'type': list_info['type'],
            'id': list_info['id'],
            'item_count': 0  # Will be calculated from items
        })
    
    return synced_lists

def main():
    print("📊 Generating full email report...")
    
    # Check if email reports are enabled
    enabled = os.getenv('EMAIL_REPORT_ENABLED', 'false').lower() == 'true'
    if not enabled:
        print("❌ Email reports are disabled (EMAIL_REPORT_ENABLED=false)")
        print("   Set EMAIL_REPORT_ENABLED=true to enable")
        sys.exit(1)
    
    # Get sync results from database
    print("📈 Loading sync data from database...")
    sync_results = get_sync_results_from_db()
    synced_lists = get_synced_lists()
    
    print(f"   Found {sync_results.total_items} total items")
    print(f"   Found {len(synced_lists)} lists")
    
    # Get Overseerr URL for Seerr links
    overseerr_url = os.getenv('OVERSEERR_URL', '')
    
    # Generate HTML report (email body - 5 items per category)
    print("📝 Generating email HTML...")
    html = generate_html_report(sync_results, synced_lists, max_items_per_category=5, overseerr_url=overseerr_url)
    print(f"   Generated {len(html)} bytes")
    
    # Generate FULL HTML attachment (all items with Seerr links)
    print("📎 Generating full HTML attachment...")
    full_html = generate_full_html_report(sync_results, synced_lists, overseerr_url)
    full_html_bytes = full_html.encode('utf-8')
    print(f"   Generated {len(full_html_bytes)} bytes ({len(full_html_bytes)/1024:.1f} KB)")
    
    # Send email
    subject = f"List-Sync Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    attachment_filename = f"ListSync_Complete_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    
    print(f"📧 Sending email: {subject}")
    print(f"   To: {os.getenv('MAIL_TO')}")
    print(f"   Attachment: {attachment_filename}")
    
    result = send_email(
        subject=subject,
        body=html,
        html=True,
        pdf_attachment=full_html_bytes,
        pdf_filename=attachment_filename
    )
    
    if result == "sent":
        print("✅ Email sent successfully!")
        print(f"📬 Check inbox: {os.getenv('MAIL_TO')}")
    elif result:
        print(f"📁 Email saved to outbox: {result}")
    else:
        print("❌ Failed to send email")
        sys.exit(1)

if __name__ == "__main__":
    main()


