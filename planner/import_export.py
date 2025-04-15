"""
Import and export functionality for Garmin workouts.

This module provides functionality to import workouts from YAML files
and export workouts to YAML or JSON files.
"""

import yaml
import re
import logging
import json
import os
import copy

from .utils import ms_to_pace, dist_time_to_ms, get_pace_range, pace_to_ms
from .workout import Target, Workout, WorkoutStep
from planner.garmin_client import GarminClient

# Keys to remove when cleaning workout data for export
CLEAN_KEYS = ['author', 'createdDate', 'ownerId', 'shared', 'updatedDate']

# Global configuration
config = {}

def cmd_import_workouts(args):
    """
    Import workouts from a YAML file to Garmin Connect.
    
    Args:
        args: Command line arguments with the following attributes:
            - workouts_file: Path to the YAML file
            - name_filter: Optional regex to filter workout names
            - oauth_folder: Path to the OAuth folder
            - dry_run: If True, only show what would be imported
            - replace: If True, replace existing workouts with the same name
            - treadmill: If True, convert distance end conditions to time
    """
    logging.info('Importing workouts from ' + args.workouts_file)
    existing_workouts = []

    client = GarminClient(args.oauth_folder)
    if not args.dry_run:
        if args.replace:
            existing_workouts = client.list_workouts()

    for workout in import_workouts(args.workouts_file, args.name_filter):
        if args.treadmill or workout.workout_name.strip().endswith('(T)'):
            workout.dist_to_time()

        if args.dry_run:
            print(json.dumps(workout.garminconnect_json()))
        else:
            logging.info('Creating workout: ' + workout.workout_name)
            workouts_to_delete = []
            id_to_replace = None
            if args.replace:
                for wo in existing_workouts:
                    if wo['workoutName'] == workout.workout_name:
                        id_to_replace = wo['workoutId']
            if id_to_replace is not None:
                client.update_workout(id_to_replace, workout)
            else:
                client.add_workout(workout)

    return None

def cmd_export_workouts(args):
    """
    Export workouts from Garmin Connect to a file.
    
    Args:
        args: Command line arguments with the following attributes:
            - export_file: Path to the output file
            - format: Output format (JSON or YAML)
            - clean: If True, remove unnecessary data
            - name_filter: Optional regex to filter workout names
            - workout_ids: Optional comma-separated list of workout IDs
            - oauth_folder: Path to the OAuth folder
    """
    client = GarminClient(args.oauth_folder)
    all_workouts = client.list_workouts()
    workout_ids = all_workouts  # Default to all workouts

    # Filter by workout_ids if specified
    if args.workout_ids:
        specified_ids = args.workout_ids.split(',')
        filtered_workouts = []
        for workout in all_workouts:
            if str(workout['workoutId']) in specified_ids:
                filtered_workouts.append(workout)
        workout_ids = filtered_workouts
        logging.info(f'Filtering to {len(workout_ids)} workouts by ID')

    # Filter by name_filter if specified (only if not already filtered by IDs)
    elif args.name_filter:
        filtered_workouts = []
        for workout in all_workouts:
            if re.search(args.name_filter, workout['workoutName']):
                filtered_workouts.append(workout)
        workout_ids = filtered_workouts
        logging.info(f'Filtering to {len(workout_ids)} workouts by name pattern')

    workouts = []
    for wid in workout_ids:
        workout = client.get_workout(wid['workoutId'])
        if args.clean:
            clean_workout_data(workout)
        workouts.append(workout)

    # Determine output format
    export_format = args.format

    # If export format was not specified in the command line, use file extension
    if not export_format and args.export_file:
        file_extension = args.export_file.split('.')[-1].upper() if '.' in args.export_file else None
        if file_extension in ['JSON', 'JSN']:
            export_format = 'JSON'
        elif file_extension in ['YAML', 'YML']:
            export_format = 'YAML'

    # Format the output
    if not export_format or export_format == 'JSON':
        formatted_output = json.dumps(workouts, indent=2)
    elif export_format == 'YAML':
        formatted_output = yaml.dump(workouts)
    else:
        logging.warning(f'Unknown export format: {export_format}. Using JSON.')
        formatted_output = json.dumps(workouts, indent=2)

    # Write to file or stdout
    if args.export_file:
        logging.info('Exporting workouts to file '+ args.export_file)
        with open(args.export_file, 'w') as f:
            f.write(formatted_output)
    else:
        print(formatted_output)

    return None

