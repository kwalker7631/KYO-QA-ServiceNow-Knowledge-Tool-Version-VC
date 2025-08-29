# main_app.py
# Author: Kenneth Walker
# Date: 2025-08-18
# Version: VA-2.6 (Robust Review Process)

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import re
from pathlib import Path
import os
import subprocess
import sys
import threading
import queue
import time
import importlib.util
import json
from datetime import datetime

import logging
from util import excel_safe, ui_helpers

# --- Core Application Modules ---
import data_harvester
import ocr_utils
import excel_processor

#==============================================================================
# GLOBAL CONFIGURATION
#==============================================================================
PDF_TEXT_OUTPUT_DIR = Path.cwd() / "PDF_TEXT_OUTPUT"
CUSTOM_PATTERNS_FILE = Path.cwd() / "custom_patterns.py"
IGNORED_PATTERNS_FILE = Path.cwd() / "ignored_patterns.py"
OUTPUT_DIR = Path.cwd() / "OUTPUT"
CONFIG_FILE = Path.cwd() / "app_config.json"

# Default config - will be overwritten by config file if it exists
DEFAULT_CONFIG = {
    "default_excel_path": "",
    "last_pdf_folder": "",
    "window_geometry": "1200x800",
    "show_tooltips": True,
    "auto_open_report": True,
    "theme": "light"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("error.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

#==============================================================================
# HELPER FUNCTIONS
#==============================================================================

def load_config():
    """Load application configuration"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except:
            pass
    return DEFAULT_CONFIG

def save_config(config):
    """Save application configuration"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except:
        pass

def create_tooltip(widget, text):
    """Create a tooltip for a widget"""
    tooltip = None
    def on_enter(event):
        nonlocal tooltip
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{event.x_root+15}+{event.y_root+10}")
        label = tk.Label(tooltip, text=text, background="#ffffe0", 
                        relief="solid", borderwidth=1, font=("Segoe UI", 9))
        label.pack(ipadx=1)
    
    def on_leave(event):
        nonlocal tooltip
        if tooltip:
            tooltip.destroy()
            tooltip = None
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


#==============================================================================
# PATTERN MANAGER DIALOGS & WINDOWS
#==============================================================================

class PatternEditDialog(tk.Toplevel):
    """Dialog for adding/editing patterns with user-friendly interface"""
    def __init__(self, parent, pattern_data=None):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Edit Pattern" if pattern_data else "Add New Pattern")
        self.geometry("600x350")
        self.configure(bg="#F0F2F5")
        self.pattern_data = pattern_data or {}
        self.result = None
        
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(1, weight=1)
        
        instructions = ttk.LabelFrame(main_frame, text=" Quick Guide ", padding=10)
        instructions.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,15))
        guide_text = "• Target Field: Choose what type of data this pattern will find\n• Regex Pattern: Enter the search pattern\n• Test your pattern before saving"
        ttk.Label(instructions, text=guide_text, font=("Segoe UI", 9), foreground="#555").pack(anchor="w")
        
        ttk.Label(main_frame, text="Target Field:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.target_field_var = tk.StringVar(value=self.pattern_data.get("field", "Model"))
        target_field_options = ["Model", "QA Number", "Author", "Topic"]
        field_combo = ttk.Combobox(main_frame, textvariable=self.target_field_var, values=target_field_options, state="readonly", width=25)
        field_combo.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        ttk.Label(main_frame, text="Regex Pattern:", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=5)
        pattern_frame = ttk.Frame(main_frame)
        pattern_frame.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        pattern_frame.columnconfigure(0, weight=1)
        self.pattern_entry_var = tk.StringVar(value=self.pattern_data.get("pattern", ""))
        self.pattern_entry = ttk.Entry(pattern_frame, textvariable=self.pattern_entry_var, font=("Consolas", 11))
        self.pattern_entry.grid(row=0, column=0, sticky="ew")
        
        self.test_label = ttk.Label(main_frame, text="", foreground="green")
        self.test_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, sticky="e", pady=(15,0))
        ttk.Button(button_frame, text="Save", command=self.on_save, style="Red.TButton").pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left")
    
    def on_save(self):
        pattern = self.pattern_entry_var.get().strip()
        if not pattern:
            messagebox.showwarning("Input Error", "Pattern cannot be empty.", parent=self)
            return
        
        try:
            re.compile(pattern)
        except re.error as e:
            messagebox.showerror("Invalid Pattern", f"The pattern is not valid:\n{str(e)}", parent=self)
            return
        
        self.result = {"field": self.target_field_var.get(), "pattern": pattern, "type": "Custom"}
        self.destroy()

