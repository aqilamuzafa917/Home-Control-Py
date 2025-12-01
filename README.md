# Home Control Py 🏠

A modern, native desktop dashboard to control **WiZ Smart Lights** and **Xiaomi Air Purifiers** directly from your Mac or PC.  
Built with Python 3.11 and CustomTkinter, featuring a clean macOS-style dark UI, local network control for instant response, and automated token extraction.

> **Note:** This is a personal hobby project. At the moment it supports WiZ lights and the Xiaomi Smart Air Purifier 4 Compact; additional devices may be added over time.

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## ✨ Features

### 💡 WiZ Lights
- **Auto-discovery** via UDP broadcast.
- **Zero setup** (no WiZ cloud login required).
- **Controls** for power, brightness, and color temperature (Kelvin).
- **Stateless sockets** each request to keep responses fast and reliable.

### 💨 Xiaomi Air Purifier (Smart Air Purifier 4 Compact)
- **QR-code login flow** that retrieves device token + IP automatically.
- **Local MIoT commands** (SIID/PIID) for direct hardware control.
- **Live dashboard** with PM2.5 (AQI), filter life, and mode indicators.
- **Manual slider** for fan speed (levels 1–14) when in Manual mode.
- **Credential persistence** so you don’t have to re-login every time.

---

## 🛠️ Prerequisites
- Python **3.11** (strongly recommended – matches dev/runtime environment).
- Your computer must share the same Wi‑Fi/LAN as the target devices.

---

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/aqilamuzafa917/Home-Control-Py.git
   cd home-control-py
   ```

2. **Install dependencies**
   ```bash
   python3.11 -m pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   python3.11 smart_home.py
   ```

---

## 🏗️ Building (macOS / Windows)

The repo ships with `build.py`, which wraps the PyInstaller command used in production.

1. **Install PyInstaller (if not already)**
   ```bash
   python3.11 -m pip install pyinstaller
   ```

2. **Run the build helper**
   ```bash
   python3.11 build.py
   ```

3. **Grab the binary**
   - Output lives in `dist/`
   - macOS: `dist/Home Control Py.app`
   - Windows: `dist/Home Control Py.exe`

> The helper passes the following options:  
> `--noconsole --windowed --onefile --clean --name="Home Control Py"`  
> plus `--collect-all` for `customtkinter`, `miio`, `micloud`, `certifi`, and `requests`.

---

## 📖 Usage Guide

### WiZ Lights Tab
1. Launch the app; discovery runs automatically.
2. If nothing appears, click **“⟳ Scan & Sync”**.
3. Use the sliders to adjust temperature and brightness, or tap the power button.

### Xiaomi Purifier Tab
1. Click **“Generate QR Code”** and scan it using the Mi Home mobile app (Scanner icon).  
   You can also hit **“Open in Browser”** to authenticate via web.
2. Once authenticated, the app fetches your local IP/token (defaults to the **Singapore (`sg`) server**).
3. Switch to **Manual** mode to enable the custom speed slider (levels 1–14).
4. Logout removes stored credentials if you need to re-authenticate.

---

## 🔧 Troubleshooting

**App works in terminal but hangs after packaging**  
- Almost always an SSL bundle issue. The included `get_ssl_cert_path()` fix and the PyInstaller flags (especially `--collect-all certifi`) solve it.

**Xiaomi device not found**  
- Ensure the purifier is online and tied to the same server region as configured (`sg` by default; change in `constants.py` if needed).

**WiZ lights do not respond**  
- Verify “Local Communication” is enabled in the WiZ mobile app settings.

---

## 📝 Configuration
- Xiaomi credentials are stored at `~/.xiaomi_config.json`.
- Use the in-app **Logout** button or delete the file manually to reset.

---

## 📜 Credits
- WiZ UDP command insights: [WiZ UDP Code Generator](https://seanmcnally.net/wiz-config.html)
- Xiaomi cloud authentication reference: [PiotrMachowski/Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor)
- MIoT specs & Home Assistant bridge: [al-one/hass-xiaomi-miot](https://github.com/al-one/hass-xiaomi-miot)

