# 📊 List Breakdown Report - Design Document

**Inspired by:** Tautulli newsletters, Plex Wrapped, Kometa reports  
**Purpose:** HTML email showing per-list breakdown and missing movies  
**Date:** January 4, 2026

---

## 🎯 **Vision:**

A beautiful HTML email sent after each sync showing:
- Per-list statistics (in Plex vs missing)
- Missing movies grouped by reason
- Visual charts/progress bars
- Actionable insights

---

## 🎨 **Design Mockup:**

```
╔════════════════════════════════════════════════════════════════╗
║              LIST-SYNC REPORT - January 4, 2026                ║
╚════════════════════════════════════════════════════════════════╝

Sync completed in 18m 12s | 1811 items processed | 181 blocked

┌─────────────────────────────────────────────────────────────┐
│ OVERVIEW                                                     │
├─────────────────────────────────────────────────────────────┤
│ ✅ In Your Library:    1180 movies (65%)  █████████░░░░░░  │
│ 🔄 Pending Download:    504 movies (28%)  █████░░░░░░░░░░  │
│ ⛔ Blocked:             181 movies (10%)  ██░░░░░░░░░░░░░  │
│ ❌ Not Found:           127 movies (7%)   █░░░░░░░░░░░░░░  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ LIST BREAKDOWN (17 Lists)                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 📋 List: moviemarder/external/66765                         │
│    Total: 57 | In Plex: 45 (79%) | Missing: 12 (21%)       │
│    Missing: 8 pending, 2 blocked, 2 not found               │
│    ▓▓▓▓▓▓▓▓░░ 79%                                           │
│                                                              │
│ 📋 List: moviemarder/external/66767                         │
│    Total: 184 | In Plex: 120 (65%) | Missing: 64 (35%)     │
│    Missing: 50 pending, 10 blocked, 4 not found             │
│    ▓▓▓▓▓▓░░░░ 65%                                           │
│                                                              │
│ ... (15 more lists)                                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BLOCKLIST ACTIVITY                                           │
├─────────────────────────────────────────────────────────────┤
│ ⛔ 181 movies blocked from being requested                  │
│                                                              │
│ Top blocked movies this sync:                                │
│   • Movie Title 1 (2024) - TMDB: 12345                      │
│   • Movie Title 2 (2023) - TMDB: 67890                      │
│   • Movie Title 3 (2024) - TMDB: 11111                      │
│   ... 178 more                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ACTION ITEMS                                                 │
├─────────────────────────────────────────────────────────────┤
│ • 504 movies pending download in Overseerr                   │
│ • 127 movies couldn't be matched (check list quality)        │
│ • 181 movies blocked (review Radarr exclusions)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ **Implementation Plan:**

### **Phase 1: Data Collection**

**Add to `sync_media_to_overseerr()` function:**

```python
# After sync completes, collect statistics per list
list_stats = {}
for list_info in synced_lists:
    list_key = f"{list_info['type']}:{list_info['id']}"
    
    # Query database for this list's items
    items = get_list_items(list_info['type'], list_info['id'])
    
    stats = {
        'total': len(items),
        'in_library': 0,
        'pending': 0,
        'blocked': 0,
        'not_found': 0,
        'error': 0
    }
    
    for item in items:
        status = item['status']
        if status in ['already_available', 'skipped']:
            stats['in_library'] += 1
        elif status == 'already_requested':
            stats['pending'] += 1
        elif status == 'blocked':
            stats['blocked'] += 1
        elif status == 'not_found':
            stats['not_found'] += 1
        elif status in ['error', 'request_failed']:
            stats['error'] += 1
    
    list_stats[list_key] = stats
