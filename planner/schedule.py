"""
Schedule management for Garmin workouts.

This module provides functionality to schedule workouts in a training plan
and manage scheduled workouts on Garmin Connect.
"""

import logging
import re
import datetime
import calendar

from planner.garmin_client import GarminClient

def cmd_schedule_workouts(args):
    """
    Schedule workouts in a training plan.
    
    Args:
        args: Command line arguments with the following attributes:
            - training_plan: ID of the training plan (common prefix of workouts)
            - race_day: Date of the race (format: YYYY-MM-DD)
            - start_day: Optional start date (format: YYYY-MM-DD)
            - workout_days: Optional comma-separated list of day indices (0=Monday, 6=Sunday)
            - oauth_folder: Path to the OAuth folder
            - dry_run: If True, only show what would be scheduled without making changes
            
    Returns:
        None
    """
    training_sessions = {}
    client = GarminClient(args.oauth_folder)
    
    logging.info(f'Getting list of workouts.')
    workouts_list = client.list_workouts()
    
    # Create mapping from workout ID to name
    wid_to_name = {}
    
    # Find workouts matching the training plan
    for workout in workouts_list:
        workout_name = workout['workoutName']
        workout_id = workout["workoutId"]
        wid_to_name[workout_id] = workout_name
        
        if re.search(args.training_plan, workout['workoutName']):
            logging.info(f'Found workout named "{workout_name}" with ID {workout_id}.')
            training_sessions[workout_id] = workout_name

    # Organize workouts by week and session
    week_sessions = {}  # Structure: {week: {session: workout_id}}
    workout_infos = {}  # Structure: {workout_id: (week, session)}
    
    for workout_id, name in training_sessions.items():
        match = re.search(r'\s(W\d\d)S(\d\d)\s', name)
        if not match:
            logging.warning(f'Workout "{name}" does not match the expected pattern WxxSxx. Skipping.')
            continue
        
        week_id = match.group(1)
        session_id = int(match.group(2))
        
        # Initialize data structures if needed
        if week_id not in week_sessions:
            week_sessions[week_id] = {}
        week_sessions[week_id][session_id] = workout_id
        workout_infos[workout_id] = (week_id, session_id)
        
    # Check if there are any defined weeks
    if not week_sessions:
        logging.warning('No valid workouts found for planning.')
        return None
    
    # Get the ordered list of weeks
    weeks = sorted(week_sessions.keys())
    
    # Get current date and race date
    today = datetime.datetime.today().date()
    try:
        race_day = datetime.datetime.strptime(args.race_day, '%Y-%m-%d').date()
    except ValueError:
        logging.error(f'Invalid race day format: {args.race_day}. Use YYYY-MM-DD format.')
        return None
    
    # Check that race day is in the future
    if race_day < today:
        logging.warning(f'Race day {race_day} is in the past. Please set a future date.')
        return None
    
    # Calculate start date if specified
    start_date = today
    if args.start_day:
        try:
            start_date = datetime.datetime.strptime(args.start_day, '%Y-%m-%d').date()
            # Check that start date is not in the past
            if start_date < today:
                logging.warning(f'Start date {start_date} is in the past. Using today instead.')
                start_date = today
            elif start_date > race_day:
                logging.warning(f'Start date {start_date} is after race day {race_day}. Using today instead.')
                start_date = today
            logging.info(f'Using custom start date: {start_date}')
        except ValueError:
            logging.warning(f'Invalid start date format: {args.start_day}. Using today instead.')
    
    # Get custom days
    custom_days = []
    if args.workout_days:
        try:
            custom_days = [int(d) for d in args.workout_days.split(',')]
            # Check that days are valid (0-6)
            for day in custom_days:
                if day < 0 or day > 6:
                    logging.warning(f'Invalid day index: {day}. Must be 0-6 (Monday-Sunday).')
                    return None
            logging.info(f'Using custom days: {[calendar.day_name[d] for d in custom_days]}')
        except ValueError:
            logging.warning(f'Invalid workout days specified: {args.workout_days}. Must be comma-separated integers (0-6).')
            return None
    
    # Calculate the Monday of the week to start planning
    if start_date.weekday() == 0:  # 0 = Monday
        next_monday = start_date
    else:
        days_until_monday = (7 - start_date.weekday()) % 7
        next_monday = start_date + datetime.timedelta(days=days_until_monday)
    
    logging.info(f'Starting planning from Monday {next_monday}')
    
    # Plan the workouts
    scheduled_workouts = {}  # {date: workout_id}
    dates_used = set()  # Set to track dates already used
    
    for week_index, week_id in enumerate(weeks):
        week_start = next_monday + datetime.timedelta(weeks=week_index)
        
        # Skip weeks that would be after the race
        if week_start > race_day:
            logging.warning(f'Week {week_id} would be after race day. Skipping.')
            continue
        
        sessions = week_sessions[week_id]
        session_ids = sorted(sessions.keys())
        
        # Check if specified days are enough
        if custom_days and len(custom_days) < len(session_ids):
            logging.warning(f'Not enough days specified for week {week_id}. Need {len(session_ids)}, got {len(custom_days)}.')
            logging.warning('Using available days and cycling through them.')
        
        # Assign workouts to specified days
        for i, session_id in enumerate(session_ids):
            workout_id = sessions[session_id]
            
            # Determine the day of the week
            if custom_days:
                # Use custom days, cycling if necessary
                day_index = custom_days[i % len(custom_days)]
            else:
                # Default distribution based on number of sessions
                if len(session_ids) == 1:
                    day_index = 2  # Wednesday
                elif len(session_ids) == 2:
                    day_index = [1, 4][i]  # Tuesday, Friday
                elif len(session_ids) == 3:
                    day_index = [1, 3, 5][i]  # Tuesday, Thursday, Saturday
                elif len(session_ids) == 4:
                    day_index = [1, 3, 5, 6][i]  # Tuesday, Thursday, Saturday, Sunday
                elif len(session_ids) == 5:
                    day_index = [0, 1, 3, 4, 6][i]  # Monday, Tuesday, Thursday, Friday, Sunday
                elif len(session_ids) == 6:
                    day_index = [0, 1, 2, 3, 4, 6][i]  # M, T, W, T, F, S
                else:
                    day_index = i % 7
            
            # Calculate the specific date
            workout_date = week_start + datetime.timedelta(days=day_index)
            date_str = workout_date.strftime('%Y-%m-%d')
            
            # Check that it's not in the past
            if workout_date < today:
                logging.warning(f'Workout {week_id}S{session_id:02d} would be scheduled in the past ({date_str}). Skipping.')
                continue
                
            # Check that it's not after the race day
            if workout_date > race_day:
                logging.warning(f'Workout {week_id}S{session_id:02d} would be scheduled after race day ({date_str}). Skipping.')
                continue
            
            # Check if this date is already used for another workout
            if date_str in scheduled_workouts:
                # If this date is already scheduled, check if the workout is different
                if workout_id != scheduled_workouts[date_str]:
                    # Look for an alternative date
                    logging.warning(f"Date {date_str} already scheduled with another workout. Looking for alternative...")
                    alternative_found = False
                    for offset in range(1, 7):
                        alt_date = workout_date + datetime.timedelta(days=offset)
                        alt_date_str = alt_date.strftime('%Y-%m-%d')
                        
                        # Check that the alternative date is valid and not occupied
                        if alt_date <= race_day and alt_date_str not in scheduled_workouts:
                            workout_date = alt_date
                            date_str = alt_date_str
                            alternative_found = True
                            logging.info(f'Found alternative date {date_str} for {week_id}S{session_id:02d}')
                            break
                            
                    if not alternative_found:
                        logging.warning(f'Could not find an alternative date for {week_id}S{session_id:02d}. Skipping.')
                        continue
                else:
                    # This is the same workout already scheduled for this date, skip it
                    logging.warning(f'Workout {week_id}S{session_id:02d} already scheduled for {date_str}. Skipping duplicate.')
                    continue
            
            # Add to schedule
            scheduled_workouts[date_str] = workout_id
            dates_used.add(date_str)
            logging.info(f'Scheduled {week_id}S{session_id:02d} for {calendar.day_name[workout_date.weekday()]} {date_str}')
    
    # Sort the schedule by date
    scheduled_workouts = dict(sorted(scheduled_workouts.items()))
    
    # Perform the actual scheduling
    for date, workout_id in scheduled_workouts.items():
        workout_name = wid_to_name[workout_id]
        week_id, session_id = workout_infos[workout_id]
        logging.info(f'Scheduling workout {workout_name} ({workout_id}) on {date}')
        
        if not args.dry_run:
            client.schedule_workout(workout_id, date)
    
    return None


