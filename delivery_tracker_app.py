import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import csv
from datetime import datetime
import requests
from PIL import Image, ImageTk
import io
import webbrowser
from google import genai
from google.genai.errors import APIError
from io import StringIO
import math
import os
import tempfile
import re
from tkinter import messagebox

# -------------------------------------------------------------------
# Global state and API Keys
# -------------------------------------------------------------------
delivery_data = []
selected_row_id = None
input_widgets = {}
summary_inputs = {}
copied_data = {}
current_street_view_url = ""
image_cache = {}
street_view_image_label = None

# GLOBAL VERSION DEFINITION
APP_VERSION = "25.10.31.1"

# GLOBAL VARIABLE FOR AUTO-SAVE
auto_save_filepath = None

# IMAGE INTERACTION GLOBALS
current_address_for_image = ""
current_heading = 0
current_fov = 90
last_mouse_x = 0
last_displayed_width = 0
last_displayed_height = 0

# FIX FOR LAYOUT STABILITY AND SQUARE RATIO
# Setting a fixed, square size
MIN_IMAGE_WIDTH = 450
MIN_IMAGE_HEIGHT = 450 

# GITHUB RAW FILE URL
GITHUB_RAW_FILE_URL = "https://raw.githubusercontent.com/masonalmazanrivr/pythontest/main/delivery_tracker_app.py"

# NOTE: REPLACE THESE WITH YOUR ACTUAL KEYS!
google_api_key = "AIzaSyBKE225e5Eq4tEyAPqJXO_Hd5grSeoYcqc" # Google Maps Street View API Key
GEMINI_API_KEY = "AIzaSyCDcp2WtRkpsuUsr3b3rTN_mkErQXsdv1I" # Gemini API Key for image processing

# Field definitions
field_map = {
    "Date": {"type": "input"},
    "Function": {"type": "dropdown", "options": ["Commercial", "R&D/Testing"]},
    "Robot ID": {"type": "input"},
    "ID in the Route": {"type": "input"},
    "Address": {"type": "input"},
    "Packages": {"type": "input"},
    "Success": {"type": "dropdown", "options": ["Yes", "No", "Skipped by robot", "Missing"]},
    "Soft help from Field Operator": {"type": "dropdown", "options": ["No help needed", "Needed help", "N/A"]},
    "Field Operator physically intervened": {"type": "dropdown", "options": ["No help needed", "Needed help", "N/A"]},
    "Autonomous Return": {"type": "dropdown", "options": ["Successful", "Successful partial return", "Needed to intervene", "Not used"]},
    "Order placement": {"type": "dropdown", "options": ["Good placement", "Bad placement", "N/A"]},
    "Robot health": {"type": "dropdown", "options": ["No faults", "Broken parts"]},
    "Connectivity": {"type": "dropdown", "options": ["Good connection", "Poor but manageable", "Bad connection", "N/A"]},
    "Cluttered environment": {"type": "dropdown", "options": ["Robot fits", "Path too tight", "N/A"]},
    "Gated environment": {"type": "dropdown", "options": ["No gates", "Gates"]},
    "Payload addressability": {"type": "dropdown", "options": ["Order was delivered", "Payload issues", "Oversized package", "N/A"]},
    "Too risky to try": {"type": "dropdown", "options": ["Not risky", "Too risky", "N/A"]},
    "Mobile Hub": {"type": "dropdown", "options": ["Successful", "Unsuccessful", "N/A"]},
    "Did the parcel drop on the first package": {"type": "dropdown", "options": ["1st try", "2nd try", "3rd try"]},
    "Operator Comments": {"type": "input"},
}

# ---------- Color schemes ----------
GREEN = "#1f7a3f"
RED = "#a31212"
YELLOW = "#f1d48a"
LGRAY = "#d9d9d9"
FG_ON = "#ffffff"
FG_OFF = "#000000"
LGREEN = "#cfecc9"

COLOR_SCHEMES = {
    "Success": {
        "Yes": (GREEN, FG_ON),
        "No": (RED, FG_ON),
        "Skipped by robot": (YELLOW, FG_OFF),
        "Missing": (LGRAY, FG_OFF),
    },
    "Soft help from Field Operator": {
        "No help needed": (GREEN, FG_ON),
        "Needed help": (RED, FG_ON),
        "N/A": (LGRAY, FG_OFF),
    },
    "Field Operator physically intervened": {
        "No help needed": (GREEN, FG_ON),
        "Needed help": (RED, FG_ON),
        "N/A": (LGRAY, FG_OFF),
    },
    "Autonomous Return": {
        "Successful": (GREEN, FG_ON),
        "Successful partial return": (LGREEN, FG_OFF),
        "Needed to intervene": (RED, FG_ON),
        "Not used": (LGRAY, FG_OFF),
    },
    "Order placement": {
        "Good placement": (GREEN, FG_ON),
        "Bad placement": (RED, FG_ON),
        "N/A": (LGRAY, FG_OFF),
    },
    "Robot health": {
        "No faults": (GREEN, FG_ON),
        "Broken parts": (RED, FG_ON),
    },
    "Connectivity": {
        "Good connection": (GREEN, FG_ON),
        "Poor but manageable": (YELLOW, FG_OFF),
        "Bad connection": (RED, FG_ON),
        "N/A": (LGRAY, FG_OFF),
    },
    "Cluttered environment": {
        "Robot fits": (GREEN, FG_ON),
        "Path too tight": (RED, FG_ON),
        "N/A": (LGRAY, FG_OFF),
    },
    "Gated environment": {
        "No gates": (GREEN, FG_ON),
        "Gates": (RED, FG_ON),
    },
    "Payload addressability": {
        "Order was delivered": (GREEN, FG_ON),
        "Payload issues": (RED, FG_ON),
        "Oversized package": (YELLOW, FG_OFF),
        "N/A": (LGRAY, FG_OFF),
    },
    "Too risky to try": {
        "Not risky": (GREEN, FG_ON),
        "Too risky": (RED, FG_ON),
        "N/A": (LGRAY, FG_OFF),
    },
    "Mobile Hub": {
        "Successful": (GREEN, FG_ON),
        "Unsuccessful": (RED, FG_ON),
        "N/A": (LGRAY, FG_OFF),
    },
    "Did the parcel drop on the first package": {
        "1st try": (GREEN, FG_ON),
        "2nd try": (YELLOW, FG_ON),
        "3rd try": (RED, FG_OFF),
    },
}

# -------------------------------------------------------------------
# NEW: Autofill Presets
# -------------------------------------------------------------------

# Data fields to be cleared/autofilled (all fields below 'Packages')
AUTOFILL_FIELDS = [
    "Success", "Soft help from Field Operator", "Field Operator physically intervened",
    "Autonomous Return", "Order placement", "Robot health", "Connectivity",
    "Cluttered environment", "Gated environment", "Payload addressability",
    "Too risky to try", "Mobile Hub", "Operator Comments"
]

AUTOFILL_PRESETS = {
    # 1. SUCCESS Preset (NEW)
    "Success": {
        "Success": "Yes", 
        "Soft help from Field Operator": "No help needed", 
        "Field Operator physically intervened": "No help needed", 
        "Autonomous Return": "Successful", 
        "Order placement": "Good placement", 
        "Robot health": "No faults",
        "Connectivity": "Good connection", 
        "Cluttered environment": "Robot fits", 
        "Gated environment": "No gates", 
        "Payload addressability": "Order was delivered", 
        "Too risky to try": "Not risky", 
        "Operator Comments": "" 
    },
    # 2. Clear Preset
    "Clear": {field: "" for field in AUTOFILL_FIELDS},
    # 3. Bad Connection Preset 
    "Bad connection": {
        "Success": "Skipped by robot", 
        "Soft help from Field Operator": "N/A", 
        "Field Operator physically intervened": "Needed help", 
        "Autonomous Return": "Not used", 
        "Order placement": "N/A", 
        "Robot health": "Broken parts", 
        "Connectivity": "Bad connection", 
        "Cluttered environment": "N/A", 
        "Gated environment": "No gates", 
        "Payload addressability": "N/A", 
        "Too risky to try": "N/A", 
        "Operator Comments": "hand delivery, bad connection"
    },
    # 4. Missing Package Preset 
    "Missing Package": {
        "Success": "Missing", 
        "Soft help from Field Operator": "N/A", 
        "Field Operator physically intervened": "N/A", 
        "Autonomous Return": "Not used", 
        "Order placement": "N/A", 
        "Robot health": "No faults", 
        "Connectivity": "N/A", 
        "Cluttered environment": "N/A", 
        "Gated environment": "No gates", 
        "Payload addressability": "N/A", 
        "Too risky to try": "N/A", 
        "Operator Comments": "Missing Package"
    }
}

AUTOFILL_SCHEME = {
    "Success": (GREEN, FG_ON),
    "Missing Package": (LGRAY, FG_OFF), 
    "Clear": (LGRAY, FG_OFF),
    "Bad connection": (RED, FG_ON),
}


def autofill_data(preset_name):
    """
    Applies a defined preset of data to all currently selected rows and updates the UI.
    This is triggered by the new 'Autofill' dropdown.
    """
    global selected_row_id
    if not delivery_data:
        status_label.config(text="No data loaded to autofill.", anchor=tk.W, foreground="red")
        # Reset dropdown immediately if no data
        autofill_dropdown.set(autofill_dropdown.EMPTY_VALUE)
        return

    preset = AUTOFILL_PRESETS.get(preset_name)
    if not preset:
        return

    selected_items = tree.selection()
    if not selected_items:
        status_label.config(text="Please select one or more stops to autofill.", anchor=tk.W, foreground="orange")
        # Reset dropdown immediately if no selection
        autofill_dropdown.set(autofill_dropdown.EMPTY_VALUE)
        return

    # 1. Apply the data to the global delivery_data list for all selected items
    for item in selected_items:
        item_index = tree.index(item)
        
        # Apply the preset values
        for field, value in preset.items():
            delivery_data[item_index][field] = value
            
            # Special handling for Success field to update the Treeview tag
            if field == 'Success':
                apply_success_tag(item, value)

    # 2. Update the visible input fields with the data from the first selected row
    first_item_index = tree.index(selected_items[0])
    populate_input_fields(delivery_data[first_item_index])

    # 3. Auto-save the changes
    write_data_to_csv()

    # 4. Provide user feedback
    status_label.config(text=f"Autofilled '{preset_name}' data for {len(selected_items)} item(s).", anchor=tk.W, foreground="darkgreen")
    
    # 5. Reset the dropdown to 'Autofill' after selection
    autofill_dropdown.set(autofill_dropdown.EMPTY_VALUE)