```

### **Phase 2: HTML Template**

**Create: `list_sync/templates/report_email.html`**

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  padding: 30px; border-radius: 10px; text-align: center; }
        .overview { background: #2a2a2a; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .list-item { background: #2a2a2a; padding: 15px; margin: 10px 0; border-radius: 8px; }
        .progress-bar { height: 20px; background: #444; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #4ade80 0%, #22c55e 100%); }
        .stat { display: inline-block; margin: 10px 20px; }
        .emoji { font-size: 1.2em; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #333; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🎬 List-Sync Report</h1>
            <p>{{ sync_date }} | {{ total_items }} items | {{ duration }}</p>
        </div>
        
        <!-- Overview -->
        <div class="overview">
            <h2>📊 Overview</h2>
            <div class="stat">✅ In Library: {{ in_library }} ({{ in_library_pct }}%)</div>
            <div class="stat">🔄 Pending: {{ pending }} ({{ pending_pct }}%)</div>
            <div class="stat">⛔ Blocked: {{ blocked }} ({{ blocked_pct }}%)</div>
        </div>
        
        <!-- Per-List Breakdown -->
        <h2>📋 List Breakdown</h2>
        {% for list in lists %}
        <div class="list-item">
            <h3>{{ list.name }}</h3>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {{ list.coverage_pct }}%"></div>
            </div>
            <p>{{ list.in_plex }}/{{ list.total }} in library ({{ list.coverage_pct }}%)</p>
            
            {% if list.missing > 0 %}
            <details>
                <summary>Missing: {{ list.missing }} movies</summary>
                <table>
                    <tr><th>Reason</th><th>Count</th></tr>
                    {% if list.pending > 0 %}<tr><td>🔄 Pending</td><td>{{ list.pending }}</td></tr>{% endif %}
                    {% if list.blocked > 0 %}<tr><td>⛔ Blocked</td><td>{{ list.blocked }}</td></tr>{% endif %}
                    {% if list.not_found > 0 %}<tr><td>❌ Not Found</td><td>{{ list.not_found }}</td></tr>{% endif %}
                </table>
            </details>
            {% endif %}
        </div>
        {% endfor %}
        
        <!-- Blocklist Activity -->
        {% if blocked_items %}
        <div class="overview">
            <h2>⛔ Blocklist Activity</h2>
            <p>{{ blocked_count }} movies filtered this sync</p>
            <details>
                <summary>View blocked movies</summary>
                <ul>
                {% for movie in blocked_items[:20] %}
                    <li>{{ movie.title }} ({{ movie.year }}) - TMDB: {{ movie.tmdb_id }}</li>
                {% endfor %}
                {% if blocked_count > 20 %}
                    <li>... and {{ blocked_count - 20 }} more</li>
                {% endif %}
                </ul>
            </details>
        </div>
        {% endif %}
        
        <!-- Footer -->
        <p style="text-align: center; color: #888; margin-top: 40px;">
            List-Sync v{{ version }} | Next sync: {{ next_sync_time }}
        </p>
    </div>
</body>
</html>
```

### **Phase 3: Report Generator**

**Create: `list_sync/reports/email_report.py`**

```python
from jinja2 import Template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailReportGenerator:
    """Generates HTML email reports"""
    
    def generate_report(self, sync_results, list_stats):
        """Generate HTML report from sync results"""
        
        # Load template
        with open('templates/report_email.html', 'r') as f:
            template = Template(f.read())
        
        # Prepare data
        data = {
            'sync_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'total_items': sync_results.total_items,
            'duration': format_duration(sync_results.total_time),
            'in_library': sync_results.results['already_available'],
            'in_library_pct': calc_pct(sync_results.results['already_available'], sync_results.total_items),
            'pending': sync_results.results['already_requested'],
            'pending_pct': calc_pct(sync_results.results['already_requested'], sync_results.total_items),
            'blocked': sync_results.results['blocked'],
            'blocked_pct': calc_pct(sync_results.results['blocked'], sync_results.total_items),
            'lists': list_stats,
            'blocked_items': sync_results.blocked_items,
            'blocked_count': sync_results.results['blocked'],
            'version': '0.7.0',
            'next_sync_time': calc_next_sync()
        }
        
        # Render HTML
        html = template.render(**data)
        return html
    
    def send_email(self, html, to_email):
        """Send HTML email via SMTP"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"List-Sync Report - {datetime.now().strftime('%Y-%m-%d')}"
        msg['From'] = "list-sync@yourdomain.com"
        msg['To'] = to_email
        
        msg.attach(MIMEText(html, 'html'))
        
        # Send via SMTP (or save to file)
        # ... SMTP code
```

### **Phase 4: Integration**

