# 📊 Enhanced Email Reports - Missing Items Breakdown Design

**Feature:** Show actual movie titles in missing items breakdown  
**Current State:** Reports show counts only (e.g., "8 pending, 2 blocked")  
**Desired State:** Show actual movie titles grouped by reason

---

## 🎯 Goal

Transform this:
```
📋 List 66765
  45/57 in library (79%)
  Missing: 8 pending, 2 blocked, 2 not found
```

Into this:
```
📋 List 66765
  45/57 in library (79%)
  
  🔄 Pending Download (8 movies):
    • The Matrix Resurrections (2021)
    • Dune: Part Two (2024)
    • Blade Runner 2099 (2025)
    • [... 5 more ...]
  
  ⛔ Blocked by Radarr Exclusions (2 movies):
    • Bad Movie Title (2020)
    • Another Unwanted Film (2019)
  
  ❌ Not Found in Overseerr (2 movies):
    • Obscure Foreign Film (2023)
    • Limited Release Documentary (2022)
```

---

## 📊 Status Categories Analysis

### Complete Status Taxonomy

From codebase analysis, items can have these statuses:

| Status | Icon | Meaning | Category | Action Needed |
|--------|------|---------|----------|---------------|
| `already_available` | ☑️ | In Plex library | ✅ Success | None |
| `already_requested` | 📌 | In Overseerr, pending download | 🔄 Pending | Wait for download |
| `requested` | ✅ | Just requested now | 🔄 Pending | Wait for download |
| `blocked` | ⛔ | On Radarr blocklist | ⛔ Blocked | Remove from blocklist if desired |
| `not_found` | ❓ | Not found in TMDB/Overseerr | ❌ Not Found | Check title/year |
| `error` | ❌ | Processing error | ❗ Error | Review logs |
| `request_failed` | ❌ | Request to Overseerr failed | ❗ Error | Check Overseerr |
| `skipped` | ⏭️ | Skipped by user/config | ⏭️ Skipped | Configuration |

### Grouping for Report

**Group 1: Pending (Waiting for Download)**
- `already_requested` - Already in Overseerr queue
- `requested` - Just added to Overseerr queue
- Overseerr status: 1 (requested), 2 (pending), 3 (processing)

**Group 2: Blocked (Intentionally Excluded)**
- `blocked` - On Radarr exclusion list
- User action: Remove from blocklist if you want it

