#!/usr/bin/env python3
"""
Sync declined requests from Seerr to local database.
This should be run periodically (or before each sync) to detect movies that were declined in Seerr.
"""
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from list_sync.config import load_env_config
from list_sync.api.overseerr import OverseerrClient
from list_sync.database import mark_request_declined, is_request_declined

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sync_declined_requests():
    """
    Check Seerr for declined requests (status=3) and mark them in local database.
    This prevents re-requesting movies that were manually declined.
    """
    # Load config
    overseerr_url = os.getenv('OVERSEERR_URL')
    api_key = os.getenv('OVERSEERR_API_KEY')
    
    if not overseerr_url or not api_key:
        config = load_env_config()
        if not config or not config[0] or not config[1]:
            logger.error("Overseerr not configured")
            return 0
        overseerr_url, api_key = config[0], config[1]
    
    client = OverseerrClient(overseerr_url, api_key)
    
    # Get declined requests from Seerr (status=3)
    logger.info("Fetching declined requests from Seerr...")
    declined_requests = client.get_declined_requests(limit=500)
    
    if not declined_requests:
        logger.info("No declined requests found in Seerr")
        return 0
    
    logger.info(f"Found {len(declined_requests)} declined requests in Seerr")
    
    # Mark them in local database
    new_count = 0
    for req in declined_requests:
        tmdb_id = req.get('tmdb_id')
        if not tmdb_id:
            continue
        
        # Check if already marked
        if not is_request_declined(str(tmdb_id), req.get('media_type', 'movie')):
            mark_request_declined(
                tmdb_id=str(tmdb_id),
                media_type=req.get('media_type', 'movie'),
                title=req.get('title'),
                year=req.get('year'),
                declined_by_user_id=req.get('requested_by_id'),
                reason='Declined in Seerr'
            )
            new_count += 1
            logger.info(f"  Marked as declined: {req.get('title')} ({req.get('year')})")
    
    logger.info(f"✅ Synced {new_count} new declined requests to database")
    return new_count

if __name__ == '__main__':
    count = sync_declined_requests()
    sys.exit(0 if count >= 0 else 1)
