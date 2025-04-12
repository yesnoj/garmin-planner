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
        self.geometry("800x850")
        
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
        
        # Crea uno stile personalizzato per i pulsanti di accento
        self.style = ttk.Style()
        self.style.configure("Accent.TButton", 
                            background="#0076c0",  # Colore di sfondo blu Garmin
                            foreground="white",    # Testo bianco
                            font=("", 10, "bold"))  # Font in grassetto

        # Configura anche gli stati di hover e premuto
        self.style.map("Accent.TButton",
                    background=[('active', '#005486')],  # Più scuro quando attivo/hover
                    foreground=[('active', 'white')])  # Testo rimane bianco
        
        # Create the notebook (tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs (spostando Log all'ultimo posto)
        self.create_login_tab()
        self.create_import_tab()
        self.create_export_tab()
        self.create_schedule_tab()
        self.create_excel_tools_tab()
        
        # Aggiungi il nuovo tab per l'editor di workout
        workout_editor.add_workout_editor_tab(self.notebook, self)
        
        # Crea la tab Log per ultima
        self.create_log_tab()

        # Common settings frame
        self.create_settings_frame()
        
        # Status bar
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)


    def run_command_with_live_output(self, cmd):
        """Esegue un comando catturando l'output in tempo reale"""
        self.log(f"Esecuzione comando: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            stdout_data = ""
            stderr_data = ""
            
            # Leggi l'output in tempo reale
            for line in process.stdout:
                line = line.strip()
                if line:
                    self.log(f"OUT: {line}")
                    stdout_data += line + "\n"
            
            # Leggi gli errori in tempo reale
            for line in process.stderr:
                line = line.strip()
                if line:
                    self.log(f"ERR: {line}")
                    stderr_data += line + "\n"
            
            # Attendi il completamento
            return_code = process.wait()
            
            return return_code, stdout_data, stderr_data
        
        except Exception as e:
            self.log(f"Errore nell'esecuzione del comando: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return -1, "", str(e)


    def analyze_training_plan(self):
        """Analizza il piano di allenamento selezionato e mostra informazioni all'utente"""
        try:
            training_plan_id = self.training_plan.get().strip()
            if not training_plan_id:
                self.training_plan_info.set("Nessun piano selezionato")
                self.plan_imported = False
                return
                
            # Aggiungi log di debug approfonditi
            self.log(f"Analisi del piano: '{training_plan_id}'")
            self.log(f"DEBUG: Formato dell'ID piano: '{training_plan_id}'")
            self.log(f"DEBUG: Lunghezza ID piano: {len(training_plan_id)} caratteri")
            self.log(f"DEBUG: Caratteri in esadecimale: {' '.join([hex(ord(c)) for c in training_plan_id])}")

            # Se il piano è AM18W115K, controlla specificamente
            if "AM18W115K" in training_plan_id:
                self.log(f"DEBUG: Il piano contiene 'AM18W115K', verificheremo match esatti")
            
            # Prima verifichiamo se esiste un file YAML corrispondente e lo analizziamo
            yaml_path = self.find_yaml_for_plan(training_plan_id)
            if yaml_path:
                self.log(f"Trovato file YAML per il piano: {yaml_path}")
                self.analyze_yaml_plan(yaml_path)
                return
                    
            # Inizializza i contatori
            total_workouts = 0
            sessions_per_week = {}
            
            # Cerca nella cache degli allenamenti
            if os.path.exists(WORKOUTS_CACHE_FILE):
                with open(WORKOUTS_CACHE_FILE, 'r') as f:
                    workouts = json.load(f)
                    
                    # Stampa info della cache
                    self.log(f"DEBUG: Trovati {len(workouts)} allenamenti nella cache")
                    workout_names = [w.get('workoutName', '') for w in workouts]
                    unique_prefixes = set()
                    for name in workout_names:
                        parts = name.split()
                        if parts:
                            unique_prefixes.add(parts[0])
                    self.log(f"DEBUG: Prefissi unici trovati: {unique_prefixes}")
                    
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
                        pattern = re.escape(training_plan_id) + r'\s*W\d\dS\d\d'
                        if re.search(pattern, workout_name, re.IGNORECASE):
                            is_match = True
                            self.log(f"Corrispondenza per pattern regex: '{workout_name}' corrisponde a '{pattern}'")

                        # 4. Controllo più permissivo (rimuove caratteri problematici)
                        clean_plan_id = re.sub(r'[^a-zA-Z0-9]', '', training_plan_id)
                        clean_workout_name = re.sub(r'[^a-zA-Z0-9]', '', workout_name)
                        if clean_plan_id and clean_plan_id in clean_workout_name:
                            is_match = True
                            self.log(f"Corrispondenza con ID pulito: '{clean_workout_name}' contiene '{clean_plan_id}'")
                                
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
                    
                # Preseleziona i giorni in base al numero di sessioni
                self.preselect_days(max_sessions)
                    
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
        """Crea la tab Login"""
        login_frame = ttk.Frame(self.notebook)
        self.notebook.add(login_frame, text="Login")
        
        # Chiama il metodo che crea il contenuto effettivo
        self.create_login_tab_content(login_frame)


    def create_login_tab_content(self, login_frame):
        """Crea il contenuto della tab Login (separato per permettere il refresh)"""
        # Verifica se esistono già file di autenticazione
        oauth_folder = self.oauth_folder.get()
        oauth_files_exist = False
        
        if os.path.exists(oauth_folder):
            # Controlla la presenza di file oauth
            oauth_files = [f for f in os.listdir(oauth_folder) if f.startswith('oauth') and f.endswith('.json')]
            if oauth_files:
                oauth_files_exist = True
        
        # Titolo della pagina
        ttk.Label(login_frame, text="Accesso a Garmin Connect", font=("", 14, "bold")).pack(pady=20)
        
        # Frame per lo stato di login
        status_frame = ttk.LabelFrame(login_frame, text="Stato di accesso")
        status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        if oauth_files_exist:
            # Mostra informazioni di login esistente
            status_icon = "✅"  # Simbolo di spunta
            status_color = "green"
            status_message = "Hai già effettuato l'accesso a Garmin Connect."
            last_login = "Ultimo accesso: " + self.get_last_login_time(oauth_folder)
        else:
            # Mostra informazioni di login necessario
            status_icon = "❌"  # Simbolo X
            status_color = "red"
            status_message = "Non hai ancora effettuato l'accesso a Garmin Connect."
            last_login = "È necessario effettuare l'accesso per utilizzare le funzionalità di pianificazione."
        
        # Visualizza lo stato
        status_container = ttk.Frame(status_frame)
        status_container.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(status_container, text=status_icon, font=("", 24)).pack(side=tk.LEFT, padx=10)
        
        status_text = ttk.Frame(status_container)
        status_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(status_text, text=status_message, font=("", 12, "bold"), foreground=status_color).pack(anchor=tk.W)
        ttk.Label(status_text, text=last_login).pack(anchor=tk.W, pady=5)
        
        # Descrizione
        description_frame = ttk.Frame(login_frame)
        description_frame.pack(fill=tk.X, padx=20, pady=10)
        
        description_text = (
            "Per utilizzare Garmin Planner è necessario effettuare l'accesso al tuo account Garmin Connect.\n\n"
            "Le credenziali verranno salvate in modo sicuro nella cartella OAuth e utilizzate per comunicare con Garmin Connect.\n\n"
            "Non è necessario effettuare nuovamente l'accesso ad ogni avvio dell'applicazione."
        )
        ttk.Label(description_frame, text=description_text, wraplength=600, justify="left").pack(pady=10)
        
        # Pulsanti
        button_frame = ttk.Frame(login_frame)
        button_frame.pack(pady=20)
        
        if oauth_files_exist:
            ttk.Button(button_frame, text="Aggiorna credenziali", command=self.perform_login).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="Verifica connessione", command=self.check_connection).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="Logout", command=self.perform_logout).pack(side=tk.LEFT, padx=10)
        else:
            # Usa un pulsante tk standard con colori espliciti
            login_button = tk.Button(button_frame, 
                                  text="Effettua login", 
                                  command=self.perform_login,
                                  bg="#0076c0",       # colore di sfondo blu
                                  fg="white",         # testo bianco
                                  font=("", 10, "bold"),  # font in grassetto
                                  padx=20,
                                  pady=10,
                                  relief=tk.RAISED,   # bordo in rilievo
                                  cursor="hand2")     # cambia il cursore al passaggio
            login_button.pack(padx=10, pady=5)
            
            # Gestione hover ed eventi del mouse
            def on_enter(e):
                login_button['bg'] = '#005486'  # blu più scuro al passaggio
                
            def on_leave(e):
                login_button['bg'] = '#0076c0'  # ritorna al blu normale
                
            def on_click(e):
                login_button['relief'] = tk.SUNKEN  # effetto premuto
                
            def on_release(e):
                login_button['relief'] = tk.RAISED  # torna al normale
                self.after(100, self.perform_login)  # esegue l'azione
            
            # Associa gli eventi
            login_button.bind("<Enter>", on_enter)
            login_button.bind("<Leave>", on_leave)
            login_button.bind("<ButtonPress-1>", on_click)
            login_button.bind("<ButtonRelease-1>", on_release)
        
        # Info sulla cartella OAuth
        info_frame = ttk.Frame(login_frame)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(info_frame, text=f"Cartella OAuth: {oauth_folder}", font=("", 8)).pack(side=tk.LEFT)
        ttk.Button(info_frame, text="Cambia", command=self.browse_oauth_folder, width=8).pack(side=tk.LEFT, padx=5)


    def get_last_login_time(self, oauth_folder):
        """Ottiene la data dell'ultimo login in base ai timestamp dei file OAuth"""
        try:
            if os.path.exists(oauth_folder):
                oauth_files = [os.path.join(oauth_folder, f) for f in os.listdir(oauth_folder) 
                              if f.startswith('oauth') and f.endswith('.json')]
                
                if oauth_files:
                    # Ottieni il timestamp più recente
                    timestamps = [os.path.getmtime(f) for f in oauth_files]
                    latest_timestamp = max(timestamps)
                    
                    # Converti il timestamp in data/ora leggibile
                    last_login_time = datetime.fromtimestamp(latest_timestamp)
                    return last_login_time.strftime("%d/%m/%Y %H:%M:%S")
                    
            return "Data non disponibile"
        except Exception as e:
            self.log(f"Errore nel recupero della data di ultimo accesso: {str(e)}")
            return "Data non disponibile"

    def check_connection(self):
        """Verifica la connessione a Garmin Connect usando le credenziali salvate"""
        self.log("Verifica della connessione a Garmin Connect...")
        
        # Disabilita temporaneamente i pulsanti
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.configure(state="disabled")
        
        # Esegui il controllo in un thread separato
        threading.Thread(target=self._do_check_connection).start()

    def _do_check_connection(self):
        """Implementazione della verifica della connessione"""
        try:
            # Importa le librerie necessarie
            import sys
            sys.path.append(SCRIPT_DIR)
            
            # Usa il GarminClient per verificare la connessione
            from planner.garmin_client import GarminClient
            
            client = GarminClient(self.oauth_folder.get())
            
            # Prova a ottenere la lista degli allenamenti come test
            response = client.list_workouts()
            
            if response:
                self.log("Connessione a Garmin Connect verificata con successo!")
                messagebox.showinfo("Connessione riuscita", 
                                  "La connessione a Garmin Connect è attiva e funzionante.\n\n"
                                  f"Trovati {len(response)} allenamenti nel tuo account.")
            else:
                self.log("Connessione a Garmin Connect non riuscita. Nessuna risposta ricevuta.")
                messagebox.showerror("Errore di connessione", 
                                   "La connessione a Garmin Connect non ha restituito dati.\n\n"
                                   "Prova ad aggiornare le credenziali.")
                
        except Exception as e:
            self.log(f"Errore nella verifica della connessione: {str(e)}")
            messagebox.showerror("Errore di connessione", 
                               f"Si è verificato un errore durante la verifica della connessione:\n\n{str(e)}")
        
        finally:
            # Riabilita i pulsanti nel thread principale
            self.after(0, self._re_enable_buttons)

    def _re_enable_buttons(self):
        """Riabilita i pulsanti dopo una operazione"""
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.configure(state="normal")



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
        # Rimossa variabile format: self.export_format = tk.StringVar(value="YAML")
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
        
        # Rimosso il combobox per il formato
        ttk.Checkbutton(options_frame, text="Pulisci dati", variable=self.export_clean).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Bottoni per l'esportazione
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
            
            # Aggiungi l'opzione clean se selezionata
            if self.export_clean.get():
                cmd.append("--clean")
            
            # Determina il formato dall'estensione del file
            file_extension = os.path.splitext(self.export_file.get())[1].lower()
            if file_extension == '.json':
                cmd.extend(["--format", "JSON"])
            else:
                # Default to YAML for other extensions
                cmd.extend(["--format", "YAML"])
            
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


