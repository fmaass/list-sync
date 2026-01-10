#!/usr/bin/env python3
"""
Sync declined requests from Seerr to local database.
This should be run periodically to detect movies that were declined in Seerr.
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
    Check Seerr for declined requests and mark them in local database.
    
    In Seerr, when a request is declined, it's removed from the requests list.
    We need to compare our database against Seerr to find what's missing.
    
    Note: This is a basic implementation. A more robust solution would:
    1. Use Seerr webhooks to get real-time decline notifications
    2. Store request IDs to track lifecycle
    """
    # Load config
    overseerr_url = os.getenv('OVERSEERR_URL')
    api_key = os.getenv('OVERSEERR_API_KEY')
    
    if not overseerr_url or not api_key:
        config = load_env_config()
        if not config or not config[0] or not config[1]:
            logger.error("Overseerr not configured")
            return
        overseerr_url, api_key = config[0], config[1]
    
    client = OverseerrClient(overseerr_url, api_key)
    
    # TODO: Implement declined request detection
    # This requires either:
    # 1. Seerr webhook integration (preferred)
    # 2. Tracking request IDs and checking if they disappeared
    # 3. Manual API endpoint if Seerr provides one
    
    logger.info("Declined request sync not yet implemented")
    logger.info("For now, use the web UI to manage declined requests")

if __name__ == '__main__':
    sync_declined_requests()
