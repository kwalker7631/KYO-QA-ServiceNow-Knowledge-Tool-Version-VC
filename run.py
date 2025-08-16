# run.py
# Author: Kenneth Walker
# Date: 2025-08-15
# Version: VA-1.9 (Final Alpha)
#
# This script serves as the main entry point for the application.
# It provides visual feedback during the environment setup process.

import sys
import subprocess
import venv
from pathlib import Path
import threading
import time
import itertools
import os

# --- Configuration ---
VENV_DIR = Path.cwd() / "venv"
REQUIREMENTS_FILE = Path.cwd() / "requirements.txt"
MAIN_APP_SCRIPT = Path.cwd() / "main_app.py"

KYO_LOGO = r"""
 _   __ __   ____  ______  _____   ____    ___    __
| | / // /  / __/ / ____/ / ___/  / __ \  / _ \  / /
| |/ // /  / /_  / __/   / /__   / /_/ / / // / / /
|___//_/  /___/ /____/  /____/   \____/ /____/ /_/

"""

class Spinner:
    """A simple, clean console spinner for long-running processes."""
    def __init__(self, message="Processing..."):
        self.spinner = itertools.cycle(['-', '/', '|', '\\'])
        self.delay = 0.1
        self.busy = False
        self.spinner_visible = False
        self.message = message
        self.thread = None

    def start(self):
        """Starts the spinner in a separate thread."""
        self.busy = True
        self.thread = threading.Thread(target=self.spinner_task)
        self.thread.start()

    def stop(self):
        """Stops the spinner and cleans up the line."""
        self.busy = False
        if self.thread:
            self.thread.join()
        if self.spinner_visible:
            # Erase the spinner and message
            sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')
            sys.stdout.flush()

    def spinner_task(self):
        """The actual spinner animation loop."""
        while self.busy:
            char = next(self.spinner)
            self.spinner_visible = True
            # Use carriage return to animate on a single line
            sys.stdout.write(f'\r{self.message} {char}')
            sys.stdout.flush()
            time.sleep(self.delay)

def get_venv_python() -> Path:
    """Returns the path to the Python executable inside the virtual environment."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    else: # macOS, Linux
        return VENV_DIR / "bin" / "python"

def create_virtual_environment():
    """Creates a new virtual environment if one doesn't exist."""
    if not VENV_DIR.exists():
        spinner = Spinner("Creating virtual environment...")
        spinner.start()
        try:
            venv.create(VENV_DIR, with_pip=True)
            spinner.stop()
            print("✔ Virtual environment created successfully.")
        except Exception as e:
            spinner.stop()
            print(f"✘ Error: Could not create virtual environment: {e}")
            sys.exit(1)
    else:
        print("✔ Virtual environment already exists.")

def install_dependencies():
    """Installs dependencies from requirements.txt, showing a spinner."""
    python_executable = get_venv_python()
    if not python_executable.exists():
        print(f"✘ Error: Python executable not found in venv at {python_executable}")
        sys.exit(1)

    spinner = Spinner("Installing/updating dependencies...")
    spinner.start()
    try:
        # Run pip commands, but hide the noisy output unless there's an error
        subprocess.check_call(
            [str(python_executable), "-m", "pip", "install", "--upgrade", "pip"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        subprocess.check_call(
            [str(python_executable), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        spinner.stop()
        print("✔ Dependencies are up to date.")
    except subprocess.CalledProcessError as e:
        spinner.stop()
        print(f"✘ Error: Failed to install dependencies.")
        print("Please check your internet connection and the requirements.txt file.")
        sys.exit(1)
    except FileNotFoundError:
        spinner.stop()
        print(f"✘ Error: Could not find '{REQUIREMENTS_FILE}'.")
        sys.exit(1)


def launch_application():
    """Launches the main Tkinter application."""
    python_executable = get_venv_python()
    print(f"\nLaunching application: {MAIN_APP_SCRIPT}")
    try:
        subprocess.call([str(python_executable), str(MAIN_APP_SCRIPT)])
    except Exception as e:
        print(f"✘ Error: Failed to launch the application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Clear the console for a clean start
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(KYO_LOGO)
    print("--- First AI Utility Launcher ---")
    
    create_virtual_environment()
    install_dependencies()
    launch_application()
    
    print("\nApplication has closed. Exiting launcher.")
    if sys.platform == "win32":
        input("Press Enter to exit...")
