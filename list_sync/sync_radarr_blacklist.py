"""
Automatic Radarr blacklist sync for ListSync.
Safely fetches exclusions from Radarr and updates blacklist.json.

SAFETY FEATURES:
- Atomic writes (temp file + rename)
- JSON validation before saving
- Backup of existing file
- Delta calculation (add new, remove deleted)
- Never overwrites without validation
"""
import logging
import os
import requests
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Set, List

logger = logging.getLogger(__name__)


def sync_radarr_blacklist(radarr_url: str = None, radarr_api_key: str = None, blacklist_file: str = None) -> bool:
    """
    Safely fetch exclusions from Radarr and update blacklist file with delta merge.
    
    This function:
    1. Loads existing blacklist
    2. Fetches current Radarr exclusions
    3. Calculates delta (new entries, removed entries)
    4. Merges properly (never blindly overwrites)
    5. Writes atomically (temp file + rename)
    6. Validates JSON integrity
    
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
        blacklist_path = Path(blacklist_file)
        
        # STEP 1: Load existing blacklist (if exists)
        existing_ids: Set[int] = set()
        existing_tv_ids: Set[int] = set()
        
        if blacklist_path.exists():
            try:
                with open(blacklist_path, 'r') as f:
                    existing_data = json.load(f)
                
                # Validate existing file structure
                if isinstance(existing_data, dict):
                    existing_ids = set(existing_data.get('movies', []))
                    existing_tv_ids = set(existing_data.get('tv', []))
                    logger.info(f"Loaded existing blacklist: {len(existing_ids)} movies, {len(existing_tv_ids)} TV shows")
                else:
                    logger.warning("Existing blacklist has unexpected format, will recreate")
            except json.JSONDecodeError as e:
                logger.error(f"Existing blacklist is corrupted: {e}")
                # Create backup of corrupted file
                backup_path = f"{blacklist_file}.corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(blacklist_path, backup_path)
                logger.info(f"Backed up corrupted file to {backup_path}")
        
        # STEP 2: Fetch current exclusions from Radarr
        logger.info(f"Fetching exclusions from Radarr ({radarr_url})...")
        headers = {'X-Api-Key': radarr_api_key}
        response = requests.get(
            f"{radarr_url.rstrip('/')}/api/v3/exclusions",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        exclusions = response.json()
        radarr_ids: Set[int] = set(e['tmdbId'] for e in exclusions if e.get('tmdbId'))
        
        logger.info(f"Fetched {len(exclusions)} Radarr exclusions ({len(radarr_ids)} with TMDb IDs)")
        
        # STEP 3: Calculate delta
        new_ids = radarr_ids - existing_ids
        removed_ids = existing_ids - radarr_ids
        
        if new_ids:
            logger.info(f"➕ New exclusions to add: {len(new_ids)}")
        if removed_ids:
            logger.info(f"➖ Exclusions removed from Radarr: {len(removed_ids)}")
        if not new_ids and not removed_ids:
            logger.info("No changes to blacklist - Radarr exclusions unchanged")
        
        # STEP 4: Merge (add new, remove deleted)
        merged_ids = radarr_ids  # Use current Radarr state as source of truth
        
        # STEP 5: Create new blacklist structure
        new_blacklist_data = {
            'version': '1.0',
            'exported_at': datetime.utcnow().isoformat() + 'Z',
            'source': 'radarr',
            'movies': sorted(list(merged_ids)),
            'tv': sorted(list(existing_tv_ids))  # Preserve existing TV blacklist
        }
        
        # STEP 6: Validate JSON can be serialized
        try:
            json_str = json.dumps(new_blacklist_data, indent=2)
        except Exception as e:
            logger.error(f"Failed to serialize blacklist to JSON: {e}")
            return False
        
        # STEP 7: Create backup before writing
        if blacklist_path.exists():
            backup_path = f"{blacklist_file}.backup"
            shutil.copy2(blacklist_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
        
        # STEP 8: Atomic write (write to temp file, then rename)
        temp_path = Path(f"{blacklist_file}.tmp")
        try:
            # Write to temp file
            with open(temp_path, 'w') as f:
                f.write(json_str)
            
            # Validate temp file
            with open(temp_path, 'r') as f:
                validated_data = json.load(f)
            
            # Atomic rename
            temp_path.replace(blacklist_path)
            
            logger.info(f"✅ Saved {len(merged_ids)} movies, {len(existing_tv_ids)} TV shows to {blacklist_file}")
            logger.info(f"   Changes: +{len(new_ids)} new, -{len(removed_ids)} removed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write blacklist file: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            return False
        
    except Exception as e:
        logger.error(f"Failed to sync Radarr blacklist: {e}")
        return False


if __name__ == '__main__':
    # For standalone execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    success = sync_radarr_blacklist()
    exit(0 if success else 1)
