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
import workout_editor

from datetime import datetime, timedelta

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
DEFAULT_OAUTH_FOLDER = os.path.expanduser("~/.garth")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class GarminPlannerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Garmin Planner")
        self.geometry("800x600")
        
        # Variables
        self.oauth_folder = tk.StringVar(value=DEFAULT_OAUTH_FOLDER)
        self.log_level = tk.StringVar(value="INFO")
        self.log_output = []
        
        # Status bar variable - SPOSTA QUESTA DICHIARAZIONE QUI
        self.status_var = tk.StringVar(value="Pronto")
        
        # Create the notebook (tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_login_tab()
        self.create_import_tab()
        self.create_export_tab()
        self.create_schedule_tab()
        self.create_fartlek_tab()
        self.create_log_tab()
        
        # Aggiungi il tab dell'editor di workout
        workout_editor.add_workout_editor_tab(self.notebook, self)
        
        # Common settings frame
        self.create_settings_frame()
        
        # Status bar
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)


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
        self.import_name_filter = tk.StringVar()
        self.import_replace = tk.BooleanVar(value=False)
        self.import_treadmill = tk.BooleanVar(value=False)
        self.import_dry_run = tk.BooleanVar(value=False)
        
        # Widgets
        ttk.Label(import_frame, text="Importa allenamenti da file YAML", font=("", 12, "bold")).pack(pady=10)
        
        file_frame = ttk.Frame(import_frame)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(file_frame, text="File allenamenti:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(file_frame, textvariable=self.import_file, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Sfoglia", command=self.browse_import_file).grid(row=0, column=2, padx=5, pady=5)
        
        filter_frame = ttk.Frame(import_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="Filtro nomi:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(filter_frame, textvariable=self.import_name_filter, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        options_frame = ttk.Frame(import_frame)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(options_frame, text="Sostituisci allenamenti esistenti", variable=self.import_replace).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Modalità tapis roulant", variable=self.import_treadmill).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Simulazione (dry run)", variable=self.import_dry_run).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(import_frame, text="Importa", command=self.perform_import).pack(pady=10)
        
        # Display available training plans
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
        self.export_name_filter = tk.StringVar()
        self.export_format = tk.StringVar(value="YAML")
        self.export_clean = tk.BooleanVar(value=True)
        
        # Widgets
        ttk.Label(export_frame, text="Esporta allenamenti", font=("", 12, "bold")).pack(pady=10)
        
        file_frame = ttk.Frame(export_frame)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(file_frame, text="File di destinazione:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(file_frame, textvariable=self.export_file, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Sfoglia", command=self.browse_export_file).grid(row=0, column=2, padx=5, pady=5)
        
        filter_frame = ttk.Frame(export_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="Filtro nomi:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(filter_frame, textvariable=self.export_name_filter, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        options_frame = ttk.Frame(export_frame)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(options_frame, text="Formato:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(options_frame, textvariable=self.export_format, values=["YAML", "JSON"]).grid(row=0, column=1, padx=5, pady=5)
        ttk.Checkbutton(options_frame, text="Pulisci dati", variable=self.export_clean).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(export_frame, text="Esporta", command=self.perform_export).pack(pady=10)
        
        # List of current workouts
        ttk.Label(export_frame, text="Allenamenti disponibili su Garmin Connect").pack(pady=5)
        
        self.workouts_tree = ttk.Treeview(export_frame, columns=("id", "name"), show="headings")
        self.workouts_tree.heading("id", text="ID")
        self.workouts_tree.heading("name", text="Nome")
        self.workouts_tree.column("id", width=100)
        self.workouts_tree.column("name", width=500)
        self.workouts_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Button(export_frame, text="Aggiorna lista", command=self.refresh_workouts).pack(pady=5)

    def create_schedule_tab(self):
        schedule_frame = ttk.Frame(self.notebook)
        self.notebook.add(schedule_frame, text="Pianifica")
        
        # Variables
        self.training_plan = tk.StringVar()
        self.race_day = tk.StringVar(value=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"))
        self.reverse_order = tk.BooleanVar(value=False)
        self.schedule_dry_run = tk.BooleanVar(value=False)
        
        # Widgets
        ttk.Label(schedule_frame, text="Pianifica allenamenti", font=("", 12, "bold")).pack(pady=10)
        
        plan_frame = ttk.Frame(schedule_frame)
        plan_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(plan_frame, text="ID Piano di allenamento:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(plan_frame, textvariable=self.training_plan, width=30).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(plan_frame, text="(prefisso comune degli allenamenti)").grid(row=0, column=2, padx=5, pady=5)
        
        date_frame = ttk.Frame(schedule_frame)
        date_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(date_frame, text="Giorno gara (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(date_frame, textvariable=self.race_day, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        options_frame = ttk.Frame(schedule_frame)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(options_frame, text="Ordine inverso delle settimane", variable=self.reverse_order).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Simulazione (dry run)", variable=self.schedule_dry_run).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
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

    def create_fartlek_tab(self):
        fartlek_frame = ttk.Frame(self.notebook)
        self.notebook.add(fartlek_frame, text="Fartlek")
        
        # Variables
        self.fartlek_duration = tk.StringVar(value="45:00")
        self.fartlek_pace = tk.StringVar(value="5:00")
        self.fartlek_schedule = tk.StringVar()
        
        # Widgets
        ttk.Label(fartlek_frame, text="Crea un allenamento Fartlek casuale", font=("", 12, "bold")).pack(pady=10)
        
        settings_frame = ttk.Frame(fartlek_frame)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(settings_frame, text="Durata (mm:ss):").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.fartlek_duration, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Ritmo target (mm:ss):").grid(row=1, column=0, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.fartlek_pace, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        schedule_frame = ttk.Frame(fartlek_frame)
        schedule_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(schedule_frame, text="Pianifica (opzionale):").grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(schedule_frame, textvariable=self.fartlek_schedule, 
                     values=["", "today", "tomorrow", datetime.now().strftime("%Y-%m-%d")]).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(fartlek_frame, text="Crea Fartlek", command=self.create_fartlek).pack(pady=10)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(fartlek_frame, text="Anteprima")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.fartlek_preview = tk.Text(preview_frame, wrap=tk.WORD, height=15)
        self.fartlek_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Example of a fartlek workout
        self.fartlek_preview.insert(tk.END, "Esempio di allenamento Fartlek:\n\n")
        self.fartlek_preview.insert(tk.END, "- Riscaldamento: 10:00\n")
        self.fartlek_preview.insert(tk.END, "- Intervallo 1: 01:15 (ritmo veloce)\n")
        self.fartlek_preview.insert(tk.END, "- Recupero 1: 01:45\n")
        self.fartlek_preview.insert(tk.END, "- Intervallo 2: 02:00 (ritmo veloce)\n")
        self.fartlek_preview.insert(tk.END, "- Recupero 2: 01:30\n")
        self.fartlek_preview.insert(tk.END, "...\n")
        self.fartlek_preview.insert(tk.END, "- Defaticamento: 10:00\n")
        self.fartlek_preview.config(state=tk.DISABLED)

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
        self.log_text.delete(1.0, tk.END)

    def log(self, message):
        """Add a message to the log tab"""
        logger.info(message)
        self.status_var.set(message)
    
    # Tab functionality methods
    def perform_login(self):
        self.log("Avvio procedura di login...")
        
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
        try:
            import sys
            import os
            
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
                garth.save(self.oauth_folder.get())
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
                        
                        if len(parts) >= 3:
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
        try:
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", self.oauth_folder.get(),
                   "--log-level", self.log_level.get()]
            
            if self.import_treadmill.get():
                cmd.append("--treadmill")
            
            if self.import_dry_run.get():
                cmd.append("--dry-run")
            
            cmd.extend(["import", "--workouts-file", self.import_file.get()])
            
            if self.import_name_filter.get():
                cmd.extend(["--name-filter", self.import_name_filter.get()])
            
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
                if self.import_dry_run.get():
                    self.log("(Modalità dry-run - nessuna modifica effettiva)")
                else:
                    messagebox.showinfo("Successo", "Importazione completata con successo")
                    # Refresh the workout list
                    self.refresh_workouts()
        
        except Exception as e:
            self.log(f"Errore durante l'importazione: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'importazione: {str(e)}")
    
    def refresh_workouts(self):
        """Refresh the list of workouts from Garmin Connect"""
        self.log("Aggiornamento lista allenamenti...")
        
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
    
    def perform_export(self):
        """Export workouts to a file"""
        self.log("Esportazione degli allenamenti...")
        
        # Run the export command in a separate thread
        threading.Thread(target=self._do_export).start()
    
    def _do_export(self):
        try:
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", self.oauth_folder.get(),
                   "--log-level", self.log_level.get(),
                   "export"]
            
            if self.export_file.get():
                cmd.extend(["--export-file", self.export_file.get()])
            
            if self.export_name_filter.get():
                cmd.extend(["--name-filter", self.export_name_filter.get()])
            
            cmd.extend(["--format", self.export_format.get()])
            
            if self.export_clean.get():
                cmd.append("--clean")
            
            self.log(f"Esecuzione comando: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante l'esportazione: {stderr}")
                messagebox.showerror("Errore", f"Errore durante l'esportazione: {stderr}")
            else:
                if self.export_file.get():
                    self.log(f"Esportazione completata con successo su {self.export_file.get()}")
                    messagebox.showinfo("Successo", f"Esportazione completata con successo su {self.export_file.get()}")
                else:
                    # Display the output in a popup
                    output_window = tk.Toplevel(self)
                    output_window.title("Risultato Esportazione")
                    output_window.geometry("800x600")
                    
                    text = tk.Text(output_window, wrap=tk.NONE)
                    text.pack(fill=tk.BOTH, expand=True)
                    
                    # Add a scrollbar
                    scrollbar = ttk.Scrollbar(text, command=text.yview)
                    text.configure(yscrollcommand=scrollbar.set)
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    
                    text.insert(tk.END, stdout)
                    text.config(state=tk.DISABLED)
                    
                    self.log("Esportazione completata con successo")
        
        except Exception as e:
            self.log(f"Errore durante l'esportazione: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'esportazione: {str(e)}")
    
    def refresh_calendar(self):
        """Refresh the calendar view"""
        self.log("Aggiornamento calendario...")
        
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
        
        # Validate race day format
        try:
            datetime.strptime(self.race_day.get(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Errore", "Formato data non valido. Usa YYYY-MM-DD")
            return
        
        self.log(f"Pianificazione allenamenti per il piano {self.training_plan.get()}...")
        
        # Run the schedule command in a separate thread
        threading.Thread(target=self._do_schedule).start()
    
    def _do_schedule(self):
        try:
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", self.oauth_folder.get(),
                   "--log-level", self.log_level.get()]
            
            if self.schedule_dry_run.get():
                cmd.append("--dry-run")
            
            cmd.extend(["schedule",
                       "--training-plan", self.training_plan.get(),
                       "--race-day", self.race_day.get()])
            
            if self.reverse_order.get():
                cmd.append("--reverse-order")
            
            self.log(f"Esecuzione comando: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante la pianificazione: {stderr}")
                messagebox.showerror("Errore", f"Errore durante la pianificazione: {stderr}")
            else:
                self.log("Pianificazione completata con successo")
                if self.schedule_dry_run.get():
                    self.log("(Modalità dry-run - nessuna modifica effettiva)")
                else:
                    messagebox.showinfo("Successo", "Pianificazione completata con successo")
                    # Refresh the calendar
                    self.refresh_calendar()
        
        except Exception as e:
            self.log(f"Errore durante la pianificazione: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante la pianificazione: {str(e)}")
    
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
    
    def create_fartlek(self):
        """Create a random fartlek workout"""
        if not self.fartlek_duration.get():
            messagebox.showerror("Errore", "Inserisci la durata dell'allenamento")
            return
        
        if not self.fartlek_pace.get():
            messagebox.showerror("Errore", "Inserisci il ritmo target")
            return
        
        # Validate duration and pace format
        duration_pattern = re.compile(r'^\d{1,2}:\d{2}$')
        pace_pattern = re.compile(r'^\d{1,2}:\d{2}$')
        
        if not duration_pattern.match(self.fartlek_duration.get()):
            messagebox.showerror("Errore", "Formato durata non valido. Usa mm:ss")
            return
        
        if not pace_pattern.match(self.fartlek_pace.get()):
            messagebox.showerror("Errore", "Formato ritmo non valido. Usa mm:ss")
            return
        
        self.log("Creazione allenamento Fartlek...")
        
        # Run the fartlek command in a separate thread
        threading.Thread(target=self._do_create_fartlek).start()
    
    def _do_create_fartlek(self):
        try:
            cmd = ["python", os.path.join(SCRIPT_DIR, "garmin_planner.py"),
                   "--oauth-folder", self.oauth_folder.get(),
                   "--log-level", self.log_level.get(),
                   "fartlek",
                   "--duration", self.fartlek_duration.get(),
                   "--target-pace", self.fartlek_pace.get()]
            
            if self.fartlek_schedule.get():
                cmd.extend(["--schedule", self.fartlek_schedule.get()])
            
            self.log(f"Esecuzione comando: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.log(f"Errore durante la creazione del Fartlek: {stderr}")
                messagebox.showerror("Errore", f"Errore durante la creazione del Fartlek: {stderr}")
            else:
                self.log("Allenamento Fartlek creato con successo")
                messagebox.showinfo("Successo", "Allenamento Fartlek creato con successo")
                
                # Display workout preview if available
                if stdout:
                    # Update preview
                    self.fartlek_preview.config(state=tk.NORMAL)
                    self.fartlek_preview.delete(1.0, tk.END)
                    self.fartlek_preview.insert(tk.END, stdout)
                    self.fartlek_preview.config(state=tk.DISABLED)
                
                # Refresh workouts list
                self.refresh_workouts()
                
                # Refresh calendar if scheduled
                if self.fartlek_schedule.get():
                    self.refresh_calendar()
        
        except Exception as e:
            self.log(f"Errore durante la creazione del Fartlek: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante la creazione del Fartlek: {str(e)}")

class TextHandler(logging.Handler):
    """Handler per redirezionare i log al widget Text"""
    
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
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