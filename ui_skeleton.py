# ui_skeleton.py
# Author: Kenneth Walker
# Date: 2025-07-23
# Version: VC-4

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import re 

# This is a functional prototype for the UI.
# Phase C: Prototyping - Version VC-4
# Functionality Added:
# - Application now starts in fullscreen mode.
# - Added a main menu bar (File, View, Tools).
# - Added Exit and Toggle Fullscreen functionality (and ESC key binding).
# - Added a "Target Field" dropdown in the Pattern Editor.
# - "Test Pattern" now uses the Target Field to apply the correct highlight color.

class KyoQAToolApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # --- Basic Window Setup ---
        self.title("First AI Utility - Kyocera QA Tool")
        self.is_fullscreen = True
        self.attributes('-fullscreen', self.is_fullscreen)
        self.bind("<Escape>", self.toggle_fullscreen)
        
        # --- Mock Data and State Variables ---
        self.review_filter_var = tk.StringVar(value="All")
        self.pattern_target_field = tk.StringVar(value="Model") # Default pattern type
        self._create_mock_data()

        # --- Load Icons (using placeholders for now) ---
        self.browse_icon = tk.PhotoImage(width=16, height=16)
        self.start_icon = tk.PhotoImage(width=16, height=16)
        self.stop_icon = tk.PhotoImage(width=16, height=16)
        self.open_icon = tk.PhotoImage(width=16, height=16)
        self.patterns_icon = tk.PhotoImage(width=16, height=16)
        self.next_icon = tk.PhotoImage(width=16, height=16)
        self.prev_icon = tk.PhotoImage(width=16, height=16)

        # --- Configure Styles ---
        self._setup_styles()

        # --- Create Widgets ---
        self._create_menu()
        self._create_widgets()
        
        # --- Final UI Setup ---
        self._populate_review_tree()
        self.review_tree.bind("<<TreeviewSelect>>", self.on_file_select)
        self.protocol("WM_DELETE_WINDOW", self.on_exit)


    def _create_mock_data(self):
        """Creates a sample data structure to simulate real processed files."""
        self.processed_files = [
            {
                "id": "item001", "filename": "QA_2024_Doc1.pdf", "status": "Needs Review",
                "text": "This document covers the ECOSYS M2540dn. The relevant QA number is QA-2024-001. Please refer to this for all service inquiries.",
                "found_items": [
                    {"type": "model", "text": "ECOSYS M2540dn"},
                    {"type": "qa_number", "text": "QA-2024-001"}
                ]
            },
            {
                "id": "item002", "filename": "Service_Bulletin_45.pdf", "status": "Pass",
                "text": "Service bulletin for TASKalfa 3554ci. This machine requires a firmware update. The bulletin ID is SB-45.",
                 "found_items": [
                    {"type": "model", "text": "TASKalfa 3554ci"},
                    {"type": "qa_number", "text": "SB-45"}
                ]
            },
            {
                "id": "item003", "filename": "Scanned_Manual.pdf", "status": "Pass (OCR)",
                "text": "A scanned document for the classic FS-1020D model. No specific QA number is listed in this version of the manual.",
                 "found_items": [{"type": "model", "text": "FS-1020D"}]
            }
        ]

    def _setup_styles(self):
        """Configures the visual styles for all ttk widgets."""
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.colors = {
            "BRAND_RED": "#DA291C", "BACKGROUND": "#F0F2F5", "FRAME_BG": "#FFFFFF",
            "ACCENT_BLUE": "#0078D4", "SUCCESS_GREEN": "#107C10", "WARN_ORANGE": "#FFA500",
            "PASTEL_GREEN": "#C8E6C9", "PASTEL_YELLOW": "#FFF9C4",
        }

        self.configure(bg=self.colors["BACKGROUND"])
        self.style.configure("TFrame", background=self.colors["BACKGROUND"])
        self.style.configure("TLabel", background=self.colors["FRAME_BG"], font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background=self.colors["BACKGROUND"], font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=8)
        self.style.configure("Red.TButton", font=("Segoe UI", 12, "bold"), background=self.colors["BRAND_RED"], foreground="white")
        self.style.map("Red.TButton", background=[('active', '#A81F14')])
        self.style.configure("TNotebook", background=self.colors["BACKGROUND"], borderwidth=0)
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[10, 5], borderwidth=0)
        self.style.map("TNotebook.Tab", 
            background=[("selected", self.colors["FRAME_BG"]), ("!selected", self.colors["BACKGROUND"])],
            expand=[("selected", [1, 1, 1, 0])]
        )
        self.style.configure("Treeview", rowheight=25, font=("Segoe UI", 9), fieldbackground=self.colors["FRAME_BG"])
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[('selected', self.colors["ACCENT_BLUE"])])

    def _create_menu(self):
        """Creates the main menu bar for the application."""
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        # File Menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.on_exit)

        # View Menu
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Fullscreen (Esc)", command=self.toggle_fullscreen)

        # Tools Menu
        tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Pattern Manager", command=lambda: messagebox.showinfo("Placeholder", "Pattern Manager window will open here."))

    def _create_widgets(self):
        """Creates and lays out all the main widgets in the window."""
        main_container = ttk.Frame(self, style="TFrame")
        main_container.pack(expand=True, fill="both", padx=10, pady=5)

        header_frame = ttk.Frame(main_container, style="TFrame", padding=(0, 0, 0, 10))
        header_frame.pack(side="top", fill="x")
        
        ttk.Label(header_frame, text="KYOCERA", foreground=self.colors["BRAND_RED"], background=self.colors["BACKGROUND"], font=("Arial Black", 24)).pack(side="left")
        ttk.Label(header_frame, text="First AI Utility", background=self.colors["BACKGROUND"], font=("Segoe UI", 16)).pack(side="left", padx=20, pady=(5,0))

        notebook = ttk.Notebook(main_container)
        notebook.pack(expand=True, fill="both")

        processing_tab = ttk.Frame(notebook, padding=15, style="TFrame")
        review_tab = ttk.Frame(notebook, padding=15, style="TFrame")
        
        notebook.add(processing_tab, text="  Processing  ")
        notebook.add(review_tab, text="  Document Review  ")

        self._create_processing_tab(processing_tab)
        self._create_review_tab(review_tab)

    def _create_processing_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1) 
        io_frame = ttk.LabelFrame(parent, text=" 1. Select Inputs ", padding=15)
        io_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        io_frame.columnconfigure(1, weight=1)
        ttk.Label(io_frame, text="Excel Template:", background=self.colors["FRAME_BG"]).grid(row=0, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(io_frame).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(io_frame, text="Browse...", image=self.browse_icon, compound="left").grid(row=0, column=2, padx=5)
        ttk.Label(io_frame, text="PDFs Folder:", background=self.colors["FRAME_BG"]).grid(row=1, column=0, sticky="w", pady=5, padx=5)
        ttk.Entry(io_frame).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(io_frame, text="Browse...", image=self.browse_icon, compound="left").grid(row=1, column=2, padx=5)
        ctrl_frame = ttk.LabelFrame(parent, text=" 2. Run & Manage ", padding=15)
        ctrl_frame.grid(row=1, column=0, sticky="ew", pady=10)
        ctrl_frame.columnconfigure(0, weight=1)
        ttk.Button(ctrl_frame, text=" START PROCESSING", image=self.start_icon, compound="left", style="Red.TButton").pack(fill="x", ipady=5)
        status_frame = ttk.LabelFrame(parent, text=" 3. Live Status ", padding=15)
        status_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))

    def _create_review_tab(self, parent):
        parent.columnconfigure(0, weight=1, minsize=350)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(1, weight=1)

        left_pane = ttk.Frame(parent, style="TFrame")
        left_pane.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        left_pane.rowconfigure(2, weight=1)
        left_pane.columnconfigure(0, weight=1)
        ttk.Label(left_pane, text="Filter by Status:", background=self.colors["BACKGROUND"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0,5))
        filter_frame = ttk.Frame(left_pane, style="TFrame")
        filter_frame.grid(row=1, column=0, sticky="ew", pady=(0,10))
        filters = ["All", "Pass", "Needs Review", "Fail"]
        for status in filters:
            ttk.Radiobutton(filter_frame, text=status, value=status, variable=self.review_filter_var).pack(side="left", padx=5)
        tree_container = ttk.Frame(left_pane, style="TFrame")
        tree_container.grid(row=2, column=0, sticky="nsew")
        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)
        self.review_tree = ttk.Treeview(tree_container, columns=('File', 'Status'), show='headings')
        self.review_tree.grid(row=0, column=0, sticky="nsew")
        self.review_tree.heading('File', text='File Name')
        self.review_tree.heading('Status', text='Status')
        self.review_tree.column('File', width=250)
        self.review_tree.column('Status', width=100, anchor="center")
        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.review_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.review_tree.configure(yscrollcommand=tree_scroll.set)

        right_pane = ttk.Frame(parent, style="TFrame")
        right_pane.grid(row=1, column=1, sticky="nsew")
        right_pane.rowconfigure(1, weight=1)
        right_pane.columnconfigure(0, weight=1)
        
        nav_controls_frame = ttk.Frame(right_pane, style="TFrame")
        nav_controls_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        ttk.Button(nav_controls_frame, text="< Prev Doc", image=self.prev_icon, compound="left", command=self.select_prev_file).pack(side="left")
        ttk.Button(nav_controls_frame, text="Next Doc >", image=self.next_icon, compound="right", command=self.select_next_file).pack(side="left", padx=5)
        ttk.Button(nav_controls_frame, text="Open Original PDF", image=self.open_icon, compound="left").pack(side="right")
        
        text_container = ttk.Frame(right_pane, borderwidth=1, relief="sunken")
        text_container.grid(row=1, column=0, sticky="nsew")
        text_container.rowconfigure(0, weight=1)
        text_container.columnconfigure(0, weight=1)
        self.doc_text = tk.Text(text_container, wrap="word", font=("Consolas", 9), relief="flat", undo=True)
        self.doc_text.grid(row=0, column=0, sticky="nsew")
        doc_scroll = ttk.Scrollbar(text_container, command=self.doc_text.yview)
        doc_scroll.grid(row=0, column=1, sticky="ns")
        self.doc_text.config(yscrollcommand=doc_scroll.set)
        
        self.doc_text.tag_configure("model_found", background=self.colors["PASTEL_GREEN"])
        self.doc_text.tag_configure("qa_number_found", background=self.colors["PASTEL_YELLOW"])
        self.doc_text.insert("1.0", "Select a file from the list on the left to view its content.")
        self.doc_text.config(state=tk.DISABLED)

        pattern_frame = ttk.LabelFrame(right_pane, text=" Pattern Editor ", padding=10)
        pattern_frame.grid(row=2, column=0, sticky="ew", pady=(10,0))
        pattern_frame.columnconfigure(1, weight=1)

        ttk.Label(pattern_frame, text="Target Field:", background=self.colors["FRAME_BG"]).grid(row=0, column=0, sticky="w")
        target_field_options = ["Model", "QA Number", "Author", "Topic"]
        ttk.Combobox(pattern_frame, textvariable=self.pattern_target_field, values=target_field_options, state="readonly").grid(row=0, column=1, sticky="ew", padx=10)

        ttk.Label(pattern_frame, text="Regex Pattern:", background=self.colors["FRAME_BG"]).grid(row=1, column=0, columnspan=2, sticky="w", pady=(5,0))
        self.pattern_entry = ttk.Entry(pattern_frame, font=("Consolas", 10))
        self.pattern_entry.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        editor_buttons = ttk.Frame(pattern_frame)
        editor_buttons.grid(row=3, column=0, columnspan=2, sticky="w", pady=(5,0))
        
        ttk.Button(editor_buttons, text="Suggest from Highlight", command=self.on_suggest_pattern).pack(side="left")
        ttk.Button(editor_buttons, text="Test Pattern", command=self.on_test_pattern).pack(side="left", padx=10)
        ttk.Button(editor_buttons, text="Save to Custom Patterns", style="Red.TButton").pack(side="right")

    # --- App Control Functions ---

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)

    def on_exit(self):
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.destroy()

    # --- Review Tab Functions ---

    def _populate_review_tree(self):
        for item in self.review_tree.get_children():
            self.review_tree.delete(item)
        for file_data in self.processed_files:
            self.review_tree.insert("", "end", iid=file_data["id"], values=(file_data["filename"], file_data["status"]))

    def on_file_select(self, event=None):
        selection = self.review_tree.selection()
        if not selection: return
        
        item_id = selection[0]
        file_data = next((f for f in self.processed_files if f["id"] == item_id), None)
        
        if file_data:
            self.doc_text.config(state=tk.NORMAL)
            self.doc_text.delete("1.0", tk.END)
            self.doc_text.insert("1.0", file_data["text"])
            
            for item in file_data.get("found_items", []):
                tag_name = f"{item['type']}_found"
                self._highlight_text(item["text"], tag_name)

            self.doc_text.config(state=tk.DISABLED)

    def select_next_file(self):
        selection = self.review_tree.selection()
        if not selection and self.review_tree.get_children():
            self.review_tree.selection_set(self.review_tree.get_children()[0])
            return
        next_item = self.review_tree.next(selection[0])
        if next_item:
            self.review_tree.selection_set(next_item)
            self.review_tree.see(next_item)

    def select_prev_file(self):
        selection = self.review_tree.selection()
        if not selection: return
        prev_item = self.review_tree.prev(selection[0])
        if prev_item:
            self.review_tree.selection_set(prev_item)
            self.review_tree.see(prev_item)

    def _highlight_text(self, text_to_find, tag):
        start_pos = "1.0"
        while True:
            start_pos = self.doc_text.search(text_to_find, start_pos, stopindex=tk.END)
            if not start_pos: break
            end_pos = f"{start_pos}+{len(text_to_find)}c"
            self.doc_text.tag_add(tag, start_pos, end_pos)
            start_pos = end_pos

    def on_suggest_pattern(self):
        try:
            selected_text = self.doc_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if not selected_text or not selected_text.strip():
                messagebox.showwarning("No Selection", "Please highlight text to generate a pattern.", parent=self)
                return
            
            escaped = re.escape(selected_text.strip())
            pattern = re.sub(r'\\d+', r'\\d+', escaped)
            final_pattern = f"\\b{pattern}\\b"
            self.pattern_entry.delete(0, tk.END)
            self.pattern_entry.insert(0, final_pattern)
        except tk.TclError:
            messagebox.showwarning("No Selection", "Please highlight text to create a pattern for.", parent=self)

    def on_test_pattern(self):
        self.doc_text.config(state=tk.NORMAL)
        for tag in ["model_found", "qa_number_found"]:
            self.doc_text.tag_remove(tag, "1.0", tk.END)

        pattern_str = self.pattern_entry.get()
        if not pattern_str:
            messagebox.showwarning("Input Error", "The 'Regex Pattern' box is empty.", parent=self)
            self.doc_text.config(state=tk.DISABLED)
            return

        # Determine which color tag to use based on the dropdown
        target_field = self.pattern_target_field.get()
        if target_field == "Model":
            highlight_tag = "model_found"
        elif target_field == "QA Number":
            highlight_tag = "qa_number_found"
        else: # Default for Author, Topic, etc.
            highlight_tag = "model_found"

        try:
            content = self.doc_text.get("1.0", tk.END)
            matches = list(re.finditer(pattern_str, content, re.IGNORECASE))
            
            if not matches:
                messagebox.showinfo("No Matches", "The pattern did not find any matches.", parent=self)
            else:
                for match in matches:
                    start_index = f"1.0+{match.start()}c"
                    end_index = f"1.0+{match.end()}c"
                    self.doc_text.tag_add(highlight_tag, start_index, end_index)
                self.doc_text.see(f"1.o+{matches[0].start()}c")
        except re.error as e:
            messagebox.showerror("Invalid Pattern", f"The regular expression is invalid:\n{e}", parent=self)
        finally:
            self.doc_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    app = KyoQAToolApp()
    app.mainloop()
