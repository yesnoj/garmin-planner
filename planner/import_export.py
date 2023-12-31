import yaml
import re
import logging
import json

from .utils import mmss_to_seconds, pace_to_ms, seconds_to_mmss
from .workout import Target, Workout, WorkoutStep
from planner.garmin_client import GarminClient

def cmd_import_workouts(args):
    logging.info('importing workouts from ' + args.workouts_file)
    existing_workouts = []

    with GarminClient(args.garmin_id, args.garmin_password) as client:
        if not args.dry_run:
            if args.replace:
                res = client.list_workouts()
                existing_workouts = res[1]

        for workout in import_workouts(args.workouts_file):
            # filter workouts
            if args.name_filter and not re.search(args.name_filter, workout.workout_name):
                continue

            if args.dry_run:
                print(json.dumps(workout.garminconnect_json()))
            else:
                logging.info('creating workout: ' + workout.workout_name)
                workouts_to_delete = []
                if args.replace:
                    print(existing_workouts)
                    for wo in existing_workouts:
                        if wo['workoutName'] == workout.workout_name:
                            workouts_to_delete.append(str(wo['workoutId']))
                res = client.add_workout(workout)
                if res[0] in [200, 204]:
                    for wod in workouts_to_delete:
                        client.delete_workout(wod)

    return None

def cmd_export_workouts(args):
    with GarminClient(args.garmin_id, args.garmin_password) as client:
        response = client.list_workouts()

        workouts = response[1]

        formatted_output = ''
        export_format = args.format

        # If export format was not indicated in the command line, the file extension can decide it
        file_extension = args.export_file.split('.')[-1].upper() if '.' in args.export_file else None
        if not export_format and file_extension:        
            if file_extension in ['JSON', 'JSN']:
                export_format = 'JSON'
            elif file_extension in ['YAML', 'YML']:
                export_format = 'YAML'

        if not export_format or export_format == 'JSON':
            formatted_output = json.dumps(workouts, indent=2)
        elif export_format == 'YAML':
            formatted_output = yaml.dump(workouts)

        if args.export_file != '':
            print('exporting workouts to file '+ args.export_file)
            f = open(args.export_file, 'w')
            f.write(formatted_output)
            f.close()
        else:
            print(formatted_output)

    return None

def cmd_delete_workouts(args):
    valid_ids = []
    client = GarminClient(args.garmin_id, args.garmin_password)
    if args.workout_ids:
        if ',' in args.workout_ids:
            workout_ids = args.workout_ids.split(',')
        else:
            workout_ids = [args.workout_ids]

        # filter out invalid workout IDs
        for workout_id in workout_ids:
            if not re.match(r'^\d{9}$', workout_id):
                logging.warning(f'ignoring invalid workout id "{workout_id}". Must be 9 digit number.')
            else:
                valid_ids.append(workout_id)

    if args.name_filter:
        client.connect()
        logging.info(f'getting list of workouts.')
        response = client.list_workouts()
        if response[0] not in [200, 204]:
            print(str(response[0]) + ': ' + str(response[1]))
        workouts_list = response[1]
        for workout in workouts_list:
            if re.search(args.name_filter, workout['workoutName']):
                logging.info(f'found workout named "{workout["workoutName"]}" with ID {workout["workoutId"]}.')
                valid_ids.append(str(workout['workoutId']))

    elif len(valid_ids) == 0:
        logging.warning('couldn\'t find any valid workout ID.')
        return

    if not args.name_filter:
        client.connect()

    for workout_id in valid_ids:
        res = client.delete_workout(workout_id)

    return None

config = {}

def get_description(step_txt):
    if ' -- ' in step_txt:
        return step_txt[step_txt.find(' -- ') + 4:].strip()
    return None

def clean_step(step_txt):
    # remove description, if any
    if ' -- ' in step_txt:
        step_txt = step_txt[:step_txt.find(' -- ')].strip()
    return step_txt    

def get_end_condition(step_txt):
    step_txt = clean_step(step_txt)
    p_distance = re.compile(r'^\d+(m|km)\s?')
    p_time = re.compile(r'^\d+(min|h|s)\s?')
    p_iterations = re.compile(r'^\d+$')
    if p_time.match(step_txt):
        return 'time'
    elif p_distance.match(step_txt):
        return 'distance'
    elif p_iterations.match(step_txt):
        return 'iterations'
    return 'lap.button'

