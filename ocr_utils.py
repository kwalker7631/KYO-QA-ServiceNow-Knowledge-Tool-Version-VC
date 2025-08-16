# ocr_utils.py
# Author: Kenneth Walker
# Date: 2025-08-15
# Version: VA-1.0 (Final Alpha)

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from pathlib import Path

# This module contains the logic for extracting text from PDFs,
# including a robust fallback to OCR for scanned or image-based documents.

# --- Configuration ---
# If a PDF has less than this many characters of digital text,
# it is considered a scanned document, and OCR will be triggered.
MIN_TEXT_LENGTH_FOR_DIGITAL = 150
OCR_DPI = 300 # Dots Per Inch for rendering PDF pages to images for OCR

def extract_text_from_pdf(pdf_path: Path) -> dict:
    """
    Extracts text from a PDF using a hybrid strategy.
    1. Tries direct digital text extraction via PyMuPDF.
    2. If the extracted text is minimal, it assumes the PDF is scanned
       and falls back to performing OCR with Tesseract on each page.

    Args:
        pdf_path (Path): The Path object for the PDF file.

    Returns:
        dict: A dictionary containing:
              - "text" (str): The extracted text.
              - "ocr_used" (bool): True if Tesseract OCR was performed.
    """
    full_text = ""
    ocr_performed = False

    try:
        # --- Stage 1: Attempt Direct Digital Text Extraction ---
        doc = fitz.open(pdf_path)
        for page in doc:
            full_text += page.get_text()
        doc.close()

        # --- Stage 2: Check if OCR Fallback is Needed ---
        # If the text is very short, it's likely an image-based PDF.
        if len(full_text.strip()) < MIN_TEXT_LENGTH_FOR_DIGITAL:
            ocr_performed = True
            full_text = ""  # Reset text to be filled with OCR content
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc):
                # Convert the PDF page to a high-resolution image
                pix = page.get_pixmap(dpi=OCR_DPI)
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))

                # Use Tesseract to perform OCR on the image from memory
                try:
                    # NOTE: For this to work, Tesseract must be installed on the
                    # system and its executable must be in the system's PATH.
                    page_text = pytesseract.image_to_string(image, lang='eng')
                    full_text += page_text + "\n"
                except pytesseract.TesseractNotFoundError:
                    # This is a critical, blocking error. Return immediately.
                    error_msg = (
                        "TESSERACT NOT FOUND. Please install Tesseract-OCR "
                        "and ensure its installation directory is in your system's PATH."
                    )
                    return {"text": error_msg, "ocr_used": True}
            doc.close()

        return {"text": full_text.strip(), "ocr_used": ocr_performed}

    except Exception as e:
        # Catch any other errors during file processing (e.g., corrupted PDF)
        print(f"Critical error during text extraction for {pdf_path.name}: {e}")
        return {"text": f"Error extracting text: {e}", "ocr_used": False}
