#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Garmin Planner License Generator

This tool generates license files for Garmin Planner application.
It creates encrypted license files bound to specific hardware IDs.
"""

import os
import sys
import json
import base64
import hashlib
import datetime
import argparse
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Secret key for encryption - this should be kept private and secure
# DO NOT SHARE THIS KEY OR INCLUDE IT IN DISTRIBUTED CODE
SECRET_KEY = b'g4rm1n_p1ann3r_s3cr3t_k3y_2024_v1'

class LicenseGenerator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Garmin Planner License Generator")
        self.geometry("800x900")
        self.resizable(True, True)
        
        # Set window icon if available
        try:
            self.iconbitmap("assets/garmin_planner_icon.ico")
        except:
            pass
        
        self.create_widgets()
        self.center_window()
    
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
            text="Garmin Planner License Generator", 
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_generator_tab(notebook)
        self.create_manager_tab(notebook)
        self.create_batch_tab(notebook)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Footer with copyright and version
        current_year = datetime.now().year
        footer = ttk.Label(main_frame, text=f"© {current_year} Garmin Planner. v1.0")
        footer.pack(pady=(10, 0))
    
    def create_generator_tab(self, notebook):
        """Create the license generator tab"""
        tab = ttk.Frame(notebook, padding="10")
        notebook.add(tab, text="Generate License")
        
        # License information section
        info_frame = ttk.LabelFrame(tab, text="License Information", padding="10")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # License key
        license_frame = ttk.Frame(info_frame)
        license_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(license_frame, text="License Key:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.license_key_var = tk.StringVar()
        license_entry = ttk.Entry(license_frame, textvariable=self.license_key_var, width=40)
        license_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(license_frame, text="Generate Key", command=self.generate_license_key).grid(
            row=0, column=2, padx=5, pady=5)
        
        # Hardware ID
        hw_frame = ttk.Frame(info_frame)
        hw_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(hw_frame, text="Hardware ID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.hardware_id_var = tk.StringVar()
        hw_entry = ttk.Entry(hw_frame, textvariable=self.hardware_id_var, width=40)
        hw_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(hw_frame, text="Paste", command=lambda: self.hardware_id_var.set(
            self.clipboard_get())).grid(row=0, column=2, padx=5, pady=5)
        
        # Username
        user_frame = ttk.Frame(info_frame)
        user_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(user_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.username_var = tk.StringVar()
        ttk.Entry(user_frame, textvariable=self.username_var, width=40).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # License type
        type_frame = ttk.Frame(info_frame)
        type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(type_frame, text="License Type:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.license_type_var = tk.StringVar(value="PRO")
        ttk.Combobox(type_frame, textvariable=self.license_type_var, 
                   values=["BASIC", "PRO", "PREMIUM"], state="readonly", width=15).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Expiration options
        expiry_frame = ttk.LabelFrame(tab, text="License Expiration", padding="10")
        expiry_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Radio buttons for expiration type
        self.expiry_type_var = tk.StringVar(value="days")
        ttk.Radiobutton(expiry_frame, text="Days from now", 
                       variable=self.expiry_type_var, value="days").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        # Days input
        self.days_var = tk.IntVar(value=365)
        ttk.Spinbox(expiry_frame, from_=1, to=3650, textvariable=self.days_var, width=5).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Specific date option
        ttk.Radiobutton(expiry_frame, text="Specific date:", 
                       variable=self.expiry_type_var, value="date").grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        # Date entry (yyyy-mm-dd)
        one_year_later = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        self.expiry_date_var = tk.StringVar(value=one_year_later)
        ttk.Entry(expiry_frame, textvariable=self.expiry_date_var, width=15).grid(
            row=1, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(expiry_frame, text="(YYYY-MM-DD)").grid(
            row=1, column=2, padx=5, pady=5, sticky=tk.W)
        
        # Perpetual license option
        ttk.Radiobutton(expiry_frame, text="Perpetual license (never expires)", 
                       variable=self.expiry_type_var, value="perpetual").grid(
            row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)
        
        # Features section
        features_frame = ttk.LabelFrame(tab, text="Enabled Features", padding="10")
        features_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Feature checkboxes
        self.feature_basic = tk.BooleanVar(value=True)
        ttk.Checkbutton(features_frame, text="Basic features", 
                       variable=self.feature_basic, state="disabled").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.feature_pro = tk.BooleanVar(value=True)
        ttk.Checkbutton(features_frame, text="Pro features", 
                       variable=self.feature_pro).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.feature_excel = tk.BooleanVar(value=True)
        ttk.Checkbutton(features_frame, text="Excel tools", 
                       variable=self.feature_excel).grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.feature_scheduling = tk.BooleanVar(value=True)
        ttk.Checkbutton(features_frame, text="Scheduling", 
                       variable=self.feature_scheduling).grid(
            row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.feature_premium = tk.BooleanVar(value=False)
        ttk.Checkbutton(features_frame, text="Premium features", 
                       variable=self.feature_premium).grid(
            row=2, column=0, padx=5, pady=5, sticky=tk.W)
        
        # Output section
        output_frame = ttk.LabelFrame(tab, text="License Output", padding="10")
        output_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Output file path
        file_frame = ttk.Frame(output_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="Save to:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.output_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "license.dat"))
        ttk.Entry(file_frame, textvariable=self.output_path_var, width=60).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(file_frame, text="Browse...", command=self.browse_output).grid(
            row=0, column=2, padx=5, pady=5)
        
        # Action buttons
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(button_frame, text="Generate License", command=self.generate_license,
                 style="Accent.TButton", width=20).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Preview License", command=self.preview_license,
                 width=20).pack(side=tk.RIGHT, padx=5)
    
    def create_manager_tab(self, notebook):
        """Create the license management tab"""
        tab = ttk.Frame(notebook, padding="10")
        notebook.add(tab, text="Manage Licenses")
        
        # License file selection
        file_frame = ttk.LabelFrame(tab, text="License File", padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame, text="License File:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.license_file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.license_file_var, width=60).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(file_frame, text="Browse...", command=self.browse_license_file).grid(
            row=0, column=2, padx=5, pady=5)
        
        # License details section
        details_frame = ttk.LabelFrame(tab, text="License Details", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        # Text widget for displaying license details
        self.details_text = tk.Text(details_frame, height=20, width=80, wrap=tk.WORD)
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for the text widget
        scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.config(yscrollcommand=scrollbar.set)
        
        # Action buttons
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(button_frame, text="Verify License", command=self.verify_license,
                 style="Accent.TButton", width=20).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Extend License", command=self.extend_license,
                 width=20).pack(side=tk.RIGHT, padx=5)
    
    def create_batch_tab(self, notebook):
        """Create the batch license generation tab"""
        tab = ttk.Frame(notebook, padding="10")
        notebook.add(tab, text="Batch Generation")
        
        # Input file selection
        input_frame = ttk.LabelFrame(tab, text="Input File (CSV)", padding="10")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(input_frame, text="CSV File:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.csv_file_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.csv_file_var, width=60).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(input_frame, text="Browse...", command=self.browse_csv_file).grid(
            row=0, column=2, padx=5, pady=5)
        
        # CSV format info
        format_text = """CSV file format:
