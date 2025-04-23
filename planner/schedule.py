"""
Schedule management for Garmin workouts.

This module provides functionality to schedule workouts in a training plan
and manage scheduled workouts on Garmin Connect.
"""

import logging
import re
from datetime import datetime, timedelta

from planner.garmin_client import GarminClient

def cmd_schedule_workouts(args):
    """
    Schedule workouts in Garmin Connect.
    
    Args:
        args: Arguments with the following attributes:
            - oauth_folder: Path to the OAuth folder
            - training_plan: ID of the training plan (usually a prefix)
            - race_day: Date of the race (YYYY-MM-DD)
            - workout_days: Comma-separated list of days (0=Monday, 6=Sunday)
            - start_day: Optional start date for scheduling (YYYY-MM-DD)
            - dry_run: If True, don't actually schedule workouts
            - sport_type: Optional sport type filter 'running' or 'cycling'
    """
    logging.info('Scheduling workouts for training plan ' + args.training_plan)
    
    # Get days of the week for scheduling
    if args.workout_days:
        workout_days = [int(d) for d in args.workout_days.split(',')]
    else:
        # Default scheduling: Tuesday, Thursday, Saturday
        workout_days = [1, 3, 5]
    
    # Get all workouts that match the training plan
    client = GarminClient.get_instance(args.oauth_folder)
    workouts = client.list_workouts()

    # Filter workouts by training plan
    training_plan_filter = args.training_plan.strip()
    
    # Filter by sport type if specified
    sport_type = getattr(args, 'sport_type', None)
    if sport_type:
        logging.info(f"Filtering workouts by sport type: {sport_type}")
    
    matching_workouts = []
    for wo in workouts:
        if training_plan_filter in wo['workoutName']:
            # Check sport type if filter is applied
            if sport_type:
                wo_sport_type = wo.get('sportType', {}).get('sportTypeKey', 'running')
                if wo_sport_type != sport_type:
                    logging.info(f"Skipping workout {wo['workoutName']} with sport type {wo_sport_type}")
                    continue
                
            matching_workouts.append(wo)
    
    logging.info(f'Found {len(matching_workouts)} workouts matching training plan {training_plan_filter}')
    
    # If no workouts match, stop
    if not matching_workouts:
        logging.error(f'No workouts found for training plan {training_plan_filter}')
        return
    
    # Extract week/session information from workout names
    workouts_by_week = {}
    for wo in matching_workouts:
        match = re.search(r'\s*(W\d\d)S(\d\d)\s*', wo['workoutName'])
        if match:
            week_id = match.group(1)
            # Convert to integer for sorting, but keep the original string format
            week_num = int(week_id[1:])
            session_num = int(match.group(2)[1:])
            
            if week_id not in workouts_by_week:
                workouts_by_week[week_id] = {}
            
            workouts_by_week[week_id][session_num] = wo
    
    # If we couldn't extract week/session information, stop
    if not workouts_by_week:
        logging.error(f'Could not extract week/session information from workout names')
        return
    
    # Parse race day
    race_date = datetime.strptime(args.race_day, '%Y-%m-%d').date()
    logging.info(f'Race day: {race_date}')
    
    # Calculate the first day (Monday) of the race week
    race_week_monday = race_date - timedelta(days=race_date.weekday())
    
    # Get start day if provided
    start_date = None
    if args.start_day:
        start_date = datetime.strptime(args.start_day, '%Y-%m-%d').date()
        logging.info(f'Start day: {start_date}')
    
    # Find the maximum week number
    max_week = max([int(w[1:]) for w in workouts_by_week.keys()])
    logging.info(f'Maximum week number: {max_week}')
    
    # Schedule workouts
    scheduled_count = 0
    for week_id, sessions in workouts_by_week.items():
        week_num = int(week_id[1:])
        
        # Calculate the week's Monday date from the race day
        week_offset = max_week - week_num
        week_monday = race_week_monday - timedelta(weeks=week_offset)
        
        logging.info(f'Week {week_id}: Monday = {week_monday}')
        
        # If a start date is provided, skip weeks that start before it
        if start_date and week_monday < start_date:
            logging.info(f'Skipping week {week_id} as it starts before the start date')
            continue
        
        # Plan sessions in this week
        for session_num, workout in sorted(sessions.items()):
            # Determine which day of the week to use for this session
            if (session_num - 1) < len(workout_days):
                day = workout_days[session_num - 1]
            else:
                # If we have more sessions than specified days, rotate through the days
                day = workout_days[(session_num - 1) % len(workout_days)]
            
            # Calculate the actual date
            session_date = week_monday + timedelta(days=day)
            
            # If the calculated date is today or in the past, skip this session
            if session_date <= datetime.now().date():
                logging.info(f'Skipping session {session_num} in week {week_id} as the date {session_date} is today or in the past')
                continue
            
            # Convert date to string for Garmin API
            date_str = session_date.strftime('%Y-%m-%d')
            
            # Schedule the workout
            if not args.dry_run:
                try:
                    logging.info(f'Scheduling workout {workout["workoutName"]} ({workout["workoutId"]}) on {date_str}')
                    client.schedule_workout(workout['workoutId'], date_str)
                    scheduled_count += 1
                except Exception as e:
                    logging.error(f'Error scheduling workout {workout["workoutName"]}: {str(e)}')
            else:
                logging.info(f'SIMULATION: Would schedule workout {workout["workoutName"]} ({workout["workoutId"]}) on {date_str}')
                scheduled_count += 1
    
    logging.info(f'Successfully scheduled {scheduled_count} workouts')
    return scheduled_count


