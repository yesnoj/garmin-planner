#!/usr/bin/env python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import yaml
import os
import re
import json
import sys
from functools import partial

print("Script avviato")  # Messaggio di debug
print("Inizializzazione delle classi...")

class WorkoutEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Editor di Allenamenti per Garmin Planner")
        self.geometry("1000x700")
        
        # Variabili generali
        self.current_file = None
        self.modified = False
        self.current_workout = None
        
        # Dati del piano
        self.configuration = {
            "paces": {},
            "heart_rates": {},
            "margins": {"faster": "0:03", "slower": "0:03", "hr_up": 5, "hr_down": 5},
            "name_prefix": ""
        }
        self.workouts = {}
        
        # Crea il menu
        self.create_menu()
        
        # Crea i pannelli principali
        self.create_main_frame()
        
        # Inizializza l'interfaccia
        self.update_workouts_list()
        
    def create_menu(self):
        menubar = tk.Menu(self)
        
        # Menu File
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Nuovo Piano", command=self.new_plan)
        file_menu.add_command(label="Apri...", command=self.open_file)
        file_menu.add_command(label="Salva", command=self.save_file)
        file_menu.add_command(label="Salva con nome...", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.quit_app)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Menu Configurazione
        config_menu = tk.Menu(menubar, tearoff=0)
        config_menu.add_command(label="Modifica Configurazione", command=self.edit_config)
        menubar.add_cascade(label="Configurazione", menu=config_menu)
        
        # Menu Allenamenti
        workout_menu = tk.Menu(menubar, tearoff=0)
        workout_menu.add_command(label="Nuovo Allenamento", command=self.add_workout)
        workout_menu.add_command(label="Elimina Allenamento", command=self.delete_workout)
        menubar.add_cascade(label="Allenamenti", menu=workout_menu)
        
        # Menu Aiuto
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Guida", command=self.show_help)
        help_menu.add_command(label="Informazioni", command=self.show_about)
        menubar.add_cascade(label="Aiuto", menu=help_menu)
        
        self.configuration(menu=menubar)
    
    def create_main_frame(self):
        # Frame principale suddiviso in due parti
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame sinistro per la lista degli allenamenti
        left_frame = ttk.LabelFrame(main_frame, text="Allenamenti")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Lista degli allenamenti
        self.workouts_listbox = tk.Listbox(left_frame, width=25, height=30)
        self.workouts_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.workouts_listbox.bind('<<ListboxSelect>>', self.on_workout_selected)
        
        # Scrollbar per la lista
        workouts_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.workouts_listbox.yview)
        workouts_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.workouts_listbox.configure(yscrollcommand=workouts_scrollbar.set)
        
        # Pulsanti per gestire gli allenamenti
        workout_buttons_frame = ttk.Frame(left_frame)
        workout_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(workout_buttons_frame, text="Aggiungi", command=self.add_workout).pack(side=tk.LEFT, padx=2)
        ttk.Button(workout_buttons_frame, text="Elimina", command=self.delete_workout).pack(side=tk.LEFT, padx=2)
        ttk.Button(workout_buttons_frame, text="Duplica", command=self.duplicate_workout).pack(side=tk.LEFT, padx=2)
        
        # Frame destro per l'editor dell'allenamento
        right_frame = ttk.LabelFrame(main_frame, text="Editor Allenamento")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Editor nome allenamento
        name_frame = ttk.Frame(right_frame)
        name_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(name_frame, text="Nome:").pack(side=tk.LEFT, padx=5)
        self.workout_name_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.workout_name_var, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.workout_name_var.trace_add("write", self.on_workout_name_changed)
        
        # Tabella degli step dell'allenamento
        steps_frame = ttk.Frame(right_frame)
        steps_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Definisci le colonne della tabella
        columns = ("step_type", "duration", "target", "description")
        self.steps_tree = ttk.Treeview(steps_frame, columns=columns, show="headings", selectmode="browse")
        
        # Definisci le intestazioni delle colonne
        self.steps_tree.heading("step_type", text="Tipo")
        self.steps_tree.heading("duration", text="Durata/Distanza")
        self.steps_tree.heading("target", text="Target")
        self.steps_tree.heading("description", text="Descrizione")
        
        # Definisci la larghezza delle colonne
        self.steps_tree.column("step_type", width=100)
        self.steps_tree.column("duration", width=150)
        self.steps_tree.column("target", width=150)
        self.steps_tree.column("description", width=200)
        
        # Scrollbar per la tabella
        steps_scrollbar = ttk.Scrollbar(steps_frame, orient=tk.VERTICAL, command=self.steps_tree.yview)
        steps_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.steps_tree.configure(yscrollcommand=steps_scrollbar.set)
        self.steps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind per la doppia-click sulla tabella
        self.steps_tree.bind("<Double-1>", self.edit_step)
        
        # Pulsanti per gestire gli step
        steps_buttons_frame = ttk.Frame(right_frame)
        steps_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(steps_buttons_frame, text="Aggiungi Step", command=self.add_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(steps_buttons_frame, text="Modifica Step", command=lambda: self.edit_step(None)).pack(side=tk.LEFT, padx=2)
        ttk.Button(steps_buttons_frame, text="Elimina Step", command=self.delete_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(steps_buttons_frame, text="Sposta Su", command=lambda: self.move_step(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(steps_buttons_frame, text="Sposta Giù", command=lambda: self.move_step(1)).pack(side=tk.LEFT, padx=2)
        
        # Pulsante per salvare l'allenamento
        save_frame = ttk.Frame(right_frame)
        save_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(save_frame, text="Salva Allenamento", command=self.save_current_workout).pack(side=tk.RIGHT, padx=5)
    
    def update_workouts_list(self):
        """Aggiorna la lista degli allenamenti."""
        self.workouts_listbox.delete(0, tk.END)
        for name in sorted(self.workouts.keys()):
            self.workouts_listbox.insert(tk.END, name)
    
    def on_workout_selected(self, event):
        """Gestisce la selezione di un allenamento dalla lista."""
        if not self.workouts_listbox.curselection():
            return
        
        # Controlla se ci sono modifiche non salvate
        if self.current_workout and self.modified:
            if not messagebox.askyesno("Modifiche non salvate", 
                                      "Ci sono modifiche non salvate. Vuoi continuare?"):
                # Riseleziona l'allenamento corrente
                index = list(self.workouts.keys()).index(self.current_workout)
                self.workouts_listbox.selection_clear(0, tk.END)
                self.workouts_listbox.selection_set(index)
                return
        
        # Ottieni il nome dell'allenamento selezionato
        index = self.workouts_listbox.curselection()[0]
        workout_name = self.workouts_listbox.get(index)
        
        # Carica l'allenamento
        self.load_workout(workout_name)
    
    def load_workout(self, workout_name):
        """Carica un allenamento nell'editor."""
        self.current_workout = workout_name
        self.modified = False
        
        # Imposta il nome dell'allenamento
        self.workout_name_var.set(workout_name)
        
        # Carica gli step dell'allenamento
        self.steps_tree.delete(*self.steps_tree.get_children())
        
        steps = self.workouts.get(workout_name, [])
        for i, step in enumerate(steps):
            for key, value in step.items():
                if key.startswith('repeat'):
                    # Gestisci ripetizioni
                    iterations = key.split()[1]
                    self.steps_tree.insert("", "end", values=(f"repeat {iterations}", "", "", ""))
                    
                    # Aggiungi gli step interni alla ripetizione
                    for sub_step in value:
                        for sub_key, sub_value in sub_step.items():
                            self.steps_tree.insert("", "end", values=(f"  {sub_key}", *self.format_step_values(sub_value)))
                else:
                    # Gestisci step normali
                    self.steps_tree.insert("", "end", values=(key, *self.format_step_values(value)))
    
    def format_step_values(self, step_value):
        """Formatta i valori di uno step per la visualizzazione nella tabella."""
        if not step_value or isinstance(step_value, (list, dict)):
            return ["", "", ""]
        
        # Cerca di estrarre target e descrizione
        step_str = str(step_value)
        target = ""
        description = ""
        
        # Cerca target di tipo pace o heartrate
        if " @ " in step_str:
            parts = step_str.split(" @ ")
            duration = parts[0]
            target = parts[1]
            
            # Cerca descrizione
            if " -- " in target:
                target_parts = target.split(" -- ")
                target = target_parts[0]
                description = target_parts[1]
        elif " @hr " in step_str:
            parts = step_str.split(" @hr ")
            duration = parts[0]
            target = f"HR: {parts[1]}"
            
            # Cerca descrizione
            if " -- " in target:
                target_parts = target.split(" -- ")
                target = target_parts[0]
                description = target_parts[1]
        elif " in " in step_str:
            parts = step_str.split(" in ")
            duration = parts[0]
            target = f"Pace: {parts[1]}"
            
            # Cerca descrizione
            if " -- " in target:
                target_parts = target.split(" -- ")
                target = target_parts[0]
                description = target_parts[1]
        else:
            duration = step_str
            
            # Cerca descrizione
            if " -- " in duration:
                duration_parts = duration.split(" -- ")
                duration = duration_parts[0]
                description = duration_parts[1]
        
        return [duration, target, description]
    
    def on_workout_name_changed(self, *args):
        """Gestisce il cambio del nome dell'allenamento."""
        if not self.current_workout:
            return
            
        new_name = self.workout_name_var.get()
        if new_name != self.current_workout:
            # Controlla se il nuovo nome esiste già
            if new_name in self.workouts and new_name != self.current_workout:
                messagebox.showerror("Errore", f"Esiste già un allenamento con il nome '{new_name}'")
                self.workout_name_var.set(self.current_workout)
                return
                
            # Rinomina l'allenamento
            self.workouts[new_name] = self.workouts.pop(self.current_workout)
            self.current_workout = new_name
            self.modified = True
            self.update_workouts_list()
            
            # Seleziona il nuovo nome nella lista
            index = list(self.workouts.keys()).index(new_name)
            self.workouts_listbox.selection_clear(0, tk.END)
            self.workouts_listbox.selection_set(index)
    
    def edit_config(self):
        """Apre l'editor della configurazione."""
        config_editor = ConfigEditor(self, self.configuration)
        self.wait_window(config_editor)
        if config_editor.result:
            self.configuration = config_editor.result
            self.modified = True
    
    def add_workout(self):
        """Aggiunge un nuovo allenamento."""
        name = simpledialog.askstring("Nuovo Allenamento", "Nome dell'allenamento:")
        if not name:
            return
            
        # Controlla se il nome esiste già
        if name in self.workouts:
            messagebox.showerror("Errore", f"Esiste già un allenamento con il nome '{name}'")
            return
            
        # Crea un nuovo allenamento vuoto
        self.workouts[name] = []
        self.update_workouts_list()
        
        # Seleziona il nuovo allenamento
        index = list(self.workouts.keys()).index(name)
        self.workouts_listbox.selection_clear(0, tk.END)
        self.workouts_listbox.selection_set(index)
        self.workouts_listbox.see(index)
        
        # Carica l'allenamento
        self.load_workout(name)
    
    def delete_workout(self):
        """Elimina un allenamento."""
        if not self.current_workout:
            messagebox.showerror("Errore", "Nessun allenamento selezionato")
            return
            
        if messagebox.askyesno("Elimina Allenamento", f"Sei sicuro di voler eliminare l'allenamento '{self.current_workout}'?"):
            del self.workouts[self.current_workout]
            self.current_workout = None
            self.modified = True
            self.update_workouts_list()
            
            # Pulisci l'editor
            self.workout_name_var.set("")
            self.steps_tree.delete(*self.steps_tree.get_children())
    
    def duplicate_workout(self):
        """Duplica un allenamento."""
        if not self.current_workout:
            messagebox.showerror("Errore", "Nessun allenamento selezionato")
            return
            
        # Chiedi il nome del nuovo allenamento
        new_name = simpledialog.askstring("Duplica Allenamento", 
                                          "Nome del nuovo allenamento:", 
                                          initialvalue=f"{self.current_workout} (copia)")
        if not new_name:
            return
            
        # Controlla se il nome esiste già
        if new_name in self.workouts:
            messagebox.showerror("Errore", f"Esiste già un allenamento con il nome '{new_name}'")
            return
            
        # Duplica l'allenamento
        self.workouts[new_name] = self.workouts[self.current_workout].copy()
        self.modified = True
        self.update_workouts_list()
        
        # Seleziona il nuovo allenamento
        index = list(self.workouts.keys()).index(new_name)
        self.workouts_listbox.selection_clear(0, tk.END)
        self.workouts_listbox.selection_set(index)
        self.workouts_listbox.see(index)
        
        # Carica l'allenamento
        self.load_workout(new_name)
    
    def add_step(self):
        """Aggiunge un nuovo step all'allenamento."""
        if not self.current_workout:
            messagebox.showerror("Errore", "Nessun allenamento selezionato")
            return
            
        # Apri l'editor di step
        step_editor = StepEditor(self, self.configuration)
        self.wait_window(step_editor)
        
        if step_editor.result:
            step_type, step_value = step_editor.result
            
            # Aggiungi lo step all'allenamento
            if step_type.startswith("repeat"):
                # Per le ripetizioni, crea una struttura speciale
                iterations = int(step_type.split()[1])
                self.workouts[self.current_workout].append({f"repeat {iterations}": []})
            else:
                # Per gli step normali
                self.workouts[self.current_workout].append({step_type: step_value})
            
            self.modified = True
            
            # Ricarica l'allenamento
            self.load_workout(self.current_workout)
    
    def edit_step(self, event):
        """Modifica uno step esistente."""
        if not self.current_workout:
            messagebox.showerror("Errore", "Nessun allenamento selezionato")
            return
            
        # Ottieni lo step selezionato
        selection = self.steps_tree.selection()
        if not selection:
            messagebox.showerror("Errore", "Nessuno step selezionato")
            return
        
        # Ottieni i dati dello step
        item = self.steps_tree.item(selection[0])
        values = item['values']
        step_type = values[0]
        
        # Non è possibile modificare direttamente le ripetizioni
        if step_type.startswith("repeat") and not step_type.startswith("  "):
            messagebox.showerror("Errore", "Non è possibile modificare direttamente le ripetizioni. Aggiungi o modifica gli step all'interno.")
            return
        
        # Ottieni l'indice dello step nel workout
        index = self.steps_tree.index(selection[0])
        
        # Per gli step all'interno di una ripetizione
        if step_type.startswith("  "):
            messagebox.showerror("Errore", "La modifica degli step all'interno delle ripetizioni non è ancora supportata")
            return
        
        # Apri l'editor di step con i dati attuali
        current_value = None
        for i, step in enumerate(self.workouts[self.current_workout]):
            if i == index:
                for k, v in step.items():
                    current_value = v
                    step_type = k
                break
        
        step_editor = StepEditor(self, self.configuration, step_type, current_value)
        self.wait_window(step_editor)
        
        if step_editor.result:
            new_step_type, new_step_value = step_editor.result
            
            # Aggiorna lo step
            self.workouts[self.current_workout][index] = {new_step_type: new_step_value}
            self.modified = True
            
            # Ricarica l'allenamento
            self.load_workout(self.current_workout)
    
    def delete_step(self):
        """Elimina uno step dall'allenamento."""
        if not self.current_workout:
            messagebox.showerror("Errore", "Nessun allenamento selezionato")
            return
            
        # Ottieni lo step selezionato
        selection = self.steps_tree.selection()
        if not selection:
            messagebox.showerror("Errore", "Nessuno step selezionato")
            return
        
        # Ottieni l'indice dello step
        index = self.steps_tree.index(selection[0])
        
        # Elimina lo step
        self.workouts[self.current_workout].pop(index)
        self.modified = True
        
        # Ricarica l'allenamento
        self.load_workout(self.current_workout)
    
    def move_step(self, direction):
        """Sposta uno step su o giù."""
        if not self.current_workout:
            messagebox.showerror("Errore", "Nessun allenamento selezionato")
            return
            
        # Ottieni lo step selezionato
        selection = self.steps_tree.selection()
        if not selection:
            messagebox.showerror("Errore", "Nessuno step selezionato")
            return
        
        # Ottieni l'indice dello step
        index = self.steps_tree.index(selection[0])
        
        # Controlla se lo spostamento è possibile
        if direction < 0 and index == 0:
            return
        if direction > 0 and index == len(self.workouts[self.current_workout]) - 1:
            return
        
        # Sposta lo step
        steps = self.workouts[self.current_workout]
        steps[index], steps[index + direction] = steps[index + direction], steps[index]
        self.modified = True
        
        # Ricarica l'allenamento
        self.load_workout(self.current_workout)
        
        # Seleziona lo step spostato
        self.steps_tree.selection_set(self.steps_tree.get_children()[index + direction])
    
    def save_current_workout(self):
        """Salva l'allenamento corrente."""
        if not self.current_workout:
            messagebox.showerror("Errore", "Nessun allenamento selezionato")
            return
            
        self.modified = False
        messagebox.showinfo("Allenamento Salvato", f"L'allenamento '{self.current_workout}' è stato salvato")
    
    def new_plan(self):
        """Crea un nuovo piano di allenamento."""
        if self.modified:
            if not messagebox.askyesno("Modifiche non salvate", 
                                      "Ci sono modifiche non salvate. Vuoi continuare?"):
                return
        
        # Resetta lo stato
        self.current_file = None
        self.modified = False
        self.current_workout = None
        
        # Resetta i dati
        self.configuration = {
            "paces": {},
            "heart_rates": {},
            "margins": {"faster": "0:03", "slower": "0:03", "hr_up": 5, "hr_down": 5},
            "name_prefix": ""
        }
        self.workouts = {}
        
        # Aggiorna l'interfaccia
        self.update_workouts_list()
        self.workout_name_var.set("")
        self.steps_tree.delete(*self.steps_tree.get_children())
        
        # Aggiorna il titolo
        self.title("Editor di Allenamenti per Garmin Planner - Nuovo Piano")
    
    def open_file(self):
        """Apre un file YAML esistente."""
        if self.modified:
            if not messagebox.askyesno("Modifiche non salvate", 
                                      "Ci sono modifiche non salvate. Vuoi continuare?"):
                return
        
        # Chiedi il file da aprire
        filepath = filedialog.askopenfilename(
            title="Apri Piano di Allenamento",
            filetypes=[("YAML", "*.yaml *.yml"), ("Tutti i file", "*.*")]
        )
        
        if not filepath:
            return
            
        try:
            # Carica il file YAML
            with open(filepath, 'r') as file:
                data = yaml.safe_load(file)
            
            # Estrai la configurazione
            self.configuration = data.pop('config', {
                "paces": {},
                "heart_rates": {},
                "margins": {"faster": "0:03", "slower": "0:03", "hr_up": 5, "hr_down": 5},
                "name_prefix": ""
            })
            
            # Il resto sono gli allenamenti
            self.workouts = data
            
            # Aggiorna lo stato
            self.current_file = filepath
            self.modified = False
            self.current_workout = None
            
            # Aggiorna l'interfaccia
            self.update_workouts_list()
            self.workout_name_var.set("")
            self.steps_tree.delete(*self.steps_tree.get_children())
            
            # Aggiorna il titolo
            filename = os.path.basename(filepath)
            self.title(f"Editor di Allenamenti per Garmin Planner - {filename}")
            
            messagebox.showinfo("File Aperto", f"Il file '{filename}' è stato aperto con successo")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire il file: {str(e)}")
    
    def save_file(self):
        """Salva il piano di allenamento nel file corrente."""
        if not self.current_file:
            return self.save_as_file()
            
        try:
            # Prepara i dati da salvare
            data = {'config': self.configuration}
            data.update(self.workouts)
            
            # Salva nel file YAML
            with open(self.current_file, 'w') as file:
                yaml.dump(data, file, default_flow_style=False, sort_keys=False)
            
            # Aggiorna lo stato
            self.modified = False
            
            # Aggiorna il titolo
            filename = os.path.basename(self.current_file)
            self.title(f"Editor di Allenamenti per Garmin Planner - {filename}")
            
            messagebox.showinfo("File Salvato", f"Il file '{filename}' è stato salvato con successo")
            return True
            
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare il file: {str(e)}")
            return False
    
    def save_as_file(self):
        """Salva il piano di allenamento in un nuovo file."""
        # Chiedi il file in cui salvare
        filepath = filedialog.asksaveasfilename(
            title="Salva Piano di Allenamento",
            filetypes=[("YAML", "*.yaml"), ("Tutti i file", "*.*")],
            defaultextension=".yaml"
        )
        
        if not filepath:
            return False
            
        # Aggiorna il file corrente
        self.current_file = filepath
        
        # Salva il file
        return self.save_file()
    
    def quit_app(self):
        """Chiude l'applicazione."""
        if self.modified:
            if not messagebox.askyesno("Modifiche non salvate", 
                                      "Ci sono modifiche non salvate. Vuoi uscire comunque?"):
                return
                
        self.destroy()
    
    def show_help(self):
        """Mostra la guida dell'applicazione."""
        help_text = """
        Editor di Allenamenti per Garmin Planner
        
        Questa applicazione consente di creare e modificare piani di allenamento da utilizzare con Garmin Planner.
        
        Funzionalità principali:
        - Creare e modificare piani di allenamento
        - Definire ritmi, zone di frequenza cardiaca e margini
        - Creare allenamenti con step di diversi tipi
        - Salvare e caricare piani di allenamento in formato YAML
        
        Per ulteriori informazioni consulta il README di Garmin Planner.
        """
        messagebox.showinfo("Guida", help_text)
    
    def show_about(self):
        """Mostra informazioni sull'applicazione."""
        about_text = """
        Editor di Allenamenti per Garmin Planner
        
        Versione 1.0
        
        Creato per facilitare la creazione e modifica dei piani di allenamento per Garmin Planner.
        
        Basato sul progetto garmin-planner.
        """
        messagebox.showinfo("Informazioni", about_text)


class ConfigEditor(tk.Toplevel):
    """Finestra per la modifica della configurazione."""
    def __init__(self, parent, config):
        super().__init__(parent)
        self.title("Configurazione Piano")
        self.geometry("800x600")
        self.resizable(True, True)
        self.transient(parent)  # Rende la finestra modale
        self.grab_set()  # Impedisce di interagire con la finestra principale
        
        # Copia della configurazione
        self.configuration = {k: (v.copy() if isinstance(v, dict) else v) for k, v in config.items()}
        self.result = None
        
        # Crea il notebook per le diverse sezioni
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scheda per i ritmi (paces)
        paces_frame = ttk.Frame(notebook)
        notebook.add(paces_frame, text="Ritmi")
        self.create_paces_tab(paces_frame)
        
        # Scheda per le frequenze cardiache
        hr_frame = ttk.Frame(notebook)
        notebook.add(hr_frame, text="Frequenze Cardiache")
        self.create_hr_tab(hr_frame)
        
        # Scheda per i margini e altre impostazioni
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Impostazioni")
        self.create_settings_tab(settings_frame)
        
        # Pulsanti di conferma e annullamento
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Annulla", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="OK", command=self.confirm).pack(side=tk.RIGHT, padx=5)
    
    def create_paces_tab(self, parent):
        """Crea la scheda per i ritmi."""
        # Istruzioni
        ttk.Label(parent, text="Definisci i ritmi da utilizzare negli allenamenti. Puoi specificare:", 
                font=("", 10, "bold")).pack(anchor=tk.W, padx=10, pady=5)
        ttk.Label(parent, text="- Un singolo ritmo (es. 4:30)").pack(anchor=tk.W, padx=10)
        ttk.Label(parent, text="- Un intervallo di ritmi (es. 4:30-4:40)").pack(anchor=tk.W, padx=10)
        ttk.Label(parent, text="- Un ritmo basato su distanza/tempo (es. 10km in 45:00)").pack(anchor=tk.W, padx=10)
        ttk.Label(parent, text="- Una percentuale di un altro ritmo (es. 80% marathon)").pack(anchor=tk.W, padx=10, pady=5)
        
        # Frame per la tabella e i pulsanti
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Tabella dei ritmi
        columns = ("name", "value")
        self.paces_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.paces_tree.heading("name", text="Nome")
        self.paces_tree.heading("value", text="Valore")
        self.paces_tree.column("name", width=150)
        self.paces_tree.column("value", width=250)
        self.paces_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar per la tabella
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.paces_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.paces_tree.configure(yscrollcommand=scrollbar.set)
        
        # Carica i ritmi esistenti
        for name, value in self.configuration.get("paces", {}).items():
            self.paces_tree.insert("", "end", values=(name, value))
        
        # Pulsanti per gestire i ritmi
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="Aggiungi", command=self.add_pace).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Modifica", command=self.edit_pace).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Elimina", command=self.delete_pace).pack(side=tk.LEFT, padx=2)
        
        # Bind per l'editing con doppio click
        self.paces_tree.bind("<Double-1>", lambda e: self.edit_pace())
    
    def create_hr_tab(self, parent):
        """Crea la scheda per le frequenze cardiache."""
        # Istruzioni
        ttk.Label(parent, text="Definisci le zone di frequenza cardiaca da utilizzare negli allenamenti. Puoi specificare:", 
                font=("", 10, "bold")).pack(anchor=tk.W, padx=10, pady=5)
        ttk.Label(parent, text="- Un valore singolo (es. 150)").pack(anchor=tk.W, padx=10)
        ttk.Label(parent, text="- Un intervallo (es. 140-150)").pack(anchor=tk.W, padx=10)
        ttk.Label(parent, text="- Una percentuale di un'altra frequenza (es. 80-90% max_hr)").pack(anchor=tk.W, padx=10, pady=5)
        
        # Frame per la tabella e i pulsanti
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Tabella delle frequenze cardiache
        columns = ("name", "value")
        self.hr_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.hr_tree.heading("name", text="Nome")
        self.hr_tree.heading("value", text="Valore")
        self.hr_tree.column("name", width=150)
        self.hr_tree.column("value", width=250)
        self.hr_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar per la tabella
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.hr_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.hr_tree.configure(yscrollcommand=scrollbar.set)
        
        # Carica le frequenze cardiache esistenti
        for name, value in self.configuration.get("heart_rates", {}).items():
            self.hr_tree.insert("", "end", values=(name, value))
        
        # Pulsanti per gestire le frequenze cardiache
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="Aggiungi", command=self.add_hr).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Modifica", command=self.edit_hr).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Elimina", command=self.delete_hr).pack(side=tk.LEFT, padx=2)
        
        # Bind per l'editing con doppio click
        self.hr_tree.bind("<Double-1>", lambda e: self.edit_hr())
    
    def create_settings_tab(self, parent):
        """Crea la scheda per margini e altre impostazioni."""
        # Frame per i margini
        margins_frame = ttk.LabelFrame(parent, text="Margini")
        margins_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Margini per ritmi
        ttk.Label(margins_frame, text="Margine più veloce (mm:ss):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.faster_var = tk.StringVar(value=self.configuration.get("margins", {}).get("faster", "0:03"))
        ttk.Entry(margins_frame, textvariable=self.faster_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(margins_frame, text="Margine più lento (mm:ss):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.slower_var = tk.StringVar(value=self.configuration.get("margins", {}).get("slower", "0:03"))
        ttk.Entry(margins_frame, textvariable=self.slower_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        # Margini per frequenze cardiache
        ttk.Label(margins_frame, text="Margine FC superiore (%):").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.hr_up_var = tk.IntVar(value=self.configuration.get("margins", {}).get("hr_up", 5))
        ttk.Entry(margins_frame, textvariable=self.hr_up_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(margins_frame, text="Margine FC inferiore (%):").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.hr_down_var = tk.IntVar(value=self.configuration.get("margins", {}).get("hr_down", 5))
        ttk.Entry(margins_frame, textvariable=self.hr_down_var, width=10).grid(row=1, column=3, padx=5, pady=5)
        
        # Prefisso nome
        prefix_frame = ttk.LabelFrame(parent, text="Prefisso Nome")
        prefix_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(prefix_frame, text="Prefisso da aggiungere ai nomi degli allenamenti:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.name_prefix_var = tk.StringVar(value=self.configuration.get("name_prefix", ""))
        ttk.Entry(prefix_frame, textvariable=self.name_prefix_var, width=30).grid(row=0, column=1, padx=5, pady=5)
    
    def add_pace(self):
        """Aggiunge un nuovo ritmo."""
        # Chiedi nome e valore
        name = simpledialog.askstring("Nuovo Ritmo", "Nome del ritmo:")
        if not name:
            return
            
        value = simpledialog.askstring("Nuovo Ritmo", "Valore del ritmo (es. 4:30, 4:30-4:40, 10km in 45:00):")
        if not value:
            return
            
        # Aggiungi alla tabella
        self.paces_tree.insert("", "end", values=(name, value))
    
    def edit_pace(self):
        """Modifica un ritmo esistente."""
        # Ottieni il ritmo selezionato
        selection = self.paces_tree.selection()
        if not selection:
            messagebox.showerror("Errore", "Nessun ritmo selezionato")
            return
            
        # Ottieni nome e valore attuali
        item = self.paces_tree.item(selection[0])
        values = item['values']
        name = values[0]
        value = values[1]
        
        # Chiedi nuovo valore
        new_value = simpledialog.askstring("Modifica Ritmo", f"Nuovo valore per '{name}':", initialvalue=value)
        if not new_value:
            return
            
        # Aggiorna la tabella
        self.paces_tree.item(selection[0], values=(name, new_value))
    
    def delete_pace(self):
        """Elimina un ritmo."""
        # Ottieni il ritmo selezionato
        selection = self.paces_tree.selection()
        if not selection:
            messagebox.showerror("Errore", "Nessun ritmo selezionato")
            return
            
        # Ottieni il nome del ritmo
        item = self.paces_tree.item(selection[0])
        name = item['values'][0]
        
        # Chiedi conferma
        if not messagebox.askyesno("Elimina Ritmo", f"Sei sicuro di voler eliminare il ritmo '{name}'?"):
            return
            
        # Elimina dalla tabella
        self.paces_tree.delete(selection[0])
    
    def add_hr(self):
        """Aggiunge una nuova frequenza cardiaca."""
        # Chiedi nome e valore
        name = simpledialog.askstring("Nuova Frequenza Cardiaca", "Nome della frequenza cardiaca:")
        if not name:
            return
            
        value = simpledialog.askstring("Nuova Frequenza Cardiaca", "Valore della frequenza cardiaca (es. 150, 140-150, 80-90% max_hr):")
        if not value:
            return
            
        # Aggiungi alla tabella
        self.hr_tree.insert("", "end", values=(name, value))
    
    def edit_hr(self):
        """Modifica una frequenza cardiaca esistente."""
        # Ottieni la frequenza cardiaca selezionata
        selection = self.hr_tree.selection()
        if not selection:
            messagebox.showerror("Errore", "Nessuna frequenza cardiaca selezionata")
            return
            
        # Ottieni nome e valore attuali
        item = self.hr_tree.item(selection[0])
        values = item['values']
        name = values[0]
        value = values[1]
        
        # Chiedi nuovo valore
        new_value = simpledialog.askstring("Modifica Frequenza Cardiaca", f"Nuovo valore per '{name}':", initialvalue=value)
        if not new_value:
            return
            
        # Aggiorna la tabella
        self.hr_tree.item(selection[0], values=(name, new_value))
    
    def delete_hr(self):
        """Elimina una frequenza cardiaca."""
        # Ottieni la frequenza cardiaca selezionata
        selection = self.hr_tree.selection()
        if not selection:
            messagebox.showerror("Errore", "Nessuna frequenza cardiaca selezionata")
            return
            
        # Ottieni il nome della frequenza cardiaca
        item = self.hr_tree.item(selection[0])
        name = item['values'][0]
        
        # Chiedi conferma
        if not messagebox.askyesno("Elimina Frequenza Cardiaca", f"Sei sicuro di voler eliminare la frequenza cardiaca '{name}'?"):
            return
            
        # Elimina dalla tabella
        self.hr_tree.delete(selection[0])
    
    def confirm(self):
        """Conferma le modifiche e chiude la finestra."""
        # Aggiorna la configurazione con i valori delle tabelle
        self.configuration["paces"] = {}
        for item_id in self.paces_tree.get_children():
            values = self.paces_tree.item(item_id)['values']
            self.configuration["paces"][values[0]] = values[1]
        
        self.configuration["heart_rates"] = {}
        for item_id in self.hr_tree.get_children():
            values = self.hr_tree.item(item_id)['values']
            self.configuration["heart_rates"][values[0]] = values[1]
        
        # Aggiorna i margini
        self.configuration["margins"] = {
            "faster": self.faster_var.get(),
            "slower": self.slower_var.get(),
            "hr_up": self.hr_up_var.get(),
            "hr_down": self.hr_down_var.get()
        }
        
        # Aggiorna il prefisso nome
        self.configuration["name_prefix"] = self.name_prefix_var.get()
        
        # Imposta il risultato e chiude
        self.result = self.configuration
        self.destroy()
    
    def cancel(self):
        """Annulla le modifiche e chiude la finestra."""
        self.destroy()

class StepEditor(tk.Toplevel):
    """Finestra per la modifica di uno step."""
    def __init__(self, parent, config, step_type=None, step_value=None):
        super().__init__(parent)
        self.title("Editor Step")
        self.geometry("600x400")
        self.resizable(True, True)
        self.transient(parent)  # Rende la finestra modale
        self.grab_set()  # Impedisce di interagire con la finestra principale
        
        # Risultato
        self.result = None
        
        # Riferimento alla configurazione
        self.configuration = config
        
        # Frame principale
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Selezione del tipo di step
        ttk.Label(main_frame, text="Tipo di step:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.step_type_var = tk.StringVar(value=step_type or "interval")
        step_types = ["interval", "warmup", "cooldown", "recovery", "rest", "other", "repeat 2", "repeat 3", "repeat 4", "repeat 5", "repeat 6", "repeat 7", "repeat 8", "repeat 9", "repeat 10"]
        step_type_combo = ttk.Combobox(main_frame, textvariable=self.step_type_var, values=step_types, state="readonly")
        step_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        step_type_combo.bind("<<ComboboxSelected>>", self.on_step_type_changed)
        
        # Dati specifici per i vari tipi di step
        self.step_frame = ttk.LabelFrame(main_frame, text="Dettagli Step")
        self.step_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Variabili per i dettagli dello step
        self.duration_type_var = tk.StringVar(value="time")
        self.duration_value_var = tk.StringVar()
        self.target_type_var = tk.StringVar(value="no_target")
        self.target_value_var = tk.StringVar()
        self.description_var = tk.StringVar()
        
        # Inizializza con i valori esistenti
        if step_value:
            self.parse_step_value(step_value)
        
        # Crea i widget per i dettagli dello step
        self.create_step_details()
        
        # Pulsanti di conferma e annullamento
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Annulla", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="OK", command=self.confirm).pack(side=tk.RIGHT, padx=5)
    
    def on_step_type_changed(self, event):
        """Gestisce il cambio del tipo di step."""
        # Ricrea i dettagli dello step
        self.create_step_details()
    
    def parse_step_value(self, step_value):
        """Analizza il valore di uno step e imposta le variabili."""
        if not step_value:
            return
            
        # Converte in stringa
        step_str = str(step_value)
        
        # Cerca target di tipo pace o heartrate
        if " @ " in step_str:
            parts = step_str.split(" @ ")
            duration = parts[0]
            target = parts[1]
            self.target_type_var.set("pace")
            self.target_value_var.set(target)
            
            # Cerca descrizione
            if " -- " in target:
                target_parts = target.split(" -- ")
                self.target_value_var.set(target_parts[0])
                self.description_var.set(target_parts[1])
                
        elif " @hr " in step_str:
            parts = step_str.split(" @hr ")
            duration = parts[0]
            target = parts[1]
            self.target_type_var.set("hr")
            self.target_value_var.set(target)
            
            # Cerca descrizione
            if " -- " in target:
                target_parts = target.split(" -- ")
                self.target_value_var.set(target_parts[0])
                self.description_var.set(target_parts[1])
                
        elif " in " in step_str:
            parts = step_str.split(" in ")
            duration = parts[0]
            target = parts[1]
            self.target_type_var.set("time")
            self.target_value_var.set(target)
            
            # Cerca descrizione
            if " -- " in target:
                target_parts = target.split(" -- ")
                self.target_value_var.set(target_parts[0])
                self.description_var.set(target_parts[1])
                
        else:
            duration = step_str
            self.target_type_var.set("no_target")
            
            # Cerca descrizione
            if " -- " in duration:
                duration_parts = duration.split(" -- ")
                duration = duration_parts[0]
                self.description_var.set(duration_parts[1])
        
        # Determina il tipo di durata (tempo, distanza, lap button)
        if duration.endswith("min") or duration.endswith("s") or duration.endswith("h") or ":" in duration:
            self.duration_type_var.set("time")
        elif duration.endswith("km") or duration.endswith("m"):
            self.duration_type_var.set("distance")
        elif duration == "lap-button":
            self.duration_type_var.set("lap_button")
        
        # Imposta il valore della durata
        self.duration_value_var.set(duration)
    
    def create_step_details(self):
        """Crea i widget per i dettagli dello step."""
        # Pulisci il frame
        for widget in self.step_frame.winfo_children():
            widget.destroy()
        
        # Se è una ripetizione, non mostrare i dettagli
        if self.step_type_var.get().startswith("repeat"):
            ttk.Label(self.step_frame, text="Le ripetizioni non hanno dettagli aggiuntivi.").pack(padx=10, pady=10)
            ttk.Label(self.step_frame, text="Aggiungi gli step all'interno della ripetizione dopo averla creata.").pack(padx=10)
            return
        
        # Frame per la durata
        duration_frame = ttk.LabelFrame(self.step_frame, text="Durata/Distanza")
        duration_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Tipo di durata
        ttk.Label(duration_frame, text="Tipo:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        duration_types = [("Tempo", "time"), ("Distanza", "distance"), ("Pulsante Lap", "lap_button")]
        for i, (text, value) in enumerate(duration_types):
            ttk.Radiobutton(duration_frame, text=text, variable=self.duration_type_var, value=value, 
                           command=self.update_duration_widgets).grid(row=0, column=i+1, padx=5, pady=5)
        
        # Frame per i dettagli della durata
        self.duration_details_frame = ttk.Frame(duration_frame)
        self.duration_details_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Frame per il target
        target_frame = ttk.LabelFrame(self.step_frame, text="Target")
        target_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Tipo di target
        ttk.Label(target_frame, text="Tipo di Target:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        target_types = [("Nessun Target", "no_target"), ("Ritmo", "pace"), ("Frequenza Cardiaca", "hr"), ("Tempo", "time")]
        for i, (text, value) in enumerate(target_types):
            ttk.Radiobutton(target_frame, text=text, variable=self.target_type_var, value=value, 
                           command=self.update_target_widgets).grid(row=0, column=i+1, padx=5, pady=5)
        
        # Frame per i dettagli del target
        self.target_details_frame = ttk.Frame(target_frame)
        self.target_details_frame.grid(row=1, column=0, columnspan=5, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Descrizione
        description_frame = ttk.LabelFrame(self.step_frame, text="Descrizione")
        description_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Entry(description_frame, textvariable=self.description_var, width=50).pack(fill=tk.X, padx=5, pady=5, expand=True)
        
        # Inizializza i widget della durata e del target
        self.update_duration_widgets()
        self.update_target_widgets()
    
    def update_duration_widgets(self):
        """Aggiorna i widget della durata in base al tipo selezionato."""
        # Pulisci il frame
        for widget in self.duration_details_frame.winfo_children():
            widget.destroy()
        
        # Se è lap button, non mostrare altri widget
        if self.duration_type_var.get() == "lap_button":
            self.duration_value_var.set("lap-button")
            return
        
        # Se è tempo, mostra le opzioni per il tempo
        if self.duration_type_var.get() == "time":
            ttk.Label(self.duration_details_frame, text="Durata:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            ttk.Entry(self.duration_details_frame, textvariable=self.duration_value_var, width=15).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            ttk.Label(self.duration_details_frame, text="(es. 30min, 1h, 45s, 1:30)").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        # Se è distanza, mostra le opzioni per la distanza
        elif self.duration_type_var.get() == "distance":
            ttk.Label(self.duration_details_frame, text="Distanza:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            ttk.Entry(self.duration_details_frame, textvariable=self.duration_value_var, width=15).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            ttk.Label(self.duration_details_frame, text="(es. 5km, 800m)").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
    
    
    def update_target_widgets(self):
        """Aggiorna i widget del target in base al tipo selezionato."""
        # Pulisci il frame
        for widget in self.target_details_frame.winfo_children():
            widget.destroy()
        
        # Se è nessun target, non mostrare altri widget
        if self.target_type_var.get() == "no_target":
            self.target_value_var.set("")
            return
        
        # Se è ritmo, mostra le opzioni per il ritmo
        if self.target_type_var.get() == "pace":
            ttk.Label(self.target_details_frame, text="Ritmo:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            
            # Combobox con i ritmi predefiniti
            pace_values = [""] + list(self.configuration.get("paces", {}).keys())
            pace_combo = ttk.Combobox(self.target_details_frame, values=pace_values, width=15)
            pace_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            pace_combo.bind("<<ComboboxSelected>>", lambda e: self.target_value_var.set(pace_combo.get()))
            
            # Entry per inserimento manuale
            ttk.Label(self.target_details_frame, text="o inserisci:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
            ttk.Entry(self.target_details_frame, textvariable=self.target_value_var, width=15).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
            ttk.Label(self.target_details_frame, text="(es. 4:30, 4:30-4:40, 80% marathon)").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        
        # Se è frequenza cardiaca, mostra le opzioni per la frequenza cardiaca
        elif self.target_type_var.get() == "hr":
            ttk.Label(self.target_details_frame, text="Frequenza Cardiaca:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            
            # Combobox con le frequenze cardiache predefinite
            hr_values = [""] + list(self.configuration.get("heart_rates", {}).keys())
            hr_combo = ttk.Combobox(self.target_details_frame, values=hr_values, width=15)
            hr_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            hr_combo.bind("<<ComboboxSelected>>", lambda e: self.target_value_var.set(hr_combo.get()))
            
            # Entry per inserimento manuale
            ttk.Label(self.target_details_frame, text="o inserisci:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
            ttk.Entry(self.target_details_frame, textvariable=self.target_value_var, width=15).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
            ttk.Label(self.target_details_frame, text="(es. 150, 140-150, zone_2)").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        
        # Se è tempo, mostra le opzioni per il tempo
        elif self.target_type_var.get() == "time":
            ttk.Label(self.target_details_frame, text="Tempo:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            ttk.Entry(self.target_details_frame, textvariable=self.target_value_var, width=15).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            ttk.Label(self.target_details_frame, text="(es. 4:30, 45:00)").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
    
    def build_step_value(self):
        """Costruisce il valore dello step in base alle selezioni dell'utente."""
        # Se è una ripetizione, ritorna None (il valore sarà gestito esternamente)
        if self.step_type_var.get().startswith("repeat"):
            return None
        
        # Costruisci la stringa del valore
        value = self.duration_value_var.get()
        
        # Aggiungi il target se presente
        if self.target_type_var.get() == "pace" and self.target_value_var.get():
            value += f" @ {self.target_value_var.get()}"
        elif self.target_type_var.get() == "hr" and self.target_value_var.get():
            value += f" @hr {self.target_value_var.get()}"
        elif self.target_type_var.get() == "time" and self.target_value_var.get():
            value += f" in {self.target_value_var.get()}"
        
        # Aggiungi la descrizione se presente
        if self.description_var.get():
            value += f" -- {self.description_var.get()}"
        
        return value
    
    def confirm(self):
        """Conferma le modifiche e chiude la finestra."""
        # Ottieni il tipo di step
        step_type = self.step_type_var.get()
        
        # Costruisci il valore dello step
        step_value = self.build_step_value()
        
        # Imposta il risultato e chiude
        self.result = (step_type, step_value)
        self.destroy()
    
    def cancel(self):
        """Annulla le modifiche e chiude la finestra."""
        self.destroy()
