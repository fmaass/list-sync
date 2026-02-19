"""
Blocklist Manager for List-Sync
--------------------------------
Manages loading and checking blocklist to prevent requesting blocked media.

This module:
1. Loads blocklist from JSON file exported by Seerr / synced from Radarr exclusions
2. Loads optional permanent manual blocklist (survives Radarr sync refreshes)
3. Caches blocklist in memory for fast lookups
4. Provides is_blocked() check for media items
5. Handles graceful fallback if blocklist is missing

Environment Variables:
    BLOCKLIST_ENABLED: Enable/disable blocklist (default: true)
    BLOCKLIST_FILE: Path to blocklist JSON (default: data/blocklist.json)
    MANUAL_BLOCKLIST_FILE: Path to manual/permanent blocklist JSON (default: data/manual_blocklist.json)
    BLOCKLIST_RELOAD_HOURS: Hours before reloading (default: 24)
    BLOCK_DOCUMENTARIES: Block documentary genre via TMDB API (default: false)
    TMDB_KEY: TMDB API key (required for BLOCK_DOCUMENTARIES)
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Set, Optional, Dict, Any

logger = logging.getLogger(__name__)


class BlocklistManager:
    """Manages blocklist loading and checking for list-sync"""
    
    def __init__(
        self,
        blocklist_path: Optional[str] = None,
        manual_blocklist_path: Optional[str] = None,
        enabled: Optional[bool] = None,
        reload_hours: int = 24
    ):
        """
        Initialize blocklist manager.
        
        Args:
            blocklist_path: Path to blocklist JSON file (synced from Radarr)
            manual_blocklist_path: Path to manual/permanent blocklist JSON
            enabled: Enable/disable blocklist checking
            reload_hours: Hours before auto-reloading blocklist
        """
        # Configuration
        self.blocklist_path = Path(
            blocklist_path or 
            os.getenv('BLOCKLIST_FILE', 'data/blocklist.json')
        )
        self.manual_blocklist_path = Path(
            manual_blocklist_path or
            os.getenv('MANUAL_BLOCKLIST_FILE', 'data/manual_blocklist.json')
        )
        self.enabled = (
            enabled if enabled is not None
            else os.getenv('BLOCKLIST_ENABLED', 'true').lower() == 'true'
        )
        self.reload_hours = reload_hours
        
        # State
        self.movie_blocklist: Set[int] = set()
        self.tv_blocklist: Set[int] = set()
        # Manual blocklist items (kept separate so Radarr refresh doesn't overwrite them)
        self.manual_movie_blocklist: Set[int] = set()
        self.manual_tv_blocklist: Set[int] = set()
        self.loaded_at: Optional[datetime] = None
        self.version: Optional[str] = None
        self.source: Optional[str] = None
        self.total_count: int = 0
        
        logger.info(f"BlocklistManager initialized (enabled={self.enabled}, path={self.blocklist_path})")
        if self.manual_blocklist_path.exists():
            logger.info(f"Manual blocklist found: {self.manual_blocklist_path}")
    
    def load(self, force: bool = False) -> bool:
        """
        Load blocklist from JSON file.
        
        Args:
            force: Force reload even if recently loaded
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.enabled:
            logger.info("Blocklist is disabled, skipping load")
            return False
        
        # Check if reload is needed
        if not force and self.loaded_at and not self.should_reload():
            logger.debug(f"Blocklist still fresh (loaded {self._age_str()} ago)")
            return True
        
        try:
            # Ensure blocklist_path is a Path object
            if not isinstance(self.blocklist_path, Path):
                self.blocklist_path = Path(self.blocklist_path)
            
            if not self.blocklist_path.exists():
                logger.warning(f"Blocklist file not found: {self.blocklist_path}")
                logger.warning("Continuing without blocklist - all items will be processed")
                return False
            
            # Load JSON file
            with open(self.blocklist_path, 'r') as f:
                data = json.load(f)
            
            # Validate format
            if not isinstance(data, dict):
                logger.error(f"Invalid blocklist format: expected dict, got {type(data)}")
                return False
            
            # Extract data
            self.movie_blocklist = set(data.get('movies', []))
            self.tv_blocklist = set(data.get('tv', []))
            self.loaded_at = datetime.now()
            self.version = data.get('version', 'unknown')
            self.source = data.get('source', 'unknown')
            
            # Log success
            exported_at = data.get('exported_at', 'unknown')
            logger.info(f"✅ Loaded blocklist from {self.blocklist_path}")
            logger.info(f"   Version: {self.version}, Source: {self.source}")
            logger.info(f"   Exported: {exported_at}")
            logger.info(f"   Movies: {len(self.movie_blocklist)}, TV: {len(self.tv_blocklist)}")
            
            # Load manual blocklist (permanent items that survive Radarr refresh)
            self._load_manual_blocklist()
            
            self.total_count = (
                len(self.movie_blocklist) + len(self.tv_blocklist) +
                len(self.manual_movie_blocklist) + len(self.manual_tv_blocklist)
            )
            logger.info(f"   Total (incl. manual): {self.total_count}")
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse blocklist JSON: {e}")
            logger.warning("Continuing without blocklist - all items will be processed")
            return False
        except Exception as e:
            logger.error(f"Failed to load blocklist: {e}")
            logger.warning("Continuing without blocklist - all items will be processed")
            return False
    
    def _load_manual_blocklist(self) -> bool:
        """
        Load the manual/permanent blocklist.
        
        This is a separate file from the Radarr-synced blocklist, so items added
        here won't be overwritten when the Radarr blocklist is refreshed.
        
        Format: {"movies": [tmdb_id, ...], "tv": [tmdb_id, ...]}
        
        Returns:
            True if loaded successfully
        """
        try:
            if not isinstance(self.manual_blocklist_path, Path):
                self.manual_blocklist_path = Path(self.manual_blocklist_path)
            
            if not self.manual_blocklist_path.exists():
                logger.debug(f"No manual blocklist at {self.manual_blocklist_path}")
                return False
            
            with open(self.manual_blocklist_path, 'r') as f:
                data = json.load(f)
            
            self.manual_movie_blocklist = set(data.get('movies', []))
            self.manual_tv_blocklist = set(data.get('tv', []))
            
            total = len(self.manual_movie_blocklist) + len(self.manual_tv_blocklist)
            if total > 0:
                logger.info(f"✅ Loaded manual blocklist: {len(self.manual_movie_blocklist)} movies, {len(self.manual_tv_blocklist)} TV")
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load manual blocklist: {e}")
            return False
    
    def is_documentary(self, tmdb_id: int, media_type: str) -> bool:
        """
        Check if item is a documentary using TMDB API.
        
        Args:
            tmdb_id: TMDB ID of the item
            media_type: 'movie' or 'tv'
            
        Returns:
            True if item is a documentary
        """
        # Only check if feature is enabled
        block_docs = os.getenv('BLOCK_DOCUMENTARIES', 'false').lower() == 'true'
        if not block_docs:
            return False
        
        try:
            import requests
            
            # Get TMDB API key from environment
            tmdb_key = os.getenv('TMDB_KEY', '')
            if not tmdb_key:
                logger.warning(
                    "BLOCK_DOCUMENTARIES is enabled but TMDB_KEY is not set! "
                    "Documentary filtering will not work without a TMDB API key."
                )
                return False
            
            # Query TMDB for genres
            url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}"
            params = {'api_key': tmdb_key}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                genres = data.get('genres', [])
                genre_names = [g.get('name', '') for g in genres]
                title = data.get('title', data.get('name', 'Unknown'))
                
                # Documentary genre ID: 99 for movies, 99 for TV as well
                is_doc = any(g.get('id') == 99 for g in genres)
                
                if is_doc:
                    logger.info(f"🎬 Documentary detected and BLOCKED: '{title}' (TMDB: {tmdb_id}, genres: {genre_names})")
                else:
                    logger.debug(f"Not a documentary: '{title}' (TMDB: {tmdb_id}, genres: {genre_names})")
                
                return is_doc
            
            elif response.status_code == 401:
                logger.error(f"TMDB API key is invalid (401 Unauthorized). Documentary filtering disabled.")
                return False
            else:
                logger.warning(f"TMDB API returned {response.status_code} for {media_type}/{tmdb_id}")
                return False
            
        except requests.Timeout:
            logger.warning(f"TMDB API timeout checking documentary genre for {media_type}/{tmdb_id}")
            return False
        except Exception as e:
            logger.warning(f"Error checking documentary genre for {media_type}/{tmdb_id}: {e}")
            return False
    
    def is_blocked(self, tmdb_id: int, media_type: str) -> bool:
        """
        Check if item is blocked (Radarr blocklist + optional documentary filter).
        
        Args:
            tmdb_id: TMDB ID of the item
            media_type: 'movie' or 'tv'
            
        Returns:
            True if item is blocked, False otherwise
        """
        if not self.enabled:
            return False
        
        if not self.loaded_at:
            # Try to load if not loaded yet
            self.load()
            if not self.loaded_at:
                # Still no blocklist, allow everything (but still check documentary filter)
                return self.is_documentary(tmdb_id, media_type)
        
        # Auto-reload if stale
        if self.should_reload():
            logger.info("Blocklist is stale, reloading...")
            self.load(force=True)
        
        # Check Radarr exclusion blocklist
        if media_type == 'movie':
            if tmdb_id in self.movie_blocklist:
                logger.debug(f"Blocked by Radarr exclusions: TMDB {tmdb_id}")
                return True
            if tmdb_id in self.manual_movie_blocklist:
                logger.debug(f"Blocked by manual blocklist: TMDB {tmdb_id}")
                return True
        elif media_type == 'tv':
            if tmdb_id in self.tv_blocklist:
                logger.debug(f"Blocked by Radarr exclusions: TMDB {tmdb_id}")
                return True
            if tmdb_id in self.manual_tv_blocklist:
                logger.debug(f"Blocked by manual blocklist: TMDB {tmdb_id}")
                return True
        
        # Check documentary filter (if enabled)
        if self.is_documentary(tmdb_id, media_type):
            return True
        
        return False
    
    def should_reload(self) -> bool:
        """
        Check if blocklist should be reloaded.
        
        Returns:
            True if blocklist is stale and should be reloaded
        """
        if not self.loaded_at:
            return True
        
        age = datetime.now() - self.loaded_at
        max_age = timedelta(hours=self.reload_hours)
        
        return age > max_age
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get blocklist statistics.
        
        Returns:
            Dictionary with blocklist stats
        """
        # Ensure blocklist_path is a Path object
        if not isinstance(self.blocklist_path, Path):
            self.blocklist_path = Path(self.blocklist_path)
        
        # Ensure paths are Path objects
        if not isinstance(self.manual_blocklist_path, Path):
            self.manual_blocklist_path = Path(self.manual_blocklist_path)
        
        return {
            'enabled': self.enabled,
            'loaded': self.loaded_at is not None,
            'loaded_at': self.loaded_at.isoformat() if self.loaded_at else None,
            'age_hours': round(self._age_hours(), 2) if self.loaded_at else None,
            'file_path': str(self.blocklist_path),
            'file_exists': self.blocklist_path.exists(),
            'version': self.version,
            'source': self.source,
            'movie_count': len(self.movie_blocklist),
            'tv_count': len(self.tv_blocklist),
            'manual_movie_count': len(self.manual_movie_blocklist),
            'manual_tv_count': len(self.manual_tv_blocklist),
            'manual_blocklist_path': str(self.manual_blocklist_path),
            'manual_blocklist_exists': self.manual_blocklist_path.exists(),
            'total_count': self.total_count,
            'block_documentaries': os.getenv('BLOCK_DOCUMENTARIES', 'false').lower() == 'true',
            'tmdb_key_set': bool(os.getenv('TMDB_KEY', '')),
            'reload_hours': self.reload_hours,
            'should_reload': self.should_reload()
        }
    
    def _age_hours(self) -> float:
        """Get age of blocklist in hours"""
        if not self.loaded_at:
            return 0.0
        age = datetime.now() - self.loaded_at
        return age.total_seconds() / 3600
    
    def _age_str(self) -> str:
        """Get human-readable age string"""
        if not self.loaded_at:
            return "never loaded"
        
        hours = self._age_hours()
        if hours < 1:
            minutes = int(hours * 60)
            return f"{minutes} min"
        elif hours < 24:
            return f"{int(hours)} hours"
        else:
            days = int(hours / 24)
            return f"{days} days"
    
    def refresh_from_radarr(self) -> bool:
        """
        Fetch current exclusions from Radarr API and update the blocklist JSON file.
        This ensures the blocklist is always in sync with Radarr's exclusion list.
        
        Requires RADARR_URL and RADARR_API_KEY environment variables.
        
        Returns:
            True if refreshed successfully, False otherwise
        """
        radarr_url = os.getenv('RADARR_URL', '').rstrip('/')
        radarr_api_key = os.getenv('RADARR_API_KEY', '')
        
        if not radarr_url or not radarr_api_key:
            logger.debug("RADARR_URL or RADARR_API_KEY not set, skipping Radarr refresh")
            return False
        
        try:
            import requests
            from datetime import datetime as dt
            
            url = f"{radarr_url}/api/v3/exclusions"
            logger.info(f"Refreshing blocklist from Radarr ({url})")
            
            resp = requests.get(
                url,
                headers={'X-Api-Key': radarr_api_key},
                timeout=30
            )
            resp.raise_for_status()
            exclusions = resp.json()
            
            # Extract TMDB IDs
            movie_ids = sorted(set(
                item['tmdbId'] for item in exclusions if 'tmdbId' in item
            ))
            
            # Build output
            output = {
                'version': '1.0',
                'exported_at': dt.utcnow().isoformat() + 'Z',
                'source': 'radarr',
                'movies': movie_ids,
                'tv': [],
            }
            
            # Write to file
            with open(self.blocklist_path, 'w') as f:
                json.dump(output, f, indent=2)
            
            old_count = len(self.movie_blocklist)
            
            # Reload in memory
            self.load(force=True)
            
            new_count = len(self.movie_blocklist)
            if new_count != old_count:
                logger.info(f"Blocklist updated from Radarr: {old_count} → {new_count} movies")
            else:
                logger.info(f"Blocklist refreshed from Radarr: {new_count} movies (no changes)")
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to refresh blocklist from Radarr: {e}")
            logger.warning("Continuing with existing blocklist")
            return False

    def refresh_from_seerr(self) -> bool:
        """
        Fetch blocklist from Seerr API and update the blocklist JSON file.
        Seerr is the single source of truth — it aggregates Radarr exclusions,
        Sonarr exclusions, and manual blocks.
        
        Uses OVERSEERR_URL and OVERSEERR_API_KEY environment variables
        (already configured for ListSync's normal operation).
        
        Returns:
            True if refreshed successfully, False otherwise
        """
        seerr_url = os.getenv('OVERSEERR_URL', '').rstrip('/')
        seerr_api_key = os.getenv('OVERSEERR_API_KEY', '')
        
        if not seerr_url or not seerr_api_key:
            logger.debug("OVERSEERR_URL or OVERSEERR_API_KEY not set, skipping Seerr refresh")
            return False
        
        try:
            import requests
            from datetime import datetime as dt
            
            url = f"{seerr_url}/api/v1/blocklist"
            logger.info(f"Refreshing blocklist from Seerr ({url})")
            
            resp = requests.get(
                url,
                headers={'X-Api-Key': seerr_api_key},
                params={'take': 10000, 'skip': 0, 'filter': 'all'},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            
            results = data.get('results', [])
            
            movie_ids = sorted(set(
                item['tmdbId'] for item in results
                if item.get('mediaType') == 'movie' and 'tmdbId' in item
            ))
            tv_ids = sorted(set(
                item['tmdbId'] for item in results
                if item.get('mediaType') == 'tv' and 'tmdbId' in item
            ))
            
            output = {
                'version': '1.0',
                'exported_at': dt.utcnow().isoformat() + 'Z',
                'source': 'seerr',
                'movies': movie_ids,
                'tv': tv_ids,
            }
            
            with open(self.blocklist_path, 'w') as f:
                json.dump(output, f, indent=2)
            
            old_movie_count = len(self.movie_blocklist)
            old_tv_count = len(self.tv_blocklist)
            
            self.load(force=True)
            
            new_movie_count = len(self.movie_blocklist)
            new_tv_count = len(self.tv_blocklist)
            
            logger.info(
                f"Blocklist refreshed from Seerr: "
                f"{new_movie_count} movies (was {old_movie_count}), "
                f"{new_tv_count} TV (was {old_tv_count})"
            )
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to refresh blocklist from Seerr: {e}")
            logger.warning("Continuing with existing blocklist")
            return False

    def reload(self) -> bool:
        """
        Force reload blocklist from file.
        
        Returns:
            True if reloaded successfully
        """
        return self.load(force=True)
    
    def disable(self):
        """Disable blocklist checking"""
        self.enabled = False
        logger.info("Blocklist disabled")
    
    def enable(self):
        """Enable blocklist checking"""
        self.enabled = True
        logger.info("Blocklist enabled")
        # Try to load if not already loaded
        if not self.loaded_at:
            self.load()


# Global instance (singleton pattern)
_blocklist_manager: Optional[BlocklistManager] = None


def get_blocklist_manager() -> BlocklistManager:
    """
    Get global blocklist manager instance.
    
    Returns:
        BlocklistManager instance
    """
    global _blocklist_manager
    if _blocklist_manager is None:
        _blocklist_manager = BlocklistManager()
    return _blocklist_manager


def load_blocklist() -> bool:
    """
    Load blocklist using global manager.
    
    Returns:
        True if loaded successfully
    """
    manager = get_blocklist_manager()
    return manager.load()


def is_blocked(tmdb_id: int, media_type: str) -> bool:
    """
    Check if item is blocked using global manager.
    
    Args:
        tmdb_id: TMDB ID of the item
        media_type: 'movie' or 'tv'
        
    Returns:
        True if item is blocked
    """
    manager = get_blocklist_manager()
    return manager.is_blocked(tmdb_id, media_type)


def refresh_blocklist_from_radarr() -> bool:
    """
    Refresh blocklist from Radarr API using global manager.
    Deprecated: use refresh_blocklist_from_seerr() instead.
    
    Returns:
        True if refreshed successfully
    """
    manager = get_blocklist_manager()
    return manager.refresh_from_radarr()


def refresh_blocklist_from_seerr() -> bool:
    """
    Refresh blocklist from Seerr API using global manager.
    Seerr is the single source of truth for all blocklists.
    
    Returns:
        True if refreshed successfully
    """
    manager = get_blocklist_manager()
    return manager.refresh_from_seerr()


def get_blocklist_stats() -> Dict[str, Any]:
    """
    Get blocklist statistics using global manager.
    
    Returns:
        Dictionary with stats
    """
    manager = get_blocklist_manager()
    return manager.get_stats()

