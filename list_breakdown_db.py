#!/usr/bin/env python3
"""
List Breakdown Report (Database Version)
-----------------------------------------
Queries database directly to create breakdown by list
"""

import sqlite3
from collections import defaultdict

DB_PATH = "/data/list_sync.db"

def create_report():
    """Create breakdown report from database"""
    print("=" * 80)
    print("LIST BREAKDOWN REPORT")
    print("=" * 80)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all lists
    cursor.execute("SELECT list_type, list_id, item_count FROM lists ORDER BY list_type, list_id")
    lists = cursor.fetchall()
    
    print(f"Total lists configured: {len(lists)}")
    print()
    
    grand_totals = defaultdict(int)
    
    for list_type, list_id, item_count in lists:
        # Get items for this list from junction table
        cursor.execute("""
            SELECT si.status, COUNT(*) as count
            FROM synced_items si
            INNER JOIN item_lists il ON si.id = il.item_id
            WHERE il.list_type = ? AND il.list_id = ?
            GROUP BY si.status
        """, (list_type, list_id))
        
        status_counts = dict(cursor.fetchall())
        total = sum(status_counts.values())
        
        # Calculate in Plex vs missing
        in_plex = status_counts.get("already_available", 0) + status_counts.get("skipped", 0)
        missing = total - in_plex
        
        # Display name (extract from URL or use as-is)
        if "external/" in list_id:
            display_name = list_id.split("/")[-1]
        else:
            display_name = list_id[-30:] if len(list_id) > 30 else list_id
        
        # Print list summary
        print(f"📋 {list_type.upper()}: {display_name}")
        print(f"   Total: {total} movies")
        print(f"   ✅ In Plex: {in_plex} ({in_plex/total*100:.1f}%)" if total > 0 else "   ✅ In Plex: 0")
        print(f"   ❌ Missing: {missing} ({missing/total*100:.1f}%)" if total > 0 else "   ❌ Missing: 0")
        
        if missing > 0:
            print(f"   Missing breakdown:")
            if status_counts.get("already_requested", 0) > 0:
                print(f"      🔄 Requested (pending download): {status_counts['already_requested']}")
            if status_counts.get("requested", 0) > 0:
                print(f"      ✨ Newly requested this sync: {status_counts['requested']}")
            if status_counts.get("blocked", 0) > 0:
                print(f"      ⛔ Blocked by blocklist: {status_counts['blocked']}")
            if status_counts.get("not_found", 0) > 0:
                print(f"      ❌ Not found (couldn't match): {status_counts['not_found']}")
            if status_counts.get("error", 0) > 0:
                print(f"      ❗ Processing error: {status_counts['error']}")
            if status_counts.get("request_failed", 0) > 0:
                print(f"      ❌ Request failed: {status_counts['request_failed']}")
        
        print()
        
        # Add to grand totals
        for status, count in status_counts.items():
            grand_totals[status] += count
    
    # Print grand totals
    print("=" * 80)
    print("GRAND TOTALS (All Lists Combined)")
    print("=" * 80)
    print()
    
    total_items = sum(grand_totals.values())
    total_in_plex = grand_totals.get("already_available", 0) + grand_totals.get("skipped", 0)
    total_missing = total_items - total_in_plex
    
    print(f"Total items: {total_items}")
    print(f"✅ In Plex: {total_in_plex} ({total_in_plex/total_items*100:.1f}%)")
    print(f"❌ Missing: {total_missing} ({total_missing/total_items*100:.1f}%)")
    print()
    
    if total_missing > 0:
        print("Why missing:")
        if grand_totals.get("already_requested", 0) > 0:
            pct = grand_totals['already_requested']/total_missing*100
            print(f"   🔄 Requested (pending): {grand_totals['already_requested']} ({pct:.1f}%)")
        if grand_totals.get("requested", 0) > 0:
            pct = grand_totals['requested']/total_missing*100
            print(f"   ✨ Newly requested: {grand_totals['requested']} ({pct:.1f}%)")
        if grand_totals.get("blocked", 0) > 0:
            pct = grand_totals['blocked']/total_missing*100
            print(f"   ⛔ Blocked: {grand_totals['blocked']} ({pct:.1f}%)")
        if grand_totals.get("not_found", 0) > 0:
            pct = grand_totals['not_found']/total_missing*100
            print(f"   ❌ Not found: {grand_totals['not_found']} ({pct:.1f}%)")
        if grand_totals.get("error", 0) > 0:
            pct = grand_totals['error']/total_missing*100
            print(f"   ❗ Errors: {grand_totals['error']} ({pct:.1f}%)")
    
    print()
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    create_report()

