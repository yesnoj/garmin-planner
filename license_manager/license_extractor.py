#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Garmin Planner Hardware ID Extractor

This tool extracts the hardware ID that is used for license binding.
"""

import os
import sys
import platform
import hashlib
import re
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

def get_mac_address():
    """Ottiene l'indirizzo MAC della scheda di rete principale"""
    try:
        if platform.system() == "Windows":
            # Per Windows
            output = subprocess.check_output('getmac /v /fo csv /nh', shell=True).decode('utf-8')
            return re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', output).group(0)
        elif platform.system() == "Linux":
            # Per Linux
            output = subprocess.check_output("cat /sys/class/net/*/address", shell=True).decode('utf-8')
            macs = output.strip().split('\n')
            # Esclude indirizzi locali o di virtualizzazione
            for mac in macs:
                if not mac.startswith(("00:00:", "fe:00:", "00:05:69")):
                    return mac
        elif platform.system() == "Darwin":  # macOS
            output = subprocess.check_output("ifconfig en0 | grep ether", shell=True).decode('utf-8')
            return re.search(r'([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})', output).group(0)
    except Exception as e:
        print(f"Error getting MAC address: {str(e)}")
    return ""

def get_disk_serial():
    """Ottiene il serial number del disco rigido principale"""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("wmic diskdrive get SerialNumber", shell=True).decode('utf-8')
            return re.search(r'(\S+)', output.split('\n')[1]).group(0)
        elif platform.system() == "Linux":
            output = subprocess.check_output("lsblk --nodeps -o name,serial", shell=True).decode('utf-8')
            return output.strip().split('\n')[1].split()[1]
        elif platform.system() == "Darwin":  # macOS
            output = subprocess.check_output("diskutil info /dev/disk0 | grep 'Volume UUID'", shell=True).decode('utf-8')
            return output.strip().split()[-1]
    except Exception as e:
        print(f"Error getting disk serial: {str(e)}")
    return ""

def get_motherboard_serial():
    """Ottiene il serial number della motherboard"""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("wmic baseboard get serialnumber", shell=True).decode('utf-8')
            return output.strip().split('\n')[1].strip()
        elif platform.system() == "Linux":
            try:
                output = subprocess.check_output("sudo dmidecode -s baseboard-serial-number", shell=True).decode('utf-8')
                return output.strip()
            except:
                # Fallback per sistemi senza permessi sudo
                try:
                    with open('/sys/class/dmi/id/board_serial', 'r') as f:
                        return f.read().strip()
                except:
                    pass
        elif platform.system() == "Darwin":  # macOS
            output = subprocess.check_output("system_profiler SPHardwareDataType | grep 'Hardware UUID'", shell=True).decode('utf-8')
            return output.strip().split()[-1]
    except Exception as e:
        print(f"Error getting motherboard serial: {str(e)}")
    return ""

def get_cpu_info():
    """Ottiene informazioni sulla CPU"""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("wmic cpu get processorid", shell=True).decode('utf-8')
            return output.strip().split('\n')[1].strip()
        elif platform.system() == "Linux":
            try:
                output = subprocess.check_output("cat /proc/cpuinfo | grep 'processor' | wc -l", shell=True).decode('utf-8')
                cores = output.strip()
                output = subprocess.check_output("cat /proc/cpuinfo | grep 'model name' | head -1", shell=True).decode('utf-8')
                model = output.strip().split(':')[1].strip()
                return f"{model}-{cores}cores"
            except:
                return platform.processor()
        elif platform.system() == "Darwin":  # macOS
            output = subprocess.check_output("sysctl -n machdep.cpu.brand_string", shell=True).decode('utf-8')
            return output.strip()
    except Exception as e:
        print(f"Error getting CPU info: {str(e)}")
    return platform.processor()

def generate_hardware_fingerprint():
    """Genera un identificatore hardware univoco combinando vari identificatori hardware"""
    print("Generating hardware fingerprint...")
    
    # Raccogli i componenti
    components = [
        platform.node(),            # Nome computer
        get_mac_address(),          # MAC address
        get_disk_serial(),          # Serial del disco
        get_motherboard_serial(),   # Serial della motherboard
        get_cpu_info(),             # Info CPU
        platform.machine()          # Architettura del sistema
    ]
    
    # Log dei componenti raccolti
    for i, component in enumerate(components):
        print(f"Component {i+1}: {component}")
    
    # Crea un identificatore concatenando i componenti e calcolando un hash
    fingerprint = "-".join([str(c) for c in components if c])
    
    # Calcola l'hash SHA-256 e restituisci i primi 16 caratteri (abbastanza univoci)
    hwid = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    print(f"Generated hardware ID: {hwid}")
    
    return hwid

