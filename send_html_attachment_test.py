import sys, os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/usr/src/app')
os.environ['EMAIL_REPORT_ENABLED'] = 'true'
os.environ['MAIL_TO'] = 'fabianmaass@me.com'

from list_sync.utils.logger import DATA_DIR
from list_sync.database import load_list_ids, get_sync_stats
from list_sync.reports.report_generator import generate_html_report, generate_full_html_report
from list_sync.reports.email_sender import send_email

# Remove schedule lock
Path(DATA_DIR + '/reports/.last_report_sent').unlink(missing_ok=True)

# Get data
stats = get_sync_stats()
lists = load_list_ids()

print(f'Data: {len(lists)} lists, Stats: {stats}')

# Check manual approval config
manual_user = os.getenv('MANUAL_APPROVAL_USER_ID', '1')
manual_lists = os.getenv('MDBLIST_MANUAL_LISTS', '')
print(f'Manual approval user: {manual_user}')
print(f'Manual lists: {manual_lists[:100]}...')

# Check which lists are configured for manual approval
for lst in lists:
    if lst.get('user_id') == '2':
        print(f'  Manual: {lst["id"]}')

class R:
    def __init__(self):
        self.total_items = sum(stats.values()) if stats else 1788
        self.start_time = 1050
        self.results = stats if stats else {'already_available': 1146, 'already_requested': 494, 'request_failed': 148}

r = R()
sl = [{'type': l['type'], 'id': l['id']} for l in lists]

# Get Overseerr URL
overseerr_url = os.getenv('OVERSEERR_URL', '')
print(f'Overseerr URL: {overseerr_url}')

# Generate HTML (5 items for email)
html = generate_html_report(r, sl, 5, overseerr_url)

# Generate FULL HTML with ALL items and Seerr links
full_html = generate_full_html_report(r, sl, overseerr_url)
full_bytes = full_html.encode('utf-8')

print(f'Email HTML: {len(html)} bytes')
print(f'Attachment HTML: {len(full_bytes)} bytes ({len(full_bytes)/1024:.1f} KB)')

# Send with HTML attachment
subj = f'List-Sync with HTML Attachment - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
attach_name = f'ListSync_Complete_Report_{datetime.now().strftime("%Y%m%d_%H%M")}.html'

result = send_email(subj, html, True, full_bytes, attach_name)
print(f'Sent: {result}')
print(f'Attachment: {attach_name}')

