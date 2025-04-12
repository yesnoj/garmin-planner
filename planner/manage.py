"""
Management of scheduled workouts in Garmin Connect.

This module provides functions to list and manage scheduled workouts
in the Garmin Connect calendar.
"""

import logging
import re
import datetime
import calendar
import yaml
from planner.garmin_client import GarminClient

def cmd_list_scheduled(args):
    """
    List scheduled workouts from Garmin Connect calendar.
    
    Args:
        args: Command line arguments with the following attributes:
            - start_date: Optional start date to look for workouts
            - end_date: Optional end date to look for workouts
            - date_range: Optional predefined date range (TODAY, TOMORROW, etc.)
            - name_filter: Optional regex to filter workout names
            - oauth_folder: Path to the OAuth folder
    """
    workouts = get_scheduled(args)
    print(workouts)

def get_scheduled(args):
    """
    Get scheduled workouts from Garmin Connect calendar.
    
    Args:
        args: Command line arguments with the following attributes:
            - start_date: Optional start date to look for workouts
            - end_date: Optional end date to look for workouts
            - date_range: Optional predefined date range (TODAY, TOMORROW, etc.)
            - name_filter: Optional regex to filter workout names
            - oauth_folder: Path to the OAuth folder
            
    Returns:
        List of scheduled workout data
    """
    # Determine date range
    start_date, end_date = determine_date_range(args)
    
    # Get workouts from calendar
    client = GarminClient(args.oauth_folder)
    matching_workouts = find_scheduled_workouts(client, start_date, end_date, args.name_filter)
    
    return matching_workouts

def determine_date_range(args):
    """
    Determine the date range for looking up scheduled workouts.
    
    Args:
        args: Command line arguments with date range information
        
    Returns:
        Tuple of (start_date, end_date) as datetime.date objects
    """
    start_date = datetime.datetime.today().date()
    end_date = None
    
    # Explicit start date provided
    if args.start_date:
        try:
            start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d').date()
        except ValueError:
            logging.error(f"Invalid start date format: {args.start_date}. Using today instead.")

    # Explicit end date provided
    if args.end_date:
        try:
            end_date = datetime.datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            logging.error(f"Invalid end date format: {args.end_date}. Using no end date instead.")

    # Use predefined date range if specified
    if args.date_range:
        date_range = args.date_range.upper()
        today = datetime.datetime.today().date()
        
        if date_range == 'TODAY':
            start_date = end_date = today
        elif date_range == 'TOMORROW':
            start_date = end_date = today + datetime.timedelta(days=1)
        elif date_range == 'CURRENT-WEEK':
            # Monday of current week
            start_date = today - datetime.timedelta(days=today.weekday())
            # Sunday of current week
            end_date = start_date + datetime.timedelta(days=6)
        elif date_range == 'NEXT-WEEK':
            # Monday of next week
            start_date = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=7)
            # Sunday of next week
            end_date = start_date + datetime.timedelta(days=6)
        elif date_range == 'CURRENT-MONTH':
            # First day of current month
            start_date = today.replace(day=1)
            # Last day of current month
            last_day = calendar.monthrange(today.year, today.month)[1]
            end_date = today.replace(day=last_day)
        else:
            logging.warning(f'Invalid date range: {args.date_range}')
    
    return start_date, end_date

def find_scheduled_workouts(client, start_date, end_date, name_filter=None):
    """
    Find scheduled workouts in Garmin Connect calendar.
    
    Args:
        client: GarminClient instance
        start_date: Start date to look for workouts
        end_date: End date to look for workouts (or None for no end date)
        name_filter: Optional regex to filter workout names
        
    Returns:
        List of matching workout data
    """
    matching_workouts = []
    workouts_by_date = {}  # Dictionary to track workouts by date (to avoid duplicates)
    
    search_year = start_date.year
    search_month = start_date.month
    
    # Maximum number of months to search (to avoid infinite loop)
    max_months = 12
    months_searched = 0
    
    while months_searched < max_months:
        response = client.get_calendar(search_year, search_month)
        found_workouts = 0
        calendar_items = response.get('calendarItems', [])
        
        for item in calendar_items:
            if item.get('itemType', '') == 'workout':
                workout_name = item.get('title', '')
                workout_id = item.get('workoutId', None)
                schedule_id = item.get('id', None)
                schedule_date = item.get('date', None)
                
                if not schedule_date:
                    continue
                
                # Filter by name if specified
                if name_filter and not re.search(name_filter, workout_name):
                    logging.debug(f'Workout name does not match [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                    continue
                        
                # Parse date for comparison
                try:
                    date_cmp = datetime.datetime.strptime(schedule_date, '%Y-%m-%d').date()
                except ValueError:
                    logging.warning(f"Invalid date format in calendar: {schedule_date}. Skipping.")
                    continue
                
                # Check date bounds
                if date_cmp < start_date or (end_date and date_cmp > end_date):
                    logging.debug(f'Date out of bounds for workout [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                else:
                    # Check if we already have a workout for this date (avoid duplicates)
                    if schedule_date in workouts_by_date:
                        logging.debug(f'Ignoring duplicate workout [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                    else:
                        logging.debug(f'Found scheduled workout [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                        workouts_by_date[schedule_date] = item
                        matching_workouts.append(item)
                        found_workouts += 1

        # Stop searching if:
        # 1. No end date specified and no workouts found in the latest iteration (likely reached end of calendar)
        # 2. End date specified and we've searched past it
        if (not end_date and found_workouts == 0) or \
           (end_date and datetime.date(year=search_year, month=search_month, day=1) > end_date):
            break
        
        # Move to the next month
        search_month += 1
        if search_month > 12:
            search_year += 1
            search_month = 1
        
        months_searched += 1
    
    # Sort the workouts by date
    matching_workouts.sort(key=lambda x: x.get('date', ''))
    
    return matching_workouts

def dist_to_time(wo_part):
    """
    Convert distance-based workouts to time-based workouts recursively.
    
    Args:
        wo_part: Workout part to convert (can be dict, list, or other)
        
    Returns:
        None (modifies wo_part in place)
    """
    if isinstance(wo_part, list):
        for wo_item in wo_part:
            dist_to_time(wo_item)
    elif isinstance(wo_part, dict):
        # We found an end condition to check
        if 'endCondition' in wo_part and wo_part['endCondition']['conditionTypeKey'] == 'distance':
            target_pace_ms = None
            if 'targetType' in wo_part and wo_part['targetType']['workoutTargetTypeKey'] == 'pace.zone':
                # Calculate average pace
                if 'targetValueOne' in wo_part and 'targetValueTwo' in wo_part:
                    target_pace_ms = (wo_part['targetValueOne'] + wo_part['targetValueTwo']) / 2
                    
                    # Convert distance to time
                    end_condition_sec = wo_part['endConditionValue'] / target_pace_ms
                    # Round to nearest 10 seconds
                    end_condition_sec = int(round(end_condition_sec/10, 0) * 10)
                    
                    # Update end condition
                    wo_part['endConditionValue'] = float(end_condition_sec)
                    wo_part['endCondition']['conditionTypeKey'] = 'time'
                    wo_part['endCondition']['conditionTypeId'] = 2
                    wo_part['endCondition']['displayOrder'] = 2
                    wo_part.pop('preferredEndConditionUnit', None)
        
        # Continue looking at nested structures
        for k, v in wo_part.items():
            if isinstance(v, list) or isinstance(v, dict):
                dist_to_time(v)