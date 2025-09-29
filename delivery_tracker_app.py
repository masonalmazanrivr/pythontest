import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import csv
from datetime import datetime
import requests
from PIL import Image, ImageTk
import io
# NEW BROWSER IMPORT
import webbrowser # <-- ADDED THIS IMPORT

# NEW GEMINI IMPORTS
from google import genai
from google.genai.errors import APIError
from io import StringIO

# ---------- Colorized dropdown widget (toggle + click-away) ----------
class ColorDropdown(tk.Frame):
    """Colored dropdown using an overrideredirect Toplevel menu."""
    def __init__(self, parent, options, color_map, on_change=None):
        super().__init__(parent)
        self.options = options
        self.color_map = color_map
        self.on_change = on_change
        self.value = ""
        self.dropdown = None
        self.label = tk.Label(self, text="", bd=1, relief="solid", padx=8, pady=4, cursor="hand2")
        self.label.pack(fill="x", expand=True)
        # open/close toggle
        self.label.bind("<Button-1>", self._on_label_click)
        self.label.bind("<space>", self._on_label_key)
        self.label.bind("<Return>", self._on_label_key)
        # global click-away closer
        self.winfo_toplevel().bind("<ButtonRelease-1>", self._on_root_click, add="+")
        
    def _on_label_click(self, _e):
        self._open_menu()
        return "break"
        
    def _on_label_key(self, _e):
        self._open_menu()
        return "break"
        
    def _open_menu(self, *_):
        # toggle
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
            
        # position under the widget
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self.dropdown.geometry(f"+{x}+{y}")
        self.dropdown.bind("<Escape>", lambda e: self._close_menu())
        self.dropdown.focus_set()
        
        # items
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
        # no menu; nothing to do
        if not (self.dropdown and self.dropdown.winfo_exists()):
            return
        # click inside menu? ignore
        if self._point_in_widget(self.dropdown, event.x_root, event.y_root):
            return
        # click on opener label? let the label handler toggle instead
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
            self.on_change()
            
    def set(self, val: str):
        self.value = val or ""
        bg, fg = self.color_map.get(self.value, ("#ffffff", "#000000"))
        text = self.value if self.value else "Select…"
        self.label.configure(text=text, bg=bg, fg=fg)
        
    def get(self) -> str:
        return self.value
        
# -------------------------------------------------------------------
# Global state
delivery_data = []
selected_row_id = None
input_widgets = {}
summary_inputs = {}
copied_data = {} 

# NEW GLOBAL URL VARIABLE
current_street_view_url = "" # <-- ADDED THIS

# NOTE: REPLACE THESE WITH YOUR ACTUAL KEYS!
google_api_key = "AIzaSyBKE225e5Eq4tEyAPqJXO_Hd5grSeoYcqc" # Google Maps Street View API Key
GEMINI_API_KEY = "AIzaSyCDcp2WtRkpsuUsr3b3rTN_mkErQXsdv1I" # Gemini API Key for image processing

image_cache = {}
street_view_image_label = None

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
    "Operator Comments": {"type": "input"},
}

# ---------- Color schemes ----------
# Corrected invalid non-printable characters (U+00A0)
GREEN = "#1f7a3f"  # dark green pill
RED = "#a31212"    # red pill
YELLOW = "#f1d48a" # yellow tag
LGRAY = "#d9d9d9"  # light gray
FG_ON = "#ffffff"
FG_OFF = "#000000"
LGREEN = "#cfecc9" # light green tag (for partial return)

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

# ----------------- NEW GEMINI FUNCTIONS (Updated for Multi-File) -----------------