def cmd_delete_workouts(args):
    """
    Delete workouts from Garmin Connect.
    
    Args:
        args: Command line arguments with the following attributes:
            - workout_ids: Optional comma-separated list of workout IDs
            - name_filter: Optional regex to filter workout names
            - oauth_folder: Path to the OAuth folder
    """
    valid_ids = []
    client = GarminClient(args.oauth_folder)
    if args.workout_ids:
        if ',' in args.workout_ids:
            workout_ids = args.workout_ids.split(',')
        else:
            workout_ids = [args.workout_ids]

        # Filter out invalid workout IDs
        for workout_id in workout_ids:
            if not re.match(r'^\d{9,10}$', workout_id):
                logging.warning(f'Ignoring invalid workout id "{workout_id}". Must be 9 or 10 digit number.')
            else:
                valid_ids.append(workout_id)

    if args.name_filter:
        logging.info(f'Getting list of workouts.')
        workouts_list = client.list_workouts()
        for workout in workouts_list:
            if re.search(args.name_filter, workout['workoutName']):
                logging.info(f'Found workout named "{workout["workoutName"]}" with ID {workout["workoutId"]}.')
                valid_ids.append(str(workout['workoutId']))

    if len(valid_ids) == 0:
        logging.warning('Could not find any valid workout ID.')
        return

    for workout_id in valid_ids:
        res = client.delete_workout(workout_id)
        if res:
            logging.info(f'Successfully deleted workout {workout_id}')
        else:
            logging.warning(f'Failed to delete workout {workout_id}')

    return None

def clean_workout_data(wo_dict):
    """
    Clean workout data by removing unnecessary fields.
    
    Args:
        wo_dict: Workout dictionary to clean
        
    Returns:
        Number of items remaining in the dictionary
    """
    if isinstance(wo_dict, list):
        for ldict in wo_dict:
            clean_workout_data(ldict)
    elif isinstance(wo_dict, dict):
        keys = list(wo_dict.keys())
        for k in keys:
            v = wo_dict[k]
            if k in CLEAN_KEYS or v is None or v == 'null':
                del wo_dict[k]
            elif isinstance(v, dict) or isinstance(v, list):
                final_size = clean_workout_data(v)
                if final_size == 0:
                    del wo_dict[k]
    return len(wo_dict)

def import_workouts(plan_file, name_filter=None):
    """
    Import workouts from a YAML file.
    
    Args:
        plan_file: Path to the YAML file
        name_filter: Optional regex to filter workout names
        
    Returns:
        List of Workout objects
    """
    # Load the file to get workout descriptions (added as comments in the YAML file)
    descriptions = {}
    with open(plan_file, 'r', encoding='utf-8') as yfile:
        line_pattern = re.compile(r'^([^:]+):\s*#\s*(.*)\s*$')
        for line in yfile:
            m = line_pattern.match(line)
            if m:
                key = m.group(1)
                comment = m.group(2)
                descriptions[key] = comment

    with open(plan_file, 'r', encoding='utf-8') as file:
        workouts = []
        import_json = yaml.safe_load(file)

        # Remove the config entry, if present
        global config
        config = import_json.pop('config', {})

        # Fix the configuration before expanding it
        fix_config(config)
        expand_config(config)

        for name, steps in import_json.items():
            if name_filter and not re.search(name_filter, name):
                continue

            # Remove any date information from the name
            name = re.sub(r'\s+\(Data:.*\)', '', name)

            # Fix repeat steps before creating the workout
            fix_steps(steps)

            w = Workout("running", config.get('name_prefix', '') + name, descriptions.get(name, None))
            
            # Estrai la data, se presente, come primo elemento
            workout_date = None
            if steps and isinstance(steps, list) and len(steps) > 0:
                first_step = steps[0]
                if isinstance(first_step, dict) and 'date' in first_step:
                    workout_date = first_step['date']
                    # Rimuovi l'elemento date dalla lista degli step
                    steps = steps[1:]
            
            # Aggiungi la data alla descrizione del workout se presente
            if workout_date:
                if w.description:
                    w.description += f" (Data: {workout_date})"
                else:
                    w.description = f"Data: {workout_date}"
            
            for step in steps:
                for k, v in step.items():
                    if k == 'repeat':
                        # Handle repeat structure correctly
                        iterations = v
                        substeps = step.get('steps', [])
                        
                        # Create the repeat step
                        ws = WorkoutStep(
                            0,
                            'repeat',
                            '',
                            end_condition='iterations',
                            end_condition_value=iterations
                        )
                        
                        # Add substeps
                        for substep in substeps:
                            for sk, sv in substep.items():
                                sub_end_condition = get_end_condition(sv)
                                sub_target = get_target(sv)
                                rws = WorkoutStep(
                                    0,
                                    sk,
                                    get_description(sv, sub_target),
                                    end_condition=sub_end_condition,
                                    end_condition_value=get_end_condition_value(sv, sub_end_condition),
                                    target=sub_target
                                )
                                ws.add_step(rws)
                        
                        w.add_step(ws)
                    elif not k.startswith('repeat') and k != 'steps':
                        end_condition = get_end_condition(v)
                        ws_target = get_target(v)
                        ws = WorkoutStep(
                            0,
                            k,
                            get_description(v, ws_target),
                            end_condition=end_condition,
                            end_condition_value=get_end_condition_value(v, end_condition),
                            target=ws_target
                        )
                        w.add_step(ws)

            workouts.append(w)
        return workouts

