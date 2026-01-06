"""
Report Generator for List-Sync
Generates HTML email reports with per-list breakdown
"""

import logging
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

from ..database import get_list_items

logger = logging.getLogger(__name__)


def generate_html_report(sync_results, synced_lists) -> str:
    """
    Generate HTML email report
    
    Args:
        sync_results: SyncResults object
        synced_lists: List of synced list info
        
    Returns:
        str: HTML content
    """
    # Collect per-list statistics
    list_breakdown = []
    
    for list_info in synced_lists:
        list_type = list_info['type']
        list_id = list_info['id']
        
        try:
            # Get items for this list
            items = get_list_items(list_type, list_id)
            
            # Calculate statistics
            stats = {
                'in_library': 0,
                'pending': 0,
                'blocked': 0,
                'not_found': 0,
                'errors': 0
            }
            
            for item in items:
                status = item.get('status', 'unknown')
                if status in ['already_available', 'skipped']:
                    stats['in_library'] += 1
                elif status == 'already_requested':
                    stats['pending'] += 1
                elif status == 'blocked':
                    stats['blocked'] += 1
                elif status == 'not_found':
                    stats['not_found'] += 1
                elif status in ['error', 'request_failed']:
                    stats['errors'] += 1
            
            total = len(items)
            missing = total - stats['in_library']
            coverage_pct = (stats['in_library'] / total * 100) if total > 0 else 0
            
            # Format list name
            if 'external/' in list_id:
                display_name = f"List {list_id.split('/')[-1]}"
            else:
                display_name = list_id[-40:] if len(list_id) > 40 else list_id
            
            list_breakdown.append({
                'name': display_name,
                'total': total,
                'in_library': stats['in_library'],
                'missing': missing,
                'coverage_pct': coverage_pct,
                'pending': stats['pending'],
                'blocked': stats['blocked'],
                'not_found': stats['not_found'],
                'errors': stats['errors']
            })
            
        except Exception as e:
            logger.warning(f"Failed to get stats for list {list_type}:{list_id}: {e}")
    
    # Sort by coverage (worst first)
    list_breakdown.sort(key=lambda x: x['coverage_pct'])
    
    # Generate HTML
    html = _generate_html(sync_results, list_breakdown)
    return html


