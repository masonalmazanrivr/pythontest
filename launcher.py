# launcher.py

import subprocess
import sys
import os
import time
from tkinter import messagebox # <--- ADD THIS IMPORT
# --- Configuration ---
# NOTE: MAIN_APP_NAME is now the name of the *executable file* created by PyInstaller
MAIN_APP_NAME = "delivery_tracker_app" 
UPDATE_EXIT_CODE = 42 

def run_main_app():
    """
    Starts the main application in a loop, handling frozen vs. script execution.
    """
    
    # 1. Determine the Base Directory
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
        # Path to the bundled EXECUTABLE file (no .py)
        app_path = os.path.join(base_dir, MAIN_APP_NAME)
    else:
        base_dir = os.path.dirname(__file__)
        # Path to the PYTHON SCRIPT (for dev testing)
        app_path = os.path.join(base_dir, MAIN_APP_NAME + ".py")

    
    print(f"[Launcher] Running application from: {app_path}")

    while True:
        print(f"[{time.strftime('%H:%M:%S')}] Launching {MAIN_APP_NAME}...")
        
        try:
            # We explicitly run the file using the system's default shell/runner
            # This is the command that gets executed when the user double-clicks.
            # Using the absolute path prevents many hidden shell path errors.
            command = [app_path]
            
            # Execute the command
            process = subprocess.run(command, check=False)
            
        except Exception as e:
            print(f"[FATAL ERROR] Subprocess failed to start: {e}. Exiting.")
            sys.exit(1)
        
        
        if process.returncode == UPDATE_EXIT_CODE:
            # Code 42: Update was successful and the main app overwrote itself.
            print(f"[{time.strftime('%H:%M:%S')}] Update signal (code {UPDATE_EXIT_CODE}) received. Relaunching...")
            time.sleep(1) 
            continue
            
        elif process.returncode != 0:
            # Non-zero exit code (e.g., 1, 127). This indicates a crash or system error.
            print(f"[FATAL ERROR] Main app crashed! Exit Code: {process.returncode}. Exiting launcher.")
            # Show a message box to the user since the crash was non-zero
            messagebox.showerror(
                "Application Crash",
                f"The application closed unexpectedly (Exit Code: {process.returncode}).\n\n"
                "Check the terminal for details."
            )
            break
            
        else:
            # Code 0: Clean exit (user closed the window normally).
            print(f"[{time.strftime('%H:%M:%S')}] Application closed cleanly. Exiting launcher.")
            break

if __name__ == "__main__":
    run_main_app()