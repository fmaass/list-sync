# Manual Approval Setup - Complete

## What Was Done

### 1. Fixed List Configuration ✅
- Separated manual approval lists from auto-approval
- 2 manual movie lists → 4 manual lists (added TV)

### 2. Declined Request Tracking ✅
- Auto-syncs declined from Seerr (status=3) before each sync
- Prevents infinite re-requesting of declined movies

### 3. Improved Blocklist ✅
- Added second blocklist check after TMDB ID resolution
- Catches blocked movies that come without TMDB ID from lists

### 4. Cleanup Tool ✅
- Unrequested 24 auto-approved movies from manual lists
- Skipped 183 already downloaded

## Current Configuration

### Manual Approval Lists (user_id=2)
- `linaspurinis/new-movies` (movies)
- `linaspurinis/imdb-moviemeter-top-100` (movies)
- `linaspurinis/imdb-tvmeter-top-100` (TV) ← NEW
- `linaspurinis/imdb-tvmeter` (TV) ← NEW

### Auto-Approval Lists (user_id=1)
- 15 moviemarder lists (movies only)

## How It Works Now

**Scenario 1: New movie/show in manual list**
- Requested with user_id=2 → Pending in Seerr → You approve/decline

**Scenario 2: Pending + sync**
- Sync sees status 1/2 → skips (doesn't duplicate)

**Scenario 3: Declined + sync**
- Auto-synced from Seerr → marked in DB → never re-requested

**Scenario 4: Blocked + sync**
- Checked against blocklist (181 movies) → status="blocked" → skipped

## Branch
`feature/manual-approval-cleanup` - All changes pushed to GitHub

## Safety Verified
- ✅ No TV lists in auto-approval config
- ✅ All TV lists have user_id=2 (manual)
- ✅ Blocklist still working (181 entries)
- ✅ .env backup created before changes
