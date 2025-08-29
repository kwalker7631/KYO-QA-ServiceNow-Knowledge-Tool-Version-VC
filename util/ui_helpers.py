"""Cross-platform UI helper functions."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def reveal_in_explorer(path: Path) -> None:
    """Show *path* in the system's file explorer."""
    path = Path(path).resolve()
    if sys.platform.startswith("win"):
        subprocess.run(["explorer", "/select,", str(path)], check=False)
    elif sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path.parent)], check=False)
