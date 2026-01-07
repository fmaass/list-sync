# 📋 Per-List Auto-Approval Feature - Software Design Document

**Date:** January 7, 2026  
**Feature:** Configure auto-approval behavior per list  
**Complexity:** Medium  
**Estimated Implementation Time:** 4-6 hours

---

## 🎯 Executive Summary

Enable per-list control over whether requests are auto-approved in Overseerr. Some lists (e.g., curated collections) should auto-approve, while others (e.g., trending/new movies) should require manual approval.

**Key Insight:** Auto-approval in Overseerr is controlled by **user permissions**, not by the API call itself. Different Overseerr users can have different permission levels.

---

## 🔍 Current Architecture Analysis

### How Auto-Approval Works Today

1. **Single User for All Requests:**
   - List-sync currently uses ONE Overseerr user ID for all requests
   - Set via `OVERSEERR_USER_ID` environment variable (default: `"1"` = admin)
   - All requests inherit this user's permissions

2. **Overseerr Permission System:**
   - Each user in Overseerr has permission flags
   - `AUTO_APPROVE` permission = instant approval
   - `REQUEST` permission without auto-approve = manual approval needed
   - API header `X-Api-User: <user_id>` determines the requesting user

3. **Database Schema:**
   ```sql
   CREATE TABLE lists (
       list_type TEXT NOT NULL,
       list_id TEXT NOT NULL UNIQUE,
       list_url TEXT,
       item_count INTEGER DEFAULT 0,
       last_synced TIMESTAMP,
       user_id TEXT DEFAULT "1",  -- Already exists!
       PRIMARY KEY (list_type, list_id)
   )
   ```

4. **Request Flow:**
   ```
   List in DB → fetch_media_from_lists()
             → Items carry source_list info with user_id
             → process_media_item()
             → choose_request_user_id() selects user
             → OverseerrClient.request_media(requester_user_id)
             → HTTP POST with X-Api-User header
             → Overseerr checks user permissions
             → Auto-approve or require manual approval
   ```

### Key Code Locations

| File | Function/Class | Purpose |
|------|----------------|---------|
| `list_sync/database.py` | `save_list_id()` (line 457) | Saves lists with user_id |
| `list_sync/database.py` | `load_list_ids()` (line 529) | Loads lists including user_id |
| `list_sync/main.py` | `choose_request_user_id()` (line 474) | **Already selects per-list user!** |
| `list_sync/main.py` | `process_media_item()` (line 486) | Calls choose_request_user_id() |
| `list_sync/api/overseerr.py` | `request_media()` (line 351) | Makes request with user_id |
| `list_sync/api/overseerr.py` | `_headers_for_user()` (line 31) | Sets X-Api-User header |

---

## 💡 Proposed Solution

### Design Approach: Two Options

#### **Option A: Use Existing `user_id` Field** ⭐ **RECOMMENDED**
- **Pros:** Already implemented! Just needs configuration
- **Cons:** Requires creating users in Overseerr
- **Complexity:** Low (configuration only)

#### **Option B: Add `auto_approve` Boolean Field**
- **Pros:** More explicit, easier to understand
- **Cons:** Requires database migration, additional logic
- **Complexity:** Medium (code changes needed)

**I recommend Option A** because the infrastructure already exists!

---

## 🏗️ Implementation Plan (Option A - Recommended)

### Phase 1: Overseerr User Setup (Manual, 5 minutes)

