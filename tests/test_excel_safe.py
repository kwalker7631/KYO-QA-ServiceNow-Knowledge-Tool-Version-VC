"""Tests for util.excel_safe."""
from pathlib import Path
import openpyxl

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from util import excel_safe


def test_save_workbook_safely(tmp_path: Path) -> None:
    wb = openpyxl.Workbook()
    target = tmp_path / "out.xlsx"
    excel_safe.save_workbook_safely(wb, target)
    assert target.exists()
    loaded = openpyxl.load_workbook(target)
    assert loaded is not None
