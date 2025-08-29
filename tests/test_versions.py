"""Tests for tools.versions."""
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from tools import versions


def test_get_tesseract_cli_version_returns_string():
    result = versions.get_tesseract_cli_version()
    assert isinstance(result, str)
