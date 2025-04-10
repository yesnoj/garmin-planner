#!/usr/bin/env python
import os
import sys
import subprocess
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
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("Installazione completata con successo.")
        except subprocess.CalledProcessError as e:
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
    
    # Avvia l'interfaccia grafica
    print("Avvio dell'interfaccia grafica...")
    subprocess.call([sys.executable, gui_path])

if __name__ == "__main__":
    main()
