#!/usr/bin/env python
import os
import sys
import importlib
import tkinter as tk
from tkinter import messagebox

def check_dependencies():
    """Verifica e installa le dipendenze necessarie."""
    required_packages = ["pyyaml", "garth", "requests"]
    missing_packages = []
    
    # Verifica pacchetti già installati
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    # Installa pacchetti mancanti
    if missing_packages:
        print(f"Installazione dei pacchetti mancanti: {', '.join(missing_packages)}")
        try:
            import pip
            for package in missing_packages:
                print(f"Installazione di {package}...")
                pip.main(['install', package])
            print("Installazione completata con successo.")
        except Exception as e:
            print(f"Errore durante l'installazione: {e}")
            return False
    
    return True

def main():
    """Funzione principale che avvia l'interfaccia grafica."""
    # Verifica percorso dello script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Percorso dell'interfaccia grafica
    gui_path = os.path.join(script_dir, "garmin_planner_gui.py")
    
    # Verifica esistenza del file
    if not os.path.exists(gui_path):
        tk.Tk().withdraw()  # Nasconde la finestra principale vuota
        messagebox.showerror(
            "Errore", 
            f"File non trovato: {gui_path}\n\n"
            "Assicurati che il file garmin_planner_gui.py sia nella stessa directory di questo script."
        )
        return
    
    # Verifica dipendenze
    if not check_dependencies():
        tk.Tk().withdraw()
        messagebox.showerror(
            "Errore", 
            "Impossibile installare tutte le dipendenze necessarie.\n\n"
            "Verifica la connessione internet e i permessi di installazione dei pacchetti Python."
        )
        return
    
    # Avvia l'interfaccia grafica importando il modulo direttamente
    print("Avvio dell'interfaccia grafica...")
    
    # Aggiungi la directory corrente al path di Python
    sys.path.append(script_dir)
    
    try:
        # Opzione 1: Importa e inizializza direttamente
        import garmin_planner_gui
        app = garmin_planner_gui.GarminPlannerGUI()
        app.mainloop()
    except Exception as e:
        print(f"Errore durante l'avvio dell'interfaccia grafica: {e}")
        
        # Opzione 2: Carica dinamicamente il modulo
        try:
            spec = importlib.util.spec_from_file_location("garmin_planner_gui", gui_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            app = module.GarminPlannerGUI()
            app.mainloop()
        except Exception as e2:
            print(f"Errore durante il caricamento dinamico: {e2}")
            tk.Tk().withdraw()
            messagebox.showerror(
                "Errore", 
                f"Impossibile avviare l'interfaccia grafica:\n{str(e)}\n\n{str(e2)}"
            )

if __name__ == "__main__":
    main()