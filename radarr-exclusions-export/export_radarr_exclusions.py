#!/usr/bin/env python3
"""
Radarr Exclusions Export Service
---------------------------------
Exports Radarr's exclusion list to a JSON file for consumption by list-sync.

This service:
1. Connects to Radarr API
2. Fetches all import exclusions (blocked movies)
3. Exports TMDB IDs to a JSON file
4. Runs on a schedule (via cron or manual trigger)

Why Radarr instead of Seerr:
- Radarr exclusions are the SOURCE OF TRUTH (~120 items)
- Seerr syncs FROM Radarr (but may not be up to date)
- Direct from Radarr ensures we get all exclusions

Environment Variables:
    RADARR_URL: Radarr API base URL (e.g., http://radarr:7878)
    RADARR_API_KEY: Radarr API key
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
RADARR_URL = os.getenv("RADARR_URL", "http://radarr:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")
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


class RadarrExclusionsExporter:
    """Exports Radarr exclusions to JSON file"""
    
    def __init__(self, radarr_url: str, api_key: str):
        """
        Initialize exporter.
        
        Args:
            radarr_url: Base URL of Radarr instance
            api_key: Radarr API key
        """
        self.radarr_url = radarr_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def fetch_exclusions(self) -> List[Dict]:
        """
        Fetch all import exclusions from Radarr API.
        
        Returns:
            List of exclusion entries
        """
        try:
            url = f"{self.radarr_url}/api/v3/exclusions"
            
            logger.info(f"Fetching exclusions from {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            exclusions = response.json()
            logger.info(f"Fetched {len(exclusions)} exclusions from Radarr")
            return exclusions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch exclusions from Radarr: {e}")
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
            # Fetch exclusions from Radarr
            logger.info("Starting exclusions export from Radarr")
            exclusions = self.fetch_exclusions()
            
            # Extract TMDB IDs from Radarr exclusions
            # Radarr exclusions are all movies
            movie_ids = [item['tmdbId'] for item in exclusions if 'tmdbId' in item]
            tv_ids = []  # Radarr only handles movies; Sonarr would have TV exclusions
            
            # Log what we found
            logger.info(f"Found {len(exclusions)} total exclusions in Radarr")
            logger.info(f"Extracted: {len(movie_ids)} movie TMDB IDs")
            
            # Remove duplicates and sort
            movie_ids = sorted(list(set(movie_ids)))
            tv_ids = sorted(list(set(tv_ids)))
            
            # Create output structure
            output_data = {
                'version': '1.0',
                'exported_at': stats['exported_at'],
                'source': 'radarr',
                'movies': movie_ids,
                'tv': tv_ids,  # Empty for Radarr (only handles movies)
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
    if not RADARR_API_KEY:
        logger.error("RADARR_API_KEY environment variable not set")
        return False
    
    if not RADARR_URL:
        logger.error("RADARR_URL environment variable not set")
        return False
    
    logger.info(f"Configuration verified:")
    logger.info(f"  RADARR_URL: {RADARR_URL}")
    logger.info(f"  OUTPUT_FILE: {OUTPUT_FILE}")
    logger.info(f"  LOG_LEVEL: {LOG_LEVEL}")
    
    return True


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Radarr Exclusions Export Service")
    logger.info("=" * 60)
    
    # Verify configuration
    if not verify_configuration():
        logger.error("Configuration verification failed")
        sys.exit(1)
    
    # Create exporter
    exporter = RadarrExclusionsExporter(RADARR_URL, RADARR_API_KEY)
    
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

