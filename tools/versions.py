#!/usr/bin/env python
"""Print versions of key dependencies."""
import platform
import subprocess

import fitz
import openpyxl
import pytesseract
from PIL import Image


def get_tesseract_cli_version() -> str:
    """Return the version string of the Tesseract CLI."""
    try:
        out = subprocess.check_output(["tesseract", "--version"], text=True)
        return out.splitlines()[0]
    except Exception as exc:  # pylint: disable=broad-except
        return f"Tesseract not found: {exc}"


def main() -> None:
    """Display installed versions for troubleshooting."""
    print(f"Python: {platform.python_version()}")
    print(f"PyMuPDF: {getattr(fitz, '__version__', 'unknown')}")
    print(f"openpyxl: {openpyxl.__version__}")
    print(f"pytesseract: {pytesseract.__version__}")
    print(f"Pillow: {Image.__version__}")
    print(get_tesseract_cli_version())


if __name__ == "__main__":
    main()
