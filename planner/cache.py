"""
Cache management for Garmin Planner.

This module provides functionality for caching data from Garmin Connect
to improve performance and reduce API calls.
"""

import os
import json
import logging
import time
from datetime import datetime

from .config import get_config

# Default cache expiration in seconds (24 hours)
DEFAULT_CACHE_EXPIRATION = 86400

class Cache:
    """Cache manager for Garmin Planner data."""
    
    def __init__(self, cache_name=None, expiration=DEFAULT_CACHE_EXPIRATION):
        """
        Initialize the cache.
        
        Args:
            cache_name: Name of the cache file (optional)
            expiration: Cache expiration time in seconds
        """
        self.config = get_config()
        self.cache_dir = self.config.get_cache_dir()
        self.cache_name = cache_name or 'default_cache'
        self.expiration = expiration
        self.cache_file = os.path.join(self.cache_dir, f"{self.cache_name}.json")
        self.cache_data = self._load_cache()
    
    def _load_cache(self):
        """
        Load cache data from file.
        
        Returns:
            Dictionary containing cache data
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    
                    # Check if cache metadata exists
                    if '_meta' not in cache:
                        cache['_meta'] = {
                            'created': time.time(),
                            'last_updated': time.time()
                        }
                    
                    return cache
            except Exception as e:
                logging.warning(f"Error loading cache file {self.cache_file}: {e}")
        
        # Return empty cache with metadata
        return {
            '_meta': {
                'created': time.time(),
                'last_updated': time.time()
            }
        }
    
    def _save_cache(self):
        """
        Save cache data to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update last updated timestamp
            self.cache_data['_meta']['last_updated'] = time.time()
            
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache_data, f, indent=2)
            return True
        except Exception as e:
            logging.warning(f"Error saving cache file {self.cache_file}: {e}")
            return False
    
    def get(self, key, default=None):
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            default: Default value if the key is not found or expired
            
        Returns:
            Cached value or default
        """
        if key in self.cache_data:
            # Check if the entry has its own expiration time
            entry = self.cache_data[key]
            
            if isinstance(entry, dict) and '_timestamp' in entry:
                timestamp = entry['_timestamp']
                data = entry['data']
                
                # Check if the entry has expired
                if time.time() - timestamp > self.expiration:
                    logging.debug(f"Cache entry {key} has expired.")
                    return default
                
                return data
            else:
                # Legacy cache format without timestamps
                return entry
        
        return default
    
    def set(self, key, value):
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if successful, False otherwise
        """
        # Store with timestamp
        self.cache_data[key] = {
            '_timestamp': time.time(),
            'data': value
        }
        
        return self._save_cache()
    
    def delete(self, key):
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key was deleted, False otherwise
        """
        if key in self.cache_data:
            del self.cache_data[key]
            return self._save_cache()
        
        return False
    
    def clear(self):
        """
        Clear the entire cache.
        
        Returns:
            True if successful, False otherwise
        """
        # Preserve metadata
        meta = self.cache_data.get('_meta', {
            'created': time.time(),
            'last_updated': time.time()
        })
        
        self.cache_data = {'_meta': meta}
        return self._save_cache()
    
    def is_expired(self):
        """
        Check if the cache as a whole has expired.
        
        Returns:
            True if the cache has expired, False otherwise
        """
        last_updated = self.cache_data.get('_meta', {}).get('last_updated', 0)
        return (time.time() - last_updated) > self.expiration
    
    def get_age(self):
        """
        Get the age of the cache in seconds.
        
        Returns:
            Cache age in seconds
        """
        last_updated = self.cache_data.get('_meta', {}).get('last_updated', 0)
        return time.time() - last_updated
    
    def get_age_str(self):
        """
        Get a human-readable string representing the cache age.
        
        Returns:
            String like "2 hours 15 minutes ago"
        """
        age_seconds = self.get_age()
        
        if age_seconds < 60:
            return "just now"
        elif age_seconds < 3600:
            minutes = int(age_seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif age_seconds < 86400:
            hours = int(age_seconds / 3600)
            minutes = int((age_seconds % 3600) / 60)
            if minutes == 0:
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            days = int(age_seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"


# Global workouts cache instance
def get_workouts_cache(expiration=DEFAULT_CACHE_EXPIRATION):
    """
    Get the workouts cache instance.
    
    Args:
        expiration: Cache expiration time in seconds
        
    Returns:
        Cache instance for workouts
    """
    return Cache('workouts_cache', expiration)