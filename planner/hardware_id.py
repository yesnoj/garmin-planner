# planner/hardware_id.py
import uuid
import subprocess
import platform
import hashlib
import re
import os
import logging

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
        logging.debug(f"Error getting MAC address: {str(e)}")
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
        logging.debug(f"Error getting disk serial: {str(e)}")
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
        logging.debug(f"Error getting motherboard serial: {str(e)}")
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
        logging.debug(f"Error getting CPU info: {str(e)}")
    return platform.processor()

def generate_hardware_fingerprint():
    """Genera un identificatore hardware univoco combinando vari identificatori hardware"""
    logging.debug("Generating hardware fingerprint...")
    
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
        logging.debug(f"Component {i+1}: {component}")
    
    # Crea un identificatore concatenando i componenti e calcolando un hash
    fingerprint = "-".join([str(c) for c in components if c])
    
    # Calcola l'hash SHA-256 e restituisci i primi 16 caratteri (abbastanza univoci)
    hwid = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    logging.debug(f"Generated hardware ID: {hwid}")
    
    return hwid