def cmd_unschedule_workouts(args):
    """
    Unschedule workouts from Garmin Connect calendar.
    
    Args:
        args: Command line arguments with the following attributes:
            - training_plan: ID of the training plan to unschedule
            - start_date: Optional start date to look for workouts
            - oauth_folder: Path to the OAuth folder
            - dry_run: If True, only show what would be unscheduled without making changes
            
    Returns:
        None
    """
    start_date = datetime.datetime.today().date()
    if args.start_date:
        try:
            start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d').date()
        except ValueError:
            logging.error(f'Invalid start date format: {args.start_date}. Use YYYY-MM-DD format.')
            return None

    client = GarminClient(args.oauth_folder)
    search_year = start_date.year
    search_month = start_date.month
    
    logging.info(f'Unscheduling workouts for training plan: {args.training_plan}')
    logging.info(f'Starting from date: {start_date}')
    
    unscheduled_count = 0
    max_months = 12  # Limit search to 12 months in the future to avoid infinite loop
    month_count = 0
    
    while month_count < max_months:
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
                    
                date_cmp = datetime.datetime.strptime(schedule_date, '%Y-%m-%d').date()
                
                if date_cmp < start_date:
                    logging.debug(f'Ignoring past workout [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                elif re.search(args.training_plan, workout_name):
                    found_workouts += 1
                    unscheduled_count += 1
                    logging.info(f'Unscheduling workout [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                    
                    if not args.dry_run:
                        client.unschedule_workout(schedule_id)
        
        # If no workouts were found in this iteration and we're past the current month, we can stop
        if found_workouts == 0 and (search_year > datetime.datetime.today().year or 
                                    (search_year == datetime.datetime.today().year and 
                                     search_month > datetime.datetime.today().month)):
            break
            
        # Continue searching in the next month
        search_month += 1
        if search_month > 12:
            search_year += 1
            search_month = 1
            
        month_count += 1
            
    logging.info(f'Unscheduled {unscheduled_count} workouts from calendar')
    return None