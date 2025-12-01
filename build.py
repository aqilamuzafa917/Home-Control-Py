"""PyInstaller build helper for the Smart Home application."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import PyInstaller.__main__  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent

PYINSTALLER_ARGS = [
    "--noconsole",
    "--windowed",
    "--onefile",
    "--clean",
    "--name=Home Control Py",
    "--collect-all=customtkinter",
    "--collect-all=miio",
    "--collect-all=micloud",
    "--collect-all=certifi",
    "--collect-all=requests",
    str(PROJECT_ROOT / "smart_home.py"),
]


def main() -> None:
    print("Executing PyInstaller with:\n ", " ".join(shlex.quote(arg) for arg in PYINSTALLER_ARGS))
    PyInstaller.__main__.run(PYINSTALLER_ARGS)


if __name__ == "__main__":
    main()

