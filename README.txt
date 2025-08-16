First AI Utility - Alpha Version VA-1.1
overview
The First AI Utility is a desktop application designed to automate the extraction of key information from Kyocera QA and service PDF documents. It uses a hybrid approach of direct text extraction and Optical Character Recognition (OCR) to handle both digital and scanned documents.

Its core feature is a dynamic pattern-matching system that identifies product models and QA numbers. This version introduces a flagging system to intelligently ignore incorrect or ambiguous model numbers, significantly improving accuracy and reducing the need for manual review.

Key Features
Automated PDF Processing: Process entire folders of PDFs or individual files in a single batch.

Hybrid Text Extraction: Automatically uses direct text extraction and falls back to the Tesseract OCR engine for scanned documents.

Live Pattern Management: A built-in Pattern Manager allows users to add, edit, and remove custom extraction patterns (using Regular Expressions) on-the-fly.

Interactive Document Review: A dedicated review tab allows users to inspect extracted text, see why a document was flagged, and create new patterns directly from highlighted text.

Intelligent Flagging System: Users can highlight incorrect text and add it to an "ignore list," teaching the application to disregard false positives in all future scans.

Automated Environment Setup: A launcher script (run.py) handles the automatic creation of a Python virtual environment and installation of all required dependencies.

Installation and Setup
This guide assumes a Windows operating system.

1. Prerequisites
Before running the application, you need two pieces of software installed on your system:

Python (Version 3.9 or newer): If you don't have Python, download the Windows installer (64-bit) from the official Python website.

Crucial Step: During installation, make sure to check the box that says "Add python.exe to PATH."

Tesseract-OCR Engine: This is required for the OCR functionality.

Download the recommended installer from Tesseract at UB Mannheim.

During installation, ensure that the option to "Add Tesseract to system PATH" is selected.

2. Running the Application
Place all the project files (main_app.py, run.py, requirements.txt, etc.) into a single folder.

Double-click the START.bat file.

The first time you run it, a command window will appear and perform a one-time setup which may take a few minutes. It will create a venv folder and install the necessary libraries. Subsequent launches will be much faster.

How to Use the Application
Processing Tab
Select Excel Template: Click the first Browse... button to select your master Excel file.

Select PDFs: Use the Folder or Files buttons to select the PDF documents to process.

Start Processing: Click the large red START PROCESSING button.

Monitor Progress: The status bar, progress bar, and counters provide live feedback.

Document Review Tab
This tab is for inspecting results and improving the tool's accuracy.

Select a File: Click on any file in the list on the left. Its extracted text will appear on the right.

<span style="background-color: #C8E6C9;">Green highlights</span> are valid models found.

<span style="background-color: #FFCDD2;">Red highlights</span> are models that were found but are on the ignore list.

Flagging Incorrect Models:

If you see an incorrect model highlighted in green, highlight the text with your mouse.

Click the Flag Text button. This adds the text to the ignored_patterns.py file.

Click Re-scan to see the highlight change from green to red. The document's status will update.

Adding New Models:

If the tool missed a model, highlight the correct model text.

Click Suggest from Highlight.

Click Test Pattern to confirm it works.

Click the red Save to Custom Patterns button.

Project File Structure
START.bat: The main launcher for Windows users.

run.py: Launcher Script. Sets up the virtual environment and installs dependencies.

requirements.txt: A list of all required Python libraries.

main_app.py: Core Application. Contains all the UI code and main application logic.

data_harvester.py: Extraction Engine. Finds data using patterns and filters it against the ignore list.

ocr_utils.py: OCR Module. Handles text extraction from PDFs.

excel_processor.py: Excel Module. Manages cloning and populating the Excel template.

custom_patterns.py: (Auto-created) Stores all your custom-saved patterns.

ignored_patterns.py: (Auto-created) Stores all your flagged/ignored patterns.

/venv/: (Auto-created) The isolated Python virtual environment.

/OUTPUT/: (Auto-created) All processed Excel files are saved here.

/PDF_TEXT_OUTPUT/: (Auto-created) Contains the raw text extracted from every processed PDF.