# -------------------------------------------------------------------
# Focus and Navigation Logic
# -------------------------------------------------------------------

def focus_next_widget(event):
    """Moves focus to the next/previous widget in the defined order, handling Up/Down arrows."""
    # Include the Autofill dropdown label in the focus cycle
    widgets = list(input_widgets.values())
    
    # Prepend the autofill dropdown label for a full cycle
    global autofill_dropdown
    if 'autofill_dropdown' in globals():
        widgets.insert(0, autofill_dropdown.label)
    
    # Normalize widgets to their focusable element
    focusable_widgets = []
    for w in widgets:
        # Check if it's the Autofill dropdown label (which is a tk.Label inside a tk.Frame)
        if isinstance(w, tk.Label) and w.master in [getattr(w.master, 'autofill_dropdown', None)]:
             focusable_widgets.append(w)
        # Check if it's a regular ColorDropdown (we need its internal label)
        elif isinstance(w, ColorDropdown):
            focusable_widgets.append(w.label)
        # Check if it's a direct focusable widget (Text, Entry, Combobox)
        elif isinstance(w, (tk.Text, ttk.Entry, ttk.Combobox)):
            focusable_widgets.append(w)
    
    if not focusable_widgets:
        return

    try:
        # Determine the currently focused widget (or its container)
        focused = root.focus_get()
        current_widget = None
        
        if focused in focusable_widgets:
            current_widget = focused
        elif isinstance(focused, tk.Label) and focused.master in [w.master for w in focusable_widgets if isinstance(w, ColorDropdown.label)]:
            # Focused on a ColorDropdown label
            current_widget = focused
        elif isinstance(focused, tk.Text):
            # For Text widgets, the widget itself is focusable
            current_widget = focused
            
        if not current_widget:
            return
            
        current_index = focusable_widgets.index(current_widget)
        
    except ValueError:
        return

    next_index = current_index
    if event.keysym in ('Down', 'Tab'):
        next_index = (current_index + 1) % len(focusable_widgets)
    elif event.keysym == 'Up': 
        next_index = (current_index - 1 + len(focusable_widgets)) % len(focusable_widgets)
        
    # Set focus to the new widget
    next_widget = focusable_widgets[next_index]
    
    # Special handling for ColorDropdown to focus the label, or the widget itself
    next_widget.focus_set()
    
    return "break" # Prevent default Tkinter focus behavior (especially for Up/Down)
    
def apply_focus_style(event, is_focus_in):
    """Applies a visual indicator on focus in/out to the field frame."""
    widget = event.widget
    
    # Find the field_frame (the ttk.Frame created in create_input_widgets)
    if isinstance(widget, tk.Label): # ColorDropdown label or Autofill label
        container_frame = widget.master.master
    elif isinstance(widget, tk.Text): # Text widget
        container_frame = widget.master.master
    else: # Entry or Combobox
        container_frame = widget.master

    if is_focus_in:
        container_frame.config(highlightbackground="blue", highlightcolor="blue", highlightthickness=2)
    else:
        container_frame.config(highlightthickness=0)

# -------------------------------------------------------------------
# Treeview Tag Helper Functions
# -------------------------------------------------------------------

def get_tag_from_success_value(success_value: str) -> str:
    """Maps the Success field value to a Treeview tag name."""
    tag_map = {
        "Yes": 'Success-Yes',
        "No": 'Success-No',
        "Skipped by robot": 'Success-Skipped',
        "Missing": 'Success-Missing',
        "": 'Success-None'
    }
    return tag_map.get(success_value, 'Success-None')

def apply_success_tag(item_id, success_value):
    """Removes all success-related tags and applies the new one."""
    current_tags = tree.item(item_id, 'tags')
    # Remove old success tags
    new_tags = [t for t in current_tags if not t.startswith('Success-')]
    
    # Add new tag
    new_tag = get_tag_from_success_value(success_value)
    if new_tag not in new_tags:
        new_tags.append(new_tag)
        
    tree.item(item_id, tags=tuple(new_tags))

# ---------- Colorized dropdown widget (toggle + click-away) ----------
class ColorDropdown(tk.Frame):
    """Colored dropdown using an overrideredirect Toplevel menu, now with keyboard navigation."""
    EMPTY_VALUE = ""
    
    def __init__(self, parent, options, color_map, on_change=None):
        # FIX APPLIED HERE: highlightthickness is set on the container Frame.
        super().__init__(parent, highlightthickness=0) 
        self.options = options
        self.all_options = [self.EMPTY_VALUE] + options # Including Clear option for keyboard
        self.color_map = color_map
        self.on_change = on_change
        self.value = self.EMPTY_VALUE
        self.dropdown = None
        
        # FIX APPLIED HERE: Removed unsupported 'tabindex=0'
        self.label = tk.Label(self, text="", bd=1, relief="solid", padx=8, pady=4, cursor="hand2")
        
        self.label.pack(fill="x", expand=True)
        
        # --- KEYBOARD BINDINGS ON LABEL ---
        self.label.bind("<Button-1>", self._on_label_click)
        self.label.bind("<FocusIn>", lambda e: apply_focus_style(e, True))
        self.label.bind("<FocusOut>", lambda e: apply_focus_style(e, False))
        self.label.bind("<space>", self._on_label_key)
        self.label.bind("<Return>", self._on_label_key)
        self.label.bind("<Up>", focus_next_widget)
        self.label.bind("<Down>", focus_next_widget)
        self.label.bind("<Tab>", focus_next_widget)
        self.label.bind("<Shift-Tab>", focus_next_widget)
        # --------------------------------------
        
        self.winfo_toplevel().bind("<ButtonRelease-1>", self._on_root_click, add="+")
        self.selected_menu_index = -1 # Index in self.all_options

    def _on_label_click(self, _e):
        self._open_menu()
        return "break"
        
    def _on_label_key(self, _e):
        self._open_menu()
        return "break"
        
    def _open_menu(self, *_):
        if self.dropdown and self.dropdown.winfo_exists():
            self._close_menu()
            return
            
        self.dropdown = tk.Toplevel(self)
        self.dropdown.overrideredirect(True)
        self.dropdown.transient(self.winfo_toplevel())
        try:
            self.dropdown.wm_attributes("-topmost", True)
        except Exception:
            pass
            
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self.dropdown.geometry(f"+{x}+{y}")
        self.dropdown.bind("<Escape>", lambda e: self._close_menu())
        self.dropdown.focus_set()
        
        # --- Menu Navigation Logic ---
        self.dropdown.bind("<Down>", self._navigate_menu)
        self.dropdown.bind("<Up>", self._navigate_menu)
        self.dropdown.bind("<Return>", self._select_via_keyboard)
        self.dropdown.bind("<space>", self._select_via_keyboard)
        # -----------------------------
        
        # Store menu item widgets (labels) for keyboard navigation
        self.menu_items = []
        
        # --- Add the CLEAR/RESET option ---
        reset_val = self.EMPTY_VALUE
        reset_item = tk.Label(
            self.dropdown, 
            text="-- Clear Selection --", 
            bg="#ffffff", 
            fg="#999999", 
            padx=10, 
            pady=6,
            font=("TkDefaultFont", 10, "italic")
        )
        reset_item.pack(fill="x")
        self.menu_items.append(reset_item)
        reset_item.bind("<Enter>", lambda e, w=reset_item: self._highlight_item(w))
        reset_item.bind("<Leave>", lambda e, w=reset_item: self._unhighlight_item(w))
        reset_item.bind("<Button-1>", lambda e, val=reset_val: self._select(val))
        
        # Separator
        ttk.Separator(self.dropdown, orient=tk.HORIZONTAL).pack(fill='x', pady=2)
        
        # Items (existing options)
        for opt in self.options:
            bg, fg = self.color_map.get(opt, ("#f0f0f0", "#000"))
            item = tk.Label(self.dropdown, text=opt, bg=bg, fg=fg, padx=10, pady=6)
            item.pack(fill="x")
            self.menu_items.append(item)
            item.bind("<Enter>", lambda e, w=item: self._highlight_item(w))
            item.bind("<Leave>", lambda e, w=item: self._unhighlight_item(w))
            item.bind("<Button-1>", lambda e, val=opt: self._select(val))

        # Initialize keyboard selection index
        try:
            current_value_index = self.all_options.index(self.value)
        except ValueError:
            current_value_index = 0 # Default to 'Clear Selection'
            
        self.selected_menu_index = current_value_index
        if self.menu_items:
             self._highlight_item(self.menu_items[self.selected_menu_index], keyboard=True)
             
    def _highlight_item(self, widget, keyboard=False):
        """Highlights a menu item (for both mouse and keyboard)."""
        if not keyboard:
             # Find index if highlighting via mouse
             try:
                 self._unhighlight_item(self.menu_items[self.selected_menu_index])
                 self.selected_menu_index = self.menu_items.index(widget)
             except:
                 pass
                 
        widget.configure(relief="solid", bd=1)
        
    def _unhighlight_item(self, widget):
        """Removes the highlight from a menu item."""
        widget.configure(relief="flat", bd=0)

    def _navigate_menu(self, event):
        """Handles Up/Down arrow key navigation in the menu."""
        if not self.menu_items:
            return "break"
        
        self._unhighlight_item(self.menu_items[self.selected_menu_index])
        
        if event.keysym == 'Down':
            self.selected_menu_index = (self.selected_menu_index + 1) % len(self.menu_items)
        elif event.keysym == 'Up':
            self.selected_menu_index = (self.selected_menu_index - 1 + len(self.menu_items)) % len(self.menu_items)
            
        self._highlight_item(self.menu_items[self.selected_menu_index], keyboard=True)
        return "break"
        
    def _select_via_keyboard(self, event):
        """Selects the highlighted item when Enter is pressed."""
        if self.selected_menu_index >= 0 and self.selected_menu_index < len(self.all_options):
            selected_value = self.all_options[self.selected_menu_index]
            self._select(selected_value)
        return "break"
            
    def _close_menu(self):
        if self.dropdown and self.dropdown.winfo_exists():
            try:
                self.dropdown.destroy()
            except Exception:
                pass
        self.dropdown = None
        self.label.focus_set() # Return focus to the main dropdown label
        
    def _on_root_click(self, event):
        if not (self.dropdown and self.dropdown.winfo_exists()):
            return
        if self._point_in_widget(self.dropdown, event.x_root, event.y_root):
            return
        if self._point_in_widget(self.label, event.x_root, event.y_root):
            return
        self._close_menu()
        
    def _point_in_widget(self, widget, x_root, y_root):
        try:
            wx = widget.winfo_rootx()
            wy = widget.winfo_rooty()
            ww = widget.winfo_width()
            wh = widget.winfo_height()
            return wx <= x_root <= wx + ww and wy <= y_root <= wy + wh
        except Exception:
            return False
            
    def _select(self, val):
        self.set(val)
        self._close_menu()
        if callable(self.on_change):
            # Pass the field name to save_data for bulk update logic
            # This logic needs adjustment for the Autofill dropdown
            if self.master.winfo_children()[0].cget("text") == "Autofill Options:":
                self.on_change(val) # For Autofill, pass the value as the preset name
            else:
                field_name = self.master.winfo_children()[0].cget("text").replace(":", "") 
                self.on_change(field_name)
            
    def set(self, val: str):
        self.value = val or self.EMPTY_VALUE 
        
        if self.value == self.EMPTY_VALUE:
            # Special handling for the main Autofill dropdown to show "Autofill"
            if 'autofill_dropdown' in globals() and self is autofill_dropdown:
                bg, fg = ("#ffffff", "#000000")
                text = "Autofill"
            else:
                bg, fg = ("#ffffff", "#000000")
                text = "Select…"
        else:
            bg, fg = self.color_map.get(self.value, ("#ffffff", "#000000"))
            text = self.value
            
        self.label.configure(text=text, bg=bg, fg=fg)
        
    def get(self) -> str:
        return self.value