**Modify `sync_media_to_overseerr()` to collect list stats:**

```python
# At end of sync_media_to_overseerr():

# Collect per-list statistics
list_stats = []
for list_info in synced_lists:
    items = get_list_items(list_info['type'], list_info['id'])
    
    stats = calculate_list_stats(items)
    stats['name'] = format_list_name(list_info)
    list_stats.append(stats)

# Generate report
if os.getenv('EMAIL_REPORT_ENABLED', 'false').lower() == 'true':
    from .reports.email_report import EmailReportGenerator
    generator = EmailReportGenerator()
    html = generator.generate_report(sync_results, list_stats)
    
    # Send or save
    if os.getenv('EMAIL_REPORT_TO'):
        generator.send_email(html, os.getenv('EMAIL_REPORT_TO'))
    else:
        # Save to file
        with open('data/latest_report.html', 'w') as f:
            f.write(html)
```

---

## 📧 **Delivery Options:**

### **Option 1: Email (Like Tautulli)**

**Pros:**
- Professional look
- Can view anywhere
- Preserved history

**Cons:**
- Needs SMTP setup
- Might go to spam

**Config:**
```yaml
environment:
  - EMAIL_REPORT_ENABLED=true
  - EMAIL_REPORT_TO=your@email.com
  - SMTP_HOST=smtp.gmail.com
  - SMTP_PORT=587
  - SMTP_USER=your@gmail.com
  - SMTP_PASSWORD=${SMTP_PASSWORD}
```

### **Option 2: Discord Webhook (Easier)**

**Pros:**
- Already have Discord webhook
- Instant delivery
- No SMTP needed

**Cons:**
- Limited formatting
- No HTML support
- Character limits

**Solution:** Use Discord embeds:

```python
def send_discord_report(list_stats, sync_results):
    """Send formatted report to Discord"""
    
    # Main embed
    embed = {
        "title": "📊 List-Sync Report",
        "color": 0x764ba2,
        "fields": [
            {
                "name": "Overview",
                "value": f"✅ In Library: {in_lib}\n🔄 Pending: {pending}\n⛔ Blocked: {blocked}"
            }
        ]
    }
    
    # Per-list embeds (separate messages or fields)
    for list_stat in list_stats[:10]:  # Discord limit
        embed["fields"].append({
            "name": f"📋 {list_stat['name'][:50]}",
            "value": f"{list_stat['in_plex']}/{list_stat['total']} ({list_stat['coverage_pct']}%)",
            "inline": True
        })
    
    # Send to webhook
    requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
```

### **Option 3: HTML File + Web View (Best of Both)**

**Pros:**
- Beautiful HTML
- View in browser
- No email/Discord limits
- Can download/share

**Implementation:**
```python
# Save HTML report
with open('/data/reports/latest.html', 'w') as f:
    f.write(html_report)

# Serve via API
@app.get("/api/reports/latest")
async def get_latest_report():
    with open('/data/reports/latest.html', 'r') as f:
        return HTMLResponse(content=f.read())
```

Then access at: `http://saturn.local:4222/api/reports/latest`

---

## 🎨 **Industry Solutions Reference:**

### **1. Tautulli Newsletters:**
- HTML email with tables
- Charts showing watch stats
- Recently added section
- Upcoming content

**What to borrow:**
- Clean table design
- Progress bars
- Color coding
- Expandable sections

### **2. Plex Wrapped:**
- Year in review style
- Big numbers with animations
- Comparison to previous periods
- Visual hierarchy

**What to borrow:**
- Bold statistics
- Visual percentages
- Trend indicators

### **3. Kometa Reports:**
- Collection-based breakdown
- Missing from collection reports
- Visual posters/grids

**What to borrow:**
- Grid layouts for items
- Missing item highlighting
- Collection completion %

### **4. Sonarr/Radarr Calendar:**
- Upcoming releases
- Missing episodes/movies
- Status indicators

**What to borrow:**
- Status color coding
- Grouped by status
- Quick scan layout

---

## 💡 **Recommended Approach:**

**START SIMPLE (Phase 1):**

1. **Discord Embed Enhancement**
   - Extend existing Discord webhook
   - Add per-list breakdown
   - Use Discord embeds for formatting
   - Quick win, uses existing infrastructure

