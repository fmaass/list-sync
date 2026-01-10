# Manual Approval Cleanup

## Quick Commands (runs on saturn.local)

```bash
# 1. Dry run (safe preview)
./run_cleanup.sh --dry-run

# 2. Actually do it
./run_cleanup.sh

# 3. Trigger sync to re-add with manual approval
ssh saturn.local "curl -X POST http://localhost:4222/api/sync/trigger"
```

## What It Does

1. Finds movies ONLY in manual approval lists (not in auto-approved lists)
2. Unrequests pending movies (status 1-2, not downloaded yet)  
3. Skips downloaded movies (status 3-5, keeps them)
4. After sync, movies need manual approval in Seerr

## Expected Output

```
Movies unique to manual lists: 45
Also in auto lists: 105 (stay auto-approved)
Unrequested: 23 → need approval after sync
Already downloaded: 15 → kept as-is
```

## Troubleshooting

- Container not running: `ssh saturn.local 'cd ~/list-sync && sudo /usr/bin/docker compose up -d'`
- No manual lists: Check `MDBLIST_MANUAL_LISTS` in `.env`
- Movies not re-requesting: Run sync after cleanup
