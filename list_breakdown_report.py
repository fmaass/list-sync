#!/usr/bin/env python3
"""
List Breakdown Report
---------------------
Creates a summary showing for each subscribed list:
- How many movies are in Plex
- How many are missing (grouped by reason)
"""

import requests
import json
from collections import defaultdict

API_URL = "http://localhost:4222"

def get_lists():
    """Get all configured lists"""
    resp = requests.get(f"{API_URL}/api/lists")
    return resp.json().get("lists", [])

def get_items_for_list(list_type, list_id):
    """Get all items for a specific list"""
    resp = requests.get(f"{API_URL}/api/items/by-list/{list_type}/{list_id}")
    return resp.json().get("items", [])

def create_report():
    """Create breakdown report"""
    print("=" * 80)
    print("LIST BREAKDOWN REPORT")
    print("=" * 80)
    print()
    
    lists = get_lists()
    print(f"Total lists configured: {len(lists)}")
    print()
    
    grand_totals = defaultdict(int)
    
    for list_info in lists:
        list_type = list_info["list_type"]
        list_id = list_info["list_id"]
        display_name = list_info.get("display_name", list_id)
        
        # Get items for this list
        try:
            items = get_items_for_list(list_type, list_id)
        except:
            print(f"📋 {list_type.upper()}: {display_name}")
            print(f"   ❌ Could not fetch items")
            print()
            continue
        
        # Count by status
        status_counts = defaultdict(int)
        for item in items:
            status = item.get("status", "unknown")
            status_counts[status] += 1
        
        total = len(items)
        in_plex = status_counts.get("already_available", 0) + status_counts.get("skipped", 0)
        missing = total - in_plex
        
        # Print list summary
        print(f"📋 {list_type.upper()}: {display_name}")
        print(f"   Total: {total} movies")
        print(f"   ✅ In Plex: {in_plex}")
        print(f"   ❌ Missing: {missing}")
        
        if missing > 0:
            print(f"   Missing breakdown:")
            if status_counts.get("already_requested", 0) > 0:
                print(f"      🔄 Requested (pending): {status_counts['already_requested']}")
            if status_counts.get("requested", 0) > 0:
                print(f"      ✨ Newly requested: {status_counts['requested']}")
            if status_counts.get("blocked", 0) > 0:
                print(f"      ⛔ Blocked (filtered): {status_counts['blocked']}")
            if status_counts.get("not_found", 0) > 0:
                print(f"      ❌ Not found (couldn't match): {status_counts['not_found']}")
            if status_counts.get("error", 0) > 0:
                print(f"      ❗ Error (processing failed): {status_counts['error']}")
        
        print()
        
        # Add to grand totals
        for status, count in status_counts.items():
            grand_totals[status] += count
    
    # Print grand totals
    print("=" * 80)
    print("GRAND TOTALS")
    print("=" * 80)
    print()
    
    total_items = sum(grand_totals.values())
    total_in_plex = grand_totals.get("already_available", 0) + grand_totals.get("skipped", 0)
    total_missing = total_items - total_in_plex
    
    print(f"Total items across all lists: {total_items}")
    print(f"✅ In Plex: {total_in_plex} ({total_in_plex/total_items*100:.1f}%)")
    print(f"❌ Missing: {total_missing} ({total_missing/total_items*100:.1f}%)")
    print()
    
    print("Missing breakdown:")
    if grand_totals.get("already_requested", 0) > 0:
        print(f"   🔄 Requested (pending): {grand_totals['already_requested']}")
    if grand_totals.get("requested", 0) > 0:
        print(f"   ✨ Newly requested: {grand_totals['requested']}")
    if grand_totals.get("blocked", 0) > 0:
        print(f"   ⛔ Blocked (filtered): {grand_totals['blocked']}")
    if grand_totals.get("not_found", 0) > 0:
        print(f"   ❌ Not found: {grand_totals['not_found']}")
    if grand_totals.get("error", 0) > 0:
        print(f"   ❗ Errors: {grand_totals['error']}")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    create_report()

