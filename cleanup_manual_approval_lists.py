#!/usr/bin/env python3
"""
Cleanup script for manual approval lists in Seerr.

This script:
1. Identifies movies that are UNIQUE to manual approval lists (not in any auto-approved list)
2. Checks their status in Seerr
3. Unrequests movies that are still pending (status 1 or 2) - not yet downloaded
4. Provides a report of actions taken

Usage:
    python cleanup_manual_approval_lists.py [--dry-run]
"""

import os
import sys
import sqlite3
import logging
import requests
from typing import List, Dict, Set, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from list_sync.utils.logger import DATA_DIR
from list_sync.config import load_env_config
from list_sync.api.overseerr import OverseerrClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use /data path in Docker, fallback to DATA_DIR for local
DB_FILE = "/data/list_sync.db" if os.path.exists("/data/list_sync.db") else os.path.join(DATA_DIR, "list_sync.db")


class ManualApprovalCleanup:
    """Handles cleanup of manual approval list requests in Seerr."""
    
    def __init__(self, overseerr_url: str, api_key: str, dry_run: bool = False):
        """
        Initialize the cleanup manager.
        
        Args:
            overseerr_url: Seerr/Overseerr URL
            api_key: API key
            dry_run: If True, only simulate actions without making changes
        """
        self.overseerr_url = overseerr_url.rstrip('/')
        self.api_key = api_key
        self.dry_run = dry_run
        self.client = OverseerrClient(overseerr_url, api_key)
        self.headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
        
        logger.info(f"Initialized cleanup manager (dry_run={dry_run})")
    
    def get_manual_approval_lists(self) -> List[Dict[str, str]]:
        """
        Get all lists configured for manual approval (user_id != '1').
        
        Returns:
            List of dicts with 'type', 'id', and 'user_id'
        """
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT list_type, list_id, user_id
                FROM lists
                WHERE user_id IS NOT NULL AND user_id != '1'
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'type': row[0],
                    'id': row[1],
                    'user_id': row[2]
                })
            
            logger.info(f"Found {len(results)} manual approval lists")
            for lst in results:
                logger.info(f"  - {lst['type']}:{lst['id']} (user_id={lst['user_id']})")
            
            return results
    
    def get_auto_approval_lists(self) -> List[Dict[str, str]]:
        """
        Get all lists configured for auto approval (user_id = '1').
        
        Returns:
            List of dicts with 'type' and 'id'
        """
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT list_type, list_id
                FROM lists
                WHERE user_id IS NULL OR user_id = '1'
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'type': row[0],
                    'id': row[1]
                })
            
            logger.info(f"Found {len(results)} auto-approval lists")
            return results
    
    def get_movies_from_lists(self, lists: List[Dict[str, str]]) -> Set[int]:
        """
        Get all unique movie TMDB IDs from specified lists.
        
        Args:
            lists: List of dicts with 'type' and 'id'
        
        Returns:
            Set of TMDB IDs
        """
        if not lists:
            return set()
        
        tmdb_ids = set()
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            for lst in lists:
                list_type = lst['type']
                list_id = lst['id']
                
                # Query the item_lists junction table to find all items in this list
                # Try using overseerr_id if tmdb_id is not populated
                cursor.execute("""
                    SELECT DISTINCT 
                        COALESCE(si.tmdb_id, CAST(si.overseerr_id AS TEXT)) as id
                    FROM synced_items si
                    INNER JOIN item_lists il ON si.id = il.item_id
                    WHERE il.list_type = ? 
                      AND il.list_id = ?
                      AND si.media_type = 'movie'
                      AND (si.tmdb_id IS NOT NULL OR si.overseerr_id IS NOT NULL)
                      AND COALESCE(si.tmdb_id, CAST(si.overseerr_id AS TEXT)) != ''
                """, (list_type, list_id))
                
                for row in cursor.fetchall():
                    try:
                        tmdb_id = int(row[0])
                        tmdb_ids.add(tmdb_id)
                    except (ValueError, TypeError):
                        continue
        
        return tmdb_ids
    
    def get_movie_details(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """
        Get movie details from the database.
        
        Args:
            tmdb_id: TMDB ID (or overseerr_id which is the same)
            
        Returns:
            Dict with movie details or None
        """
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Try both tmdb_id and overseerr_id (they're the same in Seerr)
            cursor.execute("""
                SELECT title, year, 
                       COALESCE(tmdb_id, CAST(overseerr_id AS TEXT)) as id,
                       status
                FROM synced_items
                WHERE (tmdb_id = ? OR overseerr_id = ?) 
                  AND media_type = 'movie'
                LIMIT 1
            """, (str(tmdb_id), tmdb_id))
            
            row = cursor.fetchone()
            if row:
                return {
                    'title': row[0],
                    'year': row[1],
                    'tmdb_id': int(row[2]) if row[2] else tmdb_id,
                    'db_status': row[3]
                }
        
        return None
    
    def get_request_id_by_tmdb(self, tmdb_id: int) -> Optional[int]:
        """
        Get the Seerr request ID for a given TMDB ID.
        
        Args:
            tmdb_id: TMDB ID
            
        Returns:
            Request ID or None if not found
        """
        try:
            # Get media details
            media_url = f"{self.overseerr_url}/api/v1/movie/{tmdb_id}"
            response = requests.get(media_url, headers=self.headers, timeout=10)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            media_data = response.json()
            
            # Check if there's a request
            media_info = media_data.get('mediaInfo', {})
            if not media_info:
                return None
            
            # Get requests for this media
            requests_list = media_info.get('requests', [])
            if not requests_list:
                return None
            
            # Return the first request ID (there should typically be only one)
            return requests_list[0].get('id')
            
        except Exception as e:
            logger.error(f"Error getting request ID for TMDB {tmdb_id}: {e}")
            return None
    
    def get_media_status_details(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed status information for a movie from Seerr.
        
        Args:
            tmdb_id: TMDB ID
            
        Returns:
            Dict with status details or None
        """
        try:
            media_url = f"{self.overseerr_url}/api/v1/movie/{tmdb_id}"
            response = requests.get(media_url, headers=self.headers, timeout=10)
            
            if response.status_code == 404:
                return {'status': None, 'status_text': 'Not in Seerr', 'request_id': None}
            
            response.raise_for_status()
            media_data = response.json()
            
            media_info = media_data.get('mediaInfo', {})
            status = media_info.get('status') if media_info else None
            
            # Status codes:
            # None or 0: NOT REQUESTED
            # 1: REQUESTED (pending approval)
            # 2: PENDING (approved, waiting for download)
            # 3: PROCESSING (downloading/importing)
            # 4: PARTIALLY_AVAILABLE
            # 5: AVAILABLE (fully available)
            
            status_map = {
                None: 'Not Requested',
                0: 'Not Requested',
                1: 'Pending Approval',
                2: 'Approved (Waiting Download)',
                3: 'Downloading',
                4: 'Partially Available',
                5: 'Available'
            }
            
            # Get request ID
            request_id = None
            requests_list = media_info.get('requests', []) if media_info else []
            if requests_list:
                request_id = requests_list[0].get('id')
            
            return {
                'status': status,
                'status_text': status_map.get(status, f'Unknown ({status})'),
                'request_id': request_id
            }
            
        except Exception as e:
            logger.error(f"Error getting status for TMDB {tmdb_id}: {e}")
            return None
    
    def delete_request(self, request_id: int) -> bool:
        """
        Delete/unrequest a media request from Seerr.
        
        Args:
            request_id: Request ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.dry_run:
                logger.info(f"  [DRY RUN] Would delete request ID {request_id}")
                return True
            
            delete_url = f"{self.overseerr_url}/api/v1/request/{request_id}"
            response = requests.delete(delete_url, headers=self.headers, timeout=10)
            
            if response.status_code == 404:
                logger.warning(f"  Request ID {request_id} not found (already deleted?)")
                return False
            
            response.raise_for_status()
            logger.info(f"  ✓ Successfully deleted request ID {request_id}")
            return True
            
        except Exception as e:
            logger.error(f"  ✗ Error deleting request ID {request_id}: {e}")
            return False
    
    def run_cleanup(self) -> Dict[str, Any]:
        """
        Run the cleanup process.
        
        Returns:
            Dict with cleanup results and statistics
        """
        logger.info("=" * 80)
        logger.info("Starting Manual Approval Lists Cleanup")
        logger.info("=" * 80)
        
        results = {
            'manual_lists': [],
            'auto_lists': [],
            'movies_manual_only': [],
            'movies_also_in_auto': [],
            'unrequested': [],
            'already_downloaded': [],
            'not_requested': [],
            'errors': []
        }
        
        # Step 1: Get manual approval lists
        logger.info("\n[Step 1] Identifying manual approval lists...")
        manual_lists = self.get_manual_approval_lists()
        results['manual_lists'] = manual_lists
        
        if not manual_lists:
            logger.warning("No manual approval lists found!")
            logger.info("Lists are set to manual approval when they have user_id != '1'")
            logger.info("Check your MDBLIST_MANUAL_LISTS environment variable.")
            return results
        
        # Step 2: Get auto approval lists
        logger.info("\n[Step 2] Identifying auto-approval lists...")
        auto_lists = self.get_auto_approval_lists()
        results['auto_lists'] = auto_lists
        
        # Step 3: Get movies from each category
        logger.info("\n[Step 3] Fetching movies from lists...")
        manual_movies = self.get_movies_from_lists(manual_lists)
        auto_movies = self.get_movies_from_lists(auto_lists)
        
        logger.info(f"  - Movies in manual approval lists: {len(manual_movies)}")
        logger.info(f"  - Movies in auto-approval lists: {len(auto_movies)}")
        
        # Step 4: Find movies UNIQUE to manual approval lists
        logger.info("\n[Step 4] Finding movies unique to manual approval lists...")
        unique_to_manual = manual_movies - auto_movies
        also_in_auto = manual_movies & auto_movies
        
        logger.info(f"  - Movies UNIQUE to manual approval lists: {len(unique_to_manual)}")
        logger.info(f"  - Movies also in auto-approval lists: {len(also_in_auto)}")
        
        results['movies_also_in_auto'] = list(also_in_auto)
        
        # Step 5: Check status and unrequest pending movies
        logger.info("\n[Step 5] Checking status and unrequesting pending movies...")
        logger.info("=" * 80)
        
        for tmdb_id in sorted(unique_to_manual):
            movie_details = self.get_movie_details(tmdb_id)
            if not movie_details:
                logger.warning(f"Could not find details for TMDB ID {tmdb_id}")
                continue
            
            title = movie_details['title']
            year = movie_details['year']
            
            logger.info(f"\nProcessing: {title} ({year}) [TMDB: {tmdb_id}]")
            
            # Get status from Seerr
            status_info = self.get_media_status_details(tmdb_id)
            if not status_info:
                logger.error(f"  Could not get status from Seerr")
                results['errors'].append({
                    'tmdb_id': tmdb_id,
                    'title': title,
                    'error': 'Could not get status from Seerr'
                })
                continue
            
            status = status_info['status']
            status_text = status_info['status_text']
            request_id = status_info['request_id']
            
            logger.info(f"  Status: {status_text}")
            
            movie_info = {
                'tmdb_id': tmdb_id,
                'title': title,
                'year': year,
                'status': status,
                'status_text': status_text,
                'request_id': request_id
            }
            
            # Check if we should unrequest
            # Status 1 = Pending Approval
            # Status 2 = Approved but waiting for download
            # We unrequest these since they haven't been downloaded yet
            if status in [1, 2]:
                logger.info(f"  → Movie is pending (status {status}), will unrequest")
                
                if request_id:
                    if self.delete_request(request_id):
                        results['unrequested'].append(movie_info)
                    else:
                        results['errors'].append({
                            **movie_info,
                            'error': 'Failed to delete request'
                        })
                else:
                    logger.warning(f"  ⚠ No request ID found, cannot unrequest")
                    results['errors'].append({
                        **movie_info,
                        'error': 'No request ID found'
                    })
            
            elif status in [3, 4, 5]:
                logger.info(f"  → Movie is downloaded/downloading (status {status}), skipping")
                results['already_downloaded'].append(movie_info)
            
            else:
                logger.info(f"  → Movie not requested (status {status}), skipping")
                results['not_requested'].append(movie_info)
            
            results['movies_manual_only'].append(movie_info)
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of the cleanup results."""
        logger.info("\n" + "=" * 80)
        logger.info("CLEANUP SUMMARY")
        logger.info("=" * 80)
        
        logger.info(f"\n📋 Lists:")
        logger.info(f"  - Manual approval lists: {len(results['manual_lists'])}")
        for lst in results['manual_lists']:
            logger.info(f"    • {lst['type']}:{lst['id']}")
        logger.info(f"  - Auto-approval lists: {len(results['auto_lists'])}")
        
        logger.info(f"\n🎬 Movies:")
        logger.info(f"  - Unique to manual lists: {len(results['movies_manual_only'])}")
        logger.info(f"  - Also in auto lists: {len(results['movies_also_in_auto'])}")
        
        logger.info(f"\n✅ Actions:")
        logger.info(f"  - Unrequested: {len(results['unrequested'])}")
        logger.info(f"  - Already downloaded (skipped): {len(results['already_downloaded'])}")
        logger.info(f"  - Not requested (skipped): {len(results['not_requested'])}")
        logger.info(f"  - Errors: {len(results['errors'])}")
        
        if results['unrequested']:
            logger.info(f"\n🔄 Unrequested Movies:")
            for movie in results['unrequested']:
                logger.info(f"  • {movie['title']} ({movie['year']}) - {movie['status_text']}")
        
        if results['errors']:
            logger.info(f"\n❌ Errors:")
            for error in results['errors']:
                logger.info(f"  • {error['title']} ({error['year']}): {error.get('error', 'Unknown error')}")
        
        logger.info("\n" + "=" * 80)
        
        if self.dry_run:
            logger.info("\n⚠️  DRY RUN MODE - No actual changes were made")
            logger.info("Run without --dry-run to apply changes")
        else:
            logger.info("\n✅ Cleanup completed!")
            logger.info("\nNext steps:")
            logger.info("  1. Run a sync to re-add these movies with manual approval")
            logger.info("  2. Check Seerr to verify movies are pending approval")
            logger.info("  3. Manually approve the movies you want")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Cleanup manual approval lists in Seerr",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (simulation only)
  python cleanup_manual_approval_lists.py --dry-run
  
  # Actually perform cleanup
  python cleanup_manual_approval_lists.py
        """
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate actions without making any changes'
    )
    
    args = parser.parse_args()
    
    # Load configuration - try env vars first to avoid decryption issues
    logger.info("Loading configuration...")
    overseerr_url = os.getenv('OVERSEERR_URL')
    api_key = os.getenv('OVERSEERR_API_KEY')
    
    # Fallback to config manager if env vars not set
    if not overseerr_url or not api_key:
        config = load_env_config()
        if not config or not config[0] or not config[1]:
            logger.error("❌ Overseerr/Seerr not configured!")
            logger.error("Please set OVERSEERR_URL and OVERSEERR_API_KEY in your .env file")
            sys.exit(1)
        overseerr_url, api_key = config[0], config[1]
    
    # Run cleanup
    cleanup = ManualApprovalCleanup(overseerr_url, api_key, dry_run=args.dry_run)
    results = cleanup.run_cleanup()
    cleanup.print_summary(results)
    
    # Exit code based on results
    if results['errors']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
