# planner/license_manager.py
import os
import json
import hashlib
import datetime
import base64
import logging
import tkinter.messagebox as messagebox
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from . import hardware_id

# Chiave segreta per la crittografia
SECRET_KEY = b'g4rm1n_p1ann3r_s3cr3t_k3y_2024_v1'

class LicenseManager:
    _instance = None
    
    @classmethod
    def get_instance(cls, app_dir=None):
        """
        Ottiene l'istanza singleton del LicenseManager
        Se l'istanza non esiste, la crea
        """
        if cls._instance is None:
            if app_dir is None:
                # Se app_dir non è fornito ma è necessario creare l'istanza
                # Inizializziamo con valori di default per poi configurarli dopo
                cls._instance = cls.__new__(cls)
                cls._instance.app_dir = None
                cls._instance.license_file = None
                cls._instance.hwid = None
                cls._instance.features = ["basic"]  # Default a basic features
            else:
                # Se app_dir è fornito, creiamo l'istanza completa
                cls._instance = cls(app_dir)
        return cls._instance

    def __init__(self, app_dir):
        """Inizializza il gestore delle licenze"""
        self.app_dir = app_dir
        self.license_file = os.path.join(app_dir, "license.dat")
        self.hwid = hardware_id.generate_hardware_fingerprint()
        self.features = ["basic"]  # Inizializziamo le feature a basic
        logging.debug(f"LicenseManager initialized with hardware ID: {self.hwid}")
        
        # Controlla subito la licenza durante l'inizializzazione
        self.validate_license()
    
    def initialize(self, app_dir):
        """
        Inizializza il gestore delle licenze dopo la creazione
        Utile quando get_instance() viene chiamato senza parametri
        """
        if self.app_dir is None:  # Inizializza solo se non già inizializzato
            self.app_dir = app_dir
            self.license_file = os.path.join(app_dir, "license.dat")
            self.hwid = hardware_id.generate_hardware_fingerprint()
            logging.debug(f"LicenseManager initialized with hardware ID: {self.hwid}")
            
            # Controlla subito la licenza durante l'inizializzazione
            self.validate_license()
        return self
        
    def _generate_key(self):
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
        
    def _encrypt_data(self, data):
        """Cripta i dati della licenza"""
        f = Fernet(self._generate_key())
        return f.encrypt(json.dumps(data).encode())
    
    def _decrypt_data(self, encrypted_data):
        """Decripta i dati della licenza"""
        try:
            f = Fernet(self._generate_key())
            decrypted = f.decrypt(encrypted_data)
            return json.loads(decrypted.decode())
        except Exception as e:
            logging.debug(f"Error decrypting license data: {str(e)}")
            return None
    
    def create_license(self, license_key, expiry_date=None, features=None, username=""):
        """
        Crea un file di licenza per l'hardware corrente
        
        Args:
            license_key: Chiave di licenza da attivare
            expiry_date: Data di scadenza (YYYY-MM-DD) o None per licenza perpetua
            features: Lista di feature abilitate dalla licenza
            username: Nome dell'utente associato alla licenza
        
        Returns:
            True se la licenza è stata creata con successo, False altrimenti
        """
        if features is None:
            features = ["basic"]
            
        # Crea i dati della licenza
        license_data = {
            "license_key": license_key,
            "hardware_id": self.hwid,
            "creation_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "expiry_date": expiry_date,
            "features": features,
            "username": username
        }
        
        logging.info(f"Creating license with key: {license_key}, features: {features}")
        
        # Cripta i dati
        encrypted_data = self._encrypt_data(license_data)
        
        # Salva su file
        try:
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)
            logging.info("License file created successfully")
            return True
        except Exception as e:
            logging.error(f"Error creating license file: {str(e)}")
            return False
    
    def set_features(self, features):
        """
        Imposta le feature disponibili nella licenza corrente
        
        Args:
            features: Lista di feature abilitate
        """
        self.features = features
        logging.debug(f"Set license features: {features}")

    def check_feature_access(self, feature_name, show_message=True):
        """Controlla se una feature è accessibile con la licenza corrente"""
        # Definisci la gerarchia delle feature
        feature_hierarchy = {
            "basic": ["basic"],
            "pro": ["basic", "pro"],
            "premium": ["basic", "pro", "premium"]
        }
        
        # Logging per debug
        logging.debug(f"Checking access for feature: {feature_name}")
        logging.debug(f"Current features: {self.features}")
        
        # Controlla se l'utente ha accesso alla feature
        has_access = False
        
        # Verifica direttamente se la feature è nella lista
        if feature_name in self.features:
            has_access = True
            logging.debug(f"Direct match: {feature_name} found in {self.features}")
        else:
            # Controlla se l'utente ha una licenza che include implicitamente la feature
            for license_level in self.features:
                if license_level in feature_hierarchy and feature_name in feature_hierarchy[license_level]:
                    has_access = True
                    logging.debug(f"Hierarchical match: {feature_name} included in {license_level}")
                    break
        
        logging.debug(f"Access result for {feature_name}: {has_access}")
        
        if has_access:
            return True
        
        if show_message:
            messagebox.showinfo("Funzionalità non disponibile",
                             f"La funzionalità '{feature_name}' richiede una licenza superiore.\n"
                             f"È possibile acquistare una licenza per sbloccare tutte le funzionalità.")
        return False

    def validate_license(self):
        """
        Verifica se la licenza è valida per questo hardware
        
        Returns:
            (is_valid, message, features, expiry_date, username) dove:
            - is_valid: True se la licenza è valida, False altrimenti
            - message: Messaggio esplicativo
            - features: Lista di feature abilitate dalla licenza (vuota se non valida)
            - expiry_date: Data di scadenza o None se perpetua
            - username: Nome utente associato alla licenza
        """
        # Controlla se il file di licenza esiste
        if not os.path.exists(self.license_file):
            logging.warning("License file not found")
            return False, "Licenza non trovata.", [], None, ""
        
        # Leggi e decripta il file
        try:
            with open(self.license_file, 'rb') as f:
                encrypted_data = f.read()
            license_data = self._decrypt_data(encrypted_data)
            
            if license_data is None:
                logging.warning("Invalid or corrupted license data")
                return False, "Licenza non valida o danneggiata.", [], None, ""
            
            # Verifica che la licenza sia per questo hardware
            stored_hwid = license_data.get("hardware_id", "")
            if stored_hwid != self.hwid:
                # Log degli ID hardware per debug
                logging.warning(f"Hardware ID mismatch: stored={stored_hwid}, current={self.hwid}")
                return False, "Licenza non valida per questo computer.", [], None, ""
            
            # Verifica che la licenza non sia scaduta
            expiry_date = license_data.get("expiry_date")
            if expiry_date:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                if today > expiry_date:
                    logging.warning(f"License expired on {expiry_date}")
                    return False, f"Licenza scaduta il {expiry_date}.", [], expiry_date, license_data.get("username", "")
            
            # Licenza valida!
            features = license_data.get("features", ["basic"])
            username = license_data.get("username", "")
            
            # Salva le feature nell'istanza per facilitare i controlli futuri
            self.features = features
            
            logging.info(f"Valid license found with features: {features}")
            return True, "Licenza valida.", features, expiry_date, username
            
        except Exception as e:
            logging.error(f"Error validating license: {str(e)}")
            return False, f"Errore durante la verifica della licenza: {str(e)}", [], None, ""
    
    def get_hardware_id(self):
        """Restituisce l'ID hardware corrente"""
        return self.hwid
    
    def get_license_info(self):
        """
        Ottiene le informazioni sulla licenza attuale
        
        Returns:
            Dizionario con le informazioni sulla licenza o None se non presente/non valida
        """
        if not os.path.exists(self.license_file):
            return None
        
        try:
            with open(self.license_file, 'rb') as f:
                encrypted_data = f.read()
            return self._decrypt_data(encrypted_data)
        except:
            return None