**Group 3: Not Found (Couldn't Match)**
- `not_found` - Not found in TMDB/Overseerr databases
- User action: Check if title/year is correct

**Group 4: Errors (Failed Processing)**
- `error` - Processing error during sync
- `request_failed` - Request to Overseerr API failed
- User action: Review logs, check Overseerr connection

**Group 5: Skipped (Intentionally Not Requested)**
- `skipped` - User chose to skip
- User action: None (intentional)

---

## 🎨 Visual Design

### Option A: Expandable Sections (Recommended)

```html
📋 List 66765 - Top Rated Action Movies
  45/57 in library (79%)
  ████████░░ 79%
  
  ▼ Missing Items (12 movies) - Click to expand
    
    🔄 Pending Download (8 movies)
    ├─ The Matrix Resurrections (2021)
    ├─ Dune: Part Two (2024)
    ├─ Blade Runner 2099 (2025)
    ├─ The Northman (2022)
    ├─ Mad Max: Fury Road Prequel (2024)
    ├─ The Batman Part II (2025)
    ├─ John Wick: Chapter 5 (2025)
    └─ Avatar 3 (2025)
    
    ⛔ Blocked (2 movies)
    ├─ Bad Movie A (2020)
    └─ Bad Movie B (2019)
    
    ❌ Not Found (2 movies)
    ├─ Obscure Film (2023)
    └─ Foreign Title (2022)
```

### Option B: Collapsed by Default (Better for Email)

```html
📋 List 66765
  45/57 in library (79%)
  Missing: 8 pending, 2 blocked, 2 not found
  
  [Show Details ▼]  <!-- Clickable in HTML email -->
  
  <!-- Expands to: -->
  🔄 Pending (8):
    • The Matrix Resurrections (2021)
    • Dune: Part Two (2024)
    ... (6 more)
```

### Option C: Always Expanded with Limits (Best for Insight)

Show all categories with item limits:

```html
📋 List 66765 - Top Rated Action Movies
  45/57 in library (79%)
  
  Missing Items (12):
  
  🔄 Pending Download (8 movies):
    • The Matrix Resurrections (2021)
    • Dune: Part Two (2024)  
    • Blade Runner 2099 (2025)
    • The Northman (2022)
    • Mad Max: Fury Road Prequel (2024)
    ... and 3 more
  
  ⛔ Blocked by Exclusions (2 movies):
    • Bad Movie A (2020)
    • Bad Movie B (2019)
  
  ❌ Not Found (2 movies):
    • Obscure Film (2023)
    • Foreign Title (2022)
```

---

## 💻 Implementation Design

### Data Structure Changes

**Current:**
```python
list_breakdown.append({
    'name': display_name,
    'total': total,
    'in_library': stats['in_library'],
    'pending': stats['pending'],  # Just a count
    'blocked': stats['blocked'],  # Just a count
    'not_found': stats['not_found']  # Just a count
})
```

**Enhanced:**
```python
list_breakdown.append({
    'name': display_name,
    'total': total,
    'in_library': stats['in_library'],
    'missing_details': {  # NEW: Detailed breakdown
        'pending': {
            'count': 8,
            'items': [
                {'title': 'The Matrix Resurrections', 'year': 2021},
                {'title': 'Dune: Part Two', 'year': 2024},
                # ... up to 5 items shown
            ],
            'has_more': True,
            'total': 8
        },
        'blocked': {
            'count': 2,
            'items': [
                {'title': 'Bad Movie A', 'year': 2020},
                {'title': 'Bad Movie B', 'year': 2019}
            ],
            'has_more': False,
            'total': 2
        },
        'not_found': {
            'count': 2,
            'items': [...]
        },
        'errors': {
            'count': 0,
            'items': []
        }
    }
})
```

### Code Changes Required

#### 1. Modify `generate_html_report()` in `report_generator.py`

**Location:** Lines 28-104

**Current Logic:**
```python
for item in items:
    status = item.get('status', 'unknown')
    if status in ['already_available', 'skipped']:
        stats['in_library'] += 1
    elif status == 'already_requested':
        stats['pending'] += 1
    # ... just counting
```

**Enhanced Logic:**
```python
# Initialize detailed tracking
missing_items = {
    'pending': [],
    'blocked': [],
    'not_found': [],
    'errors': [],
    'skipped': []
}

for item in items:
    status = item.get('status', 'unknown')
    
    # Track items in library (no details needed)
    if status in ['already_available']:
        stats['in_library'] += 1
    
    # Track missing items with details
    elif status in ['already_requested', 'requested']:
        stats['pending'] += 1
        missing_items['pending'].append({
            'title': item.get('title', 'Unknown'),
            'year': item.get('year'),
            'tmdb_id': item.get('tmdb_id'),
            'status': status  # Track sub-status
        })
    
    elif status == 'blocked':
        stats['blocked'] += 1
        missing_items['blocked'].append({
            'title': item.get('title', 'Unknown'),
            'year': item.get('year'),
            'tmdb_id': item.get('tmdb_id')
        })
    
    elif status == 'not_found':
        stats['not_found'] += 1
        missing_items['not_found'].append({
            'title': item.get('title', 'Unknown'),
            'year': item.get('year')
        })
    
    elif status in ['error', 'request_failed']:
        stats['errors'] += 1
        missing_items['errors'].append({
            'title': item.get('title', 'Unknown'),
            'year': item.get('year'),
            'error_type': status
        })
    
    elif status == 'skipped':
        stats['skipped'] += 1
        missing_items['skipped'].append({
            'title': item.get('title', 'Unknown'),
            'year': item.get('year')
        })
```

#### 2. Modify HTML Generation in `_generate_html()`

**Location:** Lines 304-366

**Current:**
```python
if lst['missing'] > 0:
    missing_parts = []
    if lst['pending'] > 0:
        missing_parts.append(f"<span>🔄 {lst['pending']} pending</span>")
    # ... just showing counts
```

**Enhanced:**
```python
if lst['missing'] > 0:
    missing_html = _generate_missing_items_html(lst['missing_details'])
```

**New Helper Function:**
```python
def _generate_missing_items_html(missing_details: Dict, max_items_per_category: int = 5) -> str:
    """
    Generate HTML for missing items breakdown.
    
    Args:
        missing_details: Dictionary with categorized missing items
        max_items_per_category: Maximum items to show per category
        
    Returns:
        HTML string with formatted missing items
    """
    html = '<div class="missing-breakdown">'
    html += '<div class="missing-header">Missing Items:</div>'
    
    # Pending items
    if missing_details['pending']['count'] > 0:
        items = missing_details['pending']['items'][:max_items_per_category]
        total = missing_details['pending']['total']
        
        html += f'<div class="missing-category">'
        html += f'<div class="category-title">🔄 Pending Download ({total} movies)</div>'
        html += '<ul class="movie-list">'
        
        for item in items:
            year_str = f" ({item['year']})" if item.get('year') else ""
            html += f'<li>{item["title"]}{year_str}</li>'
        
        if total > max_items_per_category:
            remaining = total - max_items_per_category
            html += f'<li class="more-items">... and {remaining} more</li>'
        
        html += '</ul></div>'
    
    # Blocked items
    if missing_details['blocked']['count'] > 0:
        items = missing_details['blocked']['items'][:max_items_per_category]
        total = missing_details['blocked']['total']
        
        html += f'<div class="missing-category">'
        html += f'<div class="category-title">⛔ Blocked by Radarr Exclusions ({total} movies)</div>'
        html += '<ul class="movie-list">'
        
        for item in items:
            year_str = f" ({item['year']})" if item.get('year') else ""
            html += f'<li>{item["title"]}{year_str}</li>'
        
        if total > max_items_per_category:
            remaining = total - max_items_per_category
            html += f'<li class="more-items">... and {remaining} more</li>'
        
        html += '</ul></div>'
    
    # Not found items
    if missing_details['not_found']['count'] > 0:
        items = missing_details['not_found']['items'][:max_items_per_category]
        total = missing_details['not_found']['total']
        
        html += f'<div class="missing-category">'
        html += f'<div class="category-title">❌ Not Found in Overseerr ({total} movies)</div>'
        html += '<ul class="movie-list">'
        
        for item in items:
            year_str = f" ({item['year']})" if item.get('year') else ""
            html += f'<li>{item["title"]}{year_str}</li>'
        
        if total > max_items_per_category:
            remaining = total - max_items_per_category
            html += f'<li class="more-items">... and {remaining} more</li>'
        
        html += '</ul></div>'
    
    # Errors
    if missing_details['errors']['count'] > 0:
        items = missing_details['errors']['items'][:max_items_per_category]
        total = missing_details['errors']['total']
        
        html += f'<div class="missing-category">'
        html += f'<div class="category-title">❗ Processing Errors ({total} movies)</div>'
        html += '<ul class="movie-list">'
        
        for item in items:
            year_str = f" ({item['year']})" if item.get('year') else ""
            html += f'<li>{item["title"]}{year_str}</li>'
        
        if total > max_items_per_category:
            remaining = total - max_items_per_category
            html += f'<li class="more-items">... and {remaining} more</li>'
        
        html += '</ul></div>'
    
    html += '</div>'
    return html
```

#### 3. Add CSS Styles

**Location:** Lines 118-261 (style section)

```css
.missing-breakdown {
    margin-top: 15px;
    padding-top: 15px;
    border-top: 1px solid #333;
}

.missing-header {
    font-weight: 600;
    margin-bottom: 10px;
    font-size: 14px;
    opacity: 0.9;
}

.missing-category {
    margin: 15px 0;
    background: #252525;
    border-radius: 6px;
    padding: 12px 15px;
}

.category-title {
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 8px;
    color: #e0e0e0;
}

.movie-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.movie-list li {
    padding: 4px 0;
    font-size: 12px;
    opacity: 0.85;
    border-bottom: 1px solid #2a2a2a;
}

.movie-list li:last-child {
    border-bottom: none;
}

.movie-list li:before {
    content: "• ";
    color: #667eea;
    font-weight: bold;
    margin-right: 6px;
}

.more-items {
    opacity: 0.6;
    font-style: italic;
}
```

---

## 📱 Responsive Design

### Desktop View (Full Details)
- Show up to 10 items per category
- All categories visible
- Full movie titles

### Mobile View (Compact)
- Show up to 5 items per category
- Collapsible categories (optional)
- Truncate long titles

---

## 🎛️ Configuration Options

### Environment Variables (Optional)

```bash
# Maximum movies to show per category in email reports
EMAIL_REPORT_MAX_ITEMS_PER_CATEGORY=5  # Default: 5

# Show all items or limit to X per category
EMAIL_REPORT_SHOW_ALL_MISSING=false  # Default: false (use limit)
```

### Database Field (Future)
```sql
ALTER TABLE lists 
ADD COLUMN report_detail_level TEXT DEFAULT 'standard'
-- Options: 'summary' (counts only), 'standard' (up to 5), 'detailed' (all)
```

---

## 📊 Example Output Scenarios

### Scenario 1: Small List (All Items Fit)
```
📋 List 66768 - Horror Classics
  14/16 in library (88%)
  
  🔄 Pending (2 movies):
    • The Exorcist III (1990)
    • Hellraiser VI (2002)
```

### Scenario 2: Large List (Items Truncated)
```
📋 List 66774 - All-Time Best
  250/307 in library (81%)
  
  🔄 Pending (45 movies):
    • The Shawshank Redemption (1994)
    • The Godfather Part III (1990)
    • Pulp Fiction (1994)
    • Fight Club (1999)
    • Inception (2010)
    ... and 40 more
  
  ❌ Not Found (12 movies):
    • Obscure Foreign Film (1987)
    • Lost Documentary (2003)
    • Limited Release (2015)
    • Festival Exclusive (2019)
    • Foreign Title (Original) (2010)
    ... and 7 more
```

### Scenario 3: Mixed Status
```
📋 List 66767 - New Releases
  120/184 in library (65%)
  
  🔄 Pending (50 movies):
    • Dune: Part Three (2026)
    • Avatar: Fire and Ash (2025)
    • The Batman Part II (2026)
    • Blade Runner 2099 (2025)
    • Star Wars: New Dawn (2026)
    ... and 45 more
  
  ⛔ Blocked (10 movies):
    • Bad Sequel 7 (2024)
    • Terrible Reboot (2025)
    • Cash Grab Movie (2024)
    • Poorly Rated Film (2023)
    • Another Bad One (2024)
    ... and 5 more
  
  ❌ Not Found (4 movies):
    • Foreign Language Film (2024)
    • Festival Circuit Movie (2024)
    • Limited Release Doc (2023)
    • Indie Production (2024)
```

---

## 🚀 Implementation Complexity

### Code Changes Required

| File | Function | Changes | LOC | Complexity |
|------|----------|---------|-----|------------|
| `report_generator.py` | `generate_html_report()` | Collect item details | +30 | Low |
| `report_generator.py` | `_generate_html()` | Use new data structure | +50 | Low |
| `report_generator.py` | `_generate_missing_items_html()` | NEW function | +80 | Medium |
| Total | | | ~160 | Medium |

### Performance Impact

- **Memory:** +5-10KB per list (storing movie titles)
- **Database:** No extra queries (data already fetched)
- **Email Size:** +10-20KB per email (more content)
- **Generation Time:** +50-100ms (formatting)

**Impact:** Negligible ✅

---

## 🎯 Recommendation

### Recommended Approach: **Option C** (Always Expanded with Limits)

**Why:**
1. **Actionable:** Users can see exactly what's missing
2. **Manageable:** 5-item limit keeps emails readable
3. **Insightful:** Reveals patterns (e.g., many blocked items)
4. **Scannable:** Easy to skim for specific titles

**Configuration:**
```python
MAX_ITEMS_PER_CATEGORY = 5  # Show up to 5 movies per category
SHOW_YEAR = True  # Include year for context
SHOW_MORE_LINK = False  # Future: link to full list in web UI
```

### Visual Mock-up

```
╔══════════════════════════════════════════════════════════╗
║  📋 List 66765 - Top Rated Action Movies               ║
║  45/57 in library (79%)                                 ║
║  ▓▓▓▓▓▓▓▓░░ 79%                                        ║
╠══════════════════════════════════════════════════════════╣
║  Missing Items (12):                                    ║
║                                                          ║
║  🔄 Pending Download (8 movies)                        ║
║    • The Matrix Resurrections (2021)                    ║
║    • Dune: Part Two (2024)                             ║
║    • Blade Runner 2099 (2025)                          ║
║    • The Northman (2022)                               ║
║    • Mad Max Prequel (2024)                            ║
║    ... and 3 more pending                              ║
║                                                          ║
║  ⛔ Blocked by Radarr (2 movies)                       ║
║    • Bad Movie A (2020)                                 ║
║    • Bad Movie B (2019)                                 ║
║                                                          ║
║  ❌ Not Found (2 movies)                               ║
║    • Obscure Film (2023)                               ║
║    • Foreign Title (2022)                               ║
╚══════════════════════════════════════════════════════════╝
```

---

## 📋 Implementation Checklist

### Phase 1: Data Collection (30 min)
- [ ] Modify stats collection loop to track item details
- [ ] Store up to N items per category
- [ ] Include title, year, and relevant IDs

### Phase 2: HTML Generation (1 hour)
- [ ] Create `_generate_missing_items_html()` helper
- [ ] Add CSS styles for movie lists
- [ ] Handle truncation ("... and X more")

### Phase 3: Configuration (30 min)
- [ ] Add `MAX_ITEMS_PER_CATEGORY` constant
- [ ] Add environment variable support (optional)
- [ ] Add configuration to UI (future)

### Phase 4: Testing (30 min)
- [ ] Test with small lists (all items shown)
- [ ] Test with large lists (truncation)
- [ ] Test empty categories
- [ ] Test HTML rendering in email client

### Total Time: ~2.5 hours

---

## 🎨 Additional Enhancements (Optional)

### 1. Priority Indicators
Show which missing items are highest priority:
```
🔄 Pending (8 movies):
  ⭐ The Matrix Resurrections (2021) - IMDb: 9.2
  ⭐ Dune: Part Two (2024) - IMDb: 8.9
  • Regular Movie (2023) - IMDb: 7.1
```

### 2. Links to Overseerr
```
🔄 Pending (8 movies):
  • The Matrix Resurrections (2021) [View in Overseerr →]
```

### 3. Estimated Availability
```
🔄 Pending (8 movies):
  • The Matrix Resurrections (2021) - In Radarr queue
  • Dune: Part Two (2024) - Searching for download
```

### 4. Categorize by List
Show which list each item came from (for movies in multiple lists):
```
❌ Not Found (3 movies):
  • Obscure Film (2023) - from List 66765, 66767
  • Foreign Title (2022) - from List 66768
```

---

## 🎯 Summary & Next Steps

### Current State
```
Missing: 8 pending, 2 blocked, 2 not found  ← Just counts
```

### Proposed State
```
Missing Items (12):

🔄 Pending Download (8 movies):
  • The Matrix Resurrections (2021)
  • Dune: Part Two (2024)
  • [... up to 5 shown ...]
  ... and 3 more

⛔ Blocked (2 movies):
  • Bad Movie A (2020)
  • Bad Movie B (2019)

❌ Not Found (2 movies):
  • Obscure Film (2023)
  • Foreign Title (2022)
```

### Implementation Approach
1. **Low-hanging fruit:** Modify data collection to track items
2. **Visual design:** Create helper function for HTML generation
3. **Polish:** Add CSS for clean presentation
4. **Test:** Verify with your actual lists

### Questions for You

1. **How many items per category?** (5? 10? All?)
2. **Include IMDb ratings?** (if available in database)
3. **Include links to Overseerr?** (for quick action)
4. **Collapsible sections?** (for very long lists)
5. **Separate email for large reports?** (if > 100 missing items)

---

**Ready to implement when you approve the design!** 🚀

Let me know if this matches your vision or if you'd like adjustments!

