"""
Blocklist Manager for List-Sync
--------------------------------
Manages loading and checking blocklist to prevent requesting blocked media.

This module:
1. Loads blocklist from JSON file exported by Seerr
2. Caches blocklist in memory for fast lookups
3. Provides is_blocked() check for media items
4. Handles graceful fallback if blocklist is missing

Environment Variables:
    BLOCKLIST_ENABLED: Enable/disable blocklist (default: true)
    BLOCKLIST_FILE: Path to blacklist JSON (default: data/blacklist.json)
    BLOCKLIST_RELOAD_HOURS: Hours before reloading (default: 24)
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
        enabled: Optional[bool] = None,
        reload_hours: int = 24
    ):
        """
        Initialize blocklist manager.
        
        Args:
            blocklist_path: Path to blocklist JSON file
            enabled: Enable/disable blocklist checking
            reload_hours: Hours before auto-reloading blocklist
        """
        # Configuration
        self.blocklist_path = Path(
            blocklist_path or 
            os.getenv('BLOCKLIST_FILE', 'data/blacklist.json')  # Changed to blacklist.json to match Radarr sync script
        )
        self.enabled = (
            enabled if enabled is not None
            else os.getenv('BLOCKLIST_ENABLED', 'true').lower() == 'true'
        )
        self.reload_hours = reload_hours
        
        # State
        self.movie_blocklist: Set[int] = set()
        self.tv_blocklist: Set[int] = set()
        self.loaded_at: Optional[datetime] = None
        self.version: Optional[str] = None
        self.source: Optional[str] = None
        self.total_count: int = 0
        
        logger.info(f"BlocklistManager initialized (enabled={self.enabled}, path={self.blocklist_path})")
    
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
            self.total_count = len(self.movie_blocklist) + len(self.tv_blocklist)
            
            # Log success
            exported_at = data.get('exported_at', 'unknown')
            logger.info(f"✅ Loaded blocklist from {self.blocklist_path}")
            logger.info(f"   Version: {self.version}, Source: {self.source}")
            logger.info(f"   Exported: {exported_at}")
            logger.info(f"   Movies: {len(self.movie_blocklist)}, TV: {len(self.tv_blocklist)}, Total: {self.total_count}")
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse blocklist JSON: {e}")
            logger.warning("Continuing without blocklist - all items will be processed")
            return False
        except Exception as e:
            logger.error(f"Failed to load blocklist: {e}")
            logger.warning("Continuing without blocklist - all items will be processed")
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
                logger.debug("TMDB_KEY not configured, cannot check documentary genre")
                return False
            
            # Query TMDB for genres
            url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}"
            params = {'api_key': tmdb_key}
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                genres = data.get('genres', [])
                
                # Documentary genre ID: 99 for movies, 99 for TV as well
                is_doc = any(g.get('id') == 99 for g in genres)
                
                if is_doc:
                    logger.info(f"🎬 Documentary detected: {data.get('title', data.get('name', 'Unknown'))} (TMDB: {tmdb_id})")
                
                return is_doc
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking documentary genre: {e}")
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
                return True
        elif media_type == 'tv':
            if tmdb_id in self.tv_blocklist:
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
            'total_count': self.total_count,
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


def get_blocklist_stats() -> Dict[str, Any]:
    """
    Get blocklist statistics using global manager.
    
    Returns:
        Dictionary with stats
    """
    manager = get_blocklist_manager()
    return manager.get_stats()

