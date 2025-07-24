# ocr_utils.py
# Author: Kenneth Walker
# Date: 2025-07-24
# Version: VC-10

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

# This module contains the logic for extracting text from PDFs,
# including a fallback to OCR for scanned documents.

MIN_TEXT_LENGTH_FOR_DIGITAL = 100 # If a PDF has less than this much text, assume it's scanned.

def extract_text_from_pdf(pdf_path) -> dict:
    """
    Extracts text from a PDF using a hybrid strategy.
    1. Tries direct text extraction via PyMuPDF.
    2. If that fails, falls back to OCR with Tesseract.

    Args:
        pdf_path: The Path object for the PDF file.

    Returns:
        A dictionary containing the extracted text and a flag indicating if OCR was used.
        Example: {"text": "...", "ocr_used": True}
    """
    full_text = ""
    ocr_performed = False

    try:
        # --- Stage 1: Attempt Direct Text Extraction ---
        doc = fitz.open(pdf_path)
        for page in doc:
            full_text += page.get_text()
        doc.close()

        # --- Stage 2: Check if OCR is needed ---
        if len(full_text.strip()) < MIN_TEXT_LENGTH_FOR_DIGITAL:
            ocr_performed = True
            full_text = "" # Reset text to fill with OCR content
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc):
                # Convert page to an image
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Use Tesseract to perform OCR on the image
                try:
                    # You may need to configure the path to tesseract executable
                    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                    page_text = pytesseract.image_to_string(image, lang='eng')
                    full_text += page_text + "\n"
                except pytesseract.TesseractNotFoundError:
                    return {"text": "TESSERACT NOT FOUND. Please install Tesseract-OCR and ensure it's in your system's PATH.", "ocr_used": True}
            doc.close()

        return {"text": full_text.strip(), "ocr_used": ocr_performed}

    except Exception as e:
        print(f"Critical error during text extraction for {pdf_path.name}: {e}")
        return {"text": f"Error extracting text: {e}", "ocr_used": False}
