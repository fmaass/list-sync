#!/usr/bin/env python3
"""
Seerr Blocklist Export Service
-------------------------------
Exports Seerr's blacklist to a JSON file for consumption by list-sync.

This service:
1. Connects to Seerr API
2. Fetches all blacklisted items (movies and TV shows)
3. Exports TMDB IDs to a JSON file
4. Runs on a schedule (via cron or manual trigger)

Environment Variables:
    SEERR_URL: Seerr API base URL (e.g., http://jellyseerr:5055)
    SEERR_API_KEY: Seerr API key
    OUTPUT_FILE: Path to output JSON file (default: /data/blocklist.json)
    LOG_LEVEL: Logging level (default: INFO)

Usage:
    python export_seerr_blocklist.py
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Configuration from environment
SEERR_URL = os.getenv("SEERR_URL", "http://jellyseerr:5055")
SEERR_API_KEY = os.getenv("SEERR_API_KEY")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "/data/blocklist.json")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("seerr-blocklist-export")


class SeerrBlocklistExporter:
    """Exports Seerr blacklist to JSON file"""
    
    def __init__(self, seerr_url: str, api_key: str):
        """
        Initialize exporter.
        
        Args:
            seerr_url: Base URL of Seerr instance
            api_key: Seerr API key
        """
        self.seerr_url = seerr_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def fetch_blacklist(self) -> List[Dict]:
        """
        Fetch all blacklist items from Seerr API.
        
        Returns:
            List of blacklist entries
        """
        try:
            url = f"{self.seerr_url}/api/v1/blacklist"
            params = {'take': 10000}  # Get all items
            
            logger.info(f"Fetching blacklist from {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            logger.info(f"Fetched {len(results)} blacklist entries")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch blacklist: {e}")
            return []
    
    def export_to_json(self, output_path: str) -> Dict:
        """
        Export blacklist to JSON file.
        
        Args:
            output_path: Path to output JSON file
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'success': False,
            'movies_count': 0,
            'tv_count': 0,
            'total_count': 0,
            'exported_at': datetime.utcnow().isoformat() + 'Z',
            'error': None
        }
        
        try:
            # Fetch blacklist (all items)
            logger.info("Starting blacklist export")
            blacklist_items = self.fetch_blacklist()
            
            # Separate by media type and extract TMDB IDs
            # Seerr uses: 'movie' or 'tv' as string values
            movie_ids = [item['tmdbId'] for item in blacklist_items 
                        if 'tmdbId' in item and item.get('mediaType') == 'movie']
            tv_ids = [item['tmdbId'] for item in blacklist_items 
                     if 'tmdbId' in item and item.get('mediaType') == 'tv']
            
            # Log what we found for debugging
            logger.info(f"Found {len(blacklist_items)} total items in blacklist")
            logger.info(f"Filtered: {len(movie_ids)} movies, {len(tv_ids)} TV shows")
            
            # Remove duplicates and sort
            movie_ids = sorted(list(set(movie_ids)))
            tv_ids = sorted(list(set(tv_ids)))
            
            # Create output structure
            output_data = {
                'version': '1.0',
                'exported_at': stats['exported_at'],
                'source': 'seerr',
                'movies': movie_ids,
                'tv': tv_ids,
                'total_count': len(movie_ids) + len(tv_ids)
            }
            
            # Ensure output directory exists
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file atomically (write to temp, then rename)
            temp_path = output_path_obj.with_suffix('.tmp')
            try:
                with open(temp_path, 'w') as f:
                    json.dump(output_data, f, indent=2)
                
                # Atomic rename
                temp_path.rename(output_path_obj)
                
                # Update stats
                stats['success'] = True
                stats['movies_count'] = len(movie_ids)
                stats['tv_count'] = len(tv_ids)
                stats['total_count'] = len(movie_ids) + len(tv_ids)
                
                logger.info(f"Successfully exported blocklist to {output_path}")
                logger.info(f"Movies: {stats['movies_count']}, TV: {stats['tv_count']}, Total: {stats['total_count']}")
                
            except Exception as e:
                # Clean up temp file if rename failed
                if temp_path.exists():
                    temp_path.unlink()
                raise e
                
        except Exception as e:
            error_msg = f"Failed to export blocklist: {e}"
            logger.error(error_msg)
            stats['error'] = str(e)
            
        return stats


def verify_configuration() -> bool:
    """
    Verify required configuration is present.
    
    Returns:
        True if configuration is valid
    """
    if not SEERR_API_KEY:
        logger.error("SEERR_API_KEY environment variable not set")
        return False
    
    if not SEERR_URL:
        logger.error("SEERR_URL environment variable not set")
        return False
    
    logger.info(f"Configuration verified:")
    logger.info(f"  SEERR_URL: {SEERR_URL}")
    logger.info(f"  OUTPUT_FILE: {OUTPUT_FILE}")
    logger.info(f"  LOG_LEVEL: {LOG_LEVEL}")
    
    return True


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Seerr Blocklist Export Service")
    logger.info("=" * 60)
    
    # Verify configuration
    if not verify_configuration():
        logger.error("Configuration verification failed")
        sys.exit(1)
    
    # Create exporter
    exporter = SeerrBlocklistExporter(SEERR_URL, SEERR_API_KEY)
    
    # Export blocklist
    stats = exporter.export_to_json(OUTPUT_FILE)
    
    # Log results
    logger.info("=" * 60)
    if stats['success']:
        logger.info("✅ Export completed successfully")
        logger.info(f"   Movies: {stats['movies_count']}")
        logger.info(f"   TV Shows: {stats['tv_count']}")
        logger.info(f"   Total: {stats['total_count']}")
        logger.info(f"   File: {OUTPUT_FILE}")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("❌ Export failed")
        logger.error(f"   Error: {stats['error']}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

