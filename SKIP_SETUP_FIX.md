# SKIP_SETUP Environment Variable Fix

## Root Cause Analysis

The `SKIP_SETUP` environment variable was not being recognized due to **two issues**:

### Issue 1: Missing from Docker Compose Configuration
**Problem:** `SKIP_SETUP` was not defined in any docker-compose files, so Docker Compose never passed it to the container.

**Files affected:**
- `docker-compose.yml`
- `docker-compose.core.yml`
- `docker-compose.local.yml`

**Impact:** Even if set in `.env` file, Docker Compose wouldn't pass it to the container unless explicitly listed in the `environment:` section.

### Issue 2: Supervisor Environment Variable Inheritance
**Problem:** Supervisor's configuration for `listsync-core` didn't explicitly ensure environment variables were passed through to the child process.

**File affected:**
- `Dockerfile` (supervisor configuration)

**Impact:** Even if Docker passed the variable to the container, supervisor might not have passed it to the Python process.

## Fixes Applied

### Fix 1: Added SKIP_SETUP to Docker Compose Files
Added `SKIP_SETUP=${SKIP_SETUP:-false}` to the environment section of all docker-compose files:

```yaml
# Docker-specific settings
- RUNNING_IN_DOCKER=true
- NO_SANDBOX=1
- DISPLAY=:99
- SKIP_SETUP=${SKIP_SETUP:-false}  # ← Added
```

This allows `SKIP_SETUP` to be:
- Set in `.env` file: `SKIP_SETUP=true`
- Set via command line: `SKIP_SETUP=true docker-compose up`
- Defaults to `false` if not set

### Fix 2: Explicit Supervisor Environment Variable Passing
Added `clear_env=false` to the supervisor configuration for `listsync-core`:

```ini
[program:listsync-core]
command=/usr/src/app/run-listsync-core.sh
directory=/usr/src/app
autostart=true
autorestart=true
clear_env=false  # ← Added - ensures env vars are inherited
...
```

This ensures supervisor doesn't clear the environment and passes all variables from Docker to the Python process.

## How to Use

### Option 1: Set in `.env` file
```bash
# In your .env file
SKIP_SETUP=true
```

### Option 2: Set via command line
```bash
SKIP_SETUP=true docker-compose up -d
```

### Option 3: Set in docker-compose.yml directly
```yaml
environment:
  - SKIP_SETUP=true
```

## Verification

After deploying the fix, verify `SKIP_SETUP` is recognized:

```bash
# Check container logs for debug output
docker logs listsync-full | grep "SKIP_SETUP"

# Should see:
# 🔍 DEBUG: SKIP_SETUP = True
# 🔍 SKIP_SETUP=true: Using environment variables directly
```

## Testing

1. **Rebuild the Docker image** (if using Dockerfile):
   ```bash
   docker build -t list-sync-custom:latest -f Dockerfile .
   ```

2. **Set SKIP_SETUP in .env**:
   ```bash
   echo "SKIP_SETUP=true" >> .env
   ```

3. **Restart container**:
   ```bash
   docker-compose restart listsync-full
   ```

4. **Check logs**:
   ```bash
   docker logs listsync-full | grep -i "skip_setup"
   ```

## Expected Behavior

When `SKIP_SETUP=true`:
- ✅ Setup wizard is bypassed
- ✅ Environment variables are used directly
- ✅ Auto-migration runs if needed
- ✅ Application starts in automated mode immediately

When `SKIP_SETUP=false` (or not set):
- ✅ Normal setup flow
- ✅ Web UI setup wizard available
- ✅ Database-based configuration

## Files Changed

1. `Dockerfile` - Added `clear_env=false` to supervisor config
2. `docker-compose.yml` - Added `SKIP_SETUP=${SKIP_SETUP:-false}`
3. `docker-compose.core.yml` - Added `SKIP_SETUP=${SKIP_SETUP:-false}`
4. `docker-compose.local.yml` - Added `SKIP_SETUP=${SKIP_SETUP:-false}`

## Notes

- The fix is backward compatible - if `SKIP_SETUP` is not set, it defaults to `false`
- Both fixes are necessary - Docker Compose must pass the variable AND supervisor must pass it to Python
- The variable is case-sensitive: use `SKIP_SETUP` (all caps)