**THEN ADD (Phase 2):**

2. **HTML Report to File**
   - Generate beautiful HTML
   - Save to `/data/reports/latest.html`
   - Serve via API endpoint
   - View in browser at `http://saturn.local:4222/reports`

**FINALLY (Phase 3):**

3. **Email Delivery (Optional)**
   - Add SMTP integration
   - Send HTML email
   - Like Tautulli newsletters

---

## 📊 **Data Structure:**

```python
{
  "sync_summary": {
    "timestamp": "2026-01-04T11:00:00Z",
    "duration_seconds": 1092,
    "total_items": 1811,
    "totals": {
      "in_library": 1180,
      "pending": 504,
      "blocked": 181,
      "not_found": 127,
      "errors": 19
    }
  },
  "list_breakdown": [
    {
      "list_type": "mdblist",
      "list_id": "https://...",
      "display_name": "66765",
      "total": 57,
      "in_library": 45,
      "coverage_pct": 79.0,
      "missing": {
        "pending": 8,
        "blocked": 2,
        "not_found": 2
      }
    },
    // ... more lists
  ],
  "blocked_items": [
    {"title": "Movie", "tmdb_id": 12345, "year": 2024},
    // ... more
  ]
}
```

---

## 🎯 **My Recommendation:**

**PHASE 1 (Quick Win - 2 hours):**
```
Enhance Discord webhook with per-list stats
✅ Uses existing infrastructure
✅ Immediate value
✅ No new dependencies
```

**PHASE 2 (Medium - 4 hours):**
```
Add HTML report generation + API endpoint
✅ Beautiful visualization
✅ View in browser
✅ No email complexity
```

**PHASE 3 (Optional - 6 hours):**
```
Email delivery via SMTP
✅ Professional delivery
✅ Like Tautulli
✅ Preserved history
```

---

## 📝 **Configuration:**

```yaml
environment:
  # Report Settings
  - REPORT_ENABLED=true
  - REPORT_TYPE=discord  # discord, html, email, all
  
  # Discord (already have this)
  - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
  
  # HTML Report
  - REPORT_HTML_ENABLED=true
  - REPORT_HTML_PATH=/data/reports
  
  # Email (optional)
  - EMAIL_REPORT_ENABLED=false
  - EMAIL_REPORT_TO=your@email.com
  - SMTP_HOST=smtp.gmail.com
  - SMTP_PORT=587
  - SMTP_USER=${SMTP_USER}
  - SMTP_PASSWORD=${SMTP_PASSWORD}
```

---

## 🎨 **Example Output (Discord Embeds):**

```
📊 List-Sync Report - January 4, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overview
✅ In Library: 1180 (65%)
🔄 Pending: 504 (28%)
⛔ Blocked: 181 (10%)

List Breakdown (showing top 10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 List 66765
57 total | 45 in Plex (79%) | 12 missing (8 pending, 2 blocked, 2 not found)

📋 List 66767  
184 total | 120 in Plex (65%) | 64 missing (50 pending, 10 blocked, 4 not found)

... (8 more)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Next sync: 6 hours | View details: http://saturn.local:4222/reports
```

---

## 🔧 **Technical Details:**

### **Dependencies:**
- `jinja2` (for HTML templating) - lightweight
- No additional dependencies for Discord (already have requests)

### **Performance:**
- Generate after sync completes
- Query database once per list
- Cache results
- ~1-2 seconds overhead

### **Storage:**
- HTML reports: ~50-100KB each
- Keep last 30 days
- Auto-cleanup old reports

---

## ✅ **What Do You Think?**

Would you like me to implement:

**Option A (Quick):** Discord embed enhancement (2 hours)
- Per-list breakdown in Discord
- Uses existing webhook
- Immediate value

**Option B (Better):** HTML report + API (4 hours)
- Beautiful HTML report
- View in browser
- More detailed breakdown

**Option C (Complete):** All three (10 hours)
- Discord + HTML + Email
- Maximum flexibility
- Like Tautulli

**I recommend starting with Option A (Discord), then adding Option B (HTML) later!**

---

**What's your preference?** 🎯

