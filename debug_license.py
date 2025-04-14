#!/usr/bin/env python
"""
Script per verificare lo stato della licenza di Garmin Planner
Questo script legge il file di licenza e mostra i dettagli sulla licenza attualmente installata
"""

import os
import sys
import json
import base64
import logging
import traceback
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LicenseDebugger")

# Chiave segreta per la crittografia
SECRET_KEY = b'g4rm1n_p1ann3r_s3cr3t_k3y_2024_v1'

def _generate_key():
    """Genera una chiave di crittografia basata sul secret key"""
    salt = b'garminplannersalt2024'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(SECRET_KEY))
    return key

def _decrypt_data(encrypted_data):
    """Decripta i dati della licenza"""
    try:
        f = Fernet(_generate_key())
        decrypted = f.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
    except Exception as e:
        logger.error(f"Error decrypting license data: {str(e)}")
        return None

def analyze_license(license_file_path):
    """Analizza un file di licenza e stampa le informazioni"""
    print(f"\n=== ANALISI LICENZA GARMIN PLANNER ===")
    print(f"File: {license_file_path}")
    
    if not os.path.exists(license_file_path):
        print(f"ERRORE: Il file di licenza non esiste!")
        return
    
    try:
        print("\nLettura del file...")
        with open(license_file_path, 'rb') as f:
            encrypted_data = f.read()
        
        print("Decifratura dei dati...")
        license_data = _decrypt_data(encrypted_data)
        
        if license_data is None:
            print("ERRORE: Impossibile decifrare il file! Potrebbe essere danneggiato o non valido.")
            return
        
        print("\n=== INFORMAZIONI LICENZA ===")
        print(f"Chiave di licenza: {license_data.get('license_key', 'N/A')}")
        print(f"ID Hardware: {license_data.get('hardware_id', 'N/A')}")
        print(f"Utente: {license_data.get('username', 'N/A')}")
        print(f"Data creazione: {license_data.get('creation_date', 'N/A')}")
        
        expiry_date = license_data.get('expiry_date')
        if expiry_date:
            print(f"Data scadenza: {expiry_date}")
            
            # Check if expired
            import datetime
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            if today > expiry_date:
                print("ATTENZIONE: LICENZA SCADUTA!")
            else:
                # Calculate days left
                expiry = datetime.datetime.strptime(expiry_date, "%Y-%m-%d")
                today_date = datetime.datetime.now()
                days_left = (expiry - today_date).days
                print(f"Giorni rimanenti: {days_left}")
        else:
            print("Data scadenza: Perpetua (nessuna scadenza)")
        
        # Features
        features = license_data.get('features', [])
        print(f"\nFeature abilitate ({len(features)}):")
        for feature in features:
            print(f"  - {feature}")
        
        # Analyze feature access
        print("\nVerifica accesso alle feature:")
        check_feature_access(features, "basic")
        check_feature_access(features, "pro")
        check_feature_access(features, "premium")
        
        # Full data for debugging
        print("\n=== DATI COMPLETI (JSON) ===")
        print(json.dumps(license_data, indent=2))
        
    except Exception as e:
        print(f"ERRORE durante l'analisi: {str(e)}")
        print("\nTraceback completo:")
        traceback.print_exc()

def check_feature_access(features, feature_name):
    """Verifica l'accesso a una feature con la logica gerarchica"""
    feature_hierarchy = {
        "basic": ["basic"],
        "pro": ["basic", "pro"],
        "premium": ["basic", "pro", "premium"]
    }
    
    has_access = False
    
    # Verifica diretta
    if feature_name in features:
        has_access = True
        reason = f"La feature '{feature_name}' è presente direttamente nella lista delle feature"
    else:
        # Verifica gerarchica
        for license_level in features:
            if license_level in feature_hierarchy and feature_name in feature_hierarchy[license_level]:
                has_access = True
                reason = f"La feature '{feature_name}' è inclusa nella licenza '{license_level}'"
                break
        else:
            reason = f"La feature '{feature_name}' non è inclusa in nessuna delle licenze attive"
    
    result = "ACCESSO CONSENTITO" if has_access else "ACCESSO NEGATO"
    print(f"  {feature_name}: {result} - {reason}")
    return has_access

def get_hardware_id():
    """
    Ottiene l'ID hardware del computer corrente
    """
    try:
        # Prova a importare e utilizzare l'implementazione completa
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from planner.hardware_id import generate_hardware_fingerprint
        return generate_hardware_fingerprint()
    except ImportError:
        # Implementazione semplificata per debug
        import uuid
        import platform
        
        # Get system information
        system_info = platform.uname()
        machine_id = str(uuid.getnode())  # MAC address as integer
        
        # Create a fingerprint
        fingerprint = f"{system_info.system}-{system_info.node}-{machine_id}"
        
        # Create a hash
        import hashlib
        return hashlib.sha256(fingerprint.encode()).hexdigest()

if __name__ == "__main__":
    # Determina il percorso del file di licenza
    script_dir = os.path.dirname(os.path.abspath(__file__))
    license_path = os.path.join(script_dir, "license.dat")
    
    # Se viene fornito un percorso come argomento, usalo
    if len(sys.argv) > 1:
        license_path = sys.argv[1]
    
    # Analizza la licenza
    analyze_license(license_path)
    
    # Mostra anche l'ID hardware corrente
    hw_id = get_hardware_id()
    print(f"\nID Hardware corrente: {hw_id}")
    print("Questo ID deve corrispondere all'ID Hardware nella licenza per funzionare correttamente.")
    
    input("\nPremi INVIO per uscire...")