def fix_config(config):
    """
    Fix configuration values before expanding.
    Ensures that numeric values are actually numeric.
    
    Args:
        config: Configuration dictionary to fix
    """
    if 'heart_rates' in config:
        for key, value in config['heart_rates'].items():
            if isinstance(value, str) and value.isdigit():
                config['heart_rates'][key] = int(value)

def fix_steps(steps):
    """
    Fix the structure of workout steps.
    
    Args:
        steps: List of workout steps to fix
    """
    if not isinstance(steps, list):
        return
    
    for step in steps:
        if not isinstance(step, dict):
            continue
            
        # Check for keys starting with 'repeat '
        for key in list(step.keys()):
            repeat_match = re.match(r'^repeat\s+(\d+)$', key)
            if repeat_match:
                iterations = int(repeat_match.group(1))
                substeps = step.pop(key)  # Remove the old key
                
                # Create the new repeat structure
                step['repeat'] = iterations
                step['steps'] = substeps
                
                # Recursively fix substeps
                fix_steps(substeps)

def get_description(step_txt, target=None):
    """
    Extract a description from a step text.
    
    Args:
        step_txt: Text describing the step
        target: Optional Target object
        
    Returns:
        Description string
    """
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

def get_end_condition(step_txt):
    """
    Determine the end condition from a step text.
    
    Args:
        step_txt: Text describing the step
        
    Returns:
        End condition string
    """
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
    """
    Extract the end condition value from a step text.
    
    Args:
        step_txt: Text describing the step
        condition_type: Type of end condition
        
    Returns:
        End condition value
    """
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

