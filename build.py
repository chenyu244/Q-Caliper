"""Build script for Nuitka packaging (standalone multi-file mode)."""

from __future__ import annotations

import subprocess
import sys


def build() -> None:
    """Build Q-Caliper standalone using Nuitka."""
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",
        "--assume-yes-for-downloads",
        "--output-dir=dist",
        "--output-filename=Q-Caliper.exe",
        "--windows-console-mode=disable",
        "--product-name=Q-Caliper",
        "--file-version=1.0.1",
        "--product-version=1.0.1",
        "--company-name=Q-Caliper",
        "--file-description=质量工程桌面分析平台",
        "--windows-icon-from-ico=images/Q-Caliper.ico",
        "--include-data-dir=q_caliper/reports/templates=q_caliper/reports/templates",
        "--follow-imports",
        "--jobs=4",
        "--remove-output",
        "main.py",
    ]

    print("Building Q-Caliper (standalone)...")
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode == 0:
        print("\nBuild successful!")
        print("Output: dist/main.dist/")
        print("Run: dist/main.dist/Q-Caliper.exe")
    else:
        print(f"\nBuild failed with return code {result.returncode}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
