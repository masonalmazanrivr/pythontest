🤖 Robot Delivery Tracker App Guide
This application was built using Visual Studio Code to streamline the process of tracking robot deliveries and generating comprehensive reports.

**⚙️ Setup and Installation**
Dependencies
To run or build the application, ensure you have the following packages installed (most should be in your virtual environment):

Python (Base language)

PyInstaller (pip install pyinstaller)

Pillow (pip install Pillow)

API Key Requirements
The application requires the following Google API keys to function, which must be set in the Python source code (delivery_tracker_app.py):

API	Purpose	Console Link
Google Gemini API	Generating address lists from images.	Google AI Studio
Street View Static & Geocoding APIs	Fetching and displaying static street view images.	Google Cloud Console

Export to Sheets
🏗️ Building the Executable
Follow these steps in your terminal to create a standalone executable using PyInstaller:

Locate the Project Folder: Navigate to your project directory (e.g., cd ~/Desktop/pythontest).

Enter Virtual Environment: Activate your Python virtual environment (if used):

Bash
source venv/bin/activate

Run the Build Command: Execute PyInstaller. The --hidden-import ensures the GUI libraries are included:

Bash
pyinstaller --onefile --hidden-import=PIL._tkinter_finder delivery_tracker_app.py

Running the Program
To View Code: Launch delivery_tracker_app.py directly using Python.

To Run App: Open the dist folder and launch the delivery_tracker_app executable.

Troubleshooting (Linux): If you get an error, right-click the app, go to Properties, and ensure the permission "Executable as Program" is enabled.

**🚀 Program Usage**
Once launched, the application's interface is divided into the Address List (left), and the Data Fields & Street View (right).

1. Loading Addresses
Click the "Choose CSV File" button to load your stop data:

Load Existing CSV: Upload a CSV file structured with at least two columns: Stop # and Address.

Generate from Image (Gemini API): Upload one or more images containing the delivery manifest or addresses. The Gemini API will extract and format the list.

You must select the Robot ID (e.g., 506, 512) before loading the addresses.

2. Data Entry Workflow
Select a Stop: Addresses populate the left column. Selecting an address loads its data into the right-hand fields and displays the corresponding static Street View image.

Edit Fields: Use the color-coded dropdowns and text inputs on the right to log the outcome of the delivery attempt. Changes are saved automatically upon interaction.

Street View Panorama: Click the Street View image (bottom right) to open the full interactive panorama in your default web browser for context.

3. Copy & Paste Data
This feature is designed for quickly logging identical outcomes across multiple stops:

Select a completed row and click Copy Data.

Select one or more target rows (using Shift + Click or Ctrl + Click).

Click Paste Data to apply all copied field values to the selected rows. (The Stop # and Address remain unchanged.)

4. End-of-Day Reporting
Click "Show Summary" to generate a statistics pop-up:

This report automatically calculates key metrics (e.g., # of Robot Deliveries, # of Interventions) from your sheet data.

Manual Entry: Certain fields (Revenue, Shift Duration, etc.) must be entered manually into the pop-up before you screenshot the final report for posting.

(Note: Location and Customer fields are currently hardcoded to Austin, US, and Veho.)

5. Exporting Data
Click "Export CSV" to save a final .csv file containing all the original data and the recorded outcomes. This data can be directly pasted into the master delivery tracking sheet.