1. **Create a "Manual Approval" user in Overseerr:**
   - Username: `list-sync-manual` (or any name)
   - Permissions:
     - ✅ REQUEST (can make requests)
     - ❌ AUTO_APPROVE (requires manual approval)
     - ❌ MANAGE_REQUESTS (can't approve own requests)
   - Note the user ID (e.g., `"2"`)

2. **Keep existing admin user for auto-approve:**
   - User ID `"1"` (admin)
   - Has AUTO_APPROVE permission
   - Used for lists that should auto-approve

### Phase 2: Database Schema (Already Done! ✅)

The `lists` table already has a `user_id` field:
```sql
user_id TEXT DEFAULT "1"
```

**No migration needed!** This field already exists and is fully functional.

### Phase 3: List Configuration Options

#### Option 3A: Environment Variable Pattern
```bash
# In .env or docker-compose.yml
MDBLIST_LISTS=https://mdblist.com/lists/user/list1,https://mdblist.com/lists/user/list2
MDBLIST_MANUAL_LISTS=https://mdblist.com/lists/user/trending  # No auto-approve
MANUAL_APPROVAL_USER_ID=2  # User without auto-approve
```

#### Option 3B: Web UI Configuration (Better UX)
Add UI fields when adding/editing lists:
- Checkbox: "Auto-approve requests from this list"
- Or dropdown: "Request as user: [Admin (auto-approve) | Manual Approval User]"

#### Option 3C: Config File Pattern
```yaml
lists:
  - type: mdblist
    url: https://mdblist.com/lists/user/curated
    user_id: "1"  # Auto-approve
    
  - type: mdblist
    url: https://mdblist.com/lists/user/trending
    user_id: "2"  # Manual approval
```

---

## 📝 Implementation Steps (Option A)

### Step 1: Create Manual Approval User in Overseerr
**Time: 5 minutes**

1. Log into Overseerr
2. Go to Settings → Users → Add User
3. Create user with REQUEST permission only (no AUTO_APPROVE)
4. Note the user ID

**Testing:**
```bash
# Test that the user can request but not auto-approve
curl -X POST http://overseerr:5055/api/v1/request \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "X-Api-User: 2" \
  -H "Content-Type: application/json" \
  -d '{"mediaId": 12345, "mediaType": "movie"}'
  
# Check in Overseerr UI - request should be "Pending" not "Approved"
```

### Step 2: Add UI Configuration
**Time: 2-3 hours**

**File:** `listsync-nuxt/components/ListForm.vue` (or similar)

Add fields to list configuration form:

```typescript
// Add to form data
interface ListConfig {
  type: string;
  id: string;
  url: string;
  user_id: string;  // Already exists in DB!
  auto_approve?: boolean;  // Computed from user_id
}

// Add UI elements
<template>
  <div class="form-group">
    <label>Request Approval</label>
    <select v-model="listConfig.user_id">
      <option value="1">Auto-approve (Admin)</option>
      <option value="2">Manual approval required</option>
    </select>
    <p class="help-text">
      Auto-approve: Requests are instantly approved
      Manual approval: Requests need admin approval in Overseerr
    </p>
  </div>
</template>
```

**API Changes:**

File: `api_server.py`
```python
@app.post("/api/lists/add")
async def add_list(request: Request):
    body = await request.json()
    list_type = body.get("list_type")
    list_id = body.get("list_id")
    user_id = body.get("user_id", "1")  # Default to admin
    
    # Save list with user_id
    save_list_id(list_id, list_type, user_id=user_id)
```

### Step 3: Environment Variable Support
**Time: 1 hour**

For users who prefer configuration files over UI:

**File:** `list_sync/config.py`

```python
def load_env_lists_with_users():
    """Load lists from environment with optional user_id configuration"""
    # Parse format: "list_url:user_id,list_url:user_id"
    # Or: "list_url1,list_url2" (defaults to user_id "1")
    
    manual_lists = os.getenv('MDBLIST_MANUAL_LISTS', '').split(',')
    manual_user_id = os.getenv('MANUAL_APPROVAL_USER_ID', '2')
    
    # Process manual lists with manual_user_id
    for list_url in manual_lists:
        if list_url.strip():
            save_list_id(list_url, 'mdblist', user_id=manual_user_id)
```

**Environment Variables:**
```bash
# New optional variables
MANUAL_APPROVAL_USER_ID=2  # User ID for manual approval lists
MDBLIST_MANUAL_LISTS=https://mdblist.com/lists/user/trending,https://mdblist.com/lists/user/new
```

### Step 4: Testing
**Time: 30 minutes**

**Test Cases:**

1. **Test auto-approve list (user_id=1):**
   ```
   - Add list with user_id="1"
   - Trigger sync
   - Check Overseerr: requests should be "Approved"
   ```

2. **Test manual approval list (user_id=2):**
   ```
   - Add list with user_id="2"
   - Trigger sync
   - Check Overseerr: requests should be "Pending"
   ```

3. **Test mixed lists:**
   ```
   - Item appears in both auto-approve and manual lists
   - Should use first list's user_id (see choose_request_user_id())
   ```

4. **Test user validation:**
   ```
   - Try invalid user_id
   - Should fall back to "1" with warning log
   ```

---

## 🔄 Alternative: Option B Implementation (If Preferred)

### Step 1: Database Migration
**Time: 30 minutes**

**File:** `list_sync/database.py`

```python
def migrate_add_auto_approve_field():
    """Add auto_approve field to lists table"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        try:
            # Add column if it doesn't exist
            cursor.execute('''
                ALTER TABLE lists 
                ADD COLUMN auto_approve BOOLEAN DEFAULT 1
            ''')
            logging.info("Added auto_approve column to lists table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                logging.debug("auto_approve column already exists")
            else:
                raise
        
        conn.commit()

# Call in init_database()
```

### Step 2: Modify choose_request_user_id()
**File:** `list_sync/main.py`

```python
def choose_request_user_id(source_lists: List[Dict[str, Any]], default_user_id: str) -> str:
    """
    Choose which Overseerr requester user_id to use for this item.
    
    Logic:
    - If any source list has auto_approve=False, use manual approval user
    - Otherwise, use auto-approve user
    """
    manual_approval_user = os.getenv('MANUAL_APPROVAL_USER_ID', '2')
    
    for source in source_lists:
        auto_approve = source.get('auto_approve', True)
        if not auto_approve:
            logging.info(f"Using manual approval user ({manual_approval_user}) due to list: {source.get('type')}:{source.get('id')}")
            return manual_approval_user
        
        # If list has explicit user_id, use it
        user_id = source.get('user_id')
        if user_id:
            return str(user_id)
    
    return str(default_user_id or "1")
```

### Step 3: Update load_list_ids()
```python
def load_list_ids() -> List[Dict[str, str]]:
    """Load all saved list IDs from database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT list_type, list_id, list_url, item_count, 
                   last_synced, user_id, auto_approve 
            FROM lists
        """)
        results = []
        for row in cursor.fetchall():
            list_item = {
                "type": row[0],
                "id": row[1],
                "url": row[2],
                "item_count": row[3],
                "last_synced": row[4],
                "user_id": row[5] or "1",
                "auto_approve": row[6] if row[6] is not None else True
            }
            results.append(list_item)
        return results
```

---

## 📊 Comparison of Options

| Feature | Option A (user_id) | Option B (auto_approve) |
|---------|-------------------|------------------------|
| **Database changes** | None ✅ | Migration needed ❌ |
| **Code changes** | Minimal (config only) ✅ | Moderate ⚠️ |
| **Flexibility** | Very flexible ✅ | Less flexible ⚠️ |
| **User understanding** | Requires Overseerr knowledge ⚠️ | More intuitive ✅ |
| **Implementation time** | 2-3 hours ✅ | 4-6 hours ❌ |
| **Maintenance** | Low ✅ | Medium ⚠️ |

---

## 🧪 Testing Strategy

### Unit Tests

```python
def test_choose_request_user_id_auto_approve():
    source_lists = [{'type': 'mdblist', 'id': 'test', 'user_id': '1'}]
    assert choose_request_user_id(source_lists, '1') == '1'

def test_choose_request_user_id_manual():
    source_lists = [{'type': 'mdblist', 'id': 'test', 'user_id': '2'}]
    assert choose_request_user_id(source_lists, '1') == '2'

def test_choose_request_user_id_mixed():
    # When item is in multiple lists, first list wins
    source_lists = [
        {'type': 'mdblist', 'id': 'manual', 'user_id': '2'},
        {'type': 'mdblist', 'id': 'auto', 'user_id': '1'}
    ]
    assert choose_request_user_id(source_lists, '1') == '2'
```

### Integration Tests

```python
def test_manual_approval_flow():
    # Setup: Create list with manual approval user
    save_list_id('test-list', 'mdblist', user_id='2')
    
    # Act: Sync a movie from this list
    overseerr_client = OverseerrClient(URL, API_KEY, '1')
    result = process_media_item(movie_item, overseerr_client, False)
    
    # Assert: Check request status in Overseerr
    request_status = overseerr_client.get_request_status(movie_item['overseerr_id'])
    assert request_status == 'PENDING'  # Not auto-approved
```

---

## 📚 Documentation Updates Needed

### 1. User Guide
**File:** `docs/user-guide.md`

```markdown
## Per-List Auto-Approval

You can configure whether requests from a list are auto-approved or require manual approval.

### Setup

1. **Create a manual approval user in Overseerr:**
   - Go to Settings → Users → Add User
   - Grant "REQUEST" permission only (no AUTO_APPROVE)
   - Note the user ID (e.g., 2)

2. **Configure lists:**
   - In List-Sync UI, select "Manual approval" for lists
   - Or set `user_id="2"` when adding lists via API

### Use Cases

- **Auto-approve:** Curated lists, favorites, watchlists
- **Manual approval:** Trending lists, new releases, large lists
```

### 2. API Documentation
**File:** `docs/api-reference.md`

```markdown
POST /api/lists/add
{
  "list_type": "mdblist",
  "list_id": "https://mdblist.com/lists/user/trending",
  "user_id": "2"  // Optional: Overseerr user ID (default: "1")
}
```

### 3. Environment Variables
**File:** `docs/configuration.md`

```markdown
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MANUAL_APPROVAL_USER_ID` | Overseerr user ID for manual approval | `"2"` | `"3"` |
| `MDBLIST_MANUAL_LISTS` | Lists requiring manual approval | - | `https://...` |
```

---

## 🚀 Rollout Strategy

### Phase 1: Backend (Week 1)
- [ ] Create manual approval user in Overseerr
- [ ] Test current user_id functionality
- [ ] Document Overseerr user setup

### Phase 2: Configuration (Week 1-2)
- [ ] Add environment variable support
- [ ] Test with configuration files
- [ ] Update documentation

### Phase 3: UI (Week 2-3)
- [ ] Add user_id dropdown to list form
- [ ] Add help text explaining options
- [ ] Test in development

### Phase 4: Production (Week 3)
- [ ] Deploy to production
- [ ] Monitor logs for user_id selection
- [ ] Gather user feedback

---

## 🎯 Success Criteria

- [ ] Lists can be configured with different user_ids
- [ ] Requests use correct user_id based on source list
- [ ] Auto-approve lists → requests instantly approved
- [ ] Manual lists → requests stay pending
- [ ] Logging shows which user_id was used
- [ ] Documentation updated
- [ ] Tests passing

---

## 🔮 Future Enhancements

### v1.1: Per-User Request Quotas
- Limit requests per user per day
- Useful for trending/new release lists

### v1.2: Conditional Auto-Approval
- Auto-approve if rating > 7.0
- Auto-approve if in top 250
- Manual review for others

### v1.3: Request Templates
- Different quality profiles per list
- Different root folders per list
- Different language profiles per list

---

## 💡 Key Insights

1. **The infrastructure already exists!** The `user_id` field and `choose_request_user_id()` function are already implemented.

2. **Auto-approval is an Overseerr user permission**, not an API parameter. We control it by changing which user makes the request.

3. **Option A (using existing user_id) is simpler and more flexible** than adding a new boolean field.

4. **The hardest part is Overseerr user management**, not the code changes. Users need to understand Overseerr's permission system.

---

## 📞 Questions for User

1. **Preferred approach?**
   - Option A: Use existing `user_id` field (simpler)
   - Option B: Add new `auto_approve` boolean (more explicit)

2. **Configuration method?**
   - Environment variables
   - Web UI
   - Both

3. **Default behavior?**
   - All lists auto-approve (current behavior)
   - All lists manual approval
   - Per-list configuration required

---

**Author:** Claude  
**Reviewer:** Fabian  
**Status:** Design Draft  
**Next Step:** User feedback on preferred approach