def get_target(step_txt, verbose=False):
    """
    Extract a target from a step text.
    
    Args:
        step_txt: Text describing the step
        verbose: If True, print verbose information
        
    Returns:
        Target object
    """
    step_txt = clean_step(step_txt)
    target_type = None
    target = None
    scale_min = 1
    scale_max = 1
    
    if verbose:
        print(f"Processing step: {step_txt}")
    
    if ' in ' in step_txt:
        target_type = 'pace.zone'
        target = ms_to_pace(dist_time_to_ms(step_txt))
    elif ' @ ' in step_txt:
        parts = [p.strip() for p in step_txt.split(' @ ')]
        target = parts[1]
        
        # Check if this is a heart rate target with _HR suffix - these are ALWAYS heart rate zones
        if '_HR' in target:
            target_type = 'heart.rate.zone'
            
            # Look up directly in config.heart_rates with the _HR suffix included
            if target in config.get('heart_rates', {}):
                target_value = config['heart_rates'][target]
                if verbose:
                    print(f"Found in heart_rates with _HR suffix: {target} -> {target_value}")
                target = target_value
            else:
                # Try removing the _HR suffix and look up in heart_rates
                clean_target = target.replace('_HR', '')
                if clean_target in config.get('heart_rates', {}):
                    target_value = config['heart_rates'][clean_target]
                    if verbose:
                        print(f"Found in heart_rates after removing _HR: {clean_target} -> {target_value}")
                    target = target_value
                else:
                    # If we can't find it, try using Zx format directly
                    if clean_target.lower() in ['z1', 'z2', 'z3', 'z4', 'z5']:
                        zone_num = int(clean_target[1:])
                        if verbose:
                            print(f"Using direct HR zone reference: {zone_num}")
                        return Target('heart.rate.zone', zone=zone_num)
                    else:
                        # Still can't find it, check if a key with _HR suffix exists in heart_rates
                        hr_key = f"{clean_target}_HR"
                        if hr_key in config.get('heart_rates', {}):
                            target_value = config['heart_rates'][hr_key]
                            if verbose:
                                print(f"Found by adding _HR: {hr_key} -> {target_value}")
                            target = target_value
                        
            # Convert integer target to range format
            if isinstance(target, int):
                target = f'{target}-{target}'
                
        # Check if target refers to a pace zone key in the paces config
        elif target in config.get('paces', {}):
            target_type = 'pace.zone'
            target_value = config['paces'][target]
            if verbose:
                print(f"Found in paces config: {target} -> {target_value}")
            target = target_value
            
        # Check if this is a plain Zx format (like Z1, Z2) - these should be pace zones by default
        # unless they're only defined in heart_rates
        elif re.match(r'^[zZ][1-5]$', target):
            zone_key = target.upper()  # Normalize to uppercase
            
            # Check if it exists in paces config
            if zone_key in config.get('paces', {}):
                target_type = 'pace.zone'
                target_value = config['paces'][zone_key]
                if verbose:
                    print(f"Found zone in paces config: {zone_key} -> {target_value}")
                target = target_value
            # If not in paces but is in heart_rates with _HR suffix, use heart rate
            elif zone_key + "_HR" in config.get('heart_rates', {}):
                target_type = 'heart.rate.zone'
                target_value = config['heart_rates'][zone_key + "_HR"]
                if verbose:
                    print(f"Zone not in paces but found in heart_rates: {zone_key}_HR -> {target_value}")
                target = target_value
                # Convert integer target to range format
                if isinstance(target, int):
                    target = f'{target}-{target}'
            # Last resort: map Z1-Z5 directly to pace zones
            else:
                target_type = 'pace.zone'
                zone_num = int(target[1:])
                if verbose:
                    print(f"Using zone number directly for pace zone: {zone_num}")
                # Map zones 1-5 to pace ranges
                zone_paces = {
                    1: "6:30",
                    2: "6:00",
                    3: "5:30",
                    4: "5:00",
                    5: "4:30"
                }
                target = zone_paces.get(zone_num, "5:00")  # Default to 5:00 if unknown
                if verbose:
                    print(f"Mapped to pace: {target}")
        else:
            # Process as pace zone for all other targets
            target_type = 'pace.zone'
            if re.compile(r'^\d{1,2}:\d{1,2}(?:-\d{1,2}:\d{1,2})?').match(target):
                pass  # Target is already in the correct format
            else:
                while not re.compile(r'^\d{1,2}:\d{1,2}(?:-\d{1,2}:\d{1,2})?').match(target):
                    # Check if the target is of type 75% marathon_pace
                    tm = re.compile(r'^(\d+-?\d+)%\s*(\S+)$').match(target)
                    if tm:
                        # Get the scale in the form 75% or 70-80%
                        scales = sorted([float(s)/100 for s in tm.group(1).split('-')])
                        scale_min = scale_max = scales[0]
                        if len(scales) == 2:
                            scale_max = scales[1]
                        target = tm.group(2).strip()
                    # Check if the target is found in the paces config block
                    if target in config.get('paces', {}):
                        target = config['paces'][target]
                    else:
                        raise ValueError(f'Cannot find pace target \'{target}\' in workout step \'{step_txt}\'')
    elif ' @hr ' in step_txt:
        target_type = 'heart.rate.zone'
        parts = [p.strip() for p in step_txt.split(' @hr ')]
        target = parts[1]
        
        # Check for both direct key and key with _HR suffix
        if target in config.get('heart_rates', {}):
            target = config['heart_rates'][target]
        elif target + "_HR" in config.get('heart_rates', {}):
            target = config['heart_rates'][target + "_HR"]
            
        if isinstance(target, int):
            target = f'{target}-{target}'
    else: # No target
        return None
    
    if target_type == 'pace.zone':
        target_range = get_pace_range(target, config.get('margins', None))
        return Target(target_type, scale_min*pace_to_ms(target_range[0]), scale_max*pace_to_ms(target_range[1]))
    elif target_type == 'heart.rate.zone':
        if re.compile(r'^\d{2,3}-\d{2,3}$').match(target):
            target_range = [int(t) for t in target.split('-')]
            return Target(target_type, target_range[0], target_range[1])
        m = re.compile(r'^(z|zone)[-_]?([1-5])$', re.IGNORECASE).match(target)
        if m:
            return Target(target_type, zone=int(m.group(2)))
            
        # Special handling for percentage-based ranges like "62-76% max_hr"
        pct_match = re.compile(r'^(\d+)-(\d+)%\s+(.+)$').match(target)
        if pct_match:
            low_pct = int(pct_match.group(1))
            high_pct = int(pct_match.group(2))
            base_hr_key = pct_match.group(3).strip()
            
            # Look up the base heart rate value (like max_hr)
            if base_hr_key in config.get('heart_rates', {}):
                base_hr = config['heart_rates'][base_hr_key]
                if isinstance(base_hr, int):
                    # Calculate the actual heart rate range
                    low_hr = int(base_hr * low_pct / 100)
                    high_hr = int(base_hr * high_pct / 100)
                    return Target(target_type, low_hr, high_hr)
        
        raise ValueError('Invalid heart rate target: ' + step_txt)
        
    raise ValueError('Invalid step description: ' + step_txt)

