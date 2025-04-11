# File: planner/yaml_to_tcx.py

import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import datetime
import yaml
import os
import re
import logging

from .utils import hhmmss_to_seconds, pace_to_ms, dist_to_m
from .workout import Workout, WorkoutStep, Target
from .import_export import import_workouts

def prettify_xml(elem):
    """Restituisce una versione formattata dell'elemento XML"""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def create_tcx_from_workout(workout):
    """
    Converte un oggetto Workout in un documento TCX.
    
    Args:
        workout: Oggetto Workout da convertire
        
    Returns:
        Una stringa contenente il documento TCX formattato
    """
    # Crea l'elemento root
    training_center_db = ET.Element('TrainingCenterDatabase')
    training_center_db.set('xmlns', 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2')
    training_center_db.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    training_center_db.set('xsi:schemaLocation', 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd')
    
    # Aggiungi elementi Folders e Workouts
    folders = ET.SubElement(training_center_db, 'Folders')
    workouts = ET.SubElement(folders, 'Workouts')
    workout_folder = ET.SubElement(workouts, 'WorkoutFolder')
    workout_folder.set('Name', 'My Workouts')
    
    # Aggiungi l'elemento Workouts
    workouts_element = ET.SubElement(training_center_db, 'Workouts')
    workout_element = ET.SubElement(workouts_element, 'Workout')
    workout_element.set('Sport', workout.sport_type.capitalize())
    
    # Aggiungi nome e descrizione
    name = ET.SubElement(workout_element, 'Name')
    name.text = workout.workout_name
    
    if workout.description:
        notes = ET.SubElement(workout_element, 'Notes')
        notes.text = workout.description
    
    # Aggiungi gli step dell'allenamento
    add_workout_steps(workout_element, workout.workout_steps)
    
    # Esporta l'XML formattato
    return prettify_xml(training_center_db)

def add_workout_steps(workout_element, steps, parent_element=None):
    """
    Aggiunge gli step dell'allenamento all'elemento workout.
    
    Args:
        workout_element: Elemento XML del workout
        steps: Lista di oggetti WorkoutStep da aggiungere
        parent_element: Elemento genitore per gli step (usato per step nidificati)
    """
    target_element = workout_element if parent_element is None else parent_element
    
    for i, step in enumerate(steps):
        step_element = ET.SubElement(target_element, 'Step')
        
        # Step ID univoco
        step_id = ET.SubElement(step_element, 'StepId')
        step_id.text = str(i + 1)
        
        # Nome dello step (tipo + descrizione)
        step_name = ET.SubElement(step_element, 'Name')
        step_name.text = f"{step.step_type.capitalize()}"
        if step.description:
            step_name.text += f": {step.description}"
        
        # Gestisci i tipi di step speciali (repeat)
        if step.step_type == 'repeat':
            # Questo è un gruppo di ripetizioni
            repeat = ET.SubElement(step_element, 'Repeat')
            repeat_count = ET.SubElement(repeat, 'RepeatCount')
            repeat_count.text = str(step.end_condition_value)
            
            # Crea gli step per ogni ripetizione
            child_steps = ET.SubElement(repeat, 'Steps')
            add_workout_steps(workout_element, step.workout_steps, child_steps)
            continue
        
        # Durata dello step
        duration = ET.SubElement(step_element, 'Duration')
        duration_type = 'Time' if step.end_condition == 'time' else 'Distance' if step.end_condition == 'distance' else 'Open'
        
        duration_type_elem = ET.SubElement(duration, duration_type)
        
        if duration_type == 'Time':
            # Durata in secondi
            seconds = step.parsed_end_condition_value()
            value = ET.SubElement(duration_type_elem, 'Seconds')
            value.text = str(seconds)
        elif duration_type == 'Distance':
            # Distanza in metri
            meters = step.parsed_end_condition_value()
            value = ET.SubElement(duration_type_elem, 'Meters')
            value.text = str(meters)
        
        # Target dello step
        target = ET.SubElement(step_element, 'Target')
        
        if step.target.target == 'no.target':
            # Nessun target
            target_type = ET.SubElement(target, 'None')
        elif step.target.target == 'pace.zone':
            # Target di passo
            target_type = ET.SubElement(target, 'Speed')
            zone = ET.SubElement(target_type, 'Zone')
            speed_zone = ET.SubElement(zone, 'SpeedZone')
            
            # Converti da m/s a secondi/km per il TCX
            low_speed = step.target.from_value  # m/s
            high_speed = step.target.to_value   # m/s
            
            # Assicurati che i valori non siano None o zero
            if low_speed is None or low_speed == 0:
                low_speed = 0.1  # valore predefinito
            if high_speed is None or high_speed == 0:
                high_speed = low_speed
                
            low_in_ms = ET.SubElement(speed_zone, 'LowInMetersPerSecond')
            low_in_ms.text = str(round(low_speed, 2))
            
            high_in_ms = ET.SubElement(speed_zone, 'HighInMetersPerSecond')
            high_in_ms.text = str(round(high_speed, 2))
        elif step.target.target == 'heart.rate.zone':
            # Target di frequenza cardiaca
            target_type = ET.SubElement(target, 'HeartRate')
            zone = ET.SubElement(target_type, 'Zone')
            hr_zone = ET.SubElement(zone, 'HeartRateZone')
            
            low = ET.SubElement(hr_zone, 'Low')
            low.text = str(step.target.from_value if step.target.from_value else 100)
            
            high = ET.SubElement(hr_zone, 'High')
            high.text = str(step.target.to_value if step.target.to_value else 160)
        else:
            # Altri tipi di target non supportati, usa None
            target_type = ET.SubElement(target, 'None')
        
        # Intensità (predefinita a Active)
        intensity = ET.SubElement(step_element, 'Intensity')
        intensity.text = 'Active' if step.step_type not in ['rest', 'recovery'] else 'Recovery'

def yaml_to_tcx(yaml_workouts):
    """
    Converte gli allenamenti da un file YAML in formato TCX.
    
    Args:
        yaml_workouts: Dizionario o lista contenente gli allenamenti dal file YAML
        
    Returns:
        Dizionario con nome_allenamento: contenuto_tcx
    """
    tcx_files = {}
    temp_yaml_path = None
    
    try:
        # Crea un file temporaneo per l'importazione
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_yaml_path = temp_file.name
            
            # Scrivi il contenuto YAML nel file temporaneo
            logging.debug(f"Tipo di yaml_workouts: {type(yaml_workouts)}")
            
            import yaml
            # Converti a un formato compatibile se necessario
            if isinstance(yaml_workouts, list):
                # Se è una lista, crea un dizionario usando gli ID come chiavi
                converted_workouts = {}
                for workout in yaml_workouts:
                    # Se l'allenamento ha un nome, usalo come chiave
                    workout_name = workout.get('workoutName', f"Workout_{workout.get('workoutId', 'unknown')}")
                    converted_workouts[workout_name] = workout
                yaml_workouts = converted_workouts
            
            with open(temp_yaml_path, 'w') as f:
                yaml.dump(yaml_workouts, f)
            
            # Importa i workout dal file temporaneo
            from .import_export import import_workouts
            workouts = import_workouts(temp_yaml_path)
            
            # Converti ciascun workout in TCX
            for workout in workouts:
                tcx_content = create_tcx_from_workout(workout)
                tcx_files[workout.workout_name] = tcx_content
            
    except Exception as e:
        logging.error(f"Errore nella conversione YAML->TCX: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        raise
    
    finally:
        # Pulizia del file temporaneo - gestione robusta
        if temp_yaml_path and os.path.exists(temp_yaml_path):
            try:
                os.unlink(temp_yaml_path)
            except Exception as e:
                logging.warning(f"Impossibile eliminare il file temporaneo {temp_yaml_path}: {str(e)}")
                # Non propagare questa eccezione, è solo un warning
    
    return tcx_files

def cmd_export_tcx(args):
    """
    Esporta gli allenamenti in formato TCX.
    
    Args:
        args: Gli argomenti del comando dalla linea di comando
    """
    # Ottieni i workout in formato YAML
    from .import_export import cmd_export_workouts
    
    # Esporta i workout in un file temporaneo
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
        temp_yaml_path = temp_file.name
    
    # Modifica gli argomenti per esportare in YAML
    args.export_file = temp_yaml_path
    args.format = 'YAML'
    
    # Esporta in YAML
    cmd_export_workouts(args)
    
    # Leggi il file YAML
    with open(temp_yaml_path, 'r') as f:
        workouts_yaml = yaml.safe_load(f)
    
    # Rimuovi il file temporaneo
    os.unlink(temp_yaml_path)
    
    # Converti in TCX
    tcx_files = yaml_to_tcx(workouts_yaml)
    
    # Salva i file TCX
    if len(tcx_files) == 1:
        # Se c'è un solo allenamento, salva direttamente nel file specificato
        workout_name, tcx_content = next(iter(tcx_files.items()))
        with open(args.export_file, 'w') as f:
            f.write(tcx_content)
        logging.info(f"Allenamento '{workout_name}' esportato come TCX in {args.export_file}")
    else:
        # Se ci sono più allenamenti, crea una directory e salva ciascuno come file separato
        base_path = os.path.splitext(args.export_file)[0]
        if not os.path.exists(base_path):
            os.makedirs(base_path, exist_ok=True)
        
        for workout_name, tcx_content in tcx_files.items():
            # Crea un nome di file valido dal nome dell'allenamento
            safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in workout_name)
            file_path = os.path.join(base_path, f"{safe_name}.tcx")
            
            with open(file_path, 'w') as f:
                f.write(tcx_content)
            
        logging.info(f"Esportati {len(tcx_files)} allenamenti in formato TCX nella cartella {base_path}")
    
    return None