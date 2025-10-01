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

# IMAGE INTERACTION GLOBALS
current_address_for_image = ""
current_heading = 0
current_fov = 90
last_mouse_x = 0

# NOTE: REPLACE THESE WITH YOUR ACTUAL KEYS!
google_api_key = "AIzaSyBKE225e5Eq4tEyAPqJXO_Hd5grSeoYcqc" # Google Maps Street View API Key
GEMINI_API_KEY = "AIzaSyCDcp2WtRkpsuUsr3b3rTN_mkErQXsdv1I" # Gemini API Key for image processing

# Field definitions (truncated for brevity)
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
    "Operator Comments": {"type": "input"},
}

# ---------- Color schemes (truncated for brevity) ----------
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
}

# ---------- Colorized dropdown widget (toggle + click-away) ----------
class ColorDropdown(tk.Frame):
    """Colored dropdown using an overrideredirect Toplevel menu."""
    EMPTY_VALUE = "" 
    
    def __init__(self, parent, options, color_map, on_change=None):
        super().__init__(parent)
        self.options = options
        self.color_map = color_map
        self.on_change = on_change
        self.value = self.EMPTY_VALUE
        self.dropdown = None
        self.label = tk.Label(self, text="", bd=1, relief="solid", padx=8, pady=4, cursor="hand2")
        self.label.pack(fill="x", expand=True)
        self.label.bind("<Button-1>", self._on_label_click)
        self.label.bind("<space>", self._on_label_key)
        self.label.bind("<Return>", self._on_label_key)
        self.winfo_toplevel().bind("<ButtonRelease-1>", self._on_root_click, add="+")
        
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
        reset_item.bind("<Enter>", lambda e, w=reset_item: w.configure(relief="solid", bd=1))
        reset_item.bind("<Leave>", lambda e, w=reset_item: w.configure(relief="flat", bd=0))
        reset_item.bind("<Button-1>", lambda e, val=reset_val: self._select(val))
        
        # Separator
        ttk.Separator(self.dropdown, orient=tk.HORIZONTAL).pack(fill='x', pady=2)
        # --- END NEW ---
        
        # Items (existing options)
        for opt in self.options:
            bg, fg = self.color_map.get(opt, ("#f0f0f0", "#000"))
            item = tk.Label(self.dropdown, text=opt, bg=bg, fg=fg, padx=10, pady=6)
            item.pack(fill="x")
            item.bind("<Enter>", lambda e, w=item: w.configure(relief="solid", bd=1))
            item.bind("<Leave>", lambda e, w=item: w.configure(relief="flat", bd=0))
            item.bind("<Button-1>", lambda e, val=opt: self._select(val))
            
    def _close_menu(self):
        if self.dropdown and self.dropdown.winfo_exists():
            try:
                self.dropdown.destroy()
            except Exception:
                pass
        self.dropdown = None
        
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
            field_name = self.master.winfo_children()[0].cget("text").replace(":", "") 
            self.on_change(field_name)
            
    def set(self, val: str):
        self.value = val or self.EMPTY_VALUE 
        
        if self.value == self.EMPTY_VALUE:
            bg, fg = ("#ffffff", "#000000")
            text = "Select…"
        else:
            bg, fg = self.color_map.get(self.value, ("#ffffff", "#000000"))
            text = self.value
            
        self.label.configure(text=text, bg=bg, fg=fg)
        
    def get(self) -> str:
        return self.value

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
            initialdir="/home/mason/Desktop/images",
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

def choose_csv_file():
    """Menu to choose between loading an existing CSV or generating from an image."""
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

    date_label = ttk.Label(popup_frame, text="Date (DD/MM/YYYY):")
    date_label.pack(pady=(0, 5))
    date_entry = ttk.Entry(popup_frame)
    current_date = datetime.now().strftime("%d/%m/%Y")
    date_entry.insert(0, current_date)
    date_entry.pack(pady=(0, 10))

    robot_label = ttk.Label(popup_frame, text="Robot ID:")
    robot_label.pack(pady=(0, 5))
    robot_options = ["", "506", "512", "968"]
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
    MODIFIED: Now applies the success tag to the Treeview item on load.
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
            
        if not id_column_name:
            status_label.config(text="Error: Data must contain 'ID in the Route' or 'Stop Number' header.", foreground="red")
            if not is_content: csvfile.close()
            return

        for row in reader:
            new_row = {header: '' for header in field_map.keys()}
            
            for key, value in row.items():
                if key in new_row:
                    new_row[key] = value
            
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

        status_label.config(text=f"Loaded {len(delivery_data)} stops from '{source_name}'. {rows_skipped} duplicates skipped.", foreground="black")
        if delivery_data:
            populate_input_fields(delivery_data[0])
            tree.selection_set(tree.get_children()[0])
            on_tree_select(None) 
    except Exception as e:
        status_label.config(text=f"An error occurred loading data: {e}", foreground="red")
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
        status_label.config(text=f"Image panned to {int(current_heading)}° heading. Click image to open in browser.")

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
            
