# run.py
# Author: Kenneth Walker
# Date: 2025-08-18
# Version: VA-2.0 (Enhanced Visuals)
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

# --- ANSI Color Codes for a more engaging console experience ---
class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"

# --- Configuration ---
VENV_DIR = Path.cwd() / "venv"
REQUIREMENTS_FILE = Path.cwd() / "requirements.txt"
MAIN_APP_SCRIPT = Path.cwd() / "main_app.py"

KYO_LOGO = r"""
                                                                                                                                             
                                                                                                    
           &$$$$$$&                                                                                 
         &XXXXXXXX$                                                                                 
 &$$$$$$$$$$$$$XXX$   &$&&   &$&&&$$&   &$$  &&$$$$$$&&  &&$$$$$$& &&$$$$$$& &$$$$$$$$&  &$$$$$$$&  
 &XXXX$&X$    $XXX$   &$&&  &$&& &$$&   &$$  &$&&&&&&$& &$$&&&&&&  $$&&&&&&& &$&&&&&&$&& &&&&&&&&$& 
 &XX$  &XXX$  $XX$    &$&&&&$&   &$$&   &$$  &$&    &$& &$$&       $$&       &$&&   &$&&       &&$& 
 &$    &XXXXX$$$      &$&&$$&    &$$&&&&&$$  &$&    &$& &$$&       $$&&&&&&& &$&&&&&&$&& &&&&&&&&$& 
 &$    &XXXXX$$$      &$&&&$&&    &&&&&&&$$  &$&    &$& &$$&       $$&&&&&&& &$&&&&$&&& &&$&&&&&&$& 
 &XX$  &XXX$  $XX&    &$&& &$&&         &$$  &$&    &$& &$$&       $$&       &$&& &&$&  &&$&   &&$& 
 &XXXX$&X$    $XXX$   &$&&  &$$&  &&&&&&&$$  &$&&&&&&$& &$$&&&&&&  $$&&&&&&& &$&&  &&$& &&$&&&&&&$& 
 &$$$$$$$$$$$$$XXX$   &$&&   &&$&&&$$$$$$&&  &&$$$$$$&&  &&$$$$$$& &&$$$$$$& &$&&    &$& &&$$$$$$$& 
         &$XXXXXXX$                                                                                 
           &$$$$$$&                                                                                 
                                                                                                                                                                                                                     
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
        self.busy = True
        self.thread = threading.Thread(target=self.spinner_task)
        self.thread.start()

    def stop(self):
        self.busy = False
        if self.thread:
            self.thread.join()
        if self.spinner_visible:
            sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')
            sys.stdout.flush()

    def spinner_task(self):
        while self.busy:
            char = next(self.spinner)
            self.spinner_visible = True
            sys.stdout.write(f'\r{Colors.YELLOW}{self.message} {char}{Colors.RESET}')
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
            print(f"{Colors.GREEN}✔ Virtual environment created successfully.{Colors.RESET}")
        except Exception as e:
            spinner.stop()
            print(f"{Colors.RED}✘ Error: Could not create virtual environment: {e}{Colors.RESET}")
            sys.exit(1)
    else:
        print(f"{Colors.GREEN}✔ Virtual environment already exists.{Colors.RESET}")

def install_dependencies():
    """Installs dependencies from requirements.txt, showing a spinner."""
    python_executable = get_venv_python()
    if not python_executable.exists():
        print(f"{Colors.RED}✘ Error: Python executable not found in venv at {python_executable}{Colors.RESET}")
        sys.exit(1)

    spinner = Spinner("Installing/updating dependencies...")
    spinner.start()
    try:
        subprocess.check_call(
            [str(python_executable), "-m", "pip", "install", "--upgrade", "pip"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        subprocess.check_call(
            [str(python_executable), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        spinner.stop()
        print(f"{Colors.GREEN}✔ Dependencies are up to date.{Colors.RESET}")
    except subprocess.CalledProcessError:
        spinner.stop()
        print(f"{Colors.RED}✘ Error: Failed to install dependencies.{Colors.RESET}")
        print("Please check your internet connection and the requirements.txt file.")
        sys.exit(1)
    except FileNotFoundError:
        spinner.stop()
        print(f"{Colors.RED}✘ Error: Could not find '{REQUIREMENTS_FILE}'.{Colors.RESET}")
        sys.exit(1)

def launch_application():
    """Launches the main Tkinter application."""
    python_executable = get_venv_python()
    print(f"\n{Colors.CYAN}🚀 Launching application: {MAIN_APP_SCRIPT}{Colors.RESET}")
    try:
        subprocess.call([str(python_executable), str(MAIN_APP_SCRIPT)])
    except Exception as e:
        print(f"{Colors.RED}✘ Error: Failed to launch the application: {e}{Colors.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Animate the logo for a "flashier" startup
    for line in KYO_LOGO.splitlines():
        print(f"{Colors.RED}{line}{Colors.RESET}")
        time.sleep(0.03)
        
    print(f"{Colors.BLUE}--- First AI Utility Launcher ---{Colors.RESET}")
    
    create_virtual_environment()
    install_dependencies()
    launch_application()
    
    print(f"\n{Colors.YELLOW}Application has closed. Exiting launcher.{Colors.RESET}")
    if sys.platform == "win32":
        input("Press Enter to exit...")