# -------------------------------------------------------------------
# Auto-Save and Export Logic
# -------------------------------------------------------------------

def initialize_auto_save_file(date, robot_id, source_name):
    """
    Sets the global auto_save_filepath to a file in the user's home/temp directory 
    and writes the initial header.
    """
    global auto_save_filepath
    
    # Create a unique filename based on date and robot ID
    filename = f"autosave_report_{date.replace('/', '-')}_{robot_id}_{datetime.now().strftime('%H%M%S')}.csv"
    
    # Use a directory inside the user's home or a system temporary directory
    # For simplicity and cross-platform compatibility, let's use a temp directory
    save_dir = tempfile.gettempdir()
    
    auto_save_filepath = os.path.join(save_dir, filename)
    
    # Write the header row
    try:
        template_headers = list(field_map.keys())
        with open(auto_save_filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=template_headers)
            writer.writeheader()
        
        status_label.config(text=f"Loaded {len(delivery_data)} stops from '{source_name}'. Auto-saving to: {auto_save_filepath}", anchor=tk.W, foreground="black")
    
    except Exception as e:
        status_label.config(text=f"Error initializing auto-save file: {e}", anchor=tk.W, foreground="red")
        auto_save_filepath = None # Disable auto-save if initialization fails
        
def write_data_to_csv():
    """
    Overwrites the entire CSV file with the current state of delivery_data.
    This is called by save_data on every change.
    """
    global auto_save_filepath
    if not delivery_data and not auto_save_filepath:
        return

    try:
        template_headers = list(field_map.keys())
        # Use 'w' mode to overwrite, ensuring the file reflects the current state (including deletions)
        if auto_save_filepath:
            with open(auto_save_filepath, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=template_headers)
                writer.writeheader()
                if delivery_data:
                    writer.writerows(delivery_data)
        
    except Exception as e:
        # Crucial to alert user if auto-save fails
        status_label.config(text=f"CRITICAL AUTO-SAVE ERROR: {e}", anchor=tk.W, foreground="red")


def export_csv_file():
    """Exports all current data to a CSV file."""
    if not delivery_data:
        status_label.config(text="No data to export. Please load data first.", anchor=tk.W)
        return
        
    # Suggest the autosave path as the default save location and name
    initialdir = os.path.dirname(auto_save_filepath) if auto_save_filepath else os.getcwd()
    initialfile = os.path.basename(auto_save_filepath) if auto_save_filepath else "report_final.csv"

    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Save Report As",
        initialdir=initialdir,
        initialfile=initialfile
    )
    if filepath:
        try:
            template_headers = list(field_map.keys())
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=template_headers)
                writer.writeheader()
                writer.writerows(delivery_data)
            status_label.config(text=f"Final Report saved to '{filepath.split('/')[-1]}'", anchor=tk.W)
        except Exception as e:
            status_label.config(text=f"An error occurred while exporting: {e}", anchor=tk.W)

# -------------------------------------------------------------------
# Update Check Logic
# -------------------------------------------------------------------

def parse_version(version_str):
    """Parses a version string (e.g., '25.10.4' or '25.10.4.1') into a comparable tuple of integers."""
    # Ensure only digits and dots are considered, then split and convert to int
    clean_version = re.sub(r'[^\d.]', '', version_str)
    try:
        return tuple(map(int, clean_version.split('.'))) # This correctly creates (25, 10, 8, 1)
    except ValueError:
        return (0, 0, 0) # Fallback if parsing fails
    
def check_for_update():
    """
    Checks the GitHub repository's main file for a newer version.
    """
    # 1. Get current version
    current_version_tuple = parse_version(APP_VERSION)
    
    try:
        # 2. Fetch the raw content of the app file from GitHub
        response = requests.get(GITHUB_RAW_FILE_URL, timeout=5)
        response.raise_for_status()
        
        file_content = response.text
        latest_version = None
        
        # 3. Search for the APP_VERSION line in the file content
        # Pattern looks for 'APP_VERSION = "X.Y.Z"'
       # The corrected, more flexible pattern
        match = re.search(r'APP_VERSION\s*=\s*["\'](\d+(?:\.\d+)+)["\']', file_content)
        
        if match:
            latest_version = match.group(1).strip()
            latest_version_tuple = parse_version(latest_version)
        else:
            status_label.config(text="Error: Could not find APP_VERSION in the GitHub file.", anchor=tk.W, foreground="orange")
            return
        
        # 4. Compare versions
        if latest_version_tuple > current_version_tuple:
            # Newer version found!
            status_label.config(text=f"Update available: v{latest_version}", anchor=tk.W, foreground="red")
            
            # Show update prompt
            result = messagebox.askyesno(
                "Update Available 🚀",
                f"A new version (v{latest_version}) is available!\n\n"
                f"Your current version: v{APP_VERSION}\n\n"
                "Would you like to open the GitHub repository to download the update?"
            )
            
            if result:
                # Construct the main repository URL from the raw file URL
                parts = GITHUB_RAW_FILE_URL.split('/')
                # parts[3] is username, parts[4] is repo name
                project_url = f"https://github.com/{parts[3]}/{parts[4]}"
                webbrowser.open(project_url)
                
        else:
            # Only show this if data hasn't been loaded yet, or if it's the latest
            if not delivery_data:
                status_label.config(text=f"v{APP_VERSION} is the latest version. Select a CSV file to get started.", anchor=tk.W, foreground="darkgreen")
            
    except requests.exceptions.RequestException as e:
        print(f"Update check failed: {e}")
        # Only show this if data hasn't been loaded yet
        if not delivery_data:
            status_label.config(text="Could not check for updates. Select a CSV file to get started.", anchor=tk.W, foreground="orange")

# -------------------------------------------------------------------
# Core Application Functions
# -------------------------------------------------------------------

def generate_csv_from_image(image_filepaths, date, robot_id, popup_window, status_label_popup):
    """Sends images to Gemini, extracts and loads data."""
    try:
        if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE" or not GEMINI_API_KEY:
            status_label_popup.config(text="Error: Please set your actual GEMINI_API_KEY.", foreground="red")
            return
            
        client = genai.Client(api_key=GEMINI_API_KEY)
        all_csv_content = []
        
        def clean_csv_output(text, is_first_image):
            lines = text.strip().split('\n')
            clean_lines = []
            expected_header_lower = "stop number,address"
            
            for line in lines:
                line_stripped = line.strip().lower()
                
                if "---" in line_stripped or "here is the extracted data" in line_stripped:
                    continue
                if line_stripped.startswith('{') or line_stripped.startswith('"'):
                    continue
                
                is_header_match = line_stripped.replace('"', '').replace("'", '').replace(' ', '') == expected_header_lower.replace(' ', '')
                
                if is_header_match:
                    if is_first_image:
                        clean_lines.append(line)
                    continue

                if ',' in line:
                    clean_lines.append(line)
                        
            if is_first_image and not any("Stop Number" in l and "Address" in l for l in clean_lines):
                 clean_lines.insert(0, "Stop Number,Address")
                        
            return "\n".join(clean_lines)

        
        for i, filepath in enumerate(image_filepaths):
            status_label_popup.config(text=f"Processing image {i+1} of {len(image_filepaths)}: {filepath.split('/')[-1]}...", foreground="blue")
            root.update_idletasks()

            img = Image.open(filepath)
            
            prompt = (
                "Extract the delivery stops from this image. "
                "Output the results as pure CSV with EXACTLY two columns: 'Stop Number' (only the number, without the word 'stop') and 'Address'. "
                "Do NOT include any extra text, markdown formatting, or explanations."
            )

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, img]
            )
            
            csv_content = response.text.strip()
            
            if not csv_content:
                status_label_popup.config(text=f"Gemini returned empty data for {filepath.split('/')[-1]}.", foreground="red")
                continue

            cleaned_content = clean_csv_output(csv_content, is_first_image=(i == 0))
            if cleaned_content:
                all_csv_content.append(cleaned_content)
        
        if not all_csv_content:
            status_label_popup.config(text="No valid data was generated from any image.", foreground="red")
            return
            
        final_csv_string = all_csv_content[0] + "\n" + "\n".join(all_csv_content[1:])

        popup_window.destroy()
        start_data_load(final_csv_string, date, robot_id, is_content=True) 
        
    except APIError as e:
        status_label_popup.config(text=f"Gemini API Error: {e.args[0]}", foreground="red")
    except ImportError:
        status_label_popup.config(text="Error: 'google-genai' library not found. Please install it.", foreground="red")
    except Exception as e:
        status_label_popup.config(text=f"An error occurred: {e}", foreground="red")


