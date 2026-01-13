"""
Automatic Radarr blacklist sync for ListSync.
Fetches exclusions from Radarr and updates blacklist.json.
"""
import logging
import os
import requests
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def sync_radarr_blacklist(radarr_url: str = None, radarr_api_key: str = None, blacklist_file: str = None) -> bool:
    """
    Fetch exclusions from Radarr and update blacklist file.
    
    Args:
        radarr_url: Radarr URL (defaults to env var or http://radarr:7878)
        radarr_api_key: Radarr API key (defaults to env var)
        blacklist_file: Path to blacklist file (defaults to env var or data/blacklist.json)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Get configuration
    radarr_url = radarr_url or os.getenv('RADARR_URL', 'http://radarr:7878')
    radarr_api_key = radarr_api_key or os.getenv('RADARR_API_KEY')
    blacklist_file = blacklist_file or os.getenv('BLOCKLIST_FILE', 'data/blacklist.json')
    
    if not radarr_api_key:
        logger.warning("RADARR_API_KEY not set - cannot sync Radarr exclusions")
        return False
    
    try:
        logger.info(f"Syncing Radarr exclusions from {radarr_url}...")
        
        # Fetch exclusions from Radarr
        headers = {'X-Api-Key': radarr_api_key}
        response = requests.get(
            f"{radarr_url.rstrip('/')}/api/v3/exclusions",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        exclusions = response.json()
        tmdb_ids = sorted([e['tmdbId'] for e in exclusions if e.get('tmdbId')])
        
        logger.info(f"Found {len(exclusions)} Radarr exclusions ({len(tmdb_ids)} with TMDb IDs)")
        
        # Create blacklist structure
        blacklist_data = {
            'version': '1.0',
            'exported_at': datetime.utcnow().isoformat() + 'Z',
            'source': 'radarr',
            'movies': tmdb_ids,
            'tv': []
        }
        
        # Ensure directory exists
        Path(blacklist_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(blacklist_file, 'w') as f:
            json.dump(blacklist_data, f, indent=2)
        
        logger.info(f"✅ Saved {len(tmdb_ids)} exclusions to {blacklist_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync Radarr blacklist: {e}")
        return False


if __name__ == '__main__':
    # For standalone execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    success = sync_radarr_blacklist()
    exit(0 if success else 1)