def clean_step(step_txt):
    """
    Remove description from a step text.
    
    Args:
        step_txt: Text describing the step
        
    Returns:
        Cleaned step text
    """
    # Remove description, if any
    if ' -- ' in step_txt:
        step_txt = step_txt[:step_txt.find(' -- ')].strip()
    return step_txt    

def expand_config(config):
    """
    Expand configuration values.
    
    Args:
        config: Configuration dictionary to expand
    """
    # Expand paces
    paces = config.get('paces', {})
    for pk, pv in paces.items():
        if isinstance(pv, str) and re.compile('^.+ in .+$').match(pv.strip()):
            paces[pk] = ms_to_pace(dist_time_to_ms(pv))
    
    # Expand heart rates
    heart_rates = config.get('heart_rates', {})
    for hrk, hrv in list(heart_rates.items()):
        # If we get an integer, this is a fixed hr. We leave it as it is.
        if isinstance(hrv, int):
            continue

        # Make sure numeric values are actually numeric
        if isinstance(hrv, str) and hrv.isdigit():
            heart_rates[hrk] = int(hrv)
            continue

        # Handle percentage references
        if isinstance(hrv, str):
            m = re.compile(r'^\s*(\d+(?:-\d+)?)%\s*(.+)\s*$').match(hrv)
            if m:
                ref_hr_key = m.group(2).strip()
                if ref_hr_key in heart_rates:
                    ref_hr = heart_rates[ref_hr_key]
                    
                    # Make sure ref_hr is a number
                    if isinstance(ref_hr, str):
                        try:
                            ref_hr = int(ref_hr)
                            heart_rates[ref_hr_key] = ref_hr  # Update the reference value
                        except ValueError:
                            logging.warning(f"Cannot convert '{ref_hr_key}' to number: {ref_hr}")
                            continue
                    
                    hr_range_str = m.group(1)
                    hr_range = hr_range_str.split('-')
                    
                    # With a single percentage
                    if len(hr_range) == 1:
                        try:
                            percent = float(hr_range[0]) / 100
                            heart_rates[hrk] = int(ref_hr * percent)
                        except (ValueError, TypeError) as e:
                            logging.warning(f"Error in HR percentage conversion: {hr_range[0]} - {str(e)}")
                    # With a percentage range
                    else:
                        try:
                            low_percent = float(hr_range[0]) / 100
                            high_percent = float(hr_range[1]) / 100
                            low_hr = int(ref_hr * low_percent)
                            high_hr = int(ref_hr * high_percent)
                            heart_rates[hrk] = f"{low_hr}-{high_hr}"
                        except (ValueError, TypeError) as e:
                            logging.warning(f"Error in HR percentage range conversion: {hr_range} - {str(e)}")
                else:
                    logging.warning(f"Error: HR reference '{ref_hr_key}' not found for '{hrk}'")
    
    return config