def show_image_to_csv_popup(date, robot_id):
    """Popup to select the image file."""
    popup = tk.Toplevel(root)
    popup.title("Generate Report from Image")
    popup.grab_set()
    popup_frame = ttk.Frame(popup, padding=20)
    popup_frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(popup_frame, text="Select ONE or MORE image files (Ctrl/Shift+Click):").pack(pady=(0, 10))

    file_path_var = tk.StringVar()
    file_path_label = ttk.Label(popup_frame, textvariable=file_path_var, text="No files selected.")
    file_path_label.pack(pady=(0, 5))

    status_label_popup = ttk.Label(popup_frame, text="", foreground="black")
    status_label_popup.pack(pady=(0, 10))
    
    selected_filepaths = [] 

    def select_image_file():
        nonlocal selected_filepaths
        
        filepaths = filedialog.askopenfilenames( 
            title="Select Image Files",
            initialdir=os.path.expanduser("~"),
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg"),
                ("All Files", "*.*")
            ]
        )
        
        if filepaths:
            selected_filepaths = filepaths 
            
            if len(filepaths) == 1:
                file_path_var.set(f".../{filepaths[0].split('/')[-1]}")
            else:
                file_path_var.set(f"{len(filepaths)} files selected.")
                
            status_label_popup.config(text="Files selected. Click Generate.", foreground="black")
            generate_button.config(state=tk.NORMAL)
        else:
            file_path_var.set("No files selected.")
            status_label_popup.config(text="", foreground="black")


    def generate_and_continue():
        if selected_filepaths:
            generate_csv_from_image(selected_filepaths, date, robot_id, popup, status_label_popup)

    select_button = ttk.Button(popup_frame, text="Browse for Images", command=select_image_file)
    select_button.pack(pady=(0, 10))

    generate_button = ttk.Button(popup_frame, text="Generate & Continue", command=generate_and_continue, state=tk.DISABLED)
    generate_button.pack()

