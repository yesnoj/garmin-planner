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
    Pianifica gli allenamenti in Garmin Connect.
    Questa versione usa la stessa logica della simulazione per calcolare le date.
    """
    training_sessions = {}
    client = GarminClient(args.oauth_folder)
    logging.info(f'getting list of workouts.')
    workouts_list = client.list_workouts()
    wid_to_name = {}
    for workout in workouts_list:
        workout_name = workout['workoutName']
        workout_id = workout["workoutId"]
        wid_to_name[workout_id] = workout_name
        if re.search(args.training_plan, workout['workoutName']):
            logging.info(f'found workout named "{workout_name}" with ID {workout_id}.')
            training_sessions[workout_id] = workout_name

    # Organizziamo gli allenamenti per settimana e sessione
    training_plan = {}
    week_ids = []
    workout_infos = {}
    
    for workout_id, name in training_sessions.items():
        match = re.search(r'\s(W\d\d)S(\d\d)\s', name)
        if match:
            week_id = match.group(1)
            session_id = int(match.group(2))
            week_num = int(week_id[1:])
            
            if week_id not in training_plan:
                training_plan[week_id] = {}
            if session_id not in training_plan[week_id]:
                training_plan[week_id][session_id] = []
            
            training_plan[week_id][session_id].append(workout_id)
            
            if week_id not in week_ids:
                week_ids.append(week_id)
            
            # Salva info per debug
            workout_infos[workout_id] = (week_id, session_id, name)

    if not training_plan:
        logging.warning('No valid workouts found for planning.')
        return None

    # Controlla se l'attributo reverse_order esiste, altrimenti usa False di default
    reverse_order = getattr(args, 'reverse_order', False)
    
    # Ordina le settimane in ordine decrescente (dall'ultima alla prima)
    week_ids = sorted(week_ids, reverse=reverse_order)
    
    # Ottieni la data della gara
    race_day = datetime.datetime.strptime(args.race_day, '%Y-%m-%d')
    today = datetime.datetime.today()
    
    logging.info(f'Race day: {race_day.strftime("%Y-%m-%d")} (weekday: {race_day.weekday()})')
    
    # Trova la settimana massima per calcolare correttamente gli offset
    max_week = max([int(w[1:]) for w in week_ids])
    logging.info(f'Max week: W{max_week:02d}, Total weeks: {len(week_ids)}')
    
    # Trova il lunedì della settimana della gara
    days_to_monday = race_day.weekday()  # 0=lunedì, 1=martedì, ecc.
    race_week_monday = race_day - datetime.timedelta(days=days_to_monday)
    logging.info(f'Monday of race week: {race_week_monday.strftime("%Y-%m-%d")}')
    
    # Ottieni i giorni della settimana selezionati
    selected_days = []
    if hasattr(args, 'workout_days') and args.workout_days:
        try:
            selected_days = [int(d) for d in args.workout_days.split(',')]
            selected_days = sorted(selected_days)  # Ordina i giorni
            day_names = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']
            logging.info(f'Selected days: {", ".join([day_names[d] for d in selected_days])}')
        except Exception as e:
            logging.error(f'Error parsing workout_days: {str(e)}')
            return None
    
    # Se non ci sono giorni selezionati, usa i giorni predefiniti
    if not selected_days:
        logging.info('No days selected, using default days')
        # Imposta giorni predefiniti in base al numero massimo di sessioni per settimana
        max_sessions = max([len(week_sessions) for week_sessions in training_plan.values()])
        if max_sessions == 1:
            selected_days = [2]  # Mercoledì
        elif max_sessions == 2:
            selected_days = [1, 4]  # Martedì, Venerdì
        elif max_sessions == 3:
            selected_days = [1, 3, 6]  # Martedì, Giovedì, Domenica
        elif max_sessions == 4:
            selected_days = [1, 3, 5, 6]  # Martedì, Giovedì, Sabato, Domenica
        elif max_sessions >= 5:
            selected_days = [0, 1, 3, 4, 6]  # Lunedì, Martedì, Giovedì, Venerdì, Domenica
    
    # Pianifica gli allenamenti
    scheduled_plan = {}
    used_dates = set()
    
    # Per ogni settimana
    for week_id in week_ids:
        # Estrai il numero della settimana
        week_num = int(week_id[1:])
        
        # Calcola l'offset rispetto alla settimana massima
        week_offset = max_week - week_num
        
        # Calcola il lunedì di questa settimana
        week_monday = race_week_monday - datetime.timedelta(weeks=week_offset)
        logging.info(f'Planning week {week_id}: starts on {week_monday.strftime("%Y-%m-%d")} (Monday)')
        
        # Ottieni le sessioni per questa settimana, ordinate
        if week_id in training_plan:
            sessions = sorted(training_plan[week_id].keys())
            
            # Assegna ogni sessione a un giorno della settimana
            for session_idx, session_id in enumerate(sessions):
                workout_ids = training_plan[week_id][session_id]
                
                # Determina il giorno della settimana
                if session_idx < len(selected_days):
                    day_idx = selected_days[session_idx]
                else:
                    # Se ci sono più sessioni che giorni selezionati, cicla
                    day_idx = selected_days[session_idx % len(selected_days)]
                
                # Calcola la data
                workout_date = week_monday + datetime.timedelta(days=day_idx)
                date_str = workout_date.strftime("%Y-%m-%d")
                
                # Verifica se coincide con il giorno della gara
                if workout_date.date() == race_day.date():
                    logging.info(f'Workout {week_id}S{session_id:02d} would be on race day ({date_str}). Skipping.')
                    continue
                
                # Verifica se è nel passato
                if workout_date < today:
                    logging.info(f'Workout {week_id}S{session_id:02d} would be in the past ({date_str}). Skipping.')
                    continue
                
                # Verifica se è dopo la gara
                if workout_date > race_day:
                    logging.info(f'Workout {week_id}S{session_id:02d} would be after race day ({date_str}). Skipping.')
                    continue
                
                # Verifica se la data è già utilizzata
                if date_str in used_dates:
                    # Cerca una data alternativa
                    logging.info(f'Date {date_str} already used. Looking for alternative...')
                    found_alternative = False
                    
                    for alt_day in [d for d in selected_days if d != day_idx]:
                        alt_date = week_monday + datetime.timedelta(days=alt_day)
                        alt_date_str = alt_date.strftime("%Y-%m-%d")
                        
                        # Verifica che l'alternativa sia valida
                        if (alt_date.date() != race_day.date() and
                            alt_date <= race_day and
                            alt_date >= today and
                            alt_date_str not in used_dates):
                            workout_date = alt_date
                            date_str = alt_date_str
                            found_alternative = True
                            logging.info(f'Found alternative date: {date_str}')
                            break
                    
                    if not found_alternative:
                        logging.info(f'No alternative date available for {week_id}S{session_id:02d}. Skipping.')
                        continue
                
                # Aggiungi alla pianificazione
                used_dates.add(date_str)
                if date_str not in scheduled_plan:
                    scheduled_plan[date_str] = []
                
                # Aggiungi tutti gli allenamenti di questa sessione
                scheduled_plan[date_str].extend(workout_ids)
                
                # Log per ogni allenamento
                for workout_id in workout_ids:
                    if workout_id in workout_infos:
                        logging.info(f'Scheduling workout {workout_infos[workout_id][2]} ({workout_id}) on {date_str}')
    
    # Ordina la pianificazione per data
    scheduled_plan = dict(sorted(scheduled_plan.items()))
    
    # Pianifica effettivamente gli allenamenti in Garmin Connect
    workouts_scheduled = 0
    
    for date_str, workout_ids in scheduled_plan.items():
        for workout_id in workout_ids:
            try:
                logging.info(f'Scheduling workout {wid_to_name[workout_id]} ({workout_id}) on {date_str}')
                if not args.dry_run:
                    client.schedule_workout(workout_id, date_str)
                workouts_scheduled += 1
            except Exception as e:
                logging.error(f'Error scheduling workout {workout_id} on {date_str}: {str(e)}')
    
    logging.info(f'Scheduled {workouts_scheduled} workouts')
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