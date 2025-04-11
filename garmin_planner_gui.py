#!/usr/bin/env python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import sys
import os
import re
import yaml
import threading
import logging
import json
import workout_editor
import calendar
from tkcalendar import Calendar, DateEntry
from datetime import datetime, timedelta

# Disabilita verifica SSL per risolvere problemi di connessione
os.environ['PYTHONHTTPSVERIFY'] = '0'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GarminPlannerGUI")

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OAUTH_FOLDER = os.path.join(SCRIPT_DIR, "oauth")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
CACHE_DIR = os.path.join(SCRIPT_DIR, "cache")
WORKOUTS_CACHE_FILE = os.path.join(CACHE_DIR, "workouts_cache.json")

class GarminPlannerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Assicurati che la cartella cache esista
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR, exist_ok=True)
        
        self.title("Garmin Planner")
        self.geometry("800x700")
        
        # Variables
        # Carica l'ultima cartella OAuth usata dal file di configurazione, se esiste
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.oauth_folder = tk.StringVar(value=config.get('oauth_folder', DEFAULT_OAUTH_FOLDER))
            else:
                self.oauth_folder = tk.StringVar(value=DEFAULT_OAUTH_FOLDER)
        except Exception as e:
            logger.error(f"Errore nel caricamento della configurazione: {str(e)}")
            self.oauth_folder = tk.StringVar(value=DEFAULT_OAUTH_FOLDER)
            
        self.log_level = tk.StringVar(value="INFO")
        self.log_output = []
        
        # Status bar variable
        self.status_var = tk.StringVar(value="Pronto")
        
        # Create the notebook (tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_login_tab()
        self.create_import_tab()
        self.create_export_tab()
        self.create_schedule_tab()
        self.create_log_tab()
        
        # Common settings frame
        self.create_settings_frame()
        
        # Status bar
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Aggiungi il nuovo tab per l'editor di workout
        workout_editor.add_workout_editor_tab(self.notebook, self)


    def analyze_training_plan(self):
        """Analizza il piano di allenamento selezionato e mostra informazioni all'utente"""
        try:
            training_plan_id = self.training_plan.get()
            if not training_plan_id:
                self.training_plan_info.set("Nessun piano selezionato")
                self.plan_imported = False
                return
                
            # Inizializza i contatori
            total_workouts = 0
            sessions_per_week = {}
            
            # Cerca nella cache degli allenamenti
            if os.path.exists(WORKOUTS_CACHE_FILE):
                with open(WORKOUTS_CACHE_FILE, 'r') as f:
                    workouts = json.load(f)
                    
                    for workout in workouts:
                        workout_name = workout.get('workoutName', '')
                        # Verifica se l'allenamento appartiene al piano specificato
                        if training_plan_id in workout_name:
                            total_workouts += 1
                            # Cerca il pattern WxxSxx per estrarre settimana e sessione
                            match = re.search(r'\s(W\d\d)S(\d\d)\s', workout_name)
                            if match:
                                week_id = match.group(1)
                                
                                # Incrementa il contatore per questa settimana
                                if week_id not in sessions_per_week:
                                    sessions_per_week[week_id] = 0
                                sessions_per_week[week_id] += 1
            
            # Se abbiamo trovato allenamenti, mostra le informazioni
            if total_workouts > 0:
                weeks = len(sessions_per_week)
                max_sessions = max(sessions_per_week.values()) if sessions_per_week else 0
                
                info_text = f"Piano: {total_workouts} allenamenti, {weeks} settimane"
                if sessions_per_week:
                    info_text += f"\nAllenamenti per settimana: "
                    for week, count in sorted(sessions_per_week.items()):
                        info_text += f"{week}={count} "
                        
                self.training_plan_info.set(info_text)
                
                # Aggiorna il testo informativo sui giorni
                if max_sessions > 0:
                    self.day_info_label.config(text=f"Si suggerisce di selezionare {max_sessions} giorni per settimana")
                else:
                    self.day_info_label.config(text="Seleziona i giorni preferiti per gli allenamenti")
                    
                # Imposta il flag di piano importato
                self.plan_imported = True
            else:
                self.training_plan_info.set(f"Nessun allenamento trovato per '{training_plan_id}'")
                self.day_info_label.config(text="Seleziona i giorni preferiti per gli allenamenti")
                # Imposta il flag di piano non importato
                self.plan_imported = False
                
        except Exception as e:
            self.log(f"Errore nell'analisi del piano: {str(e)}")
            self.training_plan_info.set("Errore nell'analisi del piano")
            self.plan_imported = False


    def load_workouts_from_cache(self):
        """Carica la lista degli allenamenti dalla cache locale"""
        try:
            if os.path.exists(WORKOUTS_CACHE_FILE):
                with open(WORKOUTS_CACHE_FILE, 'r') as f:
                    workouts = json.load(f)
                    
                    # Clear existing items
                    for item in self.workouts_tree.get_children():
                        self.workouts_tree.delete(item)
                    
                    # Add workouts to the tree view
                    for workout in workouts:
                        workout_id = workout.get('workoutId', 'N/A')
                        workout_name = workout.get('workoutName', 'Senza nome')
                        self.workouts_tree.insert("", "end", values=(workout_id, workout_name))
                    
                    self.log(f"Caricati {len(workouts)} allenamenti dalla cache")
            else:
                self.log("Nessuna cache di allenamenti trovata. Usa 'Aggiorna lista' per scaricare gli allenamenti.")
        except Exception as e:
            self.log(f"Errore nel caricamento della cache: {str(e)}")

    def save_workouts_to_cache(self, workouts):
        """Salva la lista degli allenamenti nella cache locale"""
        try:
            with open(WORKOUTS_CACHE_FILE, 'w') as f:
                json.dump(workouts, f, indent=2)
            self.log(f"Salvati {len(workouts)} allenamenti nella cache")
        except Exception as e:
            self.log(f"Errore nel salvataggio della cache: {str(e)}")

    def save_config(self):
        """Salva la configurazione attuale"""
        try:
            config = {
                'oauth_folder': self.oauth_folder.get()
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            logger.error(f"Errore nel salvataggio della configurazione: {str(e)}")

    def create_settings_frame(self):
        settings_frame = ttk.LabelFrame(self, text="Impostazioni comuni")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # OAuth folder
        ttk.Label(settings_frame, text="Cartella OAuth:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.oauth_folder, width=30).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(settings_frame, text="Sfoglia", command=self.browse_oauth_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # Log level
        ttk.Label(settings_frame, text="Livello di log:").grid(row=0, column=3, padx=5, pady=5)
        log_level_combo = ttk.Combobox(settings_frame, textvariable=self.log_level, values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        log_level_combo.grid(row=0, column=4, padx=5, pady=5)
        log_level_combo.current(1)  # Default to INFO

    def browse_oauth_folder(self):
        folder = filedialog.askdirectory(initialdir=self.oauth_folder.get())
        if folder:
            self.oauth_folder.set(folder)
            self.save_config()  # Salva la configurazione quando viene cambiata la cartella

    def create_login_tab(self):
        login_frame = ttk.Frame(self.notebook)
        self.notebook.add(login_frame, text="Login")
        
        ttk.Label(login_frame, text="Effettua il login al tuo account Garmin Connect", font=("", 12, "bold")).pack(pady=20)
        ttk.Label(login_frame, text="Questo passaggio è necessario per utilizzare le funzionalità di Garmin Connect.").pack(pady=5)
        
        ttk.Button(login_frame, text="Effettua login", command=self.perform_login).pack(pady=20)

    def create_import_tab(self):
        import_frame = ttk.Frame(self.notebook)
        self.notebook.add(import_frame, text="Importa")
        
        # Variables
        self.import_file = tk.StringVar()
        self.import_replace = tk.BooleanVar(value=False)
        
        # Widgets
        ttk.Label(import_frame, text="Importa allenamenti da file YAML", font=("", 12, "bold")).pack(pady=10)
        
        file_frame = ttk.Frame(import_frame)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(file_frame, text="File allenamenti:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(file_frame, textvariable=self.import_file, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Sfoglia", command=self.browse_import_file).grid(row=0, column=2, padx=5, pady=5)
        
        options_frame = ttk.Frame(import_frame)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(options_frame, text="Sostituisci allenamenti esistenti", variable=self.import_replace).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(import_frame, text="Importa", command=self.perform_import).pack(pady=10)
        
        # Display available training plans
        tree_buttons_frame = ttk.Frame(import_frame)
        tree_buttons_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(tree_buttons_frame, text="Piani di allenamento disponibili:").pack(side=tk.LEFT, padx=5)
        ttk.Button(tree_buttons_frame, text="Aggiorna lista", command=self.load_training_plans).pack(side=tk.RIGHT, padx=5)
        
        # Crea il training_plans_tree
        self.training_plans_tree = ttk.Treeview(import_frame, columns=("plan", "weeks", "type"), show="headings")
        self.training_plans_tree.heading("plan", text="Piano")
        self.training_plans_tree.heading("weeks", text="Settimane")
        self.training_plans_tree.heading("type", text="Tipo")
        self.training_plans_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Populate tree with available training plans
        self.load_training_plans()
        
        # Double-click to select a plan
        self.training_plans_tree.bind("<Double-1>", self.select_training_plan)

    def create_export_tab(self):
        export_frame = ttk.Frame(self.notebook)
        self.notebook.add(export_frame, text="Esporta")
        
        # Variables
        self.export_file = tk.StringVar()
        self.export_format = tk.StringVar(value="YAML")
        self.export_clean = tk.BooleanVar(value=True)
        
        # Widgets
        ttk.Label(export_frame, text="Esporta allenamenti", font=("", 12, "bold")).pack(pady=10)
        
        file_frame = ttk.Frame(export_frame)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(file_frame, text="File di destinazione:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(file_frame, textvariable=self.export_file, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Sfoglia", command=self.browse_export_file).grid(row=0, column=2, padx=5, pady=5)
        
        options_frame = ttk.Frame(export_frame)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(options_frame, text="Formato:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Combobox(options_frame, textvariable=self.export_format, values=["YAML", "JSON"]).grid(row=0, column=1, padx=5, pady=5)
        ttk.Checkbutton(options_frame, text="Pulisci dati", variable=self.export_clean).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        # Bottoni per l'esportazione - solo il bottone "Esporta Selezionati"
        export_buttons_frame = ttk.Frame(export_frame)
        export_buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(export_buttons_frame, text="Esporta Selezionati", command=self.export_selected_workouts).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_buttons_frame, text="Elimina Selezionati", command=self.delete_selected_workouts).pack(side=tk.LEFT, padx=5)
        
        # Lista degli allenamenti disponibili
        ttk.Label(export_frame, text="Allenamenti disponibili su Garmin Connect:").pack(pady=(10, 5))
        
        self.workouts_tree = ttk.Treeview(export_frame, columns=("id", "name"), show="headings")
        self.workouts_tree.heading("id", text="ID")
        self.workouts_tree.heading("name", text="Nome")
        self.workouts_tree.column("id", width=100)
        self.workouts_tree.column("name", width=500)
        self.workouts_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Carica gli allenamenti dalla cache
        self.load_workouts_from_cache()
        
        # Bottone per aggiornare la lista
        ttk.Button(export_frame, text="Aggiorna lista", command=self.refresh_workouts).pack(pady=5)


    def delete_selected_workouts(self):
        """Elimina gli allenamenti selezionati da Garmin Connect"""
        # Verifica se ci sono allenamenti selezionati
        selected_items = self.workouts_tree.selection()
        if not selected_items:
            messagebox.showwarning("Nessuna selezione", "Seleziona almeno un allenamento da eliminare")
            return
        
        # Ottieni gli ID degli allenamenti selezionati
        selected_ids = []
        selected_names = []
        for item in selected_items:
            values = self.workouts_tree.item(item, "values")
            workout_id = values[0]
            workout_name = values[1]
            selected_ids.append(workout_id)
            selected_names.append(workout_name)
        
        # Chiedi conferma all'utente
        if len(selected_ids) == 1:
            message = f"Sei sicuro di voler eliminare l'allenamento '{selected_names[0]}'?"
        else:
            message = f"Sei sicuro di voler eliminare {len(selected_ids)} allenamenti selezionati?"
        
        if not messagebox.askyesno("Conferma eliminazione", message):
            return
        
        self.log(f"Eliminazione di {len(selected_ids)} allenamenti selezionati...")
        
        # Avvia il processo di eliminazione in un thread separato
        threading.Thread(target=lambda: self._do_delete_workouts(selected_ids)).start()


    def _do_delete_workouts(self, workout_ids):
        """Esegue l'eliminazione diretta degli allenamenti tramite il client Garmin"""
        oauth_folder = self.oauth_folder.get()
        
        try:
            # Importa le librerie necessarie
            import sys
            sys.path.append(SCRIPT_DIR)
            from planner.garmin_client import GarminClient
            
            # Crea un client Garmin direttamente
            self.log(f"Creazione di un client Garmin Connect con OAuth folder: {oauth_folder}")
            client = GarminClient(oauth_folder)
            
            # Elimina gli allenamenti uno per uno
            deleted_count = 0
            for workout_id in workout_ids:
                self.log(f"Eliminazione diretta dell'allenamento {workout_id}...")
                try:
                    response = client.delete_workout(workout_id)
                    self.log(f"Risposta dall'API: {response}")
                    deleted_count += 1
                except Exception as e:
                    self.log(f"Errore nell'eliminazione dell'allenamento {workout_id}: {str(e)}")
            
            # Mostra un messaggio di conferma
            if deleted_count > 0:
                self.log(f"Eliminati {deleted_count} allenamenti con successo")
                messagebox.showinfo("Successo", f"Eliminati {deleted_count} allenamenti con successo")
                
                # Forza l'aggiornamento della lista degli allenamenti
                # Prima eliminiamo la cache per forzare un nuovo download
                if os.path.exists(WORKOUTS_CACHE_FILE):
                    os.remove(WORKOUTS_CACHE_FILE)
                    self.log("Cache degli allenamenti rimossa per forzare un nuovo download")
                
                # Quindi aggiorniamo la lista
                self.refresh_workouts()
            else:
                self.log("Nessun allenamento è stato eliminato")
                messagebox.showwarning("Attenzione", "Nessun allenamento è stato eliminato")
                
        except Exception as e:
            self.log(f"Errore durante l'eliminazione diretta: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'eliminazione: {str(e)}")


    def export_selected_workouts(self):
        """Export only selected workouts to a file"""
        # Check if any workouts are selected
        selected_items = self.workouts_tree.selection()
        if not selected_items:
            messagebox.showwarning("Nessuna selezione", "Seleziona almeno un allenamento da esportare")
            return
        
        # Get selected workout IDs
        selected_ids = []
        for item in selected_items:
            workout_id = self.workouts_tree.item(item, "values")[0]
            selected_ids.append(workout_id)
        
        # Richiedi il percorso del file se non è già specificato
        if not self.export_file.get():
            filename = filedialog.asksaveasfilename(
                title="Salva allenamenti selezionati",
                filetypes=[("YAML files", "*.yaml"), ("JSON files", "*.json"), ("All files", "*.*")],
                defaultextension=".yaml"
            )
            if not filename:
                return  # Utente ha annullato
            self.export_file.set(filename)
        
        # Esporta gli allenamenti selezionati
        self.log(f"Esportazione di {len(selected_ids)} allenamenti selezionati...")
        
        # Avvia il processo di esportazione
        try:
            # Assicurati che la cartella OAuth esista
            oauth_folder = self.oauth_folder.get()
            if not os.path.exists(oauth_folder):
                os.makedirs(oauth_folder, exist_ok=True)
                self.log(f"Creata cartella OAuth: {oauth_folder}")
                
            # Costruisci il comando
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", oauth_folder,
                   "--log-level", self.log_level.get(),
                   "export",
                   "--export-file", self.export_file.get(),
                   "--workout-ids", ",".join(selected_ids)]
            
            if self.export_clean.get():
                cmd.append("--clean")
                
            cmd.extend(["--format", self.export_format.get()])
            
            self.log(f"Esecuzione comando: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante l'esportazione: {stderr}")
                messagebox.showerror("Errore", f"Errore durante l'esportazione: {stderr}")
            else:
                self.log(f"Esportazione completata con successo su {self.export_file.get()}")
                messagebox.showinfo("Successo", f"Esportazione completata con successo su {self.export_file.get()}")
        
        except Exception as e:
            self.log(f"Errore durante l'esportazione: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'esportazione: {str(e)}")


    def create_schedule_tab(self):
        schedule_frame = ttk.Frame(self.notebook)
        self.notebook.add(schedule_frame, text="Pianifica")
        
        # Variables
        self.training_plan = tk.StringVar()
        
        # Default to 30 days from now for race day
        default_race_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        self.race_day = tk.StringVar(value=default_race_date)
        
        # Nuova variabile per la data di inizio
        default_start_date = datetime.now().strftime("%Y-%m-%d")
        self.start_day = tk.StringVar(value=default_start_date)
        
        self.schedule_dry_run = tk.BooleanVar(value=False)
        
        # For day selection
        self.day_selections = [tk.IntVar() for _ in range(7)]
        self.day_names = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        
        # Variabile per le informazioni sul piano
        self.training_plan_info = tk.StringVar(value="Nessun piano selezionato")
        
        # Widgets
        ttk.Label(schedule_frame, text="Pianifica allenamenti", font=("", 12, "bold")).pack(pady=10)
        
        plan_frame = ttk.Frame(schedule_frame)
        plan_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(plan_frame, text="ID Piano di allenamento:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(plan_frame, textvariable=self.training_plan, width=30).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(plan_frame, text="(prefisso comune degli allenamenti)").grid(row=0, column=2, padx=5, pady=5)
        
        # Frame per le date
        dates_frame = ttk.Frame(schedule_frame)
        dates_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Data di inizio
        ttk.Label(dates_frame, text="Data inizio:").grid(row=0, column=0, padx=5, pady=5)
        start_date_picker = self.create_custom_date_picker(dates_frame, self.start_day)
        start_date_picker.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Data di gara
        ttk.Label(dates_frame, text="Giorno gara:").grid(row=1, column=0, padx=5, pady=5)
        race_date_picker = self.create_custom_date_picker(dates_frame, self.race_day)
        race_date_picker.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Frame per la visualizzazione delle informazioni sul piano
        plan_info_frame = ttk.LabelFrame(schedule_frame, text="Informazioni sul piano")
        plan_info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(plan_info_frame, textvariable=self.training_plan_info, justify=tk.LEFT).pack(padx=10, pady=5, anchor=tk.W)
        
        # Frame per la selezione dei giorni
        days_frame = ttk.LabelFrame(schedule_frame, text="Giorni preferiti per gli allenamenti")
        days_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Label informativa sui giorni
        self.day_info_label = ttk.Label(days_frame, text="Seleziona i giorni preferiti per gli allenamenti", 
                                     font=("", 9, "italic"))
        self.day_info_label.grid(row=0, column=0, columnspan=7, padx=5, pady=5, sticky=tk.W)
        
        # Crea checkbox per ogni giorno della settimana
        self.day_checkbuttons = []
        for i, day_name in enumerate(self.day_names):
            cb = ttk.Checkbutton(days_frame, text=day_name, variable=self.day_selections[i])
            cb.grid(row=1, column=i, padx=5, pady=5)
            self.day_checkbuttons.append(cb)
        
        options_frame = ttk.Frame(schedule_frame)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(options_frame, text="Simulazione (dry run)", variable=self.schedule_dry_run).grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W
        )
        
        button_frame = ttk.Frame(schedule_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Pianifica", command=self.perform_schedule).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Rimuovi pianificazione", command=self.perform_unschedule).grid(row=0, column=1, padx=5, pady=5)
        
        # Calendar view
        ttk.Label(schedule_frame, text="Calendario allenamenti pianificati").pack(pady=5)
        
        self.calendar_tree = ttk.Treeview(schedule_frame, columns=("date", "workout"), show="headings")
        self.calendar_tree.heading("date", text="Data")
        self.calendar_tree.heading("workout", text="Allenamento")
        self.calendar_tree.column("date", width=100)
        self.calendar_tree.column("workout", width=500)
        self.calendar_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Button(schedule_frame, text="Aggiorna calendario", command=self.refresh_calendar).pack(pady=5)
        
        # Aggiungi listener per aggiornare le informazioni quando cambia il piano
        self.training_plan.trace("w", lambda name, index, mode: self.analyze_training_plan())
        
        # Analizza il piano all'inizio
        self.analyze_training_plan()
    
    def create_custom_date_picker(self, parent, date_var):
        """Create a custom date picker with separate widgets for year, month, and day"""
        frame = ttk.Frame(parent)
        
        # Get current date from variable or use today
        try:
            current_date = datetime.strptime(date_var.get(), "%Y-%m-%d")
        except (ValueError, TypeError):
            current_date = datetime.now()
        
        # Year picker
        year_values = list(range(current_date.year, current_date.year + 10))
        year_var = tk.StringVar(value=str(current_date.year))
        ttk.Label(frame, text="Anno:").grid(row=0, column=0, padx=(0, 5))
        year_combo = ttk.Combobox(frame, textvariable=year_var, values=year_values, width=6, state="readonly")
        year_combo.grid(row=0, column=1, padx=(0, 10))
        
        # Month picker
        month_names = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
                      "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        month_var = tk.StringVar(value=month_names[current_date.month-1])
        ttk.Label(frame, text="Mese:").grid(row=0, column=2, padx=(0, 5))
        month_combo = ttk.Combobox(frame, textvariable=month_var, values=month_names, width=10, state="readonly")
        month_combo.grid(row=0, column=3, padx=(0, 10))
        
        # Day picker - days will be adjusted based on month/year
        day_var = tk.StringVar(value=str(current_date.day))
        ttk.Label(frame, text="Giorno:").grid(row=0, column=4, padx=(0, 5))
        day_combo = ttk.Combobox(frame, textvariable=day_var, width=5, state="readonly")
        day_combo.grid(row=0, column=5)
        
        def update_days(*args):
            """Update the available days based on the selected month and year"""
            try:
                year = int(year_var.get())
                month = month_names.index(month_var.get()) + 1
                
                # Get the number of days in the month
                _, num_days = calendar.monthrange(year, month)
                
                # Update the day values
                day_values = [str(i) for i in range(1, num_days + 1)]
                day_combo['values'] = day_values
                
                # Adjust the day if it's out of range
                current_day = int(day_var.get()) if day_var.get() else 1
                if current_day > num_days:
                    day_var.set(str(num_days))
                elif not day_var.get():
                    day_var.set("1")
                    
            except (ValueError, TypeError):
                # Default to 31 days if there's an error
                day_combo['values'] = [str(i) for i in range(1, 32)]
        
        # Initial update of days
        update_days()
        
        # Function to update the main date variable
        def update_date(*args):
            try:
                year = int(year_var.get())
                month = month_names.index(month_var.get()) + 1
                day = int(day_var.get())
                
                # Validate the date
                date_obj = datetime(year, month, day)
                date_var.set(date_obj.strftime("%Y-%m-%d"))
            except (ValueError, TypeError):
                # Invalid date, don't update
                pass
        
        # Bind the update function to the variables
        year_var.trace_add("write", update_date)
        month_var.trace_add("write", lambda *args: [update_days(), update_date()])
        day_var.trace_add("write", update_date)
        
        return frame

    def analyze_training_plan(self):
        """Analizza il piano di allenamento selezionato e mostra informazioni all'utente"""
        try:
            training_plan_id = self.training_plan.get().strip()
            if not training_plan_id:
                self.training_plan_info.set("Nessun piano selezionato")
                self.plan_imported = False
                return
                
            # Inizializza i contatori
            total_workouts = 0
            sessions_per_week = {}
            
            # Aggiornamento log
            self.log(f"Analisi del piano: '{training_plan_id}'")
            
            # Cerca nella cache degli allenamenti
            if os.path.exists(WORKOUTS_CACHE_FILE):
                with open(WORKOUTS_CACHE_FILE, 'r') as f:
                    workouts = json.load(f)
                    
                    # Debug: stampa i primi allenamenti per vedere il formato
                    for i, workout in enumerate(workouts[:5]):
                        workout_name = workout.get('workoutName', '')
                        self.log(f"Allenamento di debug #{i}: '{workout_name}'")
                    
                    for workout in workouts:
                        workout_name = workout.get('workoutName', '')
                        
                        # Verifica con criteri più flessibili
                        is_match = False
                        
                        # 1. Controllo esatto (il piano è una sottostringa esatta)
                        if training_plan_id in workout_name:
                            is_match = True
                        
                        # 2. Controllo ignorando gli spazi alla fine
                        elif training_plan_id.rstrip() in workout_name:
                            is_match = True
                        
                        # 3. Controllo con pattern WxxSxx dopo il prefisso
                        pattern = re.escape(training_plan_id) + r'\s*W\d\d\S\d\d'
                        if re.search(pattern, workout_name, re.IGNORECASE):
                            is_match = True
                            
                        # Se c'è una corrispondenza, conta l'allenamento
                        if is_match:
                            total_workouts += 1
                            self.log(f"Trovato allenamento: '{workout_name}'")
                            
                            # Cerca il pattern WxxSxx per estrarre settimana e sessione
                            match = re.search(r'\s*(W\d\d)S(\d\d)\s*', workout_name)
                            if match:
                                week_id = match.group(1)
                                
                                # Incrementa il contatore per questa settimana
                                if week_id not in sessions_per_week:
                                    sessions_per_week[week_id] = 0
                                sessions_per_week[week_id] += 1
            
            # Se abbiamo trovato allenamenti, mostra le informazioni
            if total_workouts > 0:
                weeks = len(sessions_per_week)
                max_sessions = max(sessions_per_week.values()) if sessions_per_week else 0
                
                info_text = f"Piano: {total_workouts} allenamenti, {weeks} settimane"
                if sessions_per_week:
                    info_text += f"\nAllenamenti per settimana: "
                    for week, count in sorted(sessions_per_week.items()):
                        info_text += f"{week}={count} "
                        
                self.training_plan_info.set(info_text)
                
                # Aggiorna il testo informativo sui giorni
                if max_sessions > 0:
                    self.day_info_label.config(text=f"Si suggerisce di selezionare {max_sessions} giorni per settimana")
                else:
                    self.day_info_label.config(text="Seleziona i giorni preferiti per gli allenamenti")
                    
                # Imposta il flag di piano importato
                self.plan_imported = True
                self.log(f"Piano '{training_plan_id}' trovato con {total_workouts} allenamenti")
            else:
                self.training_plan_info.set(f"Nessun allenamento trovato per '{training_plan_id}'")
                self.day_info_label.config(text="Seleziona i giorni preferiti per gli allenamenti")
                # Imposta il flag di piano non importato
                self.plan_imported = False
                self.log(f"Nessun allenamento trovato per il piano '{training_plan_id}'")
                
        except Exception as e:
            self.log(f"Errore nell'analisi del piano: {str(e)}")
            self.training_plan_info.set("Errore nell'analisi del piano")
            self.plan_imported = False


    def create_log_tab(self):
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="Log")
        
        # Log text widget
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=20)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add handler to log to the text widget
        self.log_handler = TextHandler(self.log_text)
        logging.getLogger().addHandler(self.log_handler)
        
        # Clear button
        ttk.Button(log_frame, text="Pulisci log", command=self.clear_log).pack(pady=5)

    def clear_log(self):
        """Pulisce il contenuto della finestra di log"""
        self.log_text.config(state=tk.NORMAL)  # Abilita la modifica del text widget
        self.log_text.delete(1.0, tk.END)      # Cancella tutto il contenuto
        self.log_text.config(state=tk.DISABLED)  # Riporta il widget in stato di sola lettura
        self.log("Log pulito")                 # Aggiunge un messaggio di conferma

    def log(self, message):
        """Add a message to the log tab"""
        logger.info(message)
        self.status_var.set(message)
    
    # Tab functionality methods
    def perform_login(self):
        self.log("Avvio procedura di login...")
        
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        if not os.path.exists(oauth_folder):
            try:
                os.makedirs(oauth_folder, exist_ok=True)
                self.log(f"Creata cartella OAuth: {oauth_folder}")
            except Exception as e:
                self.log(f"Errore nella creazione della cartella OAuth: {str(e)}")
                
        # Creiamo una finestra di dialogo personalizzata
        login_dialog = tk.Toplevel(self)
        login_dialog.title("Login Garmin Connect")
        login_dialog.geometry("300x150")
        login_dialog.resizable(False, False)
        login_dialog.transient(self)  # Rende la finestra modale
        login_dialog.grab_set()       # Impedisce di interagire con la finestra principale
        
        # Variabili per memorizzare email e password
        email_var = tk.StringVar()
        password_var = tk.StringVar()
        
        # Frame per organizzare i widget
        frame = ttk.Frame(login_dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Widget per l'email
        ttk.Label(frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=email_var, width=30).grid(row=0, column=1, pady=5)
        
        # Widget per la password
        ttk.Label(frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(frame, textvariable=password_var, show="*", width=30)
        password_entry.grid(row=1, column=1, pady=5)
    
        def do_login():
            email = email_var.get()
            password = password_var.get()
            
            if not email or not password:
                messagebox.showerror("Errore", "Email e password sono obbligatorie", parent=login_dialog)
                return
            
            # Chiudi la finestra di dialogo
            login_dialog.destroy()
            
            # Esegui il login in un thread separato
            threading.Thread(target=lambda: self._do_login_process(email, password)).start()

        def cancel():
            login_dialog.destroy()
            self.log("Login annullato")

        # Pulsanti
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Login", command=do_login).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annulla", command=cancel).pack(side=tk.LEFT, padx=5)
        
        # Centra la finestra sullo schermo
        login_dialog.update_idletasks()
        width = login_dialog.winfo_width()
        height = login_dialog.winfo_height()
        x = (login_dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (login_dialog.winfo_screenheight() // 2) - (height // 2)
        login_dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Imposta il focus sull'input dell'email
        login_dialog.focus_set()
        
        # Attendiamo che la finestra sia chiusa prima di continuare
        self.wait_window(login_dialog)

    def _do_login_process(self, email, password):
        """Esegue effettivamente il processo di login con le credenziali fornite"""
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        try:
            # Non dichiarare os all'interno della funzione perché è già importato a livello globale
            if not os.path.exists(oauth_folder):
                os.makedirs(oauth_folder, exist_ok=True)
                self.log(f"Creata cartella OAuth: {oauth_folder}")
            
            # Aggiungiamo la directory corrente al percorso Python
            sys.path.append(SCRIPT_DIR)
            
            # Impostiamo l'ambiente per disabilitare la verifica SSL
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            
            # Importiamo direttamente i moduli necessari per il login
            import garth
            
            # Esegui il login direttamente
            self.log(f"Tentativo di login con email: {email[:3]}***")
            try:
                garth.login(email, password)
                garth.save(oauth_folder)
                self.log("Login completato con successo")
                messagebox.showinfo("Successo", "Login completato con successo")
            except Exception as e:
                self.log(f"Errore durante il login: {str(e)}")
                messagebox.showerror("Errore", f"Errore durante il login: {str(e)}")
                
        except Exception as e:
            self.log(f"Errore durante l'inizializzazione del login: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'inizializzazione del login: {str(e)}")

    def browse_import_file(self):
        filename = filedialog.askopenfilename(
            title="Seleziona file allenamenti",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        if filename:
            self.import_file.set(filename)
    
    def browse_export_file(self):
        filename = filedialog.asksaveasfilename(
            title="Salva file allenamenti",
            filetypes=[("YAML files", "*.yaml"), ("JSON files", "*.json"), ("All files", "*.*")],
            defaultextension=".yaml"
        )
        if filename:
            self.export_file.set(filename)
    
    def load_training_plans(self):
        """Load available training plans from the training_plans directory"""
        try:
            # Clear existing items
            for item in self.training_plans_tree.get_children():
                self.training_plans_tree.delete(item)
            
            # Look for the training_plans directory
            plans_dir = os.path.join(SCRIPT_DIR, "training_plans")
            if not os.path.exists(plans_dir):
                self.log("Directory training_plans non trovata")
                return
            
            # Scan for YAML files in the directory structure
            for root, _, files in os.walk(plans_dir):
                for file in files:
                    if file.endswith(('.yaml', '.yml')):
                        rel_path = os.path.relpath(os.path.join(root, file), plans_dir)
                        parts = rel_path.split(os.sep)
                        
                        # Supporta sia la struttura gerarchica che quella semplice
                        if len(parts) >= 3:
                            # Struttura gerarchica originale: tipo/settimane/variante/file.yaml
                            plan_type = parts[0]  # e.g., half_marathon
                            weeks = parts[1]      # e.g., 8_weeks
                            variant = parts[2]    # e.g., paris
                            
                            # Extract target time if available in the filename
                            target_time = ""
                            match = re.search(r'(\d+[KM])@([\dh]+)', file)
                            if match:
                                distance, time = match.groups()
                                target_time = f" ({distance} in {time})"
                            
                            plan_name = f"{plan_type} - {variant}{target_time}"
                            
                            # Add to treeview
                            self.training_plans_tree.insert("", "end", 
                                                         values=(plan_name, weeks.replace("_", " "), 
                                                                 os.path.join(root, file)))
                        elif len(parts) == 2:
                            # Struttura semplice: cartella/file.yaml
                            folder = parts[0]     # e.g., frank
                            filename = parts[1]   # e.g., my_plan.yaml
                            
                            # Extract name without extension
                            plan_name = os.path.splitext(filename)[0]
                            
                            # Add to treeview with folder name as the plan type
                            self.training_plans_tree.insert("", "end", 
                                                         values=(f"{plan_name} ({folder})", 
                                                                 "N/A", 
                                                                 os.path.join(root, file)))
                        elif len(parts) == 1:
                            # File direttamente nella cartella training_plans
                            filename = parts[0]
                            plan_name = os.path.splitext(filename)[0]
                            
                            # Add to treeview
                            self.training_plans_tree.insert("", "end", 
                                                         values=(plan_name, 
                                                                 "N/A", 
                                                                 os.path.join(root, file)))
            
            if not self.training_plans_tree.get_children():
                self.log("Nessun piano di allenamento trovato")
            else:
                self.log(f"Trovati {len(self.training_plans_tree.get_children())} piani di allenamento")
        
        except Exception as e:
            self.log(f"Errore nel caricamento dei piani di allenamento: {str(e)}")
    
    def select_training_plan(self, event):
        """Handle double-click on a training plan in the tree view"""
        item = self.training_plans_tree.selection()[0]
        plan_path = self.training_plans_tree.item(item, "values")[2]
        self.import_file.set(plan_path)
        
        # Try to extract plan ID from the YAML file
        try:
            with open(plan_path, 'r') as f:
                plan_data = yaml.safe_load(f)
                if 'config' in plan_data and 'name_prefix' in plan_data['config']:
                    plan_id = plan_data['config']['name_prefix'].strip()
                    self.training_plan.set(plan_id)
                    self.log(f"Piano selezionato: {plan_id}")
        except Exception as e:
            self.log(f"Errore nel leggere il file del piano: {str(e)}")
    
    def perform_import(self):
        """Import workouts from a YAML file"""
        if not self.import_file.get():
            messagebox.showerror("Errore", "Seleziona un file di allenamento")
            return
        
        self.log(f"Importazione degli allenamenti da {self.import_file.get()}...")
        
        # Run the import command in a separate thread
        threading.Thread(target=self._do_import).start()
    
    def _do_import(self):
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        if not os.path.exists(oauth_folder):
            try:
                os.makedirs(oauth_folder, exist_ok=True)
                self.log(f"Creata cartella OAuth: {oauth_folder}")
            except Exception as e:
                self.log(f"Errore nella creazione della cartella OAuth: {str(e)}")
                    
        try:
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", self.oauth_folder.get(),
                   "--log-level", self.log_level.get(),
                   "import", 
                   "--workouts-file", self.import_file.get()]
            
            if self.import_replace.get():
                cmd.append("--replace")
            
            self.log(f"Esecuzione comando: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante l'importazione: {stderr}")
                messagebox.showerror("Errore", f"Errore durante l'importazione: {stderr}")
            else:
                self.log("Importazione completata con successo")
                messagebox.showinfo("Successo", "Importazione completata con successo")
                # Refresh the workout list
                self.refresh_workouts()
        
        except Exception as e:
            self.log(f"Errore durante l'importazione: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'importazione: {str(e)}")
    
    def refresh_workouts(self):
        """Refresh the list of workouts from Garmin Connect"""
        self.log("Aggiornamento lista allenamenti...")
        
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        if not os.path.exists(oauth_folder):
            try:
                os.makedirs(oauth_folder, exist_ok=True)
                self.log(f"Creata cartella OAuth: {oauth_folder}")
            except Exception as e:
                self.log(f"Errore nella creazione della cartella OAuth: {str(e)}")
                return
        
        # Clear existing items
        for item in self.workouts_tree.get_children():
            self.workouts_tree.delete(item)
        
        # Run the export command with no file to get JSON output
        threading.Thread(target=self._refresh_workouts).start()
    
    def _refresh_workouts(self):
        try:
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", self.oauth_folder.get(),
                   "--log-level", self.log_level.get(),
                   "export"]
            
            self.log(f"Esecuzione comando: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante l'aggiornamento: {stderr}")
            else:
                try:
                    workouts = json.loads(stdout)
                    
                    # Salva gli allenamenti nella cache
                    self.save_workouts_to_cache(workouts)
                    
                    # Add workouts to the tree view
                    for workout in workouts:
                        workout_id = workout.get('workoutId', 'N/A')
                        workout_name = workout.get('workoutName', 'Senza nome')
                        self.workouts_tree.insert("", "end", values=(workout_id, workout_name))
                    
                    self.log(f"Trovati {len(workouts)} allenamenti su Garmin Connect")
                
                except json.JSONDecodeError:
                    self.log("Errore nel decodificare la risposta JSON")
        
        except Exception as e:
            self.log(f"Errore durante l'aggiornamento: {str(e)}")
    
    def refresh_calendar(self):
        """Refresh the calendar view"""
        self.log("Aggiornamento calendario...")
        
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        if not os.path.exists(oauth_folder):
            try:
                os.makedirs(oauth_folder, exist_ok=True)
                self.log(f"Creata cartella OAuth: {oauth_folder}")
            except Exception as e:
                self.log(f"Errore nella creazione della cartella OAuth: {str(e)}")
                return
        
        # Clear existing items
        for item in self.calendar_tree.get_children():
            self.calendar_tree.delete(item)
        
        # Run the list command to get scheduled workouts
        threading.Thread(target=self._refresh_calendar).start()
    
    def _refresh_calendar(self):
        try:
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", self.oauth_folder.get(),
                   "--log-level", self.log_level.get(),
                   "list"]
            
            if self.training_plan.get():
                cmd.extend(["--name-filter", self.training_plan.get()])
            
            self.log(f"Esecuzione comando: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante l'aggiornamento del calendario: {stderr}")
            else:
                try:
                    # The output is a list of dictionaries
                    calendar_data = eval(stdout)
                    
                    # Sort by date
                    calendar_data.sort(key=lambda x: x.get('date', ''))
                    
                    # Add to treeview
                    for item in calendar_data:
                        date = item.get('date', 'N/A')
                        workout_name = item.get('title', 'Senza nome')
                        self.calendar_tree.insert("", "end", values=(date, workout_name))
                    
                    self.log(f"Trovati {len(calendar_data)} allenamenti pianificati")
                
                except Exception as e:
                    self.log(f"Errore nel parsare i dati del calendario: {str(e)}")
        
        except Exception as e:
            self.log(f"Errore durante l'aggiornamento del calendario: {str(e)}")
    
    def perform_schedule(self):
        """Schedule workouts according to a training plan"""
        if not self.training_plan.get():
            messagebox.showerror("Errore", "Inserisci l'ID del piano di allenamento")
            return
        
        if not self.race_day.get():
            messagebox.showerror("Errore", "Inserisci la data della gara")
            return
            
        if not self.start_day.get():
            messagebox.showerror("Errore", "Inserisci la data di inizio")
            return
        
        # Validate race day and start day format
        try:
            race_date = datetime.strptime(self.race_day.get(), "%Y-%m-%d").date()
            start_date = datetime.strptime(self.start_day.get(), "%Y-%m-%d").date()
            today = datetime.today().date()
            
            if race_date < today:
                messagebox.showerror("Errore", "La data della gara deve essere nel futuro")
                return
                
            if start_date >= race_date:
                messagebox.showerror("Errore", "La data di inizio deve essere precedente alla data della gara")
                return
        except ValueError:
            messagebox.showerror("Errore", "Formato date non valido. Usa YYYY-MM-DD")
            return
        
        # Controlla se sono stati selezionati dei giorni
        selected_days = []
        for i, var in enumerate(self.day_selections):
            if var.get():
                selected_days.append(str(i))
        
        if not selected_days:
            messagebox.showwarning("Nessun giorno selezionato", 
                                  "Non hai selezionato nessun giorno per gli allenamenti.\n"
                                  "Per favore, seleziona almeno un giorno della settimana.")
            return
        
        # Verifica se siamo in modalità simulazione
        is_dry_run = self.schedule_dry_run.get()
        
        # Cerca il file YAML corrispondente al piano
        training_plan_id = self.training_plan.get().strip()
        yaml_file = None
        
        # Se non siamo in modalità simulazione, cerchiamo il file YAML per l'importazione
        if not is_dry_run:
            yaml_file = self.find_yaml_for_plan(training_plan_id)
        
        if yaml_file and not is_dry_run:
            # Chiedi conferma all'utente
            response = messagebox.askyesno("Importazione e pianificazione", 
                                          f"Trovato il file YAML per il piano '{training_plan_id}'.\n\n"
                                          f"Vuoi importare gli allenamenti prima di pianificarli?")
            
            if response:
                # Importa prima gli allenamenti
                self.log(f"Importazione automatica degli allenamenti da {yaml_file}...")
                
                # Configura le variabili di importazione
                self.import_file.set(yaml_file)
                self.import_replace.set(True)  # Sostituisci eventuali allenamenti esistenti
                
                # Esegui l'importazione in un thread separato e attendi il completamento
                import_thread = threading.Thread(target=self._do_import_for_schedule, args=(selected_days,))
                import_thread.start()
                return
        
        # Se siamo in modalità simulazione, aggiungiamo un messaggio informativo
        if is_dry_run:
            self.log(f"Simulazione pianificazione allenamenti per il piano {self.training_plan.get()}...")
            self.log(f"Giorni selezionati: {', '.join([self.day_names[int(d)] for d in selected_days])}")
            self.log(f"Data inizio: {self.start_day.get()}")
            self.log(f"Data gara: {self.race_day.get()}")
            self.log("(Modalità dry-run - nessuna modifica effettiva verrà apportata)")
        else:
            self.log(f"Pianificazione allenamenti per il piano {self.training_plan.get()}...")
            self.log(f"Data inizio: {self.start_day.get()}")
        
        # Esegui la pianificazione con il flag dry-run corretto
        threading.Thread(target=lambda: self._do_schedule(selected_days, is_dry_run)).start()

    def find_yaml_for_plan(self, plan_id):
        """Cerca il file YAML corrispondente al piano specificato"""
        try:
            # Look for the training_plans directory
            plans_dir = os.path.join(SCRIPT_DIR, "training_plans")
            if not os.path.exists(plans_dir):
                self.log("Directory training_plans non trovata")
                return None
            
            # Normalizza il plan_id per la ricerca
            plan_id_normalized = plan_id.lower().strip()
            
            # Cerca ricorsivamente nei file YAML
            for root, _, files in os.walk(plans_dir):
                for file in files:
                    if file.endswith(('.yaml', '.yml')):
                        file_path = os.path.join(root, file)
                        
                        # Controlla se il file contiene il piano
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                                # Cerca name_prefix nel file
                                match = re.search(r'name_prefix:\s*[\'"]?([^\'"]+)[\'"]?', content)
                                if match:
                                    name_prefix = match.group(1).strip()
                                    
                                    # Verifica se corrisponde al piano cercato
                                    if plan_id_normalized in name_prefix.lower() or name_prefix.lower() in plan_id_normalized:
                                        self.log(f"Trovato file YAML per il piano '{plan_id}': {file_path}")
                                        return file_path
                        except Exception as e:
                            self.log(f"Errore nella lettura del file {file_path}: {str(e)}")
            
            self.log(f"Nessun file YAML trovato per il piano '{plan_id}'")
            return None
            
        except Exception as e:
            self.log(f"Errore nella ricerca del file YAML: {str(e)}")
            return None


    def _simulate_schedule(self, selected_days):
        """Simula la pianificazione degli allenamenti senza apportare modifiche"""
        try:
            # Recupera i parametri necessari
            training_plan_id = self.training_plan.get().strip()
            race_day = datetime.strptime(self.race_day.get(), "%Y-%m-%d").date()
            start_day = datetime.strptime(self.start_day.get(), "%Y-%m-%d").date()
            today = datetime.today().date()
            
            # Verifica che la data di inizio sia valida
            if start_day < today:
                self.log("Attenzione: La data di inizio è nel passato, verrà usata la data odierna.")
                start_day = today
                
            if start_day >= race_day:
                self.log("Errore: La data di inizio deve essere precedente alla data della gara.")
                messagebox.showerror("Errore", "La data di inizio deve essere precedente alla data della gara.")
                return
            
            # Calcola il primo giorno della settimana (lunedì) a partire dalla data di inizio
            # Se start_day è già lunedì, usiamo quella data
            # Altrimenti prendiamo il lunedì successivo
            if start_day.weekday() == 0:  # 0 = lunedì
                plan_start_date = start_day
            else:
                # Calcola il prossimo lunedì
                days_until_monday = 7 - start_day.weekday()
                plan_start_date = start_day + timedelta(days=days_until_monday)
                
            self.log(f"Data inizio selezionata: {start_day}, Data inizio effettiva (lunedì): {plan_start_date}")
            
            # Cerca gli allenamenti nella cache
            workouts = []
            workout_infos = {}
            if os.path.exists(WORKOUTS_CACHE_FILE):
                with open(WORKOUTS_CACHE_FILE, 'r') as f:
                    all_workouts = json.load(f)
                    
                    # Filtra per il piano di allenamento
                    plan_workouts = []
                    for workout in all_workouts:
                        workout_name = workout.get('workoutName', '')
                        if training_plan_id in workout_name:
                            plan_workouts.append(workout)
                    
                    # Estrai informazioni settimana/sessione
                    for workout in plan_workouts:
                        workout_name = workout.get('workoutName', '')
                        workout_id = workout.get('workoutId', '')
                        
                        match = re.search(r'\s(W\d\d)S(\d\d)\s', workout_name)
                        if match:
                            week_id = match.group(1)
                            session_id = int(match.group(2))
                            
                            if week_id not in workout_infos:
                                workout_infos[week_id] = {}
                            workout_infos[week_id][session_id] = {
                                'id': workout_id,
                                'name': workout_name
                            }
            
            # Se non ci sono allenamenti, mostra un messaggio
            if not workout_infos:
                self.log("Nessun allenamento trovato per la simulazione")
                messagebox.showinfo("Simulazione", 
                                  f"Nessun allenamento trovato per il piano '{training_plan_id}'.\n\n"
                                  f"Importa prima gli allenamenti per poter simulare la pianificazione.")
                return
            
            # Ora simula la pianificazione
            simulated_schedule = []
            
            for week_index, (week_id, sessions) in enumerate(sorted(workout_infos.items())):
                # Estrai il numero della settimana (es. da "W03" ottieni 3)
                match = re.search(r'W(\d\d)', week_id)
                if not match:
                    continue
                    
                week_number = int(match.group(1)) - 1  # -1 perché iniziamo dalla settimana 1, non 0
                
                # Calcola l'inizio di questa settimana del piano
                week_start = plan_start_date + timedelta(weeks=week_number)
                
                # Salta questa settimana se inizia dopo la data della gara
                if week_start > race_day:
                    self.log(f"Settimana {week_id} inizierebbe dopo la data della gara. Saltata.")
                    continue
                
                # Ordina le sessioni
                session_ids = sorted(sessions.keys())
                
                # Assegna allenamenti ai giorni selezionati
                for i, session_id in enumerate(session_ids):
                    workout_info = sessions[session_id]
                    
                    # Determina il giorno della settimana
                    if not selected_days:
                        self.log("Nessun giorno selezionato per gli allenamenti.")
                        return
                    
                    # Prendi il giorno in modo ciclico se ci sono più sessioni che giorni
                    day_index = int(selected_days[i % len(selected_days)])
                    
                    # Calcola la data
                    workout_date = week_start + timedelta(days=day_index)
                    date_str = workout_date.strftime('%Y-%m-%d')
                    
                    # Salta date nel passato
                    if workout_date < today:
                        self.log(f"Allenamento {week_id}S{session_id:02d} cadrebbe nel passato ({date_str}). Saltato.")
                        continue
                        
                    # Salta date dopo la gara
                    if workout_date > race_day:
                        self.log(f"Allenamento {week_id}S{session_id:02d} cadrebbe dopo la gara ({date_str}). Saltato.")
                        continue
                    
                    # Aggiungi alla simulazione
                    simulated_schedule.append({
                        'date': date_str,
                        'title': workout_info['name'],
                        'id': workout_info['id'],
                        'day': self.day_names[day_index]
                    })
                    
                    self.log(f"SIMULAZIONE: Allenamento {week_id}S{session_id:02d} pianificato per {self.day_names[day_index]} {date_str}")
            
            # Ordina per data
            simulated_schedule.sort(key=lambda x: x['date'])
            
            # Visualizza gli allenamenti simulati
            self._display_simulated_workouts(simulated_schedule)
            
        except Exception as e:
            self.log(f"Errore durante la simulazione: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante la simulazione: {str(e)}")

        
    def _do_schedule(self, selected_days, is_dry_run=False):
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        if not os.path.exists(oauth_folder):
            try:
                os.makedirs(oauth_folder, exist_ok=True)
                self.log(f"Creata cartella OAuth: {oauth_folder}")
            except Exception as e:
                self.log(f"Errore nella creazione della cartella OAuth: {str(e)}")
                return
        
        # Se siamo in modalità dry-run, usiamo un approccio diverso
        if is_dry_run:
            self._simulate_schedule(selected_days)
            return
                    
        try:
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", self.oauth_folder.get(),
                   "--log-level", self.log_level.get()]
            
            cmd.extend(["schedule",
                      "--training-plan", self.training_plan.get(),
                      "--race-day", self.race_day.get(),
                      "--start-day", self.start_day.get()])  # Aggiungi la data di inizio
            
            # Add selected days if any
            if selected_days:
                cmd.extend(["--workout-days", ",".join(selected_days)])
            
            self.log(f"Esecuzione comando: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante la pianificazione: {stderr}")
                messagebox.showerror("Errore", f"Errore durante la pianificazione: {stderr}")
            else:
                self.log("Pianificazione completata con successo")
                messagebox.showinfo("Successo", "Pianificazione completata con successo")
                
                # Refresh the calendar
                self.refresh_calendar()
            
        except Exception as e:
            self.log(f"Errore durante la pianificazione: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante la pianificazione: {str(e)}")
            
    def _parse_schedule_output(self, output):
            """Estrai le informazioni sugli allenamenti pianificati dall'output del comando"""
            try:
                workouts = []
                # Cerca linee come "Scheduling workout XXX (YYY) on ZZZZ-MM-DD"
                pattern = r"Scheduling workout (.*?) \((.*?)\) on (\d{4}-\d{2}-\d{2})"
                matches = re.findall(pattern, output)
                
                for match in matches:
                    workout_name, workout_id, date = match
                    workouts.append({
                        'date': date,
                        'title': workout_name,
                        'id': workout_id
                    })
                    
                return workouts
            except Exception as e:
                self.log(f"Errore nel parsing dell'output di pianificazione: {str(e)}")
                return None

    def _display_simulated_workouts(self, workouts):
            """Visualizza gli allenamenti simulati nella tabella del calendario"""
            try:
                # Pulisci la tabella del calendario
                for item in self.calendar_tree.get_children():
                    self.calendar_tree.delete(item)
                    
                # Aggiungi gli allenamenti simulati
                for workout in workouts:
                    self.calendar_tree.insert("", "end", values=(workout['date'], workout['title'] + " (SIMULAZIONE)"))
                    
                self.log(f"Visualizzati {len(workouts)} allenamenti simulati nel calendario")
                
                # Mostra un messaggio all'utente
                if workouts:
                    messagebox.showinfo("Simulazione completata", 
                                      f"Simulazione pianificazione completata.\n"
                                      f"Sono stati trovati {len(workouts)} allenamenti da pianificare.\n"
                                      f"Questi allenamenti sono mostrati nel calendario con l'etichetta (SIMULAZIONE).\n\n"
                                      f"Nessuna modifica è stata apportata al calendario di Garmin Connect.")
                else:
                    messagebox.showinfo("Simulazione", "Nessun allenamento da pianificare con i criteri specificati.")
            
            except Exception as e:
                self.log(f"Errore nella visualizzazione degli allenamenti simulati: {str(e)}")


    def _do_import_for_schedule(self, selected_days):
        """Importa gli allenamenti e poi pianifica"""
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        if not os.path.exists(oauth_folder):
            try:
                os.makedirs(oauth_folder, exist_ok=True)
                self.log(f"Creata cartella OAuth: {oauth_folder}")
            except Exception as e:
                self.log(f"Errore nella creazione della cartella OAuth: {str(e)}")
                return
                    
        try:
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", self.oauth_folder.get(),
                   "--log-level", self.log_level.get(),
                   "import", 
                   "--workouts-file", self.import_file.get()]
            
            if self.import_replace.get():
                cmd.append("--replace")
            
            self.log(f"Esecuzione comando: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante l'importazione: {stderr}")
                messagebox.showerror("Errore", f"Errore durante l'importazione: {stderr}")
            else:
                self.log("Importazione completata con successo")
                
                # Aggiorna la lista degli allenamenti in background
                refresh_thread = threading.Thread(target=self._refresh_workouts_silent)
                refresh_thread.start()
                refresh_thread.join()  # Attendi il completamento
                
                # Ora procedi con la pianificazione
                self.log(f"Ora procedo con la pianificazione...")
                self._do_schedule(selected_days, False)  # False = non è dry run
                
        except Exception as e:
            self.log(f"Errore durante l'importazione: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'importazione: {str(e)}")


    def _refresh_workouts_silent(self):
            """Versione silenziosa di refresh_workouts che non mostra messaggi all'utente"""
            try:
                cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                       "--oauth-folder", self.oauth_folder.get(),
                       "--log-level", self.log_level.get(),
                       "export"]
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    try:
                        workouts = json.loads(stdout)
                        # Salva gli allenamenti nella cache
                        self.save_workouts_to_cache(workouts)
                        self.log(f"Aggiornati {len(workouts)} allenamenti nella cache")
                    except json.JSONDecodeError:
                        self.log("Errore nel decodificare la risposta JSON")
            
            except Exception as e:
                self.log(f"Errore durante l'aggiornamento silenzioso: {str(e)}")

    def perform_unschedule(self):
            """Unschedule workouts from a training plan"""
            if not self.training_plan.get():
                messagebox.showerror("Errore", "Inserisci l'ID del piano di allenamento")
                return
            
            # Ask for confirmation
            if not messagebox.askyesno("Conferma", f"Sei sicuro di voler rimuovere tutti gli allenamenti pianificati per {self.training_plan.get()}?"):
                return
            
            self.log(f"Rimozione pianificazione allenamenti per il piano {self.training_plan.get()}...")
            
            # Run the unschedule command in a separate thread
            threading.Thread(target=self._do_unschedule).start()
        
    def _do_unschedule(self):
            # Assicurati che la cartella OAuth esista
            oauth_folder = self.oauth_folder.get()
            if not os.path.exists(oauth_folder):
                try:
                    os.makedirs(oauth_folder, exist_ok=True)
                    self.log(f"Creata cartella OAuth: {oauth_folder}")
                except Exception as e:
                    self.log(f"Errore nella creazione della cartella OAuth: {str(e)}")
                    return
                    
            try:
                cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                       "--oauth-folder", self.oauth_folder.get(),
                       "--log-level", self.log_level.get()
                       ]
                
                if self.schedule_dry_run.get():
                    cmd.append("--dry-run")
                
                cmd.extend(["unschedule",
                          "--training-plan", self.training_plan.get()])
                
                self.log(f"Esecuzione comando: {' '.join(cmd)}")
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    self.log(f"Errore durante la rimozione della pianificazione: {stderr}")
                    messagebox.showerror("Errore", f"Errore durante la rimozione della pianificazione: {stderr}")
                else:
                    self.log("Rimozione pianificazione completata con successo")
                    if self.schedule_dry_run.get():
                        self.log("(Modalità dry-run - nessuna modifica effettiva)")
                    else:
                        messagebox.showinfo("Successo", "Rimozione pianificazione completata con successo")
                        # Refresh the calendar
                        self.refresh_calendar()
            
            except Exception as e:
                self.log(f"Errore durante la rimozione della pianificazione: {str(e)}")
                messagebox.showerror("Errore", f"Errore durante la rimozione della pianificazione: {str(e)}")
        

class TextHandler(logging.Handler):
    """Handler per redirezionare i log al widget Text"""
    
    def __init__(self, text_widget):
        # Inizializzare con un livello specifico (INFO)
        logging.Handler.__init__(self, level=logging.INFO)
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)  # Auto-scroll to end
            
        # Tkinter is not thread-safe, so we need to schedule the update on the main thread
        self.text_widget.after(0, append)

if __name__ == "__main__":
    app = GarminPlannerGUI()
    app.mainloop()