# main_app.py
# Author: Kenneth Walker
# Date: 2025-08-15
# Version: VA-1.8 (Final Alpha)

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
from pathlib import Path
import os
import subprocess
import sys
import threading
import queue
import time
import importlib.util

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
DEFAULT_EXCEL_FILE = "kb_knowledge.xlsx"

#==============================================================================
# PATTERN MANAGER DIALOGS & WINDOWS
#==============================================================================

class PatternEditDialog(tk.Toplevel):
    def __init__(self, parent, pattern_data=None):
        super().__init__(parent)
        self.transient(parent); self.grab_set()
        self.title("Edit Pattern" if pattern_data else "Add New Pattern"); self.geometry("500x200"); self.configure(bg="#F0F2F5")
        self.pattern_data = pattern_data or {}; self.result = None
        main_frame = ttk.Frame(self, padding=15); main_frame.pack(expand=True, fill="both"); main_frame.columnconfigure(1, weight=1)
        ttk.Label(main_frame, text="Target Field:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.target_field_var = tk.StringVar(value=self.pattern_data.get("field", "Model"))
        target_field_options = ["Model", "QA Number", "Author", "Topic"]
        field_combo = ttk.Combobox(main_frame, textvariable=self.target_field_var, values=target_field_options, state="readonly")
        field_combo.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        ttk.Label(main_frame, text="Regex Pattern:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.pattern_entry_var = tk.StringVar(value=self.pattern_data.get("pattern", ""))
        pattern_entry = ttk.Entry(main_frame, textvariable=self.pattern_entry_var, font=("Consolas", 10))
        pattern_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        button_frame = ttk.Frame(main_frame); button_frame.grid(row=2, column=1, sticky="e", pady=(15,0))
        ttk.Button(button_frame, text="Save", command=self.on_save, style="Red.TButton").pack(side="left")
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left", padx=10)
    def on_save(self):
        pattern = self.pattern_entry_var.get().strip()
        if not pattern: messagebox.showwarning("Input Error", "Pattern cannot be empty.", parent=self); return
        self.result = {"field": self.target_field_var.get(), "pattern": pattern, "type": "Custom"}; self.destroy()

class PatternManagerWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent); self.transient(parent); self.grab_set()
        self.title("Pattern Manager"); self.geometry("800x600"); self.minsize(600, 400)
        self.all_patterns = self._load_patterns()
        self._load_icons(); self._setup_styles(); self._create_widgets()
        self.populate_tree()
    def _load_icons(self):
        self.add_icon=tk.PhotoImage(width=16,height=16); self.edit_icon=tk.PhotoImage(width=16,height=16); self.remove_icon=tk.PhotoImage(width=16,height=16)
    def _setup_styles(self):
        self.style = ttk.Style(self); self.style.theme_use("clam")
        self.colors = {"BRAND_RED": "#DA291C", "BACKGROUND": "#F0F2F5", "FRAME_BG": "#FFFFFF", "ACCENT_BLUE": "#0078D4", "TIP_BG": "#E1F5FE"}
        self.configure(bg=self.colors["BACKGROUND"]); self.style.configure("TFrame", background=self.colors["BACKGROUND"])
        self.style.configure("TButton", font=("Segoe UI", 10), padding=6)
        self.style.configure("Red.TButton", font=("Segoe UI", 10, "bold"), background=self.colors["BRAND_RED"], foreground="white"); self.style.map("Red.TButton", background=[('active', '#A81F14')])
        self.style.configure("Treeview", rowheight=25, font=("Segoe UI", 9), fieldbackground=self.colors["FRAME_BG"]); self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.style.configure("Tip.TFrame", background=self.colors["TIP_BG"], relief="solid", borderwidth=1); self.style.configure("Tip.TLabel", background=self.colors["TIP_BG"], font=("Segoe UI", 9))
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=15); main_frame.pack(expand=True, fill="both"); main_frame.rowconfigure(0, weight=1); main_frame.columnconfigure(0, weight=1)
        tree_container = ttk.Frame(main_frame); tree_container.grid(row=0, column=0, columnspan=2, sticky="nsew"); tree_container.rowconfigure(0, weight=1); tree_container.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(tree_container, columns=('Pattern', 'Type'), show='headings tree'); self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.heading('#0', text='Target Field'); self.tree.heading('Pattern', text='Regex Pattern'); self.tree.heading('Type', text='Type')
        self.tree.column('Pattern', width=400); self.tree.column('Type', width=100, anchor="center")
        self.tree.tag_configure('category', font=('Segoe UI', 10, 'bold'), background='#EAECEE'); self.tree.tag_configure('readonly', foreground='gray', font=('Segoe UI', 9, 'italic')); self.tree.tag_configure('custom', foreground=self.colors["ACCENT_BLUE"])
        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview); tree_scroll.grid(row=0, column=1, sticky="ns"); self.tree.configure(yscrollcommand=tree_scroll.set)
        button_frame = ttk.Frame(main_frame, padding=(0, 15, 0, 0)); button_frame.grid(row=1, column=0, sticky="w")
        ttk.Button(button_frame, text=" Add New", image=self.add_icon, compound="left", command=self.add_pattern).pack(side="left")
        ttk.Button(button_frame, text=" Edit Selected", image=self.edit_icon, compound="left", command=self.edit_pattern).pack(side="left", padx=10)
        ttk.Button(button_frame, text=" Remove Selected", image=self.remove_icon, compound="left", command=self.remove_pattern).pack(side="left")
        main_action_frame = ttk.Frame(main_frame, padding=(0, 15, 0, 0)); main_action_frame.grid(row=1, column=1, sticky="e")
        ttk.Button(main_action_frame, text="Save and Close", style="Red.TButton", command=self.on_save_and_close).pack()
        tip_bar = ttk.Frame(main_frame, style="Tip.TFrame", padding=5); tip_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10,0))
        ttk.Label(tip_bar, text="💡 Tip: 'Built-in' patterns are protected. 'Custom' patterns are your own editable rules.", style="Tip.TLabel").pack()
    def _load_patterns(self):
        all_patterns = []
        built_in_patterns = data_harvester.get_all_patterns(load_custom=False)
        for field, pattern_list in built_in_patterns.items():
            for pattern in pattern_list: all_patterns.append({"field": field.replace("_", " ").capitalize(), "pattern": pattern, "type": "Built-in"})
        if CUSTOM_PATTERNS_FILE.exists():
            try:
                spec = importlib.util.spec_from_file_location("custom_patterns", CUSTOM_PATTERNS_FILE)
                custom_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(custom_module)
                field_map = {"MODEL_PATTERNS": "Model", "QA_NUMBER_PATTERNS": "QA Number"}
                for list_name, field_name in field_map.items():
                    custom_list = getattr(custom_module, list_name, [])
                    for pattern in custom_list:
                        is_duplicate = any(p['pattern'] == pattern and p['type'] == 'Built-in' for p in all_patterns)
                        if not is_duplicate: all_patterns.append({"field": field_name, "pattern": pattern, "type": "Custom"})
            except Exception as e: print(f"Error loading custom patterns file: {e}")
        return all_patterns
    def populate_tree(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        categories = {}; self.all_patterns.sort(key=lambda p: (p['field'], p['type'], p['pattern']))
        for i, p in enumerate(self.all_patterns):
            field = p["field"]
            if field not in categories: categories[field] = self.tree.insert("", "end", text=f" {field}", open=True, tags=('category',))
            item_id = f"pattern_{i}"; parent_id = categories[field]
            tag_to_use = 'readonly' if p["type"] == "Built-in" else 'custom'
            self.tree.insert(parent_id, "end", iid=item_id, values=(p["pattern"], p["type"]), tags=(tag_to_use,))
    def add_pattern(self):
        dialog = PatternEditDialog(self); self.wait_window(dialog)
        if dialog.result: self.all_patterns.append(dialog.result); self.populate_tree()
    def edit_pattern(self):
        selection = self.tree.selection()
        if not selection: messagebox.showwarning("No Selection", "Please select a pattern to edit.", parent=self); return
        item_id = selection[0]
        if 'readonly' in self.tree.item(item_id, "tags"): messagebox.showinfo("Read-only", "Built-in patterns cannot be edited.", parent=self); return
        pattern_index = int(item_id.split('_')[1]); original_data = self.all_patterns[pattern_index]
        dialog = PatternEditDialog(self, original_data); self.wait_window(dialog)
        if dialog.result: self.all_patterns[pattern_index] = dialog.result; self.populate_tree()
    def remove_pattern(self):
        selection = self.tree.selection()
        if not selection: messagebox.showwarning("No Selection", "Please select a pattern to remove.", parent=self); return
        item_id = selection[0]
        if 'readonly' in self.tree.item(item_id, "tags"): messagebox.showerror("Permission Denied", "Built-in patterns cannot be removed.", parent=self); return
        if messagebox.askyesno("Confirm Remove", "Are you sure you want to remove this custom pattern?"):
            pattern_index = int(item_id.split('_')[1]); self.all_patterns[pattern_index] = None
            self.all_patterns = [p for p in self.all_patterns if p is not None]; self.populate_tree()
    def on_save_and_close(self):
        custom_patterns = {"MODEL_PATTERNS": [], "QA_NUMBER_PATTERNS": []}
        field_map = {"Model": "MODEL_PATTERNS", "QA Number": "QA_NUMBER_PATTERNS"}
        for p in self.all_patterns:
            if p["type"] == "Custom":
                list_name = field_map.get(p["field"])
                if list_name: custom_patterns[list_name].append(p["pattern"])
        try:
            with open(CUSTOM_PATTERNS_FILE, "w", encoding="utf-8") as f:
                f.write("# custom_patterns.py\n# This file is auto-generated by the First AI Utility.\n# Manual edits may be overwritten.\n\n")
                for list_name, patterns in custom_patterns.items():
                    f.write(f"{list_name} = [\n")
                    for pattern in sorted(patterns):
                        safe_pattern = pattern.replace("'", "\\'"); f.write(f"    r'{safe_pattern}',\n")
                    f.write("]\n\n")
            messagebox.showinfo("Success", "Custom patterns have been saved.", parent=self); self.destroy()
        except Exception as e: messagebox.showerror("Save Error", f"Could not write to custom_patterns.py:\n{e}", parent=self)

#==============================================================================
# MAIN APPLICATION CLASS
#==============================================================================

class KyoQAToolApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("First AI Utility - Kyocera QA Tool")
        self.is_fullscreen = True; self.attributes('-fullscreen', self.is_fullscreen); self.bind("<Escape>", self.toggle_fullscreen)
        self.review_filter_var = tk.StringVar(value="All"); self.pattern_target_field = tk.StringVar(value="Model")
        self.processed_files = []; self.status_current_file = tk.StringVar(value="Ready to process.")
        self.progress_value = tk.DoubleVar(value=0); self.time_remaining_var = tk.StringVar(value="--:--")
        self.progress_text_var = tk.StringVar(value="0%")
        self.count_pass = tk.IntVar(value=0); self.count_fail = tk.IntVar(value=0); self.count_review = tk.IntVar(value=0)
        self.is_processing = False; self.ui_queue = queue.Queue()
        self._load_icons(); self._setup_styles(); self._create_menu(); self._create_widgets()
        self.review_tree.bind("<<TreeviewSelect>>", self.on_file_select); self.protocol("WM_DELETE_WINDOW", self.on_exit)
        PDF_TEXT_OUTPUT_DIR.mkdir(exist_ok=True); OUTPUT_DIR.mkdir(exist_ok=True)
        self._find_default_excel()
        self.after(100, self.process_ui_queue)

    def _load_icons(self):
        self.browse_icon=tk.PhotoImage(width=16,height=16); self.start_icon=tk.PhotoImage(width=16,height=16); self.next_icon=tk.PhotoImage(width=16,height=16)
        self.prev_icon=tk.PhotoImage(width=16,height=16); self.open_icon=tk.PhotoImage(width=16,height=16); self.rescan_icon=tk.PhotoImage(width=16,height=16)
        self.flag_icon=tk.PhotoImage(width=16,height=16)

    def _setup_styles(self):
        self.style = ttk.Style(self); self.style.theme_use("clam")
        self.colors = {
            "BRAND_RED": "#DA291C", "BACKGROUND": "#F0F2F5", "FRAME_BG": "#FFFFFF", "ACCENT_BLUE": "#0078D4",
            "PASTEL_GREEN": "#C8E6C9", "PASTEL_YELLOW": "#FFF9C4", "PASTEL_RED": "#FFCDD2",
            "SUCCESS_GREEN": "#107C10", "WARN_ORANGE": "#FFA500", "REASON_BG": "#FFF9C4"
        }
        self.configure(bg=self.colors["BACKGROUND"]); self.style.configure("TFrame", background=self.colors["BACKGROUND"])
        self.style.configure("TLabel", background=self.colors["FRAME_BG"], font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=8)
        self.style.configure("Red.TButton", font=("Segoe UI", 12, "bold"), background=self.colors["BRAND_RED"], foreground="white"); self.style.map("Red.TButton", background=[('active', '#A81F14')])
        self.style.configure("TNotebook", background=self.colors["BACKGROUND"], borderwidth=0)
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[10, 5], borderwidth=0); self.style.map("TNotebook.Tab", background=[("selected", self.colors["FRAME_BG"]), ("!selected", self.colors["BACKGROUND"])], expand=[("selected", [1, 1, 1, 0])])
        self.style.configure("Treeview", rowheight=25, font=("Segoe UI", 9), fieldbackground=self.colors["FRAME_BG"]); self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[('selected', self.colors["ACCENT_BLUE"])])
        self.style.configure("Reason.TLabel", background=self.colors["REASON_BG"], foreground="#5D4037", padding=5, font=("Segoe UI", 9, "italic"), borderwidth=1, relief="solid")
        self.style.layout('Red.Horizontal.TProgressbar', [('Red.Horizontal.TProgressbar.trough', {'children': [('Red.Horizontal.TProgressbar.pbar', {'side': 'left', 'sticky': 'ns'})], 'sticky': 'nswe'})])
        self.style.configure('Red.Horizontal.TProgressbar', background=self.colors["BRAND_RED"])
        self.style.layout('Orange.Horizontal.TProgressbar', [('Orange.Horizontal.TProgressbar.trough', {'children': [('Orange.Horizontal.TProgressbar.pbar', {'side': 'left', 'sticky': 'ns'})], 'sticky': 'nswe'})])
        self.style.configure('Orange.Horizontal.TProgressbar', background=self.colors["WARN_ORANGE"])
        self.style.layout('Green.Horizontal.TProgressbar', [('Green.Horizontal.TProgressbar.trough', {'children': [('Green.Horizontal.TProgressbar.pbar', {'side': 'left', 'sticky': 'ns'})], 'sticky': 'nswe'})])
        self.style.configure('Green.Horizontal.TProgressbar', background=self.colors["SUCCESS_GREEN"])

    def _create_menu(self):
        self.menu_bar = tk.Menu(self); self.config(menu=self.menu_bar)
        file_menu = tk.Menu(self.menu_bar, tearoff=0); self.menu_bar.add_cascade(label="File", menu=file_menu); file_menu.add_command(label="Exit", command=self.on_exit)
        view_menu = tk.Menu(self.menu_bar, tearoff=0); self.menu_bar.add_cascade(label="View", menu=view_menu); view_menu.add_command(label="Toggle Fullscreen (Esc)", command=self.toggle_fullscreen)
        tools_menu = tk.Menu(self.menu_bar, tearoff=0); self.menu_bar.add_cascade(label="Tools", menu=tools_menu); tools_menu.add_command(label="Pattern Manager", command=self.open_pattern_manager)

    def _create_widgets(self):
        main_container = ttk.Frame(self, style="TFrame"); main_container.pack(expand=True, fill="both", padx=10, pady=5)
        header_frame = ttk.Frame(main_container, style="TFrame", padding=(0, 0, 0, 10)); header_frame.pack(side="top", fill="x")
        ttk.Label(header_frame, text="KYOCERA", foreground=self.colors["BRAND_RED"], background=self.colors["BACKGROUND"], font=("Arial Black", 24)).pack(side="left")
        ttk.Label(header_frame, text="First AI Utility", background=self.colors["BACKGROUND"], font=("Segoe UI", 16)).pack(side="left", padx=20, pady=(5,0))
        notebook = ttk.Notebook(main_container); notebook.pack(expand=True, fill="both")
        processing_tab = ttk.Frame(notebook, padding=15, style="TFrame"); review_tab = ttk.Frame(notebook, padding=15, style="TFrame")
        notebook.add(processing_tab, text="  Processing  "); notebook.add(review_tab, text="  Document Review  ")
        self._create_processing_tab(processing_tab); self._create_review_tab(review_tab)

    def _create_processing_tab(self, parent):
        parent.columnconfigure(0, weight=1); parent.rowconfigure(2, weight=1)
        io_frame = ttk.LabelFrame(parent, text=" 1. Select Inputs ", padding=15); io_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10)); io_frame.columnconfigure(1, weight=1)
        self.excel_path_var = tk.StringVar(); ttk.Label(io_frame, text="Excel Template:", background=self.colors["FRAME_BG"]).grid(row=0, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(io_frame, textvariable=self.excel_path_var, state="readonly").grid(row=0, column=1, sticky="ew", padx=5); ttk.Button(io_frame, text="Browse...", image=self.browse_icon, compound="left", command=self.browse_excel).grid(row=0, column=2, padx=5)
        self.pdf_source_var = tk.StringVar(); ttk.Label(io_frame, text="PDF Source:", background=self.colors["FRAME_BG"]).grid(row=1, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(io_frame, textvariable=self.pdf_source_var, state="readonly").grid(row=1, column=1, sticky="ew", padx=5)
        browse_button_frame = ttk.Frame(io_frame); browse_button_frame.grid(row=1, column=2, padx=5)
        ttk.Button(browse_button_frame, text="Folder", command=self.browse_folder).pack(side="left"); ttk.Button(browse_button_frame, text="Files", command=self.browse_files).pack(side="left", padx=5)
        ctrl_frame = ttk.LabelFrame(parent, text=" 2. Run & Manage ", padding=15); ctrl_frame.grid(row=1, column=0, sticky="ew", pady=10); ctrl_frame.columnconfigure(0, weight=1)
        self.start_button = ttk.Button(ctrl_frame, text=" START PROCESSING", image=self.start_icon, compound="left", style="Red.TButton", command=self.start_processing); self.start_button.pack(fill="x", ipady=5, side="left", expand=True)
        ttk.Button(ctrl_frame, text="Open Output", command=self.open_output_folder).pack(fill="x", ipady=5, side="right", padx=(10,0))
        status_frame = ttk.LabelFrame(parent, text=" 3. Live Status ", padding=15); status_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0)); status_frame.columnconfigure(0, weight=1); status_frame.rowconfigure(1, weight=1)
        progress_info_frame = ttk.Frame(status_frame, style="TFrame"); progress_info_frame.grid(row=0, column=0, sticky="ew", pady=5); progress_info_frame.columnconfigure(0, weight=1)
        pbar_container = ttk.Frame(progress_info_frame); pbar_container.grid(row=0, column=0, sticky="ew", padx=(0,10))
        pbar_container.columnconfigure(0, weight=1); pbar_container.rowconfigure(0, weight=1)
        self.pbar = ttk.Progressbar(pbar_container, variable=self.progress_value, style='Red.Horizontal.TProgressbar')
        self.pbar.grid(row=0, column=0, sticky="ew")
        pbar_label = ttk.Label(pbar_container, textvariable=self.progress_text_var, background=self.colors["BACKGROUND"], foreground="white", font=("Segoe UI", 9, "bold"), anchor="center")
        pbar_label.grid(row=0, column=0, sticky="ew")
        ttk.Label(progress_info_frame, textvariable=self.time_remaining_var, background=self.colors["BACKGROUND"]).grid(row=0, column=1)
        ttk.Label(progress_info_frame, textvariable=self.status_current_file, background=self.colors["BACKGROUND"], font=("Segoe UI", 9, "italic")).grid(row=1, column=0, columnspan=2, sticky="w", pady=(5,0))
        summary_frame = ttk.Frame(progress_info_frame, style="TFrame"); summary_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10,0))
        counters = [("Pass:", self.count_pass, self.colors["SUCCESS_GREEN"]), ("Fail:", self.count_fail, self.colors["BRAND_RED"]), ("Review:", self.count_review, self.colors["WARN_ORANGE"])]
        for text, var, color in counters:
            ttk.Label(summary_frame, text=text, background=self.colors["BACKGROUND"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 2))
            ttk.Label(summary_frame, textvariable=var, background=self.colors["BACKGROUND"], foreground=color, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 20))

    def _create_review_tab(self, parent):
        parent.columnconfigure(0, weight=1, minsize=350); parent.columnconfigure(1, weight=2); parent.rowconfigure(2, weight=1)
        left_pane = ttk.Frame(parent, style="TFrame"); left_pane.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10)); left_pane.rowconfigure(2, weight=1); left_pane.columnconfigure(0, weight=1)
        ttk.Label(left_pane, text="Filter by Status:", background=self.colors["BACKGROUND"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0,5))
        filter_frame = ttk.Frame(left_pane, style="TFrame"); filter_frame.grid(row=1, column=0, sticky="ew", pady=(0,10))
        filters = ["All", "Pass", "Needs Review", "Fail"];
        for status in filters: ttk.Radiobutton(filter_frame, text=status, value=status, variable=self.review_filter_var, command=self._populate_review_tree).pack(side="left", padx=5)
        tree_container = ttk.Frame(left_pane, style="TFrame"); tree_container.grid(row=2, column=0, sticky="nsew"); tree_container.rowconfigure(0, weight=1); tree_container.columnconfigure(0, weight=1)
        self.review_tree = ttk.Treeview(tree_container, columns=('File', 'Status'), show='headings'); self.review_tree.grid(row=0, column=0, sticky="nsew")
        self.review_tree.heading('File', text='File Name'); self.review_tree.heading('Status', text='Status'); self.review_tree.column('File', width=250); self.review_tree.column('Status', width=100, anchor="center")
        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.review_tree.yview); tree_scroll.grid(row=0, column=1, sticky="ns"); self.review_tree.configure(yscrollcommand=tree_scroll.set)
        right_pane = ttk.Frame(parent, style="TFrame"); right_pane.grid(row=0, column=1, rowspan=3, sticky="nsew"); right_pane.rowconfigure(2, weight=1); right_pane.columnconfigure(0, weight=1)
        nav_controls_frame = ttk.Frame(right_pane, style="TFrame"); nav_controls_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        ttk.Button(nav_controls_frame, text="< Prev Doc", image=self.prev_icon, compound="left", command=self.select_prev_file).pack(side="left")
        ttk.Button(nav_controls_frame, text="Next Doc >", image=self.next_icon, compound="right", command=self.select_next_file).pack(side="left", padx=5)
        ttk.Button(nav_controls_frame, text="Re-scan", image=self.rescan_icon, compound="left", command=self.on_rescan).pack(side="left", padx=5)
        ttk.Button(nav_controls_frame, text="Flag Text", image=self.flag_icon, compound="left", command=self.on_flag_selection).pack(side="left", padx=5)
        ttk.Button(nav_controls_frame, text="Open Original PDF", image=self.open_icon, compound="left", command=self.open_original_pdf).pack(side="right")
        self.reason_label = ttk.Label(right_pane, text="Reason: N/A", style="Reason.TLabel"); self.reason_label.grid(row=1, column=0, sticky="ew", pady=(0,5))
        text_container = ttk.Frame(right_pane, borderwidth=1, relief="sunken"); text_container.grid(row=2, column=0, sticky="nsew"); text_container.rowconfigure(0, weight=1); text_container.columnconfigure(0, weight=1)
        self.doc_text = tk.Text(text_container, wrap="word", font=("Consolas", 9), relief="flat", undo=True); self.doc_text.grid(row=0, column=0, sticky="nsew")
        doc_scroll = ttk.Scrollbar(text_container, command=self.doc_text.yview); doc_scroll.grid(row=0, column=1, sticky="ns"); self.doc_text.config(yscrollcommand=doc_scroll.set)
        self.doc_text.tag_configure("model_found", background=self.colors["PASTEL_GREEN"])
        self.doc_text.tag_configure("qa_number_found", background=self.colors["PASTEL_YELLOW"])
        self.doc_text.tag_configure("flagged_found", background=self.colors["PASTEL_RED"])
        self.doc_text.insert("1.0", "Select files to process using the 'Processing' tab."); self.doc_text.config(state=tk.DISABLED)
        pattern_frame = ttk.LabelFrame(right_pane, text=" Quick Pattern Editor ", padding=10); pattern_frame.grid(row=3, column=0, sticky="ew", pady=(10,0)); pattern_frame.columnconfigure(1, weight=1)
        ttk.Label(pattern_frame, text="Target Field:", background=self.colors["FRAME_BG"]).grid(row=0, column=0, sticky="w")
        target_field_options = ["Model", "QA Number"]; ttk.Combobox(pattern_frame, textvariable=self.pattern_target_field, values=target_field_options, state="readonly").grid(row=0, column=1, sticky="ew", padx=10)
        ttk.Label(pattern_frame, text="Regex Pattern:", background=self.colors["FRAME_BG"]).grid(row=1, column=0, columnspan=2, sticky="w", pady=(5,0))
        self.pattern_entry = ttk.Entry(pattern_frame, font=("Consolas", 10)); self.pattern_entry.grid(row=2, column=0, columnspan=2, sticky="ew")
        editor_buttons = ttk.Frame(pattern_frame); editor_buttons.grid(row=3, column=0, columnspan=2, sticky="w", pady=(5,0))
        ttk.Button(editor_buttons, text="Suggest from Highlight", command=self.on_suggest_pattern).pack(side="left")
        ttk.Button(editor_buttons, text="Test Pattern", command=self.on_test_pattern).pack(side="left", padx=10)
        ttk.Button(editor_buttons, text="Save to Custom Patterns", style="Red.TButton", command=self.on_save_custom_pattern).pack(side="right")

    def _find_default_excel(self):
        default_path = Path.cwd() / DEFAULT_EXCEL_FILE
        if default_path.exists():
            self.excel_path_var.set(str(default_path.resolve()))
            self.status_current_file.set(f"Default template '{DEFAULT_EXCEL_FILE}' loaded.")

    def toggle_fullscreen(self, event=None): self.is_fullscreen = not self.is_fullscreen; self.attributes("-fullscreen", self.is_fullscreen)
    def on_exit(self):
        if self.is_processing: messagebox.showwarning("Busy", "Cannot exit while processing is in progress."); return
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"): self.destroy()
    def open_pattern_manager(self): manager = PatternManagerWindow(self); manager.focus_set()
    def browse_excel(self):
        path = filedialog.askopenfilename(title="Select Excel Template", filetypes=[("Excel Files", "*.xlsx *.xlsm"), ("All Files", "*.*")])
        if path: self.excel_path_var.set(path)
    def browse_folder(self):
        path = filedialog.askdirectory(title="Select Folder Containing PDFs")
        if path: self.pdf_source_var.set(path); self.selected_pdf_paths = sorted(list(Path(path).glob("*.pdf")))
    def browse_files(self):
        paths = filedialog.askopenfilenames(title="Select PDF Files", filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")])
        if paths: self.pdf_source_var.set(f"{len(paths)} files selected"); self.selected_pdf_paths = sorted([Path(p) for p in paths])
    def open_output_folder(self):
        try:
            if sys.platform == "win32": os.startfile(OUTPUT_DIR)
            elif sys.platform == "darwin": subprocess.call(["open", str(OUTPUT_DIR)])
            else: subprocess.call(["xdg-open", str(OUTPUT_DIR)])
        except Exception as e: messagebox.showerror("Error", f"Could not open output folder: {e}")

    def start_processing(self):
        if self.is_processing: messagebox.showwarning("Busy", "A processing job is already running."); return
        if not hasattr(self, 'selected_pdf_paths') or not self.selected_pdf_paths: messagebox.showwarning("Input Missing", "Please select PDF files or a folder."); return
        if not self.excel_path_var.get(): messagebox.showwarning("Input Missing", "Please select an Excel template file."); return
        self.is_processing = True; self.processed_files.clear(); self._populate_review_tree()
        self.count_pass.set(0); self.count_fail.set(0); self.count_review.set(0)
        self.start_button.config(state=tk.DISABLED)
        threading.Thread(target=self.processing_thread, args=(self.selected_pdf_paths, self.excel_path_var.get()), daemon=True).start()

    def processing_thread(self, pdf_paths, excel_template_path):
        total_files = len(pdf_paths)
        start_time = time.time()
        for i, pdf_path in enumerate(pdf_paths):
            elapsed_time = time.time() - start_time
            avg_time_per_file = elapsed_time / (i + 1) if i > 0 else 2
            files_remaining = total_files - (i + 1)
            eta_seconds = int(files_remaining * avg_time_per_file)
            eta_str = f"{eta_seconds // 60:02d}:{eta_seconds % 60:02d}" if i > 0 else "--:--"
            progress_percent = ((i + 1) / total_files) * 100
            progress_data = { "type": "progress", "value": progress_percent, "text": f"{int(progress_percent)}% ({i+1}/{total_files})", "eta": eta_str }
            self.ui_queue.put(progress_data)
            extraction_result = ocr_utils.extract_text_from_pdf(pdf_path)
            full_text = extraction_result["text"]
            if "TESSERACT NOT FOUND" in full_text: self.ui_queue.put({"type": "error", "msg": "Tesseract is not in your system's PATH."});
            if extraction_result["ocr_used"]: self.ui_queue.put({"type": "status", "msg": f"Running OCR on {pdf_path.name}..."})
            txt_path = PDF_TEXT_OUTPUT_DIR / f"{pdf_path.stem}.txt"; txt_path.write_text(full_text, encoding='utf-8', errors='replace')
            harvest_results = data_harvester.harvest_all_data(full_text)
            valid_items_found = any(not item['flagged'] for item in harvest_results["found_items"])
            status = "Pass" if valid_items_found else "Needs Review"
            if extraction_result["ocr_used"]: status += " (OCR)"
            file_data = {"id": str(pdf_path), "filename": pdf_path.name, "status": status, "text": full_text, "found_items": harvest_results["found_items"], "status_reason": harvest_results["status_reason"], "original_path": pdf_path}
            self.ui_queue.put({"type": "add_file", "data": file_data})
        self.ui_queue.put({"type": "finish", "excel_template": excel_template_path})

    def process_ui_queue(self):
        try:
            while not self.ui_queue.empty():
                msg = self.ui_queue.get_nowait(); msg_type = msg.get("type")
                if msg_type == "status": self.status_current_file.set(msg.get("msg"))
                elif msg_type == "progress":
                    self.progress_value.set(msg.get("value"))
                    self.progress_text_var.set(msg.get("text"))
                    self.time_remaining_var.set(f"ETA: {msg.get('eta')}")
                    val = msg.get("value")
                    if val < 40: self.pbar.config(style='Red.Horizontal.TProgressbar')
                    elif 40 <= val < 85: self.pbar.config(style='Orange.Horizontal.TProgressbar')
                    else: self.pbar.config(style='Green.Horizontal.TProgressbar')
                elif msg_type == "error": messagebox.showerror("Error", msg.get("msg"), parent=self)
                elif msg_type == "add_file":
                    file_data = msg.get("data"); self.processed_files.append(file_data); self._populate_review_tree()
                    if "Needs Review" in file_data["status"]: self.count_review.set(self.count_review.get() + 1)
                    elif "Fail" in file_data["status"]: self.count_fail.set(self.count_fail.get() + 1)
                    else: self.count_pass.set(self.count_pass.get() + 1)
                elif msg_type == "finish":
                    self.is_processing = False; self.start_button.config(state=tk.NORMAL)
                    self.status_current_file.set("Generating Excel report..."); self.progress_value.set(100)
                    self.progress_text_var.set("Complete!")
                    self.pbar.config(style='Green.Horizontal.TProgressbar')
                    try:
                        template_path = Path(msg.get("excel_template"))
                        output_file = excel_processor.process_excel_file(template_path, self.processed_files, OUTPUT_DIR)
                        self.status_current_file.set("Processing complete. Report saved.")
                        messagebox.showinfo("Success", f"Report saved to:\n{output_file}")
                    except Exception as e:
                        messagebox.showerror("Excel Error", f"Failed to generate Excel report:\n{e}"); self.status_current_file.set("Error generating report.")
        except queue.Empty: pass
        finally: self.after(100, self.process_ui_queue)

    def _populate_review_tree(self, event=None):
        for item in self.review_tree.get_children(): self.review_tree.delete(item)
        filter_status = self.review_filter_var.get()
        for file_data in self.processed_files:
            if filter_status == "All" or filter_status in file_data["status"]:
                self.review_tree.insert("", "end", iid=file_data["id"], values=(file_data["filename"], file_data["status"]))

    def on_file_select(self, event=None):
        selection = self.review_tree.selection()
        if not selection: self.reason_label.config(text="Reason: N/A"); return
        item_id = selection[0]
        file_data = next((f for f in self.processed_files if f["id"] == item_id), None)
        if file_data:
            self.reason_label.config(text=f"Reason: {file_data.get('status_reason', 'N/A')}")
            self.doc_text.config(state=tk.NORMAL); self.doc_text.delete("1.0", tk.END); self.doc_text.insert("1.0", file_data["text"])
            for item in file_data.get("found_items", []):
                if item.get('flagged'):
                    self._highlight_text(item["text"], "flagged_found")
                else:
                    tag_name = f"{item['type'].lower().replace(' ', '_')}_found"
                    if tag_name in self.doc_text.tag_names(): self._highlight_text(item["text"], tag_name)
            self.doc_text.config(state=tk.DISABLED)

    def select_next_file(self):
        selection = self.review_tree.selection()
        if not selection and self.review_tree.get_children(): self.review_tree.selection_set(self.review_tree.get_children()[0]); return
        if selection:
            next_item = self.review_tree.next(selection[0])
            if next_item: self.review_tree.selection_set(next_item); self.review_tree.see(next_item)
    def select_prev_file(self):
        selection = self.review_tree.selection();
        if not selection: return
        prev_item = self.review_tree.prev(selection[0])
        if prev_item: self.review_tree.selection_set(prev_item); self.review_tree.see(prev_item)
    def open_original_pdf(self):
        selection = self.review_tree.selection()
        if not selection: messagebox.showwarning("No Selection", "Please select a file to open.", parent=self); return
        item_id = selection[0]; file_data = next((f for f in self.processed_files if f["id"] == item_id), None)
        if file_data and file_data.get("original_path"):
            try:
                path = file_data["original_path"]
                if sys.platform == "win32": os.startfile(path)
                elif sys.platform == "darwin": subprocess.call(["open", str(path)])
                else: subprocess.call(["xdg-open", str(path)])
            except Exception as e: messagebox.showerror("Error", f"Could not open file: {e}", parent=self)
        else: messagebox.showerror("Error", "Could not find path for the selected file.", parent=self)
    def _highlight_text(self, text_to_find, tag):
        start_pos = "1.0"
        while True:
            start_pos = self.doc_text.search(text_to_find, start_pos, stopindex=tk.END)
            if not start_pos: break
            end_pos = f"{start_pos}+{len(text_to_find)}c"; self.doc_text.tag_add(tag, start_pos, end_pos); start_pos = end_pos
    def on_suggest_pattern(self):
        try:
            selected_text = self.doc_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if not selected_text: messagebox.showwarning("No Selection", "Please highlight text to generate a pattern.", parent=self); return
            escaped = re.escape(selected_text); pattern_core = re.sub(r'\\d\{2,}', r'\\d+', escaped)
            final_pattern = f"\\b{pattern_core}\\b"; self.pattern_entry.delete(0, tk.END); self.pattern_entry.insert(0, final_pattern)
        except tk.TclError: messagebox.showwarning("No Selection", "Please highlight text to create a pattern for.", parent=self)
    def on_test_pattern(self):
        self.doc_text.config(state=tk.NORMAL)
        for tag in self.doc_text.tag_names():
            if "test_" in tag: self.doc_text.tag_remove(tag, "1.0", tk.END)
        pattern_str = self.pattern_entry.get()
        if not pattern_str: messagebox.showwarning("Input Error", "The 'Regex Pattern' box is empty.", parent=self); self.doc_text.config(state=tk.DISABLED); return
        target_field = self.pattern_target_field.get(); highlight_tag = f"test_{target_field.lower().replace(' ', '_')}"
        self.doc_text.tag_configure(highlight_tag, background="orange")
        try:
            content = self.doc_text.get("1.0", tk.END); matches = list(re.finditer(pattern_str, content, re.IGNORECASE))
            if not matches: messagebox.showinfo("No Matches", "The pattern did not find any matches.", parent=self)
            else:
                for match in matches:
                    start_index = f"1.0+{match.start()}c"; end_index = f"1.0+{match.end()}c"
                    self.doc_text.tag_add(highlight_tag, start_index, end_index)
                self.doc_text.see(f"1.0+{matches[0].start()}c")
        except re.error as e: messagebox.showerror("Invalid Pattern", f"The regular expression is invalid:\n{e}", parent=self)
        finally: self.doc_text.config(state=tk.DISABLED)
    def on_rescan(self):
        selection = self.review_tree.selection()
        if not selection: messagebox.showwarning("No Selection", "Please select a file to re-scan.", parent=self); return
        item_id = selection[0]; file_index = next((i for i, f in enumerate(self.processed_files) if f["id"] == item_id), -1)
        if file_index != -1:
            file_data = self.processed_files[file_index]
            harvest_results = data_harvester.harvest_all_data(file_data["text"])
            file_data["found_items"] = harvest_results["found_items"]; file_data["status_reason"] = harvest_results["status_reason"]
            valid_items_found = any(not item.get('flagged', False) for item in harvest_results["found_items"])
            new_status = "Pass" if valid_items_found else "Needs Review"
            if "(OCR)" in self.review_tree.item(item_id, "values")[1]: new_status += " (OCR)"
            file_data["status"] = new_status
            self.review_tree.item(item_id, values=(file_data["filename"], file_data["status"]))
            self.on_file_select()
            messagebox.showinfo("Re-scan Complete", f"Re-scanned '{file_data['filename']}'.\nNew Status: {file_data['status']}", parent=self)

    def on_save_custom_pattern(self):
        pattern = self.pattern_entry.get().strip()
        if not pattern:
            messagebox.showwarning("Input Error", "Pattern cannot be empty.", parent=self)
            return
        target_field = self.pattern_target_field.get()
        field_map = {"Model": "MODEL_PATTERNS", "QA Number": "QA_NUMBER_PATTERNS"}
        list_name = field_map.get(target_field)
        if not list_name:
            messagebox.showerror("Error", "Invalid target field selected.")
            return

        try:
            if CUSTOM_PATTERNS_FILE.exists():
                lines = CUSTOM_PATTERNS_FILE.read_text(encoding="utf-8").splitlines()
            else:
                initial_content = "# custom_patterns.py\n\nMODEL_PATTERNS = []\n\nQA_NUMBER_PATTERNS = []\n"
                CUSTOM_PATTERNS_FILE.write_text(initial_content, encoding="utf-8")
                lines = initial_content.splitlines()

            list_content_str = "".join(lines)
            if f"r'{pattern}'" in list_content_str or f'r"{pattern}"' in list_content_str:
                messagebox.showinfo("Duplicate", "This pattern already exists.", parent=self)
                return

            list_start_index = next(i for i, line in enumerate(lines) if line.strip().startswith(list_name))
            
            # --- FIX for f-string backslash error ---
            safe_pattern = pattern.replace("'", "\\'")
            new_pattern_line = f"    r'{safe_pattern}',"
            
            lines.insert(list_start_index + 1, new_pattern_line)
            CUSTOM_PATTERNS_FILE.write_text("\n".join(lines), encoding="utf-8")
            messagebox.showinfo("Success", f"Pattern saved to {list_name} in custom_patterns.py", parent=self)
        except StopIteration:
            messagebox.showerror("File Error", f"Could not find list '{list_name}' in custom_patterns.py.", parent=self)
        except Exception as e:
            messagebox.showerror("File Error", f"Could not save to custom_patterns.py:\n{e}", parent=self)

    def on_flag_selection(self):
        try:
            selected_text = self.doc_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if not selected_text:
                messagebox.showwarning("No Selection", "Please highlight text to flag/ignore.", parent=self)
                return
            
            pattern_to_ignore = f"^{re.escape(selected_text)}$"

            if IGNORED_PATTERNS_FILE.exists():
                lines = IGNORED_PATTERNS_FILE.read_text(encoding="utf-8").splitlines()
            else:
                initial_content = "# ignored_patterns.py\n\nIGNORED_MODEL_PATTERNS = []\n"
                IGNORED_PATTERNS_FILE.write_text(initial_content, encoding="utf-8")
                lines = initial_content.splitlines()
            
            list_content_str = "".join(lines)
            if f"r'{pattern_to_ignore}'" in list_content_str:
                messagebox.showinfo("Already Flagged", "This pattern is already on the ignore list.", parent=self)
                return

            list_name = "IGNORED_MODEL_PATTERNS"
            list_start_index = next(i for i, line in enumerate(lines) if line.strip().startswith(list_name))
            new_line = f"    r'{pattern_to_ignore}',"
            lines.insert(list_start_index + 1, new_line)
            IGNORED_PATTERNS_FILE.write_text("\n".join(lines), encoding="utf-8")
            
            messagebox.showinfo("Success", f"'{selected_text}' added to ignore list.\nRe-scan to see changes.", parent=self)
        except tk.TclError:
            messagebox.showwarning("No Selection", "Please highlight text to flag.", parent=self)
        except Exception as e:
            messagebox.showerror("File Error", f"Could not save to ignored_patterns.py:\n{e}", parent=self)

#==============================================================================
# APPLICATION ENTRY POINT
#==============================================================================

if __name__ == "__main__":
    app = KyoQAToolApp()
    app.mainloop()