class PatternManagerWindow(tk.Toplevel):
    """Enhanced Pattern Manager with better UX for engineers"""
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Pattern Manager - Define What to Extract")
        self.geometry("900x650")
        self.minsize(700, 500)
        
        self.all_patterns = self._load_patterns()
        self._setup_styles()
        self._create_widgets()
        self.populate_tree()
    
    def _setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.colors = {"BRAND_RED": "#DA291C", "BACKGROUND": "#F0F2F5", "FRAME_BG": "#FFFFFF", "ACCENT_BLUE": "#0078D4", "SUCCESS": "#107C10", "WARNING": "#FFA500", "INFO_BG": "#E3F2FD"}
        self.configure(bg=self.colors["BACKGROUND"])
    
    def _create_widgets(self):
        header_frame = ttk.Frame(self, padding=15)
        header_frame.pack(fill="x")
        ttk.Label(header_frame, text="Pattern Manager", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(header_frame, text="Define patterns to extract model numbers, QA codes, and other data from PDFs", font=("Segoe UI", 10), foreground="#666").pack(anchor="w", pady=(5,0))
        
        main_frame = ttk.Frame(self, padding=(15,0,15,15))
        main_frame.pack(expand=True, fill="both")
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        tree_frame = ttk.LabelFrame(main_frame, text=" Active Patterns ", padding=10)
        tree_frame.grid(row=0, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        
        tree_container = ttk.Frame(tree_frame)
        tree_container.grid(row=0, column=0, sticky="nsew")
        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)
        
        self.tree = ttk.Treeview(tree_container, columns=('Pattern', 'Type', 'Status'), show='tree headings', height=15)
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        self.tree.heading('#0', text='Target Field'); self.tree.heading('Pattern', text='Pattern (Regex)'); self.tree.heading('Type', text='Type'); self.tree.heading('Status', text='Status')
        self.tree.column('#0', width=150); self.tree.column('Pattern', width=400); self.tree.column('Type', width=100, anchor="center"); self.tree.column('Status', width=100, anchor="center")
        
        self.tree.tag_configure('category', font=('Segoe UI', 10, 'bold'), background='#E8E8E8'); self.tree.tag_configure('builtin', foreground='#666'); self.tree.tag_configure('custom', foreground=self.colors["ACCENT_BLUE"]); self.tree.tag_configure('error', foreground='red')
        
        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        button_frame = ttk.Frame(tree_frame)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(10,0))
        ttk.Button(button_frame, text="➕ Add Pattern", command=self.add_pattern).pack(side="left", padx=5)
        ttk.Button(button_frame, text="✏️ Edit Selected", command=self.edit_pattern).pack(side="left", padx=5)
        ttk.Button(button_frame, text="🗑️ Remove Selected", command=self.remove_pattern).pack(side="left", padx=5)
        
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=2, column=0, sticky="e", pady=(10,0))
        ttk.Button(action_frame, text="Save All Changes", style="Red.TButton", command=self.on_save_and_close).pack(side="right", padx=5)
        ttk.Button(action_frame, text="Cancel", command=self.destroy).pack(side="right")
    
    def _load_patterns(self):
        all_patterns = []
        built_in_patterns = data_harvester.get_all_patterns(load_custom=False)
        for field, pattern_list in built_in_patterns.items():
            for pattern in pattern_list:
                all_patterns.append({"field": field.replace("_", " ").capitalize(), "pattern": pattern, "type": "Built-in"})
        
        if CUSTOM_PATTERNS_FILE.exists():
            try:
                spec = importlib.util.spec_from_file_location("custom_patterns", CUSTOM_PATTERNS_FILE)
                custom_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(custom_module)
                field_map = {"MODEL_PATTERNS": "Model", "QA_NUMBER_PATTERNS": "Qa number"}
                for list_name, field_name in field_map.items():
                    custom_list = getattr(custom_module, list_name, [])
                    for pattern in custom_list:
                        if not any(p['pattern'] == pattern and p['type'] == 'Built-in' for p in all_patterns):
                            all_patterns.append({"field": field_name, "pattern": pattern, "type": "Custom"})
            except Exception as e:
                print(f"Error loading custom patterns: {e}")
        return all_patterns
    
    def populate_tree(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        categories = {}
        self.all_patterns.sort(key=lambda p: (p['field'], p['type'], p['pattern']))
        for i, p in enumerate(self.all_patterns):
            field = p["field"]
            if field not in categories:
                categories[field] = self.tree.insert("", "end", text=f"📁 {field}", open=True, tags=('category',))
            try:
                re.compile(p["pattern"]); status = "✓ Valid"; tag = 'custom' if p["type"] == "Custom" else 'builtin'
            except:
                status = "✗ Invalid"; tag = 'error'
            self.tree.insert(categories[field], "end", iid=f"pattern_{i}", text="", values=(p["pattern"], p["type"], status), tags=(tag,))

    def add_pattern(self):
        dialog = PatternEditDialog(self); self.wait_window(dialog)
        if dialog.result: self.all_patterns.append(dialog.result); self.populate_tree()
    
    def edit_pattern(self):
        selection = self.tree.selection()
        if not selection: messagebox.showinfo("No Selection", "Please select a pattern to edit.", parent=self); return
        item_id = selection[0]
        if not item_id.startswith("pattern_"): return
        pattern_index = int(item_id.split('_')[1]); original_data = self.all_patterns[pattern_index]
        if original_data["type"] == "Built-in": messagebox.showinfo("Cannot Edit", "Built-in patterns cannot be edited.", parent=self); return
        dialog = PatternEditDialog(self, original_data); self.wait_window(dialog)
        if dialog.result: self.all_patterns[pattern_index] = dialog.result; self.populate_tree()

    def remove_pattern(self):
        selection = self.tree.selection()
        if not selection: messagebox.showinfo("No Selection", "Please select a pattern to remove.", parent=self); return
        item_id = selection[0]
        if not item_id.startswith("pattern_"): return
        pattern_index = int(item_id.split('_')[1]); pattern_data = self.all_patterns[pattern_index]
        if pattern_data["type"] == "Built-in": messagebox.showerror("Cannot Remove", "Built-in patterns cannot be removed.", parent=self); return
        if messagebox.askyesno("Confirm Remove", f"Remove this pattern?\n\n{pattern_data['pattern']}", parent=self):
            del self.all_patterns[pattern_index]; self.populate_tree()
            
    def on_save_and_close(self):
        custom_patterns = {"MODEL_PATTERNS": [], "QA_NUMBER_PATTERNS": []}
        field_map = {"Model": "MODEL_PATTERNS", "Qa number": "QA_NUMBER_PATTERNS"}
        for p in self.all_patterns:
            if p["type"] == "Custom":
                list_name = field_map.get(p["field"])
                if list_name: custom_patterns[list_name].append(p["pattern"])
        try:
            with open(CUSTOM_PATTERNS_FILE, "w", encoding="utf-8") as f:
                f.write(f"# custom_patterns.py\n# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for list_name, patterns in custom_patterns.items():
                    f.write(f"{list_name} = [\n")
                    for pattern in sorted(set(patterns)):
                        safe_pattern = pattern.replace("'", "\\'")
                        f.write(f"    r'{safe_pattern}',\n")
                    f.write("]\n\n")
            messagebox.showinfo("Success", "Patterns saved successfully!", parent=self); self.destroy()
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save patterns:\n{str(e)}", parent=self)

#==============================================================================
# MAIN APPLICATION CLASS
#==============================================================================

class KyoQAToolApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.app_config = load_config()
        self.title("First AI Utility - Kyocera QA Tool v2.6 (Stable)")
        self.geometry(self.app_config.get("window_geometry", "1200x800"))
        self.state('zoomed') if sys.platform == 'win32' else self.attributes('-zoomed', True)
        
        # Initialize variables
        self.review_filter_var = tk.StringVar(value="All")
        self.pattern_target_field = tk.StringVar(value="Model")
        self.processed_files = []
        self.status_current_file = tk.StringVar(value="Ready. Select PDFs to begin.")
        self.progress_value = tk.DoubleVar(value=0)
        self.time_remaining_var = tk.StringVar(value="--:--")
        self.progress_text_var = tk.StringVar(value="0%")
        
        # Counters
        self.count_pass = tk.IntVar(value=0); self.count_fail = tk.IntVar(value=0); self.count_review = tk.IntVar(value=0)
        self.count_total = tk.IntVar(value=0); self.count_done = tk.IntVar(value=0)
        self.count_ocr = tk.IntVar(value=0); self.count_digital = tk.IntVar(value=0)
        
        self.is_processing = False
        self.ui_queue = queue.Queue()
        self.start_time = None
        self.cancel_event = threading.Event()
        
        self._setup_styles()
        self._create_menu()
        self._create_widgets()
        
        self.review_tree.bind("<<TreeviewSelect>>", self.on_file_select)
        self.protocol("WM_DELETE_WINDOW", self.on_exit)
        
        PDF_TEXT_OUTPUT_DIR.mkdir(exist_ok=True); OUTPUT_DIR.mkdir(exist_ok=True)
        
        if self.app_config.get("default_excel_path"):
            self.excel_path_var.set(self.app_config["default_excel_path"])
        
        self.after(100, self.process_ui_queue)
        self.log_message("Welcome to First AI Utility!", "info")
        self.log_message("Optimized for large jobs. Ready to process.", "info")
    
    def _setup_styles(self):
        self.style = ttk.Style(self); self.style.theme_use("clam")
        self.colors = {"BRAND_RED": "#DA291C", "BACKGROUND": "#F0F2F5", "FRAME_BG": "#FFFFFF", "ACCENT_BLUE": "#0078D4", "PASTEL_GREEN": "#C8E6C9", "PASTEL_YELLOW": "#FFF9C4", "PASTEL_RED": "#FFCDD2", "SUCCESS_GREEN": "#107C10", "WARN_ORANGE": "#FFA500", "INFO_BG": "#E3F2FD"}
        self.configure(bg=self.colors["BACKGROUND"])
        self.style.configure("TFrame", background=self.colors["BACKGROUND"]); self.style.configure("TLabel", background=self.colors["FRAME_BG"], font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=8); self.style.configure("Red.TButton", font=("Segoe UI", 12, "bold"), background=self.colors["BRAND_RED"], foreground="white")
        self.style.map("Red.TButton", background=[('active', '#B01F14')])
        self.style.configure('Red.Horizontal.TProgressbar', background=self.colors["BRAND_RED"]); self.style.configure('Green.Horizontal.TProgressbar', background=self.colors["SUCCESS_GREEN"])
        self.style.configure("TNotebook", background=self.colors["BACKGROUND"]); self.style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[20, 8])
        self.style.configure("Treeview", rowheight=28, font=("Segoe UI", 10), fieldbackground=self.colors["FRAME_BG"]); self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
    
    def _create_menu(self):
        self.menu_bar = tk.Menu(self); self.config(menu=self.menu_bar)
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Select Excel Template...", command=self.browse_excel)
        file_menu.add_command(label="Select PDF Folder...", command=self.browse_folder)
        file_menu.add_separator(); file_menu.add_command(label="Open Output Folder", command=self.open_output_folder)
        file_menu.add_separator(); file_menu.add_command(label="Exit", command=self.on_exit)
        tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Pattern Manager...", command=self.open_pattern_manager)
        tools_menu.add_command(label="Clear Ignored List", command=self.clear_ignored_list)
    
    def _create_widgets(self):
        main_container = ttk.Frame(self, style="TFrame"); main_container.pack(expand=True, fill="both", padx=10, pady=5)
        header_frame = ttk.Frame(main_container, style="TFrame"); header_frame.pack(side="top", fill="x", pady=(0,10))
        title_frame = ttk.Frame(header_frame); title_frame.pack(side="left")
        ttk.Label(title_frame, text="KYOCERA", foreground=self.colors["BRAND_RED"], background=self.colors["BACKGROUND"], font=("Arial Black", 24)).pack(side="left")
        ttk.Label(title_frame, text="First AI Utility", background=self.colors["BACKGROUND"], font=("Segoe UI", 16)).pack(side="left", padx=20)
        self.status_indicator = ttk.Label(header_frame, text="● Ready", foreground=self.colors["SUCCESS_GREEN"], background=self.colors["BACKGROUND"], font=("Segoe UI", 12))
        self.status_indicator.pack(side="right", padx=20)
        
        notebook = ttk.Notebook(main_container); notebook.pack(expand=True, fill="both")
        processing_tab = ttk.Frame(notebook, padding=15)
        review_tab = ttk.Frame(notebook, padding=15)
        notebook.add(processing_tab, text=" 📋 Processing "); notebook.add(review_tab, text=" 🔍 Document Review ")
        self._create_processing_tab(processing_tab)
        self._create_review_tab(review_tab)
    
    def _create_processing_tab(self, parent):
        parent.columnconfigure(0, weight=1); parent.rowconfigure(2, weight=1)
        
        input_frame = ttk.LabelFrame(parent, text=" Step 1: Select Inputs ", padding=15); input_frame.grid(row=0, column=0, sticky="ew", pady=(0,10)); input_frame.columnconfigure(1, weight=1)
        ttk.Label(input_frame, text="Excel Template:").grid(row=0, column=0, sticky="w", pady=5)
        self.excel_path_var = tk.StringVar(); excel_entry = ttk.Entry(input_frame, textvariable=self.excel_path_var, state="readonly"); excel_entry.grid(row=0, column=1, sticky="ew", padx=10)
        ttk.Button(input_frame, text="Browse...", command=self.browse_excel).grid(row=0, column=2)
        
        ttk.Label(input_frame, text="PDF Source:").grid(row=1, column=0, sticky="w", pady=5)
        self.pdf_source_var = tk.StringVar(); pdf_entry = ttk.Entry(input_frame, textvariable=self.pdf_source_var, state="readonly"); pdf_entry.grid(row=1, column=1, sticky="ew", padx=10)
        pdf_buttons = ttk.Frame(input_frame); pdf_buttons.grid(row=1, column=2)
        ttk.Button(pdf_buttons, text="📁 Folder", command=self.browse_folder).pack(side="left")
        ttk.Button(pdf_buttons, text="📄 Files", command=self.browse_files).pack(side="left", padx=5)
        
        control_frame = ttk.LabelFrame(parent, text=" Step 2: Process ", padding=15); control_frame.grid(row=1, column=0, sticky="ew", pady=10)
        control_frame.columnconfigure(0, weight=1)
        
        self.start_button = ttk.Button(control_frame, text="▶ START PROCESSING", style="Red.TButton", command=self.start_processing)
        self.start_button.grid(row=0, column=0, sticky="ew")
        
        self.cancel_button = ttk.Button(control_frame, text="⏹️ CANCEL PROCESSING", command=self.cancel_processing)
        self.cancel_button.grid(row=0, column=1, sticky="e", padx=(10,0))
        self.cancel_button.grid_remove()
        self.reveal_button = ttk.Button(control_frame, text="📂 Reveal in Folder", command=self.reveal_output)
        self.reveal_button.grid(row=0, column=2, sticky="e", padx=(10,0))
        self.reveal_button.grid_remove()
        create_tooltip(self.reveal_button, "Open the folder containing the generated Excel report")

        status_frame = ttk.LabelFrame(parent, text=" Step 3: Monitor Progress ", padding=15); status_frame.grid(row=2, column=0, sticky="nsew"); status_frame.columnconfigure(0, weight=1); status_frame.rowconfigure(4, weight=1)
        progress_container = ttk.Frame(status_frame); progress_container.grid(row=0, column=0, sticky="ew", pady=(0,10)); progress_container.columnconfigure(0, weight=1)
        self.pbar = ttk.Progressbar(progress_container, variable=self.progress_value, style='Red.Horizontal.TProgressbar'); self.pbar.grid(row=0, column=0, sticky="ew")
        self.progress_label = ttk.Label(progress_container, textvariable=self.progress_text_var, background=self.colors["BACKGROUND"]); self.progress_label.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(progress_container, textvariable=self.time_remaining_var, font=("Segoe UI", 9)).grid(row=0, column=1, padx=(10,0))
        self.status_text = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.status_text, font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.status_current_file, font=("Segoe UI", 10, "italic"), foreground="#666").grid(row=2, column=0, sticky="w", pady=5)
        
        stats_frame = ttk.LabelFrame(status_frame, text=" Statistics ", padding=10); stats_frame.grid(row=3, column=0, sticky="ew", pady=(10,0))
        stat_cards = [("Total", self.count_total, "#0078D4"), ("Done", self.count_done, "#0078D4"), ("✓ Pass", self.count_pass, "#107C10"), ("✗ Fail", self.count_fail, "#DA291C"), ("⚠ Review", self.count_review, "#FFA500"), ("📷 OCR", self.count_ocr, "#9C27B0"), ("📄 Digital", self.count_digital, "#00BCD4")]
        for i, (label, var, color) in enumerate(stat_cards):
            card = ttk.Frame(stats_frame); card.grid(row=0, column=i, padx=5, sticky="ew"); stats_frame.columnconfigure(i, weight=1)
            ttk.Label(card, text=label, font=("Segoe UI", 9), foreground="#666").pack()
            ttk.Label(card, textvariable=var, font=("Segoe UI", 14, "bold"), foreground=color).pack()

        log_frame = ttk.LabelFrame(status_frame, text=" Live Processing Log ", padding=10)
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(10,0))
        log_frame.rowconfigure(0, weight=1); log_frame.columnconfigure(0, weight=1)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap="word", font=("Consolas", 9), state="disabled", relief="flat", bg=self.colors["FRAME_BG"])
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.tag_configure("info", foreground="#00529B"); self.log_text.tag_configure("success", foreground="#107C10"); self.log_text.tag_configure("warning", foreground="#FFA500"); self.log_text.tag_configure("error", foreground="#DA291C")

    def _create_review_tab(self, parent):
        parent.columnconfigure(0, weight=1, minsize=350); parent.columnconfigure(1, weight=2); parent.rowconfigure(0, weight=1)
        
        left_panel = ttk.Frame(parent); left_panel.grid(row=0, column=0, sticky="nsew", padx=(0,10)); left_panel.rowconfigure(1, weight=1)
        filter_frame = ttk.LabelFrame(left_panel, text=" Filter ", padding=10); filter_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        filters = ["All", "Pass", "Needs Review", "Fail"]
        for i, status in enumerate(filters):
            ttk.Radiobutton(filter_frame, text=status, value=status, variable=self.review_filter_var, command=self._populate_review_tree).grid(row=0, column=i, padx=5)
        
        tree_frame = ttk.LabelFrame(left_panel, text=" Processed Files ", padding=5); tree_frame.grid(row=1, column=0, sticky="nsew"); tree_frame.rowconfigure(0, weight=1); tree_frame.columnconfigure(0, weight=1)
        self.review_tree = ttk.Treeview(tree_frame, columns=('Status',), show='tree headings', height=20); self.review_tree.grid(row=0, column=0, sticky="nsew")
        self.review_tree.heading('#0', text='File Name'); self.review_tree.heading('Status', text='Status'); self.review_tree.column('#0', width=250); self.review_tree.column('Status', width=100, anchor="center")
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.review_tree.yview); tree_scroll.grid(row=0, column=1, sticky="ns"); self.review_tree.configure(yscrollcommand=tree_scroll.set)
        
        right_panel = ttk.Frame(parent); right_panel.grid(row=0, column=1, sticky="nsew"); right_panel.rowconfigure(2, weight=1); right_panel.columnconfigure(0, weight=1)
        
        nav_frame = ttk.Frame(right_panel)
        nav_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(nav_frame, text="🔄 Re-scan", command=self.on_rescan).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="🚫 Flag Selection", command=self.on_flag_selection).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="📄 Open PDF", command=self.open_original_pdf).pack(side="right", padx=2)
        
        self.reason_label = ttk.Label(right_panel, text="", font=("Segoe UI", 10), background=self.colors["INFO_BG"], padding=8); self.reason_label.grid(row=1, column=0, sticky="ew", pady=(0,10))
        
        text_frame = ttk.LabelFrame(right_panel, text=" Extracted Text ", padding=5); text_frame.grid(row=2, column=0, sticky="nsew"); text_frame.rowconfigure(0, weight=1); text_frame.columnconfigure(0, weight=1)
        text_container = ttk.Frame(text_frame); text_container.grid(row=0, column=0, sticky="nsew"); text_container.rowconfigure(0, weight=1); text_container.columnconfigure(0, weight=1)
        self.doc_text = tk.Text(text_container, wrap="word", font=("Consolas", 10), relief="flat"); self.doc_text.grid(row=0, column=0, sticky="nsew")
        text_scroll = ttk.Scrollbar(text_container, orient="vertical", command=self.doc_text.yview); text_scroll.grid(row=0, column=1, sticky="ns"); self.doc_text.configure(yscrollcommand=text_scroll.set)
        
        self.doc_text.tag_configure("model_found", background=self.colors["PASTEL_GREEN"]); self.doc_text.tag_configure("qa_number_found", background=self.colors["PASTEL_YELLOW"]); self.doc_text.tag_configure("flagged_found", background=self.colors["PASTEL_RED"])
        self.doc_text.insert("1.0", "Select a file from the list to view its content."); self.doc_text.config(state=tk.DISABLED)

        pattern_frame = ttk.LabelFrame(right_panel, text=" Pattern Testing ", padding=10)
        pattern_frame.grid(row=3, column=0, sticky="ew", pady=(10,0))
        pattern_frame.columnconfigure(1, weight=1)
        
        ttk.Label(pattern_frame, text="Target:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(pattern_frame, textvariable=self.pattern_target_field, values=["Model", "QA Number", "Author", "Topic"], state="readonly", width=15).grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(pattern_frame, text="Pattern:").grid(row=1, column=0, sticky="w", pady=(5,0))
        self.pattern_entry = ttk.Entry(pattern_frame, font=("Consolas", 10))
        self.pattern_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=(5,0))
        
        button_frame = ttk.Frame(pattern_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10,0))
        
        ttk.Button(button_frame, text="💡 Suggest from Selection", command=self.on_suggest_pattern).pack(side="left", padx=2)
        ttk.Button(button_frame, text="🧪 Test Pattern", command=self.on_test_pattern).pack(side="left", padx=2)
        ttk.Button(button_frame, text="💾 Save Pattern", command=self.on_save_custom_pattern, style="Red.TButton").pack(side="left", padx=2)

    def log_message(self, message, level):
        logging_map = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "success": logging.INFO,
        }
        logging.log(logging_map.get(level, logging.INFO), message)
        self.log_text.config(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", (level,))
        self.log_text.config(state="disabled")
        self.log_text.see(tk.END)

    def browse_excel(self):
        path = filedialog.askopenfilename(title="Select Excel Template", filetypes=[("Excel Files", "*.xlsx")])
        if path: self.excel_path_var.set(path); self.app_config["default_excel_path"] = path; save_config(self.app_config)
    
    def browse_folder(self):
        path = filedialog.askdirectory(title="Select Folder Containing PDFs")
        if path:
            self.pdf_source_var.set(path); self.selected_pdf_paths = sorted(list(Path(path).glob("*.pdf"))); count = len(self.selected_pdf_paths)
            self.count_total.set(count); self.status_current_file.set(f"Found {count} PDF files"); self.app_config["last_pdf_folder"] = path; save_config(self.app_config)
            self.log_message(f"Selected folder: {path} ({count} PDFs found)", "info")
    
    def browse_files(self):
        paths = filedialog.askopenfilenames(title="Select PDF Files", filetypes=[("PDF Files", "*.pdf")])
        if paths:
            self.selected_pdf_paths = sorted([Path(p) for p in paths]); count = len(self.selected_pdf_paths)
            self.pdf_source_var.set(f"{count} files selected"); self.count_total.set(count); self.status_current_file.set(f"Selected {count} PDF files")
            self.log_message(f"Selected {count} individual PDF files.", "info")

    def start_processing(self):
        if self.is_processing: messagebox.showinfo("Processing", "Already processing..."); return
        if not hasattr(self, 'selected_pdf_paths') or not self.selected_pdf_paths: messagebox.showwarning("No Files", "Please select PDFs."); return
        if not self.excel_path_var.get(): messagebox.showwarning("No Template", "Please select an Excel template."); return
        
        self.is_processing = True; self.processed_files.clear(); self.start_time = time.time(); self.cancel_event.clear()
        self.count_pass.set(0); self.count_fail.set(0); self.count_review.set(0); self.count_done.set(0); self.count_ocr.set(0); self.count_digital.set(0)

        self.start_button.grid_remove(); self.cancel_button.grid(); self.reveal_button.grid_remove()
        self.status_indicator.config(text="● Processing", foreground="#FFA500")
        self.pbar.config(style='Red.Horizontal.TProgressbar')
        for item in self.review_tree.get_children(): self.review_tree.delete(item)
        self.log_text.config(state="normal"); self.log_text.delete("1.0", tk.END); self.log_text.config(state="disabled")
        self.status_text.set("Processing PDFs...")
        
        thread = threading.Thread(target=self.processing_thread, args=(self.selected_pdf_paths,), daemon=True)
        thread.start()

    def cancel_processing(self):
        if self.is_processing:
            self.cancel_event.set()
            self.cancel_button.config(state=tk.DISABLED, text="Cancelling...")
            self.log_message("Cancel request received. Finishing current file...", "warning")

    def reveal_output(self):
        if getattr(self, "last_output_file", None):
            ui_helpers.reveal_in_explorer(self.last_output_file)

    def processing_thread(self, pdf_paths):
        total_files = len(pdf_paths)
        self.ui_queue.put({"type": "log", "msg": f"Starting process for {total_files} files...", "level": "info"})

        for i, pdf_path in enumerate(pdf_paths):
            if self.cancel_event.is_set():
                self.ui_queue.put({"type": "log", "msg": "Processing cancelled by user.", "level": "warning"}); break

            try:
                progress = ((i + 1) / total_files) * 100
                elapsed = time.time() - self.start_time
                time_str = f"{int((elapsed / (i+1)) * (total_files - (i+1)) // 60)}:{int(((elapsed / (i+1)) * (total_files - (i+1))) % 60):02d}" if i > 0 else "Calculating..."
                self.ui_queue.put({"type": "progress", "value": progress, "text": f"{int(progress)}%", "time": time_str})
                self.ui_queue.put({"type": "status", "msg": f"[{i+1}/{total_files}] Processing: {pdf_path.name}"})
                self.ui_queue.put({"type": "log", "msg": f"[{i+1}/{total_files}] Analyzing '{pdf_path.name}'...", "level": "info"})
                
                extraction_result = ocr_utils.extract_text_from_pdf(pdf_path)
                full_text = extraction_result.get("text", "")
                
                text_file = PDF_TEXT_OUTPUT_DIR / f"{pdf_path.stem}.txt"
                text_file.write_text(full_text, encoding='utf-8', errors='replace')

                path_type = "OCR" if extraction_result.get("ocr_used") else "Digital"
                if extraction_result.get("ocr_used"): self.ui_queue.put({"type": "log", "msg": f"  - Scanned document detected. Running OCR.", "level": "warning"})
                else: self.ui_queue.put({"type": "log", "msg": f"  - Digital text found. Extracting directly.", "level": "info"})
                
                harvest_results = data_harvester.harvest_all_data(full_text)
                valid_items_found = any(not item.get('flagged', False) for item in harvest_results.get("found_items", []))
                status = "Pass" if valid_items_found else "Needs Review"
                
                num_models = len([item for item in harvest_results.get("found_items", []) if item['type'] == 'Model' and not item['flagged']])
                self.ui_queue.put({"type": "log", "msg": f"  - Status: {status}. Found {num_models} valid models.", "level": "success" if status == "Pass" else "warning"})
                
                file_data = {"id": str(pdf_path), "filename": pdf_path.name, "text_file_path": str(text_file), "found_items": harvest_results.get("found_items", []), "status": status, "reason": harvest_results.get("status_reason", ""), "original_path": pdf_path, "path_type": path_type}
                self.ui_queue.put({"type": "add_file", "data": file_data})

            except Exception as e:
                error_msg = f"Failed to process {pdf_path.name}: {e}"
                self.ui_queue.put({"type": "log", "msg": error_msg, "level": "error"})
                file_data = {"id": str(pdf_path), "filename": pdf_path.name, "status": "Fail", "reason": str(e)}
                self.ui_queue.put({"type": "add_file", "data": file_data})
        
        self.ui_queue.put({"type": "finish"})
    
    def process_ui_queue(self):
        try:
            while not self.ui_queue.empty():
                msg = self.ui_queue.get_nowait()
                msg_type = msg.get("type")
                
                if msg_type == "status": self.status_current_file.set(msg.get("msg"))
                elif msg_type == "progress": self.progress_value.set(msg.get("value", 0)); self.progress_text_var.set(msg.get("text", "")); self.time_remaining_var.set(msg.get("time", ""))
                elif msg_type == "log": self.log_message(msg.get("msg"), msg.get("level"))
                elif msg_type == "add_file":
                    file_data = msg.get("data", {}); self.processed_files.append(file_data); self._add_file_to_review_tree(file_data)
                    status = file_data.get("status", "")
                    if "Pass" in status: self.count_pass.set(self.count_pass.get() + 1)
                    elif "Fail" in status: self.count_fail.set(self.count_fail.get() + 1)
                    elif "Review" in status: self.count_review.set(self.count_review.get() + 1)
                    self.count_done.set(self.count_done.get() + 1)
                    if file_data.get("path_type") == "OCR": self.count_ocr.set(self.count_ocr.get() + 1)
                    elif file_data.get("path_type") == "Digital": self.count_digital.set(self.count_digital.get() + 1)
                elif msg_type == "finish": self.finish_processing()
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_ui_queue)
    
    def finish_processing(self):
        self.log_message("Processing complete. Generating Excel report...", "info")
        try:
            if self.processed_files:
                self.status_text.set("Saving Excel report...")
                excel_safe.ensure_output_dir(OUTPUT_DIR)
                output_file = excel_processor.process_excel_file(Path(self.excel_path_var.get()), self.processed_files, OUTPUT_DIR)
                self.last_output_file = output_file
                self.status_text.set("Report ready.")
                self.status_current_file.set(f"Complete! Report saved to: {output_file.name}")
                self.reveal_button.grid()
                self.log_message(f"Successfully generated report: {output_file.name}", "success")
                if self.app_config.get("auto_open_report", True):
                    self.log_message("Auto-opening report...", "info")
                    if sys.platform == "win32": os.startfile(output_file)
                    else: subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", str(output_file)])
            else:
                self.status_current_file.set("No files were processed.")
                self.status_text.set("")
                self.reveal_button.grid_remove()
                self.log_message("No report generated.", "warning")
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate report:\n{str(e)}"); self.status_current_file.set("Error generating report")
            self.status_text.set("Save failed")
            self.reveal_button.grid_remove()
            self.log_message(f"Error generating report: {e}", "error")
            logger.exception("Error generating report")
        finally:
            self.is_processing = False
            self.cancel_button.grid_remove(); self.start_button.grid()
            self.cancel_button.config(state=tk.NORMAL, text="⏹️ CANCEL PROCESSING")
            self.progress_value.set(100); self.progress_text_var.set("100%"); self.pbar.config(style='Green.Horizontal.TProgressbar')
            self.status_indicator.config(text="● Complete", foreground=self.colors["SUCCESS_GREEN"])

    def _add_file_to_review_tree(self, file_data):
        filter_status = self.review_filter_var.get()
        if filter_status == "All" or filter_status in file_data["status"]:
            icon = "✓ " if "Pass" in file_data["status"] else "✗ " if "Fail" in file_data["status"] else "⚠ "
            self.review_tree.insert("", "end", iid=file_data["id"], text=icon + file_data["filename"], values=(file_data["status"],))

    def _populate_review_tree(self):
        for item in self.review_tree.get_children(): self.review_tree.delete(item)
        for file_data in self.processed_files: self._add_file_to_review_tree(file_data)
    
    def on_file_select(self, event=None):
        selection = self.review_tree.selection()
        if not selection: return
        file_data = next((f for f in self.processed_files if f["id"] == selection[0]), None)
        if file_data:
            self.reason_label.config(text=f"📋 Status: {file_data.get('reason', 'N/A')}")
            try:
                self.doc_text.config(state=tk.NORMAL)
                self.doc_text.delete("1.0", tk.END)

                # --- FIX: New logic to handle failed files gracefully ---
                if file_data.get("status") == "Fail":
                    full_text = f"Processing failed for this file.\n\nReason: {file_data.get('reason', 'Unknown error')}"
                    self.doc_text.insert("1.0", full_text)
                else:
                    text_file_path = file_data.get("text_file_path")
                    if text_file_path and Path(text_file_path).exists():
                        full_text = Path(text_file_path).read_text(encoding='utf-8')
                        self.doc_text.insert("1.0", full_text)
                        for item in file_data.get("found_items", []):
                            tag = "flagged_found" if item.get('flagged') else 'model_found' if item['type'] == 'Model' else 'qa_number_found'
                            self._highlight_text(item["text"], tag)
                    else:
                        self.doc_text.insert("1.0", "Text file not found. It may have been moved or deleted.")
                
                self.doc_text.config(state=tk.DISABLED)
            except Exception as e:
                self.doc_text.config(state=tk.NORMAL)
                self.doc_text.delete("1.0", tk.END)
                self.doc_text.insert("1.0", f"Error loading text review:\n\n{e}")
                self.doc_text.config(state=tk.DISABLED)

    def _highlight_text(self, text_to_find, tag):
        start_pos = "1.0"
        while True:
            start_pos = self.doc_text.search(text_to_find, start_pos, stopindex=tk.END, nocase=True)
            if not start_pos: break
            end_pos = f"{start_pos}+{len(text_to_find)}c"; self.doc_text.tag_add(tag, start_pos, end_pos); start_pos = end_pos
    
    def on_exit(self):
        if self.is_processing and not messagebox.askyesno("Exit", "Processing is in progress. Are you sure you want to exit?"): return
        self.app_config["window_geometry"] = self.geometry(); save_config(self.app_config)
        self.destroy()

    def open_output_folder(self):
        try:
            if sys.platform == "win32": os.startfile(OUTPUT_DIR)
            else: subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", str(OUTPUT_DIR)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def open_pattern_manager(self):
        PatternManagerWindow(self)

    def clear_ignored_list(self):
        if messagebox.askyesno("Clear Ignored List", "This will remove all flagged patterns. Are you sure?"):
            try:
                with open(IGNORED_PATTERNS_FILE, "w", encoding="utf-8") as f:
                    f.write("# ignored_patterns.py\n\nIGNORED_MODEL_PATTERNS = []\nIGNORED_QA_NUMBER_PATTERNS = []\nIGNORED_AUTHOR_PATTERNS = []\nIGNORED_TOPIC_PATTERNS = []\n")
                messagebox.showinfo("Success", "Ignored patterns list has been cleared.")
            except Exception as e:
                messagebox.showerror("Error", f"Could not clear ignored list: {e}")

    def open_original_pdf(self):
        selection = self.review_tree.selection()
        if not selection: return
        file_data = next((f for f in self.processed_files if f["id"] == selection[0]), None)
        if file_data and "original_path" in file_data:
            try:
                os.startfile(Path(file_data["original_path"]))
            except Exception as e:
                messagebox.showerror("Error", f"Could not open PDF: {e}")

    def on_rescan(self):
        selection = self.review_tree.selection()
        if not selection: return
        
        item_id = selection[0]
        file_data = next((f for f in self.processed_files if f["id"] == item_id), None)
        if not file_data or "text_file_path" not in file_data:
            messagebox.showerror("Error", "Cannot re-scan a failed item without text.")
            return

        try:
            full_text = Path(file_data["text_file_path"]).read_text(encoding='utf-8')
            harvest_results = data_harvester.harvest_all_data(full_text)
            
            file_data.update({
                "found_items": harvest_results.get("found_items", []),
                "status": "Pass" if any(not i.get('flagged', False) for i in harvest_results.get("found_items", [])) else "Needs Review",
                "reason": harvest_results.get("status_reason", "")
            })
            
            self._populate_review_tree()
            self.review_tree.selection_set(item_id)
            self.on_file_select()
            messagebox.showinfo("Success", f"Re-scan complete for {file_data['filename']}.")

        except Exception as e:
            messagebox.showerror("Re-scan Failed", f"Could not re-scan file: {e}")

    def on_flag_selection(self):
        try:
            selected_text = self.doc_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if not selected_text: return
            
            pattern_to_ignore = f"^{re.escape(selected_text)}$"
            
            with open(IGNORED_PATTERNS_FILE, "a", encoding="utf-8") as f:
                f.write(f"\nIGNORED_MODEL_PATTERNS.append(r'{pattern_to_ignore}')\n")
            
            messagebox.showinfo("Text Flagged", f"'{selected_text}' was added to the ignored list. Please Re-scan to see changes.")
        except tk.TclError:
            messagebox.showwarning("No Selection", "Please select text in the document to flag.")

    def on_suggest_pattern(self):
        try:
            selected_text = self.doc_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if not selected_text: return
            
            pattern = self._generalize_sample_to_regex(selected_text)
            self.pattern_entry.delete(0, tk.END)
            self.pattern_entry.insert(0, pattern)
        except tk.TclError:
            messagebox.showwarning("No Selection", "Please select text to suggest a pattern from.")

    def _generalize_sample_to_regex(self, selection):
        cleaned_selection = re.sub(r'[/\\]', ',', selection)
        models = [m.strip() for m in cleaned_selection.split(',') if m.strip()]

        if not models: return ""

        if len(models) == 1:
            sample = models[0]
            pattern = re.sub(r'\d+', lambda m: f'\\d{{{len(m.group(0))}}}', re.escape(sample))
            return rf'\b{pattern}\b'

        prefix = os.path.commonprefix(models)
        reversed_models = [m[::-1] for m in models]
        reversed_suffix = os.path.commonprefix(reversed_models)
        suffix = reversed_suffix[::-1]

        min_len, max_len = float('inf'), 0
        all_digits = True
        for model in models:
            variable_part = model[len(prefix):len(model)-len(suffix)]
            if not variable_part: continue
            min_len = min(min_len, len(variable_part))
            max_len = max(max_len, len(variable_part))
            if not variable_part.isdigit():
                all_digits = False

        if min_len > max_len: middle = ""
        elif all_digits:
            middle = f'\\d{{{min_len},{max_len}}}' if min_len != max_len else f'\\d{{{min_len}}}'
        else:
            middle = f'\\w{{{min_len},{max_len}}}' if min_len != max_len else f'\\w{{{min_len}}}'
            
        final_pattern = re.escape(prefix) + middle + re.escape(suffix)
        return rf'\b{final_pattern}\b'

    def on_test_pattern(self):
        pattern_str = self.pattern_entry.get()
        if not pattern_str: return
        
        self.doc_text.config(state=tk.NORMAL)
        self.doc_text.tag_remove("test_highlight", "1.0", tk.END)
        self.doc_text.tag_configure("test_highlight", background="#FFD700")
        
        try:
            content = self.doc_text.get("1.0", tk.END)
            matches = list(re.finditer(pattern_str, content, re.IGNORECASE))
            if matches:
                for match in matches:
                    start_index = f"1.0+{match.start()}c"
                    end_index = f"1.0+{match.end()}c"
                    self.doc_text.tag_add("test_highlight", start_index, end_index)
                messagebox.showinfo("Test Results", f"Found {len(matches)} matches.")
            else:
                messagebox.showinfo("Test Results", "No matches found.")
        except re.error as e:
            messagebox.showerror("Invalid Pattern", f"Regex error: {e}")
        finally:
            self.doc_text.config(state=tk.DISABLED)

    def on_save_custom_pattern(self):
        pattern = self.pattern_entry.get().strip()
        if not pattern: return
        
        target_field = self.pattern_target_field.get()
        list_name_map = {"Model": "MODEL_PATTERNS", "QA Number": "QA_NUMBER_PATTERNS", "Author": "AUTHOR_PATTERNS", "Topic": "TOPIC_PATTERNS"}
        list_name = list_name_map.get(target_field)

        if not list_name: return

        try:
            with open(CUSTOM_PATTERNS_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n{list_name}.append(r'{pattern}')\n")
            messagebox.showinfo("Pattern Saved", f"Pattern added to {target_field}. Please Re-scan to apply.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save pattern: {e}")

#==============================================================================
# APPLICATION ENTRY POINT
#==============================================================================

if __name__ == "__main__":
    try:
        app = KyoQAToolApp()
        app.mainloop()
    except Exception as e:
        import traceback
        error_log = Path.cwd() / "error.log"
        with open(error_log, "a") as f:
            f.write(f"\n\n--- Application Error on {datetime.now()} ---\n")
            f.write(f"{str(e)}\n\n{traceback.format_exc()}")
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Application Error", f"An unrecoverable error occurred: {e}\nDetails have been saved to error.log")
        raise
