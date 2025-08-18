# excel_processor.py
# Author: Kenneth Walker
# Date: 2025-08-15
# Version: VA-1.2 Version: VA-1.2.3 (Final Alpha)

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from pathlib import Path
from datetime import datetime

# This module handles all interactions with the Excel file. It is responsible
# for cloning the user's template, finding matching rows based on PDF filenames,
# and populating the relevant cells with the data harvested from the PDFs.

# --- CONFIGURATION ---
# These are the expected column names in the user's ServiceNow Excel template.
# They must match exactly (case-sensitive).
# UPDATED: Changed "Short description" to "Description" and it will now be populated.
DESCRIPTION_COL = "Description"
META_COL = "Meta"
AUTHOR_COL = "Author"
# This column will be added to the output file to show processing results.
STATUS_COL = "Processing Status"

def process_excel_file(template_path: Path, processed_data: list, output_dir: Path) -> Path:
    """
    Clones an Excel template, finds rows that correspond to the processed PDFs,
    and populates them with the extracted data and the PDF filename.

    Args:
        template_path (Path): Path to the user's ServiceNow Excel template.
        processed_data (list): A list of dictionaries from the main app,
                               each containing data for one processed PDF.
        output_dir (Path): The directory where the new Excel file will be saved.

    Returns:
        Path: The path to the newly created and populated Excel file.
    """
    # 1. Create a safe, timestamped clone of the template.
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_filename = f"PROCESSED_{template_path.stem}_{timestamp}.xlsx"
    cloned_path = output_dir / output_filename

    try:
        workbook = openpyxl.load_workbook(template_path)
        workbook.save(cloned_path)
    except Exception as e:
        raise IOError(f"Could not read or clone the Excel template at '{template_path}'. Error: {e}")

    # 2. Load the new clone and find the indices of our target columns.
    workbook = openpyxl.load_workbook(cloned_path)
    sheet = workbook.active

    headers = [cell.value for cell in sheet[1]]
    try:
        desc_idx = headers.index(DESCRIPTION_COL) + 1
        meta_idx = headers.index(META_COL) + 1
        author_idx = headers.index(AUTHOR_COL) + 1
    except ValueError as e:
        # If the Description column is missing, add it.
        if DESCRIPTION_COL not in headers:
            desc_idx = len(headers) + 1
            sheet.cell(row=1, column=desc_idx, value=DESCRIPTION_COL).font = Font(bold=True)
        else:
            raise ValueError(f"Missing a required column in Excel template: '{e}'. Please check the template.")

    # 3. Add our custom "Processing Status" column if it doesn't already exist.
    if STATUS_COL not in headers:
        status_idx = len(headers) + 1
        sheet.cell(row=1, column=status_idx, value=STATUS_COL).font = Font(bold=True)
    else:
        status_idx = headers.index(STATUS_COL) + 1

    # 4. Create a mapping from PDF filename stem to its data for fast lookups.
    data_map = {Path(item["filename"]).stem: item for item in processed_data}

    # 5. Iterate through spreadsheet rows, find matches, and populate data.
    # We will now write data starting from row 2.
    row_index = 2
    for pdf_stem, data in data_map.items():
        # --- NEW LOGIC ---
        # Instead of searching, we will now write a new line for each processed PDF.
        
        # a. Write the full PDF filename to the "Description" column.
        sheet.cell(row=row_index, column=desc_idx, value=data["filename"])

        # b. Compile the model numbers into a single string.
        models = ", ".join(sorted([item['text'] for item in data['found_items'] if item['type'] == 'Model' and not item['flagged']]))
        sheet.cell(row=row_index, column=meta_idx, value=models or "Not Found")

        # c. Populate the status column.
        sheet.cell(row=row_index, column=status_idx, value=data["status"])
        
        row_index += 1


    # 6. Apply conditional formatting for better readability.
    pass_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    review_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    fail_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
        status_cell = sheet.cell(row=row[0].row, column=status_idx)
        if status_cell.value:
            fill_color = None
            if "Pass" in status_cell.value:
                fill_color = pass_fill
            elif "Needs Review" in status_cell.value:
                fill_color = review_fill
            elif "Fail" in status_cell.value:
                fill_color = fail_fill

            if fill_color:
                for cell in row:
                    cell.fill = fill_color

    # 7. Save the final, populated workbook.
    workbook.save(cloned_path)
    return cloned_path
