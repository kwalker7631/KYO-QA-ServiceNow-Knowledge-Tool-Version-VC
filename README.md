# First AI Utility

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Version](https://img.shields.io/badge/Version-VA--1.3-orange.svg)

## Overview
The **First AI Utility** is a Python-based desktop application designed to automate the extraction of key information from Kyocera QA and service PDF documents for integration with ServiceNow knowledge bases. It processes PDFs using a hybrid approach of direct text extraction (via PyMuPDF) and Optical Character Recognition (OCR) with Tesseract for scanned documents. The tool extracts product models, QA numbers, authors, and topics using a dynamic regex-based pattern-matching system, then populates ServiceNow-compatible Excel templates (e.g., `kb_knowledge.xlsx`) with enhanced formatting for professional output.

Key features include a user-friendly Tkinter GUI, live pattern management, an intelligent flagging system to ignore false positives, and robust Excel handling. Version VA-1.3 introduces support for extracting Author and Topic fields, generalized ignore lists, and improved Excel formatting (auto-adjusted columns, text wrapping, top-aligned cells).

## Features
- **Automated PDF Processing**: Batch-process folders or individual PDFs, with output saved to `/OUTPUT/` as timestamped Excel files (e.g., `PROCESSED_kb_knowledge_2025-08-17_1030.xlsx`).
- **Hybrid Text Extraction**: Uses PyMuPDF for digital PDFs; falls back to Tesseract OCR for scanned documents (improved detection with a 300-character threshold).
- **Dynamic Pattern Matching**: Extracts Models (e.g., TASKalfa 2554ci), QA Numbers (e.g., QA_K036_SWUT-0010_SB), Authors (e.g., JUN EJIRI), and Topics (e.g., General, Desktop) using regex patterns.
- **Live Pattern Management**: Add/edit regex patterns via the Pattern Manager for Models, QA Numbers, Authors, and Topics, stored in `custom_patterns.py`.
- **Intelligent Flagging System**: Flag incorrect matches (e.g., invalid models) to add to type-specific ignore lists in `ignored_patterns.py`, with red highlights in the Review tab.
- **Enhanced Excel Output**: Populates columns like Short description (QA numbers), Description (PDF filename), Meta/Product Description (models), Author, Topic, and Processing Status. Features auto-resized columns, text wrapping, and color-coded status rows (green for Pass, yellow for Needs Review, red for Fail).
- **Automated Setup**: The `run.py` script creates a virtual environment and installs dependencies from `requirements.txt`.

## Installation

### Prerequisites
- **Python 3.9+**: Download from [python.org](https://www.python.org/downloads/). For Windows, check "Add python.exe to PATH" during installation.
- **Tesseract-OCR**: Download from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki). For Windows, select "Add Tesseract to system PATH". For Linux/macOS, install via package managers (e.g., `apt install tesseract-ocr` or `brew install tesseract`).

### Setup Steps
1. Clone or download the repository to a local folder.
2. Ensure all project files (`main_app.py`, `run.py`, `requirements.txt`, etc.) are in the same directory.
3. For Windows, double-click `START.bat`. For Linux/macOS, run `python run.py` from the terminal.
4. On first run, the script creates a virtual environment (`/venv/`) and installs dependencies (may take a few minutes). Subsequent runs are faster.

## Usage

### Processing Tab
1. **Select Excel Template**: Click *Browse...* to choose your ServiceNow Excel template (e.g., `kb_knowledge.xlsx`).
2. **Select PDFs**: Use *Folder* to select a directory or *Files* for individual PDFs.
3. **Start Processing**: Click *START PROCESSING* to extract data and generate an Excel file in `/OUTPUT/`.
4. **Monitor Progress**: View real-time updates via the status bar, progress bar, and counters.
5. **Review Output**: Check the generated Excel file for populated columns and color-coded status.

### Document Review Tab
- **View Extracted Text**: Select a PDF from the left list to see its text, with <span style="background-color: #C8E6C9;">green highlights</span> for valid matches and <span style="background-color: #FFCDD2;">red highlights</span> for ignored matches.
- **Flag Incorrect Matches**:
  - Highlight incorrect text (e.g., a misidentified model like "TASKalfa-XYZ").
  - Click *Flag Text* to add it to the appropriate ignore list (e.g., `IGNORED_MODEL_PATTERNS`).
  - Click *Re-scan* to update highlights and status (red for ignored).
- **Add New Patterns**:
  - Highlight missed text (e.g., a new model or author name).
  - Click *Suggest from Highlight* to generate a regex pattern.
  - Test it with *Test Pattern*, then save via *Save to Custom Patterns*.

### Excel Output
- **Columns Populated**:
  - *Short description*: QA numbers (e.g., QA_K036_SWUT-0010_SB) or PDF filename stem.
  - *Description*: Full PDF filename.
  - *Meta/Product Description*: Comma-separated model numbers (e.g., TASKalfa 2554ci, ECOSYS P8060cdn).
  - *Author*: Extracted author names (requires patterns like `r"Author:\s*([\w\s]+)"`).
  - *Topic*: Extracted topics (e.g., General, Desktop, based on patterns like `r"\b(General|Desktop|Applications)\b"`).
  - *Processing Status*: Pass, Needs Review, or Fail, with color-coded rows.
- **Formatting**: Auto-adjusted column widths, text wrapping, top-aligned cells, and bold headers for readability.
- **Sys ID**: Preserved for ServiceNow compatibility; new rows append without modifying existing records.

### Example Workflow
1. Load `kb_knowledge.xlsx` as the template.
2. Select a folder with PDFs like `QA_K036_SWUT-0010_SB.pdf`.
3. Process to generate an Excel file with:
   - Short description: `QA_K036_SWUT-0010_SB`
   - Meta: `TASKalfa 2554ci, ECOSYS P8060cdn`
   - Author: `JUN EJIRI` (if extracted)
   - Topic: `General`
   - Status: `Pass` (green row)
4. In the Review tab, flag an incorrect model (e.g., `TASKalfa-XYZ`) to ignore it in future scans.
5. Add a new author pattern (e.g., `r"By:\s*(\w+\s\w+)"`) via Pattern Manager.

### Export Flow
1. After processing, the Excel report is written atomically to the `OUTPUT/` folder.
2. Click **📂 Reveal in Folder** (Tip: press `Ctrl+F` to focus buttons) to open the report's location.
3. Check `error.log` if something goes wrong.

### Versions Tool
Run `python tools/versions.py` to print the installed versions of Python, PyMuPDF, openpyxl, pytesseract, Pillow, and the Tesseract CLI.

## Project File Structure
- `START.bat`: Windows launcher.
- `run.py`: Sets up virtual environment and dependencies.
- `requirements.txt`: Lists Python libraries (e.g., openpyxl, PyMuPDF, pytesseract).
- `main_app.py`: Tkinter GUI and core logic.
- `data_harvester.py`: Extracts data using regex, filters against ignore lists.
- `ocr_utils.py`: Handles PDF text extraction with OCR fallback.
- `excel_processor.py`: Clones and populates Excel templates.
- `custom_patterns.py`: Stores user-defined patterns (Models, QA Numbers, Authors, Topics).
- `ignored_patterns.py`: Stores ignored patterns (per type).
- `/venv/`: Auto-created virtual environment.
- `/OUTPUT/`: Stores processed Excel files.
- `/PDF_TEXT_OUTPUT/`: Stores raw extracted PDF text.

## Contributing
We welcome contributions to enhance the First AI Utility! To contribute:

1. **Fork the Repository**: Clone and create a branch (`git checkout -b feature/your-feature`).
2. **Add Features**:
   - Enhance `data_harvester.py` with new regex patterns (e.g., for new model formats).
   - Improve `excel_processor.py` with additional ServiceNow column mappings.
   - Optimize `ocr_utils.py` (e.g., add page markers for debugging).
3. **Test Changes**:
   - Use `kb_knowledge.xlsx` and sample PDFs to verify output.
   - Run `python run.py` to test in the virtual environment.
   - Check `error.log` for issues.
4. **Submit a Pull Request**:
   - Include a clear description of changes and test results.
   - Ensure code follows PEP 8 and maintains backward compatibility.
5. **Pattern Contributions**:
   - Add new patterns to `custom_patterns.py` (e.g., `r"Author:\s*([\w\s]+)"` for authors).
   - Test patterns in the Review tab before submitting.

## Troubleshooting
- **Tesseract Not Found**: Ensure Tesseract-OCR is installed and in your system PATH. For Windows, reinstall and check "Add to PATH". For Linux/macOS, verify with `tesseract --version`.
- **Excel Errors**: Confirm `kb_knowledge.xlsx` has a Sys ID column. Missing columns (e.g., Description, Topic) are auto-added but check header case sensitivity.
- **Syntax Errors**: Check `error.log` for details. Run `START.bat` to regenerate logs if the app crashes.
- **No Matches Found**: Add custom patterns in the Pattern Manager (e.g., `r"\b(General|FAQ)\b"` for topics) and test in the Review tab.
- **Output Issues**: Verify `/OUTPUT/` is writable. Check Excel file for color-coded rows to identify failures.
- **Contact**: For persistent issues, open a GitHub issue with `error.log` and system details.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments
Developed for the Kyocera Engineering Team by Kenneth Walker. Built with AI-assisted development to streamline QA document processing for ServiceNow integration.