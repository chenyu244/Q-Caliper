"""UI utility functions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def generate_report_filename(base_name: str, directory: str) -> str:
    """Generate a report filename with a date-time suffix.

    If a file with the same name already exists, appends a version
    letter (A, B, C ...) automatically.

    Parameters
    ----------
    base_name : str
        Base filename, e.g. ``"正态分析报告.pdf"``.
    directory : str
        Target directory path.

    Returns
    -------
    str
        Full path of the generated filename.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_stem = Path(base_name).stem
    name_suffix = Path(base_name).suffix or ".pdf"
    dir_path = Path(directory)

    candidate = f"{name_stem}_{timestamp}{name_suffix}"
    full_path = dir_path / candidate
    if not full_path.exists():
        return str(full_path)

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        candidate = f"{name_stem}_{timestamp}_{letter}{name_suffix}"
        full_path = dir_path / candidate
        if not full_path.exists():
            return str(full_path)

    i = 2
    while True:
        candidate = f"{name_stem}_{timestamp}_{i}{name_suffix}"
        full_path = dir_path / candidate
        if not full_path.exists():
            return str(full_path)
        i += 1