def debug_list_all_scheduled_titles(args):
    """
    Lista tutti i titoli degli allenamenti pianificati per debug.
    
    Args:
        args: Arguments with the following attributes:
            - oauth_folder: Path to the OAuth folder
    """
    # Get current and future workouts (from today onward)
    client = GarminClient.get_instance(args.oauth_folder)
    start_date = datetime.now().strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    
    logging.info(f"DEBUG: Looking for ALL scheduled workouts from {start_date} to {end_date}")
    
    # Get scheduled workouts with the same method used when updating the calendar
    calendar_items = get_scheduled(args)
    
    logging.info(f"DEBUG: Found {len(calendar_items)} total scheduled workouts")
    
    # Log tutti i titoli
    for i, item in enumerate(calendar_items):
        logging.info(f"DEBUG: Item {i+1}: Date={item.get('date', 'N/A')}, Title={item.get('title', 'Unknown')}")
    
    return calendar_items


def cmd_unschedule_workouts(args):
    """
    Unschedule workouts in Garmin Connect.
    
    Args:
        args: Arguments with the following attributes:
            - oauth_folder: Path to the OAuth folder
            - training_plan: ID of the training plan (usually a prefix)
            - start_date: Optional start date for unscheduling (YYYY-MM-DD)
            - dry_run: If True, don't actually unschedule workouts
            - sport_type: Optional sport type filter 'running' or 'cycling'
    """
    logging.info(f"Unscheduling workouts for training plan: {args.training_plan}")
    
    # Get current date or use specified start date
    start_date = datetime.now()
    if hasattr(args, 'start_date') and args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            logging.error(f"Invalid start date format: {args.start_date}. Using today instead.")
    
    # Initialize client
    client = GarminClient.get_instance(args.oauth_folder)
    
    # Start scanning from current month
    search_year = start_date.year
    search_month = start_date.month
    
    # Optional sport type filter
    sport_type = getattr(args, 'sport_type', None)
    
    # Keep track of total deletions
    total_deleted = 0
    
    # Continue searching month by month
    while True:
        logging.info(f"Checking calendar for {search_year}-{search_month:02d}")
        
        # Get calendar data for this month
        response = client.get_calendar(search_year, search_month)
        
        # Get calendar items
        calendar_items = response.get('calendarItems', [])
        
        # Count matching workouts for this month
        found_workouts = 0
        
        # Process each calendar item
        for item in calendar_items:
            # Verify this is a workout
            if item.get('itemType', '') == 'workout':
                workout_name = item.get('title', '')
                workout_id = item.get('workoutId', None)
                schedule_id = item.get('id', None)  # Important: use 'id' not 'calendarItemId'
                schedule_date = item.get('date', None)
                
                # Skip if we don't have essential data
                if not schedule_date or not schedule_id:
                    continue
                
                # Parse date for comparison
                try:
                    date_cmp = datetime.strptime(schedule_date, '%Y-%m-%d')
                except ValueError:
                    logging.warning(f"Invalid date format in calendar: {schedule_date}. Skipping.")
                    continue
                
                # Skip workouts in the past
                if date_cmp.date() < start_date.date():
                    logging.info(f'Ignoring past workout [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                    continue
                
                # Check if workout name matches filter pattern using re.search
                if re.search(args.training_plan, workout_name):
                    # Check sport type if filter is applied
                    if sport_type:
                        item_sport_type = item.get('sportType', {}).get('sportTypeKey', 'running')
                        if item_sport_type != sport_type:
                            logging.info(f"Skipping workout {workout_name} with sport type {item_sport_type}")
                            continue
                    
                    found_workouts += 1
                    
                    # Delete or simulate deletion
                    if not args.dry_run:
                        try:
                            logging.info(f'Unscheduling workout [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                            client.unschedule_workout(schedule_id)  # Important: use unschedule_workout not delete_calendar_item
                            total_deleted += 1
                        except Exception as e:
                            logging.error(f"Error unscheduling workout: {str(e)}")
                    else:
                        logging.info(f'SIMULATION: Would unschedule workout [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                        total_deleted += 1
        
        # If no workouts were found in this month, or we've gone too far ahead, stop searching
        if found_workouts == 0:
            # If we're searching 12 months ahead with no results, it's probably time to stop
            current_month = datetime.now().month
            current_year = datetime.now().year
            months_ahead = (search_year - current_year) * 12 + (search_month - current_month)
            if months_ahead >= 12:
                break
        
        # Continue looking for workouts in the following month
        search_month += 1
        if search_month > 12:
            search_year += 1
            search_month = 1
    
    logging.info(f"Successfully unscheduled {total_deleted} workouts")
    return total_deleted


def get_scheduled(args):
    """
    Get scheduled workouts from Garmin Connect.
    
    Args:
        args: Arguments with the following attributes:
            - oauth_folder: Path to the OAuth folder
            - start_date: Optional start date for listing (YYYY-MM-DD)
            - end_date: Optional end date for listing (YYYY-MM-DD)
            - date_range: Optional predefined date range (TODAY, TOMORROW, CURRENT-WEEK, CURRENT-MONTH)
            - name_filter: Optional regex to filter workout names
            - sport_type: Optional sport type filter 'running' or 'cycling'
            
    Returns:
        List of scheduled workouts
    """
    # Get client
    client = GarminClient.get_instance(args.oauth_folder)
    
    # Determine date range
    if hasattr(args, 'date_range') and args.date_range:
        today = datetime.now().date()
        
        if args.date_range.upper() == 'TODAY':
            start_date = today.strftime('%Y-%m-%d')
            end_date = start_date
        elif args.date_range.upper() == 'TOMORROW':
            tomorrow = today + timedelta(days=1)
            start_date = tomorrow.strftime('%Y-%m-%d')
            end_date = start_date
        elif args.date_range.upper() == 'CURRENT-WEEK':
            # Start from Monday of current week
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
            start_date = monday.strftime('%Y-%m-%d')
            end_date = sunday.strftime('%Y-%m-%d')
        elif args.date_range.upper() == 'CURRENT-MONTH':
            # Start from 1st of current month
            first_day = today.replace(day=1)
            if today.month == 12:
                next_month = 1
                next_year = today.year + 1
            else:
                next_month = today.month + 1
                next_year = today.year
            last_day = datetime(next_year, next_month, 1).date() - timedelta(days=1)
            start_date = first_day.strftime('%Y-%m-%d')
            end_date = last_day.strftime('%Y-%m-%d')
        else:
            # Invalid date range, use default (today to 30 days ahead)
            start_date = today.strftime('%Y-%m-%d')
            end_date = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    else:
        # Use provided start/end dates or defaults
        if hasattr(args, 'start_date') and args.start_date:
            start_date = args.start_date
        else:
            start_date = datetime.now().strftime('%Y-%m-%d')
        
        if hasattr(args, 'end_date') and args.end_date:
            end_date = args.end_date
        else:
            # Default to 30 days ahead
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    logging.info(f"Looking for scheduled workouts from {start_date} to {end_date}")
    
    # Get calendar items for the specified date range
    calendar_items = client.get_calendar(start_date, end_date)
    
    # Verifica se calendar_items è una lista
    if isinstance(calendar_items, dict) and 'calendarItems' in calendar_items:
        calendar_items = calendar_items.get('calendarItems', [])
    
    # Assicurati che calendar_items sia una lista
    if not isinstance(calendar_items, list):
        logging.warning(f"Unexpected calendar_items type: {type(calendar_items)}")
        calendar_items = []
    
    # Filter by name if specified
    name_filter = getattr(args, 'name_filter', None)
    sport_type = getattr(args, 'sport_type', None)
    
    if name_filter or sport_type:
        filtered_items = []
        for item in calendar_items:
            # Verifica che item sia un dizionario
            if not isinstance(item, dict):
                logging.warning(f"Skipping non-dictionary item: {item}")
                continue
                
            # Check if this is a workout and not an event
            if 'title' in item:
                item_name = item['title']
                
                # Apply name filter if specified
                if name_filter and not re.search(name_filter, item_name):
                    continue
                
                # Apply sport type filter if specified
                if sport_type:
                    item_sport_type = item.get('sportType', {}).get('sportTypeKey', 'running')
                    if item_sport_type != sport_type:
                        logging.debug(f"Filtering out workout {item_name} with sport type {item_sport_type}")
                        continue
                
                # Item passed all filters
                filtered_items.append(item)
        
        # Replace with filtered results
        calendar_items = filtered_items
    
    # Process and return the items
    result = []
    for item in calendar_items:
        # Verifica che item sia un dizionario prima di usare get()
        if isinstance(item, dict):
            # Add sport type information to each item
            if 'sportType' in item and 'sportTypeKey' in item['sportType']:
                sport_type_key = item['sportType']['sportTypeKey']
            else:
                sport_type_key = 'running'  # Default
            
            result.append({
                'date': item.get('date', 'N/A'),
                'title': item.get('title', 'Unknown'),
                'id': item.get('calendarItemId', 'N/A'),
                'sport_type': sport_type_key
            })
        else:
            # Se item non è un dizionario, log di avviso
            logging.warning(f"Skipping non-dictionary item: {item}")
    
    # Sort by date
    result.sort(key=lambda x: x['date'])
    
    return result


def cmd_list_scheduled(args):
    """
    List scheduled workouts from Garmin Connect.
    
    Args:
        args: Arguments with the following attributes:
            - oauth_folder: Path to the OAuth folder
            - start_date: Optional start date for listing (YYYY-MM-DD)
            - end_date: Optional end date for listing (YYYY-MM-DD)
            - date_range: Optional predefined date range (TODAY, TOMORROW, CURRENT-WEEK, CURRENT-MONTH)
            - name_filter: Optional regex to filter workout names
            - sport_type: Optional sport type filter 'running' or 'cycling'
    """
    # Get scheduled workouts
    calendar_items = get_scheduled(args)
    
    # Print results in a table format
    if calendar_items:
        # Create a format string for the table
        format_str = "{:<12}  {:<50}  {:<10}"
        print(format_str.format("Date", "Workout", "Sport"))
        print("-" * 80)
        
        for item in calendar_items:
            print(format_str.format(
                item['date'], 
                item['title'], 
                item['sport_type']
            ))
        
        print(f"\nTotal: {len(calendar_items)} workouts")
    else:
        print("No scheduled workouts found for the specified criteria.")
    
    return calendar_items