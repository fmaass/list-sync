"""
Report Generator for List-Sync
Generates HTML email reports with per-list breakdown
"""

import logging
import os
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

from ..database import get_list_items

logger = logging.getLogger(__name__)


def generate_html_report(sync_results, synced_lists, max_items_per_category: int = 5) -> str:
    """
    Generate HTML email report
    
    Args:
        sync_results: SyncResults object
        synced_lists: List of synced list info
        max_items_per_category: Maximum items to show per category (default: 5 for email, use 999 for PDF)
        
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
            
            # Calculate statistics with detailed item tracking
            stats = {
                'in_library': 0,
                'pending': 0,
                'blocked': 0,
                'not_found': 0,
                'errors': 0
            }
            
            # Track detailed missing items
            missing_items_details = {
                'pending': [],
                'blocked': [],
                'not_found': [],
                'errors': [],
                'request_failed': [],  # Separate from errors
                'skipped': []
            }
            
            for item in items:
                status = item.get('status', 'unknown')
                title = item.get('title', 'Unknown')
                year = item.get('year')
                
                if status in ['already_available', 'skipped']:
                    stats['in_library'] += 1
                    
                elif status in ['already_requested', 'requested']:
                    stats['pending'] += 1
                    missing_items_details['pending'].append({
                        'title': title,
                        'year': year,
                        'tmdb_id': item.get('tmdb_id'),
                        'status': status
                    })
                    
                elif status == 'blocked':
                    stats['blocked'] += 1
                    missing_items_details['blocked'].append({
                        'title': title,
                        'year': year,
                        'tmdb_id': item.get('tmdb_id')
                    })
                    
                elif status == 'not_found':
                    stats['not_found'] += 1
                    missing_items_details['not_found'].append({
                        'title': title,
                        'year': year
                    })
                    
                elif status == 'request_failed':
                    stats['errors'] += 1
                    missing_items_details['request_failed'].append({
                        'title': title,
                        'year': year,
                        'error_type': 'request_failed'
                    })
                    
                elif status == 'error':
                    stats['errors'] += 1
                    missing_items_details['errors'].append({
                        'title': title,
                        'year': year,
                        'error_type': 'error'
                    })
            
            total = len(items)
            
            # Format list name - extract meaningful parts from URL
            if 'mdblist.com/lists/' in list_id:
                # Extract username and list ID from MDBList URL
                # https://mdblist.com/lists/moviemarder/external/66765 -> "moviemarder/66765"
                parts = list_id.split('/')
                if 'external' in parts:
                    idx = parts.index('external')
                    username = parts[idx - 1] if idx > 0 else 'unknown'
                    list_num = parts[-1] if len(parts) > idx else 'unknown'
                    display_name = f"{username}/{list_num}"
                elif len(parts) >= 2:
                    # Format: username/listname
                    display_name = '/'.join(parts[-2:])
                else:
                    display_name = parts[-1] if parts else list_id[-40:]
            elif 'external/' in list_id:
                display_name = f"List {list_id.split('/')[-1]}"
            else:
                display_name = list_id[-40:] if len(list_id) > 40 else list_id
            
            # If list has no items yet, show it but indicate it hasn't been synced
            if total == 0:
                logger.debug(f"List {list_type}:{list_id} has no items yet - showing as not synced")
                list_breakdown.append({
                    'name': display_name,
                    'total': 0,
                    'in_library': 0,
                    'missing': 0,
                    'coverage_pct': 0,
                    'pending': 0,
                    'blocked': 0,
                    'not_found': 0,
                    'errors': 0,
                    'not_synced': True  # Flag to show different display
                })
                continue
            
            missing = total - stats['in_library']
            coverage_pct = (stats['in_library'] / total * 100) if total > 0 else 0
            
            list_breakdown.append({
                'name': display_name,
                'total': total,
                'in_library': stats['in_library'],
                'missing': missing,
                'coverage_pct': coverage_pct,
                'pending': stats['pending'],
                'blocked': stats['blocked'],
                'not_found': stats['not_found'],
                'errors': stats['errors'],
                'not_synced': False,
                'missing_details': missing_items_details  # NEW: Full item details
            })
            
        except Exception as e:
            logger.warning(f"Failed to get stats for list {list_type}:{list_id}: {e}")
    
    # Sort by coverage (worst first), but put unsynced lists at the end
    list_breakdown.sort(key=lambda x: (x.get('not_synced', False), x['coverage_pct']))
    
    # Generate HTML with specified max_items limit
    html = _generate_html(sync_results, list_breakdown, max_items_per_category)
    return html


def generate_full_html_report(sync_results, synced_lists) -> str:
    """
    Generate FULL HTML report with ALL missing items (for PDF attachment).
    Same as generate_html_report but shows ALL items, not just 5.
    
    Args:
        sync_results: SyncResults object
        synced_lists: List of synced list info
        
    Returns:
        str: Complete HTML with all items
    """
    # Generate report with no item limit (show all items)
    return generate_html_report(sync_results, synced_lists, max_items_per_category=999)


def generate_pdf_report(sync_results, synced_lists) -> bytes:
    """
    Generate PDF report with complete missing items breakdown.
    
    Args:
        sync_results: SyncResults object
        synced_lists: List of synced list info
        
    Returns:
        bytes: PDF file content
    """
    try:
        # Import weasyprint
        from weasyprint import HTML, CSS
        from io import BytesIO
        
        # Generate full HTML (will be modified to show ALL items)
        html_content = generate_full_html_report(sync_results, synced_lists)
        
        # Convert HTML to PDF
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_bytes = pdf_buffer.getvalue()
        
        logger.info(f"Generated PDF report: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except ImportError:
        logger.warning("weasyprint not installed - cannot generate PDF")
        return None
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}", exc_info=True)
        return None


def _generate_missing_items_html(missing_details: Dict, max_items: int = 5) -> str:
    """
    Generate HTML for missing items breakdown with movie titles.
    
    Args:
        missing_details: Dictionary with categorized missing items
        max_items: Maximum items to show per category (default: 5)
        
    Returns:
        HTML string with formatted missing items
    """
    if not missing_details:
        return ""
    
    html = '<div class="missing-breakdown-detailed">'
    html += '<div class="missing-header">Missing Items:</div>'
    
    # Pending items
    pending_items = missing_details.get('pending', [])
    if len(pending_items) > 0:
        html += '<div class="missing-category">'
        html += f'<div class="category-title">🔄 Pending Download ({len(pending_items)} movies)</div>'
        html += '<ul class="movie-list">'
        
        for item in pending_items[:max_items]:
            year_str = f" ({item['year']})" if item.get('year') else ""
            html += f"<li>{item['title']}{year_str}</li>"
        
        if len(pending_items) > max_items:
            remaining = len(pending_items) - max_items
            html += f'<li class="more-items">... and {remaining} more pending</li>'
        
        html += '</ul></div>'
    
    # Blocked items
    blocked_items = missing_details.get('blocked', [])
    if len(blocked_items) > 0:
        html += '<div class="missing-category">'
        html += f'<div class="category-title">⛔ Blocked by Radarr Exclusions ({len(blocked_items)} movies)</div>'
        html += '<ul class="movie-list">'
        
        for item in blocked_items[:max_items]:
            year_str = f" ({item['year']})" if item.get('year') else ""
            html += f"<li>{item['title']}{year_str}</li>"
        
        if len(blocked_items) > max_items:
            remaining = len(blocked_items) - max_items
            html += f'<li class="more-items">... and {remaining} more blocked</li>'
        
        html += '</ul></div>'
    
    # Not found items
    not_found_items = missing_details.get('not_found', [])
    if len(not_found_items) > 0:
        html += '<div class="missing-category">'
        html += f'<div class="category-title">❌ Not Found in Overseerr ({len(not_found_items)} movies)</div>'
        html += '<ul class="movie-list">'
        
        for item in not_found_items[:max_items]:
            year_str = f" ({item['year']})" if item.get('year') else ""
            html += f"<li>{item['title']}{year_str}</li>"
        
        if len(not_found_items) > max_items:
            remaining = len(not_found_items) - max_items
            html += f'<li class="more-items">... and {remaining} more not found</li>'
        
        html += '</ul></div>'
    
    # Request failed items (separate from errors)
    request_failed_items = missing_details.get('request_failed', [])
    if len(request_failed_items) > 0:
        html += '<div class="missing-category">'
        html += f'<div class="category-title">⚠️ Request Failed ({len(request_failed_items)} movies)</div>'
        html += '<ul class="movie-list">'
        
        for item in request_failed_items[:max_items]:
            year_str = f" ({item['year']})" if item.get('year') else ""
            html += f"<li>{item['title']}{year_str}</li>"
        
        if len(request_failed_items) > max_items:
            remaining = len(request_failed_items) - max_items
            html += f'<li class="more-items">... and {remaining} more failed</li>'
        
        html += '</ul></div>'
    
    # Processing error items (actual errors, not request failures)
    error_items = missing_details.get('errors', [])
    if len(error_items) > 0:
        html += '<div class="missing-category">'
        html += f'<div class="category-title">❗ Processing Errors ({len(error_items)} movies)</div>'
        html += '<ul class="movie-list">'
        
        for item in error_items[:max_items]:
            year_str = f" ({item['year']})" if item.get('year') else ""
            error_type = item.get('error_type', 'error')
            html += f"<li>{item['title']}{year_str} <span style='opacity:0.6'>({error_type})</span></li>"
        
        if len(error_items) > max_items:
            remaining = len(error_items) - max_items
            html += f'<li class="more-items">... and {remaining} more errors</li>'
        
        html += '</ul></div>'
    
    html += '</div>'
    return html


def _generate_html(sync_results, list_breakdown: List[Dict], max_items_per_category: int = 5) -> str:
    """
    Generate HTML content
    
    Args:
        sync_results: Sync results object
        list_breakdown: List of list statistics with missing item details
        max_items_per_category: Maximum items to show per category
    """
    
    # Calculate totals from all possible status keys
    total_items = sync_results.total_items
    in_library = sync_results.results.get('already_available', 0) + sync_results.results.get('skipped', 0)
    pending = sync_results.results.get('already_requested', 0) + sync_results.results.get('requested', 0)
    blocked = sync_results.results.get('blocked', 0)
    not_found = sync_results.results.get('not_found', 0)
    # Separate request_failed from other errors
    request_failed = sync_results.results.get('request_failed', 0)
    errors = sync_results.results.get('error', 0)
    
    in_library_pct = (in_library / total_items * 100) if total_items > 0 else 0
    pending_pct = (pending / total_items * 100) if total_items > 0 else 0
    blocked_pct = (blocked / total_items * 100) if total_items > 0 else 0
    request_failed_pct = (request_failed / total_items * 100) if total_items > 0 else 0
    
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
        .missing-breakdown-detailed {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #333;
        }}
        .missing-header {{
            font-weight: 600;
            margin-bottom: 12px;
            font-size: 14px;
            opacity: 0.9;
        }}
        .missing-category {{
            margin: 15px 0;
            background: #252525;
            border-radius: 6px;
            padding: 12px 15px;
        }}
        .category-title {{
            font-weight: 600;
            font-size: 13px;
            margin-bottom: 8px;
            color: #e0e0e0;
        }}
        .movie-list {{
            list-style: none;
            padding: 0 0 0 10px;
            margin: 0;
        }}
        .movie-list li {{
            padding: 5px 0;
            font-size: 12px;
            opacity: 0.85;
            border-bottom: 1px solid #2a2a2a;
            line-height: 1.4;
        }}
        .movie-list li:last-child {{
            border-bottom: none;
        }}
        .movie-list li:before {{
            content: "• ";
            color: #667eea;
            font-weight: bold;
            margin-right: 6px;
        }}
        .more-items {{
            opacity: 0.6;
            font-style: italic;
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
                <div class="stat-card danger">
                    <div class="stat-label">Request Failed</div>
                    <div class="stat-number">{request_failed}</div>
                    <div class="stat-pct">{request_failed_pct:.1f}%</div>
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
"""
    
    # Check if we have list data
    if len(list_breakdown) == 0:
        html += """
            <div style="background: #2a2a2a; padding: 30px; border-radius: 8px; text-align: center; opacity: 0.7;">
                <p style="margin: 0;">No per-list data available yet. List breakdown will appear after the first sync completes.</p>
            </div>
"""
    else:
        html += """
            <p style="opacity: 0.7; margin-bottom: 20px;">Sorted by coverage (lowest first)</p>
"""
    
    # Add each list
    for lst in list_breakdown:
        # Handle lists that haven't been synced yet
        if lst.get('not_synced', False):
            html += f"""
            <div class="list-item" style="opacity: 0.6;">
                <div class="list-header">
                    <div class="list-name">📋 {lst['name']}</div>
                    <div class="list-stats" style="opacity: 0.7;">Not synced yet</div>
                </div>
                <div style="padding: 10px 0; opacity: 0.7; font-size: 13px;">
                    ⏳ This list will be populated after the next sync
                </div>
            </div>
"""
            continue
        
        # Normal list with data - generate detailed missing items breakdown
        missing_items_html = ""
        if lst['missing'] > 0 and lst.get('missing_details'):
            # Generate detailed breakdown with movie titles
            missing_items_html = _generate_missing_items_html(lst['missing_details'], max_items=max_items_per_category)
        
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