def check_csv_for_report_details(filepath):
    """
    Checks the first 5 rows of an existing CSV for consistent 'Date' and 'Robot ID'.
    Returns (Date, Robot ID) if valid and consistent, otherwise (None, None).
    """
    date_val, robot_id_val = None, None
    found_data = False
    
    try:
        with open(filepath, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Check the first few rows for consistency
            for i, row in enumerate(reader):
                if i >= 5: # Only check the first 5 rows
                    break
                
                current_date = row.get("Date", "").strip()
                current_robot_id = row.get("Robot ID", "").strip()
                
                if not current_date and not current_robot_id:
                    continue
                
                if not found_data:
                    # First row with data sets the baseline
                    date_val = current_date
                    robot_id_val = current_robot_id
                    found_data = True
                else:
                    # Check for consistency with the baseline
                    if date_val != current_date or robot_id_val != current_robot_id:
                        # Inconsistent data means we must prompt the user
                        return None, None
            
        # If we found consistent data and the values are not empty
        if found_data and date_val and robot_id_val:
            return date_val, robot_id_val
        
        # If headers exist but data is empty, or no data was found
        return None, None
        
    except Exception:
        # If the file can't be read or headers are missing, default to prompting
        return None, None


def choose_csv_file():
    """
    Menu to choose between loading an existing CSV or generating from an image.
    """
    popup = tk.Toplevel(root)
    popup.title("Load Data Option")
    popup.grab_set()
    popup_frame = ttk.Frame(popup, padding=20)
    popup_frame.pack(fill=tk.BOTH, expand=True)
    
    ttk.Label(popup_frame, text="How would you like to load the delivery data?", font=("TkDefaultFont", 10, "bold")).pack(pady=10)
    
    def select_existing_csv():
        popup.destroy()
        filepath = filedialog.askopenfilename(
            title="Select an Existing CSV file",
            filetypes=[("CSV files", "*.csv")]
        )
        if filepath:
            date, robot_id = check_csv_for_report_details(filepath)
            
            if date and robot_id:
                # SKIP PROMPT: Start data load directly with extracted values
                status_label.config(text=f"Report details found in CSV. Loading data...", anchor=tk.W, foreground="darkgreen")
                start_data_load(filepath, date, robot_id)
            else:
                # SHOW PROMPT: Report details were missing or inconsistent
                show_confirmation_popup(filepath)
            
    def select_generate_from_image():
        popup.destroy()
        show_confirmation_popup(is_image_mode=True)

    ttk.Button(popup_frame, text="1. Load Existing CSV File", command=select_existing_csv).pack(fill='x', pady=5)
    ttk.Button(popup_frame, text="2. Generate from Image (Gemini API)", command=select_generate_from_image).pack(fill='x', pady=5)

def show_confirmation_popup(filepath=None, is_image_mode=False):
    """Confirmation popup for report details."""
    popup = tk.Toplevel(root)
    popup.title("Confirm Report Details")
    popup.grab_set()
    popup_frame = ttk.Frame(popup, padding=20)
    popup_frame.pack(fill=tk.BOTH, expand=True)

    # Note: The image shows DD/MM/YYYY, so we stick with that format.
    date_label = ttk.Label(popup_frame, text="Date (DD/MM/YYYY):")
    date_label.pack(pady=(0, 5))
    date_entry = ttk.Entry(popup_frame)
    current_date = datetime.now().strftime("%d/%m/%Y")
    date_entry.insert(0, current_date)
    date_entry.pack(pady=(0, 10))

    robot_label = ttk.Label(popup_frame, text="Robot ID:")
    robot_label.pack(pady=(0, 5))
    robot_options = ["", "506", "512", "968" , "970" , "972"] 
    robot_id_var = tk.StringVar(popup_frame)
    robot_dropdown = ttk.Combobox(popup_frame, textvariable=robot_id_var, values=robot_options, state="readonly")
    robot_dropdown.pack(pady=(0, 10))
    
    status_label_popup = ttk.Label(popup_frame, text="", foreground="red")
    status_label_popup.pack(pady=(0, 10))
    
    def validate_and_continue():
        if robot_id_var.get():
            date = date_entry.get()
            robot_id = robot_id_var.get()
            popup.destroy()
            
            if is_image_mode:
                show_image_to_csv_popup(date, robot_id)
            else:
                start_data_load(filepath, date, robot_id)
        else:
            status_label_popup.config(text="Please select a Robot ID to continue.")

    continue_button = ttk.Button(popup_frame, text="Continue", command=validate_and_continue)
    continue_button.pack()


def start_data_load(source, date, robot_id, is_content=False):
    """
    Loads data into the application.
    """
    global delivery_data
    delivery_data = []
    for row in tree.get_children():
        tree.delete(row)
        
    unique_rows = set()
    rows_skipped = 0 
    
    try:
        if is_content:
            csvfile = StringIO(source)
            reader = csv.DictReader(csvfile)
            source_name = "Gemini Generated Data"
        else:
            filepath = source
            csvfile = open(filepath, 'r', newline='')
            reader = csv.DictReader(csvfile)
            source_name = filepath.split('/')[-1]

        fieldnames_from_source = reader.fieldnames
        id_column_name = None
        
        if 'ID in the Route' in fieldnames_from_source:
            id_column_name = 'ID in the Route'
        elif 'Stop Number' in fieldnames_from_source:
            id_column_name = 'Stop Number' 
        elif 'Stop' in fieldnames_from_source:
            id_column_name = 'Stop' 
            
        if not id_column_name:
            status_label.config(text="Error: Data must contain 'ID in the Route' or 'Stop Number' header.", anchor=tk.W, foreground="red")
            if not is_content: csvfile.close()
            return

        for row in reader:
            new_row = {header: '' for header in field_map.keys()}
            
            for key, value in row.items():
                if key in new_row:
                    new_row[key] = value
            
            # OVERWRITE with the provided/extracted date and robot_id for consistency 
            # and to fill missing columns.
            new_row['Date'] = date
            new_row['Robot ID'] = robot_id
            
            # Use 'Commercial' if the 'Function' field is not present or is empty in the source data.
            new_row['Function'] = new_row.get('Function', 'Commercial') or 'Commercial' 
            
            if id_column_name == 'Stop Number':
                route_id = row.get('Stop Number', '').strip()
            else:
                route_id = row.get(id_column_name, '').strip()

            new_row['ID in the Route'] = route_id
            
            address = new_row.get('Address', '').strip()

            if route_id and address:
                key = (route_id, address)
                
                if key in unique_rows:
                    rows_skipped += 1
                    continue
                
                unique_rows.add(key)
                
                # Default the Success field if it's not valid
                success_value = new_row.get('Success', '')
                if success_value not in field_map['Success']['options']:
                    success_value = ''
                new_row['Success'] = success_value
                
                delivery_data.append(new_row)
                item_id = tree.insert("", "end", values=(route_id, address))
                
                # --- Apply the initial success tag ---
                apply_success_tag(item_id, success_value)
                # ----------------------------------------
            
        if not is_content: csvfile.close()

        # --- AUTO-SAVE INITIALIZATION ---
        initialize_auto_save_file(date, robot_id, source_name)
        # ------------------------------------

        if delivery_data:
            populate_input_fields(delivery_data[0])
            tree.selection_set(tree.get_children()[0])
            on_tree_select(None) 
            # Initial write of the loaded data
            write_data_to_csv()
            
    except Exception as e:
        status_label.config(text=f"An error occurred loading data: {e}", anchor=tk.W, foreground="red")
        if 'csvfile' in locals() and not is_content:
            try: csvfile.close()
            except: pass
            
def on_tree_select(event):
    global selected_row_id, current_address_for_image, current_heading, current_fov
    selected_items = tree.selection()
    if not selected_items:
        return
    
    # Only populate fields and fetch image for the first selected item
    selected_row_id = selected_items[0]
    item_index = tree.index(selected_row_id)
    selected_stop = delivery_data[item_index]
    populate_input_fields(selected_stop)
    
    address_to_fetch = selected_stop.get('Address', '')
    if address_to_fetch:
        # 1. Reset address and FOV
        current_address_for_image = address_to_fetch
        current_fov = 90
        # 2. DO NOT set the heading. Pass None so fetch_and_display_street_view skips it.
        fetch_and_display_street_view(address_to_fetch, heading=None, fov=current_fov)

def zoom_image(event):
    """Handles scroll wheel events for zooming in/out (changing FOV)."""
    global current_fov, current_address_for_image, current_heading
    
    if not current_address_for_image:
        return
        
    if event.num == 5 or event.delta < 0: # Scroll Down (Zoom Out)
        current_fov = min(current_fov + 10, 100)
    elif event.num == 4 or event.delta > 0: # Scroll Up (Zoom In)
        current_fov = max(current_fov - 10, 10)
    else:
        return
        
    fetch_and_display_street_view(current_address_for_image, current_heading, current_fov)

def start_pan(event):
    """Saves the starting x-coordinate of the mouse for panning (right click)."""
    global last_mouse_x, current_address_for_image
    if current_address_for_image:
        last_mouse_x = event.x

def do_pan(event):
    """Calculates the change in heading based on mouse drag and updates the image."""
    global last_mouse_x, current_heading, current_address_for_image
    
    if not current_address_for_image:
        return

    dx = event.x - last_mouse_x
    
    sensitivity = 0.5 * (current_fov / 90.0) 
    
    delta_heading = dx * sensitivity

    new_heading = current_heading - delta_heading
    new_heading %= 360
    if new_heading < 0:
        new_heading += 360
    
    current_heading = new_heading
    last_mouse_x = event.x

    fetch_and_display_street_view(current_address_for_image, current_heading, current_fov, cache_result=False)

def stop_pan(event):
    """Finalizes the pan action by fetching the final image and caching it."""
    global current_address_for_image, current_heading, current_fov
    if current_address_for_image:
        fetch_and_display_street_view(current_address_for_image, current_heading, current_fov, cache_result=True)
        status_label.config(text=f"Image panned to {int(current_heading)}° heading. Click image to open in browser.", anchor=tk.W)

def populate_input_fields(data):
    """Populates the input widgets with data for the selected row."""
    for key, widget in input_widgets.items():
        value = data.get(key, '')
        if isinstance(widget, ttk.Combobox):
            widget.set(value)
        elif isinstance(widget, ttk.Entry):
            widget.delete(0, tk.END)
            widget.insert(0, value)
        elif isinstance(widget, ColorDropdown):
            widget.set(value if value else ColorDropdown.EMPTY_VALUE)
        elif isinstance(widget, tk.Text):
            widget.delete('1.0', tk.END)
            widget.insert('1.0', value)
            
def save_data(field_name_changed=None):
    """
    Saves data from input fields to all currently selected rows in delivery_data.
    """
    global selected_row_id
    selected_items = tree.selection()
    
    if not selected_items:
        return

    # Determine which field(s) to update and what the new value is
    update_data = {}
    current_field_name = None
    
    if field_name_changed:
        # BULK UPDATE MODE: Only update the field that triggered the call
        current_field_name = field_name_changed
        widget = input_widgets.get(field_name_changed)
        if widget is None:
            return

        if isinstance(widget, ttk.Entry):
            update_data[field_name_changed] = widget.get()
        elif isinstance(widget, ColorDropdown):
            update_data[field_name_changed] = widget.get()
        elif isinstance(widget, ttk.Combobox):
            update_data[field_name_changed] = widget.get()
        elif isinstance(widget, tk.Text):
            update_data[field_name_changed] = widget.get('1.0', tk.END).strip()
            
    else:
        # SINGLE UPDATE MODE: Only update the first selected row (e.g., Entry keypress)
        focused_widget = root.focus_get()
        
        # This fallback is primarily for Enter/Entry keypresses where the widget is not a dropdown
        for name, widget in input_widgets.items():
            # Check if the focused widget is the main widget or a child label of ColorDropdown
            if widget is focused_widget or (isinstance(widget, ColorDropdown) and widget.label is focused_widget):
                 current_field_name = name
                 break
                 
        if current_field_name:
            widget = input_widgets.get(current_field_name)
            if isinstance(widget, ttk.Entry):
                update_data[current_field_name] = widget.get()
            elif isinstance(widget, tk.Text):
                update_data[current_field_name] = widget.get('1.0', tk.END).strip()
        else:
             # Fallback to update everything for the *first* selected item if the focus isn't clear
             first_selected_index = tree.index(selected_items[0])
             for key, widget in input_widgets.items():
                 if isinstance(widget, ttk.Combobox):
                     delivery_data[first_selected_index][key] = widget.get()
                 elif isinstance(widget, ttk.Entry):
                     delivery_data[first_selected_index][key] = widget.get()
                 elif isinstance(widget, ColorDropdown):
                     delivery_data[first_selected_index][key] = widget.get()
                 elif isinstance(widget, tk.Text):
                     delivery_data[first_selected_index][key] = widget.get('1.0', tk.END).strip()
             
             # If using the fallback, we still need to auto-save
             write_data_to_csv()
             return


    # Apply the update_data to all selected rows
    success_updated = (current_field_name == 'Success') and ('Success' in update_data)
    new_success_value = update_data.get('Success')
    
    for item in selected_items:
        item_index = tree.index(item)
        
        # Skip the two columns that MUST NOT be bulk-edited: ID in the Route and Address
        fields_to_update = {k: v for k, v in update_data.items() 
                            if k not in ['ID in the Route', 'Address']}
        
        delivery_data[item_index].update(fields_to_update)
        
        # --- Update the Treeview tag if Success changed ---
        if success_updated:
            apply_success_tag(item, new_success_value)
        # ----------------------------------------------------
        
    if current_field_name:
        status_label.config(text=f"Updated '{current_field_name}' for {len(selected_items)} item(s).", anchor=tk.W)
    
    # --- AUTO-SAVE AFTER DATA UPDATE ---
    write_data_to_csv()
    # -----------------------------------
    
def delete_selected_stop():
    """
    Deletes the currently selected row(s) from the Treeview and delivery_data list.
    """
    global delivery_data
    selected_items = tree.selection()
    
    if not selected_items:
        status_label.config(text="No stop selected to delete.", anchor=tk.W, foreground="orange")
        return

    # Use a set to store indices to delete, in reverse order
    # so deleting doesn't shift the indices of items yet to be deleted.
    indices_to_delete = sorted([tree.index(item) for item in selected_items], reverse=True)
    
    deleted_count = 0
    
    for index in indices_to_delete:
        if 0 <= index < len(delivery_data):
            # 1. Remove from the global list
            del delivery_data[index]
            deleted_count += 1
    
    # 2. Remove from the Treeview
    for item in selected_items:
        tree.delete(item)
        
    # 3. Update the data file
    if deleted_count > 0:
        write_data_to_csv()
        status_label.config(text=f"Deleted {deleted_count} stop(s) and auto-saved.", anchor=tk.W, foreground="darkgreen")
        
        # 4. Clear input fields if no more data remains or select the next stop
        if not delivery_data:
            # Clear all input widgets
            for key, widget in input_widgets.items():
                if isinstance(widget, ttk.Combobox):
                    widget.set('')
                elif isinstance(widget, ttk.Entry):
                    widget.delete(0, tk.END)
                elif isinstance(widget, ColorDropdown):
                    widget.set(ColorDropdown.EMPTY_VALUE)
                elif isinstance(widget, tk.Text):
                    widget.delete('1.0', tk.END)
                    
            status_label.config(text="All data deleted. File is empty and auto-saved.", anchor=tk.W, foreground="orange")
        else:
            # Select the item that replaced the first deleted item (which is now at the smallest index)
            try:
                # Find the next item to select. If there's data left, select the first visible item.
                next_item = tree.get_children()[0] 
                tree.selection_set(next_item)
                on_tree_select(None)
            except IndexError:
                # Should not happen if delivery_data is not empty
                pass
            
# --- Helper function for adding the Operator Comments text area ---
def add_comment_text_area(parent, row_idx, label_text):
    """Creates a label and an expanding Text widget with a scrollbar."""
    ttk.Label(parent, text=label_text, font=("TkDefaultFont", 10, "bold")).grid(row=row_idx, column=0, sticky="w", padx=5, pady=(5, 2))
    
    # Container for Text widget and Scrollbar
    text_container = ttk.Frame(parent)
    text_container.grid(row=row_idx + 1, column=0, columnspan=2, sticky="nsew", padx=5)
    text_container.grid_columnconfigure(0, weight=1) 
    text_container.grid_rowconfigure(0, weight=1) 
    
    text_widget = tk.Text(text_container, height=5, width=40, wrap=tk.WORD, bd=1, relief="solid")
    text_widget.grid(row=0, column=0, sticky="nsew")
    
    scrollbar = ttk.Scrollbar(text_container, command=text_widget.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    text_widget.config(yscrollcommand=scrollbar.set)
    
    return text_widget
# ------------------------------------------------------------------

def show_data_summary():
    """
    Generates a summary report popup based on the aggregated data.
    """
    if not delivery_data:
        status_label.config(text="No data to summarize. Please load a CSV first.", anchor=tk.W)
        return
        
    # --- FILTER OUT MISSING DELIVERIES FOR ACCURATE COUNTS ---
    # Create a filtered list of stops that are not marked as "Missing"
    non_missing_data = [row for row in delivery_data if row.get("Success") != "Missing"]
    
    total_deliveries = len(non_missing_data)
    robot_deliveries = 0
    autonomous_returns = 0
    soft_interventions = 0
    physical_interventions = 0
    bad_health_interventions = 0
    connectivity_interventions = 0
    misplaced_orders = 0
    cluttered_pathways = 0
    gates_or_doors = 0
    missing_payload_functionalities = 0
    too_risky_paths = 0
    mobile_hub_success = 0
    parcel_drop_success = 0
    
    intended_robot_deliveries = 0
    
    for row in non_missing_data: # Iterate over the filtered data
        success_status = row.get("Success")
        
        # --- Only count stops with definite Yes or No status (from the non-missing subset) ---
        if success_status in ["Yes", "No"]:
            intended_robot_deliveries += 1
            
        if success_status == "Yes":
            robot_deliveries += 1
            
        if row.get("Autonomous Return") in ["Successful", "Successful partial return"]:
            autonomous_returns += 1
        if row.get("Soft help from Field Operator") == "Needed help":
            soft_interventions += 1
        if row.get("Field Operator physically intervened") == "Needed help":
            physical_interventions += 1
        if row.get("Robot health") == "Broken parts":
            bad_health_interventions += 1
        if row.get("Connectivity") in ["Poor but manageable", "Bad connection"]:
            connectivity_interventions += 1
        if row.get("Order placement") == "Bad placement":
            misplaced_orders += 1
        if row.get("Cluttered environment") == "Path too tight":
            cluttered_pathways += 1
        if row.get("Gated environment") == "Gates":
            gates_or_doors += 1
        if row.get("Payload addressability") in ["Payload issues", "Oversized package"]:
            missing_payload_functionalities += 1
        if row.get("Too risky to try") == "Too risky":
            too_risky_paths += 1
        if row.get("Mobile Hub") == "Successful":
            mobile_hub_success += 1
        if row.get("Did the parcel drop on the first package") == "1st try":
            parcel_drop_success += 1


    popup = tk.Toplevel(root)
    popup.title("Real-World Deliveries Summary")
    popup.transient(root)
    popup.focus_set()
    
    # Configure popup grid to allow the main summary frame to expand
    popup.grid_columnconfigure(0, weight=1)
    popup.grid_rowconfigure(0, weight=1) 
    
    summary_frame = ttk.Frame(popup, padding=10)
    summary_frame.grid(row=0, column=0, sticky="nsew") 
    
    # Configure summary_frame to allow the comments section to expand vertically
    summary_frame.grid_columnconfigure(0, weight=1)
    summary_frame.grid_rowconfigure(1, weight=1) # Row 1 will contain the expandable comments frame
    
    # Inner frame for the statistical labels and single-line entries (non-expanding)
    stats_frame = ttk.Frame(summary_frame)
    stats_frame.grid(row=0, column=0, sticky="ew")
    stats_frame.grid_columnconfigure(0, weight=1)
    stats_frame.grid_columnconfigure(1, weight=1)

    # Frame for the comments text area and close button (expandable)
    comments_frame = ttk.Frame(summary_frame)
    comments_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
    comments_frame.grid_columnconfigure(0, weight=1)
    comments_frame.grid_columnconfigure(1, weight=0)
    comments_frame.grid_rowconfigure(1, weight=1) # Make the Text widget row expandable
    
    def add_label_row(parent, row_idx, label_text, value_text):
        ttk.Label(parent, text=label_text, font=("TkDefaultFont", 10, "bold")).grid(row=row_idx, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(parent, text=value_text, font=("TkDefaultFont", 10)).grid(row=row_idx, column=1, sticky="w", padx=5, pady=2)
        
    def add_entry_row(parent, row_idx, label_text, default_value):
        ttk.Label(parent, text=label_text, font=("TkDefaultFont", 10, "bold")).grid(row=row_idx, column=0, sticky="w", padx=5, pady=2)
        var = tk.StringVar(value=default_value)
        entry = ttk.Entry(parent, textvariable=var, font=("TkDefaultFont", 10))
        entry.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=2)
        return var
        
    first_row = delivery_data[0]
    current_row = 0
    
    # Populate all statistical and single-line entry rows in stats_frame
    # Corrected to show the City/Country as per the screenshot
    add_label_row(stats_frame, current_row, "Date:", first_row.get("Date", ""))
    current_row += 1
    add_label_row(stats_frame, current_row, "Country:", "USA")
    current_row += 1
    add_label_row(stats_frame, current_row, "City:", "Austin")
    current_row += 1
    
    # FIX: Corrected the Area entry call
    summary_inputs["Area"] = add_entry_row(stats_frame, current_row, "Area:", "")
    current_row += 1
    
    add_label_row(stats_frame, current_row, "Robot ID:", first_row.get("Robot ID", ""))
    current_row += 1
    # --- UPDATED TO USE total_deliveries (non_missing_data length) ---
    add_label_row(stats_frame, current_row, "Total # of Deliveries:", str(total_deliveries))
    current_row += 1
    
    add_label_row(stats_frame, current_row, "Intended # of Robot Deliveries:", str(intended_robot_deliveries))
    current_row += 1
    
    add_label_row(stats_frame, current_row, "# of Robot Deliveries:", str(robot_deliveries))
    current_row += 1
    add_label_row(stats_frame, current_row, "# of Autonomous Returns:", str(autonomous_returns))
    current_row += 1
    
    # FIX: Corrected the Revenue entry call
    summary_inputs["Revenue"] = add_entry_row(stats_frame, current_row, "Revenue:", "")
    current_row += 1
    
    add_label_row(stats_frame, current_row, "Customer:", "Veho")
    current_row += 1
    
    # FIX: Corrected the Shift Duration entry call
    summary_inputs["Shift Duration"] = add_entry_row(stats_frame, current_row, "Shift Duration:", "")
    current_row += 1
    
    # FIX: Corrected the Planned Shift Duration entry call
    summary_inputs["Planned Shift Duration"] = add_entry_row(stats_frame, current_row, "Planned Shift Duration:", "")
    current_row += 1
    
    add_label_row(stats_frame, current_row, "# of Soft Interventions:", str(soft_interventions))
    current_row += 1
    add_label_row(stats_frame, current_row, "# of Physical Interventions:", str(physical_interventions))
    current_row += 1
    add_label_row(stats_frame, current_row, "# of Autonomy Interventions:", "0")
    current_row += 1
    add_label_row(stats_frame, current_row, "# of Misplaced Orders:", str(misplaced_orders))
    current_row += 1
    add_label_row(stats_frame, current_row, "# of Bad-Health Interventions:", str(bad_health_interventions))
    current_row += 1
    add_label_row(stats_frame, current_row, "Number of Connectivity Interventions:", str(connectivity_interventions))
    current_row += 1
    add_label_row(stats_frame, current_row, "# of Cluttered Pathways:", str(cluttered_pathways))
    current_row += 1
    add_label_row(stats_frame, current_row, "# of Gates or Doors:", str(gates_or_doors))
    current_row += 1
    add_label_row(stats_frame, current_row, "# of Missing Payload Functionalities:", str(missing_payload_functionalities))
    current_row += 1
    add_label_row(stats_frame, current_row, "# of Too-Risky Paths:", str(too_risky_paths))
    current_row += 1
    add_label_row(stats_frame, current_row, "# of Remote Hub Success", str(mobile_hub_success))
    add_label_row(stats_frame, current_row, "# of Parcel Drop Success", str(parcel_drop_success))
    
    # --- ADD THE OPERATOR COMMENTS TEXT AREA TO comments_frame ---
    # Reusing add_comment_text_area but placed in the comments_frame
    comments_label = ttk.Label(comments_frame, text="Operator Comments:", font=("TkDefaultFont", 10, "bold"))
    comments_label.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 2))
    
    # Container for Text widget and Scrollbar
    text_container = ttk.Frame(comments_frame)
    text_container.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5)
    text_container.grid_columnconfigure(0, weight=1) 
    text_container.grid_rowconfigure(0, weight=1) 
    
    comments_text_widget = tk.Text(text_container, height=5, width=40, wrap=tk.WORD, bd=1, relief="solid")
    comments_text_widget.grid(row=0, column=0, sticky="nsew")
    
    scrollbar_comment = ttk.Scrollbar(text_container, command=comments_text_widget.yview)
    scrollbar_comment.grid(row=0, column=1, sticky="ns")
    comments_text_widget.config(yscrollcommand=scrollbar_comment.set)
    
    # Store the Text widget for external access if needed
    summary_inputs["Operator Comments"] = comments_text_widget 
    
    close_button = ttk.Button(comments_frame, text="Close", command=popup.destroy)
    close_button.grid(row=2, column=0, columnspan=2, pady=10)