def _generate_html(sync_results, list_breakdown: List[Dict]) -> str:
    """Generate HTML content"""
    
    # Calculate totals
    total_items = sync_results.total_items
    in_library = sync_results.results['already_available'] + sync_results.results['skipped']
    pending = sync_results.results['already_requested'] + sync_results.results['requested']
    blocked = sync_results.results['blocked']
    not_found = sync_results.results['not_found']
    errors = sync_results.results['error']
    
    in_library_pct = (in_library / total_items * 100) if total_items > 0 else 0
    pending_pct = (pending / total_items * 100) if total_items > 0 else 0
    blocked_pct = (blocked / total_items * 100) if total_items > 0 else 0
    
    # Format duration
    duration_mins = int(sync_results.start_time // 60) if hasattr(sync_results, 'start_time') else 0
    duration_secs = int(sync_results.start_time % 60) if hasattr(sync_results, 'start_time') else 0
    
    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: #1a1a1a;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 32px;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 14px;
        }}
        .overview {{
            padding: 30px;
            background: #222;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .stat-card {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .stat-card.success {{ border-left-color: #22c55e; }}
        .stat-card.warning {{ border-left-color: #f59e0b; }}
        .stat-card.danger {{ border-left-color: #ef4444; }}
        .stat-number {{
            font-size: 32px;
            font-weight: bold;
            margin: 5px 0;
        }}
        .stat-label {{
            font-size: 14px;
            opacity: 0.7;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-pct {{
            font-size: 18px;
            opacity: 0.8;
        }}
        .list-section {{
            padding: 30px;
        }}
        .list-item {{
            background: #2a2a2a;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .list-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .list-name {{
            font-size: 18px;
            font-weight: 500;
        }}
        .list-stats {{
            font-size: 14px;
            opacity: 0.8;
        }}
        .progress-bar {{
            height: 24px;
            background: #333;
            border-radius: 12px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
            color: white;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }}
        .missing-breakdown {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #333;
            font-size: 13px;
        }}
        .missing-item {{
            display: inline-block;
            margin: 5px 10px 5px 0;
            padding: 4px 12px;
            background: #333;
            border-radius: 4px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            opacity: 0.6;
            font-size: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        th {{
            background: #2a2a2a;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            opacity: 0.7;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🎬 List-Sync Report</h1>
            <p>{datetime.now().strftime('%B %d, %Y at %H:%M')} | {total_items} items processed in {duration_mins}m {duration_secs}s</p>
        </div>
        
        <!-- Overview -->
        <div class="overview">
            <h2 style="margin-top:0;">📊 Sync Overview</h2>
            <div class="stat-grid">
                <div class="stat-card success">
                    <div class="stat-label">In Your Library</div>
                    <div class="stat-number">{in_library}</div>
                    <div class="stat-pct">{in_library_pct:.1f}%</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Pending Download</div>
                    <div class="stat-number">{pending}</div>
                    <div class="stat-pct">{pending_pct:.1f}%</div>
                </div>
                <div class="stat-card danger">
                    <div class="stat-label">Blocked</div>
                    <div class="stat-number">{blocked}</div>
                    <div class="stat-pct">{blocked_pct:.1f}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Not Found</div>
                    <div class="stat-number">{not_found}</div>
                </div>
            </div>
        </div>
        
        <!-- Per-List Breakdown -->
        <div class="list-section">
            <h2>📋 List Breakdown ({len(list_breakdown)} lists)</h2>
            <p style="opacity: 0.7; margin-bottom: 20px;">Sorted by coverage (lowest first)</p>
"""
    
    # Add each list
    for lst in list_breakdown:
        missing_items_html = ""
        if lst['missing'] > 0:
            missing_parts = []
            if lst['pending'] > 0:
                missing_parts.append(f"<span class='missing-item'>🔄 {lst['pending']} pending</span>")
            if lst['blocked'] > 0:
                missing_parts.append(f"<span class='missing-item'>⛔ {lst['blocked']} blocked</span>")
            if lst['not_found'] > 0:
                missing_parts.append(f"<span class='missing-item'>❌ {lst['not_found']} not found</span>")
            if lst['errors'] > 0:
                missing_parts.append(f"<span class='missing-item'>❗ {lst['errors']} errors</span>")
            missing_items_html = f"""
            <div class="missing-breakdown">
                <strong>Missing:</strong> {' '.join(missing_parts)}
            </div>
"""
        
        html += f"""
            <div class="list-item">
                <div class="list-header">
                    <div class="list-name">📋 {lst['name']}</div>
                    <div class="list-stats">{lst['in_library']}/{lst['total']} in library</div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {lst['coverage_pct']:.1f}%">
                        {lst['coverage_pct']:.1f}%
                    </div>
                </div>
                {missing_items_html}
            </div>
"""
    
    html += """
        </div>
        
        <!-- Footer -->
        <div class="footer">
            List-Sync | Next sync in 6 hours
        </div>
    </div>
</body>
</html>
"""
    
    return html


def send_sync_report(sync_results, synced_lists):
    """
    Generate and send sync report
    
    Args:
        sync_results: SyncResults object
        synced_lists: List of synced list info
    """
    logger.info("send_sync_report() called")
    
    # Check if email reports are enabled
    enabled = os.getenv('EMAIL_REPORT_ENABLED', 'false').lower() == 'true'
    logger.info(f"EMAIL_REPORT_ENABLED: {enabled}")
    
    if not enabled:
        logger.info("Email reports disabled (EMAIL_REPORT_ENABLED=false)")
        return
    
    try:
        logger.info("Generating HTML report...")
        # Generate HTML
        html = generate_html_report(sync_results, synced_lists)
        logger.info(f"HTML generated: {len(html)} bytes")
        
        # Send email
        subject = f"List-Sync Report - {datetime.now().strftime('%Y-%m-%d')}"
        logger.info(f"Sending email: {subject}")
        
        from .email_sender import send_email
        result = send_email(subject, html, html=True)
        
        if result:
            logger.info(f"✅ Sync report sent/saved: {result}")
        else:
            logger.warning("Email report returned None (MAIL_TO not configured?)")
        
    except Exception as e:
        logger.error(f"Failed to generate/send sync report: {e}", exc_info=True)