class HardwareIDExtractor(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Garmin Planner Hardware ID Extractor")
        self.geometry("600x500")
        self.resizable(True, True)
        
        # Set window icon if available
        try:
            self.iconbitmap("assets/garmin_planner_icon.ico")
        except:
            pass
        
        self.create_widgets()
        self.center_window()
        
        # Generate hardware ID on startup
        self.generate_id()
    
    def center_window(self):
        """Center the window on the screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """Create the UI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Garmin Planner Hardware ID Extractor", 
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Description
        description = (
            "This tool extracts the hardware ID used for Garmin Planner license activation.\n"
            "Send this ID to your license provider to get a license file for this computer."
        )
        ttk.Label(main_frame, text=description, wraplength=500).pack(pady=(0, 20))
        
        # Hardware ID Frame
        hw_frame = ttk.LabelFrame(main_frame, text="Hardware ID", padding="10")
        hw_frame.pack(fill=tk.X, pady=10)
        
        self.hw_id_var = tk.StringVar()
        id_entry = ttk.Entry(hw_frame, textvariable=self.hw_id_var, width=60, font=("Courier", 12))
        id_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(hw_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save to File", command=self.save_to_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Regenerate", command=self.generate_id).pack(side=tk.LEFT, padx=5)
        
        # Component details
        details_frame = ttk.LabelFrame(main_frame, text="System Components", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create a text widget for component details
        self.details_text = tk.Text(details_frame, height=10, wrap=tk.WORD)
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.config(yscrollcommand=scrollbar.set)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def generate_id(self):
        """Generate and display hardware ID"""
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, "Collecting system information...\n\n")
        self.update_idletasks()
        
        try:
            # Collect component information
            node = platform.node()
            mac = get_mac_address()
            disk = get_disk_serial()
            board = get_motherboard_serial()
            cpu = get_cpu_info()
            arch = platform.machine()
            
            # Display component details
            details = f"Computer Name: {node}\n"
            details += f"MAC Address: {mac}\n"
            details += f"Disk Serial: {disk}\n"
            details += f"Motherboard Serial: {board}\n"
            details += f"CPU Information: {cpu}\n"
            details += f"Architecture: {arch}\n"
            
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, details)
            
            # Generate the hardware ID
            hwid = generate_hardware_fingerprint()
            self.hw_id_var.set(hwid)
            
            self.status_var.set("Hardware ID generated successfully")
            
        except Exception as e:
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"Error: {str(e)}")
            self.status_var.set(f"Error generating hardware ID: {str(e)}")
    
    def copy_to_clipboard(self):
        """Copy the hardware ID to the clipboard"""
        hwid = self.hw_id_var.get()
        if hwid:
            self.clipboard_clear()
            self.clipboard_append(hwid)
            self.status_var.set("Hardware ID copied to clipboard")
            messagebox.showinfo("Copied", "Hardware ID has been copied to clipboard")
        else:
            self.status_var.set("No hardware ID to copy")
            messagebox.showwarning("No ID", "No hardware ID to copy")
    
    def save_to_file(self):
        """Save the hardware ID to a file"""
        hwid = self.hw_id_var.get()
        if not hwid:
            self.status_var.set("No hardware ID to save")
            messagebox.showwarning("No ID", "No hardware ID to save")
            return
        
        try:
            # Get desktop path
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop):
                desktop = os.path.expanduser("~")
            
            # Create filename
            computer_name = platform.node().replace(" ", "_")
            filename = f"garmin_planner_hwid_{computer_name}.txt"
            filepath = os.path.join(desktop, filename)
            
            # Write to file
            with open(filepath, 'w') as f:
                f.write(f"Garmin Planner Hardware ID\n")
                f.write(f"Computer: {platform.node()}\n")
                f.write(f"Generated: {os.path.basename(sys.argv[0])}\n")
                f.write(f"\nHardware ID: {hwid}\n")
                
            self.status_var.set(f"Hardware ID saved to {filepath}")
            messagebox.showinfo("Saved", f"Hardware ID has been saved to:\n{filepath}")
            
        except Exception as e:
            self.status_var.set(f"Error saving hardware ID: {str(e)}")
            messagebox.showerror("Error", f"Failed to save hardware ID:\n{str(e)}")

def main():
    app = HardwareIDExtractor()
    app.mainloop()

if __name__ == "__main__":
    main()
