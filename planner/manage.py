import logging
import re
import datetime
import calendar
import yaml
from planner.garmin_client import GarminClient


def cmd_list_scheduled(args):
    workouts = get_scheduled(args)
    print(workouts)

def get_scheduled(args):
    start_date = datetime.datetime.today().date()
    end_date = None
    if args.start_date:
        start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d').date()

    if args.end_date:
        end_date = datetime.datetime.strptime(args.end_date, '%Y-%m-%d').date()

    if args.date_range:
        if args.date_range.upper() == 'TODAY':
            start_date = end_date = datetime.datetime.today().date()
        elif args.date_range.upper() == 'TOMORROW':
            start_date = end_date = datetime.datetime.today().date() + datetime.timedelta(days=1)
        elif args.date_range.upper() == 'CURRENT-WEEK':
            start_date = datetime.datetime.today().date() - datetime.timedelta(days = datetime.datetime.today().weekday())
            end_date = start_date + datetime.timedelta(days=6)
        elif args.date_range.upper() == 'NEXT-WEEK': # TODO: calculate the right dates
            start_date = datetime.datetime.today().date() - datetime.timedelta(days = datetime.datetime.today().weekday()) + datetime.timedelta(days=7)
            end_date = start_date + datetime.timedelta(days=6)
        elif args.date_range.upper() == 'CURRENT-MONTH': # TODO: calculate the right dates
            start_date = datetime.datetime.today().date() - datetime.timedelta(days = datetime.datetime.today().day - 1)
            end_date = start_date + datetime.timedelta(days=calendar.monthrange(start_date.year, start_date.month)[1]-1)
        else:
            logging.warn(f'invalid date range: {args.date_range}')
            return

    client = GarminClient(args.oauth_folder)
    matching_workouts = []
    search_year = start_date.year
    search_month = start_date.month
    
    # Dizionario per tenere traccia degli allenamenti per data (per evitare duplicati)
    workouts_by_date = {}
    
    while True:
        response = client.get_calendar(search_year, search_month)
        found_workouts = 0
        calendar_items = response.get('calendarItems', [])
        for item in calendar_items:
            if item.get('itemType', '') == 'workout':
                workout_name = item.get('title', '')
                workout_id = item.get('workoutId', None)
                schedule_id = item.get('id', None)
                schedule_date = item.get('date', None)
                
                if args.name_filter:
                    if not re.search(args.name_filter, workout_name):
                        logging.debug(f'workout name does not match [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                        continue
                        
                date_cmp = datetime.datetime.strptime(schedule_date, '%Y-%m-%d').date()
                
                if date_cmp < start_date or (end_date and date_cmp > end_date):
                    logging.debug(f'date out bounds for workout[{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                else:
                    # Verifica se abbiamo già un allenamento per questa data
                    if schedule_date in workouts_by_date:
                        logging.debug(f'Ignorato duplicato allenamento[{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                    else:
                        logging.debug(f'found scheduled workout[{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                        workouts_by_date[schedule_date] = item
                        matching_workouts.append(item)
                        found_workouts += 1

        # if no workouts were found in the latest iteration
        if not end_date and found_workouts == 0:
            break
        # continue looking for workouts the following month
        search_month += 1
        if search_month > 12:
            search_year += 1
            search_month = 1
        # until the next month is out of bounds
        if end_date and datetime.date(year=search_year, month=search_month, day=1) > end_date:
            break
    return matching_workouts

# def cmd_list_scheduled(args): # 
#     with open('sample_workout.yaml', 'r') as file:
#         workout = yaml.safe_load(file)
#         dist_to_time(workout)
#         print(workout)

def dist_to_time(wo_part):
    if isinstance(wo_part, list):
        for wo_item in wo_part:
            dist_to_time(wo_item)
    elif isinstance(wo_part, dict):
        # We found an end condition to check
        if 'endCondition' in wo_part and wo_part['endCondition']['conditionTypeKey'] == 'distance':
            target_pace_ms = None
            if wo_part['targetType']['workoutTargetTypeKey'] == 'pace.zone':
                target_pace_ms = (wo_part['targetValueOne'] + wo_part['targetValueTwo']) / 2
                # 
                end_condition_sec = wo_part['endConditionValue'] / target_pace_ms
                # Round it to the nearest 10 seconds
                end_condition_sec = int(round(end_condition_sec/10, 0) * 10)
                # Update end condition
                wo_part['endConditionValue'] = float(end_condition_sec)
                wo_part['endCondition']['conditionTypeKey'] = 'time'
                wo_part['endCondition']['conditionTypeId'] = 2
                wo_part['endCondition']['displayOrder'] = 2
                wo_part.pop('preferredEndConditionUnit', None)
        # Continue looking at this dict
        for k, v in wo_part.items():
            if isinstance(v, list) or isinstance(v, dict):
                dist_to_time(v)