def generate_csv_from_image(image_filepaths, date, robot_id, popup_window, status_label_popup):
    """
    Sends multiple image files to the Gemini API, extracts addresses from each,
    concatenates the results, and then starts the data loading process.
    """
    try:
        if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE" or not GEMINI_API_KEY:
            status_label_popup.config(text="Error: Please set your actual GEMINI_API_KEY.", foreground="red")
            return
            
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        all_csv_content = []
        
        # Define a cleaning function to remove non-CSV lines
        def clean_csv_output(text, is_first_image):
            # Split lines and filter out lines that clearly aren't CSV data/header
            lines = text.strip().split('\n')
            clean_lines = []
            
            # The header line we expect (case-insensitive check)
            expected_header_lower = "stop number,address"
            
            for line in lines:
                line_stripped = line.strip().lower()
                
                # Rule 1: Skip if it looks like a markdown pipe table separator or extra text
                if "---" in line_stripped or "here is the extracted data" in line_stripped:
                    continue
                
                # Rule 2: Skip any line that starts with { (likely JSON) or just text
                if line_stripped.startswith('{') or line_stripped.startswith('"'):
                    continue
                
                # Rule 3: Handle the header row
                is_header_match = line_stripped.replace('"', '').replace("'", '').replace(' ', '') == expected_header_lower.replace(' ', '')
                
                if is_header_match:
                    # If it's the first image, keep the header. Otherwise, skip it.
                    if is_first_image:
                        clean_lines.append(line)
                    continue

                # Rule 4: Must contain a comma (the CSV separator) to be considered data
                if ',' in line:
                    clean_lines.append(line)
                    
            # If it's the first image, and we didn't find the header, add a fallback header
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

            # Clean the output before combining
            cleaned_content = clean_csv_output(csv_content, is_first_image=(i == 0))
            if cleaned_content:
                all_csv_content.append(cleaned_content)
        
        if not all_csv_content:
            status_label_popup.config(text="No valid data was generated from any image.", foreground="red")
            return
            
        # Join all content
        final_csv_string = "\n".join(all_csv_content)
        
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
    
    selected_filepaths = [] # Now a list/tuple of paths

    def select_image_file():
        nonlocal selected_filepaths
        
        # MODIFIED: Use askopenfilenames (plural) to allow multiple selections
        filepaths = filedialog.askopenfilenames( 
            title="Select Image Files",
            initialdir="/home/mason/Desktop/images", # Added initialdir fix
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg"),
                ("All Files", "*.*") # Added "All Files" fix
            ]
        )
        
        # The result is a tuple of file paths.
        if filepaths:
            selected_filepaths = filepaths 
            
            # Update the label to show how many files were selected
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
            # Pass the tuple of file paths
            generate_csv_from_image(selected_filepaths, date, robot_id, popup, status_label_popup)

    select_button = ttk.Button(popup_frame, text="Browse for Images", command=select_image_file)
    select_button.pack(pady=(0, 10))

    generate_button = ttk.Button(popup_frame, text="Generate & Continue", command=generate_and_continue, state=tk.DISABLED)
    generate_button.pack()

