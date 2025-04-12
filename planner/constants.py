"""
Constants module for Garmin Planner.

This module defines constants used throughout the Garmin Planner application.
"""

# Version information
VERSION = '1.1.0'
VERSION_DATE = '2023-04-12'

# Sport types for Garmin Connect API
SPORT_TYPES = {
    "running": 1,
    "cycling": 2,
    "swimming": 5,
    "strength_training": 3,
    "walking": 9,
    "hiking": 10
}

# Step types for Garmin Connect API
STEP_TYPES = {
    "warmup": 1, 
    "cooldown": 2, 
    "interval": 3, 
    "recovery": 4, 
    "rest": 5, 
    "repeat": 6, 
    "other": 7
}

# End conditions for Garmin Connect API
END_CONDITIONS = {
    "lap.button": 1,
    "time": 2,
    "distance": 3,
    "calories": 4,
    "heart.rate": 5,
    "power": 6,
    "iterations": 7,
}

# Target types for Garmin Connect API
TARGET_TYPES = {
    "no.target": 1,
    "power.zone": 2,
    "cadence.zone": 3,
    "heart.rate.zone": 4,
    "speed.zone": 5,
    "pace.zone": 6,  # meters per second
}

# File extensions
YAML_EXTENSIONS = ['.yaml', '.yml']
JSON_EXTENSIONS = ['.json', '.jsn']
EXCEL_EXTENSIONS = ['.xlsx', '.xls']

# Date formats
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# Predefined date ranges
DATE_RANGES = {
    'TODAY': 'today',
    'TOMORROW': 'tomorrow',
    'CURRENT-WEEK': 'current_week',
    'NEXT-WEEK': 'next_week',
    'CURRENT-MONTH': 'current_month'
}

# Day names (for use with calendar module)
DAY_NAMES = [
    'Monday', 
    'Tuesday', 
    'Wednesday', 
    'Thursday', 
    'Friday', 
    'Saturday', 
    'Sunday'
]

# Default distribution of workout days based on number of sessions per week
DEFAULT_WORKOUT_DAYS = {
    1: [2],                  # Wednesday
    2: [1, 4],               # Tuesday, Friday
    3: [1, 3, 5],            # Tuesday, Thursday, Saturday
    4: [1, 3, 5, 6],         # Tuesday, Thursday, Saturday, Sunday
    5: [0, 1, 3, 4, 6],      # Monday, Tuesday, Thursday, Friday, Sunday
    6: [0, 1, 2, 3, 4, 6],   # Monday, Tuesday, Wednesday, Thursday, Friday, Sunday
    7: [0, 1, 2, 3, 4, 5, 6] # All days
}

# Cache related constants
DEFAULT_CACHE_EXPIRATION = 86400  # 24 hours in seconds
WORKOUTS_CACHE_NAME = 'workouts_cache'

# Keys to remove when cleaning workout data for export
CLEAN_KEYS = [
    'author', 
    'createdDate', 
    'ownerId', 
    'shared', 
    'updatedDate'
]