def copy_data():
    """Copies data from the currently selected row (only if one is selected) to the clipboard."""
    global copied_data
    selected_items = tree.selection()
    
    if not selected_items:
        status_label.config(text="Please select one row to copy.", anchor=tk.W, foreground="red")
        return
        
    if len(selected_items) > 1:
        status_label.config(text="Copy failed. Please select ONLY ONE stop to copy data from.", anchor=tk.W, foreground="red")
        return
    
    item_index = tree.index(selected_items[0])
    copied_data = delivery_data[item_index].copy()
    status_label.config(text="Data copied successfully.", anchor=tk.W)
    
def paste_data():
    """Pasts the copied data to all currently selected rows."""
    global selected_row_id
    if not copied_data:
        status_label.config(text="No data to paste. Please copy a row first.", anchor=tk.W)
        return
    selected_items = tree.selection()
    if not selected_items:
        status_label.config(text="Please select one or more rows to paste into.", anchor=tk.W)
        return
    
    num_pasted = 0
    for item in selected_items:
        item_index = tree.index(item)
        
        # Preserve the essential, unique fields
        temp_id = delivery_data[item_index]['ID in the Route']
        temp_address = delivery_data[item_index]['Address']
        
        # Apply the copied data
        delivery_data[item_index].update(copied_data)
        
        # Restore the essential, unique fields
        delivery_data[item_index]['ID in the Route'] = temp_id
        delivery_data[item_index]['Address'] = temp_address
        
        # Apply the new success tag if it was in the copied data
        if 'Success' in copied_data:
            apply_success_tag(item, copied_data['Success'])
        
        num_pasted += 1
        
    # Refresh the input fields to show the pasted data (from the first selected item)
    if selected_items:
        first_item_index = tree.index(selected_items[0])
        populate_input_fields(delivery_data[first_item_index])
    
    status_label.config(text=f"Data pasted to {num_pasted} row(s).", anchor=tk.W)
    
    # --- AUTO-SAVE AFTER DATA PASTE ---
    write_data_to_csv()
    # -----------------------------------
    
