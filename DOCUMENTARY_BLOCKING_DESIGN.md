# 🎬 Block All Documentaries - Design

**Feature:** Automatically block all documentaries from being requested

---

## 🎯 Approach

### Option A: Genre-Based Filtering (Recommended)

Add genre filtering to the blocklist check:

```python
# In list_sync/blocklist.py

def is_documentary(tmdb_id: int, media_type: str) -> bool:
    """Check if item is a documentary via TMDB API"""
    try:
        import requests
        tmdb_key = os.getenv('TMDB_KEY')
        if not tmdb_key:
            return False
        
        url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}"
        params = {'api_key': tmdb_key}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            genres = data.get('genres', [])
            # Documentary genre ID: 99
            return any(g.get('id') == 99 for g in genres)
        
        return False
    except:
        return False

def is_blocked(tmdb_id: int, media_type: str) -> bool:
    """Check if item is blocked (existing logic + documentary check)"""
    # Existing blocklist check
    if tmdb_id in blocklist:
        return True
    
    # NEW: Block documentaries if enabled
    if os.getenv('BLOCK_DOCUMENTARIES', 'false').lower() == 'true':
        if is_documentary(tmdb_id, media_type):
            logger.info(f"⛔ Blocking documentary (TMDB: {tmdb_id})")
            return True
    
    return False
```

### Environment Variable

```bash
BLOCK_DOCUMENTARIES=true  # Block all documentaries
```

### Pros/Cons

**Pros:**
- ✅ Automatic - no manual list management
- ✅ Works for all lists
- ✅ Easy to toggle on/off

**Cons:**
- ⚠️ Requires TMDB API calls (slight performance impact)
- ⚠️ Blocks ALL documentaries (might want some)

---

## 🚀 Implementation

**Time:** ~1 hour  
**Complexity:** Low  
**Files:** `blocklist.py`, docker-compose.yml

**Ready to implement when you want it!**