# Modifica al metodo create_schedule_tab in garmin_planner_gui.py

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
        
        # Solo il bottone "Pianifica" (rimosso il bottone "Rimuovi pianificazione")
        ttk.Button(button_frame, text="Pianifica", command=self.perform_schedule).pack(pady=5)
        
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
                        pattern = re.escape(training_plan_id) + r'\s*W\d\dS\d\d'
                        if re.search(pattern, workout_name, re.IGNORECASE):
                            is_match = True
                            self.log(f"Corrispondenza per pattern regex: '{workout_name}' corrisponde a '{pattern}'")

                        # 4. Controllo più permissivo (rimuove caratteri problematici)
                        clean_plan_id = re.sub(r'[^a-zA-Z0-9]', '', training_plan_id)
                        clean_workout_name = re.sub(r'[^a-zA-Z0-9]', '', workout_name)
                        if clean_plan_id and clean_plan_id in clean_workout_name:
                            is_match = True
                            self.log(f"Corrispondenza con ID pulito: '{clean_workout_name}' contiene '{clean_plan_id}'")
                            
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


    def create_excel_tools_tab(self):
        """Crea la tab per le funzionalità di Excel"""
        excel_frame = ttk.Frame(self.notebook)
        self.notebook.add(excel_frame, text="Excel Tools")
        
        # Variabili
        self.excel_input_file = tk.StringVar()
        self.yaml_output_file = tk.StringVar()
        
        # Titolo e descrizione
        ttk.Label(excel_frame, text="Strumenti di conversione Excel 🠖 YAML", font=("", 12, "bold")).pack(pady=10)
        ttk.Label(excel_frame, text="Converti file Excel in formato YAML per l'importazione in Garmin Planner").pack(pady=5)
        
        # Frame per la conversione da Excel a YAML
        convert_frame = ttk.LabelFrame(excel_frame, text="Conversione Excel → YAML")
        convert_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Input file Excel
        input_frame = ttk.Frame(convert_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(input_frame, text="File Excel:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(input_frame, textvariable=self.excel_input_file, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(input_frame, text="Sfoglia", command=self.browse_excel_input).grid(row=0, column=2, padx=5, pady=5)
        
        # Output file YAML
        output_frame = ttk.Frame(convert_frame)
        output_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(output_frame, text="File YAML:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(output_frame, textvariable=self.yaml_output_file, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(output_frame, text="Sfoglia", command=self.browse_yaml_output).grid(row=0, column=2, padx=5, pady=5)
        
        # Bottoni azione
        btn_frame = ttk.Frame(convert_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Crea file Excel di esempio", command=self.create_excel_sample).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btn_frame, text="Converti Excel → YAML", command=self.convert_excel_to_yaml).pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Pianificazione degli allenamenti
        plan_frame = ttk.LabelFrame(excel_frame, text="Pianificazione degli allenamenti nel file Excel")
        plan_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(plan_frame, text="Pianifica le date degli allenamenti direttamente nel file Excel").pack(pady=5)
        ttk.Button(plan_frame, text="Pianifica allenamenti in Excel", command=self.schedule_workouts_in_excel).pack(pady=10)
        
        # Istruzioni
        help_frame = ttk.LabelFrame(excel_frame, text="Informazioni")
        help_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        help_text = (
            "Utilizzo degli strumenti Excel:\n\n"
            "1. Crea un file Excel di esempio per visualizzare la struttura richiesta\n"
            "2. Modifica il file Excel con i tuoi allenamenti\n"
            "3. Converti il file Excel in formato YAML\n"
            "4. Importa il file YAML risultante in Garmin Planner utilizzando la tab 'Importa'\n\n"
            "Oppure aggiungi le date direttamente nel file Excel con lo strumento di pianificazione."
        )
        
        help_label = ttk.Label(help_frame, text=help_text, wraplength=700, justify=tk.LEFT)
        help_label.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    def browse_excel_input(self):
        """Apre il dialogo per selezionare il file Excel di input"""
        filename = filedialog.askopenfilename(
            title="Seleziona file Excel",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.excel_input_file.set(filename)
            self.log(f"File Excel selezionato: {filename}")
            
            # Se il file YAML non è stato specificato, proponi lo stesso nome con estensione YAML
            if not self.yaml_output_file.get():
                yaml_path = os.path.splitext(filename)[0] + ".yaml"
                self.yaml_output_file.set(yaml_path)

    def browse_yaml_output(self):
        """Apre il dialogo per selezionare il file YAML di output"""
        filename = filedialog.asksaveasfilename(
            title="Salva file YAML",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            defaultextension=".yaml"
        )
        if filename:
            self.yaml_output_file.set(filename)
            self.log(f"File YAML di output impostato: {filename}")

    def create_excel_sample(self):
        """Crea un file Excel di esempio"""
        try:
            # Importa il modulo excel_to_yaml_converter
            from planner.excel_to_yaml_converter import create_sample_excel
            
            filename = filedialog.asksaveasfilename(
                title="Salva file Excel di esempio",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                defaultextension=".xlsx"
            )
            if not filename:
                return
                
            self.log(f"Creazione file Excel di esempio: {filename}")
            
            # Esegui la creazione in un thread separato
            def _create_sample_thread():
                try:
                    created_file = create_sample_excel(filename)
                    
                    # Aggiorna l'interfaccia nel thread principale
                    self.after(0, lambda: self._sample_created(created_file))
                except Exception as e:
                    self.after(0, lambda: self.log(f"Errore nella creazione del file di esempio: {str(e)}"))
                    messagebox.showerror("Errore", f"Si è verificato un errore durante la creazione del file:\n{str(e)}")
            
            threading.Thread(target=_create_sample_thread).start()
            
        except Exception as e:
            self.log(f"Errore: {str(e)}")
            messagebox.showerror("Errore", f"Si è verificato un errore:\n{str(e)}")

    def _sample_created(self, file_path):
        """Chiamato quando il file di esempio è stato creato"""
        self.log(f"File Excel di esempio creato con successo!")
        self.excel_input_file.set(file_path)
        
        # Proponi un file YAML con lo stesso nome
        yaml_path = os.path.splitext(file_path)[0] + ".yaml"
        self.yaml_output_file.set(yaml_path)
        
        messagebox.showinfo("Successo", 
                           f"File Excel di esempio creato con successo:\n{file_path}")

    def convert_excel_to_yaml(self):
        """Converte il file Excel in formato YAML"""
        try:
            # Verifica che il file Excel esista
            excel_file = self.excel_input_file.get()
            if not excel_file:
                messagebox.showerror("Errore", "Seleziona un file Excel da convertire")
                return
                
            if not os.path.exists(excel_file):
                messagebox.showerror("Errore", f"Il file Excel non esiste: {excel_file}")
                return
                
            # Determina il file YAML di output
            yaml_file = self.yaml_output_file.get()
            if not yaml_file:
                yaml_file = os.path.splitext(excel_file)[0] + ".yaml"
                self.yaml_output_file.set(yaml_file)
                
            self.log(f"Conversione di {excel_file} in {yaml_file}...")
            
            # Importa il modulo excel_to_yaml_converter
            from planner.excel_to_yaml_converter import excel_to_yaml
            
            # Esegui la conversione in un thread separato
            def _convert_thread():
                try:
                    plan = excel_to_yaml(excel_file, yaml_file)
                    
                    # Aggiorna l'interfaccia nel thread principale
                    workout_count = len(plan) - 1 if "config" in plan else len(plan)  # -1 per escludere config
                    self.after(0, lambda: self._conversion_success(yaml_file, workout_count))
                except Exception as e:
                    self.after(0, lambda: self.log(f"Errore nella conversione: {str(e)}"))
                    messagebox.showerror("Errore", f"Si è verificato un errore durante la conversione:\n{str(e)}")
            
            threading.Thread(target=_convert_thread).start()
            
        except Exception as e:
            self.log(f"Errore: {str(e)}")
            messagebox.showerror("Errore", f"Si è verificato un errore:\n{str(e)}")

    def _conversion_success(self, yaml_file, workout_count):
        """Chiamato quando la conversione è stata completata con successo"""
        self.log(f"Conversione completata con successo!")
        self.log(f"File YAML salvato: {yaml_file}")
        self.log(f"Piano di allenamento con {workout_count} allenamenti")
        
        messagebox.showinfo("Successo", 
                          f"Conversione completata con successo!\n\n"
                          f"File YAML salvato: {yaml_file}\n"
                          f"Allenamenti creati: {workout_count}")

    def schedule_workouts_in_excel(self):
        """Apre il dialogo per pianificare gli allenamenti nel file Excel"""
        try:
            # Verifica che sia stato selezionato un file Excel
            excel_file = self.excel_input_file.get()
            if not excel_file:
                messagebox.showerror("Errore", "Seleziona prima un file Excel.")
                return
                
            if not os.path.exists(excel_file):
                messagebox.showerror("Errore", f"Il file Excel non esiste: {excel_file}")
                return
                
            # Importa il modulo necessario
            from planner.excel_to_yaml_converter import excel_to_yaml
            
            # Crea una finestra di dialogo personalizzata per la pianificazione
            self._open_schedule_dialog(excel_file)
            
        except Exception as e:
            self.log(f"Errore: {str(e)}")
            messagebox.showerror("Errore", f"Si è verificato un errore:\n{str(e)}")

    def _open_schedule_dialog(self, excel_file):
        """Apre un dialogo personalizzato per la pianificazione degli allenamenti"""
        try:
            # Importa la classe di dialogo
            from planner.excel_to_yaml_gui import ScheduleDialog
            
            # Crea il dialogo
            dialog = ScheduleDialog(self, excel_file)
            
            # Se la pianificazione è stata completata con successo
            if dialog.result:
                self.log("Pianificazione degli allenamenti in Excel completata con successo.")
                messagebox.showinfo("Successo", "Le date sono state aggiunte al file Excel.")
                
        except Exception as e:
            self.log(f"Errore durante l'apertura del dialogo di pianificazione: {str(e)}")
            messagebox.showerror("Errore", f"Si è verificato un errore:\n{str(e)}")



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
        """Gestisce il processo di login a Garmin Connect"""
        self.log("Avvio procedura di login...")
        
        # Verifica se c'è già una finestra di login aperta (evita duplicati)
        for widget in self.winfo_children():
            if isinstance(widget, tk.Toplevel) and widget.title() == "Login Garmin Connect":
                self.log("Finestra di login già aperta")
                widget.lift()  # Porta in primo piano la finestra esistente
                return
        
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        if not os.path.exists(oauth_folder):
            try:
                os.makedirs(oauth_folder, exist_ok=True)
                self.log(f"Creata cartella OAuth: {oauth_folder}")
            except Exception as e:
                self.log(f"Errore nella creazione della cartella OAuth: {str(e)}")
                return
                
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
            """Callback quando l'utente preme Login"""
            email = email_var.get()
            password = password_var.get()
            
            if not email or not password:
                messagebox.showerror("Errore", "Email e password sono obbligatorie", parent=login_dialog)
                return
            
            # Cambia l'interfaccia per mostrare che stiamo elaborando
            for widget in frame.winfo_children():
                if isinstance(widget, ttk.Entry) or isinstance(widget, ttk.Button):
                    widget.configure(state="disabled")
            
            # Mostra un messaggio di attesa
            wait_label = ttk.Label(frame, text="Login in corso...", font=("", 10, "italic"))
            wait_label.grid(row=3, column=0, columnspan=2, pady=5)
            login_dialog.update()
            
            # Esegui il login in un thread separato
            threading.Thread(target=lambda: self._do_login_process(email, password, login_dialog)).start()

        def cancel():
            """Callback quando l'utente preme Annulla"""
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

    def _do_login_process(self, email, password, login_dialog=None):
        """Esegue effettivamente il processo di login con le credenziali fornite"""
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        success = False
        
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
                success = True
                
                # Chiudi il dialogo di login se esiste
                if login_dialog and login_dialog.winfo_exists():
                    login_dialog.destroy()
                    
                # Aggiorna l'interfaccia dopo il login riuscito
                self.after(0, self.refresh_login_tab)
                self.after(100, lambda: messagebox.showinfo("Successo", "Login completato con successo"))
                
            except Exception as e:
                self.log(f"Errore durante il login: {str(e)}")
                
                # Se il dialogo esiste ancora, aggiorna l'interfaccia per mostrare l'errore
                if login_dialog and login_dialog.winfo_exists():
                    def update_ui():
                        # Rimuovi messaggio di attesa se esiste
                        for widget in login_dialog.winfo_children():
                            if isinstance(widget, ttk.Label) and "Login in corso" in str(widget.cget("text")):
                                widget.destroy()
                        
                        # Riattiva i campi
                        for widget in login_dialog.winfo_children():
                            if isinstance(widget, ttk.Entry):
                                widget.configure(state="normal")
                        
                        # Riattiva i pulsanti
                        for widget in login_dialog.winfo_children():
                            if isinstance(widget, ttk.Button):
                                widget.configure(state="normal")
                        
                        # Mostra errore
                        messagebox.showerror("Errore", f"Errore durante il login: {str(e)}", parent=login_dialog)
                    
                    self.after(0, update_ui)
                else:
                    # Mostra errore nella finestra principale
                    self.after(0, lambda: messagebox.showerror("Errore", f"Errore durante il login: {str(e)}"))
                
        except Exception as e:
            self.log(f"Errore durante l'inizializzazione del login: {str(e)}")
            
            # Se il dialogo esiste ancora, chiudilo
            if login_dialog and login_dialog.winfo_exists():
                login_dialog.destroy()
                
            # Mostra errore nella finestra principale
            self.after(0, lambda: messagebox.showerror("Errore", f"Errore durante l'inizializzazione del login: {str(e)}"))

    def perform_logout(self):
        """Esegue il logout cancellando i file OAuth"""
        # Chiedi conferma all'utente
        if not messagebox.askyesno("Conferma logout", 
                                 "Sei sicuro di voler effettuare il logout?\n\n"
                                 "Verranno eliminati tutti i file di autenticazione e dovrai effettuare nuovamente il login."):
            return
        
        oauth_folder = self.oauth_folder.get()
        if os.path.exists(oauth_folder):
            try:
                # Elimina tutti i file OAuth
                oauth_files = [f for f in os.listdir(oauth_folder) if f.startswith('oauth') and f.endswith('.json')]
                
                if not oauth_files:
                    messagebox.showinfo("Informazione", "Nessun file di autenticazione trovato.")
                    return
                    
                for file in oauth_files:
                    file_path = os.path.join(oauth_folder, file)
                    os.remove(file_path)
                    self.log(f"File eliminato: {file_path}")
                
                # Aggiorna la tab Login
                self.refresh_login_tab()
                
                messagebox.showinfo("Logout completato", "Logout effettuato con successo.")
                
            except Exception as e:
                self.log(f"Errore durante il logout: {str(e)}")
                messagebox.showerror("Errore", f"Si è verificato un errore durante il logout: {str(e)}")
        else:
            messagebox.showinfo("Informazione", "Cartella OAuth non trovata.")

    def refresh_login_tab(self):
        """Aggiorna l'interfaccia della tab Login ricostruendola"""
        # Salva l'indice della tab attualmente selezionata
        current_tab = self.notebook.index("current")
        
        # Rimuovi la tab esistente
        login_tab_index = 0  # Assumiamo che Login sia la prima tab
        self.notebook.forget(login_tab_index)
        
        # Ricrea la tab Login
        login_frame = ttk.Frame(self.notebook)
        self.notebook.insert(login_tab_index, login_frame, text="Login")
        
        # Ridisegna il contenuto della tab
        self.create_login_tab_content(login_frame)
        
        # Ripristina la tab che era selezionata
        self.notebook.select(current_tab)
        
        self.log("Tab Login aggiornata con il nuovo stato")


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
            self.log(f"File di esportazione impostato: {filename}")
            self.log(f"Il formato sarà determinato dall'estensione del file (.yaml per YAML, .json per JSON)")
    
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
                    
                    # Set the plan ID in the Schedule tab without switching tabs
                    self.training_plan.set(plan_id)
                    self.log(f"Piano selezionato: {plan_id} (ID impostato nella tab Pianifica)")
                    
                    # Analizza il piano usando il file YAML ma non cambia tab
                    self.analyze_yaml_plan(plan_path)
        except Exception as e:
            self.log(f"Errore nel leggere il file del piano: {str(e)}")
    

    def analyze_yaml_plan(self, yaml_path):
        """Analizza il piano direttamente dal file YAML senza necessità di importarlo"""
        try:
            self.log(f"Analisi piano da file YAML: {yaml_path}")
            
            with open(yaml_path, 'r') as f:
                plan_data = yaml.safe_load(f)
                
                # Rimuovi la sezione config se presente
                config = plan_data.pop('config', {})
                
                # Conta gli allenamenti (escludendo la configurazione)
                workout_count = len(plan_data)
                
                # Analizza le settimane e sessioni
                weeks = {}
                
                for workout_name in plan_data.keys():
                    # Cerca il pattern WxxSxx nel nome
                    match = re.search(r'\s*(W\d\d)S(\d\d)\s*', workout_name)
                    if match:
                        week_id = match.group(1)
                        session_id = match.group(2)
                        
                        # Conteggia le sessioni per settimana
                        if week_id not in weeks:
                            weeks[week_id] = 0
                        weeks[week_id] += 1
                
                # Costruisci il testo informativo
                num_weeks = len(weeks)
                max_sessions = max(weeks.values()) if weeks else 0
                
                info_text = f"Piano da file YAML: {workout_count} allenamenti, {num_weeks} settimane"
                if weeks:
                    info_text += f"\nAllenamenti per settimana: "
                    for week, count in sorted(weeks.items()):
                        info_text += f"{week}={count} "
                
                # Aggiorna l'interfaccia
                self.training_plan_info.set(info_text)
                
                # Aggiorna il testo informativo sui giorni
                if max_sessions > 0:
                    self.day_info_label.config(text=f"Si suggerisce di selezionare {max_sessions} giorni per settimana")
                else:
                    self.day_info_label.config(text="Seleziona i giorni preferiti per gli allenamenti")
                
                # Preseleziona i giorni in base al numero di sessioni
                self.preselect_days(max_sessions)
                
                # Imposta il flag di piano caricato
                self.plan_imported = True
                
                self.log(f"Analisi completata: {workout_count} allenamenti in {num_weeks} settimane")
                
        except Exception as e:
            self.log(f"Errore nell'analisi del piano YAML: {str(e)}")
            self.training_plan_info.set(f"Errore nell'analisi del piano YAML: {str(e)}")
            self.plan_imported = False

    def preselect_days(self, sessions_per_week):
        """Preseleziona i giorni della settimana in base al numero di sessioni"""
        # Prima deseleziona tutti i giorni
        for var in self.day_selections:
            var.set(0)
        
        # Poi seleziona i giorni appropriati
        if sessions_per_week == 1:
            self.day_selections[2].set(1)  # Mercoledì
        elif sessions_per_week == 2:
            self.day_selections[1].set(1)  # Martedì
            self.day_selections[4].set(1)  # Venerdì
        elif sessions_per_week == 3:
            self.day_selections[1].set(1)  # Martedì
            self.day_selections[3].set(1)  # Giovedì
            self.day_selections[5].set(1)  # Sabato
        elif sessions_per_week == 4:
            self.day_selections[1].set(1)  # Martedì
            self.day_selections[3].set(1)  # Giovedì
            self.day_selections[5].set(1)  # Sabato
            self.day_selections[6].set(1)  # Domenica
        elif sessions_per_week >= 5:
            self.day_selections[0].set(1)  # Lunedì
            self.day_selections[1].set(1)  # Martedì
            self.day_selections[3].set(1)  # Giovedì
            self.day_selections[4].set(1)  # Venerdì
            self.day_selections[6].set(1)  # Domenica

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
        
        # Ottieni i giorni selezionati
        selected_days = []
        for i, var in enumerate(self.day_selections):
            if var.get():
                selected_days.append(i)  # Nota: usiamo gli indici numerici, non le stringhe
        
        if not selected_days:
            messagebox.showwarning("Nessun giorno selezionato", 
                                  "Non hai selezionato nessun giorno per gli allenamenti.\n"
                                  "Per favore, seleziona almeno un giorno della settimana.")
            return
        
        # Verifica se siamo in modalità simulazione
        is_dry_run = self.schedule_dry_run.get()
        training_plan_id = self.training_plan.get().strip()
        
        # Se siamo in modalità simulazione, procediamo come prima
        if is_dry_run:
            yaml_path = self.find_yaml_for_plan(training_plan_id)
            
            if yaml_path:
                self.log(f"Simulazione pianificazione usando il file YAML: {yaml_path}")
                # Pianifica gli allenamenti dal file YAML usando le stesse date
                self.plan_yaml_workouts(yaml_path, start_date, race_date, selected_days)
                return
            
            # Se siamo in modalità simulazione ma non c'è un file YAML e gli allenamenti non sono importati
            if not self.plan_imported and not yaml_path:
                # Ora è appropriato mostrare un messaggio di errore perché non abbiamo né un file YAML né gli allenamenti importati
                messagebox.showerror("Errore", "File YAML del piano non trovato e nessun allenamento importato. Importa prima gli allenamenti o fornisci un file YAML valido.")
                return
            
            self.log(f"Simulazione pianificazione allenamenti per il piano {training_plan_id}...")
            self.log(f"Giorni selezionati: {', '.join([self.day_names[d] for d in selected_days])}")
            self.log(f"Data inizio: {self.start_day.get()}")
            self.log(f"Data gara: {self.race_day.get()}")
            self.log("(Modalità dry-run - nessuna modifica effettiva verrà apportata)")
            
            # Converti selected_days in stringhe per _do_schedule
            selected_days_str = [str(d) for d in selected_days]
            
            # Esegui la simulazione
            threading.Thread(target=lambda: self._simulate_schedule(selected_days_str)).start()
        else:
            # Non siamo in modalità simulazione, dobbiamo eseguire la pianificazione effettiva
            
            # Prima verifica nella cache se gli allenamenti sono già presenti su Garmin Connect
            self.check_workouts_in_cache(training_plan_id)
            
            # Chiedi conferma prima di procedere
            if not messagebox.askyesno("Conferma pianificazione", 
                                     "Stai per pianificare gli allenamenti su Garmin Connect.\n\n"
                                     "Assicurati che gli allenamenti siano stati importati correttamente.\n"
                                     "Vuoi procedere con la pianificazione?"):
                return
                
            # Converti selected_days in stringhe per _do_schedule
            selected_days_str = [str(d) for d in selected_days]
            
            # Esegui la pianificazione
            threading.Thread(target=lambda: self._do_schedule(selected_days_str, False)).start()

    def check_workouts_in_cache(self, training_plan_id):
        """Verifica se gli allenamenti del piano sono presenti nella cache di Garmin Connect."""
        # Aggiorna la cache se necessario
        if not os.path.exists(WORKOUTS_CACHE_FILE):
            self.log("La cache degli allenamenti non esiste. Aggiornamento in corso...")
            self.refresh_workouts()
            return
        
        try:
            with open(WORKOUTS_CACHE_FILE, 'r') as f:
                cache = json.load(f)
                
            # Cerca allenamenti che corrispondono al piano
            matching_workouts = []
            for workout in cache:
                if training_plan_id in workout.get('workoutName', ''):
                    matching_workouts.append(workout)
            
            if matching_workouts:
                self.log(f"Trovati {len(matching_workouts)} allenamenti per il piano {training_plan_id} in Garmin Connect")
                self.plan_imported = True
            else:
                self.log(f"Non sono stati trovati allenamenti per il piano {training_plan_id} in Garmin Connect")
                
                # Chiedi all'utente se vuole importare gli allenamenti
                yaml_path = self.find_yaml_for_plan(training_plan_id)
                
                if yaml_path and messagebox.askyesno("Importazione necessaria", 
                                              f"Non sono stati trovati allenamenti per il piano {training_plan_id} in Garmin Connect.\n\n"
                                              f"Vuoi importare gli allenamenti dal file {yaml_path} prima di pianificarli?"):
                    self.log(f"Importazione degli allenamenti da {yaml_path}...")
                    self.import_file.set(yaml_path)
                    self.import_replace.set(True)  # Sostituisci eventuali allenamenti esistenti
                    
                    # Eseguiamo l'importazione e attendiamo il completamento
                    self._do_import_for_schedule()
                    self.plan_imported = True
        except Exception as e:
            self.log(f"Errore durante il controllo della cache: {str(e)}")

    def _do_import_and_schedule(self, selected_days):
        """Importa gli allenamenti e poi pianifica"""
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        if not os.path.exists(oauth_folder):
            try:
                os.makedirs(oauth_folder, exist_ok=True)
                self.log(f"Creata cartella OAuth: {oauth_folder}")
            except Exception as e:
                self.log(f"Errore nella creazione della cartella OAuth: {str(e)}")
                messagebox.showerror("Errore", f"Errore nella creazione della cartella OAuth: {str(e)}")
                return
                    
        try:
            # Costruisci il comando per l'importazione
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", oauth_folder,
                   "--log-level", self.log_level.get(),
                   "import", 
                   "--workouts-file", self.import_file.get()]
            
            if self.import_replace.get():
                cmd.append("--replace")
            
            self.log(f"Esecuzione comando di importazione: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante l'importazione: {stderr}")
                messagebox.showerror("Errore", f"Errore durante l'importazione: {stderr}")
                return
            
            self.log("Importazione completata con successo")
            
            # Aggiorna la lista degli allenamenti in background
            self.log("Aggiornamento cache degli allenamenti...")
            refresh_thread = threading.Thread(target=self._refresh_workouts_silent)
            refresh_thread.start()
            refresh_thread.join()  # Attendi il completamento
            
            # Imposta il flag di piano importato
            self.plan_imported = True
            
            # Ora procedi con la pianificazione
            self.log("Procedo con la pianificazione degli allenamenti...")
            self._do_schedule(selected_days, False)  # False = non è dry run
            
        except Exception as e:
            self.log(f"Errore durante l'importazione e pianificazione: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'importazione e pianificazione: {str(e)}")


    def plan_yaml_workouts(self, yaml_path, start_date, race_date, selected_days):
        """Pianifica gli allenamenti dal file YAML usando le date selezionate"""
        try:
            today = datetime.today().date()
            
            # Carica il file YAML
            with open(yaml_path, 'r') as f:
                plan_data = yaml.safe_load(f)
                
                # Rimuovi la configurazione
                plan_data.pop('config', {})
                
                # Estrai e ordina gli allenamenti per settimana e sessione
                workouts = []
                for name, _ in plan_data.items():
                    match = re.search(r'(W\d\d)S(\d\d)', name)
                    if match:
                        week_id = match.group(1)
                        session_id = int(match.group(2))
                        workouts.append((week_id, session_id, name))
                
                # Ordina per settimana e sessione
                workouts.sort()
                
                # Calcola il lunedì della settimana per iniziare la pianificazione
                if start_date.weekday() == 0:  # 0 = Monday
                    next_monday = start_date
                else:
                    days_until_monday = (7 - start_date.weekday()) % 7
                    next_monday = start_date + timedelta(days=days_until_monday)
                
                self.log(f"Pianificazione dal lunedì {next_monday}")
                
                # Organizza gli allenamenti per settimana
                week_sessions = {}
                for week_id, session_id, name in workouts:
                    if week_id not in week_sessions:
                        week_sessions[week_id] = {}
                    week_sessions[week_id][session_id] = name
                
                # Ordina le settimane
                weeks = sorted(week_sessions.keys())
                
                # Pianificazione
                scheduled = []
                used_dates = set()
                
                for week_index, week_id in enumerate(weeks):
                    week_start = next_monday + timedelta(weeks=week_index)
                    
                    # Salta settimane che sarebbero dopo la gara
                    if week_start > race_date:
                        self.log(f"Settimana {week_id} sarebbe dopo la data della gara. Saltata.")
                        continue
                    
                    sessions = week_sessions[week_id]
                    session_ids = sorted(sessions.keys())
                    
                    # Verifica che ci siano abbastanza giorni selezionati
                    if len(selected_days) < len(session_ids):
                        self.log(f"Non abbastanza giorni selezionati per settimana {week_id}. Necessari {len(session_ids)}, disponibili {len(selected_days)}.")
                    
                    # Assegna gli allenamenti ai giorni selezionati
                    for i, session_id in enumerate(session_ids):
                        workout_name = sessions[session_id]
                        
                        # Utilizza i giorni selezionati in modo ciclico
                        day_index = selected_days[i % len(selected_days)]
                        
                        # Calcola la data specifica
                        workout_date = week_start + timedelta(days=day_index)
                        date_str = workout_date.strftime('%Y-%m-%d')
                        
                        # Controlla che non sia nel passato
                        if workout_date < today:
                            self.log(f"Allenamento {week_id}S{session_id} sarebbe pianificato nel passato ({date_str}). Saltato.")
                            continue
                        
                        # Controlla che non sia dopo la data della gara
                        if workout_date > race_date:
                            self.log(f"Allenamento {week_id}S{session_id} sarebbe pianificato dopo la data della gara ({date_str}). Saltato.")
                            continue
                        
                        # Controlla se questa data è già stata utilizzata
                        if date_str in used_dates:
                            self.log(f"Data {date_str} già occupata. Cerco un'alternativa...")
                            
                            # Cerca una data alternativa
                            alternative_found = False
                            for offset in range(1, 7):
                                alt_date = workout_date + timedelta(days=offset)
                                alt_date_str = alt_date.strftime('%Y-%m-%d')
                                
                                if alt_date <= race_date and alt_date_str not in used_dates:
                                    workout_date = alt_date
                                    date_str = alt_date_str
                                    alternative_found = True
                                    self.log(f"Trovata data alternativa {date_str} per {workout_name}")
                                    break
                            
                            if not alternative_found:
                                self.log(f"Impossibile trovare una data alternativa per {workout_name}. Saltato.")
                                continue
                        
                        # Aggiungi alla pianificazione
                        used_dates.add(date_str)
                        day_name = calendar.day_name[workout_date.weekday()]
                        self.log(f"{workout_name} pianificato per {day_name} {date_str}")
                        
                        scheduled.append({
                            'date': date_str,
                            'workout': workout_name + " (SIMULAZIONE)"
                        })
                
                # Ordina la pianificazione per data
                scheduled.sort(key=lambda x: x['date'])
                
                # Visualizza nella tabella del calendario
                self.display_yaml_schedule(scheduled)
                
                # Mostra un messaggio all'utente
                messagebox.showinfo("Simulazione completata", 
                                  f"Simulazione pianificazione completata con successo.\n"
                                  f"Sono stati pianificati {len(scheduled)} allenamenti.\n"
                                  f"Questi allenamenti sono visualizzati nella tabella con l'etichetta (SIMULAZIONE).")
        
        except Exception as e:
            self.log(f"Errore nella pianificazione: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("Errore", f"Si è verificato un errore durante la pianificazione: {str(e)}")

    def display_yaml_schedule(self, scheduled):
        """Visualizza la pianificazione nella tabella del calendario"""
        try:
            # Pulisci la tabella esistente
            for item in self.calendar_tree.get_children():
                self.calendar_tree.delete(item)
            
            # Aggiungi gli allenamenti pianificati
            for item in scheduled:
                date = item['date']
                workout = item['workout']
                self.calendar_tree.insert("", "end", values=(date, workout))
        
        except Exception as e:
            self.log(f"Errore nella visualizzazione della pianificazione: {str(e)}")





    def find_yaml_for_plan(self, plan_id):
        """Cerca il file YAML corrispondente al piano specificato"""
        try:
            self.log(f"Ricerca del file YAML per il piano: '{plan_id}'")
            
            # Normalizza il plan_id per la ricerca
            plan_id_normalized = plan_id.lower().strip()
            
            # Controlla se il file YAML è già stato selezionato nella tab Importa
            import_file = self.import_file.get()
            if import_file and os.path.exists(import_file) and import_file.endswith(('.yaml', '.yml')):
                self.log(f"Controllando il file selezionato: {import_file}")
                # Verifica se il file contiene il piano
                try:
                    with open(import_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if 'config' in data and 'name_prefix' in data['config']:
                            name_prefix = data['config']['name_prefix'].strip().lower()
                            
                            # Verifica se corrisponde al piano cercato
                            self.log(f"Confronto: '{name_prefix}' con '{plan_id_normalized}'")
                            if plan_id_normalized in name_prefix or name_prefix in plan_id_normalized:
                                self.log(f"Corrispondenza trovata! Usando il file YAML già selezionato: {import_file}")
                                return import_file
                            else:
                                self.log(f"Prefisso {name_prefix} non corrisponde a {plan_id_normalized}")
                except Exception as e:
                    self.log(f"Errore nella lettura del file {import_file}: {str(e)}")
            
            # Cerca nelle directory standard
            search_dirs = [
                os.path.join(SCRIPT_DIR, "training_plans"),  # Directory principale training_plans
                SCRIPT_DIR,  # Directory principale dello script
                os.getcwd()  # Directory di lavoro corrente
            ]
            
            self.log(f"Cercando nelle directory: {search_dirs}")
            
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    self.log(f"Cercando in: {search_dir}")
                    # Cerca ricorsivamente nei file YAML
                    for root, _, files in os.walk(search_dir):
                        for file in files:
                            if file.endswith(('.yaml', '.yml')):
                                file_path = os.path.join(root, file)
                                self.log(f"Trovato file YAML: {file_path}, verifico se contiene il piano")
                                
                                # Controlla se il file contiene il piano
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        data = yaml.safe_load(f)
                                        if 'config' in data and 'name_prefix' in data['config']:
                                            name_prefix = data['config']['name_prefix'].strip().lower()
                                            
                                            # Verifica se corrisponde al piano cercato
                                            self.log(f"Confronto: '{name_prefix}' con '{plan_id_normalized}'")
                                            if plan_id_normalized in name_prefix or name_prefix in plan_id_normalized:
                                                self.log(f"Corrispondenza trovata! File YAML per il piano '{plan_id}': {file_path}")
                                                return file_path
                                            else:
                                                self.log(f"Prefisso {name_prefix} non corrisponde a {plan_id_normalized}")
                                except Exception as e:
                                    self.log(f"Errore nella lettura del file {file_path}: {str(e)}")
            
            # Se non trova automaticamente, chiede all'utente di selezionare un file
            if messagebox.askyesno("File YAML non trovato", 
                                  f"Non è stato trovato un file YAML per il piano '{plan_id}'.\n\n"
                                  f"Vuoi selezionare manualmente un file YAML?"):
                file_path = filedialog.askopenfilename(
                    title="Seleziona file YAML",
                    filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
                )
                if file_path:
                    self.log(f"File YAML selezionato manualmente: {file_path}")
                    return file_path
            
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


    def _do_import_for_schedule(self):
        """Esegue l'importazione degli allenamenti e attende il completamento."""
        self.log("Importazione degli allenamenti in corso...")
        
        # Assicurati che la cartella OAuth esista
        oauth_folder = self.oauth_folder.get()
        if not os.path.exists(oauth_folder):
            os.makedirs(oauth_folder, exist_ok=True)
            self.log(f"Creata cartella OAuth: {oauth_folder}")
        
        try:
            # Costruisci il comando per l'importazione
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", oauth_folder,
                   "--log-level", self.log_level.get(),
                   "import", 
                   "--workouts-file", self.import_file.get()]
            
            if self.import_replace.get():
                cmd.append("--replace")
            
            self.log(f"Esecuzione comando di importazione: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante l'importazione: {stderr}")
                messagebox.showerror("Errore", f"Errore durante l'importazione: {stderr}")
                return False
            
            self.log("Importazione completata con successo")
            
            # Aggiorna la lista degli allenamenti
            self.refresh_workouts()
            
            messagebox.showinfo("Importazione completata", 
                              "Gli allenamenti sono stati importati con successo.\n"
                              "Ora puoi procedere con la pianificazione.")
            
            return True
        except Exception as e:
            self.log(f"Errore durante l'importazione: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'importazione: {str(e)}")
            return False


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
            
    def validate_name_prefix(self, prefix):
        """
        Verifica che il prefisso del nome termini con uno spazio.
        
        Args:
            prefix: Il name_prefix da validare
            
        Returns:
            Il prefisso corretto con uno spazio alla fine
        """
        if prefix:
            # Se c'è un prefisso, assicurati che termini con uno spazio
            if not prefix.endswith(' '):
                return prefix.rstrip() + ' '
        return prefix

        

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