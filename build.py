"""Build script for Nuitka packaging."""

from __future__ import annotations

import subprocess
import sys


def build() -> None:
    """Build Q-Caliper EXE using Nuitka."""
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--enable-plugin=pyside6",
        "--output-dir=dist",
        "--windows-console-mode=disable",
        "--product-name=Q-Caliper",
        "--file-version=0.1.0",
        "--product-version=0.1.0",
        "--company-name=Q-Caliper",
        "--file-description=质量工程桌面分析平台",
        "main.py",
    ]

    print("Building Q-Caliper EXE...")
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode == 0:
        print("\nBuild successful! Output: dist/main.exe")
    else:
        print(f"\nBuild failed with return code {result.returncode}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