def create_input_widgets():
    """
    Creates the input widgets based on field_map.
    """
    global input_widgets
    row_count = 0
    
    # Widgets are now created in scrollable_frame, not right_pane
    for field_name, details in field_map.items():
        # Create an outer frame to hold the focus highlight
        field_frame = ttk.Frame(input_widgets_frame, style="TFrame")
        field_frame.grid(row=row_count, column=0, sticky="ew", padx=5, pady=2)
        
        label = ttk.Label(field_frame, text=field_name + ":", width=35)
        label.pack(side="left", padx=(0, 5))
        widget = None
        
        save_data_with_field = (lambda f=field_name: lambda *args: save_data(f))
        
        if details.get("type") == "input":
            if field_name == "Operator Comments":
                text_container = ttk.Frame(field_frame)
                text_container.pack(side="right", fill="x", expand=True)
                text_container.grid_columnconfigure(0, weight=1)
                text_widget = tk.Text(text_container, height=3, width=20, wrap=tk.WORD, bd=1, relief="solid")
                text_widget.grid(row=0, column=0, sticky="nsew")
                
                widget = text_widget
                
                # --- KEY CHANGE: Bind to <KeyRelease> for instant saving ---
                widget.bind("<KeyRelease>", save_data_with_field(field_name)) 
                
                # --- Keyboard navigation for Text widget ---
                widget.bind("<FocusIn>", lambda e: apply_focus_style(e, True))
                # FocusOut is now only for visual style, saving is done on KeyRelease
                widget.bind("<FocusOut>", lambda e: apply_focus_style(e, False)) 
                widget.bind("<Up>", focus_next_widget)
                widget.bind("<Down>", focus_next_widget)
                widget.bind("<Tab>", focus_next_widget)
                widget.bind("<Shift-Tab>", focus_next_widget) 
                # -------------------------------------------
                
            else:
                widget = ttk.Entry(field_frame)
                widget.pack(side="right", fill="x", expand=True)

                # --- Keyboard navigation for Entry widget ---
                widget.bind("<KeyRelease>", save_data_with_field(field_name)) 
                widget.bind("<FocusIn>", lambda e: apply_focus_style(e, True))
                widget.bind("<FocusOut>", lambda e: apply_focus_style(e, False))
                widget.bind("<Up>", focus_next_widget)
                widget.bind("<Down>", focus_next_widget)
                widget.bind("<Tab>", focus_next_widget)
                widget.bind("<Shift-Tab>", focus_next_widget)
                # --------------------------------------------
                
        elif details.get("type") == "dropdown":
            scheme = COLOR_SCHEMES.get(field_name)
            if scheme:
                widget = ColorDropdown(
                    field_frame,
                    options=details.get("options", []),
                    color_map=scheme,
                    on_change=save_data_with_field(field_name) 
                )
                widget.pack(side="right", fill="x", expand=True)
                # ColorDropdown handles its own label focus/keyboard bindings
            else:
                widget = ttk.Combobox(field_frame, values=details.get("options", []), state="readonly")
                widget.pack(side="right", fill="x", expand=True)
                widget.bind("<<ComboboxSelected>>", save_data_with_field(field_name))
                
                # --- Keyboard navigation for Combobox widget ---
                widget.bind("<FocusIn>", lambda e: apply_focus_style(e, True))
                widget.bind("<FocusOut>", lambda e: apply_focus_style(e, False))
                widget.bind("<Up>", focus_next_widget)
                widget.bind("<Down>", focus_next_widget)
                widget.bind("<Tab>", focus_next_widget)
                widget.bind("<Shift-Tab>", focus_next_widget)
                # ----------------------------------------------
                
        input_widgets[field_name] = widget
        row_count += 1
        
def fetch_and_display_street_view(address, heading=None, fov=90, cache_result=True):
    """
    Fetches and displays a Street View image. If heading is None, relies on the API's default.
    Fix: Uses fixed MIN_IMAGE_WIDTH/HEIGHT to ensure square aspect ratio and stability.
    """
    global street_view_image_label, current_street_view_url, current_heading, MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT
    
    # NOTE: The 'google_api_key' check now correctly uses the global variable.
    if not google_api_key or google_api_key == "":
        status_label.config(text="ERROR: Google Maps API key is invalid or missing. Please update it.", anchor=tk.W, foreground="red")
        # Display generic gray box instead of making API call with invalid key
        # Create a blank image to avoid previous exception handling
        try:
            img_pil = Image.new('RGB', (MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT), color = 'gray')
            img_tk = ImageTk.PhotoImage(img_pil)
            street_view_image_label.configure(image=img_tk, text="API Key Invalid. Check Console.", compound="center", foreground="red")
            street_view_image_label.image = img_tk
        except Exception:
            pass # Fails silently if PIL isn't fully working
        return
        
    current_street_view_url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={requests.utils.quote(address)}&heading={int(current_heading)}&fov={int(fov)}"
    
    # 1. Determine size for display (max size to request from API for quality)
    max_request_width = 1000
    max_request_height = 800
    
    # --- FIX: Use FIXED square dimensions for the display target ---
    display_width = MIN_IMAGE_WIDTH
    display_height = MIN_IMAGE_HEIGHT 
    # -----------------------------------------------------------------

    # Get the actual size of the display label for resizing the final image
    root.update_idletasks()
        
    # 2. Prepare parameters
    params = {
        "key": google_api_key,
        "size": f"{max_request_width}x{max_request_height}",
        "location": address,
        "fov": int(fov),
        "pitch": 0,
    }
    
    # 3. Cache key 
    if heading is not None:
        params["heading"] = int(heading)
        cache_key = f"{address}_{int(heading)}_{fov}" 
    else:
        cache_key = f"{address}_default_{fov}" 
        
    # 4. Check cache
    if cache_result and cache_key in image_cache:
        # Retrieve the original PIL image from the cache (before resizing)
        img_pil_cached = image_cache[cache_key]['pil_img']
        
        # --- RESIZE CACHED IMAGE TO CURRENT FIXED DISPLAY SIZE ---
        img_width, img_height = img_pil_cached.size
        ratio = min(display_width / img_width, display_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)

        img_pil_resized = img_pil_cached.resize((new_width, new_height), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(img_pil_resized)
        
        street_view_image_label.configure(image=img_tk, text="", compound="none")
        street_view_image_label.image = img_tk
        # ---------------------------------------------------

        status_label.config(text=f"Image loaded from cache. (H: {int(current_heading)}°, FOV: {fov}). Click image to open in browser.", anchor=tk.W, foreground="green")
        return

    # Status message before API call
    status_label.config(text=f"Fetching image from API for '{address}' (FOV: {fov})....", anchor=tk.W, foreground="blue")
    
    # 5. Fetch image
    url = "https://maps.googleapis.com/maps/api/streetview"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # 6. Extract the heading from the response headers if not provided
        if heading is None:
            header_content = response.headers.get('X-Google-Imagery-Content-Type', '')
            match = re.search(r'heading=([\d.]+)', header_content)
            if match:
                try:
                    auto_heading = float(match.group(1))
                    current_heading = auto_heading
                except Exception:
                    current_heading = 0 
            else:
                 current_heading = 0

        image_data = response.content
        img_pil = Image.open(io.BytesIO(image_data))
        
        # 7. Resize image to fit the fixed area (preserving aspect ratio)
        img_width, img_height = img_pil.size
        
        # Calculate fit size
        ratio = min(display_width / img_width, display_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)

        img_pil_resized = img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        img_tk = ImageTk.PhotoImage(img_pil_resized)
        
        street_view_image_label.configure(image=img_tk, text="", compound="none")
        street_view_image_label.image = img_tk # Keep a reference
        
        if cache_result:
             # Cache the original, full-size PIL image for subsequent resizing
             image_cache[cache_key] = {
                 'pil_img': img_pil, 
             }
        
        status_label.config(text=f"Image fetched (API Call). (H: {int(current_heading)}°, FOV: {fov}). Click image to open in browser.", anchor=tk.W, foreground="black")
        
    except requests.exceptions.HTTPError as e:
        # This catches 400 errors (like API key invalid/quota exceeded)
        error_text = f"API Error: The Google Maps Platform server rejected your request. The provided API key is invalid."
        
        # Check if the error response text is available and more specific
        try:
             response_text = e.response.text
             if "API key is invalid" in response_text or "Key is missing" in response_text:
                 # Use the default invalid key message
                 pass 
             elif "quota" in response_text:
                 error_text = "API Error: Google Maps Quota Exceeded. Please check billing/limits."
             else:
                 error_text = f"API Error: {e.response.text.split('.')[0]}."
        except Exception:
             pass

        status_label.config(text=error_text, anchor=tk.W, foreground="red")
        
        # Display generic gray box on failure
        try:
            img_pil = Image.new('RGB', (MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT), color = 'darkgray')
            img_tk = ImageTk.PhotoImage(img_pil)
            street_view_image_label.configure(image=img_tk, text="Image Failed to Load.", compound="center", foreground="white")
            street_view_image_label.image = img_tk
        except Exception:
            pass
            
    except Exception as e:
        status_label.config(text=f"An error occurred fetching image: {e}", anchor=tk.W, foreground="red")

def open_browser_link(event):
    """Opens the globally stored Street View URL in the default web browser."""
    global current_street_view_url
    if current_street_view_url:
        try:
            webbrowser.open(current_street_view_url, new=2)
            status_label.config(text="Opened Street View link in browser.", anchor=tk.W, foreground="blue")
        except Exception as e:
            status_label.config(text=f"Error opening browser: {e}", anchor=tk.W, foreground="red")
    else:
        status_label.config(text="No valid Street View URL to open.", anchor=tk.W, foreground="red")


# -------------------------------------------------------------------
# GUI Setup
# -------------------------------------------------------------------
root = tk.Tk()
root.title("Robot Delivery Tracker")
root.geometry("900x650")

style = ttk.Style()
style.configure("TEntry", font=("TkDefaultFont", 12))
style.configure("TCombobox", font=("TkDefaultFont", 12))
# Custom style for the field frame to allow highlightthickness to work universally
style.configure("TFrame", background=root.cget('bg')) 

# Treeview tags
style.map('Treeview',
    foreground=[('selected', 'white')],
    background=[('selected', 'blue')] 
)
style.configure("Treeview", rowheight=30) 

# --- ROOT WINDOW GRID SETUP ---
root.grid_rowconfigure(0, weight=1) # Main content (paned window) row expands
root.grid_rowconfigure(1, weight=0) # Status bar row is fixed height
root.grid_columnconfigure(0, weight=1) # Single column expands
# ------------------------------

main_paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
# Use grid to place the paned window in the expandable row 0
main_paned_window.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0)) 

