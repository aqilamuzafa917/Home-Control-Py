# Smart Home Control Dashboard (Python/PyQt6)

A modern, "Apple-style" smart home dashboard built with Python and Qt (PyQt6).  
Designed for **macOS, Windows, and Linux**, it provides a centralized control capability for:

*   **WiZ Smart Lights** (Control, Sleep Mode, Circadian Rhythm)
*   **Xiaomi Air Purifiers** (miot protocol)
*   **IP Security Cameras** (RTSP via go2rtc low-latency bridge)

## Features

*   **📷 Low-Latency Video**: Uses `go2rtc` interactions for <500ms latency video feeds (RTSP -> WebRTC/MSE).
*   **💡 Advanced Lighting Control**: Group control for WiZ lights, Kelvin temperature adjustment, and custom "Sleep Mode" (Night light).
*   **💨 Air Quality Monitor**: Visualization of PM2.5 levels and control of Xiaomi Air Purifiers.
*   **🖥️ Dashboard UI**: Fluid animations, dark mode, responsive grid layouts, and unified "Safari-like" address bar status.

## Prerequisites

*   **Python 3.10+**
*   **Operating System:**
    *   **macOS** (Tested on Sonoma/Sequoia)
    *   **Windows** (10/11)
    *   **Linux** (Ubuntu/Debian)
*   **Dependencies:**
    *   **FFmpeg**: Required for video transcoding. Must be installed and available in system PATH.
        *   macOS: `brew install ffmpeg`
        *   Windows: Install and add to PATH.
        *   Linux: `sudo apt install ffmpeg`
*   **Usage of `go2rtc`**: This app relies on the `go2rtc` binary for video streaming.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/home-control-py.git
    cd home-control-py
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Build the App:**
    The build script will **automatically download** the correct `go2rtc` binary for your OS.
    ```bash
    python3 build.py
    ```

    The app will be compiled to the `dist/` folder.

## Configuration

The application automatically creates a configuration file in your home directory: `~/.home_control_config.json`.
You can configure devices via the UI **Settings** page:

*   **Cameras**: Add RTSP links or XMeye credentials.
*   **Xiaomi**: Enter IP and Token for Air Purifiers.
*   **WiZ**: Auto-discovery via UDP broadcast.

## Running the App

```bash
python3 -u smart_home.py
```

## Features in Detail

### 📹 Camera Tab
*   **Auto-reconnect**: Handles connection drops robustly.
*   **Progress Bar**: Safari-style loading bar in the top toolbar to indicate connection status.
*   **Fullscreen Mode**: Dedicated overlay viewer.
*   **Snapshots**: "Zoom" view support.

### 💡 WiZ Lights Tab
*   **Auto-Discovery**: Scans network for lights.
*   **Sleep Mode**: One-click "Night Light" setting (Scene 14, ultra-low dimming).
*   **Group Control**: Toggle all lights at once.

### 💨 Air Purifier Tab
*   **Ring Visualization**: Color-coded PM2.5 index.
*   **Mode Control**: Auto/Sleep/Favorite.

## Development

Built with:
*   **PyQt6**: UI Framework
*   **OpenCV**: Frame processing
*   **go2rtc**: RTSP handling
*   **python-miio**: Xiaomi communication
