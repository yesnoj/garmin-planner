#!/usr/bin/env python
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import os
import yaml
import re
import copy
from functools import partial
from planner.license_manager import LicenseManager

# Colori moderni (ispirati a Garmin Connect)
COLORS = {
    "bg_main": "#f5f5f5",
    "bg_header": "#333333",
    "bg_light": "#ffffff",
    "accent": "#0076c0",  # Blu Garmin
    "accent_dark": "#005486",
    "text_light": "#ffffff",
    "text_dark": "#333333",
    "warmup": "#52b69a",   # Verde acqua 
    "interval": "#e07a5f", # Arancione 
    "recovery": "#81b29a", # Verde chiaro
    "cooldown": "#3d5a80", # Blu scuro
    "rest": "#98c1d9",     # Azzurro
    "repeat": "#5e548e",   # Viola
    "other": "#bdbdbd"     # Grigio
}

# Icone per i diversi tipi di passi (emoji Unicode)
STEP_ICONS = {
    "warmup": "🔥",     # Fiamma per riscaldamento
    "interval": "⚡",   # Fulmine per intervallo
    "recovery": "🌊",   # Onda per recupero
    "cooldown": "❄️",   # Fiocco di neve per defaticamento
    "rest": "⏸️",       # Pausa per riposo
    "repeat": "🔄",     # Frecce circolari per ripetizione
    "other": "📝"       # Note per altro
}

workout_config = {
    'paces': {},
    'heart_rates': {},
    'margins': {
        'faster': '0:03',
        'slower': '0:03',
        'hr_up': 5,
        'hr_down': 5
    },
    'name_prefix': ''
}

class StepDialog(tk.Toplevel):
    """Dialog for adding/editing a workout step"""
    
    def __init__(self, parent, step_type=None, step_detail=None):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        
        self.title("Dettagli del passo")
        self.geometry("500x300")
        self.configure(bg=COLORS["bg_light"])
        
        # Rendi la finestra modale
        self.transient(parent)
        self.grab_set()
        
        # Tipo di passo
        type_frame = ttk.Frame(self)
        type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(type_frame, text="Tipo di passo:").grid(row=0, column=0, padx=5, pady=5)
        
        step_types = ["warmup", "interval", "recovery", "cooldown", "rest", "other"]
        self.step_type = tk.StringVar(value=step_type if step_type else "interval")
        
        # Usa un combobox invece di dropdown
        step_type_combo = ttk.Combobox(type_frame, textvariable=self.step_type, values=step_types, state="readonly", width=15)
        step_type_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Quando cambia il tipo, aggiorna l'interfaccia
        step_type_combo.bind('<<ComboboxSelected>>', self.on_type_change)
        
        # Dettaglio del passo
        detail_frame = ttk.LabelFrame(self, text="Definisci il passo")
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Per la durata/distanza
        measure_frame = ttk.Frame(detail_frame)
        measure_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(measure_frame, text="Durata/Distanza:").grid(row=0, column=0, padx=5, pady=5)
        self.measure_var = tk.StringVar()
        self.measure_entry = ttk.Entry(measure_frame, textvariable=self.measure_var, width=10)
        self.measure_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Dropdown per unità (min, km, m)
        self.unit_var = tk.StringVar(value="min")
        self.unit_combo = ttk.Combobox(measure_frame, textvariable=self.unit_var, values=["min", "km", "m", "lap-button"], width=10, state="readonly")
        self.unit_combo.grid(row=0, column=2, padx=5, pady=5)
        self.unit_combo.bind('<<ComboboxSelected>>', self.on_unit_change)
        
        # Per la zona (ritmo o FC)
        zone_frame = ttk.Frame(detail_frame)
        zone_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.zone_type = tk.StringVar(value="pace")
        ttk.Radiobutton(zone_frame, text="Ritmo", variable=self.zone_type, value="pace", 
                        command=self.update_zone_options).grid(row=0, column=0, padx=5, pady=5)
        ttk.Radiobutton(zone_frame, text="Frequenza Cardiaca", variable=self.zone_type, value="hr", 
                        command=self.update_zone_options).grid(row=0, column=1, padx=5, pady=5)
        ttk.Radiobutton(zone_frame, text="Nessuna", variable=self.zone_type, value="none", 
                        command=self.update_zone_options).grid(row=0, column=2, padx=5, pady=5)
        
        # Frame per le opzioni della zona
        self.zone_options_frame = ttk.Frame(detail_frame)
        self.zone_options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Lista vuota per i valori di zona
        self.zone_var = tk.StringVar()
        self.zone_combo = ttk.Combobox(self.zone_options_frame, textvariable=self.zone_var, width=15)
        self.zone_combo.pack(side=tk.LEFT, padx=5)
        
        # Aggiornamento delle opzioni di zona
        self.update_zone_options()
        
        # Descrizione (opzionale)
        desc_frame = ttk.LabelFrame(detail_frame, text="Descrizione (opzionale)")
        desc_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.description_var = tk.StringVar()
        ttk.Entry(desc_frame, textvariable=self.description_var, width=50).pack(fill=tk.X, padx=5, pady=5)
        
        # Bottoni
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annulla", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Se abbiamo dei dettagli, popola i campi
        if step_detail:
            self.populate_from_detail(step_detail)
            
        # Centra la finestra sullo schermo
        self.center_window()
        
        # Attendi che la finestra sia chiusa
        self.wait_window()
    
    def center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def on_type_change(self, event):
        """Handle step type change"""
        # Adatta l'interfaccia in base al tipo selezionato
        step_type = self.step_type.get()
        
        # Aggiorna le unità di default
        if step_type in ["warmup", "cooldown", "recovery"]:
            self.unit_var.set("min")
        elif step_type == "interval":
            self.unit_var.set("m")
        elif step_type == "rest":
            # Per i passi di riposo, mostra anche lap-button come opzione
            self.unit_var.set("min")
        
    def on_unit_change(self, event):
        """Handle unit change"""
        if self.unit_var.get() == "lap-button":
            # Disabilita il campo misura
            self.measure_var.set("")
            self.measure_entry.configure(state="disabled")
            # Imposta zona a none
            self.zone_type.set("none")
            self.update_zone_options()
        else:
            # Riabilita il campo misura
            self.measure_entry.configure(state="normal")
    
    def update_zone_options(self):
        """Update zone options based on the selected zone type"""
        zone_type = self.zone_type.get()
        
        # Pulisci le opzioni correnti
        for widget in self.zone_options_frame.winfo_children():
            widget.destroy()
        
        if zone_type == "pace":
            # Carica le opzioni per il ritmo dal config globale
            pace_zones = list(workout_config.get('paces', {}).keys())
            
            # Se non ci sono zone definite, usa le predefinite
            if not pace_zones:
                pace_zones = ["Z1", "Z2", "Z3", "Z4", "Z5", "6:00", "5:30", "5:00", "4:30", "4:00"]
            
            self.zone_var = tk.StringVar()
            self.zone_combo = ttk.Combobox(self.zone_options_frame, textvariable=self.zone_var, values=pace_zones, width=15)
            self.zone_combo.pack(side=tk.LEFT, padx=5)
            
            # Aggiungi simbolo @
            ttk.Label(self.zone_options_frame, text="@").pack(side=tk.LEFT)
            
            # Il primo valore come default
            if pace_zones:
                self.zone_var.set(pace_zones[0])
                
        elif zone_type == "hr":
            # Carica le opzioni per la frequenza cardiaca dal config globale
            hr_zones = list(workout_config.get('heart_rates', {}).keys())
            
            # Se non ci sono zone definite, usa le predefinite
            if not hr_zones:
                hr_zones = ["Z1", "Z2", "Z3", "Z4", "Z5", "120-130", "130-140", "140-150", "150-160", "160-170"]
            
            self.zone_var = tk.StringVar()
            self.zone_combo = ttk.Combobox(self.zone_options_frame, textvariable=self.zone_var, values=hr_zones, width=15)
            self.zone_combo.pack(side=tk.LEFT, padx=5)
            
            # Aggiungi simbolo @hr
            ttk.Label(self.zone_options_frame, text="@hr").pack(side=tk.LEFT)
            
            # Il primo valore come default
            if hr_zones:
                self.zone_var.set(hr_zones[0])
        
        else:  # none - nessuna zona
            # Non mostrare opzioni di zona
            pass
            
        # Gestione speciale per lap-button
        if self.unit_var.get() == "lap-button":
            # Disabilita il campo misura
            self.measure_var.set("")
            self.measure_entry.configure(state="disabled")
    
    def populate_from_detail(self, detail):
        """Populate fields from step detail"""
        # Handle case where detail is a list (old format)
        if isinstance(detail, list):
            self.measure_var.set("1")  # Default value
            self.unit_var.set("min")   # Default unit
            self.zone_type.set("pace") # Default zone type
            self.zone_var.set("Z2")    # Default zone
            return
        
        # Caso speciale per lap-button
        if detail == "lap-button" or detail.startswith("lap-button"):
            self.unit_var.set("lap-button")
            self.measure_var.set("")
            self.measure_entry.configure(state="disabled")
            self.zone_type.set("none")
            
            # Estrai eventuale descrizione
            if " -- " in detail:
                _, description = detail.split(" -- ", 1)
                self.description_var.set(description.strip())
            
            self.update_zone_options()
            return
        
        # Esempio: "10min @ Z1 -- Riscaldamento iniziale"
        
        # Cerca la descrizione
        if " -- " in detail:
            parts = detail.split(" -- ")
            main_part = parts[0].strip()
            description = parts[1].strip()
            self.description_var.set(description)
        else:
            main_part = detail.strip()
        
        # Cerca la misura e la zona
        if " @ " in main_part:
            measure, zone = main_part.split(" @ ", 1)
            
            # Identifica se è HR o pace
            if "@hr" in detail:
                self.zone_type.set("hr")
                zone = zone.replace("hr ", "")
            else:
                self.zone_type.set("pace")
            
            self.zone_var.set(zone.strip())
            
            # Estrai la misura e l'unità
            measure = measure.strip()
            if "min" in measure:
                value = measure.replace("min", "").strip()
                self.measure_var.set(value)
                self.unit_var.set("min")
            elif "km" in measure:
                value = measure.replace("km", "").strip()
                self.measure_var.set(value)
                self.unit_var.set("km")
            elif "m" in measure:
                value = measure.replace("m", "").strip()
                self.measure_var.set(value)
                self.unit_var.set("m")
            else:
                self.measure_var.set(measure)
        else:
            # Nessuna zona specificata
            self.zone_type.set("none")
            
            # Estrai solo la misura e l'unità
            measure = main_part.strip()
            if "min" in measure:
                value = measure.replace("min", "").strip()
                self.measure_var.set(value)
                self.unit_var.set("min")
            elif "km" in measure:
                value = measure.replace("km", "").strip()
                self.measure_var.set(value)
                self.unit_var.set("km")
            elif "m" in measure:
                value = measure.replace("m", "").strip()
                self.measure_var.set(value)
                self.unit_var.set("m")
            else:
                self.measure_var.set(measure)
        
        # Aggiorna la UI
        self.update_zone_options()
    
    def on_ok(self):
        """Handle OK button click"""
        # Caso speciale per lap-button
        if self.unit_var.get() == "lap-button":
            detail = "lap-button"
            
            # Aggiungi la descrizione se presente
            if self.description_var.get():
                detail += f" -- {self.description_var.get()}"
                
            # Imposta il risultato
            self.result = (self.step_type.get(), detail)
            self.destroy()
            return
        
        # Valida i dati
        if not self.measure_var.get():
            messagebox.showerror("Errore", "Inserisci una durata o distanza", parent=self)
            return
        
        try:
            # Verifica che la misura sia un numero
            float(self.measure_var.get())
        except ValueError:
            messagebox.showerror("Errore", "La durata o distanza deve essere un numero", parent=self)
            return
        
        # Costruisci il dettaglio del passo
        measure = f"{self.measure_var.get()}{self.unit_var.get()}"
        
        if self.zone_type.get() == "hr":
            zone = f"@hr {self.zone_var.get()}"
            detail = f"{measure} {zone}"
        elif self.zone_type.get() == "pace":
            zone = f"@ {self.zone_var.get()}"
            detail = f"{measure} {zone}"
        else:
            # No zone
            detail = measure
        
        # Aggiungi la descrizione se presente
        if self.description_var.get():
            detail += f" -- {self.description_var.get()}"
        
        # Imposta il risultato
        self.result = (self.step_type.get(), detail)
        
        # Chiudi la finestra
        self.destroy()
    
    def on_cancel(self):
        """Handle Cancel button click"""
        self.destroy()