left_pane = ttk.Frame(main_paned_window, padding="0 0 10 0") 
left_pane.grid_columnconfigure(0, weight=1)
left_pane.grid_rowconfigure(1, weight=1)

right_pane = ttk.Frame(main_paned_window, padding="10 0 0 0") 
right_pane.grid_columnconfigure(0, weight=1)
right_pane.grid_rowconfigure(0, weight=1) # The canvas will take all vertical space

main_paned_window.add(left_pane, weight=1)
main_paned_window.add(right_pane, weight=1)

# --- LEFT PANE (Controls and Treeview) ---
control_frame = ttk.Frame(left_pane)
control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

choose_button = ttk.Button(control_frame, text="Load Data", command=choose_csv_file)
choose_button.pack(side=tk.LEFT)

export_button = ttk.Button(control_frame, text="Export CSV", command=export_csv_file)
export_button.pack(side=tk.LEFT, padx=(10, 0))

summary_button = ttk.Button(control_frame, text="Show Summary", command=show_data_summary)
summary_button.pack(side=tk.LEFT, padx=(10, 0))

copy_button = ttk.Button(control_frame, text="Copy Data", command=copy_data)
copy_button.pack(side=tk.LEFT, padx=(10, 0))

paste_button = ttk.Button(control_frame, text="Paste Data", command=paste_data)
paste_button.pack(side=tk.LEFT, padx=(10, 0))

# --- DELETE BUTTON ---
#delete_button = ttk.Button(control_frame, text="Delete Stop", command=delete_selected_stop)
#delete_button.pack(side=tk.LEFT, padx=(10, 0))
# ---------------------

columns = ("ID in the Route", "Address")
tree = ttk.Treeview(left_pane, columns=columns, show="headings")
# --- UPDATED HEADING FOR STOP NUMBER ---
tree.heading("ID in the Route", text="Stop #") 
# ---------------------------------------
tree.heading("Address", text="Address")
tree.column("ID in the Route", width=120, anchor=tk.CENTER)
tree.column("Address", width=300)
tree.grid(row=1, column=0, sticky="nsew")

tree.tag_configure('Success-Yes', background=GREEN, foreground=FG_ON) 
tree.tag_configure('Success-No', background=RED, foreground=FG_ON)
tree.tag_configure('Success-Skipped', background=YELLOW, foreground=FG_OFF)
tree.tag_configure('Success-Missing', background=LGRAY, foreground=FG_OFF)
tree.tag_configure('Success-None', background='#ffffff', foreground=FG_OFF) 

scrollbar = ttk.Scrollbar(left_pane, orient=tk.VERTICAL, command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
scrollbar.grid(row=1, column=1, sticky="ns")

tree.bind("<<TreeviewSelect>>", on_tree_select)

# --- RIGHT PANE (Inputs and Image) ---
# Create a Canvas for scrolling
canvas = tk.Canvas(right_pane)
canvas.grid(row=0, column=0, sticky="nsew")

# Create a Scrollbar and link it to the canvas
scrollbar_right_pane = ttk.Scrollbar(right_pane, orient="vertical", command=canvas.yview)
scrollbar_right_pane.grid(row=0, column=1, sticky="ns")
canvas.configure(yscrollcommand=scrollbar_right_pane.set)

# Create a frame inside the canvas to hold the actual content
scrollable_frame = ttk.Frame(canvas)

# Place the scrollable_frame inside the canvas
# The width will be managed by on_canvas_configure
canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

# --- MOUSE WHEEL SCROLLING LOGIC ---
def _on_mouse_wheel(event):
    """Scrolls the canvas based on mouse wheel movement."""
    # Determine the scroll direction/amount based on the platform
    if event.delta: # Windows/macOS
        # Scroll 5 units up or down (negative for up, positive for down)
        delta = -1 * (event.delta // 120) * 5
    elif event.num == 4: # Linux scroll up
        delta = -1 * 5
    elif event.num == 5: # Linux scroll down
        delta = 1 * 5
    else:
        return
        
    canvas.yview_scroll(delta, "units")
    
# Bind the mouse wheel events to the canvas's parent to catch events when over any child widget
canvas.bind_all("<MouseWheel>", _on_mouse_wheel) # Windows/macOS
canvas.bind_all("<Button-4>", _on_mouse_wheel)   # Linux scroll up
canvas.bind_all("<Button-5>", _on_mouse_wheel)   # Linux scroll down
# --- END MOUSE WHEEL SCROLLING LOGIC ---


# Configure the canvas scroll region and the frame's width
# Configure the canvas scroll region and the frame's width
def on_canvas_configure(event):
    # Update the scroll region of the canvas
    canvas.configure(scrollregion=canvas.bbox("all"))
    # Ensure the scrollable frame's width matches the canvas's width
    canvas.itemconfig(canvas_window, width=event.width)
    
    # --- FIX: REMOVE canvas.yview_moveto(0.0) from here. ---
    # This was preventing proper initial scroll positioning.

canvas.bind("<Configure>", on_canvas_configure)

# Bind a function to the scrollable_frame's size changes to update scrollregion
# Bind a function to the scrollable_frame's size changes to update scrollregion
def on_frame_configure(event):
    # 1. Update the scroll region based on the content's final size
    canvas.configure(scrollregion=canvas.bbox("all"))
    
    # 2. --- ADDED FIX: Force the scroll bar to reset to the absolute top. ---
    # This addresses the overshoot issue when content changes or on initial load.
    canvas.yview_moveto(0.0) 
    # --------------------------------------------------------------------------

scrollable_frame.bind("<Configure>", on_frame_configure)


# --- NEW: AUTOFILL DROPDOWN FRAME (ROW 0) ---
autofill_frame = ttk.Frame(scrollable_frame)
autofill_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 5))
autofill_frame.grid_columnconfigure(1, weight=1)

ttk.Label(autofill_frame, text="Autofill Options:", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))

# The actual Autofill dropdown
autofill_dropdown = ColorDropdown(
    autofill_frame,
    # === UPDATED LIST ORDER HERE ===
    options=["Clear", "Success", "Bad connection", "Missing Package"], 
    # ===============================
    color_map=AUTOFILL_SCHEME,
    on_change=autofill_data # This is the new callback
)
autofill_dropdown.set(autofill_dropdown.EMPTY_VALUE)
autofill_dropdown.label.config(text="Autofill") # Default text for the dropdown
autofill_dropdown.grid(row=0, column=1, sticky="e") 
# ----------------------------------------------


# --- INPUT WIDGETS FRAME (ROW 1) ---
input_widgets_frame = ttk.Frame(scrollable_frame) # Change parent to scrollable_frame
input_widgets_frame.grid(row=1, column=0, sticky="ew") # Change row from 0 to 1
create_input_widgets()


# --- Image Frame setup for fixed size, left-aligned image (ROW 2) ---
street_view_image_frame = ttk.Frame(scrollable_frame, padding=5) # Change parent to scrollable_frame
street_view_image_frame.grid(row=2, column=0, sticky="nw", pady=(10, 0)) # Change row from 1 to 2

street_view_image_frame.grid_columnconfigure(0, weight=0) 
street_view_image_frame.grid_rowconfigure(0, weight=0) 

street_view_image_label = ttk.Label(
    street_view_image_frame, 
    text="Street View Preview\n\nScroll to Zoom | Right Click to Pan", 
    background="gray", 
    cursor="hand2",
    width=MIN_IMAGE_WIDTH // 8
)
street_view_image_label.grid(row=0, column=0, sticky="w") 

street_view_image_label.bind("<Button-1>", open_browser_link)
street_view_image_label.bind("<Button-4>", zoom_image)
street_view_image_label.bind("<Button-5>", zoom_image)
street_view_image_label.bind("<MouseWheel>", zoom_image)
street_view_image_label.bind("<Button-3>", start_pan)
street_view_image_label.bind("<B3-Motion>", do_pan)
street_view_image_label.bind("<ButtonRelease-3>", stop_pan)


# ----------------------------------------------------------------------------------
# --- STATUS BAR AND VERSION LABEL (MOVED TO BOTTOM OF ROOT) ---

# 1. Create the new status label (using a Frame/Label combination for alignment)
# We use a Label here directly for simplicity, but anchor it West (left)
status_label = tk.Label(
    root, 
    text="Select a CSV file to get started.", 
    anchor=tk.W, 
    background='lightgray', 
    padx=10, # Add horizontal padding
    pady=2, # Add vertical padding
    relief=tk.SUNKEN # Give it a status bar look
)

# 2. Place it in the bottom row (row 1) of the root window's grid
status_label.grid(row=1, column=0, sticky="ew")

# 3. Create/Relocate the version label inside the status_label
version_label = tk.Label(status_label, text=f"v{APP_VERSION}", font=("TkDefaultFont", 8), fg="gray", background='lightgray')
version_label.pack(side=tk.RIGHT, padx=5) # Use pack inside the status_label to push it right

# ----------------------------------------------------------------------------------

# --- BIND KEYBOARD SHORTCUTS FOR COPY/PASTE ---
# Binds Ctrl+c (Windows/Linux) and Command+c (macOS) to copy_data
root.bind('<Control-c>', lambda e: copy_data())
root.bind('<Command-c>', lambda e: copy_data())

# Binds Ctrl+v (Windows/Linux) and Command+v (macOS) to paste_data
root.bind('<Control-v>', lambda e: paste_data())
root.bind('<Command-v>', lambda e: paste_data())
# ----------------------------------------------

# ------------------------------------------------
# CHECK FOR UPDATES ON STARTUP
# ------------------------------------------------
check_for_update()

root.mainloop()