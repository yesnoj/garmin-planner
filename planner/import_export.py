import yaml
import re
import logging
import json

from .utils import hhmmss_to_seconds, pace_to_ms, seconds_to_mmss, ms_to_pace, dist_time_to_ms
from .workout import Target, Workout, WorkoutStep
from planner.garmin_client import GarminClient

CLEAN_KEYS = ['author', 'createdDate', 'ownerId', 'shared', 'updatedDate']

def cmd_import_workouts(args):
    logging.info('importing workouts from ' + args.workouts_file)
    existing_workouts = []

    client = GarminClient(args.oauth_folder)
    if not args.dry_run:
        if args.replace:
            existing_workouts = client.list_workouts()

    for workout in import_workouts(args.workouts_file):
        # filter workouts
        if args.name_filter and not re.search(args.name_filter, workout.workout_name):
            continue

        if args.treadmill or workout.workout_name.strip().endswith('(T)'):
            workout.dist_to_time()

        if args.dry_run:
            print(json.dumps(workout.garminconnect_json()))
        else:
            logging.info('creating workout: ' + workout.workout_name)
            workouts_to_delete = []
            id_to_replace = None
            if args.replace:
                for wo in existing_workouts:
                    if wo['workoutName'] == workout.workout_name:
                        id_to_replace = wo['workoutId']
            if id_to_replace != None:
                client.update_workout(id_to_replace, workout)
            else:
                client.add_workout(workout)

    return None

def cmd_export_workouts(args):

    def clean(wo_dict):
        if isinstance(wo_dict, list):
            for ldict in wo_dict:
                clean(ldict)
        elif isinstance(wo_dict, dict):
            keys = list(wo_dict.keys())
            for k in keys:
                v = wo_dict[k]
                if k in CLEAN_KEYS or v == None or v == 'null':
                    del wo_dict[k]
                elif isinstance(v, dict) or isinstance(v, list):
                    final_size = clean(v)
                    if final_size == 0:
                        del wo_dict[k]
        return len(wo_dict)

    client = GarminClient(args.oauth_folder)
    workout_ids = client.list_workouts()

    if args.name_filter:
        filtered = []
        for workout in workout_ids:
            if re.search(args.name_filter, workout['workoutName']):
                filtered.append(workout)
        workout_ids = filtered

    workouts = []
    for wid in workout_ids:
        workout = client.get_workout(wid['workoutId'])
        if args.clean:
            clean(workout)
        workouts.append(workout)

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
    client = GarminClient(args.oauth_folder)
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
        logging.info(f'getting list of workouts.')
        workouts_list = client.list_workouts()
        for workout in workouts_list:
            if re.search(args.name_filter, workout['workoutName']):
                logging.info(f'found workout named "{workout["workoutName"]}" with ID {workout["workoutId"]}.')
                valid_ids.append(str(workout['workoutId']))

    elif len(valid_ids) == 0:
        logging.warning('couldn\'t find any valid workout ID.')
        return

    for workout_id in valid_ids:
        res = client.delete_workout(workout_id)

    return None

config = {}

def import_workouts(plan_file):

    with open(plan_file, 'r') as file:
        workouts = []
        import_json = yaml.safe_load(file)

        # remove the config entry, if present
        global config
        config = import_json.pop('config', {})

        expand_config(config)

        for name, steps in import_json.items():
            w = Workout("running", config.get('name_prefix', '') + name)
            for step in steps:
                for k, v in step.items():
                  if not k.startswith('repeat'):
                    end_condition = get_end_condition(v)
                    ws_target=get_target(v)
                    ws = WorkoutStep(
                        0,
                        k,
                        get_description(v, ws_target),
                        end_condition=end_condition,
                        end_condition_value=get_end_condition_value(v, end_condition),
                        target=ws_target
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
                          rws_target=get_target(rv)
                          rws = WorkoutStep(
                              0,
                              rk,
                              get_description(rv, rws_target),
                              end_condition=end_condition,
                              end_condition_value=get_end_condition_value(rv, end_condition),
                              target=rws_target
                          )
                        ws.add_step(rws)
                        w.add_step(ws)

            #print(json.dumps(w.garminconnect_json(), indent=2))
            workouts.append(w)
        return workouts

def get_description(step_txt, target=None):
    description = None
    if ' -- ' in step_txt:
        description = step_txt[step_txt.find(' -- ') + 4:].strip()
    if target and target.target == 'pace.zone':
        avg_pace = (target.from_value + target.to_value) / 2
        avg_pace_kmph = avg_pace / 0.27778
        avg_pace_kmph_str = f'{avg_pace_kmph:.1f} kmph'
        if description:
            description += '\n' + avg_pace_kmph_str
        else:
            description = avg_pace_kmph_str
    return description

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

def get_target(step_txt):
    step_txt = clean_step(step_txt)

    m = re.compile('^(.+) @ (.+)$').match(step_txt)
    if m:
        scale = 1
        target = m.group(2).strip()

        # See if the target can be found in the config block
        if target in config['paces']:
            target = config['paces'][target]

        # Check if the target is of type 75% marathon_pace
        tm = re.compile(r'^([\d.]+)%\s*(.+)$').match(target)
        if tm:
            scale = float(tm.group(1)) / 100
            target = tm.group(2).strip()

            # Check again if the new target is found in the config block
            if target in config['paces']:
                target = config['paces'][target]

        if re.compile(r'^\d{1,2}:\d{1,2}$').match(target):
            target = add_pace_margins(target, config.get('margins', None))

        pm = re.compile(r'^(\d{1,2}:\d{1,2})-(\d{1,2}:\d{1,2})$').match(target)
        if pm:
            return Target("pace.zone", scale*pace_to_ms(pm.group(1)), scale*pace_to_ms(pm.group(2)))
            
    if re.compile('^.+ in .+$').match(step_txt):
        target = ms_to_pace(dist_time_to_ms(step_txt))
        target = add_pace_margins(target, config.get('margins', None))
        pm = re.compile(r'^(\d{1,2}:\d{1,2})-(\d{1,2}:\d{1,2})$').match(target)
        if pm:
            return Target("pace.zone", pace_to_ms(pm.group(1)), pace_to_ms(pm.group(2)))
    return None

def add_pace_margins(fixed_pace, margins):
    if not margins:
        return fixed_pace + '-' + fixed_pace
        
    fixed_pace_s = hhmmss_to_seconds(fixed_pace)
    fast_margin_s = hhmmss_to_seconds(margins['faster'])
    slow_margin_s = hhmmss_to_seconds(margins['slower'])
    fast_pace_s = fixed_pace_s - fast_margin_s
    slow_pace_s = fixed_pace_s + slow_margin_s
    return seconds_to_mmss(slow_pace_s) + '-' + seconds_to_mmss(fast_pace_s)

def expand_config(config):
    paces = config.get('paces', [])
    # If we find paces in <distance> in <time> format, convert them to mm:ss
    for pk, pv in paces.items():
        if re.compile('^.+ in .+$').match(pv.strip()):
            paces[pk] = ms_to_pace(dist_time_to_ms(pv))
    return