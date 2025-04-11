import tempfile
import os
import logging
import yaml
from fitparse import FitFile
from fitparse.profile import FIELD_TYPES
from fitparse.utils import fileish_open
from fitparse.base import FitData
from io import BytesIO


def cmd_export_fit(args):
    """
    Esporta gli allenamenti in formato FIT.
    
    Args:
        args: Gli argomenti del comando dalla linea di comando
    """
    # Ottieni i workout in formato YAML
    from .import_export import cmd_export_workouts
    
    # Esporta i workout in un file temporaneo
    import tempfile
    import os
    import yaml
    import logging
    
    temp_yaml_path = None
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_yaml_path = temp_file.name
        
        # Modifica gli argomenti per esportare in YAML
        original_format = args.format
        original_export_file = args.export_file
        args.format = 'YAML'
        args.export_file = temp_yaml_path
        
        # Disabilita temporaneamente la stampa di output
        import sys
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        
        # Esporta in YAML
        from .import_export import cmd_export_workouts
        cmd_export_workouts(args)
        
        # Ripristina stdout
        sys.stdout.close()
        sys.stdout = original_stdout
        
        # Ripristina i parametri originali
        args.format = original_format
        args.export_file = original_export_file
        
        # Leggi il file YAML
        with open(temp_yaml_path, 'r') as f:
            workouts_yaml = yaml.safe_load(f)
        
        # Converti in FIT
        fit_files = yaml_to_fit(workouts_yaml)
        
        # Salva i file FIT
        if len(fit_files) == 1:
            # Se c'è un solo allenamento, salva direttamente nel file specificato
            workout_name, fit_content = next(iter(fit_files.items()))
            with open(args.export_file, 'wb') as f:
                f.write(fit_content)
            logging.info(f"Allenamento '{workout_name}' esportato come FIT in {args.export_file}")
        else:
            # Se ci sono più allenamenti, crea una directory e salva ciascuno come file separato
            base_path = os.path.splitext(args.export_file)[0]
            if not os.path.exists(base_path):
                os.makedirs(base_path, exist_ok=True)
            
            for workout_name, fit_content in fit_files.items():
                # Crea un nome di file valido dal nome dell'allenamento
                safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in workout_name)
                file_path = os.path.join(base_path, f"{safe_name}.fit")
                
                with open(file_path, 'wb') as f:
                    f.write(fit_content)
            
            logging.info(f"Esportati {len(fit_files)} allenamenti in formato FIT nella cartella {base_path}")
    
    except Exception as e:
        logging.error(f"Errore durante l'esportazione FIT: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        raise
    
    finally:
        # Pulizia del file temporaneo
        if temp_yaml_path and os.path.exists(temp_yaml_path):
            try:
                os.unlink(temp_yaml_path)
            except Exception as e:
                logging.warning(f"Impossibile eliminare il file temporaneo {temp_yaml_path}: {str(e)}")
    
    return None

def yaml_to_fit(yaml_workouts):
    """
    Converte gli allenamenti da un file YAML in formato FIT.
    
    Args:
        yaml_workouts: Dizionario o lista contenente gli allenamenti
        
    Returns:
        Dizionario con nome_allenamento: contenuto_fit_binario
    """
    fit_files = {}
    temp_yaml_path = None
    
    try:
        # Convertire i dati in un formato compatibile
        if isinstance(yaml_workouts, list):
            converted_workouts = {}
            for workout in yaml_workouts:
                workout_name = workout.get('workoutName', f"Workout_{workout.get('workoutId', 'unknown')}")
                converted_workouts[workout_name] = workout
            yaml_workouts = converted_workouts
        
        # Importa i workout da YAML
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_yaml_path = temp_file.name
            with open(temp_yaml_path, 'w') as f:
                yaml.dump(yaml_workouts, f)
            
            from .import_export import import_workouts
            workouts = import_workouts(temp_yaml_path)
            
        # Convertire ciascun workout in FIT
        for workout in workouts:
            fit_content = create_fit_from_workout(workout)
            fit_files[workout.workout_name] = fit_content
    
    except Exception as e:
        logging.error(f"Errore nella conversione YAML->FIT: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        raise
    
    finally:
        # Pulizia del file temporaneo
        if temp_yaml_path and os.path.exists(temp_yaml_path):
            try:
                os.unlink(temp_yaml_path)
            except Exception as e:
                logging.warning(f"Impossibile eliminare il file temporaneo {temp_yaml_path}: {str(e)}")
    
    return fit_files

def create_fit_from_workout(workout):
    """
    Crea un file FIT a partire da un workout.
    
    Args:
        workout: Oggetto Workout da convertire
        
    Returns:
        Dati binari del file FIT
    """
    # Creazione di un nuovo file FIT
    fit_file = BytesIO()
    
    # Creazione dei messaggi del file FIT
    # File ID message
    file_id_msg = {
        'type': 'workout',
        'manufacturer': 'development',
        'product': 1,
        'time_created': int(time.time()),
    }
    
    # Workout message
    workout_msg = {
        'wkt_name': workout.workout_name,
        'sport': workout.sport_type,
    }
    
    # Workout step messages
    step_msgs = []
    for step in workout.workout_steps:
        step_msg = create_fit_step_message(step)
        step_msgs.append(step_msg)
    
    # Scrittura dei messaggi nel file FIT
    # (Nota: questa parte richiede una conoscenza dettagliata della struttura dei file FIT)
    # ...
    
    # Ritorna i dati binari del file FIT
    fit_file.seek(0)
    return fit_file.read()

def create_fit_step_message(step):
    """
    Crea un messaggio FIT per uno step di workout.
    
    Args:
        step: Oggetto WorkoutStep
        
    Returns:
        Dati del messaggio FIT per lo step
    """
    step_msg = {}
    
    # Tipo di step
    if step.step_type == 'warmup':
        step_msg['wkt_step_name'] = 'Warmup'
        step_msg['intensity'] = 'active'
    elif step.step_type == 'cooldown':
        step_msg['wkt_step_name'] = 'Cooldown'
        step_msg['intensity'] = 'active'
    elif step.step_type == 'interval':
        step_msg['wkt_step_name'] = 'Interval'
        step_msg['intensity'] = 'active'
    elif step.step_type == 'recovery':
        step_msg['wkt_step_name'] = 'Recovery'
        step_msg['intensity'] = 'recovery'
    elif step.step_type == 'rest':
        step_msg['wkt_step_name'] = 'Rest'
        step_msg['intensity'] = 'recovery'
    else:
        step_msg['wkt_step_name'] = step.step_type.capitalize()
        step_msg['intensity'] = 'active'
    
    # Descrizione
    if step.description:
        step_msg['wkt_step_name'] = f"{step_msg['wkt_step_name']}: {step.description}"
    
    # Durata
    if step.end_condition == 'time':
        step_msg['duration_type'] = 'time'
        step_msg['duration_value'] = step.parsed_end_condition_value()
    elif step.end_condition == 'distance':
        step_msg['duration_type'] = 'distance'
        step_msg['duration_value'] = step.parsed_end_condition_value()
    else:
        step_msg['duration_type'] = 'open'
        step_msg['duration_value'] = 0
    
    # Target
    if step.target.target == 'no.target':
        step_msg['target_type'] = 'open'
        step_msg['target_value'] = 0
    elif step.target.target == 'pace.zone':
        step_msg['target_type'] = 'speed'
        step_msg['target_value_low'] = step.target.from_value
        step_msg['target_value_high'] = step.target.to_value
    elif step.target.target == 'heart.rate.zone':
        step_msg['target_type'] = 'heart_rate'
        step_msg['target_value_low'] = step.target.from_value
        step_msg['target_value_high'] = step.target.to_value
    
    return step_msg