def get_end_condition_value(step_txt, condition_type=None):
    step_txt = clean_step(step_txt)

    if not condition_type:
        condition_type = get_end_condition(step_txt)
    
    if condition_type == 'time':
        p = re.compile(r'^(\d+)((min|h|s))\s?')
        m = p.match(step_txt)
        cv = int(m.group(1))
        tu = m.group(2)
        if tu == 'h':
            cv = cv * 60 * 60
        elif tu == 'min':
            cv = cv * 60
        elif tu == 's':
            cv = cv

        return str(cv)
    elif condition_type == 'distance':
        p = re.compile(r'^(\d+)((m|km))\s?')
        m = p.match(step_txt)
        cv = int(m.group(1))
        tu = m.group(2)
        if tu == 'km':
            cv = cv * 1000
        return str(cv)
    return None

def add_pace_margins(fixed_pace, margins):
    if not margins:
        return fixed_pace + '-' + fixed_pace
        
    fixed_pace_s = mmss_to_seconds(fixed_pace)
    fast_margin_s = mmss_to_seconds(margins['faster'])
    slow_margin_s = mmss_to_seconds(margins['slower'])
    fast_pace_s = fixed_pace_s - fast_margin_s
    slow_pace_s = fixed_pace_s + slow_margin_s
    return seconds_to_mmss(slow_pace_s) + '-' + seconds_to_mmss(fast_pace_s)

def get_target(step_txt):
    step_txt = clean_step(step_txt)

    m = re.compile('^(.+) @ (.+)$').match(step_txt)
    if m:
        target = m.group(2).strip()
        if target in config['paces']:
            target = config['paces'][target]
        if re.compile(r'^\d{1,2}:\d{1,2}$').match(target):
            target = add_pace_margins(target, config.get('margins', None))

        pm = re.compile(r'^(\d{1,2}:\d{1,2})-(\d{1,2}:\d{1,2})$').match(target)
        if pm:
            return Target("pace.zone", pace_to_ms(pm.group(1)), pace_to_ms(pm.group(2)))
            
    m = re.compile('^(.+) in (.+)$').match(step_txt)
    if m:
        end_condition = get_end_condition(step_txt)
        if end_condition != 'distance':
            print('invalid step. "in" target requires distance condition: ' + step_txt)
            return None
        target = m.group(2).strip()
        if re.compile(r'^\d{1,2}:\d{1,2}$').match(target):
            full_time = pace_to_ms(target)
            full_distance = int(get_end_condition_value(step_txt))
            km_distance = full_distance / 1000
            target_pace = full_time * km_distance
            # print('full_time: ' + str(full_time))
            # print('full_distance: ' + str(full_distance))
            # print('km_distance: ' + str(km_distance))
            # print('target_pace: ' + str(target_pace))
            return Target("pace.zone", target_pace, target_pace)
    return None

def import_workouts(plan_file):

    with open(plan_file, 'r') as file:
        workouts = []
        import_json = yaml.safe_load(file)

        # remove the config entry, if present
        global config
        config = import_json.pop('config', {})

        for name, steps in import_json.items():
            w = Workout("running", config.get('name_prefix', '') + name)
            for step in steps:
                for k, v in step.items():
                  if not k.startswith('repeat'):
                    end_condition = get_end_condition(v)
                    ws = WorkoutStep(
                        0,
                        k,
                        get_description(v),
                        end_condition=end_condition,
                        end_condition_value=get_end_condition_value(v, end_condition),
                        target=get_target(v)
                    )
                    w.add_step(ws)
                  else:
                      m = re.compile(r'^repeat\s+(\d+)$').match(k)
                      iterations = int(m.group(1))
                      # create the repetition step
                      ws = WorkoutStep(
                          0,
                          'repeat',
                          get_description(v),
                          end_condition='iterations',
                          end_condition_value=iterations
                      )
                      # create the repeated steps
                      for step in v:
                        for rk, rv in step.items():
                          end_condition = get_end_condition(rv)
                          rws = WorkoutStep(
                              0,
                              rk,
                              get_description(rv),
                              end_condition=end_condition,
                              end_condition_value=get_end_condition_value(rv, end_condition),
                              target=get_target(rv)
                          )
                        ws.add_step(rws)
                        w.add_step(ws)

            #print(json.dumps(w.garminconnect_json(), indent=2))
            workouts.append(w)
        return workouts
