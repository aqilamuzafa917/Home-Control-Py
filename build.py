"""PyInstaller build helper for the Smart Home application."""

from __future__ import annotations

import shlex
import sys
import os
import platform
import urllib.request
import zipfile
import stat
from pathlib import Path

import PyInstaller.__main__  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent
GO2RTC_VERSION = "v1.9.8" # Pin version for stability

def download_go2rtc():
    """Downloads the correct go2rtc binary for the current platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    bin_name = "go2rtc.exe" if system == "windows" else "go2rtc"
    bin_path = PROJECT_ROOT / bin_name
    
    if bin_path.exists():
        print(f"✅ Found {bin_name}, skipping download.")
        return

    print(f"⬇️ {bin_name} not found. Detecting platform...")
    
    # Map platform to filename
    # release: https://github.com/AlexxIT/go2rtc/releases/download/{tag}/{filename}
    filename = ""
    
    if system == "darwin": # macOS
        if "arm" in machine or "aarch" in machine:
            filename = "go2rtc_mac_arm64"
        else:
            filename = "go2rtc_mac_amd64"
            
    elif system == "windows":
        filename = "go2rtc_win64.zip" 
        
    elif system == "linux":
        if "arm" in machine or "aarch" in machine:
            filename = "go2rtc_linux_arm64"
        else:
             filename = "go2rtc_linux_amd64"
    
    if not filename:
        print(f"❌ Could not determine go2rtc binary for {system} {machine}. Please download manually.")
        sys.exit(1)
        
    url = f"https://github.com/AlexxIT/go2rtc/releases/download/{GO2RTC_VERSION}/{filename}"
    print(f"⬇️ Downloading {url}...")
    
    try:
        if filename.endswith(".zip"):
            zip_path = PROJECT_ROOT / filename
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extract("go2rtc.exe", PROJECT_ROOT)
            os.remove(zip_path) # Cleanup zip
        else:
            urllib.request.urlretrieve(url, bin_path)
            
        print("✅ Download complete.")
        
        # Make executable on Unix
        if system != "windows":
            st = os.stat(bin_path)
            os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
            
    except Exception as e:
        print(f"❌ Failed to download go2rtc: {e}")
        sys.exit(1)


PYINSTALLER_ARGS = [
    "--noconsole",
    "--windowed",
    "--onefile",
    "--clean",
    "--name=Home Control Py",
    "--osx-bundle-identifier=com.aqilamuzafa.homecontrolpy",
    "--collect-all=customtkinter",
    "--collect-all=miio",
    "--collect-all=micloud",
    "--collect-all=certifi",
    "--collect-all=requests",
    "--add-binary=go2rtc:." if sys.platform != "win32" else "--add-binary=go2rtc.exe:.",
    str(PROJECT_ROOT / "smart_home.py"),
]


def main() -> None:
    download_go2rtc()
    print("Executing PyInstaller with:\n ", " ".join(shlex.quote(arg) for arg in PYINSTALLER_ARGS))
    PyInstaller.__main__.run(PYINSTALLER_ARGS)


if __name__ == "__main__":
    main()