hardware_id,username,license_type,expiry_date,features

Example:
a1b2c3d4e5f6g7h8,John Doe,PRO,2025-12-31,basic;pro;excel_tools;scheduling
i9j0k1l2m3n4o5p6,Jane Smith,PREMIUM,,basic;pro;excel_tools;scheduling;premium
        """
        ttk.Label(input_frame, text=format_text, justify=tk.LEFT).grid(
            row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)
        
        # Output directory selection
        output_frame = ttk.LabelFrame(tab, text="Output Directory", padding="10")
        output_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Label(output_frame, text="Save to:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.output_dir_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(output_frame, textvariable=self.output_dir_var, width=60).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(output_frame, text="Browse...", command=self.browse_output_dir).grid(
            row=0, column=2, padx=5, pady=5)
        
        # Filename template
        ttk.Label(output_frame, text="Filename pattern:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.filename_pattern_var = tk.StringVar(value="license_{username}.dat")
        ttk.Entry(output_frame, textvariable=self.filename_pattern_var, width=40).grid(
            row=1, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(output_frame, text="{username}, {license_type}, and {hardware_id} will be replaced").grid(
            row=2, column=0, columnspan=3, padx=5, pady=0, sticky=tk.W)
        
        # Log area
        log_frame = ttk.LabelFrame(tab, text="Generation Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        # Text widget for displaying log
        self.log_text = tk.Text(log_frame, height=15, width=80, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for the text widget
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Action buttons
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(button_frame, text="Generate Batch", command=self.generate_batch,
                 style="Accent.TButton", width=20).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Create Sample CSV", command=self.create_sample_csv,
                 width=20).pack(side=tk.RIGHT, padx=5)
    
    def _generate_key(self):
        """Generate a cryptographic key based on the secret key"""
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
        """Encrypt license data"""
        f = Fernet(self._generate_key())
        return f.encrypt(json.dumps(data).encode())
    
    def _decrypt_data(self, encrypted_data):
        """Decrypt license data"""
        try:
            f = Fernet(self._generate_key())
            decrypted = f.decrypt(encrypted_data)
            return json.loads(decrypted.decode())
        except Exception as e:
            self.log_to_ui(f"Error decrypting license data: {str(e)}")
            return None
    
    def generate_license_key(self):
        """Generate a unique license key"""
        license_type = self.license_type_var.get()
        current_year = datetime.now().year
        
        # Generate a unique identifier
        unique_id = os.urandom(4).hex().upper()
        
        # Create a random code part
        random_code = os.urandom(4).hex().upper()
        
        # Format: GPLNR-XXXX-YYYY-TYPE-RANDOMCODE
        license_key = f"GPLNR-{unique_id}-{current_year}-{license_type}-{random_code}"
        
        self.license_key_var.set(license_key)
        self.status_var.set(f"Generated license key: {license_key}")
    
    def get_expiry_date(self):
        """Get the expiry date based on user selection"""
        expiry_type = self.expiry_type_var.get()
        
        if expiry_type == "perpetual":
            return None
        elif expiry_type == "days":
            days = self.days_var.get()
            expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
            return expiry_date
        else:  # specific date
            try:
                # Validate date format
                expiry_date = self.expiry_date_var.get()
                datetime.strptime(expiry_date, "%Y-%m-%d")
                return expiry_date
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD")
                return None
    
    def get_features(self):
        """Get the enabled features list"""
        features = []
        
        if self.feature_basic.get():
            features.append("basic")
        
        if self.feature_pro.get():
            features.append("pro")
        
        if self.feature_excel.get():
            features.append("excel_tools")
        
        if self.feature_scheduling.get():
            features.append("scheduling")
        
        if self.feature_premium.get():
            features.append("premium")
        
        return features
    
    def preview_license(self):
        """Preview the license that would be generated"""
        # Get hardware ID
        hardware_id = self.hardware_id_var.get().strip()
        if not hardware_id:
            messagebox.showerror("Error", "Hardware ID is required")
            return
        
        # Get username
        username = self.username_var.get().strip()
        
        # Get license key
        license_key = self.license_key_var.get().strip()
        if not license_key:
            messagebox.showerror("Error", "License key is required")
            return
        
        # Get expiry date
        expiry_date = self.get_expiry_date()
        if expiry_date is False:  # Error in date format
            return
        
        # Get features
        features = self.get_features()
        
        # Create license data
        license_data = {
            "license_key": license_key,
            "hardware_id": hardware_id,
            "creation_date": datetime.now().strftime("%Y-%m-%d"),
            "expiry_date": expiry_date,
            "features": features,
            "username": username
        }
        
        # Display preview
        preview_text = json.dumps(license_data, indent=2)
        
        # Show in message box
        dialog = tk.Toplevel(self)
        dialog.title("License Preview")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Make the dialog modal
        dialog.focus_set()
        
        # Create text widget
        text = tk.Text(dialog, wrap=tk.WORD)
        text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(text, orient=tk.VERTICAL, command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.config(yscrollcommand=scrollbar.set)
        
        # Insert text
        text.insert(tk.END, preview_text)
        
        # Make text readonly
        text.config(state=tk.DISABLED)
        
        # Add close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
        
        self.status_var.set("License preview generated")
    
    def generate_license(self):
        """Generate the license file"""
        # Get hardware ID
        hardware_id = self.hardware_id_var.get().strip()
        if not hardware_id:
            messagebox.showerror("Error", "Hardware ID is required")
            return
        
        # Get username
        username = self.username_var.get().strip()
        
        # Get license key
        license_key = self.license_key_var.get().strip()
        if not license_key:
            messagebox.showerror("Error", "License key is required")
            return
        
        # Get expiry date
        expiry_date = self.get_expiry_date()
        if expiry_date is False:  # Error in date format
            return
        
        # Get features
        features = self.get_features()
        
        # Get output path
        output_path = self.output_path_var.get().strip()
        if not output_path:
            messagebox.showerror("Error", "Output file path is required")
            return
        
        # Create license data
        license_data = {
            "license_key": license_key,
            "hardware_id": hardware_id,
            "creation_date": datetime.now().strftime("%Y-%m-%d"),
            "expiry_date": expiry_date,
            "features": features,
            "username": username
        }
        
        # Encrypt the data
        encrypted_data = self._encrypt_data(license_data)
        
        # Save to file
        try:
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            self.status_var.set(f"License file saved to {output_path}")
            messagebox.showinfo("Success", f"License file generated successfully:\n{output_path}")
        except Exception as e:
            self.status_var.set(f"Error saving license file: {str(e)}")
            messagebox.showerror("Error", f"Failed to save license file:\n{str(e)}")
    
    def verify_license(self):
        """Verify a license file and display its contents"""
        # Get license file path
        license_file = self.license_file_var.get().strip()
        if not license_file:
            messagebox.showerror("Error", "Please select a license file to verify")
            return
        
        if not os.path.isfile(license_file):
            messagebox.showerror("Error", f"License file not found: {license_file}")
            return
        
        try:
            # Read and decrypt the license file
            with open(license_file, 'rb') as f:
                encrypted_data = f.read()
            
            license_data = self._decrypt_data(encrypted_data)
            
            if license_data is None:
                self.details_text.delete(1.0, tk.END)
                self.details_text.insert(tk.END, "Invalid or corrupted license file.")
                self.status_var.set("License verification failed: Invalid or corrupted file")
                return
            
            # Check license expiration
            expiry_date = license_data.get("expiry_date")
            if expiry_date:
                today = datetime.now().strftime("%Y-%m-%d")
                if today > expiry_date:
                    status = f"⚠️ This license has EXPIRED on {expiry_date}"
                else:
                    # Calculate days left
                    expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
                    today_date = datetime.now()
                    days_left = (expiry - today_date).days
                    status = f"✓ Valid license, expires in {days_left} days ({expiry_date})"
            else:
                status = "✓ Valid perpetual license (never expires)"
            
            # Format license data for display
            display_text = f"LICENSE STATUS: {status}\n\n"
            display_text += "LICENSE DETAILS:\n"
            display_text += f"License Key: {license_data.get('license_key', 'N/A')}\n"
            display_text += f"Username: {license_data.get('username', 'N/A')}\n"
            display_text += f"Hardware ID: {license_data.get('hardware_id', 'N/A')}\n"
            display_text += f"Created: {license_data.get('creation_date', 'N/A')}\n"
            display_text += f"Expires: {expiry_date if expiry_date else 'Never'}\n"
            display_text += f"Features: {', '.join(license_data.get('features', []))}\n\n"
            
            # Add raw data for debugging
            display_text += "RAW LICENSE DATA:\n"
            display_text += json.dumps(license_data, indent=2)
            
            # Display in text widget
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, display_text)
            
            self.status_var.set("License verified successfully")
            
        except Exception as e:
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"Error verifying license: {str(e)}")
            self.status_var.set(f"License verification failed: {str(e)}")
    
    def extend_license(self):
        """Extend an existing license file"""
        # Get license file path
        license_file = self.license_file_var.get().strip()
        if not license_file:
            messagebox.showerror("Error", "Please select a license file to extend")
            return
        
        if not os.path.isfile(license_file):
            messagebox.showerror("Error", f"License file not found: {license_file}")
            return
        
        try:
            # Read and decrypt the license file
            with open(license_file, 'rb') as f:
                encrypted_data = f.read()
            
            license_data = self._decrypt_data(encrypted_data)
            
            if license_data is None:
                messagebox.showerror("Error", "Invalid or corrupted license file")
                return
            
            # Ask user for the new expiry date
            dialog = tk.Toplevel(self)
            dialog.title("Extend License")
            dialog.geometry("400x250")
            dialog.transient(self)
            dialog.grab_set()
            
            # Current expiration info
            current_expiry = license_data.get("expiry_date", "Perpetual")
            ttk.Label(dialog, text=f"Current expiration: {current_expiry}").pack(pady=(20, 10))
            
            # Extension options
            extension_frame = ttk.LabelFrame(dialog, text="New Expiration", padding="10")
            extension_frame.pack(fill=tk.X, padx=20, pady=10)
            
            # Radio buttons for extension type
            extension_type = tk.StringVar(value="add_days")
            ttk.Radiobutton(extension_frame, text="Add days to current expiration:", 
                           variable=extension_type, value="add_days").grid(
                row=0, column=0, padx=5, pady=5, sticky=tk.W)
            
            # Days input
            days_var = tk.IntVar(value=365)
            ttk.Spinbox(extension_frame, from_=1, to=3650, textvariable=days_var, width=5).grid(
                row=0, column=1, padx=5, pady=5, sticky=tk.W)
            
            # Specific date option
            ttk.Radiobutton(extension_frame, text="Set new expiration date:", 
                           variable=extension_type, value="new_date").grid(
                row=1, column=0, padx=5, pady=5, sticky=tk.W)
            
            # Date entry (yyyy-mm-dd)
            one_year_later = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
            new_date_var = tk.StringVar(value=one_year_later)
            ttk.Entry(extension_frame, textvariable=new_date_var, width=15).grid(
                row=1, column=1, padx=5, pady=5, sticky=tk.W)
            
            # Perpetual license option
            ttk.Radiobutton(extension_frame, text="Convert to perpetual license", 
                           variable=extension_type, value="perpetual").grid(
                row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
            
            # Button frame
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill=tk.X, padx=20, pady=20)
            
            # Function to handle extension
            def do_extension():
                try:
                    ext_type = extension_type.get()
                    
                    if ext_type == "add_days":
                        days_to_add = days_var.get()
                        if license_data.get("expiry_date"):
                            current_date = datetime.strptime(license_data["expiry_date"], "%Y-%m-%d")
                            new_expiry = (current_date + timedelta(days=days_to_add)).strftime("%Y-%m-%d")
                        else:
                            # If it was perpetual, start from today
                            new_expiry = (datetime.now() + timedelta(days=days_to_add)).strftime("%Y-%m-%d")
                        
                        license_data["expiry_date"] = new_expiry
                        
                    elif ext_type == "new_date":
                        try:
                            # Validate date format
                            new_date = new_date_var.get()
                            datetime.strptime(new_date, "%Y-%m-%d")
                            license_data["expiry_date"] = new_date
                        except ValueError:
                            messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD", parent=dialog)
                            return
                            
                    elif ext_type == "perpetual":
                        license_data["expiry_date"] = None
                    
                    # Update the creation date to today
                    license_data["creation_date"] = datetime.now().strftime("%Y-%m-%d")
                    
                    # Encrypt and save the updated license
                    encrypted_data = self._encrypt_data(license_data)
                    
                    with open(license_file, 'wb') as f:
                        f.write(encrypted_data)
                    
                    messagebox.showinfo("Success", "License extended successfully", parent=dialog)
                    dialog.destroy()
                    
                    # Refresh the license details display
                    self.verify_license()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to extend license: {str(e)}", parent=dialog)
            
            # Buttons
            ttk.Button(button_frame, text="Extend License", command=do_extension).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error reading license file: {str(e)}")
    
    def generate_batch(self):
        """Generate batch of licenses from CSV file"""
        # Get CSV file path
        csv_file = self.csv_file_var.get().strip()
        if not csv_file:
            messagebox.showerror("Error", "Please select a CSV file")
            return
        
        if not os.path.isfile(csv_file):
            messagebox.showerror("Error", f"CSV file not found: {csv_file}")
            return
        
        # Get output directory
        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            messagebox.showerror("Error", "Please specify an output directory")
            return
        
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output directory: {str(e)}")
                return
        
        # Get filename pattern
        filename_pattern = self.filename_pattern_var.get().strip()
        if not filename_pattern:
            messagebox.showerror("Error", "Please specify a filename pattern")
            return
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        try:
            import csv
            
            # Read CSV file
            with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)  # Skip header row
                
                success_count = 0
                error_count = 0
                
                for row_idx, row in enumerate(reader, 1):
                    try:
                        if len(row) < 3:
                            self.log_to_ui(f"Row {row_idx}: Insufficient columns, skipping")
                            error_count += 1
                            continue
                        
                        hardware_id = row[0].strip()
                        username = row[1].strip() if len(row) > 1 else ""
                        license_type = row[2].strip() if len(row) > 2 else "BASIC"
                        expiry_date = row[3].strip() if len(row) > 3 else None
                        
                        # Parse features
                        features = ["basic"]
                        if len(row) > 4 and row[4].strip():
                            additional_features = [f.strip() for f in row[4].split(';')]
                            features.extend([f for f in additional_features if f])
                        
                        # Generate license key if not in CSV
                        license_key = f"GPLNR-{os.urandom(4).hex().upper()}-{datetime.now().year}-{license_type}-{os.urandom(4).hex().upper()}"
                        
                        # Create license data
                        license_data = {
                            "license_key": license_key,
                            "hardware_id": hardware_id,
                            "creation_date": datetime.now().strftime("%Y-%m-%d"),
                            "expiry_date": expiry_date if expiry_date else None,
                            "features": features,
                            "username": username
                        }
                        
                        # Format filename from pattern
                        safe_username = ''.join(c if c.isalnum() else '_' for c in username)
                        filename = filename_pattern.format(
                            username=safe_username,
                            license_type=license_type.lower(),
                            hardware_id=hardware_id
                        )
                        
                        output_path = os.path.join(output_dir, filename)
                        
                        # Encrypt the data
                        encrypted_data = self._encrypt_data(license_data)
                        
                        # Save to file
                        with open(output_path, 'wb') as f:
                            f.write(encrypted_data)
                        
                        self.log_to_ui(f"Row {row_idx}: Generated license for {username} ({hardware_id})")
                        success_count += 1
                        
                    except Exception as e:
                        self.log_to_ui(f"Row {row_idx}: Error - {str(e)}")
                        error_count += 1
                
                summary = f"\nBatch generation completed:\n"
                summary += f"- Successfully generated: {success_count} licenses\n"
                summary += f"- Errors: {error_count}\n"
                summary += f"- Output directory: {output_dir}"
                
                self.log_to_ui(summary)
                self.status_var.set(f"Batch generation completed: {success_count} successes, {error_count} errors")
                
                if success_count > 0:
                    messagebox.showinfo("Success", f"Generated {success_count} licenses with {error_count} errors.\nOutput directory: {output_dir}")
                else:
                    messagebox.showerror("Error", "No licenses were generated successfully.")
                
        except Exception as e:
            self.log_to_ui(f"Error processing CSV file: {str(e)}")
            self.status_var.set(f"Batch generation failed: {str(e)}")
            messagebox.showerror("Error", f"Failed to process CSV file: {str(e)}")
    
    def create_sample_csv(self):
        """Create a sample CSV file"""
        output_file = filedialog.asksaveasfilename(
            title="Save Sample CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            defaultextension=".csv"
        )
        
        if not output_file:
            return
        
        try:
            import csv
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["hardware_id", "username", "license_type", "expiry_date", "features"])
                writer.writerow(["abcdef1234567890", "John Doe", "PRO", 
                               (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"), 
                               "basic;pro;excel_tools;scheduling"])
                writer.writerow(["fedcba0987654321", "Jane Smith", "PREMIUM", 
                               "", "basic;pro;excel_tools;scheduling;premium"])
                writer.writerow(["12345abcdef67890", "Bob Johnson", "BASIC", 
                               (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"), 
                               "basic"])
            
            self.status_var.set(f"Sample CSV file created: {output_file}")
            messagebox.showinfo("Success", f"Sample CSV file created:\n{output_file}")
            
            # Set the CSV file path
            self.csv_file_var.set(output_file)
            
        except Exception as e:
            self.status_var.set(f"Error creating sample CSV: {str(e)}")
            messagebox.showerror("Error", f"Failed to create sample CSV: {str(e)}")
    
    def log_to_ui(self, message):
        """Add a message to the log text area"""
        # Get current timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Append message to log
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)  # Scroll to end
        
        # Update the UI
        self.update_idletasks()
    
    def browse_output(self):
        """Browse for output file location"""
        filename = filedialog.asksaveasfilename(
            title="Save License File As",
            filetypes=[("License files", "*.dat"), ("All files", "*.*")],
            defaultextension=".dat"
        )
        if filename:
            self.output_path_var.set(filename)
    
    def browse_license_file(self):
        """Browse for license file"""
        filename = filedialog.askopenfilename(
            title="Select License File",
            filetypes=[("License files", "*.dat"), ("All files", "*.*")]
        )
        if filename:
            self.license_file_var.set(filename)
            # Automatically verify the license
            self.verify_license()
    
    def browse_csv_file(self):
        """Browse for CSV file"""
        filename = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.csv_file_var.set(filename)
    
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(
            title="Select Output Directory"
        )
        if directory:
            self.output_dir_var.set(directory)

def main():
    app = LicenseGenerator()
    
    # Configure style
    style = ttk.Style()
    style.configure("Accent.TButton", 
                  background="#0076c0",  # Garmin blue
                  foreground="white")
    
    app.mainloop()

if __name__ == "__main__":
    main()