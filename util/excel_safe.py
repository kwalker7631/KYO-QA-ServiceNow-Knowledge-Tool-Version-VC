"""Utilities for safely writing Excel workbooks."""
from __future__ import annotations

from pathlib import Path
import logging
import os
import tempfile
from typing import Any


def ensure_output_dir(path: Path) -> None:
    """Ensure the output directory exists."""
    logging.debug("Ensuring output directory %s", path)
    path.mkdir(parents=True, exist_ok=True)


def build_output_path(output_dir: Path, base_name: str) -> Path:
    """Build a full output path under *output_dir* using *base_name*."""
    return output_dir / base_name


def save_workbook_safely(workbook: Any, path: Path) -> None:
    """Atomically save *workbook* to *path* using a temporary file."""
    logging.debug("Saving workbook to %s", path)
    ensure_output_dir(path.parent)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix=path.suffix) as tmp:
        temp_name = tmp.name
    try:
        workbook.save(temp_name)
        os.replace(temp_name, path)
        logging.info("Workbook saved to %s", path)
    except Exception:
        logging.exception("Failed to save workbook to %s", path)
        raise
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)