def save_data(field_name_changed=None):
    """
    Saves data from input fields to all currently selected rows in delivery_data.
    MODIFIED: Now updates the Treeview tag if the "Success" field is changed.
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
            
    else:
        # SINGLE UPDATE MODE: Only update the first selected row (e.g., Entry keypress)
        focused_widget = root.focus_get()
        
        for name, widget in input_widgets.items():
            if widget is focused_widget or widget.winfo_children() and focused_widget in widget.winfo_children():
                 current_field_name = name
                 break
                 
        if current_field_name:
            widget = input_widgets.get(current_field_name)
            if isinstance(widget, ttk.Entry):
                update_data[current_field_name] = widget.get()
            # Dropdowns are handled by the 'field_name_changed' path
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
        status_label.config(text=f"Updated '{current_field_name}' for {len(selected_items)} item(s).")
            
def export_csv_file():
    """Exports all current data to a CSV file."""
    if not delivery_data:
        status_label.config(text="No data to export. Please load a CSV first.")
        return
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Save Report As"
    )
    if filepath:
        try:
            template_headers = list(field_map.keys())
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=template_headers)
                writer.writeheader()
                writer.writerows(delivery_data)
            status_label.config(text=f"Report saved to '{filepath.split('/')[-1]}'")
        except Exception as e:
            status_label.config(text=f"An error occurred while exporting: {e}")
            
def show_data_summary():
    """
    Generates a summary report popup based on the aggregated data.
    FIXED: Calculates 'Intended # of Robot Deliveries' to only count stops explicitly marked 'Yes' or 'No'.
    """
    if not delivery_data:
        status_label.config(text="No data to summarize. Please load a CSV first.")
        return
        
    total_deliveries = len(delivery_data)
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
    
    intended_robot_deliveries = 0
    
    for row in delivery_data:
        success_status = row.get("Success")
        
        # --- FIX APPLIED HERE: Only count stops with definite Yes or No status ---
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

    popup = tk.Toplevel(root)
    popup.title("Real-World Deliveries Summary")
    popup.transient(root)
    popup.focus_set()
    summary_frame = ttk.Frame(popup, padding=10)
    summary_frame.pack(fill=tk.BOTH, expand=True)
    
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
    add_label_row(summary_frame, current_row, "Real-World Deliveries in Austin 🇺🇸", "")
    current_row += 1
    add_label_row(summary_frame, current_row, "Date:", first_row.get("Date", ""))
    current_row += 1
    add_label_row(summary_frame, current_row, "Country:", "USA")
    current_row += 1
    add_label_row(summary_frame, current_row, "City:", "Austin")
    current_row += 1
    
    add_entry_row(summary_frame, current_row, "Area:", "Terry Town, Allendale, Crest View, West...")
    current_row += 1
    add_label_row(summary_frame, current_row, "Robot ID:", first_row.get("Robot ID", ""))
    current_row += 1
    add_label_row(summary_frame, current_row, "Total # of Deliveries:", str(total_deliveries))
    current_row += 1
    
    # --- MODIFIED: Calculated and displayed as a label ---
    add_label_row(summary_frame, current_row, "Intended # of Robot Deliveries:", str(intended_robot_deliveries))
    current_row += 1
    # ----------------------------------------------------
    
    add_label_row(summary_frame, current_row, "# of Robot Deliveries:", str(robot_deliveries))
    current_row += 1
    add_label_row(summary_frame, current_row, "# of Autonomous Returns:", str(autonomous_returns))
    current_row += 1
    
    add_entry_row(summary_frame, current_row, "Revenue:", "")
    current_row += 1
    add_label_row(summary_frame, current_row, "Customer:", "Veho")
    current_row += 1
    add_entry_row(summary_frame, current_row, "Shift Duration:", "")
    current_row += 1
    add_entry_row(summary_frame, current_row, "Planned Shift Duration:", "")
    current_row += 1
    
    add_label_row(summary_frame, current_row, "# of Soft Interventions:", str(soft_interventions))
    current_row += 1
    add_label_row(summary_frame, current_row, "# of Physical Interventions:", str(physical_interventions))
    current_row += 1
    add_label_row(summary_frame, current_row, "# of Autonomy Interventions:", "0")
    current_row += 1
    add_label_row(summary_frame, current_row, "# of Misplaced Orders:", str(misplaced_orders))
    current_row += 1
    add_label_row(summary_frame, current_row, "# of Bad-Health Interventions:", str(bad_health_interventions))
    current_row += 1
    add_label_row(summary_frame, current_row, "Number of Connectivity Interventions:", str(connectivity_interventions))
    current_row += 1
    add_label_row(summary_frame, current_row, "# of Cluttered Pathways:", str(cluttered_pathways))
    current_row += 1
    add_label_row(summary_frame, current_row, "# of Gates or Doors:", str(gates_or_doors))
    current_row += 1
    add_label_row(summary_frame, current_row, "# of Missing Payload Functionalities:", str(missing_payload_functionalities))
    current_row += 1
    add_label_row(summary_frame, current_row, "# of Too-Risky Paths:", str(too_risky_paths))
    current_row += 1
    
    close_button = ttk.Button(summary_frame, text="Close", command=popup.destroy)
    close_button.grid(row=current_row, column=0, columnspan=2, pady=10)

def copy_data():
    """Copies data from the currently selected row to the clipboard."""
    global copied_data
    selected_items = tree.selection()
    if not selected_items:
        status_label.config(text="Please select a row to copy.")
        return
    
    item_index = tree.index(selected_items[0])
    copied_data = delivery_data[item_index].copy()
    status_label.config(text="Data copied successfully.")
    
def paste_data():
    """Pasts the copied data to all currently selected rows."""
    global selected_row_id
    if not copied_data:
        status_label.config(text="No data to paste. Please copy a row first.")
        return
    selected_items = tree.selection()
    if not selected_items:
        status_label.config(text="Please select one or more rows to paste into.")
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
    
    status_label.config(text=f"Data pasted to {num_pasted} row(s).")
    
def create_input_widgets():
    """Creates the input widgets based on field_map."""
    global input_widgets
    row_count = 0
    for field_name, details in field_map.items():
        field_frame = ttk.Frame(input_widgets_frame)
        field_frame.grid(row=row_count, column=0, sticky="ew", padx=5, pady=2)
        label = ttk.Label(field_frame, text=field_name + ":", width=35)
        label.pack(side="left", padx=(0, 5))
        widget = None
        
        # Get a reference to the field name for passing to save_data
        save_data_with_field = (lambda f=field_name: lambda *args: save_data(f))
        
        if details.get("type") == "input":
            widget = ttk.Entry(field_frame)
            widget.pack(side="right", fill="x", expand=True)
            # Use KeyRelease for real-time saving/updating
            widget.bind("<KeyRelease>", save_data_with_field(field_name)) 
        elif details.get("type") == "dropdown":
            scheme = COLOR_SCHEMES.get(field_name)
            if scheme:
                widget = ColorDropdown(
                    field_frame,
                    options=details.get("options", []),
                    color_map=scheme,
                    # ColorDropdown calls on_change with no args, so we pass field name to its constructor
                    on_change=save_data_with_field(field_name) 
                )
                widget.pack(side="right", fill="x", expand=True)
            else:
                widget = ttk.Combobox(field_frame, values=details.get("options", []), state="readonly")
                widget.pack(side="right", fill="x", expand=True)
                # Use ComboboxSelected for traditional ttk Combobox saving/updating
                widget.bind("<<ComboboxSelected>>", save_data_with_field(field_name))
                
        input_widgets[field_name] = widget
        row_count += 1
        
def fetch_and_display_street_view(address, heading=None, fov=90, cache_result=True):
    """
    Fetches and displays a Street View image. If heading is None, relies on the API's default.
    MODIFIED: Status message now indicates if the image was loaded from the cache.
    """
    global street_view_image_label, current_street_view_url, current_heading
    
    if not google_api_key or google_api_key == "YOUR_API_KEY_HERE":
        status_label.config(text="Error: Please set your actual Google Maps Street View API Key.", foreground="red")
        return
        
    current_street_view_url = f"https://www.google.com/maps/search/?api=1&query={requests.utils.quote(address)}"
    
    # 1. Determine size for display (max size to request from API for quality)
    max_request_width = 1000
    max_request_height = 800
    
    # Get the actual size of the display label for resizing the final image
    root.update_idletasks()
    try:
        display_width = street_view_image_label.winfo_width()
        display_height = street_view_image_label.winfo_height()
        if display_width < 100 or display_height < 100: 
             display_width, display_height = 400, 300 # Fallback 
    except Exception:
        display_width, display_height = 400, 300 # Fallback 
        
    # 2. Prepare parameters
    params = {
        "key": google_api_key,
        "size": f"{max_request_width}x{max_request_height}",
        "location": address,
        "fov": int(fov),
        "pitch": 0,
    }
    
    # 3. Cache key (includes max requested size for uniqueness)
    if heading is not None:
        params["heading"] = int(heading)
        cache_key = f"{address}_{heading:.2f}_{fov}_{max_request_width}x{max_request_height}" 
    else:
        # Note: When heading is None, the actual heading determined by the API must be stored
        # This cache key assumes the API returns a consistent default *for a given location*.
        cache_key = f"{address}_default_{fov}_{max_request_width}x{max_request_height}" 
        
    # 4. Check cache
    if cache_result and cache_key in image_cache:
        img_tk_cached = image_cache[cache_key]['tk_img']
        
        if image_cache[cache_key]['width'] == display_width and image_cache[cache_key]['height'] == display_height:
            street_view_image_label.configure(image=img_tk_cached)
            street_view_image_label.image = img_tk_cached
            
            # --- MODIFIED STATUS MESSAGE FOR CACHE HIT ---
            status_label.config(text=f"Image loaded from cache. (FOV: {fov}). Click image to open in browser.", foreground="green")
            # ---------------------------------------------
            return

    # Status message before API call
    status_label.config(text=f"Fetching image from API for '{address}' (FOV: {fov})...", foreground="blue")
    
    # 5. Fetch image
    url = "https://maps.googleapis.com/maps/api/streetview"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # 6. Extract the heading from the response headers if not provided
        if heading is None:
            header_content = response.headers.get('X-Google-Imagery-Content-Type', '')
            if 'heading=' in header_content:
                try:
                    start = header_content.index('heading=') + 8
                    end = header_content.index(',', start)
                    auto_heading = float(header_content[start:end])
                    current_heading = auto_heading
                except Exception:
                    current_heading = 0 
            else:
                 current_heading = 0

        image_data = response.content
        img_pil = Image.open(io.BytesIO(image_data))
        
        # 7. Resize image to fit the label area (preserving aspect ratio)
        img_width, img_height = img_pil.size
        
        # Calculate fit size
        ratio = min(display_width / img_width, display_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)

        img_pil = img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        img_tk = ImageTk.PhotoImage(img_pil)
        
        street_view_image_label.configure(image=img_tk)
        street_view_image_label.image = img_tk # Keep a reference
        
        if cache_result:
             image_cache[cache_key] = {
                 'tk_img': img_tk, 
                 'width': new_width, 
                 'height': new_height
             }
        
        # --- MODIFIED STATUS MESSAGE FOR API FETCH ---
        status_label.config(text=f"Image fetched (API Call). (H: {int(current_heading)}°, FOV: {fov}). Click image to open in browser.", foreground="black")
        # ---------------------------------------------
        
    except requests.exceptions.HTTPError as e:
        status_label.config(text=f"API Error: {e.response.text}", foreground="red")
    except Exception as e:
        status_label.config(text=f"An error occurred fetching image: {e}", foreground="red")

def open_browser_link(event):
    """Opens the globally stored Street View URL in the default web browser."""
    global current_street_view_url
    if current_street_view_url:
        try:
            webbrowser.open(current_street_view_url, new=2)
            status_label.config(text="Opened Street View link in browser.", foreground="blue")
        except Exception as e:
            status_label.config(text=f"Error opening browser: {e}", foreground="red")
    else:
        status_label.config(text="No valid Street View URL to open.", foreground="red")


# -------------------------------------------------------------------
# GUI Setup
# -------------------------------------------------------------------
root = tk.Tk()
root.title("Robot Delivery Tracker")
root.geometry("900x650")

style = ttk.Style()
style.configure("TEntry", font=("TkDefaultFont", 12))
style.configure("TCombobox", font=("TkDefaultFont", 12))

# --- Treeview Selection Override (Kept here as it is a style.map call on the Toplevel style) ---
style.map('Treeview',
    foreground=[('selected', 'white')],
    background=[('selected', 'blue')] 
)
style.configure("Treeview", rowheight=30) 
# ------------------------------------------------------

main_paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

left_pane = ttk.Frame(main_paned_window, padding="0 0 10 0") 
left_pane.grid_columnconfigure(0, weight=1)
left_pane.grid_rowconfigure(1, weight=1)

right_pane = ttk.Frame(main_paned_window, padding="10 0 0 0") 
right_pane.grid_columnconfigure(0, weight=1)
right_pane.grid_rowconfigure(0, weight=0) 
right_pane.grid_rowconfigure(1, weight=100) 

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

status_label = ttk.Label(control_frame, text="Select a CSV file to get started.")
status_label.pack(side=tk.LEFT, padx=(10, 0))

columns = ("ID in the Route", "Address")
tree = ttk.Treeview(left_pane, columns=columns, show="headings")
tree.heading("ID in the Route", text="ID in the Route")
tree.heading("Address", text="Address")
tree.column("ID in the Route", width=120, anchor=tk.CENTER)
tree.column("Address", width=300)
tree.grid(row=1, column=0, sticky="nsew")

# --- FIXED: Tag configuration is now called on the tree widget itself ---
tree.tag_configure('Success-Yes', background=GREEN, foreground=FG_ON) 
tree.tag_configure('Success-No', background=RED, foreground=FG_ON)
tree.tag_configure('Success-Skipped', background=YELLOW, foreground=FG_OFF)
tree.tag_configure('Success-Missing', background=LGRAY, foreground=FG_OFF)
tree.tag_configure('Success-None', background='#ffffff', foreground=FG_OFF) # Default white
# ------------------------------------------------------------------------

scrollbar = ttk.Scrollbar(left_pane, orient=tk.VERTICAL, command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
scrollbar.grid(row=1, column=1, sticky="ns")

tree.bind("<<TreeviewSelect>>", on_tree_select)

# --- RIGHT PANE (Inputs and Image) ---
input_widgets_frame = ttk.Frame(right_pane)
input_widgets_frame.grid(row=0, column=0, sticky="nsew")
create_input_widgets()

street_view_image_frame = ttk.Frame(right_pane, padding=5)
street_view_image_frame.grid(row=1, column=0, sticky="nsew")
street_view_image_frame.grid_columnconfigure(0, weight=1)
street_view_image_frame.grid_rowconfigure(0, weight=1)

street_view_image_label = ttk.Label(street_view_image_frame, text="Street View Preview\n\nScroll to Zoom | Right Click to Pan", background="gray", cursor="hand2")
street_view_image_label.grid(row=0, column=0, sticky="nsew")

street_view_image_label.bind("<Button-1>", open_browser_link)
street_view_image_label.bind("<Button-4>", zoom_image)
street_view_image_label.bind("<Button-5>", zoom_image)
street_view_image_label.bind("<MouseWheel>", zoom_image)
street_view_image_label.bind("<Button-3>", start_pan)
street_view_image_label.bind("<B3-Motion>", do_pan)
street_view_image_label.bind("<ButtonRelease-3>", stop_pan)

# BIND an event to ensure the map redraws when the window is resized
def resize_handler(event):
    if current_address_for_image and event.widget == street_view_image_label:
        fetch_and_display_street_view(current_address_for_image, current_heading, current_fov, cache_result=False)

street_view_image_label.bind("<Configure>", resize_handler)


root.mainloop()