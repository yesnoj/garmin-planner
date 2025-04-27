#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Excel to YAML Converter for Garmin Planner with Scheduling Support

This module converts a structured Excel file into a YAML file compatible with garmin-planner.
It includes support for a Date column with workout scheduling.
"""

import pandas as pd
import yaml
import re
import os
import sys
import copy
import openpyxl  # Aggiungi questa riga
from datetime import datetime
import argparse
import logging
import random
import string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Customize YAML dumper to avoid references/aliases
class NoAliasDumper(yaml.SafeDumper):
    """Custom YAML dumper that ignores aliases"""
    def ignore_aliases(self, data):
        return True

# Valid step types supported by garmin-planner
VALID_STEP_TYPES = {"warmup", "cooldown", "interval", "recovery", "rest", "repeat", "other"}


def yaml_to_excel(yaml_data, excel_file, create_new=False):
    """
    Converti i dati YAML in un file Excel.
    
    Args:
        yaml_data: Dizionario con i dati YAML
        excel_file: Percorso del file Excel di output
        create_new: Se True, crea un nuovo file. Se False, aggiorna un file esistente.
    
    Returns:
        True se la conversione è riuscita, False altrimenti
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        import os
        
        # Estrai la configurazione
        config = yaml_data.get('config', {})
        sport_type = config.get('sport_type', 'running')
        
        logging.info(f"Tipo di sport rilevato: {sport_type}")
        
        # NUOVO APPROCCIO: Se il file esiste, eliminalo prima di ricrearlo
        if os.path.exists(excel_file):
            try:
                os.remove(excel_file)
                logging.info(f"File Excel esistente eliminato: {excel_file}")
            except PermissionError:
                # Se non possiamo eliminare il file (potrebbe essere aperto), 
                # crea un nuovo file con un nome diverso
                dir_name = os.path.dirname(excel_file)
                base_name = os.path.basename(excel_file)
                name, ext = os.path.splitext(base_name)
                new_file = os.path.join(dir_name, f"{name}_new{ext}")
                logging.warning(f"Impossibile eliminare il file esistente. Creazione di un nuovo file: {new_file}")
                excel_file = new_file
        
        # Crea un nuovo file Excel con il tipo di sport corretto
        create_sample_excel(excel_file, sport_type)
        
        # Carica il nuovo file appena creato
        try:
            wb = openpyxl.load_workbook(excel_file)
        except Exception as e:
            logging.error(f"Errore nel caricamento del file Excel: {str(e)}")
            return False
        
        # Aggiorna la configurazione nel foglio Config
        if 'Config' in wb.sheetnames:
            update_config_sheet(wb['Config'], config)
        
        # Aggiorna i ritmi in base al tipo di sport - ora entrambi nel foglio Paces
        if 'Paces' in wb.sheetnames:
            # Crea una nuova versione del foglio Paces con entrambi i tipi di dati
            wb.remove(wb['Paces'])
            create_unified_paces_sheet(wb, sport_type)
            
            # Aggiorna i valori specifici per il tipo di sport attuale
            paces_sheet = wb['Paces']
            
            # Dobbiamo rilevare dove sono le sezioni per running e cycling
            running_section_start = None
            running_section_end = None
            cycling_section_start = None
            cycling_section_end = None
            
            for row in range(1, paces_sheet.max_row + 1):
                cell_value = paces_sheet.cell(row=row, column=1).value
                if isinstance(cell_value, str) and "RITMI PER LA CORSA" in cell_value:
                    running_section_start = row + 1
                elif isinstance(cell_value, str) and "VELOCITÀ PER IL CICLISMO" in cell_value:
                    if running_section_start and not running_section_end:
                        running_section_end = row - 2  # -2 per escludere la riga vuota
                    cycling_section_start = row + 1
            
            # Se non abbiamo trovato la fine della sezione cycling, è l'ultima riga prima della nota
            if cycling_section_start and not cycling_section_end:
                for row in range(cycling_section_start, paces_sheet.max_row + 1):
                    if not paces_sheet.cell(row=row, column=1).value:
                        cycling_section_end = row - 1
                        break
                # Se ancora non troviamo la fine, prendiamo l'ultima riga
                if not cycling_section_end:
                    cycling_section_end = paces_sheet.max_row - 1  # -1 per escludere la nota
            
            # Aggiorna i valori in base al tipo di sport
            if sport_type == "running" and running_section_start and running_section_end:
                # Aggiorna i valori per la corsa dalle configurazioni
                running_values = config.get('paces', {})
                for row in range(running_section_start, running_section_end + 1):
                    name = paces_sheet.cell(row=row, column=1).value
                    if name in running_values:
                        paces_sheet.cell(row=row, column=2).value = running_values[name]
            
            elif sport_type == "cycling" and cycling_section_start and cycling_section_end:
                # Aggiorna i valori per il ciclismo dalle configurazioni
                cycling_values = config.get('speeds', {})
                for row in range(cycling_section_start, cycling_section_end + 1):
                    name = paces_sheet.cell(row=row, column=1).value
                    if name in cycling_values:
                        paces_sheet.cell(row=row, column=2).value = cycling_values[name]
        
        # Aggiorna le frequenze cardiache
        if 'HeartRates' in wb.sheetnames:
            update_heart_rates_sheet(wb['HeartRates'], config.get('heart_rates', {}))
        
        # Definisci i colori per le settimane
        week_colors = [
            "FFF2CC",  # Light yellow
            "DAEEF3",  # Light blue
            "E2EFDA",  # Light green
            "FCE4D6",  # Light orange
            "EAD1DC",  # Light pink
            "D9D9D9",  # Light gray
        ]
        
        # Bordo per le celle
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Aggiorna gli allenamenti nel foglio Workouts
        if 'Workouts' in wb.sheetnames:
            workouts_sheet = wb['Workouts']
            
            # Mantieni le prime due righe (intestazione e nome atleta)
            if workouts_sheet.max_row > 2:
                for row in range(workouts_sheet.max_row, 2, -1):
                    workouts_sheet.delete_rows(row)
            
            # Imposta il nome dell'atleta se presente
            if 'athlete_name' in config:
                workouts_sheet['A1'] = f"Atleta: {config['athlete_name']}"
            
            # Ottieni la lista di allenamenti (escluso 'config')
            workouts = []
            for name, steps in yaml_data.items():
                if name != 'config' and isinstance(steps, list):
                    # Estrai informazioni dall'allenamento
                    match = re.match(r'W(\d+)S(\d+)\s+(.*)', name)
                    if match:
                        week = int(match.group(1))
                        session = int(match.group(2))
                        description = match.group(3)
                        
                        # Estrai la data se presente
                        workout_date = ""
                        workout_sport_type = sport_type  # Default al tipo di sport principale
                        
                        # Filtra i passi effettivi (escludendo metadati)
                        actual_steps = []
                        for step in steps:
                            if isinstance(step, dict):
                                if 'sport_type' in step:
                                    workout_sport_type = step['sport_type']
                                elif 'date' in step:
                                    workout_date = step['date']
                                else:
                                    actual_steps.append(step)
                        
                        # Converti i passi in formato leggibile e ben formattato, specificando il tipo di sport
                        steps_text = format_steps_for_excel(actual_steps, workout_sport_type)
                        
                        workouts.append((week, session, workout_date, description, steps_text, workout_sport_type))
            
            # Ordina gli allenamenti per settimana e sessione
            workouts.sort(key=lambda x: (x[0], x[1]))
            
            # Aggiungi gli allenamenti al foglio
            current_week = None
            current_color_index = 0
            
            row = 3  # Prima riga di dati (dopo intestazione e atleta)
            for week, session, workout_date, description, steps_text, workout_sport_type in workouts:
                # Se la settimana cambia, cambia il colore
                if week != current_week:
                    current_week = week
                    current_color_index = (week - 1) % len(week_colors)
                
                # Colore di sfondo per la riga corrente
                row_fill = PatternFill(start_color=week_colors[current_color_index],
                                     end_color=week_colors[current_color_index],
                                     fill_type="solid")
                
                # Aggiungi valori alle celle
                workouts_sheet.cell(row=row, column=1, value=week)
                workouts_sheet.cell(row=row, column=2, value=workout_date)
                workouts_sheet.cell(row=row, column=3, value=session)
                workouts_sheet.cell(row=row, column=4, value=description)
                workouts_sheet.cell(row=row, column=5, value=steps_text)
                
                # Applica colore di sfondo e bordo a tutte le celle della riga
                for col in range(1, 6):  # Colonne A-E
                    cell = workouts_sheet.cell(row=row, column=col)
                    cell.fill = row_fill
                    cell.border = thin_border
                    
                    # Imposta testo a capo e allineamento
                    cell.alignment = Alignment(wrapText=True, vertical='top')
                
                # Calcola l'altezza appropriata della riga in base al contenuto
                # Conta le linee di testo negli step (sia \n che ;)
                num_lines = 1 + steps_text.count('\n') + steps_text.count(';')
                
                # Considera l'indentazione per i repeat
                if 'repeat' in steps_text and '\n' in steps_text:
                    # Conta le linee indentate dopo repeat
                    lines_after_repeat = steps_text.split('repeat')[1].count('\n')
                    if lines_after_repeat > 0:
                        num_lines += lines_after_repeat - 1  # -1 perché la linea con 'repeat' è già contata
                
                # Altezza minima più altezza per ogni linea di testo (circa 15 punti per linea)
                row_height = max(20, 15 * num_lines)  # Altezza minima aumentata
                workouts_sheet.row_dimensions[row].height = row_height
                
                row += 1
            
            # Assicurati che le colonne abbiano la giusta larghezza
            workouts_sheet.column_dimensions['A'].width = 10  # Week
            workouts_sheet.column_dimensions['B'].width = 15  # Date
            workouts_sheet.column_dimensions['C'].width = 10  # Session
            workouts_sheet.column_dimensions['D'].width = 25  # Description
            workouts_sheet.column_dimensions['E'].width = 60  # Steps
        
        # Crea un foglio Examples unificato con esempi per entrambi i tipi di sport
        create_unified_examples_sheet(wb)
        
        # Assicurati che i fogli siano nell'ordine corretto
        sheet_order = ['Config', 'Paces', 'HeartRates', 'Workouts', 'Examples']
        
        # Riordina i fogli solo se necessario e solo quelli che esistono
        existing_sheets = []
        for sheet_name in sheet_order:
            if sheet_name in wb.sheetnames:
                existing_sheets.append(sheet_name)
        
        # Aggiungi eventuali fogli non specificati alla fine
        for sheet_name in wb.sheetnames:
            if sheet_name not in existing_sheets:
                existing_sheets.append(sheet_name)
        
        # Riordina i fogli
        try:
            wb._sheets = [wb[sheet_name] for sheet_name in existing_sheets]
        except Exception as e:
            logging.warning(f"Impossibile riordinare i fogli: {str(e)}")
        
        # Salva il file Excel
        try:
            wb.save(excel_file)
            logging.info(f"File Excel salvato con successo: {excel_file}")
            return True
        except Exception as e:
            logging.error(f"Errore nel salvataggio del file Excel: {str(e)}")
            return False
            
    except Exception as e:
        logging.error(f"Errore nella conversione YAML to Excel: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def format_steps_for_excel(steps, sport_type="running"):
    """
    Formatta i passi per il foglio Excel con la corretta indentazione.
    
    Args:
        steps: Lista di passi dell'allenamento
        sport_type: Tipo di sport ('running' o 'cycling')
        
    Returns:
        Testo formattato dei passi
    """
    formatted_steps = []
    
    for step in steps:
        if 'repeat' in step and 'steps' in step:
            # Passo di tipo repeat
            iterations = step['repeat']
            substeps = step['steps']
            
            # Formatta il passo di repeat
            formatted_steps.append(f"repeat {iterations}:")
            
            # Formatta i substeps con indentazione
            for substep in substeps:
                if isinstance(substep, dict) and len(substep) == 1:
                    substep_type = list(substep.keys())[0]
                    substep_detail = substep[substep_type]
                    
                    # Gestisci i diversi formati in base al tipo di sport
                    if sport_type == "cycling":
                        # Per il ciclismo, assicurati che @ diventi @spd nei passi che hanno zona di ritmo
                        if '@' in substep_detail and '@spd' not in substep_detail and '@hr' not in substep_detail:
                            substep_detail = substep_detail.replace('@', '@spd ')
                    else:  # running
                        # Per la corsa, assicurati che @spd diventi @ nei passi che hanno zona di velocità
                        if '@spd' in substep_detail:
                            substep_detail = substep_detail.replace('@spd ', '@')
                    
                    # Usa l'indentazione con due spazi per i substep
                    formatted_steps.append(f"  {substep_type}: {substep_detail}")
        
        elif isinstance(step, dict) and len(step) == 1:
            # Passo normale
            step_type = list(step.keys())[0]
            step_detail = step[step_type]
            
            # Gestisci i diversi formati in base al tipo di sport
            if sport_type == "cycling":
                # Per il ciclismo, assicurati che @ diventi @spd nei passi che hanno zona di ritmo
                if '@' in step_detail and '@spd' not in step_detail and '@hr' not in step_detail:
                    step_detail = step_detail.replace('@', '@spd ')
            else:  # running
                # Per la corsa, assicurati che @spd diventi @ nei passi che hanno zona di velocità
                if '@spd' in step_detail:
                    step_detail = step_detail.replace('@spd ', '@')
            
            formatted_steps.append(f"{step_type}: {step_detail}")
    
    return "\n".join(formatted_steps)




def excel_to_yaml(excel_file, output_file=None, sport_type="running"):
    """
    Converte un file Excel strutturato in un file YAML compatibile con garmin-planner.
    Include supporto per estrarre le date degli allenamenti e la data della gara.
    Ora estrae sia paces che speeds indipendentemente dal tipo di sport.
    
    Args:
        excel_file: Percorso del file Excel di input
        output_file: Percorso del file YAML di output (opzionale)
        sport_type: Tipo di sport ('running' o 'cycling')
    """
    # Se non viene specificato un file di output, creiamo uno con lo stesso nome ma estensione .yaml
    if output_file is None:
        output_file = os.path.splitext(excel_file)[0] + '.yaml'
    
    print(f"Convertendo {excel_file} in {output_file}...")
    
    # Carica il file Excel
    try:
        # Leggi esplicitamente con le intestazioni nella seconda riga (header=1)
        df = pd.read_excel(excel_file, sheet_name='Workouts', header=1)
        
        # Verifica che ci siano le colonne richieste
        required_cols = ['Week', 'Session', 'Description', 'Steps']
        if all(col in df.columns for col in required_cols):
            print("Foglio 'Workouts' trovato con intestazioni nella seconda riga.")
        else:
            # Verifica se le colonne esistono ma con case diverso
            df_cols_lower = [col.lower() for col in df.columns]
            missing = []
            
            for req_col in required_cols:
                if req_col.lower() not in df_cols_lower:
                    missing.append(req_col)
            
            if missing:
                raise ValueError(f"Colonne mancanti nel foglio 'Workouts': {', '.join(missing)}")
            else:
                # Rinomina le colonne per uniformarle
                rename_map = {}
                for col in df.columns:
                    for req_col in required_cols:
                        if col.lower() == req_col.lower():
                            rename_map[col] = req_col
                
                df = df.rename(columns=rename_map)
                print("Colonne rinominate per uniformità.")
        
        # Ora puoi continuare con la lettura del resto del file
        xls = pd.ExcelFile(excel_file)
        
    except Exception as e:
        raise ValueError(f"Errore nel caricamento del foglio 'Workouts': {str(e)}")
    
    # Dizionario che conterrà il piano completo
    plan = {'config': {
        'heart_rates': {},
        'paces': {},
        'speeds': {},  # Manteniamo sempre entrambe le sezioni
        'margins': {
            'faster': '0:03',
            'slower': '0:03',
            'faster_spd': '2.0',  # Margini per velocità in km/h
            'slower_spd': '2.0',
            'hr_up': 5,
            'hr_down': 5
        },
        'name_prefix': '',
    }}
    
    # Estrai il nome atleta dalla prima riga se presente
    try:
        athlete_row = pd.read_excel(excel_file, sheet_name='Workouts', header=None, nrows=1)
        athlete_text = str(athlete_row.iloc[0, 0])
        
        if athlete_text and athlete_text.strip().startswith("Atleta:"):
            athlete_name = athlete_text.replace("Atleta:", "").strip()
            if athlete_name:
                # Aggiungi il nome dell'atleta alla configurazione
                plan['config']['athlete_name'] = athlete_name
                print(f"Nome atleta estratto: {athlete_name}")
    except Exception as e:
        print(f"Nota: impossibile estrarre il nome dell'atleta: {str(e)}")
    
    # Estrai la data della gara SOLO dal foglio Config
    race_day = None
    try:
        if 'Config' in xls.sheet_names:
            config_df = pd.read_excel(excel_file, sheet_name='Config')
            race_day_rows = config_df[config_df.iloc[:, 0] == 'race_day']
            
            # Check for sport_type in Config sheet
            sport_type_rows = config_df[config_df.iloc[:, 0] == 'sport_type']
            if not sport_type_rows.empty and pd.notna(sport_type_rows.iloc[0, 1]):
                extracted_sport_type = str(sport_type_rows.iloc[0, 1]).strip().lower()
                if extracted_sport_type in ["running", "cycling"]:
                    sport_type = extracted_sport_type
                    print(f"Tipo di sport trovato nel foglio Config: {sport_type}")
            
            if not race_day_rows.empty and pd.notna(race_day_rows.iloc[0, 1]):
                race_day_value = race_day_rows.iloc[0, 1]
                
                # Gestisci diversi formati di data
                if isinstance(race_day_value, datetime):
                    race_day = race_day_value.strftime("%Y-%m-%d")
                elif isinstance(race_day_value, str):
                    try:
                        # Prova a interpretare il formato
                        if len(race_day_value) == 10 and race_day_value[4] == '-' and race_day_value[7] == '-':
                            # Già in formato YYYY-MM-DD
                            race_day = race_day_value
                        else:
                            # Prova altre interpretazioni comuni
                            try:
                                date_obj = datetime.strptime(race_day_value, "%d/%m/%Y").date()
                                race_day = date_obj.strftime("%Y-%m-%d")
                            except ValueError:
                                try:
                                    date_obj = datetime.strptime(race_day_value, "%m/%d/%Y").date()
                                    race_day = date_obj.strftime("%Y-%m-%d")
                                except ValueError:
                                    print(f"Impossibile interpretare la data: {race_day_value}")
                    except:
                        print(f"Errore nel parsing della data: {race_day_value}")
                else:
                    # Gestisci altri tipi di dato, come date numeriche
                    try:
                        race_day = pd.to_datetime(race_day_value).strftime("%Y-%m-%d")
                    except:
                        print(f"Impossibile convertire il valore in data: {race_day_value}")
                
                if race_day:
                    plan['config']['race_day'] = race_day
                    print(f"Data della gara trovata nel foglio Config: {race_day}")
            else:
                print("Campo 'race_day' non trovato nel foglio Config o valore mancante")
                # Qui potresti lanciare un'eccezione se la data della gara è obbligatoria
                raise ValueError("Data della gara (race_day) mancante nel foglio Config")
        else:
            print("Foglio Config non trovato nel file Excel")
            # Qui potresti lanciare un'eccezione se la data della gara è obbligatoria
            raise ValueError("Foglio Config mancante nel file Excel, impossibile determinare la data della gara")
    except Exception as e:
        print(f"Errore nell'estrazione della data della gara: {str(e)}")
        # Se la data della gara è considerata obbligatoria, rilancia l'eccezione
        raise ValueError(f"Impossibile determinare la data della gara: {str(e)}")
    
    # Estrai le informazioni di configurazione
    if 'Config' in xls.sheet_names:
        config_df = pd.read_excel(xls, 'Config', header=0)
        
        # Estrai il prefisso del nome (se presente)
        name_prefix_rows = config_df[config_df.iloc[:, 0] == 'name_prefix']
        if not name_prefix_rows.empty:
            # Assicurati che il prefisso termini con uno spazio
            prefix = str(name_prefix_rows.iloc[0, 1]).strip()
            # Aggiungi uno spazio alla fine se non c'è già
            if prefix and not prefix.endswith(' '):
                prefix = prefix + ' '
            plan['config']['name_prefix'] = prefix
        
        # Estrai i margini (se presenti)
        margins_rows = config_df[config_df.iloc[:, 0] == 'margins']
        if not margins_rows.empty:
            # Controlla se ci sono valori per i margini
            if pd.notna(margins_rows.iloc[0, 1]):
                if sport_type == "cycling":
                    plan['config']['margins']['faster_spd'] = str(margins_rows.iloc[0, 1]).strip()
                else:
                    plan['config']['margins']['faster'] = str(margins_rows.iloc[0, 1]).strip()
            if pd.notna(margins_rows.iloc[0, 2]):
                if sport_type == "cycling":
                    plan['config']['margins']['slower_spd'] = str(margins_rows.iloc[0, 2]).strip()
                else:
                    plan['config']['margins']['slower'] = str(margins_rows.iloc[0, 2]).strip()
            if pd.notna(margins_rows.iloc[0, 3]):
                plan['config']['margins']['hr_up'] = int(margins_rows.iloc[0, 3])
            if pd.notna(margins_rows.iloc[0, 4]):
                plan['config']['margins']['hr_down'] = int(margins_rows.iloc[0, 4])
        
        # Estrai preferred_days se presente
        preferred_days_rows = config_df[config_df.iloc[:, 0] == 'preferred_days']
        if not preferred_days_rows.empty and pd.notna(preferred_days_rows.iloc[0, 1]):
            preferred_days_value = str(preferred_days_rows.iloc[0, 1]).strip()
            plan['config']['preferred_days'] = preferred_days_value
    
    # NUOVA IMPLEMENTAZIONE: Utilizzare il parser migliorato per estrarre ritmi e velocità
    if 'Paces' in xls.sheet_names:
        paces, speeds = extract_paces_and_speeds_from_excel(excel_file)
        
        # Aggiorna il piano con i valori estratti
        if paces:
            plan['config']['paces'] = paces
        if speeds:
            plan['config']['speeds'] = speeds
    
    # Estrai le frequenze cardiache
    if 'HeartRates' in xls.sheet_names:
        hr_df = pd.read_excel(xls, 'HeartRates', header=0)
        
        for _, row in hr_df.iterrows():
            # Assicurati che ci siano sia il nome che il valore
            if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                name = str(row.iloc[0]).strip()
                value = row.iloc[1]
                
                # Converti i valori numerici in interi
                if isinstance(value, (int, float)) and not pd.isna(value):
                    value = int(value)
                elif isinstance(value, str) and value.strip().isdigit():
                    value = int(value.strip())
                else:
                    value = str(value).strip()
                    
                plan['config']['heart_rates'][name] = value
    
    # Dictionary to store workout descriptions for comments
    workout_descriptions = {}
    
    # Processa gli allenamenti dal DataFrame
    for _, row in df.iterrows():
        # Verifica che ci siano i dati necessari
        if pd.isna(row['Week']) or pd.isna(row['Session']) or pd.isna(row['Description']) or pd.isna(row['Steps']):
            continue
        
        # Estrai i dati
        week = str(int(row['Week'])).zfill(2)  # Formatta come 01, 02, ecc.
        session = str(int(row['Session'])).zfill(2)
        description = str(row['Description']).strip()
        
        # Crea il nome completo dell'allenamento (senza includere la data)
        full_name = f"W{week}S{session} {description}"
        
        # Memorizza la descrizione per i commenti
        workout_descriptions[full_name] = description
        
        # Estrai i passi dell'allenamento
        steps_str = str(row['Steps']).strip()
        
        # Prepara la lista dei passi
        workout_steps = parse_workout_steps(steps_str, full_name, sport_type)
        
        # Aggiungi metadati del tipo di sport come primo elemento 
        sport_type_meta = {"sport_type": sport_type}
        workout_steps.insert(0, sport_type_meta)
        
        # Aggiungi la data come secondo elemento se disponibile
        if 'Date' in df.columns and pd.notna(row['Date']):
            date_value = row['Date']
            if isinstance(date_value, str):
                formatted_date = date_value
            else:
                # Se è un oggetto datetime o date, formattalo come stringa
                formatted_date = date_value.strftime("%Y-%m-%d") if hasattr(date_value, 'strftime') else str(date_value)
            
            # Aggiungi la data come secondo elemento dei passi
            date_step = {"date": formatted_date}
            workout_steps.insert(1, date_step)
        
        # Aggiungi l'allenamento al piano (senza la data nel nome)
        plan[full_name] = workout_steps
    
    # Salva il piano in formato YAML
    with open(output_file, 'w', encoding='utf-8') as f:
        # Usa NoAliasDumper per evitare riferimenti YAML
        yaml.dump(plan, f, default_flow_style=False, sort_keys=False, Dumper=NoAliasDumper)
    
    print(f"Conversione completata! File YAML salvato in: {output_file}")
    
    # Ora aggiungi i commenti al file
    add_comments_to_yaml(output_file, workout_descriptions)
    
    return plan

def extract_paces_and_speeds_from_excel(excel_file):
    """
    Estrae sia i ritmi per la corsa che le velocità per il ciclismo
    dal foglio Paces unificato, usando openpyxl per accedere alle celle direttamente.
    
    Args:
        excel_file: Percorso del file Excel
        
    Returns:
        Tuple (paces, speeds) con i dizionari contenenti i valori estratti
    """
    try:
        import openpyxl
        
        # Carica il workbook
        wb = openpyxl.load_workbook(excel_file, data_only=True)
        
        # Verifica se il foglio Paces esiste
        if 'Paces' not in wb.sheetnames:
            print("Foglio Paces non trovato!")
            return {}, {}
        
        # Ottieni il foglio
        sheet = wb['Paces']
        
        # Dizionari da popolare
        paces = {}
        speeds = {}
        
        # Inizializza lo stato del parser
        current_section = None  # 'running' o 'cycling'
        
        # Processa riga per riga
        for row_idx in range(1, sheet.max_row + 1):
            # Leggi i valori dalle prime tre colonne
            col0 = sheet.cell(row=row_idx, column=1).value
            col1 = sheet.cell(row=row_idx, column=2).value
            
            col0_str = str(col0) if col0 is not None else ""
            
            # Stampa la riga per debug
            print(f"Riga {row_idx}: {col0_str} - {col1}")
            
            # Controlla se è un'intestazione di sezione
            if col0_str and "RITMI PER LA CORSA" in col0_str:
                current_section = 'running'
                print(f"Trovata sezione RUNNING a riga {row_idx}")
                continue
            elif col0_str and "VELOCITÀ PER IL CICLISMO" in col0_str:
                current_section = 'cycling'
                print(f"Trovata sezione CYCLING a riga {row_idx}")
                continue
            
            # Salta righe vuote, intestazioni o righe di commento
            if not col0 or col0 == "Name" or col0_str.startswith('*') or col0_str.startswith('#'):
                continue
            
            # Se abbiamo un nome e un valore in una sezione valida
            if current_section and col0 and col1:
                # Estrai nome e valore
                name = col0_str.strip()
                
                # Gestisci diversi tipi di dati per il valore
                if isinstance(col1, (int, float)):
                    value = str(col1)
                else:
                    value = str(col1).strip()
                
                # Aggiunta importante di debug
                print(f"Aggiungendo {name}: {value} a {current_section}")
                
                # Aggiungi al dizionario appropriato
                if current_section == 'running':
                    paces[name] = value
                elif current_section == 'cycling':
                    speeds[name] = value
        
        # Stampa i valori estratti per debug
        print(f"Ritmi estratti: {paces}")
        print(f"Velocità estratte: {speeds}")
        
        return paces, speeds
    
    except Exception as e:
        import traceback
        print(f"Errore nell'estrazione dei ritmi e velocità: {str(e)}")
        traceback.print_exc()
        return {}, {}

def update_workouts_sheet(sheet, yaml_data):
    """
    Aggiorna il foglio Workouts con i dati dagli allenamenti YAML.
    
    Args:
        sheet: Foglio Excel Workouts
        yaml_data: Dizionario con i dati YAML
    """
    # Mantieni le prime due righe (intestazione e atleta)
    for row in range(sheet.max_row, 2, -1):
        sheet.delete_rows(row)
    
    # Ottieni la lista di allenamenti (escluso 'config')
    workouts = []
    for name, steps in yaml_data.items():
        if name != 'config' and isinstance(steps, list):
            # Estrai informazioni dall'allenamento
            match = re.match(r'W(\d+)S(\d+)\s+(.*)', name)
            if match:
                week = int(match.group(1))
                session = int(match.group(2))
                description = match.group(3)
                
                # Estrai la data se presente
                workout_date = ""
                sport_type = "running"
                
                # Filtra i passi effettivi (escludendo metadati)
                actual_steps = []
                for step in steps:
                    if isinstance(step, dict):
                        if 'sport_type' in step:
                            sport_type = step['sport_type']
                        elif 'date' in step:
                            workout_date = step['date']
                        else:
                            actual_steps.append(step)
                
                # Converti i passi in formato leggibile
                steps_text = format_steps_for_excel(actual_steps)
                
                workouts.append((week, session, workout_date, description, steps_text, sport_type))
    
    # Ordina gli allenamenti per settimana e sessione
    workouts.sort(key=lambda x: (x[0], x[1]))
    
    # Aggiungi gli allenamenti al foglio
    row = 3  # Prima riga di dati (dopo intestazione e atleta)
    for week, session, workout_date, description, steps_text, sport_type in workouts:
        sheet.cell(row=row, column=1).value = week
        sheet.cell(row=row, column=2).value = workout_date
        sheet.cell(row=row, column=3).value = session
        sheet.cell(row=row, column=4).value = description
        sheet.cell(row=row, column=5).value = steps_text
        row += 1


def format_steps_for_excel(steps, sport_type="running"):
    """
    Formatta i passi per il foglio Excel con la corretta indentazione.
    
    Args:
        steps: Lista di passi dell'allenamento
        sport_type: Tipo di sport ('running' o 'cycling')
        
    Returns:
        Testo formattato dei passi
    """
    formatted_steps = []
    
    for step in steps:
        if 'repeat' in step and 'steps' in step:
            # Passo di tipo repeat
            iterations = step['repeat']
            substeps = step['steps']
            
            # Formatta il passo di repeat
            formatted_steps.append(f"repeat {iterations}:")
            
            # Formatta i substeps con indentazione
            for substep in substeps:
                if isinstance(substep, dict) and len(substep) == 1:
                    substep_type = list(substep.keys())[0]
                    substep_detail = substep[substep_type]
                    
                    # Gestisci i diversi formati in base al tipo di sport
                    if sport_type == "cycling":
                        # Per il ciclismo, assicurati che @ diventi @spd nei passi che hanno zona di ritmo
                        if '@' in substep_detail and '@spd' not in substep_detail and '@hr' not in substep_detail:
                            substep_detail = substep_detail.replace('@', '@spd ')
                    else:  # running
                        # Per la corsa, assicurati che @spd diventi @ nei passi che hanno zona di velocità
                        if '@spd' in substep_detail:
                            substep_detail = substep_detail.replace('@spd', '@')
                    
                    # Usa l'indentazione con due spazi per i substep
                    formatted_steps.append(f"  {substep_type}: {substep_detail}")
        
        elif isinstance(step, dict) and len(step) == 1:
            # Passo normale
            step_type = list(step.keys())[0]
            step_detail = step[step_type]
            
            # Gestisci i diversi formati in base al tipo di sport
            if sport_type == "cycling":
                # Per il ciclismo, assicurati che @ diventi @spd nei passi che hanno zona di ritmo
                if '@' in step_detail and '@spd' not in step_detail and '@hr' not in step_detail:
                    step_detail = step_detail.replace('@', '@spd ')
            else:  # running
                # Per la corsa, assicurati che @spd diventi @ nei passi che hanno zona di velocità
                if '@spd' in step_detail:
                    step_detail = step_detail.replace('@spd', '@')
            
            formatted_steps.append(f"{step_type}: {step_detail}")
    
    return "\n".join(formatted_steps)

def update_heart_rates_sheet(sheet, heart_rates):
    """
    Aggiorna il foglio HeartRates con i dati dalle frequenze cardiache YAML.
    
    Args:
        sheet: Foglio Excel HeartRates
        heart_rates: Dizionario con le frequenze cardiache
    """
    # Cancella le righe esistenti (tranne l'intestazione)
    for row in range(sheet.max_row, 1, -1):
        sheet.delete_rows(row)
    
    # Aggiungi le nuove righe
    row = 2
    for name, value in heart_rates.items():
        sheet.cell(row=row, column=1).value = name
        sheet.cell(row=row, column=2).value = value
        row += 1


def update_speeds_sheet(sheet, speeds):
    """
    Aggiorna il foglio Speeds con i dati dalle velocità YAML.
    
    Args:
        sheet: Foglio Excel Speeds
        speeds: Dizionario con le velocità
    """
    # Cancella le righe esistenti (tranne l'intestazione)
    for row in range(sheet.max_row, 1, -1):
        sheet.delete_rows(row)
    
    # Aggiungi le nuove righe
    row = 2
    for name, value in speeds.items():
        sheet.cell(row=row, column=1).value = name
        sheet.cell(row=row, column=2).value = value
        row += 1

def update_paces_sheet(sheet, paces):
    """
    Aggiorna il foglio Paces con i dati dai ritmi YAML.
    
    Args:
        sheet: Foglio Excel Paces
        paces: Dizionario con i ritmi
    """
    # Cancella le righe esistenti (tranne l'intestazione)
    for row in range(sheet.max_row, 1, -1):
        sheet.delete_rows(row)
    
    # Aggiungi le nuove righe
    row = 2
    for name, value in paces.items():
        sheet.cell(row=row, column=1).value = name
        sheet.cell(row=row, column=2).value = value
        row += 1

def update_config_sheet(sheet, config):
    """
    Aggiorna il foglio Config con i dati dalla configurazione YAML.
    
    Args:
        sheet: Foglio Excel Config
        config: Dizionario con la configurazione
    """
    # Mappa delle righe da aggiornare
    config_rows = {}
    
    # Trova le righe esistenti e mappa le chiavi alle righe
    for row in range(1, sheet.max_row + 1):
        key = sheet.cell(row=row, column=1).value
        if key:
            config_rows[key] = row
    
    # Liste delle chiavi da gestire - SENZA 'athlete_name'
    priority_keys = ['name_prefix', 'sport_type', 'margins', 'race_day', 'preferred_days']
    
    # Chiavi da NON includere nelle righe di Config in quanto già presenti nei loro fogli dedicati
    # o perché non devono essere mostrate nel foglio Config
    excluded_keys = ['paces', 'speeds', 'heart_rates', 'athlete_name']
    
    # Prima gestisci le chiavi prioritarie
    for key in priority_keys:
        if key in config:
            if key in config_rows:
                row_index = config_rows[key]
            else:
                row_index = sheet.max_row + 1
                sheet.cell(row=row_index, column=1).value = key
            
            if key == 'margins':
                # Aggiorna i margini
                margins = config.get('margins', {})
                if 'faster' in margins and margins['faster'] is not None:
                    sheet.cell(row=row_index, column=2).value = margins['faster']
                if 'slower' in margins and margins['slower'] is not None:
                    sheet.cell(row=row_index, column=3).value = margins['slower']
                if 'hr_up' in margins and margins['hr_up'] is not None:
                    sheet.cell(row=row_index, column=4).value = margins['hr_up']
                if 'hr_down' in margins and margins['hr_down'] is not None:
                    sheet.cell(row=row_index, column=5).value = margins['hr_down']
            elif key == 'preferred_days':
                # Gestisci preferred_days come lista o stringa
                preferred_days = config[key]
                if preferred_days is not None:
                    if isinstance(preferred_days, list):
                        sheet.cell(row=row_index, column=2).value = str(preferred_days)
                    else:
                        sheet.cell(row=row_index, column=2).value = str(preferred_days)
            else:
                # Gestisci altre chiavi normali
                value = config[key]
                if value is not None:
                    # Converti dizionari, liste o altri tipi complessi in stringhe
                    if isinstance(value, (dict, list, tuple, set)):
                        if value:  # Se non è vuoto
                            sheet.cell(row=row_index, column=2).value = str(value)
                        else:
                            sheet.cell(row=row_index, column=2).value = ""  # Dizionario vuoto -> stringa vuota
                    else:
                        sheet.cell(row=row_index, column=2).value = value
    
    # Poi gestisci altre chiavi che potrebbero essere presenti nel config,
    # ma escludiamo le chiavi che non vanno nel foglio Config
    for key, value in config.items():
        if key not in priority_keys and key not in excluded_keys:
            if key in config_rows:
                row_index = config_rows[key]
            else:
                row_index = sheet.max_row + 1
                sheet.cell(row=row_index, column=1).value = key
            
            # Gestisci tutti gli altri parametri, convertendo tipi complessi in stringhe
            if value is not None:
                if isinstance(value, (dict, list, tuple, set)):
                    if value:  # Se non è vuoto
                        sheet.cell(row=row_index, column=2).value = str(value)
                    else:
                        sheet.cell(row=row_index, column=2).value = ""  # Dizionario vuoto -> stringa vuota
                else:
                    sheet.cell(row=row_index, column=2).value = value


def are_required_columns_present(df, required_cols):
    """
    Check if all required columns are present in the DataFrame.
    
    Args:
        df: DataFrame to check
        required_cols: List of required column names
        
    Returns:
        True if all required columns are present, False otherwise
    """
    return all(col in df.columns for col in required_cols)

def handle_missing_columns(excel_file, required_cols):
    """
    Handle missing columns by trying different header positions or case-insensitive matching.
    
    Args:
        excel_file: Path to the Excel file
        required_cols: List of required column names
        
    Returns:
        DataFrame with corrected columns
        
    Raises:
        ValueError: If required columns cannot be found
    """
    try:
        # Try reading with header in the first row
        df = pd.read_excel(excel_file, sheet_name='Workouts', header=0)
        
        if are_required_columns_present(df, required_cols):
            logging.info("'Workouts' sheet found with headers in the first row.")
            return df
            
        # Try case-insensitive matching
        df_cols_lower = [col.lower() for col in df.columns]
        missing = []
        
        for req_col in required_cols:
            if req_col.lower() not in df_cols_lower:
                missing.append(req_col)
        
        if missing:
            raise ValueError(f"Missing columns in 'Workouts' sheet: {', '.join(missing)}")
        
        # Rename columns for consistency
        rename_map = {}
        for col in df.columns:
            for req_col in required_cols:
                if col.lower() == req_col.lower():
                    rename_map[col] = req_col
        
        df = df.rename(columns=rename_map)
        logging.info("Columns renamed for consistency.")
        return df
        
    except Exception as e:
        raise ValueError(f"Error finding required columns: {str(e)}")

def extract_config(xls, plan):
    """
    Extract configuration information from the Config sheet.
    
    Args:
        xls: ExcelFile object
        plan: Plan dictionary to update
        
    Returns:
        Updated plan dictionary
    """
    if 'Config' in xls.sheet_names:
        try:
            config_df = pd.read_excel(xls, 'Config', header=0)
            
            # Extract name prefix (if present)
            name_prefix_rows = config_df[config_df.iloc[:, 0] == 'name_prefix']
            if not name_prefix_rows.empty:
                # Ensure the prefix ends with a space
                prefix = str(name_prefix_rows.iloc[0, 1]).strip()
                # Add a space at the end if not already there
                if prefix and not prefix.endswith(' '):
                    prefix = prefix + ' '
                plan['config']['name_prefix'] = prefix
            
            # Extract margins (if present)
            margins_rows = config_df[config_df.iloc[:, 0] == 'margins']
            if not margins_rows.empty:
                # Check if there are values for the margins
                if pd.notna(margins_rows.iloc[0, 1]):
                    plan['config']['margins']['faster'] = str(margins_rows.iloc[0, 1]).strip()
                if pd.notna(margins_rows.iloc[0, 2]):
                    plan['config']['margins']['slower'] = str(margins_rows.iloc[0, 2]).strip()
                if pd.notna(margins_rows.iloc[0, 3]):
                    plan['config']['margins']['hr_up'] = int(margins_rows.iloc[0, 3])
                if pd.notna(margins_rows.iloc[0, 4]):
                    plan['config']['margins']['hr_down'] = int(margins_rows.iloc[0, 4])
        except Exception as e:
            logging.warning(f"Error extracting configuration: {str(e)}")
    
    return plan

def extract_paces(xls, plan):
    """
    Extract pace information from the Paces sheet.
    
    Args:
        xls: ExcelFile object
        plan: Plan dictionary to update
        
    Returns:
        Updated plan dictionary
    """
    if 'Paces' in xls.sheet_names:
        try:
            paces_df = pd.read_excel(xls, 'Paces', header=0)
            
            for _, row in paces_df.iterrows():
                # Ensure both name and value are present
                if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                    name = str(row.iloc[0]).strip()
                    value = str(row.iloc[1]).strip()
                    plan['config']['paces'][name] = value
        except Exception as e:
            logging.warning(f"Error extracting paces: {str(e)}")
    
    return plan

def extract_heart_rates(xls, plan):
    """
    Extract heart rate information from the HeartRates sheet.
    
    Args:
        xls: ExcelFile object
        plan: Plan dictionary to update
        
    Returns:
        Updated plan dictionary
    """
    if 'HeartRates' in xls.sheet_names:
        try:
            hr_df = pd.read_excel(xls, 'HeartRates', header=0)
            
            for _, row in hr_df.iterrows():
                # Ensure both name and value are present
                if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                    name = str(row.iloc[0]).strip()
                    value = row.iloc[1]
                    
                    # Convert numeric values to integers
                    if isinstance(value, (int, float)) and not pd.isna(value):
                        value = int(value)
                    elif isinstance(value, str) and value.strip().isdigit():
                        value = int(value.strip())
                    else:
                        value = str(value).strip()
                        
                    plan['config']['heart_rates'][name] = value
        except Exception as e:
            logging.warning(f"Error extracting heart rates: {str(e)}")
    
    return plan

def add_comments_to_yaml(yaml_file, descriptions):
    """
    Add comments to the YAML file for workout descriptions.
    
    Args:
        yaml_file: Path to the YAML file
        descriptions: Dictionary with workout names and their descriptions
    """
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add comments for each workout
        for workout_name, description in descriptions.items():
            # Find the line with the workout name
            pattern = f"^{re.escape(workout_name)}:"
            content = re.sub(pattern, f"{workout_name}: # {description}", content, flags=re.MULTILINE)
        
        # Write the updated content
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logging.info("Comments added to YAML file")
    except Exception as e:
        logging.warning(f"Error adding comments to YAML: {str(e)}")

def parse_workout_steps(steps_str, workout_name, sport_type="running"):
    """
    Parse a string of steps into a structured list.
    
    Args:
        steps_str: String containing the workout steps
        workout_name: Name of the workout (for error messages)
        sport_type: Type of sport ('running' or 'cycling')
        
    Returns:
        List of structured workout steps
    """
    # Prepare the list of steps
    workout_steps = []
    
    # Replace semicolons with newlines for uniform processing
    # Ma prima correggi il formato "repeat X:" se è seguito da altre istruzioni sulla stessa riga
    steps_str = re.sub(r'(repeat\s+\d+):(.*?);', r'\1:\n\2;', steps_str)
    steps_str = re.sub(r';(\s*repeat\s+\d+:)', r';\n\1', steps_str)
    steps_str = steps_str.replace(';', '\n')
    
    # Manage steps with @spd notation for cycling
    if sport_type == "cycling":
        steps_str = steps_str.replace(' @ ', ' @spd ')
    
    # Split steps by lines
    step_lines = steps_str.split('\n')
    i = 0
    
    # Process each line
    while i < len(step_lines):
        step_str = step_lines[i].strip()
        if not step_str:
            i += 1
            continue
        
        # Check specifically for repeat pattern
        repeat_match = re.match(r'^repeat\s+(\d+):?$', step_str)
        if repeat_match:
            iterations = int(repeat_match.group(1))
            
            # Extract steps within the repeat
            substeps = []
            i += 1  # Move to the next line
            
            # Collect all indented steps after the repeat
            while i < len(step_lines):
                substep_str = step_lines[i].strip()
                if not substep_str:
                    i += 1
                    continue
                
                # If line doesn't look like a main step (doesn't contain a colon or is indented),
                # consider it part of the repeat block
                if not re.match(r'^(warmup|cooldown|interval|recovery|rest|repeat|other):', substep_str) or step_lines[i].startswith((' ', '\t')):
                    # Identify the substep type and details
                    substep_parts = substep_str.split(':')
                    if len(substep_parts) < 2:
                        logging.warning(f"Invalid substep format in {workout_name}: {substep_str}")
                        i += 1
                        continue
                    
                    substep_type = substep_parts[0].strip().lower()
                    substep_details = ':'.join(substep_parts[1:]).strip()
                    
                    # Verify substep type is valid
                    if substep_type not in VALID_STEP_TYPES:
                        if substep_type == "steady":
                            logging.warning(f"'steady' not supported in garmin-planner. Converted to 'interval' in {workout_name}")
                            substep_type = "interval"
                        else:
                            logging.warning(f"Substep type '{substep_type}' not recognized in {workout_name}, converted to 'other'")
                            substep_type = "other"
                    
                    # Handle cooldown inside repeat (likely an error)
                    if substep_type == "cooldown":
                        logging.warning(f"'cooldown' found inside a repeat in {workout_name}. Moved outside.")
                        # Save the cooldown for later
                        cooldown_details = substep_details
                        i += 1
                        # Add the repeat step with its substeps
                        # Correct format for garmin-planner: 'repeat' key and iterations value
                        repeat_step = {"repeat": iterations, "steps": copy.deepcopy(substeps)}
                        workout_steps.append(repeat_step)
                        # Add the cooldown as a separate step
                        workout_steps.append({"cooldown": cooldown_details})
                        break  # Exit the substep loop
                    
                    substeps.append({substep_type: substep_details})
                    i += 1
                else:
                    # This is a new main step, exit the repeat substeps loop
                    break
            
            # If we collected substeps, add the repeat step
            if substeps:
                # Correct format for garmin-planner: 'repeat' key and iterations value
                repeat_step = {"repeat": iterations, "steps": copy.deepcopy(substeps)}
                workout_steps.append(repeat_step)
            else:
                # If no substeps were found, add a simple repeat
                workout_steps.append({"repeat": iterations, "steps": []})
                logging.warning(f"No substeps found for repeat in {workout_name}")
        else:
            # If not a repeat, it's a normal step
            # Identify step type and details
            step_parts = step_str.split(':')
            if len(step_parts) < 2:
                logging.warning(f"Invalid step format in {workout_name}: {step_str}")
                i += 1
                continue
            
            step_type = step_parts[0].strip().lower()
            step_details = ':'.join(step_parts[1:]).strip()
            
            # Verify step type is valid for garmin-planner
            if step_type not in VALID_STEP_TYPES:
                if step_type == "steady":
                    logging.warning(f"'steady' is not supported in garmin-planner. Converted to 'interval' in {workout_name}")
                    step_type = "interval"
                else:
                    logging.warning(f"Step type '{step_type}' not recognized in {workout_name}, converted to 'other'")
                    step_type = "other"
            
            # Add a normal step
            workout_steps.append({step_type: step_details})
            i += 1
    
    return workout_steps


def auto_adjust_column_widths(worksheet):
    """
    Automatically adjust column widths based on content, handling merged cells properly.
    
    Args:
        worksheet: openpyxl worksheet object
    """
    for column_cells in worksheet.columns:
        max_length = 0
        column = None
        
        for cell in column_cells:
            # Skip merged cells which don't have column_letter attribute
            if hasattr(cell, 'column_letter'):
                if column is None:
                    column = cell.column_letter
                
                if cell.value:
                    cell_length = len(str(cell.value))
                    max_length = max(max_length, cell_length)
        
        if column is not None:  # Only adjust if we found a valid column
            adjusted_width = max(max_length + 2, 8)  # Add some extra space
            worksheet.column_dimensions[column].width = min(adjusted_width, 60)  # Limit to 60 to avoid too wide columns


def create_sample_excel(output_file='sample_training_plan.xlsx', sport_type="running"):
    """
    Create a sample Excel file with the expected structure for the training plan.
    Always includes both running and cycling paces in a unified Paces sheet.
    
    Args:
        output_file: Path for the output Excel file
        sport_type: Type of sport ('running' or 'cycling') - usato solo per impostare il valore di default
        
    Returns:
        Path to the created Excel file, or None if there was an error
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        logging.error("ERROR: openpyxl library is not installed.")
        logging.error("Install openpyxl with: pip install openpyxl")
        return None
    
    logging.info(f"Creating sample Excel file: {output_file}")
    
    wb = openpyxl.Workbook()
    
    # Define a thin border style
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    prefix = f"MYRUN_{random_suffix}_"
    
    # Config sheet
    config_sheet = wb.active
    config_sheet.title = 'Config'
    
    # Config sheet headers
    config_sheet['A1'] = 'Parameter'
    config_sheet['B1'] = 'Value'
    config_sheet['C1'] = 'Slower'
    config_sheet['D1'] = 'HR Up'
    config_sheet['E1'] = 'HR Down'
    
    # Config sheet values
    config_sheet['A2'] = 'name_prefix'
    config_sheet['B2'] = prefix
    
    # Imposta il tipo di sport
    config_sheet['A3'] = 'sport_type'
    config_sheet['B3'] = sport_type
    
    # Imposta i margini appropriati 
    config_sheet['A4'] = 'margins'
    config_sheet['B4'] = '0:03'   # faster in min:sec
    config_sheet['C4'] = '0:03'   # slower in min:sec
    config_sheet['D4'] = 5        # hr_up
    config_sheet['E4'] = 5        # hr_down
    
    # Aggiungi race_day (data gara)
    config_sheet['A5'] = 'race_day'
    # Imposta una data di esempio 6 mesi nel futuro
    from datetime import datetime, timedelta
    future_date = datetime.now() + timedelta(days=180)
    config_sheet['B5'] = future_date.strftime("%Y-%m-%d")
    
    # Aggiungi preferred_days (giorni preferiti)
    config_sheet['A6'] = 'preferred_days'
    config_sheet['B6'] = '[1, 3, 5]'  # Martedì, Giovedì, Sabato
    
    # Format header
    header_fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
    for col in ['A', 'B', 'C', 'D', 'E']:
        config_sheet[f'{col}1'].font = Font(bold=True)
        config_sheet[f'{col}1'].fill = header_fill
    
    # Crea il foglio Paces unificato con entrambi i tipi di ritmi/velocità
    create_unified_paces_sheet(wb, sport_type)
    
    # HeartRates sheet (Z1-Z5 zones)
    hr_sheet = wb.create_sheet(title='HeartRates')
    
    hr_sheet['A1'] = 'Name'
    hr_sheet['B1'] = 'Value'
    
    # Example of using max_hr with percentages
    hr_sheet['A2'] = 'max_hr'
    hr_sheet['B2'] = 180  # Use an integer instead of a string
    
    hr_sheet['A3'] = 'Z1_HR'
    hr_sheet['B3'] = '62-76% max_hr'
    
    hr_sheet['A4'] = 'Z2_HR'
    hr_sheet['B4'] = '76-85% max_hr'
    
    hr_sheet['A5'] = 'Z3_HR'
    hr_sheet['B5'] = '85-91% max_hr'
    
    hr_sheet['A6'] = 'Z4_HR'
    hr_sheet['B6'] = '91-95% max_hr'
    
    hr_sheet['A7'] = 'Z5_HR'
    hr_sheet['B7'] = '95-100% max_hr'
    
    # Format header
    for col in ['A', 'B']:
        hr_sheet[f'{col}1'].font = Font(bold=True)
        hr_sheet[f'{col}1'].fill = header_fill
    
    # Single Workouts sheet for all workouts
    workouts_sheet = wb.create_sheet(title='Workouts')
    
    # Add a row for the athlete's name
    # Create a merged cell for the athlete's name
    workouts_sheet.merge_cells('A1:E1')
    athlete_cell = workouts_sheet['A1']
    athlete_cell.value = "Atleta: "  # Prepared to be filled in
    athlete_cell.alignment = Alignment(horizontal='center', vertical='center')
    athlete_cell.font = Font(size=12, bold=True)
    # Add border to the athlete cell
    athlete_cell.border = thin_border

    # Headers in row 2
    workouts_sheet['A2'] = 'Week'
    workouts_sheet['B2'] = 'Date'
    workouts_sheet['C2'] = 'Session'
    workouts_sheet['D2'] = 'Description'
    workouts_sheet['E2'] = 'Steps'

    # Format header
    for col in ['A', 'B', 'C', 'D', 'E']:
        cell = workouts_sheet[f'{col}2']
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.border = thin_border  # Add border to all header cells
    
    # Esempi di allenamenti per running (sempre mostriamo questi)
    workouts = [
        # Week, Session, Description, Steps
        (1, 1, 'Easy run', 'warmup: 10min @ Z1_HR\ninterval: 30min @ Z2\ncooldown: 5min @ Z1_HR'),
        (1, 2, 'Short intervals', 'warmup: 15min @ Z1_HR\nrepeat 5:\n  interval: 400m @ Z5\n  recovery: 2min @ Z1_HR\ncooldown: 10min @ Z1_HR'),
        (1, 3, 'Long slow run', 'warmup: 10min @ Z1_HR\ninterval: 45min @ Z2\ncooldown: 5min @ Z1_HR'),
        (2, 1, 'Recovery run', 'interval: 30min @ Z1_HR'),
        (2, 2, 'Threshold run', 'warmup: 15min @ Z1_HR\ninterval: 20min @ Z4\ncooldown: 10min @ Z1_HR'),
        (2, 3, 'Progressive long run', 'warmup: 10min @ Z1_HR\ninterval: 30min @ Z2\ninterval: 20min @ Z3\ncooldown: 10min @ Z1_HR')
    ]
    
    # Define alternating colors for weeks
    week_colors = [
        "FFF2CC",  # Light yellow
        "DAEEF3",  # Light blue
        "E2EFDA",  # Light green
        "FCE4D6",  # Light orange
        "EAD1DC",  # Light pink
        "D9D9D9",  # Light gray
    ]
    
    # Add workouts to the sheet
    current_week = None
    current_color_index = 0
    
    for i, (week, session, description, steps) in enumerate(workouts, start=3):
        # If the week changes, change the color
        if week != current_week:
            current_week = week
            current_color_index = (current_color_index + 1) % len(week_colors)
            
        # Background color for the current row
        row_fill = PatternFill(start_color=week_colors[current_color_index], 
                              end_color=week_colors[current_color_index], 
                              fill_type="solid")
        
        # Assign values to cells
        workouts_sheet[f'A{i}'] = week
        workouts_sheet[f'B{i}'] = None  # Empty Date column to be filled by Plan function
        workouts_sheet[f'C{i}'] = session
        workouts_sheet[f'D{i}'] = description
        workouts_sheet[f'E{i}'] = steps
        
        # Apply background color and border to all cells in the row
        for col in ['A', 'B', 'C', 'D', 'E']:
            cell = workouts_sheet[f'{col}{i}']
            cell.fill = row_fill
            cell.border = thin_border
            
            # Set text wrapping and alignment
            cell.alignment = Alignment(wrapText=True, vertical='top')
        
        # Calculate appropriate row height based on content
        # Count lines of text in steps (both \n and ;)
        num_lines = 1 + steps.count('\n') + steps.count(';')
        
        # Consider indentation for repeats
        if 'repeat' in steps and '\n' in steps:
            # Count indented lines after repeat
            lines_after_repeat = steps.split('repeat')[1].count('\n')
            if lines_after_repeat > 0:
                num_lines += lines_after_repeat - 1  # -1 because the line with 'repeat' is already counted
        
        # Minimum height plus height for each line of text (about 15 points per line)
        row_height = max(20, 15 * num_lines)  # Increased minimum height
        workouts_sheet.row_dimensions[i].height = row_height
    
    # Set column widths
    workouts_sheet.column_dimensions['A'].width = 10  # Week
    workouts_sheet.column_dimensions['B'].width = 15  # Date
    workouts_sheet.column_dimensions['C'].width = 10  # Session
    workouts_sheet.column_dimensions['D'].width = 25  # Description
    workouts_sheet.column_dimensions['E'].width = 60  # Steps
    
    # Create Examples sheet with proper content for both running and cycling
    create_unified_examples_sheet(wb)
    
    # Ensure sheets are in the correct order
    sheet_order = ['Config', 'Paces', 'HeartRates', 'Workouts', 'Examples']
    
    # Reorder sheets
    wb._sheets = [wb[sheet_name] for sheet_name in sheet_order if sheet_name in wb.sheetnames]
    
    # Save the file
    wb.save(output_file)
    logging.info(f"Sample Excel file created: {output_file}")
    return output_file



def create_unified_paces_sheet(workbook, sport_type="running"):
    """
    Crea un foglio Paces unificato che contiene sia i ritmi per la corsa
    che le velocità per il ciclismo.
    
    Args:
        workbook: Workbook di openpyxl
        sport_type: Tipo di sport ('running' o 'cycling') - determina quali valori evidenziare
        
    Returns:
        Il foglio Paces creato
    """
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    # Crea o ottieni il foglio Paces
    if 'Paces' in workbook.sheetnames:
        paces_sheet = workbook['Paces']
        # Pulisci il foglio esistente
        for row in range(paces_sheet.max_row, 0, -1):
            paces_sheet.delete_rows(row)
    else:
        paces_sheet = workbook.create_sheet(title='Paces')
    
    # Definisci stili
    header_font = Font(bold=True)
    subheader_font = Font(bold=True, size=12)
    wrapped_alignment = Alignment(wrap_text=True, vertical='top')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    header_fill = PatternFill(start_color="E6E6E6", end_color="E6E6E6", fill_type="solid")
    running_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")  # Verde chiaro
    cycling_fill = PatternFill(start_color="DAEEF3", end_color="DAEEF3", fill_type="solid")  # Azzurro chiaro
    active_fill = running_fill if sport_type == "running" else cycling_fill
    
    # Imposta le intestazioni di colonna
    paces_sheet['A1'] = 'Name'
    paces_sheet['B1'] = 'Value'
    paces_sheet['C1'] = 'Note'
    
    # Formatta le intestazioni
    for col in ['A', 'B', 'C']:
        cell = paces_sheet[f'{col}1']
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Imposta larghezze colonne
    paces_sheet.column_dimensions['A'].width = 15
    paces_sheet.column_dimensions['B'].width = 15
    paces_sheet.column_dimensions['C'].width = 30
    
    # Sezione Running
    row = 2
    paces_sheet.merge_cells(f'A{row}:C{row}')
    paces_sheet[f'A{row}'] = 'RITMI PER LA CORSA (min/km)'
    paces_sheet[f'A{row}'].font = subheader_font
    paces_sheet[f'A{row}'].fill = running_fill
    paces_sheet[f'A{row}'].alignment = Alignment(horizontal='center', vertical='center')
    row += 1
    
    # Ritmi per la corsa
    running_paces = [
        ('Z1', '6:30', 'Ritmo facile (rigenerativo)'),
        ('Z2', '6:00', 'Ritmo aerobico (endurance)'),
        ('Z3', '5:30', 'Ritmo medio (soglia aerobica)'),
        ('Z4', '5:00', 'Ritmo soglia (soglia anaerobica)'),
        ('Z5', '4:30', 'Ritmo VO2max (anaerobico)'),
        ('recovery', '7:00', 'Ritmo recupero (molto lento)'),
        ('threshold', '5:10', 'Ritmo soglia personalizzato'),
        ('marathon', '5:20', 'Ritmo maratona personalizzato'),
        ('race_pace', '5:10', 'Ritmo gara personalizzato'),
    ]
    
    # Aggiungi ritmi per la corsa
    for name, value, note in running_paces:
        paces_sheet[f'A{row}'] = name
        paces_sheet[f'B{row}'] = value
        paces_sheet[f'C{row}'] = note
        
        # Applica bordi e formattazione a tutte le celle della riga
        for col in ['A', 'B', 'C']:
            cell = paces_sheet[f'{col}{row}']
            cell.border = thin_border
            cell.alignment = wrapped_alignment
            
            # Evidenzia le righe in base al tipo di sport attivo
            if sport_type == "running":
                cell.fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
        
        row += 1
    
    # Aggiungi una riga vuota tra le sezioni
    row += 1
    
    # Sezione Cycling
    paces_sheet.merge_cells(f'A{row}:C{row}')
    paces_sheet[f'A{row}'] = 'VELOCITÀ PER IL CICLISMO (km/h)'
    paces_sheet[f'A{row}'].font = subheader_font
    paces_sheet[f'A{row}'].fill = cycling_fill
    paces_sheet[f'A{row}'].alignment = Alignment(horizontal='center', vertical='center')
    row += 1
    
    # Velocità per il ciclismo
    cycling_speeds = [
        ('Z1', '15.0', 'Velocità facile (zona 1)'),
        ('Z2', '20.0', 'Velocità aerobica (zona 2)'),
        ('Z3', '25.0', 'Velocità media (zona 3)'),
        ('Z4', '30.0', 'Velocità soglia (zona 4)'),
        ('Z5', '35.0', 'Velocità VO2max (zona 5)'),
        ('recovery', '12.0', 'Velocità recupero (molto lenta)'),
        ('threshold', '28.0', 'Velocità soglia personalizzata'),
        ('ftp', '32.0', 'Velocità FTP personalizzata'),
    ]
    
    # Aggiungi velocità per il ciclismo
    for name, value, note in cycling_speeds:
        paces_sheet[f'A{row}'] = name
        paces_sheet[f'B{row}'] = value
        paces_sheet[f'C{row}'] = note
        
        # Applica bordi e formattazione a tutte le celle della riga
        for col in ['A', 'B', 'C']:
            cell = paces_sheet[f'{col}{row}']
            cell.border = thin_border
            cell.alignment = wrapped_alignment
            
            # Evidenzia le righe in base al tipo di sport attivo
            if sport_type == "cycling":
                cell.fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
        
        row += 1
    
    # Aggiungi una nota informativa alla fine
    row += 1
    paces_sheet.merge_cells(f'A{row}:C{row}')
    if sport_type == "running":
        paces_sheet[f'A{row}'] = '* Il tipo di sport attivo è CORSA. Le zone Z1-Z5 si riferiscono ai ritmi in min/km.'
    else:
        paces_sheet[f'A{row}'] = '* Il tipo di sport attivo è CICLISMO. Le zone Z1-Z5 si riferiscono alle velocità in km/h.'
    paces_sheet[f'A{row}'].font = Font(italic=True)
    paces_sheet[f'A{row}'].alignment = wrapped_alignment
    
    return paces_sheet



def create_examples_sheet(workbook, sport_type="running"):
    """
    Crea un foglio Examples nel formato corretto in italiano con formattazione appropriata,
    adattato al tipo di sport specificato.
    
    Args:
        workbook: Workbook di openpyxl
        sport_type: Tipo di sport ('running' o 'cycling')
        
    Returns:
        Il foglio Examples creato
    """
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    # Crea o ottieni il foglio Examples
    if 'Examples' in workbook.sheetnames:
        examples_sheet = workbook['Examples']
        # Pulisci il foglio esistente
        for row in range(examples_sheet.max_row, 0, -1):
            examples_sheet.delete_rows(row)
    else:
        examples_sheet = workbook.create_sheet(title='Examples')
    
    # Definisci stili
    header_font = Font(bold=True)
    wrapped_alignment = Alignment(wrap_text=True, vertical='top')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    header_fill = PatternFill(start_color="E6E6E6", end_color="E6E6E6", fill_type="solid")
    alternate_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
    
    # Imposta le intestazioni di colonna
    examples_sheet['A1'] = 'Tipo di Esempio'
    examples_sheet['B1'] = 'Descrizione'
    examples_sheet['C1'] = 'Passi (Steps)'
    
    # Formatta le intestazioni
    for col in ['A', 'B', 'C']:
        cell = examples_sheet[f'{col}1']
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Imposta larghezze colonne
    examples_sheet.column_dimensions['A'].width = 20
    examples_sheet.column_dimensions['B'].width = 40
    examples_sheet.column_dimensions['C'].width = 60
    
    # Riga 2: Nota informativa
    examples_sheet.merge_cells('A2:C2')
    examples_sheet['A2'] = '# ESEMPI DI SINTASSI - questo foglio è solo per scopo informativo e non viene importato'
    examples_sheet['A2'].font = Font(italic=True)
    examples_sheet['A2'].alignment = wrapped_alignment
    
    # Compila dati di esempio in base al tipo di sport
    examples_data = []
    
    if sport_type == "running":
        # Esempi per la corsa
        examples_data = [
            # Distanza
            ('Distanza', 'Esempio di allenamento basato su distanza', 
             "warmup: 2km @Z1_HR\ninterval: 5km @Z3\ncooldown: 1km @Z1_HR"),
            
            # Tempo
            ('Tempo', 'Esempio di allenamento basato su tempo', 
             "warmup: 10min @Z1_HR\ninterval: 30min @Z2\ncooldown: 5min @Z1_HR"),
            
            # Ripetute semplici
            ('Ripetute semplici', 'Esempio di allenamento con ripetute', 
             "warmup: 10min @Z1_HR\nrepeat 5:\n  interval: 1km @Z4\n  recovery: 2min @Z1_HR\ncooldown: 10min @Z1_HR"),
            
            # Ripetute annidate
            ('Ripetute annidate', 'Esempio di ripetute annidate', 
             "warmup: 10min @Z1_HR\nrepeat 3:\n  interval: 5min @Z3\n  repeat 4:\n    interval: 30s @Z5\n    recovery: 30s @Z1_HR\n  recovery: 3min @Z2_HR\ncooldown: 10min @Z1_HR"),
            
            # Con descrizioni
            ('Con descrizioni', 'Esempio con descrizioni per ogni passo', 
             "warmup: 10min @Z1_HR -- Inizia lentamente\ninterval: 20min @Z3 -- Mantieni ritmo costante\ncooldown: 5min @Z1_HR -- Rallenta gradualmente"),
            
            # Pulsante lap
            ('Pulsante lap', 'Esempio con pulsante lap', 
             "warmup: 10min @Z1_HR\nrest: lap-button @Z1_HR -- Premi lap quando sei pronto\ninterval: 5km @Z3\ncooldown: 5min @Z1_HR"),
            
            # Zone personalizzate
            ('Zone personalizzate', 'Esempio con zone personalizzate', 
             "warmup: 10min @Z1_HR\ninterval: 20min @marathon\ninterval: 10min @threshold\ncooldown: 5min @Z1_HR")
        ]
    else:  # cycling
        # Esempi per il ciclismo
        examples_data = [
            # Distanza
            ('Distanza', 'Esempio di allenamento basato su distanza', 
             "warmup: 5km @hr Z1_HR\ninterval: 20km @spd Z3\ncooldown: 3km @hr Z1_HR"),
            
            # Tempo
            ('Tempo', 'Esempio di allenamento basato su tempo', 
             "warmup: 15min @hr Z1_HR\ninterval: 40min @spd Z2\ncooldown: 5min @hr Z1_HR"),
            
            # Ripetute semplici
            ('Ripetute semplici', 'Esempio di allenamento con ripetute', 
             "warmup: 15min @hr Z1_HR\nrepeat 5:\n  interval: 2min @spd Z4\n  recovery: 2min @hr Z1_HR\ncooldown: 10min @hr Z1_HR"),
            
            # Ripetute annidate
            ('Ripetute annidate', 'Esempio di ripetute annidate', 
             "warmup: 15min @hr Z1_HR\nrepeat 3:\n  interval: 8min @spd Z3\n  repeat 4:\n    interval: 20s @spd Z5\n    recovery: 40s @hr Z1_HR\n  recovery: 3min @hr Z2_HR\ncooldown: 10min @hr Z1_HR"),
            
            # Con descrizioni
            ('Con descrizioni', 'Esempio con descrizioni per ogni passo', 
             "warmup: 15min @hr Z1_HR -- Inizia lentamente\ninterval: 30min @spd Z3 -- Mantieni ritmo costante\ncooldown: 10min @hr Z1_HR -- Rallenta gradualmente"),
            
            # Pulsante lap
            ('Pulsante lap', 'Esempio con pulsante lap', 
             "warmup: 15min @hr Z1_HR\nrest: lap-button @hr Z1_HR -- Premi lap quando sei pronto\ninterval: 20km @spd Z3\ncooldown: 5min @hr Z1_HR"),
            
            # Zone personalizzate
            ('Zone personalizzate', 'Esempio con zone personalizzate', 
             "warmup: 15min @hr Z1_HR\ninterval: 30min @spd 28.0\ninterval: 20min @spd threshold\ncooldown: 10min @hr Z1_HR")
        ]
    
    # Aggiungi esempi alla tabella
    for i, (tipo, descrizione, passi) in enumerate(examples_data, start=3):
        row_num = i
        examples_sheet[f'A{row_num}'] = tipo
        examples_sheet[f'B{row_num}'] = descrizione
        examples_sheet[f'C{row_num}'] = passi
        
        # Applica bordi e formattazione a tutte le celle della riga
        for col in ['A', 'B', 'C']:
            cell = examples_sheet[f'{col}{row_num}']
            cell.border = thin_border
            cell.alignment = wrapped_alignment
            
            # Applica un colore di sfondo alternato per migliorare la leggibilità
            if row_num % 2 == 1:
                cell.fill = alternate_fill
    
    # Aggiungi una riga vuota prima delle note sulla sintassi
    row_num = len(examples_data) + 3
    
    # Aggiungi note sulla sintassi, diverse per ogni sport
    row_num += 1
    examples_sheet.merge_cells(f'A{row_num}:C{row_num}')
    examples_sheet[f'A{row_num}'] = '# SINTASSI SUPPORTATA NEGLI STEP'
    examples_sheet[f'A{row_num}'].font = Font(italic=True)
    examples_sheet[f'A{row_num}'].alignment = wrapped_alignment
    
    # Regole di sintassi specifiche per sport
    if sport_type == "running":
        syntax_rules = [
            "Tipo: durata @zona -- descrizione opzionale",
            "Tipi: warmup, interval, recovery, cooldown, rest, repeat, other",
            "Durata: tempo (s, min, h) o distanza (m, km)",
            "Zone: Z1-Z5 (passo), Z1_HR-Z5_HR (freq. cardiaca), o qualsiasi zona definita nei fogli Paces/HeartRates",
            "Repeat: repeat N: seguito da step indentati con 2 spazi"
        ]
    else:  # cycling
        syntax_rules = [
            "Tipo: durata @hr zona o durata @spd zona -- descrizione opzionale",
            "Tipi: warmup, interval, recovery, cooldown, rest, repeat, other",
            "Durata: tempo (s, min, h) o distanza (m, km)",
            "Zone HR: Z1_HR-Z5_HR (freq. cardiaca) o qualsiasi zona HR definita nel foglio HeartRates",
            "Zone Velocità: Z1-Z5 (km/h) o qualsiasi zona definita nel foglio Speeds",
            "Repeat: repeat N: seguito da step indentati con 2 spazi"
        ]
    
    for i, rule in enumerate(syntax_rules, start=1):
        rule_row = row_num + i
        examples_sheet.merge_cells(f'A{rule_row}:C{rule_row}')
        examples_sheet[f'A{rule_row}'] = rule
        examples_sheet[f'A{rule_row}'].font = Font(italic=True)
        examples_sheet[f'A{rule_row}'].alignment = wrapped_alignment
    
    return examples_sheet


def create_unified_examples_sheet(workbook):
    """
    Crea un foglio Examples unificato che contiene esempi sia per la corsa che per il ciclismo.
    
    Args:
        workbook: Workbook di openpyxl
        
    Returns:
        Il foglio Examples creato
    """
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    # Crea o ottieni il foglio Examples
    if 'Examples' in workbook.sheetnames:
        examples_sheet = workbook['Examples']
        # Pulisci il foglio esistente
        for row in range(examples_sheet.max_row, 0, -1):
            examples_sheet.delete_rows(row)
    else:
        examples_sheet = workbook.create_sheet(title='Examples')
    
    # Definisci stili
    header_font = Font(bold=True)
    subheader_font = Font(bold=True, size=12)
    wrapped_alignment = Alignment(wrap_text=True, vertical='top')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    header_fill = PatternFill(start_color="E6E6E6", end_color="E6E6E6", fill_type="solid")
    running_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")  # Verde chiaro
    cycling_fill = PatternFill(start_color="DAEEF3", end_color="DAEEF3", fill_type="solid")  # Azzurro chiaro
    alternate_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
    
    # Imposta le intestazioni di colonna
    examples_sheet['A1'] = 'Tipo di Esempio'
    examples_sheet['B1'] = 'Descrizione'
    examples_sheet['C1'] = 'Passi (Steps)'
    
    # Formatta le intestazioni
    for col in ['A', 'B', 'C']:
        cell = examples_sheet[f'{col}1']
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Imposta larghezze colonne
    examples_sheet.column_dimensions['A'].width = 20
    examples_sheet.column_dimensions['B'].width = 40
    examples_sheet.column_dimensions['C'].width = 60
    
    # Riga 2: Nota informativa
    examples_sheet.merge_cells('A2:C2')
    examples_sheet['A2'] = '# ESEMPI DI SINTASSI - questo foglio è solo per scopo informativo e non viene importato'
    examples_sheet['A2'].font = Font(italic=True)
    examples_sheet['A2'].alignment = wrapped_alignment
    
    # Sezione Running
    row = 3
    examples_sheet.merge_cells(f'A{row}:C{row}')
    examples_sheet[f'A{row}'] = 'ESEMPI PER LA CORSA (RUNNING)'
    examples_sheet[f'A{row}'].font = subheader_font
    examples_sheet[f'A{row}'].fill = running_fill
    examples_sheet[f'A{row}'].alignment = Alignment(horizontal='center', vertical='center')
    row += 1
    
    # Esempi per la corsa
    running_examples = [
        # Distanza
        ('Distanza', 'Esempio di allenamento basato su distanza', 
         "warmup: 2km @Z1_HR\ninterval: 5km @Z3\ncooldown: 1km @Z1_HR"),
        
        # Tempo
        ('Tempo', 'Esempio di allenamento basato su tempo', 
         "warmup: 10min @Z1_HR\ninterval: 30min @Z2\ncooldown: 5min @Z1_HR"),
        
        # Ripetute semplici
        ('Ripetute semplici', 'Esempio di allenamento con ripetute', 
         "warmup: 10min @Z1_HR\nrepeat 5:\n  interval: 1km @Z4\n  recovery: 2min @Z1_HR\ncooldown: 10min @Z1_HR"),
        
        # Con descrizioni
        ('Con descrizioni', 'Esempio con descrizioni per ogni passo', 
         "warmup: 10min @Z1_HR -- Inizia lentamente\ninterval: 20min @Z3 -- Mantieni ritmo costante\ncooldown: 5min @Z1_HR -- Rallenta gradualmente"),
        
        # Pulsante lap
        ('Pulsante lap', 'Esempio con pulsante lap', 
         "warmup: 10min @Z1_HR\nrest: lap-button @Z1_HR -- Premi lap quando sei pronto\ninterval: 5km @Z3\ncooldown: 5min @Z1_HR"),
        
        # Zone personalizzate
        ('Zone personalizzate', 'Esempio con zone personalizzate', 
         "warmup: 10min @Z1_HR\ninterval: 20min @marathon\ninterval: 10min @threshold\ncooldown: 5min @Z1_HR")
    ]
    
    # Aggiungi esempi per la corsa
    for i, (tipo, descrizione, passi) in enumerate(running_examples):
        examples_sheet[f'A{row}'] = tipo
        examples_sheet[f'B{row}'] = descrizione
        examples_sheet[f'C{row}'] = passi
        
        # Applica bordi e formattazione a tutte le celle della riga
        for col in ['A', 'B', 'C']:
            cell = examples_sheet[f'{col}{row}']
            cell.border = thin_border
            cell.alignment = wrapped_alignment
            
            # Applica un colore di sfondo alternato per migliorare la leggibilità
            if i % 2 == 0:
                cell.fill = alternate_fill
        
        row += 1
    
    # Aggiungi una riga vuota tra le sezioni
    row += 1
    
    # Sezione Cycling
    examples_sheet.merge_cells(f'A{row}:C{row}')
    examples_sheet[f'A{row}'] = 'ESEMPI PER IL CICLISMO (CYCLING)'
    examples_sheet[f'A{row}'].font = subheader_font
    examples_sheet[f'A{row}'].fill = cycling_fill
    examples_sheet[f'A{row}'].alignment = Alignment(horizontal='center', vertical='center')
    row += 1
    
    # Esempi per il ciclismo
    cycling_examples = [
        # Distanza
        ('Distanza', 'Esempio di allenamento basato su distanza', 
         "warmup: 5km @hr Z1_HR\ninterval: 20km @spd Z3\ncooldown: 3km @hr Z1_HR"),
        
        # Tempo
        ('Tempo', 'Esempio di allenamento basato su tempo', 
         "warmup: 15min @hr Z1_HR\ninterval: 40min @spd Z2\ncooldown: 5min @hr Z1_HR"),
        
        # Ripetute semplici
        ('Ripetute semplici', 'Esempio di allenamento con ripetute', 
         "warmup: 15min @hr Z1_HR\nrepeat 5:\n  interval: 2min @spd Z4\n  recovery: 2min @hr Z1_HR\ncooldown: 10min @hr Z1_HR"),
        
        # Con descrizioni
        ('Con descrizioni', 'Esempio con descrizioni per ogni passo', 
         "warmup: 15min @hr Z1_HR -- Inizia lentamente\ninterval: 30min @spd Z3 -- Mantieni ritmo costante\ncooldown: 10min @hr Z1_HR -- Rallenta gradualmente"),
        
        # Pulsante lap
        ('Pulsante lap', 'Esempio con pulsante lap', 
         "warmup: 15min @hr Z1_HR\nrest: lap-button @hr Z1_HR -- Premi lap quando sei pronto\ninterval: 20km @spd Z3\ncooldown: 5min @hr Z1_HR"),
        
        # Zone personalizzate
        ('Zone personalizzate', 'Esempio con zone personalizzate', 
         "warmup: 15min @hr Z1_HR\ninterval: 30min @spd 28.0\ninterval: 20min @spd threshold\ncooldown: 10min @hr Z1_HR")
    ]
    
    # Aggiungi esempi per il ciclismo
    for i, (tipo, descrizione, passi) in enumerate(cycling_examples):
        examples_sheet[f'A{row}'] = tipo
        examples_sheet[f'B{row}'] = descrizione
        examples_sheet[f'C{row}'] = passi
        
        # Applica bordi e formattazione a tutte le celle della riga
        for col in ['A', 'B', 'C']:
            cell = examples_sheet[f'{col}{row}']
            cell.border = thin_border
            cell.alignment = wrapped_alignment
            
            # Applica un colore di sfondo alternato per migliorare la leggibilità
            if i % 2 == 0:
                cell.fill = alternate_fill
        
        row += 1
    
    # Aggiungi una riga vuota prima delle note sulla sintassi
    row += 1
    
    # Aggiungi note sulla sintassi generali
    examples_sheet.merge_cells(f'A{row}:C{row}')
    examples_sheet[f'A{row}'] = '# SINTASSI SUPPORTATA NEGLI STEP'
    examples_sheet[f'A{row}'].font = Font(italic=True, bold=True)
    examples_sheet[f'A{row}'].alignment = wrapped_alignment
    row += 1
    
    # Regole di sintassi comuni
    syntax_rules = [
        "Tipi di passo: warmup, interval, recovery, cooldown, rest, repeat, other",
        "Durata: tempo (s, min, h) o distanza (m, km)",
        "Per la corsa: usa @ per il ritmo (es. @Z2) e @hr per la frequenza cardiaca (es. @hr Z2_HR)",
        "Per il ciclismo: usa @spd per la velocità (es. @spd Z3) e @hr per la frequenza cardiaca (es. @hr Z1_HR)",
        "Zone ritmo/velocità: Z1-Z5 o qualsiasi zona definita nei fogli Paces",
        "Zone freq. cardiaca: Z1_HR-Z5_HR o qualsiasi zona definita nel foglio HeartRates",
        "Repeat: repeat N: seguito da step indentati con 2 spazi",
        "Descrizioni opzionali: aggiungi -- seguito dalla descrizione alla fine del passo"
    ]
    
    for rule in syntax_rules:
        examples_sheet.merge_cells(f'A{row}:C{row}')
        examples_sheet[f'A{row}'] = rule
        examples_sheet[f'A{row}'].font = Font(italic=True)
        examples_sheet[f'A{row}'].alignment = wrapped_alignment
        row += 1
    
    return examples_sheet


def safe_adjust_column_widths(worksheet):
    """
    Automatically adjust column widths based on content, safely handling merged cells.
    
    Args:
        worksheet: openpyxl worksheet object
    """
    for column_cells in worksheet.columns:
        max_length = 0
        column = None
        
        for cell in column_cells:
            # Skip merged cells which don't have column_letter attribute
            if hasattr(cell, 'column_letter'):
                if column is None:
                    column = cell.column_letter
                
                if cell.value:
                    cell_length = len(str(cell.value))
                    max_length = max(max_length, cell_length)
        
        if column is not None:  # Only adjust if we found a valid column
            adjusted_width = max(max_length + 2, 8)  # Add some extra space
            worksheet.column_dimensions[column].width = min(adjusted_width, 60)  # Limit to 60 to avoid too wide columns


def main():
    """Main function for command line use"""
    # Define command line arguments
    parser = argparse.ArgumentParser(description='Convert an Excel file to a YAML file for garmin-planner')
    parser.add_argument('--excel', '-e', help='Path to the input Excel file', default='')
    parser.add_argument('--output', '-o', help='Path to the output YAML file (optional)')
    parser.add_argument('--create-sample', '-s', action='store_true', help='Create a sample Excel file')
    parser.add_argument('--sample-name', help='Name for the sample Excel file', default='sample_training_plan.xlsx')
    parser.add_argument('--sport-type', help='Type of sport (running or cycling)', choices=['running', 'cycling'], default='running')
    
    args = parser.parse_args()
    
    # Create a sample file if requested
    if args.create_sample:
        sample_file = create_sample_excel(args.sample_name, args.sport_type)
        if sample_file:
            # If specified --excel, immediately convert the sample file
            if args.excel == '':
                args.excel = sample_file
    
    # Verify that an input file is specified
    if not args.excel:
        logging.error("ERROR: You must specify an input Excel file (--excel)")
        logging.info("Use --create-sample to create a sample file")
        parser.print_help()
        return
    
    # Verify that the Excel file exists
    if not os.path.exists(args.excel):
        logging.error(f"ERROR: File {args.excel} does not exist")
        return
    
    # Convert the Excel file to YAML
    try:
        excel_to_yaml(args.excel, args.output, args.sport_type)
        logging.info("Operation completed successfully!")
    except Exception as e:
        logging.error(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()