# ----------------- MODIFIED EXISTING FUNCTIONS -----------------

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
    """
    Modified to handle both CSV file selection and image generation flow.
    """
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
    Modified to accept either a file path or the CSV content string directly,
    and now includes logic to SKIP duplicate rows (ID + Address match).
    """
    global delivery_data
    delivery_data = []
    for row in tree.get_children():
        tree.delete(row)
        
    # Set to store unique (ID in the Route, Address) tuples
    unique_rows = set()
    rows_skipped = 0 
    
    try:
        if is_content:
            # StringIO creates a file-like object from the CSV string
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
            
            # 1. Map fields from the source data
            for key, value in row.items():
                if key in new_row:
                    new_row[key] = value
            
            # 2. Populate fixed fields and map the route ID
            new_row['Date'] = date
            new_row['Robot ID'] = robot_id
            new_row['Function'] = new_row.get('Function', 'Commercial') 
            
            if id_column_name == 'Stop Number':
                route_id = row.get('Stop Number', '').strip()
            else:
                route_id = row.get(id_column_name, '').strip()

            new_row['ID in the Route'] = route_id
            
            address = new_row.get('Address', '').strip()

            # 3. Enforce Uniqueness
            if route_id and address:
                key = (route_id, address)
                
                if key in unique_rows:
                    rows_skipped += 1
                    continue  # Skip this row, it's a duplicate
                
                unique_rows.add(key)
                
                # 4. Append and insert into Treeview
                delivery_data.append(new_row)
                tree.insert("", "end", values=(route_id, address))
            
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
            
# ----------------- UNMODIFIED EXISTING FUNCTIONS -----------------

def on_tree_select(event):
    global selected_row_id
    selected_items = tree.selection()
    if not selected_items:
        return
    selected_row_id = selected_items[0]
    item_index = tree.index(selected_row_id)
    selected_stop = delivery_data[item_index]
    populate_input_fields(selected_stop)
    
    address_to_fetch = selected_stop.get('Address', '')
    if address_to_fetch:
        fetch_and_display_street_view(address_to_fetch)

def populate_input_fields(data):
    for key, widget in input_widgets.items():
        value = data.get(key, '')
        if isinstance(widget, ttk.Combobox):
            widget.set(value)
        elif isinstance(widget, ttk.Entry):
            widget.delete(0, tk.END)
            widget.insert(0, value)
        elif isinstance(widget, ColorDropdown):
            widget.set(value)

def save_data():
    global selected_row_id
    if selected_row_id is None:
        return
    item_index = tree.index(selected_row_id)
    for key, widget in input_widgets.items():
        if isinstance(widget, ttk.Combobox):
            delivery_data[item_index][key] = widget.get()
        elif isinstance(widget, ttk.Entry):
            delivery_data[item_index][key] = widget.get()
        elif isinstance(widget, ColorDropdown):
            delivery_data[item_index][key] = widget.get()

def export_csv_file():
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
    """Generates a summary report popup based on the aggregated data."""
    if not delivery_data:
        status_label.config(text="No data to summarize. Please load a CSV first.")
        return
        
    # Calculate key metrics from the loaded data
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
    
    for row in delivery_data:
        if row.get("Success") == "Yes":
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

    # Create the popup window
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
    add_entry_row(summary_frame, current_row, "Intended # of Robot Deliveries:", "")
    current_row += 1
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
        
        # Save unique fields before pasting
        temp_id = delivery_data[item_index]['ID in the Route']
        temp_address = delivery_data[item_index]['Address']
        
        # Update the entire row with copied data
        delivery_data[item_index].update(copied_data)
        
        # Restore unique fields
        delivery_data[item_index]['ID in the Route'] = temp_id
        delivery_data[item_index]['Address'] = temp_address
        
        num_pasted += 1
        
    if selected_items:
        first_item_index = tree.index(selected_items[0])
        populate_input_fields(delivery_data[first_item_index])
    
    status_label.config(text=f"Data pasted to {num_pasted} row(s).")
    
def create_input_widgets():
    global input_widgets
    row_count = 0
    for field_name, details in field_map.items():
        field_frame = ttk.Frame(input_widgets_frame)
        field_frame.grid(row=row_count, column=0, sticky="ew", padx=5, pady=2)
        label = ttk.Label(field_frame, text=field_name + ":", width=25)
        label.pack(side="left", padx=(0, 5))
        widget = None
        if details.get("type") == "input":
            widget = ttk.Entry(field_frame)
            widget.pack(side="right", fill="x", expand=True)
            widget.bind("<KeyRelease>", lambda event: save_data())
        elif details.get("type") == "dropdown":
            scheme = COLOR_SCHEMES.get(field_name)
            if scheme:
                widget = ColorDropdown(
                    field_frame,
                    options=details.get("options", []),
                    color_map=scheme,
                    on_change=save_data
                )
                widget.pack(side="right", fill="x", expand=True)
            else:
                widget = ttk.Combobox(field_frame, values=details.get("options", []), state="readonly")
                widget.pack(side="right", fill="x", expand=True)
                widget.bind("<<ComboboxSelected>>", lambda event: save_data())
        input_widgets[field_name] = widget
        row_count += 1
        
def fetch_and_display_street_view(address):
    """Fetches and displays a Street View image for a given address."""
    global street_view_image_label, current_street_view_url # <-- ADDED current_street_view_url
    
    # Reset URL
    current_street_view_url = ""
    
    if not google_api_key or google_api_key == "YOUR_API_KEY_HERE":
        # Do not show error if the Google Maps key is the placeholder
        return
        
    # Construct the link to the actual Google Maps Street View/Map page
    # This URL works for opening the full interactive map view centered at the address
    current_street_view_url = f"https://www.google.com/maps/search/?api=1&query={requests.utils.quote(address)}" # <-- STORED THE URL
    
    if address in image_cache:
        img_tk = image_cache[address]
        street_view_image_label.configure(image=img_tk)
        street_view_image_label.image = img_tk
        status_label.config(text=f"Loaded image from cache for '{address}'. Click image to open in browser.")
        return
    status_label.config(text=f"Fetching image for '{address}'...")
    
    # URL for the static Street View Image API (used for the display image)
    url = "https://maps.googleapis.com/maps/api/streetview"
    params = {
        "key": google_api_key,
        "size": "400x300",
        "location": address,
        "fov": 90,
        "pitch": 0,
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        image_data = response.content
        img_pil = Image.open(io.BytesIO(image_data))
        img_tk = ImageTk.PhotoImage(img_pil)
        street_view_image_label.configure(image=img_tk)
        street_view_image_label.image = img_tk
        
        image_cache[address] = img_tk
        
        status_label.config(text=f"Image fetched for '{address}'. Click image to open in browser.") # <-- UPDATED STATUS
    except requests.exceptions.HTTPError as e:
        status_label.config(text=f"API Error: {e.response.text}")
    except Exception as e:
        status_label.config(text=f"An error occurred fetching image: {e}")

# NEW FUNCTION TO OPEN BROWSER
def open_browser_link(event):
    """Opens the globally stored Street View URL in the default web browser."""
    global current_street_view_url
    if current_street_view_url:
        try:
            webbrowser.open(current_street_view_url, new=2)  # new=2 opens in a new tab if possible
            status_label.config(text="Opened Street View link in browser.", foreground="blue")
        except Exception as e:
            status_label.config(text=f"Error opening browser: {e}", foreground="red")
    else:
        status_label.config(text="No valid Street View URL to open.", foreground="red")


# --- GUI Setup ---
root = tk.Tk()
root.title("Robot Delivery Tracker")
root.geometry("900x650")

style = ttk.Style()
style.configure("Treeview", rowheight=30)
style.configure("TEntry", font=("TkDefaultFont", 12))
style.configure("TCombobox", font=("TkDefaultFont", 12))

# Use grid for a more precise, flexible layout
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(0, weight=1)

# Left Frame for the list and controls
left_frame = ttk.Frame(root, padding="10")
left_frame.grid(row=0, column=0, sticky="nsew")
left_frame.grid_columnconfigure(0, weight=1)
left_frame.grid_rowconfigure(1, weight=1)

control_frame = ttk.Frame(left_frame)
control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

choose_button = ttk.Button(control_frame, text="Choose CSV File", command=choose_csv_file)
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
tree = ttk.Treeview(left_frame, columns=columns, show="headings")
tree.heading("ID in the Route", text="ID in the Route")
tree.heading("Address", text="Address")
tree.column("ID in the Route", width=120, anchor=tk.CENTER)
tree.column("Address", width=300)
tree.grid(row=1, column=0, sticky="nsew")

scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
scrollbar.grid(row=1, column=1, sticky="ns")

tree.bind("<<TreeviewSelect>>", on_tree_select)

# Right Frame for inputs and image
right_frame = ttk.Frame(root, padding="10")
right_frame.grid(row=0, column=1, sticky="nsew")
right_frame.grid_columnconfigure(0, weight=1)
right_frame.grid_rowconfigure(0, weight=1)
right_frame.grid_rowconfigure(1, weight=1)

input_widgets_frame = ttk.Frame(right_frame)
input_widgets_frame.grid(row=0, column=0, sticky="nsew")
create_input_widgets()

street_view_image_frame = ttk.Frame(right_frame, padding=5)
street_view_image_frame.grid(row=1, column=0, sticky="nsew")

street_view_image_label = ttk.Label(street_view_image_frame, text="Street View Preview", background="gray", cursor="hand2") # <-- ADDED cursor="hand2"
street_view_image_label.pack(fill=tk.BOTH, expand=True)

# BIND THE CLICK EVENT TO THE NEW FUNCTION
street_view_image_label.bind("<Button-1>", open_browser_link) # <-- ADDED THIS BINDING

root.mainloop()