class ConfigEditorDialog(tk.Toplevel):
    """Dialog for editing paces, heart rates, and other configuration options"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        self.title("Configurazione Allenamenti")
        self.geometry("800x600")
        self.configure(bg=COLORS["bg_light"])
        
        # Rendi la finestra modale
        self.transient(parent)
        self.grab_set()
        
        # Crea il notebook per le schede
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scheda per i ritmi (paces)
        self.paces_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.paces_frame, text="Ritmi")
        
        # Scheda per le frequenze cardiache (heart rates)
        self.hr_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.hr_frame, text="Frequenze Cardiache")
        
        # Scheda per i margini
        self.margins_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.margins_frame, text="Margini")
        
        # Inizializza le schede
        self.init_paces_tab()
        self.init_hr_tab()
        self.init_margins_tab()
        
        # Bottoni
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Annulla", command=self.on_cancel).pack(side=tk.RIGHT, padx=5)
        
        # Centra la finestra
        self.center_window()
        
        # Carica i dati
        self.load_data()
        
        # Attendi la chiusura della finestra
        self.wait_window()
    
    def center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def init_paces_tab(self):
        """Initialize the paces tab"""
        # Frame per la lista
        list_frame = ttk.Frame(self.paces_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Crea la treeview
        self.paces_tree = ttk.Treeview(list_frame, columns=("name", "value"), show="headings")
        self.paces_tree.heading("name", text="Nome")
        self.paces_tree.heading("value", text="Valore")
        self.paces_tree.column("name", width=150)
        self.paces_tree.column("value", width=250)
        
        # Aggiungi scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.paces_tree.yview)
        self.paces_tree.configure(yscrollcommand=scrollbar.set)
        
        # Packing
        self.paces_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottoni
        button_frame = ttk.Frame(self.paces_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Aggiungi", command=lambda: self.add_item('paces')).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Modifica", command=lambda: self.edit_item('paces')).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Elimina", command=lambda: self.delete_item('paces')).pack(side=tk.LEFT, padx=5)
        
        # Double-click to edit
        self.paces_tree.bind("<Double-1>", lambda e: self.edit_item('paces'))
    
    def init_hr_tab(self):
        """Initialize the heart rates tab"""
        # Frame per la lista
        list_frame = ttk.Frame(self.hr_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Crea la treeview
        self.hr_tree = ttk.Treeview(list_frame, columns=("name", "value"), show="headings")
        self.hr_tree.heading("name", text="Nome")
        self.hr_tree.heading("value", text="Valore")
        self.hr_tree.column("name", width=150)
        self.hr_tree.column("value", width=250)
        
        # Aggiungi scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.hr_tree.yview)
        self.hr_tree.configure(yscrollcommand=scrollbar.set)
        
        # Packing
        self.hr_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottoni
        button_frame = ttk.Frame(self.hr_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Aggiungi", command=lambda: self.add_item('heart_rates')).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Modifica", command=lambda: self.edit_item('heart_rates')).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Elimina", command=lambda: self.delete_item('heart_rates')).pack(side=tk.LEFT, padx=5)
        
        # Double-click to edit
        self.hr_tree.bind("<Double-1>", lambda e: self.edit_item('heart_rates'))
    
    def init_margins_tab(self):
        """Initialize the margins tab"""
        # Grid per i campi
        grid_frame = ttk.Frame(self.margins_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Faster margin
        ttk.Label(grid_frame, text="Ritmo più veloce (mm:ss):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.faster_var = tk.StringVar()
        ttk.Entry(grid_frame, textvariable=self.faster_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Slower margin
        ttk.Label(grid_frame, text="Ritmo più lento (mm:ss):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.slower_var = tk.StringVar()
        ttk.Entry(grid_frame, textvariable=self.slower_var, width=10).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # HR up margin
        ttk.Label(grid_frame, text="FC sopra target (%):").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.hr_up_var = tk.IntVar()
        ttk.Entry(grid_frame, textvariable=self.hr_up_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # HR down margin
        ttk.Label(grid_frame, text="FC sotto target (%):").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.hr_down_var = tk.IntVar()
        ttk.Entry(grid_frame, textvariable=self.hr_down_var, width=10).grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Name prefix
        ttk.Label(grid_frame, text="Prefisso nome:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.name_prefix_var = tk.StringVar()
        ttk.Entry(grid_frame, textvariable=self.name_prefix_var, width=40).grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Help text
        help_text = ("Queste impostazioni controllano i margini di tolleranza per ritmi e frequenze cardiache.\n"
                     "Ad esempio, un margine di '0:03' permette di correre fino a 3 secondi più veloce o più lento\n"
                     "rispetto al ritmo target. Similarmente, una tolleranza del 5% permette che la frequenza cardiaca\n"
                     "vari del 5% sopra o sotto il target impostato.")
        
        ttk.Label(grid_frame, text=help_text, wraplength=600, justify=tk.LEFT).grid(row=3, column=0, columnspan=4, padx=5, pady=15, sticky=tk.W)
    
    def load_data(self):
        """Load configuration data"""
        global workout_config
        
        # Load paces
        for name, value in workout_config.get('paces', {}).items():
            self.paces_tree.insert("", "end", values=(name, value))
        
        # Load heart rates
        for name, value in workout_config.get('heart_rates', {}).items():
            self.hr_tree.insert("", "end", values=(name, value))
        
        # Load margins
        margins = workout_config.get('margins', {})
        self.faster_var.set(margins.get('faster', '0:03'))
        self.slower_var.set(margins.get('slower', '0:03'))
        self.hr_up_var.set(margins.get('hr_up', 5))
        self.hr_down_var.set(margins.get('hr_down', 5))
        
        # Load name prefix
        self.name_prefix_var.set(workout_config.get('name_prefix', ''))
    
    def add_item(self, item_type):
        """Add a new pace or heart rate"""
        dialog = ConfigItemDialog(self, "Aggiungi " + ("Ritmo" if item_type == 'paces' else "Frequenza Cardiaca"))
        
        if dialog.result:
            name, value = dialog.result
            
            # Add to treeview
            tree = self.paces_tree if item_type == 'paces' else self.hr_tree
            tree.insert("", "end", values=(name, value))
    
    def edit_item(self, item_type):
        """Edit a pace or heart rate"""
        # Get the selected item
        tree = self.paces_tree if item_type == 'paces' else self.hr_tree
        selection = tree.selection()
        
        if not selection:
            messagebox.showwarning("Nessuna selezione", f"Seleziona un {'ritmo' if item_type == 'paces' else 'frequenza cardiaca'} da modificare", parent=self)
            return
        
        # Get the values
        item_values = tree.item(selection[0], "values")
        name, value = item_values
        
        # Open dialog
        title = "Modifica " + ("Ritmo" if item_type == 'paces' else "Frequenza Cardiaca")
        dialog = ConfigItemDialog(self, title, name, value)
        
        if dialog.result:
            new_name, new_value = dialog.result
            
            # Update treeview
            tree.item(selection[0], values=(new_name, new_value))
    
    def delete_item(self, item_type):
        """Delete a pace or heart rate"""
        # Get the selected item
        tree = self.paces_tree if item_type == 'paces' else self.hr_tree
        selection = tree.selection()
        
        if not selection:
            messagebox.showwarning("Nessuna selezione", f"Seleziona un {'ritmo' if item_type == 'paces' else 'frequenza cardiaca'} da eliminare", parent=self)
            return
        
        # Get the name
        item_values = tree.item(selection[0], "values")
        name = item_values[0]
        
        # Confirm
        if not messagebox.askyesno("Conferma", f"Sei sicuro di voler eliminare {name}?", parent=self):
            return
        
        # Delete from treeview
        tree.delete(selection[0])
    
    def save_data(self):
        """Save configuration data"""
        global workout_config
        
        # Create new dictionaries
        paces = {}
        heart_rates = {}
        
        # Get paces from treeview
        for item_id in self.paces_tree.get_children():
            name, value = self.paces_tree.item(item_id, "values")
            paces[name] = value
        
        # Get heart rates from treeview
        for item_id in self.hr_tree.get_children():
            name, value = self.hr_tree.item(item_id, "values")
            heart_rates[name] = value
        
        # Get margins
        margins = {
            'faster': self.faster_var.get(),
            'slower': self.slower_var.get(),
            'hr_up': self.hr_up_var.get(),
            'hr_down': self.hr_down_var.get()
        }
        
        # Get name prefix
        name_prefix = self.name_prefix_var.get()
        
        # Update config
        workout_config['paces'] = paces
        workout_config['heart_rates'] = heart_rates
        workout_config['margins'] = margins
        workout_config['name_prefix'] = name_prefix
        
        return True
    
    def on_ok(self):
        """Handle OK button click"""
        if self.save_data():
            self.destroy()
    
    def on_cancel(self):
        """Handle Cancel button click"""
        self.destroy()



class ConfigItemDialog(tk.Toplevel):
    """Dialog for adding or editing a configuration item (pace or heart rate)"""
    
    def __init__(self, parent, title, name="", value=""):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        
        self.title(title)
        self.geometry("450x250")
        self.configure(bg=COLORS["bg_light"])
        
        # Rendi la finestra modale
        self.transient(parent)
        self.grab_set()
        
        # Nome
        name_frame = ttk.Frame(self)
        name_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(name_frame, text="Nome:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.name_var = tk.StringVar(value=name)
        ttk.Entry(name_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Valore
        value_frame = ttk.Frame(self)
        value_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(value_frame, text="Valore:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.value_var = tk.StringVar(value=value)
        ttk.Entry(value_frame, textvariable=self.value_var, width=30).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Descrizione
        desc_frame = ttk.Frame(self)
        desc_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Testo di aiuto
        help_text = """
        Esempi di formati validi:
        
        Per ritmi (paces):
        - '5:30-5:10' (intervallo di ritmo)
        - '10km in 45:00' (distanza in tempo)
        - '80-85% marathon' (percentuale di un altro ritmo)
        
        Per frequenze cardiache (heart rates):
        - '150-160' (intervallo di battiti)
        - '70-76% max_hr' (percentuale di FC massima)
        - '160' (valore singolo)
        """
        
        ttk.Label(desc_frame, text=help_text, wraplength=400, justify=tk.LEFT).pack(padx=5, pady=5, fill=tk.X)
        
        # Bottoni
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annulla", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Centra la finestra
        self.center_window()
        
        # Attendi la chiusura della finestra
        self.wait_window()
    
    def center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def on_ok(self):
        """Handle OK button click"""
        name = self.name_var.get().strip()
        value = self.value_var.get().strip()
        
        if not name:
            messagebox.showerror("Errore", "Il nome non può essere vuoto", parent=self)
            return
        
        if not value:
            messagebox.showerror("Errore", "Il valore non può essere vuoto", parent=self)
            return
        
        self.result = (name, value)
        self.destroy()
    
    def on_cancel(self):
        """Handle Cancel button click"""
        self.destroy()


class RepeatDialog(tk.Toplevel):
    """Dialog for adding/editing a repeat section"""
    
    def __init__(self, parent, iterations=None, steps=None):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        
        self.title("Definisci ripetizione")
        self.geometry("700x500")
        self.configure(bg=COLORS["bg_light"])
        
        # Rendi la finestra modale
        self.transient(parent)
        self.grab_set()
        
        # Numero di ripetizioni
        repeat_frame = ttk.Frame(self)
        repeat_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(repeat_frame, text="Numero di ripetizioni:").grid(row=0, column=0, padx=5, pady=5)
        
        self.iterations_var = tk.StringVar(value=str(iterations) if iterations else "")
        iterations_entry = ttk.Entry(repeat_frame, textvariable=self.iterations_var, width=5)
        iterations_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Lista dei passi da ripetere
        steps_frame = ttk.LabelFrame(self, text="Passi da ripetere")
        steps_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Crea la Treeview per la lista dei passi
        self.steps_tree = ttk.Treeview(steps_frame, columns=("type", "details"), show="headings")
        self.steps_tree.heading("type", text="Tipo")
        self.steps_tree.heading("details", text="Dettagli")
        self.steps_tree.column("type", width=100)
        self.steps_tree.column("details", width=400)
        
        # Aggiungi una scrollbar
        scrollbar = ttk.Scrollbar(steps_frame, orient=tk.VERTICAL, command=self.steps_tree.yview)
        self.steps_tree.configure(yscrollcommand=scrollbar.set)
        
        # Packing
        self.steps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottoni per aggiungere/modificare/rimuovere passi
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(buttons_frame, text="Aggiungi passo", command=self.add_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Modifica passo", command=self.edit_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Rimuovi passo", command=self.remove_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Sposta su", command=self.move_step_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Sposta giù", command=self.move_step_down).pack(side=tk.LEFT, padx=5)
        
        # OK/Cancel buttons
        ok_cancel_frame = ttk.Frame(self)
        ok_cancel_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(ok_cancel_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(ok_cancel_frame, text="Annulla", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Inizializza la lista dei passi
        self.repeat_steps = steps if steps else []
        self.load_steps()
        
        # Centra la finestra
        self.center_window()
        
        # Attendi la chiusura della finestra
        self.wait_window()
    
    def add_step(self):
        """Add a new step to the repeat"""
        dialog = StepDialog(self)
        
        if dialog.result:
            step_type, step_detail = dialog.result
            self.repeat_steps.append({step_type: step_detail})
            self.load_steps()


    def center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def load_steps(self):
        """Load steps into the treeview"""
        # Clear existing items
        for item in self.steps_tree.get_children():
            self.steps_tree.delete(item)
        
        # Add steps to the tree
        for step in self.repeat_steps:
            if isinstance(step, dict):
                step_type = list(step.keys())[0]
                step_detail = step[step_type]
                
                # Handle case where step_detail is a list (old format)
                if isinstance(step_detail, list):
                    self.steps_tree.insert("", "end", values=(step_type, f"[Formato vecchio - {len(step_detail)} passi]"))
                else:
                    self.steps_tree.insert("", "end", values=(step_type, step_detail))
    

    def on_ok(self):
        """Handle OK button click"""
        # Validate data
        if not self.iterations_var.get():
            messagebox.showerror("Errore", "Inserisci il numero di ripetizioni", parent=self)
            return
        
        try:
            iterations = int(self.iterations_var.get())
            if iterations <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Errore", "Il numero di ripetizioni deve essere un intero positivo", parent=self)
            return
        
        if not self.repeat_steps:
            messagebox.showerror("Errore", "Aggiungi almeno un passo alla ripetizione", parent=self)
            return
        
        # Set the result
        self.result = (iterations, self.repeat_steps)
        
        # Close the dialog
        self.destroy()
    
    def on_cancel(self):
        """Handle Cancel button click"""
        self.destroy()


    def edit_step(self):
        """Edit the selected step"""
        selection = self.steps_tree.selection()
        
        if not selection:
            messagebox.showwarning("Nessuna selezione", "Seleziona un passo da modificare", parent=self)
            return
        
        # Get the selected step
        index = self.steps_tree.index(selection[0])
        step = self.repeat_steps[index]
        
        # Get step type and detail
        step_type = list(step.keys())[0]
        step_detail = step[step_type]
        
        # Open the step dialog
        dialog = StepDialog(self, step_type, step_detail)
        
        if dialog.result:
            new_type, new_detail = dialog.result
            self.repeat_steps[index] = {new_type: new_detail}
            self.load_steps()

    def remove_step(self):
        """Remove the selected step"""
        selection = self.steps_tree.selection()
        
        if not selection:
            messagebox.showwarning("Nessuna selezione", "Seleziona un passo da rimuovere", parent=self)
            return
        
        # Get the selected step
        index = self.steps_tree.index(selection[0])
        
        # Remove the step
        self.repeat_steps.pop(index)
        self.load_steps()

    def move_step_up(self):
        """Move the selected step up"""
        selection = self.steps_tree.selection()
        
        if not selection:
            return
        
        # Get the selected step
        index = self.steps_tree.index(selection[0])
        
        # Can't move up if already at the top
        if index == 0:
            return
        
        # Swap with the step above
        self.repeat_steps[index], self.repeat_steps[index - 1] = self.repeat_steps[index - 1], self.repeat_steps[index]
        self.load_steps()
        
        # Re-select the step
        self.steps_tree.selection_set(self.steps_tree.get_children()[index - 1])

    def move_step_down(self):
        """Move the selected step down"""
        selection = self.steps_tree.selection()
        
        if not selection:
            return
        
        # Get the selected step
        index = self.steps_tree.index(selection[0])
        
        # Can't move down if already at the bottom
        if index >= len(self.repeat_steps) - 1:
            return
        
        # Swap with the step below
        self.repeat_steps[index], self.repeat_steps[index + 1] = self.repeat_steps[index + 1], self.repeat_steps[index]
        self.load_steps()
        
        # Re-select the step
        self.steps_tree.selection_set(self.steps_tree.get_children()[index + 1])

class WorkoutEditor(tk.Toplevel):
    """Main workout editor window"""
    
    def __init__(self, parent, workout_name=None, workout_steps=None):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        
        self.title("Editor Allenamento")
        self.geometry("800x700")
        self.configure(bg=COLORS["bg_main"])
        
        # Stato dell'editor
        self.workout_name = workout_name if workout_name else "Nuovo allenamento"
        self.workout_steps = workout_steps if workout_steps else []
        
        # Inizializza l'interfaccia
        self.init_ui()
        
        # Carica passi se disponibili
        self.load_steps()
        
        # Centra la finestra
        self.center_window()
        
        # Rendi la finestra principale
        self.wait_window()
    
    def center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def init_ui(self):
        """Initialize the user interface"""
        name_frame = ttk.Frame(self)
        name_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(name_frame, text="Nome allenamento:").grid(row=0, column=0, padx=5, pady=5)

        self.name_var = tk.StringVar(value=self.workout_name)
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var, width=40)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        # Aggiungiamo un suggerimento sulla formattazione
        format_label = ttk.Label(name_frame, text="(Formato consigliato: W01S01 Descrizione)", 
                               font=("Arial", 9), foreground="gray")
        format_label.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        # Aggiungiamo anche una funzione di placeholder per il campo nome
        if self.workout_name == "Nuovo allenamento":
            def on_entry_click(event):
                """Clear placeholder text when entry is clicked"""
                if self.name_var.get() == "Nuovo allenamento":
                    self.name_var.set("W01S01 ")
                    name_entry.icursor(6)  # Posiziona il cursore dopo "W01S01 "
            
            name_entry.bind("<FocusIn>", on_entry_click)
        
        self.name_var = tk.StringVar(value=self.workout_name)
        ttk.Entry(name_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        
        # Canvas per visualizzare graficamente i passi
        canvas_frame = ttk.LabelFrame(self, text="Anteprima allenamento")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Crea il canvas
        self.canvas = tk.Canvas(canvas_frame, bg=COLORS["bg_light"], highlightthickness=0, height=140)  # Aggiunta height=140
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Aggiungi i binding dopo aver creato il canvas
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # Inizializza i dati di trascinamento del canvas con una struttura completa
        self.canvas_drag_data = {
            "item": None,
            "index": -1,
            "start_x": 0,
            "start_y": 0,
            "current_x": 0,
            "current_y": 0,
            "type": "",
            "color": ""
        }
        
        # Frame per i bottoni
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(buttons_frame, text="Aggiungi passo", command=self.add_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Aggiungi ripetizione", command=self.add_repeat).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Modifica passo", command=self.edit_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Rimuovi passo", command=self.remove_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Sposta su", command=self.move_step_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Sposta giù", command=self.move_step_down).pack(side=tk.LEFT, padx=5)
        
        # Lista dei passi
        list_frame = ttk.LabelFrame(self, text="Passi dell'allenamento")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Crea la Treeview
        self.steps_tree = ttk.Treeview(list_frame, columns=("index", "type", "details"), show="headings")
        self.steps_tree.heading("index", text="#")
        self.steps_tree.heading("type", text="Tipo")
        self.steps_tree.heading("details", text="Dettagli")
        self.steps_tree.column("index", width=30)
        self.steps_tree.column("type", width=100)
        self.steps_tree.column("details", width=500)
        self.steps_tree.bind("<ButtonPress-1>", self.on_tree_press)
        self.steps_tree.bind("<B1-Motion>", self.on_tree_motion)
        self.steps_tree.bind("<ButtonRelease-1>", self.on_tree_release)
        self.drag_data = {"item": None, "index": -1}
                
        # Aggiungi scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.steps_tree.yview)
        self.steps_tree.configure(yscrollcommand=scrollbar.set)
        
        # Packing
        self.steps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottoni OK/Cancel
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(bottom_frame, text="Salva", command=self.on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="Annulla", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Bind eventi
        self.steps_tree.bind("<Double-1>", self.on_step_double_click)
        self.steps_tree.bind("<<TreeviewSelect>>", self.on_step_select)
        
        # Programmazione del disegno iniziale dopo che l'interfaccia è stata completamente inizializzata
        self.after(100, self.initial_draw)
    
    def initial_draw(self):
        """Force an initial drawing of the canvas to ensure dimensions are set correctly"""
        # Forza l'aggiornamento del canvas
        self.canvas.update_idletasks()
        
        # Ridisegna il workout
        self.draw_workout()
        
        # Stampa informazioni di debug sulle dimensioni del canvas dopo l'inizializzazione
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        print(f"Canvas initialized with dimensions: {width}x{height}")
        print(f"Canvas center calculated at y={height//2}")

    def on_canvas_press(self, event):
        """Handle press on canvas for drag-and-drop with more flexible click area"""
        # Canvas dimensions
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        # Se il canvas non è ancora inizializzato correttamente, forza l'aggiornamento
        if width <= 1 or height <= 1:
            self.canvas.update_idletasks()
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            print(f"Canvas dimensions updated: {width}x{height}")
        
        margin = 5
        draw_width = width - 2 * margin
        
        # Calcola il centro e la zona cliccabile con più tolleranza
        center_y = height // 2
        click_zone_height = 80  # Aumentata per essere più permissiva
        
        # Debug info
        print(f"Canvas click at: ({event.x}, {event.y})")
        print(f"Canvas dimensions: {width}x{height}, center: {center_y}")
        print(f"Step count: {len(self.workout_steps)}")
        print(f"Click zone: {center_y - click_zone_height/2} to {center_y + click_zone_height/2}")
        
        # Verifica che ci siano step
        if not self.workout_steps or len(self.workout_steps) == 0:
            print("No steps to select")
            return
        
        # Verifica se il click è nella zona degli step (fascia centrale con tolleranza)
        if center_y - click_zone_height/2 <= event.y <= center_y + click_zone_height/2:
            print("Click is in the step area (vertically)")
            
            # Calcola la larghezza di ciascun blocco e determina quale è stato cliccato
            base_width = draw_width / len(self.workout_steps)
            
            # Calcola l'indice dello step cliccato (correzione per i margini)
            relative_x = event.x - margin
            step_index = int(relative_x / base_width)
            
            print(f"Calculated step index: {step_index}")
            print(f"Base width: {base_width}")
            print(f"Relative X: {relative_x}")
            
            # Verifica e limita l'indice per sicurezza
            if 0 <= step_index < len(self.workout_steps):
                print(f"Valid step index: {step_index}")
                
                # Seleziona anche nella TreeView
                try:
                    tree_item = self.steps_tree.get_children()[step_index]
                    self.steps_tree.selection_set(tree_item)
                    self.steps_tree.see(tree_item)
                    print(f"Selected item in tree: {tree_item}")
                except Exception as e:
                    print(f"Error selecting in tree: {e}")
                
                # Memorizza i dettagli dell'elemento per il trascinamento
                step = self.workout_steps[step_index]
                
                # Inizializza i dati di trascinamento
                self.canvas_drag_data = {
                    "item": step,
                    "index": step_index,
                    "start_x": event.x,
                    "start_y": event.y,
                    "current_x": event.x,
                    "current_y": event.y
                }
                
                # Determina tipo e colore
                if 'repeat' in step and 'steps' in step:
                    self.canvas_drag_data["type"] = "repeat"
                    self.canvas_drag_data["color"] = COLORS["repeat"]
                else:
                    step_type = list(step.keys())[0]
                    self.canvas_drag_data["type"] = step_type
                    self.canvas_drag_data["color"] = COLORS.get(step_type, COLORS["other"])
                
                # Ridisegna con l'elemento evidenziato
                self.draw_workout(highlight_index=step_index)
                print(f"Drag data set: {self.canvas_drag_data}")
                return
            else:
                print(f"Step index {step_index} out of range (0-{len(self.workout_steps)-1})")
        else:
            print(f"Click outside step area (y={event.y}, center={center_y}, zone={click_zone_height})")
        
        # Se arriviamo qui, nessuno step è stato selezionato
        self.canvas_drag_data = {
            "item": None,
            "index": -1,
            "start_x": 0,
            "start_y": 0,
            "current_x": 0,
            "current_y": 0,
            "type": "",
            "color": ""
        }
        print("No step selected")


    def on_canvas_motion(self, event):
        """Handle motion while dragging on canvas"""
        # Solo se abbiamo un elemento selezionato
        if self.canvas_drag_data["item"] is not None:
            # Aggiorna la posizione corrente
            self.canvas_drag_data["current_x"] = event.x
            self.canvas_drag_data["current_y"] = event.y
            
            # Canvas dimensions
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            margin = 5
            draw_width = width - 2 * margin
            
            # Lista degli step visibili
            visible_steps = self.workout_steps
            
            # Larghezza di base per ogni step
            base_width = draw_width / max(1, len(visible_steps))
            
            # Determina la nuova posizione in base alla coordinata x
            x = event.x
            new_index = int((x - margin) / base_width)
            
            # Limita l'indice all'intervallo valido
            new_index = max(0, min(new_index, len(visible_steps) - 1))
            
            # Ridisegna il grafico con l'indicatore di trascinamento
            self.draw_workout(drag_from=self.canvas_drag_data["index"], drag_to=new_index, event_x=event.x, event_y=event.y)

    def on_canvas_release(self, event):
        """Handle release to complete drag-and-drop on canvas"""
        # Solo se abbiamo un elemento selezionato
        if self.canvas_drag_data["item"] is not None:
            # Canvas dimensions
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            margin = 5
            draw_width = width - 2 * margin
            
            # Lista degli step visibili
            visible_steps = []
            for step in self.workout_steps:
                visible_steps.append(step)
            
            # Larghezza di base per ogni step
            base_width = draw_width / max(1, len(visible_steps))
            
            # Determina la nuova posizione in base alla coordinata x
            x = event.x
            new_index = int((x - margin) / base_width)
            
            # Limita l'indice all'intervallo valido
            new_index = max(0, min(new_index, len(visible_steps) - 1))
            
            # Sposta l'elemento solo se la posizione è cambiata
            if new_index != self.canvas_drag_data["index"]:
                source_index = self.canvas_drag_data["index"]
                
                # Esegui lo spostamento nella lista di step
                item = self.workout_steps.pop(source_index)
                self.workout_steps.insert(new_index, item)
                
                # Aggiorna sia il grafico che la lista
                self.load_steps()
                
                # Seleziona l'elemento spostato nella lista
                target_item = self.steps_tree.get_children()[new_index]
                self.steps_tree.selection_set(target_item)
                self.steps_tree.see(target_item)
            else:
                # Se non c'è stato spostamento, ridisegna semplicemente senza evidenziazione
                self.draw_workout()
                
            # Resetta i dati di trascinamento
            self.canvas_drag_data = {"item": None, "index": -1, "start_x": 0, "start_y": 0}


    def on_tree_press(self, event):
        """Handle press on treeview for drag-and-drop"""
        # Get the item that was clicked
        item = self.steps_tree.identify_row(event.y)
        if item:
            # Save the item details
            self.drag_data["item"] = item
            index = self.steps_tree.index(item)
            self.drag_data["index"] = index

    def on_tree_motion(self, event):
        """Handle motion while dragging"""
        # Only move if we have an item
        if self.drag_data["item"]:
            # Get the position to move to
            target_item = self.steps_tree.identify_row(event.y)
            if target_item and target_item != self.drag_data["item"]:
                # Visual feedback - could add a dashed line or change background color
                pass

    def on_tree_release(self, event):
        """Handle release to complete drag-and-drop"""
        # Only process if we have an item
        if self.drag_data["item"]:
            # Get the position to move to
            target_item = self.steps_tree.identify_row(event.y)
            if target_item and target_item != self.drag_data["item"]:
                # Get target index
                target_index = self.steps_tree.index(target_item)
                # Get source index
                source_index = self.drag_data["index"]
                
                # Move the item in the workout_steps list
                item = self.workout_steps.pop(source_index)
                self.workout_steps.insert(target_index, item)
                
                # Reload the steps (which will update the treeview)
                self.load_steps()
                
                # Select the moved item
                self.steps_tree.selection_set(self.steps_tree.get_children()[target_index])
                self.steps_tree.focus(self.steps_tree.get_children()[target_index])
                
            # Reset drag data
            self.drag_data = {"item": None, "index": -1}


    def load_steps(self):
        """Load steps into the treeview and update the canvas"""
        # Clear existing items
        for item in self.steps_tree.get_children():
            self.steps_tree.delete(item)
        
        # Add steps to the tree
        for i, step in enumerate(self.workout_steps):  # Questo è corretto
            if 'repeat' in step and 'steps' in step:
                # It's a repeat step
                iterations = step['repeat']
                substeps = step['steps']
                details = f"{iterations}x [{len(substeps)} passi]"
                self.steps_tree.insert("", "end", values=(i+1, "repeat", details))
            else:
                # Regular step
                step_type = list(step.keys())[0]
                step_detail = step[step_type]
                self.steps_tree.insert("", "end", values=(i+1, step_type, step_detail))
        
        # Update the visual representation
        self.draw_workout()
    

    def draw_workout(self, highlight_index=None, drag_from=None, drag_to=None, event_x=None, event_y=None):
            """Draw a visual representation of the workout on the canvas with visible separators between steps"""
            self.canvas.delete("all")
            
            # Canvas dimensions
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            
            if width <= 1 or height <= 1:  # Canvas not yet realized
                self.canvas.update_idletasks()
                width = self.canvas.winfo_width()
                height = self.canvas.winfo_height()
                
                # If still not realized, use default dimensions
                if width <= 1:
                    width = 700
                if height <= 1:
                    height = 150
            
            # Margin
            margin = 5
            
            # Available drawing area
            draw_width = width - 2 * margin
            draw_height = height - 2 * margin
            
            # Lista degli step visibili
            visible_steps = self.workout_steps
            
            # Calcola la larghezza totale disponibile
            total_width = draw_width
            
            # Larghezza di base per ogni step
            base_width = total_width / max(1, len(visible_steps))
            
            # Current x position
            x = margin
            y = height // 2
            
            # Numerazione progressiva degli step
            step_number = 1
            
            # Se stiamo trascinando, disegna un indicatore per la posizione target
            if drag_from is not None and drag_to is not None:
                # Calcola la posizione x dell'indicatore di trascinamento
                indicator_x = margin + drag_to * base_width
                
                # Disegna una linea verticale per indicare dove verrà inserito l'elemento
                self.canvas.create_line(
                    indicator_x, y - 30, 
                    indicator_x, y + 30,
                    fill=COLORS["accent"], width=2, dash=(6, 4)
                )
            
            # Draw representation
            for i, step in enumerate(visible_steps):
                try:
                    # Calcola se questo step deve essere evidenziato
                    is_highlighted = (i == highlight_index)
                    
                    # Salta temporaneamente il disegno dell'elemento che stiamo trascinando
                    if i == drag_from and event_x is not None and event_y is not None:
                        x += base_width  # Salta avanti
                        continue  # Non disegnare questo elemento nella sua posizione originale
                    
                    outline_width = 2 if is_highlighted else 0
                    outline_color = COLORS["accent"] if is_highlighted else ""
                    
                    if 'repeat' in step and 'steps' in step:
                        # Repeat step
                        iterations = step['repeat']
                        substeps = step['steps']
                        
                        # Larghezza per ogni ripetizione
                        repeat_width = base_width
                        
                        # Draw repeat box
                        repeat_x = x
                        repeat_y = y - 30
                        self.canvas.create_rectangle(
                            repeat_x, repeat_y, 
                            repeat_x + repeat_width, repeat_y + 60,
                            outline=COLORS["repeat"], width=2, dash=(5, 2)
                        )
                        
                        # Draw repeat label
                        self.canvas.create_text(
                            repeat_x + 10, repeat_y - 10,
                            text=f"{STEP_ICONS['repeat']} {iterations}x",
                            fill=COLORS["repeat"], 
                            font=("Arial", 10, "bold"),
                            anchor=tk.W
                        )
                        
                        # Draw substeps
                        sub_width = repeat_width / max(1, len(substeps)) # Distribuisci uniformemente
                        sub_x = x
                        sub_number = 1  # Numerazione dei substep all'interno della ripetizione
                        
                        for substep in substeps:
                            if isinstance(substep, dict):
                                substep_type = list(substep.keys())[0]
                                
                                # Color for this type
                                color = COLORS.get(substep_type, COLORS["other"])
                                
                                # Draw box
                                self.canvas.create_rectangle(
                                    sub_x, y - 20, sub_x + sub_width, y + 20,
                                    fill=color, outline=outline_color, width=outline_width
                                )
                                
                                # Draw text
                                self.canvas.create_text(
                                    sub_x + sub_width // 2, y,
                                    text=f"{STEP_ICONS.get(substep_type, '📝')} {sub_number}",
                                    fill=COLORS["text_light"],
                                    font=("Arial", 9, "bold")
                                )
                                
                                # Disegna separatore tra substep (eccetto l'ultimo)
                                if sub_number < len(substeps):
                                    self.canvas.create_line(
                                        sub_x + sub_width, y - 20,
                                        sub_x + sub_width, y + 20,
                                        fill="white", width=1
                                    )
                                
                                # Move to next position
                                sub_x += sub_width
                                sub_number += 1
                        
                        # Aggiorna la posizione x per il prossimo step principale
                        x += repeat_width
                        step_number += 1
                        
                    else:
                        # Regular step
                        step_type = list(step.keys())[0]
                        
                        # Calculate width based on base_width
                        step_width = base_width
                        
                        # Color for this type
                        color = COLORS.get(step_type, COLORS["other"])
                        
                        # Draw box
                        self.canvas.create_rectangle(
                            x, y - 20, x + step_width, y + 20,
                            fill=color, outline=outline_color, width=outline_width
                        )
                        
                        # Draw text
                        self.canvas.create_text(
                            x + step_width // 2, y,
                            text=f"{STEP_ICONS.get(step_type, '📝')} {step_number}",
                            fill=COLORS["text_light"],
                            font=("Arial", 9, "bold")
                        )
                        
                        # Move to next position
                        x += step_width
                        step_number += 1
                        
                except Exception as e:
                    # Skip drawing problematic steps
                    step_width = base_width
                    self.canvas.create_rectangle(
                        x, y - 20, x + step_width, y + 20,
                        fill=COLORS["other"], outline=outline_color, width=outline_width
                    )
                    
                    self.canvas.create_text(
                        x + step_width // 2, y,
                        text=f"[?]",
                        fill=COLORS["text_light"],
                        font=("Arial", 9)
                    )
                    
                    x += step_width
                    step_number += 1
                    
                # Disegna separatori tra step principali (linea verticale)
                if i < len(visible_steps) - 1:  # Non disegnare dopo l'ultimo step
                    self.canvas.create_line(
                        x, y - 22,  # Leggermente oltre il bordo del rettangolo
                        x, y + 22,
                        fill="#333333", width=1, dash=(2, 2)  # Linea tratteggiata grigia
                    )
            
            # Se stiamo trascinando, disegna l'elemento trascinato sotto il cursore
            if drag_from is not None and event_x is not None and event_y is not None and 'type' in self.canvas_drag_data:
                block_width = base_width
                block_height = 40
                
                # Disegna un rettangolo semitrasparente che rappresenta l'elemento trascinato
                element_type = self.canvas_drag_data["type"]
                color = self.canvas_drag_data["color"]
                
                # Per ottenere un effetto semitrasparente, usiamo un colore leggermente più chiaro
                # Questo non è vera trasparenza (richiederebbe il supporto alpha), ma è un buon sostituto
                light_color = self.lighten_color(color)
                
                # Disegna il rettangolo centrato sul cursore
                self.canvas.create_rectangle(
                    event_x - block_width/2, event_y - block_height/2,
                    event_x + block_width/2, event_y + block_height/2,
                    fill=light_color, outline=COLORS["accent"], width=2
                )
                
                # Aggiunge anche un'icona o un numero all'elemento trascinato
                if element_type == "repeat":
                    icon = STEP_ICONS["repeat"]
                else:
                    icon = STEP_ICONS.get(element_type, '📝')
                
                self.canvas.create_text(
                    event_x, event_y,
                    text=f"{icon} {drag_from + 1}",
                    fill=COLORS["text_dark"],
                    font=("Arial", 9, "bold")
                )


    def lighten_color(self, hex_color):
        """Rende più chiaro un colore hexadecimale mescolandolo con bianco"""
        # Converte hex_color in componenti RGB
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        
        # Mescola con bianco (255,255,255) con un rapporto 40/60
        r = r * 0.6 + 255 * 0.4
        g = g * 0.6 + 255 * 0.4
        b = b * 0.6 + 255 * 0.4
        
        # Converte in hex e restituisce
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    
    def get_step_visual_length(self, step):
        """Calculate a visual length for a step based on its duration/distance"""
        if 'repeat' in step:
            # For repeat steps, calculate based on substeps
            return 10  # Default size for empty repeats
        
        step_type = list(step.keys())[0]
        step_detail = step[step_type]
        
        # Handle case where step_detail is a list (old format)
        if isinstance(step_detail, list):
            return 30  # Default length for steps with unknown structure
        
        # Extract the duration/distance
        if ' @ ' in step_detail:
            measure = step_detail.split(' @ ')[0].strip()
        else:
            measure = step_detail.strip()
        
        # Try to parse the measure
        try:
            if 'min' in measure:
                # Duration in minutes
                mins = float(measure.replace('min', '').strip())
                return mins * 5  # Scale factor for minutes
            elif 'km' in measure:
                # Distance in km
                km = float(measure.replace('km', '').strip())
                return km * 50  # Scale factor for km
            elif 'm' in measure:
                # Distance in meters
                m = float(measure.replace('m', '').strip())
                return m / 20  # Scale factor for meters
            else:
                # Default length if parsing fails
                return 30
        except ValueError:
            # Default length if parsing fails
            return 30
    
    def get_step_display_text(self, step_type, step_detail):
        """Get a short display text for a step"""
        # Handle case where step_detail is a list (old format)
        if isinstance(step_detail, list):
            return f"{step_type} ({len(step_detail)} steps)"
        
        # Extract the measure and zone
        if ' @ ' in step_detail:
            measure, zone = step_detail.split(' @ ', 1)
            
            # Remove description if any
            if ' -- ' in zone:
                zone = zone.split(' -- ')[0].strip()
            
            return f"{measure} @ {zone}"
        else:
            # Remove description if any
            if ' -- ' in step_detail:
                step_detail = step_detail.split(' -- ')[0].strip()
            
            return step_detail
    
    def add_step(self):
        """Add a new step to the workout"""
        dialog = StepDialog(self)
        
        if dialog.result:
            step_type, step_detail = dialog.result
            self.workout_steps.append({step_type: step_detail})
            self.load_steps()
    
    def add_repeat(self):
        """Add a repeat section"""
        dialog = RepeatDialog(self)
        
        if dialog.result:
            iterations, steps = dialog.result
            
            # Create the repeat step with correct structure
            repeat_step = {'repeat': iterations, 'steps': steps}
            
            # Add to steps list
            self.workout_steps.append(repeat_step)
            
            # Reload the steps
            self.load_steps()
    
    def edit_step(self):
        """Edit the selected step"""
        selection = self.steps_tree.selection()
        
        if not selection:
            messagebox.showwarning("Nessuna selezione", "Seleziona un passo da modificare", parent=self)
            return
        
        # Get the selected step index
        item = selection[0]
        item_values = self.steps_tree.item(item, "values")
        index = int(item_values[0]) - 1
        
        # Check if it's a repeat step
        step = self.workout_steps[index]
        if 'repeat' in step and 'steps' in step:
            # It's a repeat step, edit it with RepeatDialog
            iterations = step['repeat']
            steps = step['steps']
            
            # Aggiungi un debug qui per vedere cosa contiene steps
            print(f"Steps prima di RepeatDialog: {steps}")
            
            dialog = RepeatDialog(self, iterations, steps)
            
            if dialog.result:
                new_iterations, new_steps = dialog.result
                
                # Update the repeat step with correct structure
                self.workout_steps[index] = {'repeat': new_iterations, 'steps': new_steps}
                
                # Reload the steps
                self.load_steps()
        else:
            # Regular step or old format step
            if isinstance(step, dict):
                step_type = list(step.keys())[0]
                step_detail = step[step_type]
                
                # Handle case where step_detail is a list (old format)
                if isinstance(step_detail, list):
                    messagebox.showinfo("Formato non supportato", 
                                       f"Questo passo ha un formato vecchio che non può essere modificato direttamente.\n"
                                       f"Ti suggeriamo di eliminarlo e ricrearlo.", parent=self)
                    return
                
                dialog = StepDialog(self, step_type, step_detail)
                
                if dialog.result:
                    new_type, new_detail = dialog.result
                    
                    # Update the step
                    self.workout_steps[index] = {new_type: new_detail}
                    
                    # Reload the steps
                    self.load_steps()
            else:
                # Handle completely unsupported format
                messagebox.showinfo("Formato non supportato", 
                                   f"Questo passo ha un formato che non può essere modificato direttamente.\n"
                                   f"Ti suggeriamo di eliminarlo e ricrearlo.", parent=self)
    
    def remove_step(self):
        """Remove the selected step"""
        selection = self.steps_tree.selection()
        
        if not selection:
            messagebox.showwarning("Nessuna selezione", "Seleziona un passo da rimuovere", parent=self)
            return
        
        # Get the selected step index
        item = selection[0]
        item_values = self.steps_tree.item(item, "values")
        index = int(item_values[0]) - 1
        
        # Remove the step
        self.workout_steps.pop(index)
        self.load_steps()
    
    def move_step_up(self):
        """Move the selected step up"""
        selection = self.steps_tree.selection()
        
        if not selection:
            return
        
        # Get the selected step index
        item = selection[0]
        item_values = self.steps_tree.item(item, "values")
        index = int(item_values[0]) - 1
        
        # Can't move up if already at the top
        if index == 0:
            return
        
        # Swap with the step above
        self.workout_steps[index], self.workout_steps[index - 1] = self.workout_steps[index - 1], self.workout_steps[index]
        self.load_steps()
        
        # Re-select the step
        for item in self.steps_tree.get_children():
            if int(self.steps_tree.item(item, "values")[0]) == index:
                self.steps_tree.selection_set(item)
                break
    
    def move_step_down(self):
        """Move the selected step down"""
        selection = self.steps_tree.selection()
        
        if not selection:
            return
        
        # Get the selected step index
        item = selection[0]
        item_values = self.steps_tree.item(item, "values")
        index = int(item_values[0]) - 1
        
        # Can't move down if already at the bottom
        if index >= len(self.workout_steps) - 1:
            return
        
        # Swap with the step below
        self.workout_steps[index], self.workout_steps[index + 1] = self.workout_steps[index + 1], self.workout_steps[index]
        self.load_steps()
        
        # Re-select the step
        for item in self.steps_tree.get_children():
            if int(self.steps_tree.item(item, "values")[0]) == index + 2:
                self.steps_tree.selection_set(item)
                break
    
    def on_step_double_click(self, event):
        """Handle double-click on a step"""
        self.edit_step()
    
    def on_step_select(self, event):
        """Handle step selection"""
        # Update the canvas to highlight the selected step
        self.draw_workout()
    
    def on_save(self):
        """Handle Save button click"""
        # Validate the workout name
        workout_name = self.name_var.get().strip()
        if not workout_name:
            messagebox.showerror("Errore", "Inserisci un nome per l'allenamento", parent=self)
            return
        
        # Validate that there are steps
        if not self.workout_steps:
            messagebox.showerror("Errore", "Aggiungi almeno un passo all'allenamento", parent=self)
            return
        
        # Set the result
        self.result = (workout_name, self.workout_steps)
        
        # Close the editor
        self.destroy()
    
    def on_cancel(self):
        """Handle Cancel button click"""
        self.destroy()


def create_workout(parent):
    """Create a new workout"""
    editor = WorkoutEditor(parent)
    return editor.result

def edit_workout(parent, workout_name, workout_steps):
    """Edit an existing workout"""
    editor = WorkoutEditor(parent, workout_name, workout_steps)
    return editor.result


def add_workout_editor_tab(notebook, parent):
    """Add a tab with workout editor functionality"""
    # Create a frame for the editor tab
    editor_frame = ttk.Frame(notebook)
    notebook.add(editor_frame, text="Editor Allenamenti")
    
    # Upper frame for the list of workouts
    upper_frame = ttk.LabelFrame(editor_frame, text="Allenamenti disponibili")
    upper_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # Create treeview for the list of workouts
    workout_tree = ttk.Treeview(upper_frame, columns=("name", "steps"), show="headings")
    workout_tree.heading("name", text="Nome")
    workout_tree.heading("steps", text="Passi")
    workout_tree.column("name", width=300)
    workout_tree.column("steps", width=100)
    
    # Add scrollbar
    scrollbar = ttk.Scrollbar(upper_frame, orient=tk.VERTICAL, command=workout_tree.yview)
    workout_tree.configure(yscrollcommand=scrollbar.set)
    
    # Pack widgets
    workout_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Store workouts in memory
    workouts = []
    
    def load_workouts_from_file():
        """Load workouts from a YAML file"""
        filename = filedialog.askopenfilename(
            title="Seleziona file allenamenti",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
                # Clear existing workouts
                workouts.clear()
                
                # Extract config data if available
                global workout_config
                if 'config' in data:
                    workout_config.update(data['config'])
                
                # Extract workouts
                for key, value in data.items():
                    if key != 'config' and isinstance(value, list):
                        # Process the workout steps to handle repeat formats
                        processed_steps = []
                        for step in value:
                            # Check if this is a repeat step
                            if isinstance(step, dict) and len(step) == 1 and list(step.keys())[0].startswith('repeat'):
                                repeat_key = list(step.keys())[0]
                                # Extract number of iterations
                                iterations = int(repeat_key.split(' ')[1].rstrip(':'))
                                # Get the substeps
                                substeps = step[repeat_key]
                                # Create the repeat step in the expected format
                                repeat_step = {'repeat': iterations, 'steps': substeps}
                                processed_steps.append(repeat_step)
                            else:
                                processed_steps.append(step)
                        
                        workouts.append((key, processed_steps))
                
                # Update the treeview
                load_workouts_to_tree()
                
                messagebox.showinfo("Successo", f"Caricati {len(workouts)} allenamenti dal file", parent=parent)
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento del file: {str(e)}", parent=parent)
    
    def save_workouts_to_file():
        """Save workouts to a YAML file"""
        if not LicenseManager.get_instance().check_feature_access("premium"):
            return
        if not workouts:
            messagebox.showwarning("Attenzione", "Nessun allenamento da salvare", parent=parent)
            return
        
        filename = filedialog.asksaveasfilename(
            title="Salva file allenamenti",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            defaultextension=".yaml"
        )
        
        if not filename:
            return
        
        try:
            # Create a dictionary with all workouts
            data = {}
            
            # Add the config section
            global workout_config
            data['config'] = workout_config
            
            # Add all workouts
            for name, steps in workouts:
                data[name] = steps
            
            # Use NoAliasDumper to prevent YAML aliases
            class NoAliasDumper(yaml.SafeDumper):
                def ignore_aliases(self, data):
                    return True
            
            # Write the file
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False, Dumper=NoAliasDumper)
            
            messagebox.showinfo("Successo", f"Salvati {len(workouts)} allenamenti nel file", parent=parent)
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel salvataggio del file: {str(e)}", parent=parent)
    
    def load_workouts_to_tree():
        """Load workouts into the treeview"""
        # Clear existing items
        for item in workout_tree.get_children():
            workout_tree.delete(item)
        
        # Add workouts to the tree
        for name, steps in workouts:
            workout_tree.insert("", "end", values=(name, f"{len(steps)} passi"))
    
    def create_new_workout():
        """Create a new workout"""
        result = create_workout(parent)
        
        if result:
            name, steps = result
            workouts.append((name, copy.deepcopy(steps)))
            load_workouts_to_tree()
    
    def edit_selected_workout():
        """Edit the selected workout"""
        selection = workout_tree.selection()
        
        if not selection:
            messagebox.showwarning("Nessuna selezione", "Seleziona un allenamento da modificare", parent=parent)
            return
        
        # Get the selected workout index
        index = workout_tree.index(selection[0])
        name, steps = workouts[index]
        
        # Open the editor
        result = edit_workout(parent, name, copy.deepcopy(steps))
        
        if result:
            new_name, new_steps = result
            workouts[index] = (new_name, copy.deepcopy(new_steps))
            load_workouts_to_tree()
    
    def delete_selected_workout():
        """Delete the selected workouts"""
        selection = workout_tree.selection()
        
        if not selection:
            messagebox.showwarning("Nessuna selezione", "Seleziona uno o più allenamenti da eliminare", parent=parent)
            return
        
        # Ottieni i nomi degli allenamenti selezionati
        selected_workouts = []
        for item in selection:
            index = workout_tree.index(item)
            name, _ = workouts[index]
            selected_workouts.append(name)
        
        # Conferma plurale o singolare in base al numero di selezioni
        if len(selected_workouts) == 1:
            confirm_message = f"Sei sicuro di voler eliminare l'allenamento '{selected_workouts[0]}'?"
        else:
            confirm_message = f"Sei sicuro di voler eliminare questi {len(selected_workouts)} allenamenti?\n\n"
            # Mostra i primi 5 allenamenti nel messaggio, poi "..." se sono di più
            if len(selected_workouts) > 5:
                confirm_message += "\n".join(selected_workouts[:5]) + "\n..."
            else:
                confirm_message += "\n".join(selected_workouts)
        
        # Chiedi conferma
        if not messagebox.askyesno("Conferma", confirm_message, parent=parent):
            return
        
        # Elimina gli allenamenti selezionati (dalla fine all'inizio per evitare problemi di indice)
        indices = [workout_tree.index(item) for item in selection]
        indices.sort(reverse=True)  # Ordina in ordine decrescente
        
        for index in indices:
            workouts.pop(index)
        
        # Aggiorna la vista
        load_workouts_to_tree()
    
    def edit_configuration():
        """Edit pace and heart rate configuration"""
        # Open the configuration editor dialog
        ConfigEditorDialog(parent)
        
    # Button frame
    button_frame = ttk.Frame(editor_frame)
    button_frame.pack(fill=tk.X, padx=10, pady=5)
    
    ttk.Button(button_frame, text="Nuovo allenamento", command=create_new_workout).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Modifica allenamento", command=edit_selected_workout).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Elimina allenamento", command=delete_selected_workout).pack(side=tk.LEFT, padx=5)
    
    # File operations frame
    file_frame = ttk.Frame(editor_frame)
    file_frame.pack(fill=tk.X, padx=10, pady=5)
    
    ttk.Button(file_frame, text="Carica da file", command=load_workouts_from_file).pack(side=tk.LEFT, padx=5)
    ttk.Button(file_frame, text="Salva su file", command=save_workouts_to_file).pack(side=tk.LEFT, padx=5)
    ttk.Button(file_frame, text="Modifica Configurazione", command=edit_configuration).pack(side=tk.LEFT, padx=5)
    
    # Double-click to edit
    workout_tree.bind("<Double-1>", lambda e: edit_selected_workout())
    
    return editor_frame



if __name__ == "__main__":
    # Demo app
    root = tk.Tk()
    root.title("Demo Editor Allenamenti")
    root.geometry("800x650")
    
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    add_workout_editor_tab(notebook, root)
    
    root.mainloop()