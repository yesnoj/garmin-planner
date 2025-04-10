#!/usr/bin/env python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import yaml
import os
import re
import logging
from copy import deepcopy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WorkoutEditorGUI")

class WorkoutEditor(tk.Toplevel):
    def __init__(self, parent, file_path=None):
        super().__init__(parent)
        
        self.parent = parent
        self.file_path = file_path
        
        self.title("Workout Editor")
        self.geometry("1000x800")
        
        # Set up variables
        self.workout_data = {
            'config': {
                'heart_rates': {},
                'paces': {},
                'margins': {
                    'faster': '0:03',
                    'slower': '0:03',
                    'hr_up': 5,
                    'hr_down': 5
                },
                'name_prefix': ''
            }
        }
        
        # Create the UI
        self.create_menu()
        self.create_layout()
        
        # If a file path was provided, load the file
        if file_path and os.path.exists(file_path):
            self.load_file(file_path)

    def create_menu(self):
        """Create menu bar"""
        self.menu_bar = tk.Menu(self)
        
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="New", command=self.new_workout_file)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self.destroy)
        
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        edit_menu.add_command(label="Add Pace", command=lambda: self.add_config_item('paces'))
        edit_menu.add_command(label="Add Heart Rate", command=lambda: self.add_config_item('heart_rates'))
        edit_menu.add_command(label="Edit Margins", command=self.edit_margins)
        edit_menu.add_command(label="Set Name Prefix", command=self.set_name_prefix)
        
        workout_menu = tk.Menu(self.menu_bar, tearoff=0)
        workout_menu.add_command(label="Add Workout", command=self.add_workout)
        workout_menu.add_command(label="Clone Selected Workout", command=self.clone_workout)
        workout_menu.add_command(label="Delete Selected Workout", command=self.delete_workout)
        
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)
        self.menu_bar.add_cascade(label="Workout", menu=workout_menu)
        
        self.config(menu=self.menu_bar)

    def create_layout(self):
        """Create the main layout"""
        # Main frame to hold everything
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top frame for configuration
        self.config_frame = ttk.LabelFrame(main_frame, text="Configuration")
        self.config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create notebook for config tabs
        config_notebook = ttk.Notebook(self.config_frame)
        config_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Paces tab
        paces_frame = ttk.Frame(config_notebook)
        config_notebook.add(paces_frame, text="Paces")
        
        # Heart rates tab
        hr_frame = ttk.Frame(config_notebook)
        config_notebook.add(hr_frame, text="Heart Rates")
        
        # Margins tab
        margins_frame = ttk.Frame(config_notebook)
        config_notebook.add(margins_frame, text="Margins")
        
        # Paces treeview
        self.paces_tree = ttk.Treeview(paces_frame, columns=("name", "value"), show="headings")
        self.paces_tree.heading("name", text="Name")
        self.paces_tree.heading("value", text="Value")
        self.paces_tree.column("name", width=150)
        self.paces_tree.column("value", width=300)
        self.paces_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        paces_buttons_frame = ttk.Frame(paces_frame)
        paces_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(paces_buttons_frame, text="Add", command=lambda: self.add_config_item('paces')).pack(side=tk.LEFT, padx=5)
        ttk.Button(paces_buttons_frame, text="Edit", command=lambda: self.edit_config_item('paces')).pack(side=tk.LEFT, padx=5)
        ttk.Button(paces_buttons_frame, text="Delete", command=lambda: self.delete_config_item('paces')).pack(side=tk.LEFT, padx=5)
        
        # Heart rates treeview
        self.hr_tree = ttk.Treeview(hr_frame, columns=("name", "value"), show="headings")
        self.hr_tree.heading("name", text="Name")
        self.hr_tree.heading("value", text="Value")
        self.hr_tree.column("name", width=150)
        self.hr_tree.column("value", width=300)
        self.hr_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        hr_buttons_frame = ttk.Frame(hr_frame)
        hr_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(hr_buttons_frame, text="Add", command=lambda: self.add_config_item('heart_rates')).pack(side=tk.LEFT, padx=5)
        ttk.Button(hr_buttons_frame, text="Edit", command=lambda: self.edit_config_item('heart_rates')).pack(side=tk.LEFT, padx=5)
        ttk.Button(hr_buttons_frame, text="Delete", command=lambda: self.delete_config_item('heart_rates')).pack(side=tk.LEFT, padx=5)
        
        # Margins frame
        margins_grid = ttk.Frame(margins_frame)
        margins_grid.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(margins_grid, text="Faster:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.faster_var = tk.StringVar(value="0:03")
        ttk.Entry(margins_grid, textvariable=self.faster_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(margins_grid, text="Slower:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.slower_var = tk.StringVar(value="0:03")
        ttk.Entry(margins_grid, textvariable=self.slower_var, width=10).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(margins_grid, text="HR Up (%):").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.hr_up_var = tk.IntVar(value=5)
        ttk.Entry(margins_grid, textvariable=self.hr_up_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(margins_grid, text="HR Down (%):").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.hr_down_var = tk.IntVar(value=5)
        ttk.Entry(margins_grid, textvariable=self.hr_down_var, width=10).grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(margins_grid, text="Name Prefix:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.name_prefix_var = tk.StringVar(value="")
        ttk.Entry(margins_grid, textvariable=self.name_prefix_var, width=40).grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(margins_grid, text="Apply Changes", command=self.apply_margins).grid(row=3, column=0, columnspan=4, padx=5, pady=5)
        
        # Middle frame for workouts list
        workouts_frame = ttk.LabelFrame(main_frame, text="Workouts")
        workouts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a frame for the workout list and search
        workout_list_frame = ttk.Frame(workouts_frame)
        workout_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Search box
        search_frame = ttk.Frame(workout_list_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_workouts)
        ttk.Entry(search_frame, textvariable=self.search_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Workouts treeview
        self.workouts_tree = ttk.Treeview(workout_list_frame, columns=("name", "description"), show="headings")
        self.workouts_tree.heading("name", text="Name")
        self.workouts_tree.heading("description", text="Description")
        self.workouts_tree.column("name", width=200)
        self.workouts_tree.column("description", width=400)
        self.workouts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        workouts_scrollbar = ttk.Scrollbar(workout_list_frame, orient="vertical", command=self.workouts_tree.yview)
        workouts_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.workouts_tree.configure(yscrollcommand=workouts_scrollbar.set)
        
        # Buttons for workouts
        workouts_buttons_frame = ttk.Frame(workouts_frame)
        workouts_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(workouts_buttons_frame, text="Add Workout", command=self.add_workout).pack(side=tk.LEFT, padx=5)
        ttk.Button(workouts_buttons_frame, text="Clone Workout", command=self.clone_workout).pack(side=tk.LEFT, padx=5)
        ttk.Button(workouts_buttons_frame, text="Delete Workout", command=self.delete_workout).pack(side=tk.LEFT, padx=5)
        ttk.Button(workouts_buttons_frame, text="Edit Workout", command=self.edit_workout).pack(side=tk.LEFT, padx=5)
        
        # Bottom frame for workout details (steps)
        self.workout_details_frame = ttk.LabelFrame(main_frame, text="Workout Details")
        self.workout_details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # YAML preview at the bottom
        self.yaml_frame = ttk.LabelFrame(main_frame, text="YAML Preview")
        self.yaml_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.yaml_text = tk.Text(self.yaml_frame, wrap=tk.WORD, height=10)
        self.yaml_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bottom buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(buttons_frame, text="Update Preview", command=self.update_yaml_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Bind events
        self.workouts_tree.bind("<Double-1>", lambda e: self.edit_workout())
        self.workouts_tree.bind("<<TreeviewSelect>>", self.on_workout_selected)
        
        # Initialize the UI with data
        self.update_ui_from_data()

    def update_ui_from_data(self):
        """Update the UI with the current data"""
        # Clear existing items
        self.paces_tree.delete(*self.paces_tree.get_children())
        self.hr_tree.delete(*self.hr_tree.get_children())
        self.workouts_tree.delete(*self.workouts_tree.get_children())
        
        # Fill paces tree
        for name, value in self.workout_data.get('config', {}).get('paces', {}).items():
            self.paces_tree.insert('', 'end', values=(name, value))
            
        # Fill heart rates tree
        for name, value in self.workout_data.get('config', {}).get('heart_rates', {}).items():
            self.hr_tree.insert('', 'end', values=(name, value))
            
        # Update margins variables
        margins = self.workout_data.get('config', {}).get('margins', {})
        self.faster_var.set(margins.get('faster', '0:03'))
        self.slower_var.set(margins.get('slower', '0:03'))
        self.hr_up_var.set(margins.get('hr_up', 5))
        self.hr_down_var.set(margins.get('hr_down', 5))
        
        # Update name prefix
        self.name_prefix_var.set(self.workout_data.get('config', {}).get('name_prefix', ''))
        
        # Fill workouts tree
        for name, workout in self.workout_data.items():
            if name != 'config':
                # Extract description from comments (if any)
                description = ""
                if isinstance(workout, str) and "#" in workout:
                    description = workout.split("#", 1)[1].strip()
                self.workouts_tree.insert('', 'end', values=(name, description))
        
        # Update YAML preview
        self.update_yaml_preview()

    def apply_margins(self):
        """Apply the margin values from the UI to the data"""
        margins = self.workout_data.get('config', {}).get('margins', {})
        margins['faster'] = self.faster_var.get()
        margins['slower'] = self.slower_var.get()
        margins['hr_up'] = self.hr_up_var.get()
        margins['hr_down'] = self.hr_down_var.get()
        
        # Update name prefix
        self.workout_data['config']['name_prefix'] = self.name_prefix_var.get()
        
        # Update YAML preview
        self.update_yaml_preview()

    def filter_workouts(self, *args):
        """Filter the workout list based on search text"""
        search_text = self.search_var.get().lower()
        
        # Clear the treeview
        self.workouts_tree.delete(*self.workouts_tree.get_children())
        
        # Add workouts that match the filter
        for name, workout in self.workout_data.items():
            if name != 'config' and search_text in name.lower():
                # Extract description from comments (if any)
                description = ""
                if isinstance(workout, str) and "#" in workout:
                    description = workout.split("#", 1)[1].strip()
                self.workouts_tree.insert('', 'end', values=(name, description))

    def on_workout_selected(self, event):
        """Handle workout selection"""
        pass  # Will be implemented to show the workout steps

    def add_config_item(self, config_type):
        """Add a new pace or heart rate to the configuration"""
        # Create a dialog to get name and value
        dialog = ConfigItemDialog(self, "Add " + config_type.replace('_', ' ').title())
        
        if dialog.result:
            name, value = dialog.result
            
            # Add to data structure
            if config_type not in self.workout_data['config']:
                self.workout_data['config'][config_type] = {}
            
            self.workout_data['config'][config_type][name] = value
            
            # Update UI
            self.update_ui_from_data()

    def edit_config_item(self, config_type):
        """Edit a selected pace or heart rate"""
        # Get the selected item
        tree = self.paces_tree if config_type == 'paces' else self.hr_tree
        selection = tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", f"Please select a {config_type} item to edit.")
            return
            
        item = tree.item(selection[0])
        name, value = item['values']
        
        # Create a dialog with the current values
        dialog = ConfigItemDialog(self, "Edit " + config_type.replace('_', ' ').title(), 
                                 name, value)
        
        if dialog.result:
            new_name, new_value = dialog.result
            
            # Update data structure
            # Remove old key if name changed
            if new_name != name:
                del self.workout_data['config'][config_type][name]
                
            # Add new value
            self.workout_data['config'][config_type][new_name] = new_value
            
            # Update UI
            self.update_ui_from_data()

    def delete_config_item(self, config_type):
        """Delete a selected pace or heart rate"""
        # Get the selected item
        tree = self.paces_tree if config_type == 'paces' else self.hr_tree
        selection = tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", f"Please select a {config_type} item to delete.")
            return
            
        item = tree.item(selection[0])
        name = item['values'][0]
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {name}?"):
            # Delete from data structure
            del self.workout_data['config'][config_type][name]
            
            # Update UI
            self.update_ui_from_data()

    def edit_margins(self):
        """Edit the margins in the config"""
        # Switch to the margins tab
        self.config_frame.select(2)  # Index 2 is the margins tab

    def set_name_prefix(self):
        """Set the name prefix for workouts"""
        # Create a simple dialog
        prefix = simpledialog.askstring("Set Name Prefix", 
                                      "Enter the name prefix for workouts:",
                                      initialvalue=self.workout_data.get('config', {}).get('name_prefix', ''))
        
        if prefix is not None:  # None means cancel was pressed
            self.workout_data['config']['name_prefix'] = prefix
            self.name_prefix_var.set(prefix)
            self.update_yaml_preview()

    def add_workout(self):
        """Add a new workout"""
        # Create a dialog to get the workout name
        name = simpledialog.askstring("New Workout", "Enter workout name (format: W##S## Description):")
        
        if not name:
            return
            
        # Validate the format (W01S01 Workout Name)
        if not re.match(r'^W\d{2}S\d{2}\s+.+', name):
            messagebox.showerror("Invalid Format", "Workout name must be in the format 'W##S## Description'")
            return
            
        # Check if workout already exists
        if name in self.workout_data:
            messagebox.showerror("Duplicate", f"A workout named '{name}' already exists.")
            return
            
        # Create a new empty workout
        self.workout_data[name] = []
        
        # Update UI
        self.update_ui_from_data()
        
        # Edit the new workout
        self.edit_workout(name)

    def clone_workout(self):
        """Clone the selected workout"""
        selection = self.workouts_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a workout to clone.")
            return
            
        item = self.workouts_tree.item(selection[0])
        original_name = item['values'][0]
        
        # Ask for the new name
        new_name = simpledialog.askstring("Clone Workout", 
                                         "Enter new workout name (format: W##S## Description):",
                                         initialvalue=original_name)
        
        if not new_name:
            return
            
        # Validate the format
        if not re.match(r'^W\d{2}S\d{2}\s+.+', new_name):
            messagebox.showerror("Invalid Format", "Workout name must be in the format 'W##S## Description'")
            return
            
        # Check if workout already exists
        if new_name in self.workout_data:
            messagebox.showerror("Duplicate", f"A workout named '{new_name}' already exists.")
            return
            
        # Clone the workout
        self.workout_data[new_name] = deepcopy(self.workout_data[original_name])
        
        # Update UI
        self.update_ui_from_data()

    def delete_workout(self):
        """Delete the selected workout"""
        selection = self.workouts_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a workout to delete.")
            return
            
        item = self.workouts_tree.item(selection[0])
        name = item['values'][0]
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {name}?"):
            # Delete from data structure
            del self.workout_data[name]
            
            # Update UI
            self.update_ui_from_data()

    def edit_workout(self, workout_name=None):
        """Edit the selected workout"""
        if not workout_name:
            selection = self.workouts_tree.selection()
            
            if not selection:
                messagebox.showwarning("No Selection", "Please select a workout to edit.")
                return
                
            item = self.workouts_tree.item(selection[0])
            workout_name = item['values'][0]
        
        # Open the workout editor dialog
        editor = WorkoutStepsEditor(self, workout_name, self.workout_data)
        
        # Update UI after editing
        self.update_ui_from_data()

    def new_workout_file(self):
        """Create a new workout file"""
        # Confirm if there are unsaved changes
        if messagebox.askyesno("New File", "Create a new workout file? Unsaved changes will be lost."):
            # Reset the data structure
            self.workout_data = {
                'config': {
                    'heart_rates': {},
                    'paces': {},
                    'margins': {
                        'faster': '0:03',
                        'slower': '0:03',
                        'hr_up': 5,
                        'hr_down': 5
                    },
                    'name_prefix': ''
                }
            }
            
            # Reset the file path
            self.file_path = None
            
            # Update UI
            self.update_ui_from_data()

    def open_file(self):
        """Open a workout file"""
        file_path = filedialog.askopenfilename(
            title="Open Workout File",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        """Load a workout file"""
        try:
            with open(file_path, 'r') as file:
                self.workout_data = yaml.safe_load(file)
                
                # Ensure the config section exists
                if 'config' not in self.workout_data:
                    self.workout_data['config'] = {
                        'heart_rates': {},
                        'paces': {},
                        'margins': {
                            'faster': '0:03',
                            'slower': '0:03',
                            'hr_up': 5,
                            'hr_down': 5
                        },
                        'name_prefix': ''
                    }
                
                # Ensure all config subsections exist
                for section in ['heart_rates', 'paces', 'margins']:
                    if section not in self.workout_data['config']:
                        self.workout_data['config'][section] = {}
                
                # Update UI
                self.update_ui_from_data()
                
                # Store the file path
                self.file_path = file_path
                
                # Update the window title
                self.title(f"Workout Editor - {os.path.basename(file_path)}")
                
                logger.info(f"Loaded workout file: {file_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
            logger.error(f"Failed to load file: {str(e)}")

    def save_file(self):
        """Save the workout file"""
        if not self.file_path:
            self.save_file_as()
        else:
            self.write_file(self.file_path)

    def save_file_as(self):
        """Save the workout file with a new name"""
        file_path = filedialog.asksaveasfilename(
            title="Save Workout File",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            defaultextension=".yaml"
        )
        
        if file_path:
            self.write_file(file_path)
            self.file_path = file_path
            self.title(f"Workout Editor - {os.path.basename(file_path)}")

    def write_file(self, file_path):
        """Write the workout data to a file"""
        try:
            with open(file_path, 'w') as file:
                yaml.dump(self.workout_data, file, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Saved workout file: {file_path}")
            messagebox.showinfo("Success", f"File saved: {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")
            logger.error(f"Failed to save file: {str(e)}")

    def update_yaml_preview(self):
        """Update the YAML preview text widget"""
        try:
            # Convert data to YAML
            yaml_text = yaml.dump(self.workout_data, default_flow_style=False, sort_keys=False)
            
            # Update the text widget
            self.yaml_text.delete(1.0, tk.END)
            self.yaml_text.insert(tk.END, yaml_text)
            
        except Exception as e:
            self.yaml_text.delete(1.0, tk.END)
            self.yaml_text.insert(tk.END, f"Error generating YAML: {str(e)}")


class ConfigItemDialog(tk.Toplevel):
    """Dialog for adding or editing configuration items (paces, heart rates)"""
    def __init__(self, parent, title, name="", value=""):
        super().__init__(parent)
        
        self.result = None
        
        self.title(title)
        self.geometry("400x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Create widgets
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Name:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.name_var = tk.StringVar(value=name)
        ttk.Entry(frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(frame, text="Value:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.value_var = tk.StringVar(value=value)
        ttk.Entry(frame, textvariable=self.value_var, width=30).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Help text
        help_text = ("Examples:\n"
                   "- Pace: '5:30-5:10' or '10km in 45:00' or '80-85% marathon'\n"
                   "- Heart Rate: '70-76% max_hr' or '150-160' or '160'")
        ttk.Label(frame, text=help_text, wraplength=380).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        # Center the dialog
        self.center_window()
        
        # Start the dialog
        self.wait_window()
        
    def center_window(self):
        """Center the dialog on the parent window"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.master.winfo_rootx() + (self.master.winfo_width() // 2)) - (width // 2)
        y = (self.master.winfo_rooty() + (self.master.winfo_height() // 2)) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def ok(self):
        """Handle OK button click"""
        name = self.name_var.get().strip()
        value = self.value_var.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Name cannot be empty", parent=self)
            return
            
        if not value:
            messagebox.showerror("Error", "Value cannot be empty", parent=self)
            return
            
        self.result = (name, value)
        self.destroy()
        
    def cancel(self):
        """Handle Cancel button click"""
        self.destroy()


class WorkoutStepsEditor(tk.Toplevel):
    """Dialog for editing workout steps"""
    def __init__(self, parent, workout_name, workout_data):
        super().__init__(parent)
        
        self.parent = parent
        self.workout_name = workout_name
        self.workout_data = workout_data
        self.workout_steps = deepcopy(workout_data[workout_name]) if workout_name in workout_data else []
        
        self.title(f"Edit Workout: {workout_name}")
        self.geometry("800x600")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        
        # Create widgets
        self.create_ui()
        
        # Center the dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.parent.winfo_rootx() + (self.parent.winfo_width() // 2)) - (width // 2)
        y = (self.parent.winfo_rooty() + (self.parent.winfo_height() // 2)) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Wait for the dialog to close
        self.wait_window()
        
    def create_ui(self):
        """Create the user interface"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Description frame
        desc_frame = ttk.Frame(main_frame)
        desc_frame.pack(fill=tk.X, expand=False, pady=5)
        
        ttk.Label(desc_frame, text="Workout Description:").pack(side=tk.LEFT, padx=5)
        self.description_var = tk.StringVar()
        ttk.Entry(desc_frame, textvariable=self.description_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Extract description from comment if it exists
        if isinstance(self.workout_data.get(self.workout_name, None), str) and '#' in self.workout_data[self.workout_name]:
            self.description_var.set(self.workout_data[self.workout_name].split('#', 1)[1].strip())
        
        # Create frame for steps list
        steps_frame = ttk.LabelFrame(main_frame, text="Workout Steps")
        steps_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create treeview for steps
        self.steps_tree = ttk.Treeview(steps_frame, columns=("type", "details", "description"), show="headings")
        self.steps_tree.heading("type", text="Type")
        self.steps_tree.heading("details", text="Details")
        self.steps_tree.heading("description", text="Description")
        self.steps_tree.column("type", width=100)
        self.steps_tree.column("details", width=300)
        self.steps_tree.column("description", width=300)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(steps_frame, orient="vertical", command=self.steps_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.steps_tree.configure(yscrollcommand=scrollbar.set)
        self.steps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Buttons for managing steps
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(buttons_frame, text="Add Step", command=self.add_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Add Repeat", command=self.add_repeat).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Edit Step", command=self.edit_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Delete Step", command=self.delete_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Move Up", command=lambda: self.move_step(-1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Move Down", command=lambda: self.move_step(1)).pack(side=tk.LEFT, padx=5)
        
        # Save/Cancel buttons
        action_buttons = ttk.Frame(main_frame)
        action_buttons.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_buttons, text="Save Changes", command=self.save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_buttons, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Bind double click to edit
        self.steps_tree.bind("<Double-1>", lambda e: self.edit_step())
        
        # Load steps into treeview
        self.load_steps()
        
    def load_steps(self):
        """Load the workout steps into the treeview"""
        # Clear existing items
        self.steps_tree.delete(*self.steps_tree.get_children())
        
        # Add steps to treeview
        self.add_steps_to_tree(self.workout_steps)
        
    def add_steps_to_tree(self, steps, parent=""):
        """Add steps to the treeview recursively"""
        for i, step in enumerate(steps):
            # For each key in the step (there should be only one)
            for step_type, step_data in step.items():
                if step_type == 'repeat':
                    # Get the number of repetitions
                    iterations = step_data
                    # Create a repeat node
                    step_id = self.steps_tree.insert(parent, 'end', 
                                                 values=("repeat", f"{iterations} times", ""),
                                                 tags=("repeat",))
                    
                    # Process its children if any
                    if len(step) > 1:  # There are child steps
                        for child_key, child_steps in step.items():
                            if child_key != 'repeat':
                                self.add_steps_to_tree(child_steps, step_id)
                else:
                    # Regular step
                    description = ""
                    details = ""
                    
                    # Parse the step details
                    if isinstance(step_data, str):
                        details_parts = step_data.split("--", 1)
                        details = details_parts[0].strip()
                        if len(details_parts) > 1:
                            description = details_parts[1].strip()
                    elif isinstance(step_data, list):
                        # This could be a nested repeat or something else
                        details = "Complex step"
                        
                    # Insert into tree
                    self.steps_tree.insert(parent, 'end', 
                                        values=(step_type, details, description),
                                        tags=(step_type,))
        
    def add_step(self):
        """Add a new step to the workout"""
        dialog = StepDialog(self)
        
        if dialog.result:
            step_type, step_details, step_description = dialog.result
            
            # Create the step
            step = {step_type: step_details}
            
            # Add description if provided
            if step_description:
                step[step_type] += f" -- {step_description}"
                
            # Add to steps list
            self.workout_steps.append(step)
            
            # Reload the steps
            self.load_steps()
            
    def add_repeat(self):
        """Add a repeat section"""
        dialog = RepeatDialog(self)
        
        if dialog.result:
            iterations, steps = dialog.result
            
            # Create the repeat step
            repeat_step = {'repeat': iterations}
            
            # Add the repeated steps
            if steps:
                repeat_step.update(steps)
                
            # Add to steps list
            self.workout_steps.append(repeat_step)
            
            # Reload the steps
            self.load_steps()
            
    def edit_step(self):
        """Edit the selected step"""
        selection = self.steps_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a step to edit.")
            return
            
        item = self.steps_tree.item(selection[0])
        step_type, details, description = item['values']
        
        # Check if it's a repeat
        if step_type == 'repeat':
            # Extract iterations
            iterations = int(details.split()[0])
            
            # Get child steps
            child_steps = []
            for child_id in self.steps_tree.get_children(selection[0]):
                child_item = self.steps_tree.item(child_id)
                child_type, child_details, child_description = child_item['values']
                child_step = {child_type: child_details}
                if child_description:
                    child_step[child_type] += f" -- {child_description}"
                child_steps.append(child_step)
                
            # Open repeat dialog
            dialog = RepeatDialog(self, iterations, child_steps)
            
            if dialog.result:
                new_iterations, new_steps = dialog.result
                
                # Find the step in the workout_steps list
                step_index = self.find_step_index(selection[0])
                
                if step_index is not None:
                    # Update the repeat step
                    self.workout_steps[step_index] = {'repeat': new_iterations}
                    
                    # Add the repeated steps
                    if new_steps:
                        self.workout_steps[step_index].update(new_steps)
                        
                    # Reload the steps
                    self.load_steps()
                    
        else:
            # Regular step
            step_data = details
            if description:
                step_data += f" -- {description}"
                
            # Open step dialog
            dialog = StepDialog(self, step_type, step_data)
            
            if dialog.result:
                new_type, new_details, new_description = dialog.result
                
                # Find the step in the workout_steps list
                step_index = self.find_step_index(selection[0])
                
                if step_index is not None:
                    # Create the updated step
                    new_step = {new_type: new_details}
                    
                    # Add description if provided
                    if new_description:
                        new_step[new_type] += f" -- {new_description}"
                        
                    # Update the step
                    self.workout_steps[step_index] = new_step
                    
                    # Reload the steps
                    self.load_steps()
                    
    def find_step_index(self, item_id):
        """Find the index of a step in the workout_steps list based on the treeview item"""
        # This is a simplified approach and may not work for complex nested structures
        # For a real implementation, you'd need a more sophisticated algorithm
        # to traverse both the treeview and the workout_steps list in parallel
        
        # Get the path of indices in the treeview
        path = []
        parent_id = item_id
        
        while parent_id:
            parent_parent = self.steps_tree.parent(parent_id)
            if parent_parent:
                # Count position among siblings
                siblings = self.steps_tree.get_children(parent_parent)
                position = siblings.index(parent_id)
                path.insert(0, position)
            else:
                # Root level item
                siblings = self.steps_tree.get_children()
                position = siblings.index(parent_id)
                path.insert(0, position)
                break
            parent_id = parent_parent
            
        # Get the item at the path in workout_steps
        if len(path) == 1:
            # Simple case - item at root level
            return path[0]
        else:
            # More complex case with nesting
            # This simplified version just returns None for nested items
            return None
            
    def delete_step(self):
        """Delete the selected step"""
        selection = self.steps_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a step to delete.")
            return
            
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this step?"):
            # Find the step in the workout_steps list
            step_index = self.find_step_index(selection[0])
            
            if step_index is not None:
                # Delete the step
                del self.workout_steps[step_index]
                
                # Reload the steps
                self.load_steps()
                
    def move_step(self, direction):
        """Move the selected step up or down"""
        selection = self.steps_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a step to move.")
            return
            
        # Find the step in the workout_steps list
        step_index = self.find_step_index(selection[0])
        
        if step_index is not None:
            # Calculate the new index
            new_index = step_index + direction
            
            # Check if the new index is valid
            if 0 <= new_index < len(self.workout_steps):
                # Swap the steps
                self.workout_steps[step_index], self.workout_steps[new_index] = \
                    self.workout_steps[new_index], self.workout_steps[step_index]
                
                # Reload the steps
                self.load_steps()
                
                # Select the moved item
                children = self.steps_tree.get_children()
                if 0 <= new_index < len(children):
                    self.steps_tree.selection_set(children[new_index])
                    
    def save_changes(self):
        """Save changes to the workout"""
        # Create a comment for the workout description
        description = self.description_var.get().strip()
        if description:
            # Add the description as a comment
            self.workout_data[self.workout_name] = self.workout_steps
            
            # Add a comment to the workout key
            yaml_str = yaml.dump({self.workout_name: self.workout_steps}, default_flow_style=False)
            first_line = yaml_str.split('\n', 1)[0]
            commented_first_line = f"{first_line} # {description}"
            
            # Split the remaining lines
            remaining_lines = yaml_str.split('\n', 1)[1] if '\n' in yaml_str else ""
            
            # Reconstruct with comment
            yaml_str = f"{commented_first_line}\n{remaining_lines}" if remaining_lines else commented_first_line
            
            # Parse the YAML string back to an object
            parsed = yaml.safe_load(yaml_str)
            
            # Update the workout data
            for k, v in parsed.items():
                self.workout_data[k] = v
        else:
            self.workout_data[self.workout_name] = self.workout_steps
        
        # Close the dialog
        self.destroy()


class StepDialog(tk.Toplevel):
    """Dialog for adding or editing a workout step"""
    def __init__(self, parent, step_type="", step_data=""):
        super().__init__(parent)
        
        self.result = None
        
        self.title("Edit Step" if step_type else "Add Step")
        self.geometry("500x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Parse step data
        details = step_data
        description = ""
        
        if " -- " in step_data:
            details, description = step_data.split(" -- ", 1)
        
        # Create widgets
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Step type selection
        ttk.Label(frame, text="Step Type:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.step_type_var = tk.StringVar(value=step_type)
        step_types = ["warmup", "interval", "recovery", "cooldown", "rest", "other"]
        step_type_combo = ttk.Combobox(frame, textvariable=self.step_type_var, values=step_types, width=20)
        step_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Step details
        ttk.Label(frame, text="Step Details:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.details_var = tk.StringVar(value=details)
        ttk.Entry(frame, textvariable=self.details_var, width=40).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Step description
        ttk.Label(frame, text="Description:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.description_var = tk.StringVar(value=description)
        ttk.Entry(frame, textvariable=self.description_var, width=40).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Help text for step details
        help_text = ("Step Details Examples:\n"
                   "- Duration: '10min', '1h', '30s'\n"
                   "- Distance: '400m', '5km'\n"
                   "- Pace: '@ 4:30', '@ marathon'\n"
                   "- Button: 'lap-button'\n"
                   "- Combined: '5km @ marathon', '400m @ 4:30', '10min @hr lt_hr'")
                   
        help_label = ttk.Label(frame, text=help_text, wraplength=480, justify=tk.LEFT)
        help_label.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        # Builder section
        builder_frame = ttk.LabelFrame(frame, text="Step Builder")
        builder_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # End condition
        ttk.Label(builder_frame, text="End Condition:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.end_condition_var = tk.StringVar(value="lap-button")
        end_conditions = ["lap-button", "time", "distance"]
        ttk.Combobox(builder_frame, textvariable=self.end_condition_var, values=end_conditions, width=15).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # End value
        ttk.Label(builder_frame, text="Value:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.end_value_var = tk.StringVar()
        ttk.Entry(builder_frame, textvariable=self.end_value_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Target type
        ttk.Label(builder_frame, text="Target:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.target_type_var = tk.StringVar(value="none")
        target_types = ["none", "pace", "heart rate"]
        ttk.Combobox(builder_frame, textvariable=self.target_type_var, values=target_types, width=15).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Target value
        ttk.Label(builder_frame, text="Value:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.target_value_var = tk.StringVar()
        ttk.Entry(builder_frame, textvariable=self.target_value_var, width=20).grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Apply button
        ttk.Button(builder_frame, text="Generate Step Details", command=self.generate_step).grid(row=2, column=0, columnspan=4, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        # Center the dialog
        self.center_window()
        
        # Start the dialog
        self.wait_window()
        
    def center_window(self):
        """Center the dialog on the parent window"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.master.winfo_rootx() + (self.master.winfo_width() // 2)) - (width // 2)
        y = (self.master.winfo_rooty() + (self.master.winfo_height() // 2)) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def generate_step(self):
        """Generate step details from the builder fields"""
        end_condition = self.end_condition_var.get()
        end_value = self.end_value_var.get()
        target_type = self.target_type_var.get()
        target_value = self.target_value_var.get()
        
        step_details = ""
        
        # Add end condition
        if end_condition == "lap-button":
            step_details = "lap-button"
        elif end_condition == "time":
            if not end_value:
                messagebox.showerror("Error", "Please enter a time value", parent=self)
                return
            step_details = end_value
        elif end_condition == "distance":
            if not end_value:
                messagebox.showerror("Error", "Please enter a distance value", parent=self)
                return
            step_details = end_value
            
        # Add target
        if target_type == "pace" and target_value:
            step_details += f" @ {target_value}"
        elif target_type == "heart rate" and target_value:
            step_details += f" @hr {target_value}"
            
        # Update the details field
        self.details_var.set(step_details)
        
    def ok(self):
        """Handle OK button click"""
        step_type = self.step_type_var.get().strip()
        details = self.details_var.get().strip()
        description = self.description_var.get().strip()
        
        if not step_type:
            messagebox.showerror("Error", "Step type cannot be empty", parent=self)
            return
            
        if not details:
            messagebox.showerror("Error", "Step details cannot be empty", parent=self)
            return
            
        self.result = (step_type, details, description)
        self.destroy()
        
    def cancel(self):
        """Handle Cancel button click"""
        self.destroy()


class RepeatDialog(tk.Toplevel):
    """Dialog for adding or editing a repeat section"""
    def __init__(self, parent, iterations=0, steps=None):
        super().__init__(parent)
        
        self.result = None
        self.steps = steps or []
        
        self.title("Edit Repeat" if iterations else "Add Repeat")
        self.geometry("600x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        
        # Create widgets
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Number of iterations
        ttk.Label(frame, text="Number of Iterations:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.iterations_var = tk.IntVar(value=iterations or 1)
        ttk.Spinbox(frame, from_=1, to=100, textvariable=self.iterations_var, width=5).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Steps frame
        steps_frame = ttk.LabelFrame(frame, text="Repeated Steps")
        steps_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E+tk.N+tk.S)
        steps_frame.columnconfigure(0, weight=1)
        steps_frame.rowconfigure(0, weight=1)
        
        # Steps treeview
        self.steps_tree = ttk.Treeview(steps_frame, columns=("type", "details", "description"), show="headings")
        self.steps_tree.heading("type", text="Type")
        self.steps_tree.heading("details", text="Details")
        self.steps_tree.heading("description", text="Description")
        self.steps_tree.column("type", width=100)
        self.steps_tree.column("details", width=200)
        self.steps_tree.column("description", width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(steps_frame, orient="vertical", command=self.steps_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.N+tk.S)
        self.steps_tree.configure(yscrollcommand=scrollbar.set)
        self.steps_tree.grid(row=0, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        
        # Buttons for steps
        steps_buttons = ttk.Frame(steps_frame)
        steps_buttons.grid(row=1, column=0, columnspan=2, pady=5)
        
        ttk.Button(steps_buttons, text="Add Step", command=self.add_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(steps_buttons, text="Edit Step", command=self.edit_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(steps_buttons, text="Delete Step", command=self.delete_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(steps_buttons, text="Move Up", command=lambda: self.move_step(-1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(steps_buttons, text="Move Down", command=lambda: self.move_step(1)).pack(side=tk.LEFT, padx=5)
        
        # OK/Cancel buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        # Configure grid
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        
        # Populate steps
        self.load_steps()
        
        # Center the dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.master.winfo_rootx() + (self.master.winfo_width() // 2)) - (width // 2)
        y = (self.master.winfo_rooty() + (self.master.winfo_height() // 2)) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Bind double click to edit
        self.steps_tree.bind("<Double-1>", lambda e: self.edit_step())
        
        # Start the dialog
        self.wait_window()
        
    def load_steps(self):
        """Load the steps into the treeview"""
        # Clear existing items
        self.steps_tree.delete(*self.steps_tree.get_children())
        
        # Add steps to treeview
        for i, step in enumerate(self.steps):
            for step_type, step_data in step.items():
                description = ""
                details = step_data
                
                if isinstance(step_data, str) and " -- " in step_data:
                    details, description = step_data.split(" -- ", 1)
                
                self.steps_tree.insert('', 'end', values=(step_type, details, description))
        
    def add_step(self):
        """Add a new step to the repeat"""
        dialog = StepDialog(self)
        
        if dialog.result:
            step_type, step_details, step_description = dialog.result
            
            # Create the step
            step = {step_type: step_details}
            
            # Add description if provided
            if step_description:
                step[step_type] += f" -- {step_description}"
                
            # Add to steps list
            self.steps.append(step)
            
            # Reload the steps
            self.load_steps()
            
    def edit_step(self):
        """Edit the selected step"""
        selection = self.steps_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a step to edit.")
            return
            
        item = self.steps_tree.item(selection[0])
        step_type, details, description = item['values']
        
        # Prepare step data
        step_data = details
        if description:
            step_data += f" -- {description}"
            
        # Open step dialog
        dialog = StepDialog(self, step_type, step_data)
        
        if dialog.result:
            new_type, new_details, new_description = dialog.result
            
            # Get the index of the selected step
            index = self.steps_tree.index(selection[0])
            
            # Create the updated step
            new_step = {new_type: new_details}
            
            # Add description if provided
            if new_description:
                new_step[new_type] += f" -- {new_description}"
                
            # Update the step
            self.steps[index] = new_step
            
            # Reload the steps
            self.load_steps()
            
    def delete_step(self):
        """Delete the selected step"""
        selection = self.steps_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a step to delete.")
            return
            
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this step?"):
            # Get the index of the selected step
            index = self.steps_tree.index(selection[0])
            
            # Delete the step
            del self.steps[index]
            
            # Reload the steps
            self.load_steps()
            
    def move_step(self, direction):
        """Move the selected step up or down"""
        selection = self.steps_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a step to move.")
            return
            
        # Get the index of the selected step
        index = self.steps_tree.index(selection[0])
        
        # Calculate the new index
        new_index = index + direction
        
        # Check if the new index is valid
        if 0 <= new_index < len(self.steps):
            # Swap the steps
            self.steps[index], self.steps[new_index] = self.steps[new_index], self.steps[index]
            
            # Reload the steps
            self.load_steps()
            
            # Select the moved item
            children = self.steps_tree.get_children()
            if 0 <= new_index < len(children):
                self.steps_tree.selection_set(children[new_index])
            
    def ok(self):
        """Handle OK button click"""
        iterations = self.iterations_var.get()
        
        if iterations <= 0:
            messagebox.showerror("Error", "Number of iterations must be positive", parent=self)
            return
            
        self.result = (iterations, self.steps)
        self.destroy()
        
    def cancel(self):
        """Handle Cancel button click"""
        self.destroy()

# Function to integrate this editor into the main Garmin Planner GUI
def add_workout_editor_tab(notebook, parent):
    """Add a tab to open the workout editor from the main GUI"""
    editor_frame = ttk.Frame(notebook)
    notebook.add(editor_frame, text="Workout Editor")
    
    ttk.Label(editor_frame, text="Workout Plan Editor", font=("", 12, "bold")).pack(pady=10)
    
    ttk.Label(editor_frame, text="Create and edit workout plans in YAML format").pack(pady=5)
    
    # Buttons frame
    buttons_frame = ttk.Frame(editor_frame)
    buttons_frame.pack(pady=20)
    
    ttk.Button(buttons_frame, text="New Workout Plan", 
             command=lambda: open_workout_editor(parent)).pack(pady=5, fill=tk.X)
    
    ttk.Button(buttons_frame, text="Open Existing Plan", 
             command=lambda: open_workout_editor(parent, select_file=True)).pack(pady=5, fill=tk.X)
    
    # Tips and instructions
    tips_frame = ttk.LabelFrame(editor_frame, text="Tips")
    tips_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    tips_text = (
        "- Create workout plans with a visual editor\n"
        "- Define paces and heart rates for your training plan\n"
        "- Create structured workouts with intervals, repeats, etc.\n"
        "- Save as YAML format compatible with Garmin Planner\n\n"
        "Workout naming convention:\n"
        "W##S## Description (e.g., 'W01S01 Easy Run')\n"
        "Where W## is the week number and S## is the session number."
    )
    
    ttk.Label(tips_frame, text=tips_text, justify=tk.LEFT, wraplength=500).pack(padx=10, pady=10)
    
    return editor_frame

def open_workout_editor(parent, select_file=False):
    """Open the workout editor with an optional file selection"""
    file_path = None
    
    if select_file:
        file_path = filedialog.askopenfilename(
            title="Open Workout Plan",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            initialdir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "training_plans")
        )
        
        if not file_path:  # User cancelled
            return
    
    # Create and show the workout editor
    editor = WorkoutEditor(parent, file_path)
    
if __name__ == "__main__":
    # Stand-alone testing
    root = tk.Tk()
    root.title("Workout Editor Test")
    
    # Create a button to open the editor
    ttk.Button(root, text="Open Workout Editor", 
             command=lambda: WorkoutEditor(root)).pack(padx=20, pady=20)
    
    root.mainloop()
