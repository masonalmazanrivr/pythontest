# 🤖 Robot Delivery Tracker App Guide

This application was built using Python and the `tkinter` library to streamline the process of tracking robot deliveries, annotating outcomes, and generating comprehensive reports.

---

## 🚀 Program Usage

Launch by extracting the zip to your desktop. Open $\text{phythontest} > \text{dist} > \text{delivery\_tracker\_app}$.

Once launched, the application's interface is divided into the **Stop List** (left) and the **Data Fields & Street View** (right).

---

## I. Data Management and Loading

### 1. Loading Addresses

Click the **Load Data** button to choose your preferred method for importing stop data. You must select the **Date** and the **Robot ID** (e.g., 506, 512, 968) before proceeding.

* **Load Existing CSV:** Upload a CSV file structured with at least two required columns: **Stop \#** (or `ID in the Route`) and **Address**.
* **Generate from Image (Gemini API):** Upload one or more images (manifests, screenshots, etc.) containing the delivery stops. The **Gemini API** will extract the Stop Number and Address list and format it for the tracker.

### 2. Deleting Stops (New Feature)

* **Delete Stop:** Select one or more rows in the left **Stop List** and click the **Delete Stop** button to permanently remove them from the list. The changes are immediately reflected in the auto-save file.

---

## II. Data Entry and Annotation

### 3. Data Entry Workflow

* **Select a Stop:** Addresses populate the left column under the clear header **Stop \#**. Selecting a stop loads its specific data into the right-hand fields and displays the corresponding static Street View image.
* **Edit Fields:** Use the color-coded dropdowns and text inputs on the right to log the outcome of the delivery attempt.
* **Automatic Saving:** **Changes are saved automatically** to a temporary auto-save file (`autosave_report_[...]`) upon interacting with a dropdown, typing in an entry box, or using Paste.

### 4. Street View Interaction (Visual Context)

The bottom right panel provides a visual preview of the delivery location using the Google Street View Static API.

* **Zoom:** Hover over the street view image and use the **scroll wheel (up/down)** to zoom in or out (changing the Field of View or FOV).
* **Pan:** **Hold right click and drag slowly** to pan the camera angle (Heading).
* **Open Full View:** **Click the Street View image** (left click) to open the full interactive panorama in your default web browser for a 360-degree view.

### 5. Copy & Paste Data (Bulk Entry)

This feature is designed for quickly logging identical outcomes across multiple stops. It works using both buttons and standard keyboard shortcuts.

* **Copy Data ($\text{Ctrl}+\text{C}$ / $\text{Cmd}+\text{C}$):** Select **exactly one completed row** and click **Copy Data** or use the shortcut. This copies all field values (excluding Stop \# and Address).
* **Paste Data ($\text{Ctrl}+\text{V}$ / $\text{Cmd}+\text{V}$):** Select **one or more target rows** (using Shift + Click or Ctrl + Click) and click **Paste Data** or use the shortcut to apply all copied field values to the selections. (The Stop \# and Address remain unchanged.)

---

## III. Reporting and Export

### 6. End-of-Day Reporting

Click **Show Summary** to generate a statistics pop-up window.

* **Automatic Metrics:** This report automatically calculates key metrics (e.g., \# of Robot Deliveries, \# of Interventions, \# of Too-Risky Paths) based on the current sheet data.
* **Manual Entry:** Fields like **Revenue** and **Shift Duration** must be entered manually into the pop-up before you screenshot or save the final report.
* *(Note: Location and Customer fields are currently hardcoded to Austin, US, and Veho.)*

### 7. Exporting Data

Click **Export CSV** to save a final `.csv` file containing all the original stop information and the fully recorded outcomes. This file can be used for final archival or integration into the master tracking sheet.

---

## ⚙️ Setup and Installation through Visual Studio Code

### Dependencies

To run or build the application through Visual Studio Code, ensure you have the following packages installed:

| Package | Purpose | Installation |
| :--- | :--- | :--- |
| **Pillow** | Image handling for Street View and Gemini | `pip install Pillow` |
| **google-genai** | API interface for image processing | `pip install google-genai` |
| **requests** | HTTP requests (API calls and Update Check) | `pip install requests` |
| **PyInstaller** | (Optional) Building the executable | `pip install pyinstaller` |

### API Key Requirements

The application requires the following Google API keys to function, which **must be set in the Python source code** (`delivery_tracker_app.py`):

| API | Purpose |
| :--- | :--- |
| **Google Gemini API** | Generating address lists from images. |
| **Street View Static & Geocoding APIs** | Fetching and displaying static street view images. |

### 🏗️ Building the Executable

Follow these steps in your terminal to create a standalone executable using PyInstaller:

1.  **Locate the Project Folder:** Navigate to your project directory (e.g., `cd ~/Desktop/pythontest`).
2.  **Enter Virtual Environment:** Activate your Python virtual environment (if used): `source venv/bin/activate` (Bash).
3.  **Run the Build Command:** Execute PyInstaller. The `--hidden-import` ensures the GUI libraries are included:
    ```bash
    pyinstaller --onefile --hidden-import=PIL._tkinter_finder delivery_tracker_app.py
    ```

### Running the Program

* **To View Code:** Launch `delivery_tracker_app.py` directly using Python.
* **To Run App:** Open the `dist` folder and launch the `delivery_tracker_app` executable.

*(Troubleshooting (Linux): If you get an error, right-click the app, go to Properties, and ensure the permission "Executable as Program" is enabled.)*
