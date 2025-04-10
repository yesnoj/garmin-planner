import logging
import re
import datetime
import calendar

from planner.garmin_client import GarminClient

def cmd_schedule_workouts(args):
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

    # Organizza gli allenamenti per settimana e sessione
    week_sessions = {}  # Struttura: {week: {session: workout_id}}
    workout_infos = {}  # Struttura: {workout_id: (week, session)}
    
    for workout_id, name in training_sessions.items():
        match = re.search(r'\s(W\d\d)S(\d\d)\s', name)
        if not match:
            logging.warning(f'Workout "{name}" does not match the expected pattern WxxSxx. Skipping.')
            continue
        
        week_id = match.group(1)
        session_id = int(match.group(2))
        
        # Inizializza le strutture dati se necessario
        if week_id not in week_sessions:
            week_sessions[week_id] = {}
        week_sessions[week_id][session_id] = workout_id
        workout_infos[workout_id] = (week_id, session_id)
        
    # Verifica se ci sono settimane definite
    if not week_sessions:
        logging.warning('No valid workouts found for planning.')
        return None
    
    # Ottieni la lista ordinata delle settimane
    weeks = sorted(week_sessions.keys())
    
    # Ottieni data corrente e data gara
    today = datetime.datetime.today().date()
    race_day = datetime.datetime.strptime(args.race_day, '%Y-%m-%d').date()
    
    # Controlla che la data della gara sia nel futuro
    if race_day < today:
        logging.warning(f'Race day {race_day} is in the past. Please set a future date.')
        return None
    
    # Ottieni giorni personalizzati
    custom_days = []
    if args.workout_days:
        try:
            custom_days = [int(d) for d in args.workout_days.split(',')]
            # Controlla che i giorni siano validi (0-6)
            for day in custom_days:
                if day < 0 or day > 6:
                    logging.warning(f'Invalid day index: {day}. Must be 0-6 (Monday-Sunday).')
                    return None
            logging.info(f'Using custom days: {[calendar.day_name[d] for d in custom_days]}')
        except ValueError:
            logging.warning(f'Invalid workout days specified: {args.workout_days}. Must be comma-separated integers (0-6).')
            return None
    
    # Calcola il lunedì della settimana successiva
    next_monday = today + datetime.timedelta(days=(7 - today.weekday()))
    logging.info(f'Starting planning from Monday {next_monday}')
    
    # Pianifica gli allenamenti
    scheduled_workouts = {}  # {date: workout_id}
    dates_used = set()  # Set per tenere traccia delle date già utilizzate
    
    for week_index, week_id in enumerate(weeks):
        week_start = next_monday + datetime.timedelta(weeks=week_index)
        
        # Salta settimane che sarebbero dopo la gara
        if week_start > race_day:
            logging.warning(f'Week {week_id} would be after race day. Skipping.')
            continue
        
        sessions = week_sessions[week_id]
        session_ids = sorted(sessions.keys())
        
        # Verifica che i giorni specificati siano sufficienti
        if custom_days and len(custom_days) < len(session_ids):
            logging.warning(f'Not enough days specified for week {week_id}. Need {len(session_ids)}, got {len(custom_days)}.')
            logging.warning('Using available days and cycling through them.')
        
        # Assegna gli allenamenti ai giorni specificati
        for i, session_id in enumerate(session_ids):
            workout_id = sessions[session_id]
            
            # Determina il giorno della settimana
            if custom_days:
                # Usa i giorni personalizzati, ciclando se necessario
                day_index = custom_days[i % len(custom_days)]
            else:
                # Distribuzione predefinita basata sul numero di sessioni
                if len(session_ids) == 1:
                    day_index = 2  # Mercoledì
                elif len(session_ids) == 2:
                    day_index = [1, 4][i]  # Martedì, Venerdì
                elif len(session_ids) == 3:
                    day_index = [1, 3, 5][i]  # Martedì, Giovedì, Sabato
                elif len(session_ids) == 4:
                    day_index = [1, 3, 5, 6][i]  # Martedì, Giovedì, Sabato, Domenica
                elif len(session_ids) == 5:
                    day_index = [0, 1, 3, 4, 6][i]  # Lunedì, Martedì, Giovedì, Venerdì, Domenica
                elif len(session_ids) == 6:
                    day_index = [0, 1, 2, 3, 4, 6][i]  # L, M, M, G, V, D
                else:
                    day_index = i % 7
            
            # Calcola la data specifica
            workout_date = week_start + datetime.timedelta(days=day_index)
            date_str = workout_date.strftime('%Y-%m-%d')
            
            # Controlla che non sia nel passato
            if workout_date < today:
                logging.warning(f'Workout {week_id}S{session_id:02d} would be scheduled in the past ({date_str}). Skipping.')
                continue
                
            # Controlla che non sia dopo la data della gara
            if workout_date > race_day:
                logging.warning(f'Workout {week_id}S{session_id:02d} would be scheduled after race day ({date_str}). Skipping.')
                continue
            
            # Controlla se questa data è già stata utilizzata per un altro allenamento
            if date_str in scheduled_workouts:
                # Se questa data è già pianificata, verifica se l'allenamento è diverso
                if workout_id != scheduled_workouts[date_str]:
                    # In questo caso, cerca una data alternativa
                    logging.warning(f"Data {date_str} già pianificata con un altro allenamento. Cerco un'alternativa...")
                    alternative_found = False
                    for offset in range(1, 7):
                        alt_date = workout_date + datetime.timedelta(days=offset)
                        alt_date_str = alt_date.strftime('%Y-%m-%d')
                        
                        # Verifica che la data alternativa sia valida e non occupata
                        if alt_date <= race_day and alt_date_str not in scheduled_workouts:
                            workout_date = alt_date
                            date_str = alt_date_str
                            alternative_found = True
                            logging.info(f'Trovata data alternativa {date_str} per {week_id}S{session_id:02d}')
                            break
                            
                    if not alternative_found:
                        logging.warning(f'Non è stato possibile trovare una data alternativa per {week_id}S{session_id:02d}. Salto.')
                        continue
                else:
                    # Questo è lo stesso allenamento già pianificato in questa data, lo saltiamo
                    logging.warning(f'Allenamento {week_id}S{session_id:02d} già pianificato per {date_str}. Salto il duplicato.')
                    continue
            
            # Aggiungi alla pianificazione
            scheduled_workouts[date_str] = workout_id
            dates_used.add(date_str)
            logging.info(f'Pianificato {week_id}S{session_id:02d} per {calendar.day_name[workout_date.weekday()]} {date_str}')
    
    # Ordina la pianificazione per data
    scheduled_workouts = dict(sorted(scheduled_workouts.items()))
    
    # Esegui la pianificazione effettiva
    for date, workout_id in scheduled_workouts.items():
        workout_name = wid_to_name[workout_id]
        week_id, session_id = workout_infos[workout_id]
        logging.info(f'Scheduling workout {workout_name} ({workout_id}) on {date}')
        
        if not args.dry_run:
            client.schedule_workout(workout_id, date)
    
    return None


def cmd_unschedule_workouts(args):
    start_date = datetime.datetime.today().date()
    if args.start_date:
        start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d').date()

    client = GarminClient(args.oauth_folder)
    search_year = start_date.year
    search_month = start_date.month
    
    logging.info(f'Unscheduling workouts for training plan: {args.training_plan}')
    logging.info(f'Starting from date: {start_date}')
    
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
                
                if not schedule_date:
                    continue
                    
                date_cmp = datetime.datetime.strptime(schedule_date, '%Y-%m-%d').date()
                
                if date_cmp < start_date:
                    logging.debug(f'Ignoring past workout [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                elif re.search(args.training_plan, workout_name):
                    found_workouts += 1
                    logging.info(f'Unscheduling workout [{schedule_date}, {schedule_id}]: {workout_name} ({workout_id})')
                    
                    if not args.dry_run:
                        client.unschedule_workout(schedule_id)
        
        # Se non sono stati trovati allenamenti in questa iterazione, esci
        if found_workouts == 0:
            break
            
        # Continua cercando nel mese successivo
        search_month += 1
        if search_month > 12:
            search_year += 1
            search_month = 1
            
        # Limita la ricerca a 12 mesi nel futuro
        if search_year > start_date.year + 1:
            break
            
    return None