def _should_send_report() -> bool:
    """
    Check if we should send a report based on schedule.
    Reports are sent once per day at 3am.
    
    Returns:
        bool: True if report should be sent
    """
    from pathlib import Path
    
    # Get report schedule settings
    report_hour = int(os.getenv('EMAIL_REPORT_HOUR', '3'))  # Default: 3am
    
    # Check if we've already sent today
    try:
        from ..utils.logger import DATA_DIR
        last_sent_file = Path(DATA_DIR) / "reports" / ".last_report_sent"
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        if last_sent_file.exists():
            last_sent_date = last_sent_file.read_text().strip()
            if last_sent_date == today:
                logger.debug(f"Report already sent today ({today})")
                return False
        
        # Check if current hour is the scheduled hour (or within 1 hour after)
        current_hour = datetime.now().hour
        if current_hour != report_hour and current_hour != (report_hour + 1) % 24:
            logger.debug(f"Not report time. Current hour: {current_hour}, scheduled: {report_hour}")
            return False
        
        # Mark as sent for today
        last_sent_file.parent.mkdir(parents=True, exist_ok=True)
        last_sent_file.write_text(today)
        
        return True
        
    except Exception as e:
        logger.warning(f"Error checking report schedule: {e}")
        # If there's an error, send the report anyway
        return True


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
    
    # Check if we should send based on schedule
    if not _should_send_report():
        logger.info("Skipping report - not scheduled time or already sent today")
        return
    
    try:
        logger.info("Generating HTML report...")
        # Generate HTML (with 5 items per category for email body)
        html = generate_html_report(sync_results, synced_lists)
        logger.info(f"HTML generated: {len(html)} bytes")
        
        # Generate PDF attachment (with ALL items for complete details)
        logger.info("Generating PDF attachment...")
        pdf_data = generate_pdf_report(sync_results, synced_lists)
        if pdf_data:
            logger.info(f"PDF generated: {len(pdf_data)} bytes")
        else:
            logger.warning("PDF generation failed or weasyprint not available")
        
        # Send email with PDF attachment
        subject = f"List-Sync Report - {datetime.now().strftime('%Y-%m-%d')}"
        logger.info(f"Sending email: {subject}")
        
        from .email_sender import send_email
        pdf_filename = f"ListSync_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
        result = send_email(subject, html, html=True, pdf_attachment=pdf_data, pdf_filename=pdf_filename)
        
        if result:
            logger.info(f"✅ Sync report sent/saved: {result}")
        else:
            logger.warning("Email report returned None (MAIL_TO not configured?)")
        
    except Exception as e:
        logger.error(f"Failed to generate/send sync report: {e}", exc_info=True)

