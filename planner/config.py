"""
Configuration module for Garmin Planner.

This module provides centralized access to configuration settings
used throughout the Garmin Planner application.
"""

import os
import json
import logging
from pathlib import Path

class Config:
    """Configuration manager for Garmin Planner."""
    
    # Default values
    _defaults = {
        'oauth_folder': '~/.garth',
        'cache_dir': '~/.garmin_planner/cache',
        'training_plans_dir': '~/.garmin_planner/training_plans',
        'max_retries': 3,
        'timeout': 30,
        'default_format': 'YAML'
    }
    
    # Singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of Config."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize with default configuration."""
        self._config = self._defaults.copy()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file if it exists."""
        config_file = self._get_config_file_path()
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    self._config.update(loaded_config)
                logging.debug(f"Loaded configuration from {config_file}")
            except Exception as e:
                logging.warning(f"Error loading configuration file {config_file}: {e}")
    
    def save(self):
        """Save the current configuration to file."""
        config_file = self._get_config_file_path()
        config_dir = os.path.dirname(config_file)
        
        # Create the directory if it doesn't exist
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
            except Exception as e:
                logging.error(f"Failed to create config directory {config_dir}: {e}")
                return False
        
        try:
            with open(config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            logging.debug(f"Saved configuration to {config_file}")
            return True
        except Exception as e:
            logging.error(f"Failed to save configuration to {config_file}: {e}")
            return False
    
    def _get_config_file_path(self):
        """Get the path to the configuration file."""
        config_dir = os.path.expanduser('~/.garmin_planner')
        return os.path.join(config_dir, 'config.json')
    
    def get(self, key, default=None):
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if the key is not found
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)
    
    def set(self, key, value):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        self._config[key] = value
        return self.save()
    
    def get_oauth_folder(self):
        """Get the OAuth folder path, expanding ~ if needed."""
        return os.path.expanduser(self._config.get('oauth_folder', self._defaults['oauth_folder']))
    
    def get_cache_dir(self):
        """Get the cache directory path, expanding ~ if needed."""
        cache_dir = os.path.expanduser(self._config.get('cache_dir', self._defaults['cache_dir']))
        
        # Create the directory if it doesn't exist
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir, exist_ok=True)
                logging.debug(f"Created cache directory: {cache_dir}")
            except Exception as e:
                logging.warning(f"Failed to create cache directory {cache_dir}: {e}")
        
        return cache_dir
    
    def get_training_plans_dir(self):
        """Get the training plans directory path, expanding ~ if needed."""
        return os.path.expanduser(self._config.get('training_plans_dir', self._defaults['training_plans_dir']))
    
    def get_workouts_cache_file(self):
        """Get the path to the workouts cache file."""
        return os.path.join(self.get_cache_dir(), 'workouts_cache.json')
    
    def get_max_retries(self):
        """Get the maximum number of API retries."""
        return self._config.get('max_retries', self._defaults['max_retries'])
    
    def get_timeout(self):
        """Get the API timeout in seconds."""
        return self._config.get('timeout', self._defaults['timeout'])

# Global function to get the configuration instance
def get_config():
    """Get the configuration instance."""
    return Config.get_instance()