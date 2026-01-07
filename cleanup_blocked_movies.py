#!/usr/bin/env python3
"""
Emergency Cleanup: Remove all blocked movies from Radarr
---------------------------------------------------------
This script removes movies that are on Radarr's exclusion list
but somehow ended up in the library anyway.

Usage: python3 cleanup_blocked_movies.py
"""

import requests
import sys
import time

# Configuration
RADARR_URL = "http://radarr:7878"
RADARR_API_KEY = "b96abe1b76384476b9fbf381ed6941d6"

def get_radarr_exclusions():
    """Get all exclusions from Radarr"""
    headers = {"X-Api-Key": RADARR_API_KEY}
    resp = requests.get(f"{RADARR_URL}/api/v3/exclusions", headers=headers, timeout=30)
    resp.raise_for_status()
    exclusions = resp.json()
    print(f"✅ Found {len(exclusions)} exclusions in Radarr")
    return exclusions

def get_radarr_movies():
    """Get all movies currently in Radarr library"""
    headers = {"X-Api-Key": RADARR_API_KEY}
    resp = requests.get(f"{RADARR_URL}/api/v3/movie", headers=headers, timeout=30)
    resp.raise_for_status()
    movies = resp.json()
    print(f"✅ Found {len(movies)} movies in Radarr library")
    return movies

def delete_movie(movie_id, title, tmdb_id):
    """Delete a movie from Radarr"""
    headers = {"X-Api-Key": RADARR_API_KEY}
    
    # Delete with deleteFiles=true to remove downloaded files
    resp = requests.delete(
        f"{RADARR_URL}/api/v3/movie/{movie_id}",
        headers=headers,
        params={"deleteFiles": "true", "addImportExclusion": "false"},
        timeout=30
    )
    resp.raise_for_status()
    print(f"  ✅ Deleted: {title} (TMDB: {tmdb_id}, Radarr ID: {movie_id})")
    return True

def main():
    print("=" * 80)
    print("EMERGENCY CLEANUP: Removing Blocked Movies from Radarr")
    print("=" * 80)
    print()
    
    try:
        # Get exclusions
        print("Step 1: Fetching Radarr exclusions...")
        exclusions = get_radarr_exclusions()
        excluded_tmdb_ids = set(e["tmdbId"] for e in exclusions)
        print(f"  Excluded TMDB IDs: {len(excluded_tmdb_ids)}")
        print()
        
        # Get library
        print("Step 2: Fetching Radarr library...")
        movies = get_radarr_movies()
        print()
        
        # Find violations
        print("Step 3: Finding movies that shouldn't be in library...")
        violations = []
        for movie in movies:
            if movie.get("tmdbId") in excluded_tmdb_ids:
                violations.append(movie)
        
        print(f"  🚨 Found {len(violations)} movies that are on exclusion list!")
        print()
        
        if not violations:
            print("✅ No violations found! Library is clean.")
            return
        
        # Display violations
        print("Movies to be deleted:")
        for movie in violations:
            size_mb = (movie.get("movieFile", {}).get("size", 0) / 1024 / 1024)
            print(f"  • {movie['title']} ({movie.get('year', 'N/A')}) - TMDB: {movie['tmdbId']} - Size: {size_mb:.1f} MB")
        print()
        
        # Confirm
        response = input(f"Delete {len(violations)} movies? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            return
        
        # Delete each movie
        print()
        print("Step 4: Deleting movies...")
        deleted_count = 0
        failed_count = 0
        total_size_freed = 0
        
        for movie in violations:
            try:
                title = movie["title"]
                tmdb_id = movie["tmdbId"]
                movie_id = movie["id"]
                size = movie.get("movieFile", {}).get("size", 0)
                
                delete_movie(movie_id, title, tmdb_id)
                deleted_count += 1
                total_size_freed += size
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ❌ Failed to delete {movie['title']}: {e}")
                failed_count += 1
        
        # Summary
        print()
        print("=" * 80)
        print("CLEANUP COMPLETE")
        print("=" * 80)
        print(f"Deleted: {deleted_count} movies")
        print(f"Failed: {failed_count} movies")
        print(f"Space freed: {total_size_freed / 1024 / 1024 / 1024:.2f} GB")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


